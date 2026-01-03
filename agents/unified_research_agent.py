"""
Unified Research Agent - Combines domain expertise with citation tracking.

This agent merges subject-specific knowledge with the Citation Agent
to provide comprehensive research assistance with:
- Domain-specific expertise (psychology, statistics, biology, etc.)
- Automatic citation tracking and author metrics
- Memory system for context-rot prevention
- Cross-domain research synthesis
"""

import json
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from openai import OpenAI
from duckduckgo_search import DDGS

from .citation_agent import CitationAgent, Paper, Author
from memory import (
    MemoryAgentMixin,
    MemoryCategory,
    RetrievalIntent,
    create_memory_system,
)


class ResearchDomain(Enum):
    """Available research domains."""
    STATISTICS = "statistics"
    PSYCHOLOGY = "psychology"
    BIOLOGY = "biology"
    PHILOSOPHY = "philosophy"
    PSYCHIATRY = "psychiatry"
    ECONOMICS = "economics"
    COMPUTER_SCIENCE = "computer_science"
    GENERAL = "general"


# Domain-specific system prompt additions
DOMAIN_PROMPTS = {
    ResearchDomain.STATISTICS: """
You have deep expertise in statistical methodology including:
- Experimental design, hypothesis testing, power analysis
- Regression, ANOVA, mixed-effects models
- Bayesian statistics and causal inference
- Meta-analysis and effect size interpretation
Key authors: Fisher, Neyman, Pearson, Tukey, Box, Efron, Gelman""",

    ResearchDomain.PSYCHOLOGY: """
You have deep expertise in psychological research including:
- Cognitive psychology, behavioral economics
- Social psychology, consumer behavior
- Research methods in psychology
- Replication crisis and open science
Key authors: Kahneman, Tversky, Cialdini, Baumeister, Dweck, Ariely""",

    ResearchDomain.BIOLOGY: """
You have deep expertise in biological sciences including:
- Molecular biology, genetics, genomics
- Systems biology, bioinformatics
- Experimental methods and statistical genetics
Key authors: Watson, Crick, Venter, Collins, Doudna""",

    ResearchDomain.PHILOSOPHY: """
You have deep expertise in philosophy including:
- Philosophy of science and epistemology
- Ethics and moral philosophy
- Philosophy of mind
Key authors: Popper, Kuhn, Quine, Dennett, Chalmers""",

    ResearchDomain.PSYCHIATRY: """
You have deep expertise in psychiatry including:
- Clinical psychiatry, psychopharmacology
- Diagnostic systems (DSM, ICD)
- Evidence-based treatments
Key authors: Kandel, Insel, Frances, First""",

    ResearchDomain.ECONOMICS: """
You have deep expertise in economics including:
- Behavioral economics, microeconomics
- Econometrics, causal inference
- Market design, game theory
Key authors: Thaler, Shiller, Acemoglu, Duflo, Banerjee""",

    ResearchDomain.COMPUTER_SCIENCE: """
You have deep expertise in computer science including:
- Machine learning, artificial intelligence
- Algorithms, data structures
- Human-computer interaction
Key authors: Hinton, LeCun, Bengio, Ng, Russell""",

    ResearchDomain.GENERAL: """
You are a general research assistant with broad knowledge across disciplines.
You can identify relevant domains and synthesize cross-domain insights.""",
}


class UnifiedResearchAgent(MemoryAgentMixin):
    """
    Unified Research Agent combining domain expertise, citation tracking, and memory.

    Features:
    - Multi-domain research expertise
    - Integrated citation tracking (papers, authors, h-index)
    - Context-rot prevention memory system
    - Automatic extraction and storage of research findings
    - Cross-domain synthesis capabilities
    """

    def __init__(
        self,
        primary_domain: ResearchDomain = ResearchDomain.GENERAL,
        secondary_domains: Optional[List[ResearchDomain]] = None,
        persist_dir: Optional[str] = None,
        enable_memory: bool = True,
    ):
        """
        Initialize the unified research agent.

        Args:
            primary_domain: Main research domain
            secondary_domains: Additional domains for cross-domain research
            persist_dir: Directory for persisting memory and citations
            enable_memory: Whether to enable memory features
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []

        self.primary_domain = primary_domain
        self.secondary_domains = secondary_domains or []

        # Set up persistence
        self._persist_dir = persist_dir or ".research_agent_data"
        os.makedirs(self._persist_dir, exist_ok=True)

        # Initialize citation subagent
        citation_dir = os.path.join(self._persist_dir, "citations")
        self.citation_agent = CitationAgent(persist_dir=citation_dir)

        # Initialize memory system
        if enable_memory:
            memory_dir = os.path.join(self._persist_dir, "memory")
            self.init_memory(persist_dir=memory_dir)

        self.tools = self._get_tools()

    @property
    def name(self) -> str:
        return f"Research Agent ({self.primary_domain.value})"

    @property
    def description(self) -> str:
        domains = [self.primary_domain.value] + [d.value for d in self.secondary_domains]
        return f"Unified research agent for {', '.join(domains)} with citation tracking"

    @property
    def system_prompt(self) -> str:
        # Base prompt
        prompt = """You are a Unified Research Agent with integrated citation tracking.

