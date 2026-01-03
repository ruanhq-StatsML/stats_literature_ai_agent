#!/usr/bin/env python3
"""
Statistics Literature Review Agent (OpenAI GPT-4 Version)

An interactive agent that helps researchers find and summarize
academic papers in Statistics using GPT-4.
"""

import json
import os
from openai import OpenAI
from duckduckgo_search import DDGS

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert Statistics literature review assistant.
Your role is to help researchers find, analyze, and summarize academic papers in Statistics.

When the user asks about a topic, you should:
1. Use the search tool to find relevant academic papers, focusing on:
   - arXiv (arxiv.org)
   - Google Scholar
   - Statistics journals (JASA, Annals of Statistics, Biometrika, etc.)

2. For each relevant paper found, provide:
   - Title and authors
   - Publication venue and year
   - Key contributions/findings
   - Methodology used

3. Synthesize findings to identify:
   - Common themes and approaches
   - Recent trends and developments
   - Seminal/foundational works

4. Always cite sources with URLs when available.

Be thorough but concise. Focus on statistical methodology and theory."""

# Define the search tool
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for academic papers and articles. Use this to find statistics papers on arXiv, Google Scholar, and academic journals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Include 'statistics', 'arxiv', or 'paper' for academic results."
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def web_search(query: str) -> str:
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


def process_tool_calls(tool_calls):
    """Process tool calls and return results."""
    results = []
    for tool_call in tool_calls:
        if tool_call.function.name == "web_search":
            args = json.loads(tool_call.function.arguments)
            result = web_search(args["query"])
            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "content": result
            })
    return results


def chat(user_message: str, conversation_history: list) -> str:
    """Send a message and get a response, handling tool calls."""

    conversation_history.append({"role": "user", "content": user_message})

    while True:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
            tools=TOOLS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # Check if the model wants to use tools
        if message.tool_calls:
            # Add assistant's message with tool calls to history
            conversation_history.append({
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

            # Process tools and add results
            tool_results = process_tool_calls(message.tool_calls)
            conversation_history.extend(tool_results)

            print("  [Searching...]")
            # Continue the loop to get the final response
        else:
            # No more tool calls, return the response
            conversation_history.append({"role": "assistant", "content": message.content})
            return message.content


def main():
    """Run the interactive literature review agent."""

    print("=" * 60)
    print("  Statistics Literature Review Agent (GPT-4)")
    print("=" * 60)
    print("\nI can help you find and summarize statistics papers.")
    print("Examples:")
    print("  - 'Find recent papers on Bayesian optimization'")
    print("  - 'What are the key papers on causal inference?'")
    print("  - 'Summarize methods for high-dimensional regression'")
    print("\nType 'quit' or 'exit' to end the session.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("\nYour query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ('quit', 'exit', 'q'):
            print("\nGoodbye! Happy researching!")
            break

        print("\nSearching and analyzing...\n")

        try:
            response = chat(user_input, conversation_history)
            print(response)
        except Exception as e:
            print(f"Error: {e}")
            print("Please check your API key and try again.")


if __name__ == "__main__":
    main()
