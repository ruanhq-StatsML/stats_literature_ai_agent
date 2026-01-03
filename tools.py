"""Web search and retrieval tools for the research agent."""

import os
from typing import List, Optional
from langchain_core.documents import Document
from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 8) -> List[Document]:
    """
    Perform a web search using DuckDuckGo.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        List of Document objects with search results
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return []

        documents = []
        for r in results:
            content = f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}"
            doc = Document(
                page_content=content,
                metadata={
                    "title": r["title"],
                    "url": r["href"],
                    "source": "web_search"
                }
            )
            documents.append(doc)

        return documents

    except Exception as e:
        print(f"Web search error: {e}")
        return []


def academic_search(query: str, max_results: int = 8) -> List[Document]:
    """
    Perform an academic-focused web search.
    Adds academic source modifiers to the query.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        List of Document objects with search results
    """
    # Enhance query for academic sources
    academic_query = f"{query} site:arxiv.org OR site:scholar.google.com OR site:pubmed.ncbi.nlm.nih.gov OR site:nature.com OR site:sciencedirect.com"

    return web_search(academic_query, max_results)


def industry_search(query: str, max_results: int = 8) -> List[Document]:
    """
    Perform an industry/applications-focused web search.
    Targets industry blogs and practical implementations.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        List of Document objects with search results
    """
    # Enhance query for industry sources
    industry_query = f"{query} site:engineering.uber.com OR site:research.google OR site:ai.meta.com OR site:github.com OR site:towardsdatascience.com OR site:medium.com"

    return web_search(industry_query, max_results)


def format_documents_for_context(documents: List[Document]) -> str:
    """
    Format a list of documents into a string for LLM context.

    Args:
        documents: List of Document objects

    Returns:
        Formatted string with document contents
    """
    if not documents:
        return "No documents available."

    formatted = []
    for i, doc in enumerate(documents, 1):
        formatted.append(f"[Document {i}]\n{doc.page_content}\n")

    return "\n---\n".join(formatted)


def format_agent_responses(responses: dict) -> str:
    """
    Format agent responses for synthesis.

    Args:
        responses: Dictionary of {agent_name: response}

    Returns:
        Formatted string with agent responses
    """
    if not responses:
        return "No agent responses available."

    formatted = []
    for agent_name, response in responses.items():
        formatted.append(f"[{agent_name}]\n{response}\n")

    return "\n---\n".join(formatted)


# Optional: Tavily search integration (requires API key)
def tavily_search(query: str, max_results: int = 5) -> List[Document]:
    """
    Perform a search using Tavily API (better for research queries).
    Requires TAVILY_API_KEY environment variable.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        List of Document objects with search results
    """
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        print("TAVILY_API_KEY not set, falling back to DuckDuckGo")
        return web_search(query, max_results)

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=tavily_key)
        response = client.search(query, max_results=max_results)

        documents = []
        for result in response.get("results", []):
            content = f"Title: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
            doc = Document(
                page_content=content,
                metadata={
                    "title": result["title"],
                    "url": result["url"],
                    "source": "tavily"
                }
            )
            documents.append(doc)

        return documents

    except ImportError:
        print("tavily package not installed, falling back to DuckDuckGo")
        return web_search(query, max_results)
    except Exception as e:
        print(f"Tavily search error: {e}, falling back to DuckDuckGo")
        return web_search(query, max_results)
