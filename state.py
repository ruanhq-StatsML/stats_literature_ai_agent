"""State definitions for the LangGraph research agent workflow."""

from typing import List, Dict, Any
from typing_extensions import TypedDict
from langchain_core.documents import Document


class ResearchState(TypedDict):
    """
    Represents the state of the research agent graph.

    Attributes:
        question: The user's research question
        primary_domain: Main domain for the query (statistics, biology, etc.)
        secondary_domains: Related domains for cross-domain queries
        agent_responses: Responses from each specialist agent {agent_name: response}
        documents: Retrieved/searched documents for grounding
        web_search_needed: Flag indicating if web search fallback is needed
        synthesis: Combined response from multiple agents
        hallucination_grade: "grounded" or "not_grounded"
        answer_grade: "useful" or "not_useful"
        iteration_count: Retry counter (max 3)
        final_response: The final formatted output
    """

    question: str
    primary_domain: str
    secondary_domains: List[str]
    agent_responses: Dict[str, str]
    documents: List[Document]
    web_search_needed: bool
    synthesis: str
    hallucination_grade: str
    answer_grade: str
    iteration_count: int
    final_response: str


# Domain constants
AVAILABLE_DOMAINS = [
    "statistics",
    "biology",
    "psychology",
    "philosophy",
    "psychiatry",
    "applications",
    "product_manager",
    "writing"
]

# Maximum retry iterations
MAX_ITERATIONS = 3
