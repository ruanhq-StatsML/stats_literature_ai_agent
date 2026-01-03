#!/usr/bin/env python3
"""
Run the Citation-Enabled Research Agent locally.

This script provides an interactive research assistant with:
- Domain-specific expertise
- Automatic citation tracking
- Author metrics and h-index
- Memory for context-rot prevention

Usage:
    python run_citation_agent.py                    # General research agent
    python run_citation_agent.py --domain psychology # Psychology-focused
    python run_citation_agent.py --domain statistics # Statistics-focused
    python run_citation_agent.py --demo             # Run demo mode
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from agents import (
    UnifiedResearchAgent,
    ResearchDomain,
    CitationAgent,
    create_psychology_research_agent,
    create_statistics_research_agent,
)
from memory import MemoryCategory


def print_header(agent: UnifiedResearchAgent):
    """Print welcome header."""
    print()
    print("=" * 70)
    print(f"  {agent.name.upper()}")
    print("  With Citation Tracking & Memory System")
    print("=" * 70)
    print()
    print(f"Primary Domain: {agent.primary_domain.value}")
    if agent.secondary_domains:
        print(f"Secondary Domains: {', '.join(d.value for d in agent.secondary_domains)}")
    print()


def print_commands():
    """Print available commands."""
    print("Commands:")
    print("  /stats      - Show citation statistics")
    print("  /authors    - List tracked authors with h-index")
    print("  /papers     - List tracked papers by citations")
    print("  /search     - Search citation database")
    print("  /memory     - Show memory summary")
    print("  /health     - Show system health")
    print("  /summary    - Full research summary")
    print("  /clear      - Clear conversation history")
    print("  /help       - Show this help")
    print("  /quit       - Exit")
    print()


def run_demo(agent: UnifiedResearchAgent):
    """Run a demonstration of citation tracking features."""
    print("\n>>> DEMO MODE: Citation Tracking Features\n")
    print("-" * 60)

    # 1. Record some foundational papers
    print("\n1. Recording foundational papers...")

    papers = [
        {
            "title": "Prospect Theory: An Analysis of Decision under Risk",
            "authors": ["Daniel Kahneman", "Amos Tversky"],
            "year": 1979,
            "citations": 65000,
            "venue": "Econometrica",
            "domain": "psychology",
        },
        {
            "title": "Judgment under Uncertainty: Heuristics and Biases",
            "authors": ["Amos Tversky", "Daniel Kahneman"],
            "year": 1974,
            "citations": 45000,
            "venue": "Science",
            "domain": "psychology",
        },
        {
            "title": "Influence: The Psychology of Persuasion",
            "authors": ["Robert Cialdini"],
            "year": 1984,
            "citations": 25000,
            "venue": "Book",
            "domain": "psychology",
        },
        {
            "title": "Thinking, Fast and Slow",
            "authors": ["Daniel Kahneman"],
            "year": 2011,
            "citations": 35000,
            "venue": "Book",
            "domain": "psychology",
        },
        {
            "title": "Predictably Irrational",
            "authors": ["Dan Ariely"],
            "year": 2008,
            "citations": 8000,
            "venue": "Book",
            "domain": "psychology",
        },
        {
            "title": "Statistical Power Analysis for the Behavioral Sciences",
            "authors": ["Jacob Cohen"],
            "year": 1988,
            "citations": 120000,
            "venue": "Book",
            "domain": "statistics",
        },
        {
            "title": "The Design of Experiments",
            "authors": ["Ronald Fisher"],
            "year": 1935,
            "citations": 30000,
            "venue": "Book",
            "domain": "statistics",
        },
    ]

    for p in papers:
        agent.citation_agent.record_paper(**p)
        print(f"   Recorded: {p['title'][:50]}... ({p['citations']:,} citations)")

    # 2. Show author statistics
    print("\n2. Author Statistics:")
    print("-" * 40)

    top_authors = ["Daniel Kahneman", "Amos Tversky", "Robert Cialdini", "Jacob Cohen"]
    for author_name in top_authors:
        author = agent.citation_agent.graph.get_author(author_name)
        if author:
            print(f"   {author.name}")
            print(f"      Papers: {len(author.papers)}")
            print(f"      H-index: {author.h_index}")
            print(f"      Total citations: {author.total_citations:,}")
            print(f"      Collaborators: {len(author.collaborators)}")
            print()

    # 3. Show collaboration network
    print("3. Collaboration Network (Kahneman):")
    print("-" * 40)
    network = agent.citation_agent.graph.get_collaboration_network("Daniel Kahneman")
    if network.get("collaborators"):
        for collab in network["collaborators"]:
            print(f"   - {collab['name']} (h-index: {collab['h_index']})")

    # 4. Show domain statistics
    print("\n4. Domain Statistics:")
    print("-" * 40)
    for domain in ["psychology", "statistics"]:
        stats = agent.citation_agent.get_domain_statistics(domain)
        print(f"   {domain.upper()}")
        print(f"      Papers: {stats.get('papers', 0)}")
        print(f"      Total citations: {stats.get('total_citations', 0):,}")
        print(f"      Avg citations: {stats.get('avg_citations', 0):,.0f}")
        print()

    # 5. Store findings in memory
    print("5. Storing key findings in memory...")
    if agent.memory_enabled:
        agent.remember(
            "Kahneman & Tversky's Prospect Theory shows loss aversion coefficient ~2.0-2.5",
            category=MemoryCategory.FACTUAL,
            source="paper:kahneman:1979",
            confidence=0.95,
        )
        agent.remember(
            "Cialdini's 6 principles of persuasion: reciprocity, commitment, social proof, authority, liking, scarcity",
            category=MemoryCategory.FACTUAL,
            source="paper:cialdini:1984",
            confidence=0.9,
        )
        print("   Stored 2 key findings")

    # 6. Show overall summary
    print("\n6. Research Summary:")
    print("-" * 40)
    print(agent.get_research_summary())

    print("\n" + "-" * 60)
    print(">>> DEMO COMPLETE\n")
    print("You can now chat with the agent. Type /help for commands.\n")


def show_citation_stats(agent: UnifiedResearchAgent):
    """Show citation statistics."""
    stats = agent.citation_agent.graph.get_statistics()
    print("\n=== Citation Statistics ===")
    print(f"Total Papers: {stats.get('total_papers', 0)}")
    print(f"Total Authors: {stats.get('total_authors', 0)}")
    print(f"Total Citations: {stats.get('total_citations', 0):,}")
    print(f"Avg Citations: {stats.get('avg_citations', 0):,.1f}")

    if stats.get('papers_by_domain'):
        print("\nBy Domain:")
        for domain, count in stats['papers_by_domain'].items():
            print(f"  {domain}: {count} papers")


def show_authors(agent: UnifiedResearchAgent):
    """Show tracked authors."""
    stats = agent.citation_agent.graph.get_statistics()
    print("\n=== Top Authors by H-Index ===")
    for author in stats.get('top_authors', []):
        print(f"  {author['name']}: h-index={author['h_index']}, citations={author['citations']:,}")


def show_papers(agent: UnifiedResearchAgent):
    """Show tracked papers."""
    stats = agent.citation_agent.graph.get_statistics()
    print("\n=== Top Cited Papers ===")
    for paper in stats.get('top_cited_papers', []):
        authors_str = ", ".join(paper['authors'][:2])
        if len(paper['authors']) > 2:
            authors_str += " et al."
        print(f"  [{paper['citations']:,}] {paper['title'][:50]}...")
        print(f"          by {authors_str}")


def search_database(agent: UnifiedResearchAgent):
    """Search the citation database."""
    query = input("  Search query: ").strip()
    if not query:
        return

    papers = agent.citation_agent.graph.search_papers(query=query)
    if papers:
        print(f"\n  Found {len(papers)} papers:")
        for p in papers[:5]:
            print(f"    - {p.title[:50]}... ({p.citation_count:,} citations)")
    else:
        print("  No papers found matching query.")


def interactive_chat(agent: UnifiedResearchAgent):
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

                elif cmd == "/stats":
                    show_citation_stats(agent)

                elif cmd == "/authors":
                    show_authors(agent)

                elif cmd == "/papers":
                    show_papers(agent)

                elif cmd == "/search":
                    search_database(agent)

                elif cmd == "/memory":
                    if agent.memory_enabled:
                        print("\n" + agent.get_memory_summary())
                    else:
                        print("  Memory not enabled.")

                elif cmd == "/health":
                    print("\nSystem Health:")
                    health = agent.get_memory_health()
                    for key, value in health.items():
                        if isinstance(value, dict):
                            print(f"  {key}:")
                            for k, v in value.items():
                                print(f"    {k}: {v}")
                        else:
                            print(f"  {key}: {value}")

                elif cmd == "/summary":
                    print("\n" + agent.get_research_summary())

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
    parser = argparse.ArgumentParser(description="Run Citation-Enabled Research Agent")
    parser.add_argument(
        "--domain",
        type=str,
        default="general",
        choices=["general", "psychology", "statistics", "biology", "philosophy", "psychiatry"],
        help="Primary research domain"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode before interactive chat"
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default=".research_agent_data",
        help="Directory for persistence"
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memory system"
    )
    args = parser.parse_args()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set in environment or .env file")
        print("Chat functionality will not work without it.\n")

    # Map domain string to enum
    domain_map = {
        "general": ResearchDomain.GENERAL,
        "psychology": ResearchDomain.PSYCHOLOGY,
        "statistics": ResearchDomain.STATISTICS,
        "biology": ResearchDomain.BIOLOGY,
        "philosophy": ResearchDomain.PHILOSOPHY,
        "psychiatry": ResearchDomain.PSYCHIATRY,
    }

    primary_domain = domain_map.get(args.domain, ResearchDomain.GENERAL)

    # Create agent
    print("Initializing research agent...")

    if args.domain == "psychology":
        agent = create_psychology_research_agent(persist_dir=args.persist_dir)
    elif args.domain == "statistics":
        agent = create_statistics_research_agent(persist_dir=args.persist_dir)
    else:
        agent = UnifiedResearchAgent(
            primary_domain=primary_domain,
            persist_dir=args.persist_dir,
            enable_memory=not args.no_memory,
        )

    print_header(agent)

    # Run demo if requested
    if args.demo:
        run_demo(agent)

    # Start interactive chat
    interactive_chat(agent)


if __name__ == "__main__":
    main()
