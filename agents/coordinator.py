"""Coordinator Agent - Orchestrates multiple specialized agents."""

import json
import os
from openai import OpenAI

from .statistics_agent import StatisticsAgent
from .biology_agent import BiologyAgent
from .psychology_agent import PsychologyAgent
from .philosophy_agent import PhilosophyAgent
from .psychiatry_agent import PsychiatryAgent
from .applications_agent import ApplicationsAgent
from .product_manager_agent import ProductManagerAgent
from .writing_agent import WritingAgent


class CoordinatorAgent:
    """
    Coordinator that routes queries to specialized agents and synthesizes results.

    This agent analyzes user requests and delegates to the appropriate
    specialist agent(s), handling cross-domain queries by coordinating
    multiple agents.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []

        # Initialize all specialist agents
        self.agents = {
            "statistics": StatisticsAgent(),
            "biology": BiologyAgent(),
            "psychology": PsychologyAgent(),
            "philosophy": PhilosophyAgent(),
            "psychiatry": PsychiatryAgent(),
            "applications": ApplicationsAgent(),
            "product_manager": ProductManagerAgent(),
            "writing": WritingAgent(),
        }

        self.tools = self._get_tools()

    def _get_agent_descriptions(self) -> str:
        """Get descriptions of all available agents."""
        descriptions = []
        for key, agent in self.agents.items():
            descriptions.append(f"- {key}: {agent.name} - {agent.description}")
        return "\n".join(descriptions)

    @property
    def system_prompt(self) -> str:
        return f"""You are a Coordinator Agent that manages a team of specialized research assistants.

Your role is to:
1. Analyze user queries to determine which specialist(s) should handle them
2. Delegate tasks to the appropriate agent(s)
3. For cross-domain queries, coordinate multiple agents
4. Synthesize results from multiple agents into coherent responses

Available specialist agents:
{self._get_agent_descriptions()}

Guidelines:
- For simple, single-domain queries, delegate to one specialist
- For cross-domain queries (e.g., "statistical methods in psychology"), delegate to multiple specialists
- For questions about real-world applications, include the applications agent
- For product strategy, user needs, or research-to-product questions, include the product_manager agent
- For documentation needs (PRDs, research papers, technical reports, white papers), include the writing agent
- When combining theory with practice, use domain expert + applications agent together
- For full research-to-product pipeline, use: domain expert + applications + product_manager
- For comprehensive documentation workflows, use: domain expert + product_manager + writing
- When multiple agents are needed, clearly explain how their perspectives complement each other
- Always identify which agent(s) provided which information in your synthesis

When delegating, use the delegate_to_agent tool with the agent key and a clear, specific query."""

    def _get_tools(self) -> list:
        """Get coordinator tools."""
        agent_keys = list(self.agents.keys())
        return [
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_agent",
                    "description": "Delegate a query to a specialist agent. Use this to get expert research on specific domains.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "enum": agent_keys,
                                "description": "The specialist agent to delegate to."
                            },
                            "query": {
                                "type": "string",
                                "description": "The specific query for the specialist agent."
                            }
                        },
                        "required": ["agent", "query"]
                    }
                }
            }
        ]

    def _process_tool_calls(self, tool_calls) -> list:
        """Process delegation tool calls."""
        results = []
        for tool_call in tool_calls:
            if tool_call.function.name == "delegate_to_agent":
                args = json.loads(tool_call.function.arguments)
                agent_key = args["agent"]
                query = args["query"]

                agent = self.agents.get(agent_key)
                if agent:
                    print(f"\n  [Coordinator] Delegating to {agent.name}...")
                    response = agent.chat(query)
                    results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": f"[Response from {agent.name}]:\n{response}"
                    })
                else:
                    results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": f"Error: Agent '{agent_key}' not found."
                    })
        return results

    def chat(self, user_message: str) -> str:
        """Process a user message and coordinate agents."""
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

    def clear_all_history(self):
        """Clear conversation history for coordinator and all agents."""
        self.conversation_history = []
        for agent in self.agents.values():
            agent.clear_history()

    def list_agents(self) -> str:
        """List all available specialist agents."""
        lines = ["Available Specialist Agents:", "=" * 40]
        for key, agent in self.agents.items():
            lines.append(f"\n[{key}] {agent.name}")
            lines.append(f"    {agent.description}")
        return "\n".join(lines)
