"""Node functions for the LangGraph research agent workflow."""

from typing import Dict, Any
from langchain_core.documents import Document

from state import ResearchState, MAX_ITERATIONS
from graders import (
    question_router,
    hallucination_grader,
    answer_grader,
    query_refiner,
    response_synthesizer
)
from tools import (
    web_search,
    academic_search,
    format_documents_for_context,
    format_agent_responses
)

# Import agents
from agents.statistics_agent import StatisticsAgent
from agents.biology_agent import BiologyAgent
from agents.psychology_agent import PsychologyAgent
from agents.philosophy_agent import PhilosophyAgent
from agents.psychiatry_agent import PsychiatryAgent
from agents.applications_agent import ApplicationsAgent
from agents.product_manager_agent import ProductManagerAgent
from agents.writing_agent import WritingAgent


# Initialize all specialist agents
AGENTS = {
    "statistics": StatisticsAgent(),
    "biology": BiologyAgent(),
    "psychology": PsychologyAgent(),
    "philosophy": PhilosophyAgent(),
    "psychiatry": PsychiatryAgent(),
    "applications": ApplicationsAgent(),
    "product_manager": ProductManagerAgent(),
    "writing": WritingAgent(),
}


def route_question(state: ResearchState) -> ResearchState:
    """
    Route the question to appropriate domain agent(s).

    Uses LLM to classify the question and determine routing.
    """
    print("---ROUTE QUESTION---")
    question = state["question"]

    # Use the router to classify
    routing = question_router.invoke({"question": question})

    print(f"  Primary domain: {routing['primary_domain']}")
    print(f"  Secondary domains: {routing['secondary_domains']}")
    print(f"  Needs web search: {routing['needs_web_search']}")

    return {
        **state,
        "primary_domain": routing["primary_domain"],
        "secondary_domains": routing.get("secondary_domains", []),
        "web_search_needed": routing.get("needs_web_search", False),
        "iteration_count": state.get("iteration_count", 0)
    }


def query_primary_agent(state: ResearchState) -> ResearchState:
    """
    Query the primary domain expert.
    """
    print("---QUERY PRIMARY AGENT---")
    question = state["question"]
    primary_domain = state["primary_domain"]

    agent = AGENTS.get(primary_domain)
    if not agent:
        print(f"  Warning: Agent '{primary_domain}' not found, using statistics")
        agent = AGENTS["statistics"]

    print(f"  Querying {agent.name}...")
    response = agent.chat(question)

    agent_responses = state.get("agent_responses", {})
    agent_responses[agent.name] = response

    return {
        **state,
        "agent_responses": agent_responses,
        "synthesis": response  # Initial synthesis is just the primary response
    }


def query_secondary_agents(state: ResearchState) -> ResearchState:
    """
    Query secondary domain experts for cross-domain questions.
    """
    print("---QUERY SECONDARY AGENTS---")
    question = state["question"]
    secondary_domains = state.get("secondary_domains", [])

    agent_responses = state.get("agent_responses", {})

    for domain in secondary_domains:
        agent = AGENTS.get(domain)
        if agent:
            print(f"  Querying {agent.name}...")
            response = agent.chat(question)
            agent_responses[agent.name] = response

    return {
        **state,
        "agent_responses": agent_responses
    }


def synthesize_responses(state: ResearchState) -> ResearchState:
    """
    Synthesize responses from multiple agents into a coherent answer.
    """
    print("---SYNTHESIZE RESPONSES---")
    question = state["question"]
    agent_responses = state.get("agent_responses", {})
    documents = state.get("documents", [])

    # Format inputs for synthesis
    formatted_responses = format_agent_responses(agent_responses)
    formatted_docs = format_documents_for_context(documents)

    # Generate synthesis
    synthesis = response_synthesizer.invoke({
        "question": question,
        "agent_responses": formatted_responses,
        "web_results": formatted_docs
    })

    return {
        **state,
        "synthesis": synthesis.content if hasattr(synthesis, 'content') else str(synthesis)
    }


def web_search_node(state: ResearchState) -> ResearchState:
    """
    Perform web search to augment agent responses.
    """
    print("---WEB SEARCH---")
    question = state["question"]
    documents = state.get("documents", [])

    # Perform academic search
    new_docs = academic_search(question, max_results=5)
    documents.extend(new_docs)

    print(f"  Found {len(new_docs)} documents")

    return {
        **state,
        "documents": documents
    }


