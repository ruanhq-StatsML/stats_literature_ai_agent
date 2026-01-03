"""
Citation Agent - Tracks papers, authors, and citation relationships.

This agent serves as a subagent for domain-specific agents, providing:
- Paper and author tracking with citation counts
- Citation graph/network analysis
- Author collaboration networks
- Citation statistics and metrics (h-index, impact)
- Cross-domain citation patterns
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

from openai import OpenAI
from duckduckgo_search import DDGS


@dataclass
class Author:
    """Represents an author with their publication record."""
    name: str
    author_id: str = ""
    affiliations: List[str] = field(default_factory=list)
    papers: List[str] = field(default_factory=list)  # Paper IDs
    total_citations: int = 0
    h_index: int = 0
    domains: Set[str] = field(default_factory=set)
    collaborators: Set[str] = field(default_factory=set)  # Author names

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "author_id": self.author_id,
            "affiliations": self.affiliations,
            "papers": self.papers,
            "total_citations": self.total_citations,
            "h_index": self.h_index,
            "domains": list(self.domains),
            "collaborators": list(self.collaborators),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Author":
        return cls(
            name=data["name"],
            author_id=data.get("author_id", ""),
            affiliations=data.get("affiliations", []),
            papers=data.get("papers", []),
            total_citations=data.get("total_citations", 0),
            h_index=data.get("h_index", 0),
            domains=set(data.get("domains", [])),
            collaborators=set(data.get("collaborators", [])),
        )


@dataclass
class Paper:
    """Represents a research paper with citation information."""
    title: str
    paper_id: str
    authors: List[str] = field(default_factory=list)
    year: int = 0
    venue: str = ""  # Journal/Conference
    abstract: str = ""
    doi: str = ""
    url: str = ""
    citation_count: int = 0
    references: List[str] = field(default_factory=list)  # Paper IDs this cites
    cited_by: List[str] = field(default_factory=list)    # Paper IDs that cite this
    domains: Set[str] = field(default_factory=set)
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "paper_id": self.paper_id,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "abstract": self.abstract,
            "doi": self.doi,
            "url": self.url,
            "citation_count": self.citation_count,
            "references": self.references,
            "cited_by": self.cited_by,
            "domains": list(self.domains),
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Paper":
        return cls(
            title=data["title"],
            paper_id=data["paper_id"],
            authors=data.get("authors", []),
            year=data.get("year", 0),
            venue=data.get("venue", ""),
            abstract=data.get("abstract", ""),
            doi=data.get("doi", ""),
            url=data.get("url", ""),
            citation_count=data.get("citation_count", 0),
            references=data.get("references", []),
            cited_by=data.get("cited_by", []),
            domains=set(data.get("domains", [])),
            keywords=data.get("keywords", []),
        )


class CitationGraph:
    """
    Citation graph for tracking paper and author relationships.

    Provides:
    - Paper-to-paper citation links
    - Author collaboration networks
    - Citation statistics
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.papers: Dict[str, Paper] = {}
        self.authors: Dict[str, Author] = {}
        self._persist_path = persist_path

        if persist_path and os.path.exists(persist_path):
            self._load()

    def add_paper(self, paper: Paper) -> str:
        """Add a paper to the graph."""
        self.papers[paper.paper_id] = paper

        # Update author records
        for author_name in paper.authors:
            if author_name not in self.authors:
                self.authors[author_name] = Author(name=author_name)

            author = self.authors[author_name]
            if paper.paper_id not in author.papers:
                author.papers.append(paper.paper_id)
            author.domains.update(paper.domains)

            # Track collaborators
            for coauthor in paper.authors:
                if coauthor != author_name:
                    author.collaborators.add(coauthor)

        self._persist()
        return paper.paper_id

    def add_citation(self, citing_paper_id: str, cited_paper_id: str) -> bool:
        """Add a citation link between two papers."""
        if citing_paper_id not in self.papers or cited_paper_id not in self.papers:
            return False

        citing = self.papers[citing_paper_id]
        cited = self.papers[cited_paper_id]

        if cited_paper_id not in citing.references:
            citing.references.append(cited_paper_id)
        if citing_paper_id not in cited.cited_by:
            cited.cited_by.append(citing_paper_id)
            cited.citation_count = len(cited.cited_by)

        # Update author citation counts
        for author_name in cited.authors:
            if author_name in self.authors:
                self._recalculate_author_stats(author_name)

        self._persist()
        return True

    def _recalculate_author_stats(self, author_name: str) -> None:
        """Recalculate citation statistics for an author."""
        if author_name not in self.authors:
            return

        author = self.authors[author_name]
        citation_counts = []

        for paper_id in author.papers:
            if paper_id in self.papers:
                citation_counts.append(self.papers[paper_id].citation_count)

        author.total_citations = sum(citation_counts)

        # Calculate h-index
        citation_counts.sort(reverse=True)
        h = 0
        for i, count in enumerate(citation_counts):
            if count >= i + 1:
                h = i + 1
            else:
                break
        author.h_index = h

    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Get a paper by ID."""
        return self.papers.get(paper_id)

    def get_author(self, name: str) -> Optional[Author]:
        """Get an author by name."""
        return self.authors.get(name)

    def search_papers(
        self,
        query: str = "",
        author: str = "",
        domain: str = "",
        min_citations: int = 0,
        year_range: Optional[Tuple[int, int]] = None,
    ) -> List[Paper]:
        """Search papers with filters."""
        results = []
        query_lower = query.lower()

        for paper in self.papers.values():
            # Filter by query
            if query and query_lower not in paper.title.lower():
                if query_lower not in paper.abstract.lower():
                    continue

            # Filter by author
            if author:
                author_lower = author.lower()
                if not any(author_lower in a.lower() for a in paper.authors):
                    continue

            # Filter by domain
            if domain and domain.lower() not in [d.lower() for d in paper.domains]:
                continue

            # Filter by citations
            if paper.citation_count < min_citations:
                continue

            # Filter by year
            if year_range:
                if paper.year < year_range[0] or paper.year > year_range[1]:
                    continue

            results.append(paper)

        # Sort by citation count
        results.sort(key=lambda p: p.citation_count, reverse=True)
        return results

    def get_citation_network(self, paper_id: str, depth: int = 1) -> Dict[str, Any]:
        """Get citation network around a paper."""
        if paper_id not in self.papers:
            return {}

        paper = self.papers[paper_id]
        network = {
            "center": paper.to_dict(),
            "cites": [],
            "cited_by": [],
        }

        # Get papers this cites
        for ref_id in paper.references[:10]:
            if ref_id in self.papers:
                network["cites"].append(self.papers[ref_id].to_dict())

        # Get papers that cite this
        for citing_id in paper.cited_by[:10]:
            if citing_id in self.papers:
                network["cited_by"].append(self.papers[citing_id].to_dict())

        return network

    def get_collaboration_network(self, author_name: str) -> Dict[str, Any]:
        """Get collaboration network for an author."""
        if author_name not in self.authors:
            return {}

        author = self.authors[author_name]
        network = {
            "author": author.to_dict(),
            "collaborators": [],
            "shared_papers": {},
        }

        for collab_name in list(author.collaborators)[:20]:
            if collab_name in self.authors:
                collab = self.authors[collab_name]
                network["collaborators"].append({
                    "name": collab.name,
                    "h_index": collab.h_index,
                    "total_citations": collab.total_citations,
                })

                # Find shared papers
                shared = set(author.papers) & set(collab.papers)
                if shared:
                    network["shared_papers"][collab_name] = len(shared)

        return network

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall citation statistics."""
        if not self.papers:
            return {"total_papers": 0, "total_authors": 0}

        citation_counts = [p.citation_count for p in self.papers.values()]

        return {
            "total_papers": len(self.papers),
            "total_authors": len(self.authors),
            "total_citations": sum(citation_counts),
            "avg_citations": sum(citation_counts) / len(citation_counts) if citation_counts else 0,
            "max_citations": max(citation_counts) if citation_counts else 0,
            "papers_by_domain": self._count_by_domain(),
            "top_cited_papers": self._get_top_cited(5),
            "top_authors": self._get_top_authors(5),
        }

    def _count_by_domain(self) -> Dict[str, int]:
        """Count papers by domain."""
        counts = defaultdict(int)
        for paper in self.papers.values():
            for domain in paper.domains:
                counts[domain] += 1
        return dict(counts)

    def _get_top_cited(self, n: int) -> List[Dict]:
        """Get top N cited papers."""
        sorted_papers = sorted(
            self.papers.values(),
            key=lambda p: p.citation_count,
            reverse=True
        )
        return [
            {"title": p.title, "citations": p.citation_count, "authors": p.authors[:3]}
            for p in sorted_papers[:n]
        ]

    def _get_top_authors(self, n: int) -> List[Dict]:
        """Get top N authors by h-index."""
        sorted_authors = sorted(
            self.authors.values(),
            key=lambda a: (a.h_index, a.total_citations),
            reverse=True
        )
        return [
            {"name": a.name, "h_index": a.h_index, "citations": a.total_citations}
            for a in sorted_authors[:n]
        ]

    def _persist(self) -> None:
        """Persist to disk."""
        if self._persist_path:
            data = {
                "papers": {k: v.to_dict() for k, v in self.papers.items()},
                "authors": {k: v.to_dict() for k, v in self.authors.items()},
            }
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, 'w') as f:
                json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load from disk."""
        try:
            with open(self._persist_path, 'r') as f:
                data = json.load(f)
            self.papers = {k: Paper.from_dict(v) for k, v in data.get("papers", {}).items()}
            self.authors = {k: Author.from_dict(v) for k, v in data.get("authors", {}).items()}
        except (json.JSONDecodeError, FileNotFoundError):
            pass


class CitationAgent:
    """
    Citation Agent - Tracks and analyzes academic citations.

    Can be used standalone or as a subagent for domain-specific agents.
    Provides tools for:
    - Searching academic papers
    - Tracking citations and authors
    - Building citation networks
    - Computing citation metrics
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []

        # Initialize citation graph
        graph_path = None
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            graph_path = os.path.join(persist_dir, "citation_graph.json")
        self.graph = CitationGraph(persist_path=graph_path)

        self.tools = self._get_tools()

    @property
    def name(self) -> str:
        return "Citation Agent"

    @property
    def description(self) -> str:
        return "Tracks papers, authors, citations, and analyzes academic networks"

    @property
    def system_prompt(self) -> str:
        stats = self.graph.get_statistics()
        return f"""You are a Citation Agent specialized in tracking and analyzing academic literature.

Your capabilities:
1. Search for academic papers and their citation counts
2. Track author publication records and h-indices
3. Build and analyze citation networks
4. Identify influential papers and authors in a field
5. Find connections between research domains

Current database:
- Papers tracked: {stats.get('total_papers', 0)}
- Authors tracked: {stats.get('total_authors', 0)}
- Total citations: {stats.get('total_citations', 0)}

When searching for papers, extract and record:
- Paper title, authors, year, venue
- Citation count
- Key findings relevant to the query
- Relationships to other papers

Always provide citation counts and author metrics when discussing papers."""

    def _get_tools(self) -> list:
        """Get tools for citation operations."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_papers",
                    "description": "Search for academic papers on a topic. Returns paper titles, authors, citations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for papers"
                            },
                            "domain": {
                                "type": "string",
                                "description": "Academic domain (e.g., psychology, statistics, biology)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_author_info",
                    "description": "Get information about an author including h-index and publications.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "author_name": {
                                "type": "string",
                                "description": "Name of the author to look up"
                            }
                        },
                        "required": ["author_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_citation_stats",
                    "description": "Get citation statistics for the tracked literature.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "record_paper",
                    "description": "Record a paper in the citation database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "authors": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "year": {"type": "integer"},
                            "citations": {"type": "integer"},
                            "venue": {"type": "string"},
                            "domain": {"type": "string"},
                            "abstract": {"type": "string"}
                        },
                        "required": ["title", "authors", "year", "citations"]
                    }
                }
            }
        ]

    def search_papers_web(self, query: str, domain: str = "") -> str:
        """Search for papers using web search."""
        search_query = f"academic paper {query}"
        if domain:
            search_query += f" {domain}"
        search_query += " citations"

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=10))

            if not results:
                return "No papers found."

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

    def record_paper(
        self,
        title: str,
        authors: List[str],
        year: int,
        citations: int,
        venue: str = "",
        domain: str = "",
        abstract: str = "",
    ) -> str:
        """Record a paper in the citation graph."""
        import hashlib
        paper_id = hashlib.sha256(f"{title}{year}".encode()).hexdigest()[:12]

        paper = Paper(
            title=title,
            paper_id=paper_id,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            citation_count=citations,
            domains={domain} if domain else set(),
        )

        self.graph.add_paper(paper)
        return f"Recorded paper '{title}' (ID: {paper_id}) with {citations} citations"

    def get_author_info(self, author_name: str) -> str:
        """Get author information."""
        author = self.graph.get_author(author_name)
        if author:
            return (
                f"Author: {author.name}\n"
                f"H-index: {author.h_index}\n"
                f"Total Citations: {author.total_citations}\n"
                f"Papers: {len(author.papers)}\n"
                f"Domains: {', '.join(author.domains)}\n"
                f"Collaborators: {len(author.collaborators)}"
            )
        else:
            # Search for author
            return self.search_papers_web(f"author:{author_name}")

    def _process_tool_calls(self, tool_calls) -> list:
        """Process tool calls."""
        results = []
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"  [{self.name}] {func_name}...")

            if func_name == "search_papers":
                result = self.search_papers_web(
                    args["query"],
                    args.get("domain", "")
                )
            elif func_name == "get_author_info":
                result = self.get_author_info(args["author_name"])
            elif func_name == "get_citation_stats":
                stats = self.graph.get_statistics()
                result = json.dumps(stats, indent=2)
            elif func_name == "record_paper":
                result = self.record_paper(
                    title=args["title"],
                    authors=args["authors"],
                    year=args["year"],
                    citations=args["citations"],
                    venue=args.get("venue", ""),
                    domain=args.get("domain", ""),
                    abstract=args.get("abstract", ""),
                )
            else:
                result = f"Unknown tool: {func_name}"

            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "content": result
            })

        return results

    def chat(self, user_message: str) -> str:
        """Chat with the citation agent."""
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

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    # =========================================================================
    # Subagent API - Methods for use by parent agents
    # =========================================================================

    def lookup_citations(self, paper_title: str) -> Optional[Dict]:
        """Quick lookup of a paper's citation info (for subagent use)."""
        papers = self.graph.search_papers(query=paper_title)
        if papers:
            return papers[0].to_dict()
        return None

    def get_author_metrics(self, author_name: str) -> Optional[Dict]:
        """Get author metrics (for subagent use)."""
        author = self.graph.get_author(author_name)
        if author:
            return author.to_dict()
        return None

    def add_paper_from_search(
        self,
        title: str,
        authors: List[str],
        year: int,
        citations: int,
        domain: str,
    ) -> str:
        """Add a paper discovered during research (for subagent use)."""
        return self.record_paper(title, authors, year, citations, domain=domain)

    def get_domain_statistics(self, domain: str) -> Dict:
        """Get statistics for a specific domain (for subagent use)."""
        papers = self.graph.search_papers(domain=domain)
        if not papers:
            return {"domain": domain, "papers": 0}

        citations = [p.citation_count for p in papers]
        authors = set()
        for p in papers:
            authors.update(p.authors)

        return {
            "domain": domain,
            "papers": len(papers),
            "total_citations": sum(citations),
            "avg_citations": sum(citations) / len(citations),
            "unique_authors": len(authors),
            "top_papers": [
                {"title": p.title, "citations": p.citation_count}
                for p in papers[:5]
            ],
        }
