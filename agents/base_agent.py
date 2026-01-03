"""Base agent class with shared functionality."""

import json
import os
from abc import ABC, abstractmethod
from openai import OpenAI
from duckduckgo_search import DDGS


class BaseAgent(ABC):
    """Base class for all research agents."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        self.tools = self._get_tools()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description for the coordinator."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent."""
        pass

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
                print(f"  [{self.name}] Searching: {args['query'][:50]}...")
                result = self.web_search(args["query"])
                results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": result
                })
        return results

    def chat(self, user_message: str) -> str:
        """Send a message and get a response."""
        self.conversation_history.append({"role": "user", "content": user_message})

        while True:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": self.system_prompt}] + self.conversation_history,
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
            else:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content
                })
                return message.content

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
