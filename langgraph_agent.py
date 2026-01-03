"""LangGraph-based research agent with routing, self-correction, and hallucination checking."""

from langgraph.graph import END, StateGraph

from state import ResearchState
from nodes import (
    route_question,
    query_primary_agent,
    query_secondary_agents,
    synthesize_responses,
    web_search_node,
    check_hallucination,
    grade_answer,
    refine_and_retry,
    generate_response,
    decide_routing_path,
    decide_after_hallucination_check,
    decide_after_answer_grade,
)


def create_research_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for research queries.

    Workflow:
    1. Route question to appropriate agent(s)
    2. Query primary agent
    3. Optionally query secondary agents for cross-domain questions
    4. Optionally perform web search for augmentation
    5. Synthesize responses (if multiple agents)
    6. Check for hallucinations
    7. Grade answer quality
    8. Retry with refinement if needed (max 3 iterations)
    9. Generate final response
    """

    # Create the workflow
    workflow = StateGraph(ResearchState)

    # =========================================================================
    # Add Nodes
    # =========================================================================
    workflow.add_node("route_question", route_question)
    workflow.add_node("query_primary_agent", query_primary_agent)
    workflow.add_node("query_secondary_agents", query_secondary_agents)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("synthesize_responses", synthesize_responses)
    workflow.add_node("check_hallucination", check_hallucination)
    workflow.add_node("grade_answer", grade_answer)
    workflow.add_node("refine_and_retry", refine_and_retry)
    workflow.add_node("generate_response", generate_response)

    # =========================================================================
    # Set Entry Point
    # =========================================================================
    workflow.set_entry_point("route_question")

    # =========================================================================
    # Add Edges
    # =========================================================================

    # From route_question: decide routing path
    workflow.add_conditional_edges(
        "route_question",
        decide_routing_path,
        {
            "single_domain": "query_primary_agent",
            "cross_domain": "query_primary_agent",  # Will also query secondary
            "web_search": "web_search"
        }
    )

    # From query_primary_agent: check if we need secondary agents
    def check_need_secondary(state: ResearchState) -> str:
        if state.get("secondary_domains"):
            return "query_secondary"
        elif state.get("web_search_needed"):
            return "web_search"
        else:
            return "check_hallucination"

    workflow.add_conditional_edges(
        "query_primary_agent",
        check_need_secondary,
        {
            "query_secondary": "query_secondary_agents",
            "web_search": "web_search",
            "check_hallucination": "check_hallucination"
        }
    )

    # From query_secondary_agents: synthesize or web search
    def after_secondary(state: ResearchState) -> str:
        if state.get("web_search_needed"):
            return "web_search"
        else:
            return "synthesize"

    workflow.add_conditional_edges(
        "query_secondary_agents",
        after_secondary,
        {
            "web_search": "web_search",
            "synthesize": "synthesize_responses"
        }
    )

    # From web_search: check if we have agent responses to synthesize
    def after_web_search(state: ResearchState) -> str:
        if len(state.get("agent_responses", {})) > 1:
            return "synthesize"
        elif state.get("agent_responses"):
            return "check_hallucination"
        else:
            # No agent responses yet, need to query
            return "query_primary"

    workflow.add_conditional_edges(
        "web_search",
        after_web_search,
        {
            "synthesize": "synthesize_responses",
            "check_hallucination": "check_hallucination",
            "query_primary": "query_primary_agent"
        }
    )

    # From synthesize_responses: check hallucination
    workflow.add_edge("synthesize_responses", "check_hallucination")

    # From check_hallucination: decide next step
    workflow.add_conditional_edges(
        "check_hallucination",
        decide_after_hallucination_check,
        {
            "grounded": "grade_answer",
            "not_grounded": "web_search"
        }
    )

    # From grade_answer: decide next step
    workflow.add_conditional_edges(
        "grade_answer",
        decide_after_answer_grade,
        {
            "useful": "generate_response",
            "not_useful": "refine_and_retry"
        }
    )

    # From refine_and_retry: go back to routing
    workflow.add_edge("refine_and_retry", "route_question")

    # From generate_response: END
    workflow.add_edge("generate_response", END)

    return workflow


def compile_app():
    """Compile the workflow into a runnable app."""
    workflow = create_research_workflow()
    app = workflow.compile()
    return app


# Create the compiled app
app = compile_app()


def run_research_query(question: str) -> str:
    """
    Run a research query through the workflow.

    Args:
        question: The research question to answer

    Returns:
        The final response
    """
    # Initialize state
    initial_state: ResearchState = {
        "question": question,
        "primary_domain": "",
        "secondary_domains": [],
        "agent_responses": {},
        "documents": [],
        "web_search_needed": False,
        "synthesis": "",
        "hallucination_grade": "",
        "answer_grade": "",
        "iteration_count": 0,
        "final_response": ""
    }

    # Run the workflow
    print(f"\n{'='*60}")
    print(f"Research Query: {question}")
    print(f"{'='*60}\n")

    final_state = None
    for output in app.stream(initial_state):
        for key, value in output.items():
            final_state = value

    if final_state:
        return final_state.get("final_response", final_state.get("synthesis", "No response generated"))
    return "Error: No output from workflow"


# Interactive CLI for testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("LangGraph Research Agent")
    print("With routing, self-correction, and hallucination checking")
    print("="*60)
    print("\nType 'quit' to exit\n")

    while True:
        try:
            question = input("\nYour question: ").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            if not question:
                continue

            response = run_research_query(question)
            print(f"\n{'='*60}")
            print("FINAL RESPONSE:")
            print("="*60)
            print(response)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