def check_hallucination(state: ResearchState) -> ResearchState:
    """
    Check if the generated response is grounded in sources.
    """
    print("---CHECK HALLUCINATION---")
    synthesis = state.get("synthesis", "")
    documents = state.get("documents", [])
    agent_responses = state.get("agent_responses", {})

    # Combine all sources for grounding check
    all_sources = format_documents_for_context(documents)
    if agent_responses:
        all_sources += "\n\nAgent research:\n" + format_agent_responses(agent_responses)

    # Grade hallucination
    result = hallucination_grader.invoke({
        "documents": all_sources,
        "generation": synthesis
    })

    grade = result.get("score", "yes").lower()
    print(f"  Hallucination check: {'GROUNDED' if grade == 'yes' else 'NOT GROUNDED'}")

    if grade != "yes" and result.get("unsupported_claims"):
        print(f"  Unsupported claims: {result['unsupported_claims']}")

    return {
        **state,
        "hallucination_grade": "grounded" if grade == "yes" else "not_grounded"
    }


def grade_answer(state: ResearchState) -> ResearchState:
    """
    Check if the answer adequately addresses the question.
    """
    print("---GRADE ANSWER---")
    question = state["question"]
    synthesis = state.get("synthesis", "")

    # Grade the answer
    result = answer_grader.invoke({
        "question": question,
        "generation": synthesis
    })

    grade = result.get("score", "yes").lower()
    print(f"  Answer grade: {'USEFUL' if grade == 'yes' else 'NOT USEFUL'}")

    if grade != "yes" and result.get("missing_aspects"):
        print(f"  Missing aspects: {result['missing_aspects']}")

    return {
        **state,
        "answer_grade": "useful" if grade == "yes" else "not_useful"
    }


def refine_and_retry(state: ResearchState) -> ResearchState:
    """
    Refine the query and prepare for retry.
    """
    print("---REFINE AND RETRY---")
    question = state["question"]
    synthesis = state.get("synthesis", "")
    iteration_count = state.get("iteration_count", 0)

    # Identify issues
    issues = []
    if state.get("hallucination_grade") == "not_grounded":
        issues.append("Response contains unsupported claims")
    if state.get("answer_grade") == "not_useful":
        issues.append("Response does not adequately address the question")

    # Refine query
    refinement = query_refiner.invoke({
        "question": question,
        "generation": synthesis,
        "issues": ", ".join(issues)
    })

    print(f"  Refined query: {refinement.get('refined_query', question)}")
    print(f"  Iteration: {iteration_count + 1}")

    # Clear agent responses for retry
    for agent in AGENTS.values():
        agent.clear_history()

    return {
        **state,
        "question": refinement.get("refined_query", question),
        "agent_responses": {},
        "documents": [],
        "synthesis": "",
        "iteration_count": iteration_count + 1,
        "web_search_needed": True  # Force web search on retry
    }


def generate_response(state: ResearchState) -> ResearchState:
    """
    Generate the final formatted response.
    """
    print("---GENERATE FINAL RESPONSE---")
    synthesis = state.get("synthesis", "")
    documents = state.get("documents", [])

    # Add source citations if available
    final_response = synthesis
    if documents:
        sources = "\n\nSources:\n"
        for doc in documents:
            if "url" in doc.metadata:
                sources += f"- {doc.metadata.get('title', 'Unknown')}: {doc.metadata['url']}\n"
        final_response += sources

    return {
        **state,
        "final_response": final_response
    }


# ============================================================================
# Conditional Edge Functions
# ============================================================================

def decide_routing_path(state: ResearchState) -> str:
    """
    Decide the routing path based on question classification.

    Returns:
        - "single_domain" for single agent queries
        - "cross_domain" for multi-agent queries
        - "web_search" for direct web search
    """
    secondary_domains = state.get("secondary_domains", [])
    web_search_needed = state.get("web_search_needed", False)

    if secondary_domains:
        return "cross_domain"
    elif web_search_needed and not state.get("primary_domain"):
        return "web_search"
    else:
        return "single_domain"


def decide_after_hallucination_check(state: ResearchState) -> str:
    """
    Decide next step after hallucination check.

    Returns:
        - "grounded" to proceed to answer grading
        - "not_grounded" to do web search and retry
    """
    grade = state.get("hallucination_grade", "grounded")
    iteration_count = state.get("iteration_count", 0)

    if grade == "grounded":
        return "grounded"
    elif iteration_count >= MAX_ITERATIONS:
        print(f"  Max iterations ({MAX_ITERATIONS}) reached, proceeding anyway")
        return "grounded"
    else:
        return "not_grounded"


def decide_after_answer_grade(state: ResearchState) -> str:
    """
    Decide next step after answer grading.

    Returns:
        - "useful" to generate final response
        - "not_useful" to refine and retry
    """
    grade = state.get("answer_grade", "useful")
    iteration_count = state.get("iteration_count", 0)

    if grade == "useful":
        return "useful"
    elif iteration_count >= MAX_ITERATIONS:
        print(f"  Max iterations ({MAX_ITERATIONS}) reached, returning current response")
        return "useful"
    else:
        return "not_useful"
