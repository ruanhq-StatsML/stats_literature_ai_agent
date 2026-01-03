#!/usr/bin/env python3
"""
Multi-Agent Research Assistant

An interactive system with specialized agents for literature review
across multiple domains. Supports two modes:
1. LangGraph mode (default): Self-corrective workflow with hallucination checking
2. Coordinator mode: Classic multi-agent orchestration
"""

import argparse
import sys


def run_langgraph_mode():
    """Run the LangGraph-based research agent with self-correction."""
    from langgraph_agent import run_research_query

    print("=" * 60)
    print("  LangGraph Research Agent")
    print("  With routing, self-correction, and hallucination checking")
    print("=" * 60)

    print("\nFeatures:")
    print("  - Smart routing to appropriate domain expert(s)")
    print("  - Cross-domain synthesis for interdisciplinary queries")
    print("  - Hallucination checking (verifies claims are grounded)")
    print("  - Self-correction loop (refines answers up to 3 times)")
    print("  - Web search fallback for additional sources")

    print("\nDomains:")
    print("  - statistics      : Statistical methods, ML theory, causal inference")
    print("  - biology         : Molecular biology, genetics, ecology")
    print("  - psychology      : Cognitive, social, clinical psychology")
    print("  - philosophy      : Ethics, epistemology, philosophy of science")
    print("  - psychiatry      : Mental disorders, psychopharmacology")
    print("  - applications    : Real-world use cases, industry implementations")
    print("  - product_manager : Product strategy, user needs, research-to-product")

    print("\nExamples:")
    print("  - 'What is propensity score matching?'")
    print("  - 'How is causal inference used in psychiatric trials?'")
    print("  - 'What are industry applications of A/B testing?'")
    print("  - 'How can I productize a recommendation system based on collaborative filtering?'")

    print("\nCommands:")
    print("  'quit'  - Exit the program")
    print("\n" + "=" * 60)

    while True:
        try:
            user_input = input("\nYour question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ('quit', 'exit', 'q'):
            print("\nGoodbye! Happy researching!")
            break

        try:
            response = run_research_query(user_input)
            print("\n" + "=" * 60)
            print("FINAL RESPONSE:")
            print("=" * 60)
            print(response)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


def run_coordinator_mode():
    """Run the classic coordinator-based multi-agent system."""
    from agents import CoordinatorAgent

    print("=" * 60)
    print("  Multi-Agent Research Assistant (Coordinator Mode)")
    print("=" * 60)

    coordinator = CoordinatorAgent()

    print("\n" + coordinator.list_agents())
    print("\n" + "=" * 60)
    print("\nI can help you with research across multiple domains.")
    print("For cross-domain queries, I'll coordinate multiple specialists.")
    print("\nExamples:")
    print("  - 'Find papers on statistical methods in psychology research'")
    print("  - 'What's the philosophy of consciousness in psychiatry?'")
    print("  - 'Review literature on Bayesian methods in biology'")
    print("  - 'How is machine learning applied in healthcare?'")
    print("\nCommands:")
    print("  'agents'  - List available specialist agents")
    print("  'clear'   - Clear conversation history")
    print("  'quit'    - Exit the program")
    print("\n" + "=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ('quit', 'exit', 'q'):
            print("\nGoodbye! Happy researching!")
            break

        if user_input.lower() == 'agents':
            print("\n" + coordinator.list_agents())
            continue

        if user_input.lower() == 'clear':
            coordinator.clear_all_history()
            print("\nConversation history cleared for all agents.")
            continue

        print("\nAnalyzing and coordinating...\n")

        try:
            response = coordinator.chat(user_input)
            print("\n" + "-" * 40)
            print(response)
        except Exception as e:
            print(f"Error: {e}")
            print("Please check your API key and try again.")


def main():
    """Parse arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Research Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                  # Run LangGraph mode (default)
  python main.py --mode langgraph # Run LangGraph mode explicitly
  python main.py --mode coordinator  # Run classic coordinator mode
        """
    )
    parser.add_argument(
        "--mode",
        choices=["langgraph", "coordinator"],
        default="langgraph",
        help="Execution mode: 'langgraph' (self-corrective, default) or 'coordinator' (classic)"
    )

    args = parser.parse_args()

    if args.mode == "langgraph":
        run_langgraph_mode()
    else:
        run_coordinator_mode()


if __name__ == "__main__":
    main()
