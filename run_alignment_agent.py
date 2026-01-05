#!/usr/bin/env python3
"""
Run the Alignment Agent - Examples of simplest LLM alignment procedures.

This script demonstrates:
1. Best-of-N sampling (no training required)
2. Generating preference data for DPO
3. Generating SFT training data
4. Using the AlignmentAgent for research queries

Usage:
    python run_alignment_agent.py
    python run_alignment_agent.py --mode interactive
    python run_alignment_agent.py --mode generate-data

Requirements:
    export OPENAI_API_KEY=your-api-key
"""

import os
import argparse
from agents import (
    AlignmentAgent,
    SimpleAlignmentPipeline,
    quick_align_response,
    generate_preference_dataset,
    generate_sft_dataset,
    dpo_loss_reference,
)


def demo_best_of_n():
    """Demonstrate best-of-n sampling - the simplest alignment method."""
    print("\n" + "="*60)
    print("DEMO: Best-of-N Sampling (Simplest Alignment)")
    print("="*60)

    pipeline = SimpleAlignmentPipeline()

    prompt = "Explain what machine learning is to a 10-year-old."

    print(f"\nPrompt: {prompt}")
    print("\nGenerating 4 responses and selecting the best...")

    best_response, all_responses = pipeline.best_of_n_sampling(prompt, n=4)

    print(f"\nGenerated {len(all_responses)} responses")
    print("\n--- Best Response ---")
    print(best_response)


def demo_preference_generation():
    """Demonstrate preference data generation for DPO."""
    print("\n" + "="*60)
    print("DEMO: Preference Data Generation (for DPO)")
    print("="*60)

    pipeline = SimpleAlignmentPipeline()

    prompt = "What are the benefits of exercise?"

    print(f"\nPrompt: {prompt}")
    print("\nGenerating preference pair using constitutional approach...")

    pair = pipeline.generate_preference_pair(prompt)

    print("\n--- CHOSEN (Improved) Response ---")
    print(pair.chosen[:500] + "..." if len(pair.chosen) > 500 else pair.chosen)

    print("\n--- REJECTED (Original) Response ---")
    print(pair.rejected[:500] + "..." if len(pair.rejected) > 500 else pair.rejected)


def demo_sft_data():
    """Demonstrate SFT data generation."""
    print("\n" + "="*60)
    print("DEMO: SFT Dataset Generation")
    print("="*60)

    prompts = [
        "What is photosynthesis?",
        "How does gravity work?",
    ]

    print(f"\nGenerating SFT data for {len(prompts)} prompts...")
    print("(Using best-of-3 to get high-quality responses)")

    pipeline = SimpleAlignmentPipeline()
    dataset = pipeline.create_sft_dataset(prompts)

    for i, item in enumerate(dataset):
        print(f"\n--- Example {i+1} ---")
        print(f"Instruction: {item['instruction']}")
        print(f"Output: {item['output'][:300]}...")


def demo_dpo_loss():
    """Show the DPO loss implementation."""
    print("\n" + "="*60)
    print("DEMO: DPO Loss Implementation (Reference)")
    print("="*60)

    print("\nThe DPO loss equation:")
    print("L_DPO = -log(sigmoid(beta * (log(pi(y_w|x)/pi_ref(y_w|x)) - log(pi(y_l|x)/pi_ref(y_l|x)))))")

    print("\nPyTorch implementation:")
    print(dpo_loss_reference())


def interactive_mode():
    """Run the alignment agent interactively."""
    print("\n" + "="*60)
    print("ALIGNMENT AGENT - Interactive Mode")
    print("="*60)
    print("\nAsk about alignment methods: DPO, SFT, RLHF, Constitutional AI")
    print("Commands: 'explain dpo', 'explain sft', 'quit'\n")

    agent = AlignmentAgent()

    while True:
        try:
            query = input("\nYou: ").strip()

            if not query:
                continue

            if query.lower() == 'quit':
                print("Goodbye!")
                break

            if query.lower() == 'explain dpo':
                print("\nAlignment Agent: ", end="")
                print(agent.explain_dpo())
                continue

            if query.lower() == 'explain sft':
                print("\nAlignment Agent: ", end="")
                print(agent.explain_sft())
                continue

            response = agent.chat(query)
            print(f"\nAlignment Agent: {response}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


def generate_data_mode():
    """Generate alignment datasets."""
    print("\n" + "="*60)
    print("ALIGNMENT DATA GENERATION")
    print("="*60)

    # Example prompts for generating alignment data
    sample_prompts = [
        "What is the meaning of life?",
        "How can I be more productive?",
        "Explain quantum computing simply.",
        "What makes a good leader?",
        "How does the immune system work?",
    ]

    print(f"\nGenerating alignment data for {len(sample_prompts)} prompts...")

    # Generate DPO preference data
    print("\n1. Generating DPO preference data...")
    dpo_dataset = generate_preference_dataset(
        sample_prompts,
        output_file="alignment_data/dpo_preferences.json",
        method="constitutional"
    )

    # Generate SFT data
    print("\n2. Generating SFT data...")
    sft_dataset = generate_sft_dataset(
        sample_prompts,
        output_file="alignment_data/sft_data.json"
    )

    print("\n" + "="*60)
    print("DATA GENERATION COMPLETE")
    print("="*60)
    print(f"\nDPO data: alignment_data/dpo_preferences.json ({len(dpo_dataset.pairs)} pairs)")
    print(f"SFT data: alignment_data/sft_data.json ({len(sft_dataset)} examples)")


def main():
    parser = argparse.ArgumentParser(description="LLM Alignment Agent Demo")
    parser.add_argument(
        "--mode",
        choices=["demo", "interactive", "generate-data"],
        default="demo",
        help="Mode to run (default: demo)"
    )
    args = parser.parse_args()

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY=your-api-key")
        return

    if args.mode == "demo":
        print("\n" + "#"*60)
        print("# SIMPLEST LLM ALIGNMENT PROCEDURES")
        print("#"*60)

        # Run demos
        demo_best_of_n()
        demo_preference_generation()
        demo_sft_data()
        demo_dpo_loss()

        print("\n" + "#"*60)
        print("# SUMMARY: Simplest Alignment Methods")
        print("#"*60)
        print("""
1. Best-of-N Sampling (SIMPLEST - No training!)
   - Generate N responses, pick the best
   - Use LLM-as-judge or reward model to score
   - Works at inference time

2. SFT (Supervised Fine-Tuning)
   - Fine-tune on (instruction, response) pairs
   - Need high-quality demonstrations
   - Foundation for other methods

3. DPO (Direct Preference Optimization)
   - Train on (prompt, chosen, rejected) triplets
   - No reward model needed
   - Single training stage
   - Simpler than RLHF

4. Constitutional AI
   - Generate -> Critique -> Revise
   - Self-improvement using principles
   - Can auto-generate preference data
""")

    elif args.mode == "interactive":
        interactive_mode()

    elif args.mode == "generate-data":
        os.makedirs("alignment_data", exist_ok=True)
        generate_data_mode()


if __name__ == "__main__":
    main()
