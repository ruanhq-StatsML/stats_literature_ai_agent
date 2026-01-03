#!/usr/bin/env python3
"""
Statistics Literature Review Agent

An interactive agent that helps researchers find and summarize
academic papers in Statistics.
"""

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

SYSTEM_PROMPT = """You are an expert Statistics literature review assistant.
Your role is to help researchers find, analyze, and summarize academic papers in Statistics.

When the user asks about a topic, you should:
1. Search for relevant academic papers, focusing on reputable sources like:
   - arXiv (arxiv.org)
   - Google Scholar
   - JSTOR
   - PubMed (for biostatistics)
   - Statistics journals (JASA, Annals of Statistics, Biometrika, etc.)

2. For each relevant paper found, provide:
   - Title and authors
   - Publication venue and year
   - Key contributions/findings
   - Methodology used
   - Relevance to the user's query

3. Synthesize findings across multiple papers to identify:
   - Common themes and approaches
   - Gaps in the literature
   - Recent trends and developments
   - Seminal/foundational works

4. Always cite sources with URLs when available.

Be thorough but concise. Focus on statistical methodology and theory."""


async def run_literature_review():
    """Run an interactive literature review session."""

    print("=" * 60)
    print("  Statistics Literature Review Agent")
    print("=" * 60)
    print("\nI can help you find and summarize statistics papers.")
    print("Examples:")
    print("  - 'Find recent papers on Bayesian optimization'")
    print("  - 'What are the key papers on causal inference?'")
    print("  - 'Summarize methods for high-dimensional regression'")
    print("\nType 'quit' or 'exit' to end the session.\n")

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
            async for message in query(
                prompt=user_input,
                options=ClaudeAgentOptions(
                    system_prompt=SYSTEM_PROMPT,
                    allowed_tools=["WebSearch", "WebFetch"],
                )
            ):
                # Print the final result
                if hasattr(message, "result"):
                    print(message.result)
                # Print assistant messages as they stream
                elif hasattr(message, "content") and message.role == "assistant":
                    for block in message.content:
                        if hasattr(block, "text"):
                            print(block.text)

        except Exception as e:
            print(f"Error: {e}")
            print("Please try again or rephrase your query.")


def main():
    """Entry point."""
    asyncio.run(run_literature_review())


if __name__ == "__main__":
    main()
