#!/usr/bin/env python3
"""
Run the Memory-Enhanced Agent locally.

This script demonstrates the context-rot prevention memory system
in an interactive chat session.

Usage:
    python run_memory_agent.py
    python run_memory_agent.py --no-persist  # Disable persistence
    python run_memory_agent.py --demo        # Run demo mode
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from agents import MemoryEnhancedAgent
from memory import MemoryCategory, RetrievalIntent


def print_header():
    """Print welcome header."""
    print()
    print("=" * 60)
    print("  MEMORY-ENHANCED RESEARCH AGENT")
    print("  Context-Rot Prevention System Demo")
    print("=" * 60)
    print()


def print_commands():
    """Print available commands."""
    print("Commands:")
    print("  /memory     - Show memory summary")
    print("  /health     - Show memory health status")
    print("  /recall     - Recall memories (prompts for query)")
    print("  /decisions  - Show recent decisions")
    print("  /state      - Show agent state")
    print("  /clear      - Clear conversation history")
    print("  /help       - Show this help")
    print("  /quit       - Exit")
    print()


def run_demo(agent: MemoryEnhancedAgent):
    """Run a demonstration of memory features."""
    print("\n>>> DEMO MODE: Demonstrating Memory Features\n")
    print("-" * 50)

    # 1. Store some initial memories
    print("\n1. Storing factual memories...")
    agent.remember(
        "Anchoring bias has effect size d=0.3-0.5 in pricing studies",
        MemoryCategory.FACTUAL,
        "demo:cognitive_bias_research",
        confidence=0.9
    )
    agent.remember(
        "Social proof increases conversion by 10-15% on average",
        MemoryCategory.FACTUAL,
        "demo:social_proof_meta_analysis",
        confidence=0.85
    )
    agent.remember(
        "Loss aversion coefficient lambda typically 2.0-2.5",
        MemoryCategory.FACTUAL,
        "demo:kahneman_tversky",
        confidence=0.95
    )
    print("   Stored 3 factual memories")

    # 2. Set up agent state
    print("\n2. Setting up agent state...")
    agent.memory.set_goal("Analyze cognitive biases for e-commerce optimization")
    agent.memory.add_user_constraint("Focus on quantitative effect sizes")
    agent.memory.add_assumption(
        "Users respond predictably to scarcity signals",
        confidence=0.75,
        source="inferred from literature"
    )
    print("   Set goal, constraint, and assumption")

    # 3. Record some decisions
    print("\n3. Recording decisions...")
    agent.note_decision(
        "Use meta-analysis effect sizes over individual studies",
        "More reliable and generalizable"
    )
    agent.note_decision(
        "Prioritize anchoring and social proof for MVP",
        "Highest effect sizes with lowest implementation cost"
    )
    print("   Recorded 2 decisions")

    # 4. Show memory summary
    print("\n4. Memory Summary:")
    print("-" * 40)
    print(agent.get_memory_summary())

    # 5. Demonstrate recall
    print("\n5. Recalling memories about 'bias effect'...")
    memories = agent.recall("bias effect sizes", RetrievalIntent.FACTUAL_QA)
    for i, mem in enumerate(memories, 1):
        print(f"   [{i}] {mem[:70]}...")

    # 6. Show health status
    print("\n6. Memory Health Status:")
    health = agent.get_memory_health()
    print(f"   Enabled: {health.get('enabled', False)}")
    print(f"   Policy: {health.get('policy', 'N/A')}")
    print(f"   Active Memories: {health.get('active_memories', 0)}")

    # 7. Simulate drift detection
    print("\n7. Simulating drift detection...")
    print("   Recording user corrections...")
    agent.on_user_correction("Incorrect effect size cited")
    agent.on_user_correction("Wrong study reference")
    health = agent.get_memory_health()
    print(f"   Policy after corrections: {health.get('policy', 'N/A')}")

    # 8. Reset
    print("\n8. Completing task (resetting quality signals)...")
    agent.memory.on_task_complete(success=True)
    health = agent.get_memory_health()
    print(f"   Policy after reset: {health.get('policy', 'N/A')}")

    print("\n" + "-" * 50)
    print(">>> DEMO COMPLETE\n")
    print("You can now chat with the agent. Type /help for commands.\n")


def interactive_chat(agent: MemoryEnhancedAgent):
    """Run interactive chat session."""
    print_commands()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]

                if cmd == "/quit" or cmd == "/exit":
                    print("\nGoodbye!")
                    break

                elif cmd == "/help":
                    print_commands()

                elif cmd == "/memory":
                    print("\n" + agent.get_memory_summary())

                elif cmd == "/health":
                    print("\nMemory Health:")
                    health = agent.get_memory_health()
                    for key, value in health.items():
                        if isinstance(value, dict):
                            print(f"  {key}:")
                            for k, v in value.items():
                                print(f"    {k}: {v}")
                        else:
                            print(f"  {key}: {value}")

                elif cmd == "/recall":
                    query = input("  Recall query: ").strip()
                    if query:
                        memories = agent.recall(query, RetrievalIntent.FACTUAL_QA, max_items=5)
                        if memories:
                            print("\n  Recalled memories:")
                            for i, mem in enumerate(memories, 1):
                                print(f"    [{i}] {mem[:80]}...")
                        else:
                            print("  No relevant memories found.")

                elif cmd == "/decisions":
                    decisions = agent.memory.get_decisions()
                    if decisions:
                        print("\n  Recent Decisions:")
                        for d in decisions[-5:]:
                            print(f"    - {d['decision'][:60]}...")
                    else:
                        print("  No decisions recorded yet.")

                elif cmd == "/state":
                    print("\n" + agent.memory.get_state_summary())

                elif cmd == "/clear":
                    agent.clear_history()
                    print("  Conversation history cleared.")

                else:
                    print(f"  Unknown command: {cmd}")
                    print("  Type /help for available commands.")

            else:
                # Regular chat
                print("\nAgent: ", end="", flush=True)
                try:
                    response = agent.chat(user_input)
                    print(response)
                except Exception as e:
                    print(f"\n[Error: {e}]")
                    print("(Make sure OPENAI_API_KEY is set in .env)")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type /quit to exit.")
        except EOFError:
            print("\nGoodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Run Memory-Enhanced Agent")
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Disable memory persistence"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode before interactive chat"
    )
    parser.add_argument(
        "--memory-dir",
        type=str,
        default=".memory_store",
        help="Directory for memory persistence"
    )
    args = parser.parse_args()

    print_header()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set in environment or .env file")
        print("Chat functionality will not work without it.\n")

    # Initialize agent
    persist_dir = None if args.no_persist else args.memory_dir
    print(f"Initializing agent (persist={persist_dir is not None})...")

    agent = MemoryEnhancedAgent(
        enable_memory=True,
        memory_persist_dir=persist_dir
    )

    print(f"Memory system initialized.")
    if persist_dir:
        print(f"Memory will be persisted to: {persist_dir}/")
    print()

    # Run demo if requested
    if args.demo:
        run_demo(agent)

    # Start interactive chat
    interactive_chat(agent)


if __name__ == "__main__":
    main()
