"""
Memory-Enhanced Base Agent.

Demonstrates minimal integration of the context-rot prevention system
with the existing BaseAgent architecture. This is an opt-in enhancement
that doesn't break backward compatibility.
"""

import json
import os
from typing import Optional

from openai import OpenAI
from duckduckgo_search import DDGS

from memory import (
    MemoryAgentMixin,
    MemoryCategory,
    RetrievalIntent,
    create_memory_system,
)


class MemoryEnhancedAgent(MemoryAgentMixin):
    """
    Base agent with integrated memory system.

    This is an enhanced version of BaseAgent that includes:
    - Three-tier memory (working, long-term, episodic)
    - Explicit state management
    - Gated retrieval with decay
    - Drift detection and contradiction checking

    The memory features are completely optional and can be disabled.
    """

    def __init__(
        self,
        enable_memory: bool = True,
        memory_persist_dir: Optional[str] = None,
    ):
        """
        Initialize the memory-enhanced agent.

        Args:
            enable_memory: Whether to enable memory features (default True)
            memory_persist_dir: Directory for memory persistence (optional)
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        self.tools = self._get_tools()

        # Initialize memory if enabled
        if enable_memory:
            persist_dir = memory_persist_dir or os.path.join(
                os.path.dirname(__file__), "..", ".memory_store", self.name
            )
            self.init_memory(persist_dir=persist_dir)

    @property
    def name(self) -> str:
        return "MemoryEnhancedAgent"

    @property
    def description(self) -> str:
        return "Base agent with context-rot prevention memory system"

    @property
    def system_prompt(self) -> str:
        base_prompt = """You are a helpful research assistant with enhanced memory capabilities.
You can remember important facts, decisions, and context across conversations.
You track your own assumptions and flag when information may need verification."""

        # Append memory context if enabled
        if self.memory_enabled:
            memory_context = self.get_context_for_llm()
            if memory_context:
                base_prompt += f"\n\n{memory_context}"

        return base_prompt

    def _get_tools(self) -> list:
        """Get the tools available to this agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information, papers, and articles.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def web_search(self, query: str) -> str:
        """Perform a web search using DuckDuckGo."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))

            if not results:
                return "No results found."

            formatted = []
            for r in results:
                formatted.append(
                    f"Title: {r['title']}\n"
                    f"URL: {r['href']}\n"
                    f"Snippet: {r['body']}\n"
                )
            return "\n---\n".join(formatted)
        except Exception as e:
            return f"Search error: {e}"

    def _process_tool_calls(self, tool_calls) -> list:
        """Process tool calls and return results."""
        results = []
        for tool_call in tool_calls:
            if tool_call.function.name == "web_search":
                args = json.loads(tool_call.function.arguments)
                query = args["query"]
                print(f"  [{self.name}] Searching: {query[:50]}...")

                result = self.web_search(query)

                # Log tool output to memory (summarized)
                self.on_tool_call("web_search", f"Query: {query[:30]}... ({len(result)} chars)")

                results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": result
                })
        return results

    def chat(self, user_message: str) -> str:
        """Send a message and get a response with memory enhancement."""
        # Pre-chat: add to memory context
        self.on_chat_start(user_message)

        # Store user message in conversation history
        self.conversation_history.append({"role": "user", "content": user_message})

        # Check for user constraints/goals in the message
        self._extract_constraints(user_message)

        while True:
            # Get memory-enhanced system prompt
            system_prompt = self.system_prompt

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": system_prompt}] + self.conversation_history,
                tools=self.tools,
                tool_choice="auto"
            )

            message = response.choices[0].message

            if message.tool_calls:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                tool_results = self._process_tool_calls(message.tool_calls)
                self.conversation_history.extend(tool_results)

                # Store factual information from search results
                self._extract_facts_from_tools(tool_results)

            else:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content
                })

                # Post-chat: record response
                self.on_chat_end(message.content)

                # Record any decisions made in the response
                self._extract_decisions(message.content)

                return message.content

    def _extract_constraints(self, message: str) -> None:
        """Extract and store user constraints from message."""
        if not self.memory_enabled:
            return

        constraint_keywords = [
            "must", "should", "need to", "require", "only",
            "don't", "avoid", "focus on", "prioritize"
        ]
        message_lower = message.lower()
        for keyword in constraint_keywords:
            if keyword in message_lower:
                self.note_user_constraint(message[:200])
                break

    def _extract_facts_from_tools(self, tool_results: list) -> None:
        """Extract and store factual information from tool results."""
        if not self.memory_enabled:
            return

        for result in tool_results:
            content = result.get("content", "")
            # Simple heuristic: store snippets that look like facts
            lines = content.split("\n")
            for line in lines:
                if line.startswith("Snippet:") and len(line) > 50:
                    snippet = line.replace("Snippet:", "").strip()
                    # Only store if it looks factual (contains numbers, specific claims)
                    if any(c.isdigit() for c in snippet):
                        self.remember(
                            snippet[:300],
                            category=MemoryCategory.FACTUAL,
                            source="web_search",
                            confidence=0.6,  # Lower confidence for web results
                        )

    def _extract_decisions(self, response: str) -> None:
        """Extract and record decisions from agent response."""
        if not self.memory_enabled:
            return

        decision_keywords = [
            "I recommend", "I suggest", "We should", "The best approach",
            "I've decided", "Let's", "Based on"
        ]
        for keyword in decision_keywords:
            if keyword.lower() in response.lower():
                # Record first sentence after keyword as decision
                idx = response.lower().find(keyword.lower())
                decision_text = response[idx:idx+200].split('.')[0]
                self.note_decision(decision_text, "derived from response")
                break

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        if self.memory_enabled:
            self.memory.clear_working_context()

    def get_memory_summary(self) -> str:
        """Get a summary of the memory state."""
        if not self.memory_enabled:
            return "Memory not enabled"
        return self.memory.generate_summary(f"{self.name} Memory")


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("Creating memory-enhanced agent...")
    agent = MemoryEnhancedAgent(enable_memory=True)

    print("\nMemory system initialized:")
    print(agent.get_memory_summary())

    print("\nSimulating a conversation...")
    agent.note_context("User is researching cognitive biases in e-commerce")
    agent.remember(
        "Anchoring bias has effect size d=0.3-0.5 in pricing studies",
        MemoryCategory.FACTUAL,
        "example_setup",
        0.85
    )

    print("\nRecalling memories about pricing...")
    memories = agent.recall("pricing bias")
    for mem in memories:
        print(f"  - {mem}")

    print("\nMemory health status:")
    print(agent.get_memory_health())