Your capabilities:
1. Deep domain expertise in your specialized fields
2. Automatic tracking of papers, authors, and citation counts
3. Memory of past research findings and decisions
4. Cross-domain research synthesis

When discussing research:
- Always cite papers with author names and years
- Include citation counts when available
- Track author metrics (h-index, total citations)
- Note relationships between papers and authors
- Store important findings for future reference

"""
        # Add domain-specific prompts
        prompt += "\n=== PRIMARY DOMAIN ===\n"
        prompt += DOMAIN_PROMPTS.get(self.primary_domain, DOMAIN_PROMPTS[ResearchDomain.GENERAL])

        if self.secondary_domains:
            prompt += "\n\n=== SECONDARY DOMAINS ===\n"
            for domain in self.secondary_domains:
                prompt += f"\n{domain.value.upper()}:"
                prompt += DOMAIN_PROMPTS.get(domain, "")[:200]

        # Add citation stats
        stats = self.citation_agent.graph.get_statistics()
        prompt += f"""

=== CITATION DATABASE ===
Papers tracked: {stats.get('total_papers', 0)}
Authors tracked: {stats.get('total_authors', 0)}
Total citations: {stats.get('total_citations', 0)}
"""

        # Add memory context if available
        if self.memory_enabled:
            memory_context = self.get_context_for_llm()
            if memory_context:
                prompt += f"\n{memory_context}"

        return prompt

    def _get_tools(self) -> list:
        """Get available tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_literature",
                    "description": "Search for academic papers and literature on a topic.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "domain": {
                                "type": "string",
                                "description": "Specific domain to search in"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "record_paper",
                    "description": "Record a paper in the citation database with its details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "authors": {"type": "array", "items": {"type": "string"}},
                            "year": {"type": "integer"},
                            "citations": {"type": "integer"},
                            "venue": {"type": "string"},
                            "domain": {"type": "string"},
                            "key_finding": {"type": "string"}
                        },
                        "required": ["title", "authors", "year", "citations"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "lookup_author",
                    "description": "Look up an author's publication record and metrics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "author_name": {"type": "string"}
                        },
                        "required": ["author_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_citation_statistics",
                    "description": "Get overall citation statistics and top papers/authors.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Optional domain to filter by"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recall_research",
                    "description": "Recall previously stored research findings from memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "domain": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "store_finding",
                    "description": "Store an important research finding in memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "finding": {"type": "string"},
                            "source": {"type": "string"},
                            "confidence": {"type": "number"}
                        },
                        "required": ["finding", "source"]
                    }
                }
            }
        ]

    def _search_literature(self, query: str, domain: str = "") -> str:
        """Search for academic literature."""
        search_query = f"academic research {query}"
        if domain:
            search_query += f" {domain}"

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=10))

            if not results:
                return "No results found."

            formatted = []
            for r in results:
                formatted.append(
                    f"Title: {r['title']}\n"
                    f"URL: {r['href']}\n"
                    f"Summary: {r['body']}\n"
                )
            return "\n---\n".join(formatted)
        except Exception as e:
            return f"Search error: {e}"

    def _process_tool_calls(self, tool_calls) -> list:
        """Process tool calls."""
        results = []

        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"  [{self.name}] {func_name}...")

            if func_name == "search_literature":
                result = self._search_literature(
                    args["query"],
                    args.get("domain", self.primary_domain.value)
                )

            elif func_name == "record_paper":
                # Record in citation graph
                paper_result = self.citation_agent.record_paper(
                    title=args["title"],
                    authors=args["authors"],
                    year=args["year"],
                    citations=args["citations"],
                    venue=args.get("venue", ""),
                    domain=args.get("domain", self.primary_domain.value),
                )

                # Also store key finding in memory if provided
                if self.memory_enabled and args.get("key_finding"):
                    self.remember(
                        f"{args['title']} ({args['year']}): {args['key_finding']}",
                        MemoryCategory.FACTUAL,
                        f"paper:{args['authors'][0] if args['authors'] else 'unknown'}:{args['year']}",
                        confidence=0.85,
                    )

                result = paper_result

            elif func_name == "lookup_author":
                author_info = self.citation_agent.get_author_info(args["author_name"])
                result = author_info

            elif func_name == "get_citation_statistics":
                domain = args.get("domain")
                if domain:
                    stats = self.citation_agent.get_domain_statistics(domain)
                else:
                    stats = self.citation_agent.graph.get_statistics()
                result = json.dumps(stats, indent=2)

            elif func_name == "recall_research":
                if self.memory_enabled:
                    memories = self.recall(
                        args["query"],
                        RetrievalIntent.FACTUAL_QA,
                        max_items=5
                    )
                    if memories:
                        result = "Recalled findings:\n" + "\n".join(f"- {m}" for m in memories)
                    else:
                        result = "No relevant findings in memory."
                else:
                    result = "Memory system not enabled."

            elif func_name == "store_finding":
                if self.memory_enabled:
                    success = self.remember(
                        args["finding"],
                        MemoryCategory.FACTUAL,
                        args["source"],
                        confidence=args.get("confidence", 0.8),
                    )
                    result = "Finding stored in memory." if success else "Failed to store finding."
                else:
                    result = "Memory system not enabled."

            else:
                result = f"Unknown tool: {func_name}"

            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "content": result
            })

        return results

    def chat(self, user_message: str) -> str:
        """Process a chat message."""
        # Pre-chat hook for memory
        self.on_chat_start(user_message)

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

                # Post-chat hook
                self.on_chat_end(message.content)

                # Extract and record any papers mentioned
                self._extract_papers_from_response(message.content)

                return message.content

    def _extract_papers_from_response(self, response: str) -> None:
        """Extract paper references from response and offer to record them."""
        # Simple heuristic: look for patterns like "Author (Year)"
        import re
        pattern = r'([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+))?)\s*\((\d{4})\)'
        matches = re.findall(pattern, response)

        for author, year in matches[:3]:  # Limit to avoid noise
            # Record in episodic trace for potential later extraction
            if self.memory_enabled:
                self.memory.record_event(
                    "paper_reference",
                    f"Referenced: {author} ({year})",
                    {"author": author, "year": year}
                )

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        if self.memory_enabled:
            self.memory.clear_working_context()

    def get_research_summary(self) -> str:
        """Get a summary of research findings and citations."""
        lines = [
            f"=== {self.name} Research Summary ===",
            "",
            "--- Citation Database ---",
        ]

        stats = self.citation_agent.graph.get_statistics()
        lines.append(f"Papers: {stats.get('total_papers', 0)}")
        lines.append(f"Authors: {stats.get('total_authors', 0)}")
        lines.append(f"Total Citations: {stats.get('total_citations', 0)}")

        if stats.get('top_cited_papers'):
            lines.append("\nTop Cited Papers:")
            for p in stats['top_cited_papers'][:3]:
                lines.append(f"  - {p['title'][:50]}... ({p['citations']} citations)")

        if stats.get('top_authors'):
            lines.append("\nTop Authors:")
            for a in stats['top_authors'][:3]:
                lines.append(f"  - {a['name']} (h-index: {a['h_index']})")

        if self.memory_enabled:
            lines.append("\n--- Memory Status ---")
            lines.append(self.memory.get_state_summary())

        return "\n".join(lines)


# Factory functions for common configurations

def create_psychology_research_agent(persist_dir: Optional[str] = None) -> UnifiedResearchAgent:
    """Create a psychology-focused research agent."""
    return UnifiedResearchAgent(
        primary_domain=ResearchDomain.PSYCHOLOGY,
        secondary_domains=[ResearchDomain.STATISTICS, ResearchDomain.ECONOMICS],
        persist_dir=persist_dir,
    )


def create_statistics_research_agent(persist_dir: Optional[str] = None) -> UnifiedResearchAgent:
    """Create a statistics-focused research agent."""
    return UnifiedResearchAgent(
        primary_domain=ResearchDomain.STATISTICS,
        secondary_domains=[ResearchDomain.PSYCHOLOGY, ResearchDomain.BIOLOGY],
        persist_dir=persist_dir,
    )


def create_interdisciplinary_agent(
    domains: List[ResearchDomain],
    persist_dir: Optional[str] = None
) -> UnifiedResearchAgent:
    """Create an interdisciplinary research agent."""
    return UnifiedResearchAgent(
        primary_domain=domains[0] if domains else ResearchDomain.GENERAL,
        secondary_domains=domains[1:] if len(domains) > 1 else [],
        persist_dir=persist_dir,
    )
