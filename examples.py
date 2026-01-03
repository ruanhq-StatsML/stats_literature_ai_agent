#!/usr/bin/env python3
"""
Example script demonstrating how to use the research agent system.

Usage:
    python examples.py [example_number]

    python examples.py 1  # Single agent query
    python examples.py 2  # Cross-domain query
    python examples.py 3  # Full pipeline (research + applications + product)
    python examples.py 4  # Direct agent access
    python examples.py 5  # Coordinator mode
"""

import sys
import os

# Ensure OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable not set")
    print("Run: export OPENAI_API_KEY='your-key-here'")
    sys.exit(1)


def example_1_single_domain():
    """Single domain query - Statistics only."""
    print("\n" + "="*60)
    print("Example 1: Single Domain Query (Statistics)")
    print("="*60)

    from langgraph_agent import run_research_query

    question = "What is LASSO regression and when should I use it?"
    response = run_research_query(question)
    print(response)


def example_2_cross_domain():
    """Cross-domain query - Statistics + Psychiatry."""
    print("\n" + "="*60)
    print("Example 2: Cross-Domain Query (Statistics + Psychiatry)")
    print("="*60)

    from langgraph_agent import run_research_query

    question = "How are propensity scores used in psychiatric drug trials?"
    response = run_research_query(question)
    print(response)


def example_3_full_pipeline():
    """Full pipeline - Research + Applications + Product Manager."""
    print("\n" + "="*60)
    print("Example 3: Full Pipeline (Research → Applications → Product)")
    print("="*60)

    from langgraph_agent import run_research_query

    question = """I want to build a product that uses A/B testing for e-commerce optimization.
    What's the statistical methodology, how do companies like Amazon use it,
    and how should I productize this as a SaaS offering?"""

    response = run_research_query(question)
    print(response)


def example_4_direct_agents():
    """Direct access to individual agents."""
    print("\n" + "="*60)
    print("Example 4: Direct Agent Access")
    print("="*60)

    from agents import StatisticsAgent, ApplicationsAgent, ProductManagerAgent

    # Initialize agents
    stats = StatisticsAgent()
    apps = ApplicationsAgent()
    pm = ProductManagerAgent()

    topic = "collaborative filtering for recommendation systems"

    # Query each agent
    print("\n--- Statistics Agent ---")
    theory = stats.chat(f"Explain the statistical methodology behind {topic}")
    print(theory[:500] + "..." if len(theory) > 500 else theory)

    print("\n--- Applications Agent ---")
    use_cases = apps.chat(f"How is {topic} used in industry? Give specific examples.")
    print(use_cases[:500] + "..." if len(use_cases) > 500 else use_cases)

    print("\n--- Product Manager Agent ---")
    product = pm.chat(f"How would you productize {topic}? Define user needs, MVP, and success metrics.")
    print(product[:500] + "..." if len(product) > 500 else product)


def example_5_coordinator():
    """Using the Coordinator to automatically orchestrate agents."""
    print("\n" + "="*60)
    print("Example 5: Coordinator Mode (Auto-orchestration)")
    print("="*60)

    from agents import CoordinatorAgent

    coordinator = CoordinatorAgent()

    # The coordinator will automatically decide which agents to use
    question = "What are the latest developments in causal inference and how can they be applied to marketing attribution products?"

    print(f"\nQuestion: {question}\n")
    print("Coordinator analyzing and delegating...\n")

    response = coordinator.chat(question)
    print(response)


def list_examples():
    """List all available examples."""
    print("\nAvailable examples:")
    print("  1 - Single domain query (Statistics)")
    print("  2 - Cross-domain query (Statistics + Psychiatry)")
    print("  3 - Full pipeline (Research + Applications + Product)")
    print("  4 - Direct agent access (manual control)")
    print("  5 - Coordinator mode (auto-orchestration)")
    print("\nUsage: python examples.py [1-5]")
    print("       python examples.py      # Run example 1")


def main():
    examples = {
        "1": example_1_single_domain,
        "2": example_2_cross_domain,
        "3": example_3_full_pipeline,
        "4": example_4_direct_agents,
        "5": example_5_coordinator,
    }

    if len(sys.argv) > 1:
        choice = sys.argv[1]
        if choice in examples:
            examples[choice]()
        elif choice in ["-h", "--help", "help"]:
            list_examples()
        else:
            print(f"Unknown example: {choice}")
            list_examples()
    else:
        # Default to example 1
        list_examples()
        print("\nRunning Example 1 by default...\n")
        example_1_single_domain()


if __name__ == "__main__":
    main()
