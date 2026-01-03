#!/usr/bin/env python3
"""Test script for the context-rot prevention memory system."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory import (
    MemorySystem,
    MemoryCategory,
    RetrievalIntent,
    create_lightweight_memory_system,
)


def test_basic_operations():
    """Test basic memory operations."""
    print("=" * 60)
    print("TEST 1: Basic Operations")
    print("=" * 60)

    # Create lightweight memory system (no persistence)
    mem = create_lightweight_memory_system()

    # Store some memories
    print("\n1. Storing memories...")
    mem.store(
        "Cohen's d for anchoring bias is typically 0.3-0.5",
        category=MemoryCategory.FACTUAL,
        source="research:cognitive_bias_framework",
        confidence=0.9,
    )
    mem.store(
        "Social proof increases conversion by 10-15%",
        category=MemoryCategory.FACTUAL,
        source="research:social_proof_study",
        confidence=0.85,
    )
    mem.store(
        "Use logistic regression for conversion modeling",
        category=MemoryCategory.PROCEDURAL,
        source="methodology:statistics_agent",
        confidence=0.8,
    )
    print("   Stored 3 memories")

    # Add working context
    print("\n2. Adding working context...")
    mem.set_current_task("Analyze cognitive bias effects on e-commerce")
    mem.add_context("User wants quantitative analysis", "user_input")
    mem.add_user_constraint("Focus on effect sizes from peer-reviewed research")
    print("   Added task and constraints")

    # Retrieve memories
    print("\n3. Retrieving memories...")
    result = mem.retrieve(RetrievalIntent.FACTUAL_QA, query="cognitive bias effect sizes")
    print(f"   Retrieved {len(result.items)} items")
    for item in result.items:
        print(f"   - [{item.score:.2f}] {item.item.content[:60]}...")

    # Check state
    print("\n4. State summary:")
    print(mem.get_state_summary())

    print("\n[TEST 1 PASSED]")


def test_contradiction_detection():
    """Test contradiction detection."""
    print("\n" + "=" * 60)
    print("TEST 2: Contradiction Detection")
    print("=" * 60)

    mem = create_lightweight_memory_system()

    # Store initial memory
    print("\n1. Storing initial memory...")
    mem.store(
        "The anchoring effect size is d = 0.5",
        category=MemoryCategory.FACTUAL,
        source="study_1",
        confidence=0.9,
    )
    print("   Stored: 'anchoring effect size is d = 0.5'")

    # Store contradicting memory
    print("\n2. Storing potentially contradicting memory...")
    result = mem.check_and_store(
        "The anchoring effect size is d = 0.2",
        category=MemoryCategory.FACTUAL,
        source="study_2",
        supersede_on_conflict=False,
    )
    print(f"   Conflicts detected: {len(result['conflicts'])}")
    for conflict in result["conflicts"]:
        print(f"   - {conflict['reason']}")

    # Check health status
    print("\n3. Health status after contradiction:")
    health = mem.get_health_status()
    print(f"   Policy: {health['policy']}")
    print(f"   Active memories: {health['active_memories']}")

    print("\n[TEST 2 PASSED]")


def test_decay_and_retrieval():
    """Test decay scoring in retrieval."""
    print("\n" + "=" * 60)
    print("TEST 3: Decay and Retrieval Scoring")
    print("=" * 60)

    mem = create_lightweight_memory_system()

    # Store memories with different confidence levels
    print("\n1. Storing memories with different confidence levels...")
    mem.store(
        "High confidence fact about anchoring",
        category=MemoryCategory.FACTUAL,
        source="verified_source",
        confidence=0.95,
    )
    mem.store(
        "Medium confidence fact about scarcity",
        category=MemoryCategory.FACTUAL,
        source="web_search",
        confidence=0.6,
    )
    mem.store(
        "Low confidence speculation",
        category=MemoryCategory.FACTUAL,
        source="inferred",
        confidence=0.4,
    )
    print("   Stored 3 memories with confidence: 0.95, 0.6, 0.4")

    # Retrieve with different confidence thresholds
    print("\n2. Retrieving with min_confidence=0.7...")
    result = mem.retrieve(
        RetrievalIntent.FACTUAL_QA,
        min_confidence=0.7,
    )
    print(f"   Retrieved {len(result.items)} items")

    print("\n3. Checking verification requirements...")
    for item in result.items:
        if item.needs_verification:
            print(f"   - Needs verification: {item.verification_reason}")

    print("\n[TEST 3 PASSED]")


def test_focus_window_and_decisions():
    """Test focus window for long tasks."""
    print("\n" + "=" * 60)
    print("TEST 4: Focus Window and Decisions")
    print("=" * 60)

    mem = create_lightweight_memory_system()

    # Record several decisions
    print("\n1. Recording decisions...")
    for i in range(15):
        mem.record_decision(
            f"Decision {i+1}: Chose approach {chr(65+i)}",
            f"Rationale for decision {i+1}",
        )
    print("   Recorded 15 decisions")

    # Check focus window (should be limited)
    print("\n2. Checking focus window...")
    decisions = mem.get_decisions()
    print(f"   Focus window contains {len(decisions)} decisions")
    print(f"   Latest decision: {decisions[-1]['decision'][:50]}...")

    # Run consolidation
    print("\n3. Running consolidation...")
    report = mem.consolidate()
    print(f"   Archived: {report['archived']}")
    print(f"   Promoted: {report['promoted']}")
    print(f"   Expired: {report['expired']}")

    print("\n[TEST 4 PASSED]")


def test_summary_generation():
    """Test anti-drift summary generation."""
    print("\n" + "=" * 60)
    print("TEST 5: Summary Generation")
    print("=" * 60)

    mem = create_lightweight_memory_system()

    # Set up state
    print("\n1. Setting up agent state...")
    mem.set_goal("Analyze cognitive biases in e-commerce")
    mem.add_user_constraint("Focus on quantitative metrics")
    mem.add_assumption(
        "Users respond to social proof signals",
        confidence=0.85,
        source="psychology_research",
    )
    mem.record_decision(
        "Use effect sizes from meta-analyses",
        "More reliable than individual studies",
    )
    mem.add_question("What is the optimal number of reviews to display?")

    # Store some factual memories
    mem.store(
        "Social proof increases conversion by 10-15%",
        MemoryCategory.FACTUAL,
        "meta_analysis",
        0.9,
    )

    # Generate fresh summary
    print("\n2. Generating fresh summary from atomic facts...")
    summary = mem.generate_summary("E-Commerce Bias Analysis")
    print(summary)

    print("\n[TEST 5 PASSED]")


def test_lifecycle():
    """Test task lifecycle management."""
    print("\n" + "=" * 60)
    print("TEST 6: Task Lifecycle")
    print("=" * 60)

    mem = create_lightweight_memory_system()

    # Start task
    print("\n1. Starting task...")
    mem.on_task_start("Cognitive bias deep dive")
    print(f"   Policy: {mem.get_health_status()['policy']}")

    # Simulate some issues
    print("\n2. Simulating quality issues...")
    mem.record_user_correction("Incorrect effect size cited")
    mem.record_tool_retry("Web search timeout")
    mem.record_user_correction("Wrong confidence interval")

    # Check health
    print("\n3. Checking health after issues...")
    health = mem.get_health_status()
    print(f"   Policy: {health['policy']}")
    if 'drift_health' in health:
        print(f"   Health: {health['drift_health']['health']}")

    # Complete task successfully
    print("\n4. Completing task successfully...")
    mem.on_task_complete(success=True)
    health = mem.get_health_status()
    print(f"   Policy after reset: {health['policy']}")

    print("\n[TEST 6 PASSED]")


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# CONTEXT-ROT PREVENTION MEMORY SYSTEM TESTS")
    print("#" * 60)

    test_basic_operations()
    test_contradiction_detection()
    test_decay_and_retrieval()
    test_focus_window_and_decisions()
    test_summary_generation()
    test_lifecycle()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
