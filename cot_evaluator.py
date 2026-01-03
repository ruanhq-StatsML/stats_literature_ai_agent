"""
Chain-of-Thought (CoT) Evaluator for the Stats Literature AI Agent.

This module provides comprehensive evaluation of reasoning quality across
the agent's workflow, including:
- Reasoning step quality
- Logical coherence between steps
- Grounding in evidence
- Completeness of reasoning chains
- Causal validity of inferences
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser


# ============================================================================
# Data Classes for Evaluation Results
# ============================================================================

class ReasoningQuality(Enum):
    """Quality levels for reasoning evaluation."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"
    INVALID = "invalid"


@dataclass
class StepEvaluation:
    """Evaluation result for a single reasoning step."""
    step_name: str
    step_content: str
    quality: ReasoningQuality
    score: float  # 0-100
    coherence_score: float  # 0-100
    grounding_score: float  # 0-100
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class ChainEvaluation:
    """Evaluation result for the entire reasoning chain."""
    query: str
    timestamp: str
    overall_score: float  # 0-100
    step_evaluations: List[StepEvaluation] = field(default_factory=list)
    chain_coherence: float = 0.0  # 0-100
    chain_completeness: float = 0.0  # 0-100
    causal_validity: float = 0.0  # 0-100
    evidence_grounding: float = 0.0  # 0-100
    logical_flow: float = 0.0  # 0-100
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        for i, step in enumerate(result['step_evaluations']):
            step['quality'] = step['quality'].value if isinstance(step['quality'], ReasoningQuality) else step['quality']
        return result


# ============================================================================
# CoT Evaluator Prompts
# ============================================================================

STEP_EVALUATION_PROMPT = PromptTemplate(
    template="""You are an expert evaluator of chain-of-thought reasoning in AI systems.

Evaluate the following reasoning step from a multi-agent research system.

Step Name: {step_name}
Step Content: {step_content}
Previous Context: {previous_context}
Original Query: {query}

Evaluate this step on the following criteria:

1. QUALITY (0-100): How well-reasoned is this step?
   - Clear logical structure
   - Appropriate depth of analysis
   - Relevant to the query

2. COHERENCE (0-100): How well does this step connect to previous steps?
   - Logical flow from prior reasoning
   - Consistent terminology and concepts
   - Builds appropriately on prior conclusions

3. GROUNDING (0-100): How well is the reasoning grounded in evidence?
   - Claims supported by sources
   - Appropriate citations or references
   - Avoids unfounded assertions

Output a JSON object with this exact structure:
{{
    "quality_score": <0-100>,
    "coherence_score": <0-100>,
    "grounding_score": <0-100>,
    "quality_level": "excellent|good|adequate|poor|invalid",
    "issues": ["list of specific issues found"],
    "strengths": ["list of specific strengths"],
    "reasoning": "explanation of evaluation"
}}""",
    input_variables=["step_name", "step_content", "previous_context", "query"]
)

CHAIN_EVALUATION_PROMPT = PromptTemplate(
    template="""You are an expert evaluator of chain-of-thought reasoning in AI systems.

Evaluate the complete reasoning chain from a multi-agent research system.

Original Query: {query}

Complete Reasoning Chain:
{reasoning_chain}

Step-by-Step Evaluations:
{step_evaluations}

Evaluate the OVERALL chain on these criteria:

1. CHAIN COHERENCE (0-100): How well do all steps connect as a unified argument?
   - Logical progression from start to finish
   - No contradictions between steps
   - Smooth transitions

2. CHAIN COMPLETENESS (0-100): Does the chain fully address the query?
   - All aspects of query covered
   - No major gaps in reasoning
   - Appropriate depth

3. CAUSAL VALIDITY (0-100): Are causal claims valid?
   - Distinguishes correlation from causation
   - Appropriate causal language
   - Acknowledges limitations

4. EVIDENCE GROUNDING (0-100): Is the chain grounded in evidence?
   - Claims supported throughout
   - Sources appropriately cited
   - Balanced use of evidence

5. LOGICAL FLOW (0-100): Is the overall logic sound?
   - Valid inferences
   - No logical fallacies
   - Clear reasoning structure

Output a JSON object with this exact structure:
{{
    "chain_coherence": <0-100>,
    "chain_completeness": <0-100>,
    "causal_validity": <0-100>,
    "evidence_grounding": <0-100>,
    "logical_flow": <0-100>,
    "overall_score": <0-100>,
    "summary": "overall assessment of the reasoning chain",
    "recommendations": ["list of specific improvements"]
}}""",
    input_variables=["query", "reasoning_chain", "step_evaluations"]
)

CAUSAL_REASONING_PROMPT = PromptTemplate(
    template="""You are an expert in causal inference and reasoning evaluation.

Evaluate the causal reasoning in the following response.

Query: {query}
Response: {response}

Evaluate the causal aspects:

1. CAUSAL CLAIMS IDENTIFICATION: List all causal claims made
2. CAUSAL VALIDITY: Are causal claims justified?
3. CONFOUNDING AWARENESS: Does it acknowledge potential confounders?
4. CAUSAL VS PREDICTIVE: Does it distinguish causal from predictive claims?
5. INTERVENTION REASONING: Are "what-if" scenarios handled correctly?

Output a JSON object with this exact structure:
{{
    "causal_claims": ["list of causal claims identified"],
    "valid_claims": ["list of justified causal claims"],
    "invalid_claims": ["list of unjustified causal claims"],
    "confounding_acknowledged": true|false,
    "causal_predictive_distinction": true|false,
    "causal_score": <0-100>,
    "reasoning": "explanation of causal evaluation"
}}""",
    input_variables=["query", "response"]
)

REASONING_STEP_EXTRACTION_PROMPT = PromptTemplate(
    template="""Extract the reasoning steps from the following agent workflow trace.

Workflow Trace:
{trace}

Identify and extract each distinct reasoning step, including:
- Question routing decisions
- Agent selection rationale
- Query formulation
- Evidence gathering
- Synthesis reasoning
- Quality checks

Output a JSON object with this exact structure:
{{
    "steps": [
        {{
            "step_number": 1,
            "step_name": "name of this step",
            "step_type": "routing|query|search|synthesis|validation|other",
            "content": "the actual reasoning content",
            "inputs": ["what this step used as input"],
            "outputs": ["what this step produced"]
        }}
    ],
    "total_steps": <number>
}}""",
    input_variables=["trace"]
)


# ============================================================================
# Main Evaluator Class
# ============================================================================

class ChainOfThoughtEvaluator:
    """
    Comprehensive evaluator for chain-of-thought reasoning in the
    stats_literature_agent system.
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.0,
        api_key: Optional[str] = None
    ):
        """
        Initialize the CoT evaluator.

        Args:
            model_name: OpenAI model to use for evaluation
            temperature: Temperature for evaluation (0 = deterministic)
            api_key: OpenAI API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            api_key=self.api_key
        )

        # Initialize evaluation chains
        self.step_evaluator = STEP_EVALUATION_PROMPT | self.llm | JsonOutputParser()
        self.chain_evaluator = CHAIN_EVALUATION_PROMPT | self.llm | JsonOutputParser()
        self.causal_evaluator = CAUSAL_REASONING_PROMPT | self.llm | JsonOutputParser()
        self.step_extractor = REASONING_STEP_EXTRACTION_PROMPT | self.llm | JsonOutputParser()

        # Evaluation history
        self.evaluation_history: List[ChainEvaluation] = []

    def extract_reasoning_steps(self, trace: str) -> List[Dict[str, Any]]:
        """
        Extract reasoning steps from a workflow trace.

        Args:
            trace: Raw workflow trace or log

        Returns:
            List of extracted reasoning steps
        """
        try:
            result = self.step_extractor.invoke({"trace": trace})
            return result.get("steps", [])
        except Exception as e:
            print(f"Error extracting steps: {e}")
            return []

    def evaluate_step(
        self,
        step_name: str,
        step_content: str,
        previous_context: str,
        query: str
    ) -> StepEvaluation:
        """
        Evaluate a single reasoning step.

        Args:
            step_name: Name/identifier of the step
            step_content: Content of the reasoning step
            previous_context: Context from previous steps
            query: Original user query

        Returns:
            StepEvaluation object with scores and analysis
        """
        try:
            result = self.step_evaluator.invoke({
                "step_name": step_name,
                "step_content": step_content,
                "previous_context": previous_context,
                "query": query
            })

            quality_map = {
                "excellent": ReasoningQuality.EXCELLENT,
                "good": ReasoningQuality.GOOD,
                "adequate": ReasoningQuality.ADEQUATE,
                "poor": ReasoningQuality.POOR,
                "invalid": ReasoningQuality.INVALID
            }

            return StepEvaluation(
                step_name=step_name,
                step_content=step_content[:500] + "..." if len(step_content) > 500 else step_content,
                quality=quality_map.get(result.get("quality_level", "adequate"), ReasoningQuality.ADEQUATE),
                score=result.get("quality_score", 50),
                coherence_score=result.get("coherence_score", 50),
                grounding_score=result.get("grounding_score", 50),
                issues=result.get("issues", []),
                strengths=result.get("strengths", []),
                reasoning=result.get("reasoning", "")
            )
        except Exception as e:
            print(f"Error evaluating step {step_name}: {e}")
            return StepEvaluation(
                step_name=step_name,
                step_content=step_content[:200],
                quality=ReasoningQuality.INVALID,
                score=0,
                coherence_score=0,
                grounding_score=0,
                issues=[f"Evaluation error: {str(e)}"],
                strengths=[],
                reasoning="Could not evaluate step"
            )

    def evaluate_causal_reasoning(
        self,
        query: str,
        response: str
    ) -> Dict[str, Any]:
        """
        Evaluate the causal reasoning quality in a response.

        Args:
            query: Original query
            response: Agent response to evaluate

        Returns:
            Dictionary with causal evaluation results
        """
        try:
            result = self.causal_evaluator.invoke({
                "query": query,
                "response": response
            })
            return result
        except Exception as e:
            print(f"Error in causal evaluation: {e}")
            return {
                "causal_claims": [],
                "valid_claims": [],
                "invalid_claims": [],
                "confounding_acknowledged": False,
                "causal_predictive_distinction": False,
                "causal_score": 0,
                "reasoning": f"Evaluation error: {str(e)}"
            }

    def evaluate_chain(
        self,
        query: str,
        workflow_state: Dict[str, Any],
        agent_responses: Optional[Dict[str, str]] = None,
        verbose: bool = True
    ) -> ChainEvaluation:
        """
        Evaluate the complete reasoning chain from a workflow execution.

        Args:
            query: Original user query
            workflow_state: Final state from LangGraph workflow
            agent_responses: Optional dict of agent name -> response
            verbose: Whether to print progress

        Returns:
            ChainEvaluation with comprehensive analysis
        """
        if verbose:
            print("=" * 60)
            print("CHAIN-OF-THOUGHT EVALUATION")
            print("=" * 60)

        # Extract components from workflow state
        primary_domain = workflow_state.get("primary_domain", "unknown")
        secondary_domains = workflow_state.get("secondary_domains", [])
        synthesis = workflow_state.get("synthesis", "")
        final_response = workflow_state.get("final_response", synthesis)
        hallucination_grade = workflow_state.get("hallucination_grade", "unknown")
        answer_grade = workflow_state.get("answer_grade", "unknown")
        iteration_count = workflow_state.get("iteration_count", 0)

        # Get agent responses
        if agent_responses is None:
            agent_responses = workflow_state.get("agent_responses", {})

        # Build reasoning chain for evaluation
        reasoning_chain_parts = []
        step_evaluations = []
        previous_context = ""

        # Step 1: Evaluate routing decision
        if verbose:
            print("\n[1/5] Evaluating routing decision...")
        routing_content = (
            f"Primary domain selected: {primary_domain}\n"
            f"Secondary domains: {secondary_domains}\n"
            f"Query: {query}"
        )
        routing_eval = self.evaluate_step(
            step_name="Question Routing",
            step_content=routing_content,
            previous_context="",
            query=query
        )
        step_evaluations.append(routing_eval)
        reasoning_chain_parts.append(f"ROUTING: {routing_content}")
        previous_context = routing_content

        # Step 2: Evaluate each agent response
        if verbose:
            print(f"\n[2/5] Evaluating {len(agent_responses)} agent responses...")
        for agent_name, response in agent_responses.items():
            agent_eval = self.evaluate_step(
                step_name=f"Agent Response: {agent_name}",
                step_content=response[:2000],
                previous_context=previous_context,
                query=query
            )
            step_evaluations.append(agent_eval)
            reasoning_chain_parts.append(f"{agent_name}: {response[:1000]}...")
            previous_context += f"\n{agent_name}: {response[:500]}"

        # Step 3: Evaluate synthesis
        if verbose:
            print("\n[3/5] Evaluating synthesis...")
        if synthesis:
            synthesis_eval = self.evaluate_step(
                step_name="Response Synthesis",
                step_content=synthesis[:2000],
                previous_context=previous_context,
                query=query
            )
            step_evaluations.append(synthesis_eval)
            reasoning_chain_parts.append(f"SYNTHESIS: {synthesis[:1000]}...")

        # Step 4: Evaluate validation steps
        if verbose:
            print("\n[4/5] Evaluating validation steps...")
        validation_content = (
            f"Hallucination check: {hallucination_grade}\n"
            f"Answer quality: {answer_grade}\n"
            f"Iterations required: {iteration_count}"
        )
        validation_eval = self.evaluate_step(
            step_name="Quality Validation",
            step_content=validation_content,
            previous_context=previous_context,
            query=query
        )
        step_evaluations.append(validation_eval)

        # Step 5: Evaluate causal reasoning
        if verbose:
            print("\n[5/5] Evaluating causal reasoning...")
        causal_eval = self.evaluate_causal_reasoning(query, final_response)

        # Build complete reasoning chain string
        reasoning_chain = "\n\n".join(reasoning_chain_parts)

        # Format step evaluations for chain evaluation
        step_eval_summary = "\n".join([
            f"- {se.step_name}: Score={se.score}, Quality={se.quality.value}"
            for se in step_evaluations
        ])

        # Perform overall chain evaluation
        if verbose:
            print("\n[FINAL] Computing overall chain evaluation...")
        try:
            chain_result = self.chain_evaluator.invoke({
                "query": query,
                "reasoning_chain": reasoning_chain[:4000],
                "step_evaluations": step_eval_summary
            })
        except Exception as e:
            print(f"Error in chain evaluation: {e}")
            chain_result = {
                "chain_coherence": 50,
                "chain_completeness": 50,
                "causal_validity": causal_eval.get("causal_score", 50),
                "evidence_grounding": 50,
                "logical_flow": 50,
                "overall_score": 50,
                "summary": f"Partial evaluation due to error: {str(e)}",
                "recommendations": []
            }

        # Create final evaluation
        evaluation = ChainEvaluation(
            query=query,
            timestamp=datetime.now().isoformat(),
            overall_score=chain_result.get("overall_score", 50),
            step_evaluations=step_evaluations,
            chain_coherence=chain_result.get("chain_coherence", 50),
            chain_completeness=chain_result.get("chain_completeness", 50),
            causal_validity=chain_result.get("causal_validity", causal_eval.get("causal_score", 50)),
            evidence_grounding=chain_result.get("evidence_grounding", 50),
            logical_flow=chain_result.get("logical_flow", 50),
            summary=chain_result.get("summary", ""),
            recommendations=chain_result.get("recommendations", [])
        )

        # Store in history
        self.evaluation_history.append(evaluation)

        if verbose:
            self._print_evaluation_report(evaluation, causal_eval)

        return evaluation

    def _print_evaluation_report(
        self,
        evaluation: ChainEvaluation,
        causal_eval: Dict[str, Any]
    ):
        """Print a formatted evaluation report."""
        print("\n" + "=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)

        print(f"\nQuery: {evaluation.query[:100]}...")
        print(f"Timestamp: {evaluation.timestamp}")

        print("\n--- OVERALL SCORES ---")
        print(f"Overall Score:      {evaluation.overall_score:.1f}/100")
        print(f"Chain Coherence:    {evaluation.chain_coherence:.1f}/100")
        print(f"Chain Completeness: {evaluation.chain_completeness:.1f}/100")
        print(f"Causal Validity:    {evaluation.causal_validity:.1f}/100")
        print(f"Evidence Grounding: {evaluation.evidence_grounding:.1f}/100")
        print(f"Logical Flow:       {evaluation.logical_flow:.1f}/100")

        print("\n--- STEP EVALUATIONS ---")
        for step in evaluation.step_evaluations:
            status = "✓" if step.score >= 70 else "△" if step.score >= 50 else "✗"
            print(f"{status} {step.step_name}: {step.score:.1f}/100 ({step.quality.value})")
            if step.issues:
                for issue in step.issues[:2]:
                    print(f"    Issue: {issue}")

        print("\n--- CAUSAL REASONING ---")
        print(f"Causal Claims Found: {len(causal_eval.get('causal_claims', []))}")
        print(f"Valid Claims: {len(causal_eval.get('valid_claims', []))}")
        print(f"Invalid Claims: {len(causal_eval.get('invalid_claims', []))}")
        print(f"Confounding Acknowledged: {causal_eval.get('confounding_acknowledged', False)}")
        print(f"Causal/Predictive Distinction: {causal_eval.get('causal_predictive_distinction', False)}")

        print("\n--- SUMMARY ---")
        print(evaluation.summary)

        if evaluation.recommendations:
            print("\n--- RECOMMENDATIONS ---")
            for i, rec in enumerate(evaluation.recommendations, 1):
                print(f"{i}. {rec}")

        print("\n" + "=" * 60)

    def evaluate_from_trace(
        self,
        query: str,
        trace: str,
        verbose: bool = True
    ) -> ChainEvaluation:
        """
        Evaluate reasoning from a raw workflow trace/log.

        Args:
            query: Original query
            trace: Raw trace string from workflow execution
            verbose: Whether to print progress

        Returns:
            ChainEvaluation object
        """
        # Extract steps from trace
        steps = self.extract_reasoning_steps(trace)

        # Build workflow state from extracted steps
        workflow_state = {
            "primary_domain": "extracted",
            "secondary_domains": [],
            "synthesis": "",
            "final_response": trace,
            "hallucination_grade": "unknown",
            "answer_grade": "unknown",
            "iteration_count": 0
        }

        # Extract agent responses
        agent_responses = {}
        for step in steps:
            if step.get("step_type") in ["query", "synthesis"]:
                agent_responses[step.get("step_name", "Unknown")] = step.get("content", "")

        return self.evaluate_chain(
            query=query,
            workflow_state=workflow_state,
            agent_responses=agent_responses,
            verbose=verbose
        )

    def get_aggregate_metrics(self) -> Dict[str, float]:
        """
        Get aggregate metrics across all evaluations in history.

        Returns:
            Dictionary with average scores
        """
        if not self.evaluation_history:
            return {}

        n = len(self.evaluation_history)
        return {
            "avg_overall_score": sum(e.overall_score for e in self.evaluation_history) / n,
            "avg_chain_coherence": sum(e.chain_coherence for e in self.evaluation_history) / n,
            "avg_chain_completeness": sum(e.chain_completeness for e in self.evaluation_history) / n,
            "avg_causal_validity": sum(e.causal_validity for e in self.evaluation_history) / n,
            "avg_evidence_grounding": sum(e.evidence_grounding for e in self.evaluation_history) / n,
            "avg_logical_flow": sum(e.logical_flow for e in self.evaluation_history) / n,
            "total_evaluations": n
        }

    def save_evaluations(self, filepath: str):
        """Save evaluation history to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(
                [e.to_dict() for e in self.evaluation_history],
                f,
                indent=2
            )
        print(f"Saved {len(self.evaluation_history)} evaluations to {filepath}")

    def load_evaluations(self, filepath: str):
        """Load evaluation history from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.evaluation_history = []
        for item in data:
            # Reconstruct step evaluations
            steps = []
            for step_data in item.get('step_evaluations', []):
                quality = ReasoningQuality(step_data.get('quality', 'adequate'))
                steps.append(StepEvaluation(
                    step_name=step_data['step_name'],
                    step_content=step_data['step_content'],
                    quality=quality,
                    score=step_data['score'],
                    coherence_score=step_data['coherence_score'],
                    grounding_score=step_data['grounding_score'],
                    issues=step_data.get('issues', []),
                    strengths=step_data.get('strengths', []),
                    reasoning=step_data.get('reasoning', '')
                ))

            self.evaluation_history.append(ChainEvaluation(
                query=item['query'],
                timestamp=item['timestamp'],
                overall_score=item['overall_score'],
                step_evaluations=steps,
                chain_coherence=item['chain_coherence'],
                chain_completeness=item['chain_completeness'],
                causal_validity=item['causal_validity'],
                evidence_grounding=item['evidence_grounding'],
                logical_flow=item['logical_flow'],
                summary=item['summary'],
                recommendations=item['recommendations']
            ))

        print(f"Loaded {len(self.evaluation_history)} evaluations from {filepath}")


# ============================================================================
# Integration with LangGraph Workflow
# ============================================================================

def create_evaluator_node(evaluator: ChainOfThoughtEvaluator):
    """
    Create a LangGraph node function for evaluation.

    Args:
        evaluator: ChainOfThoughtEvaluator instance

    Returns:
        Node function for LangGraph workflow
    """
    def evaluate_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluation node for LangGraph workflow."""
        evaluation = evaluator.evaluate_chain(
            query=state.get("question", ""),
            workflow_state=state,
            verbose=False
        )

        return {
            **state,
            "cot_evaluation": evaluation.to_dict(),
            "cot_score": evaluation.overall_score
        }

    return evaluate_node


# ============================================================================
# CLI Interface
# ============================================================================

def run_evaluation_demo():
    """Run a demonstration of the CoT evaluator."""
    print("Chain-of-Thought Evaluator Demo")
    print("=" * 60)

    # Initialize evaluator
    evaluator = ChainOfThoughtEvaluator()

    # Example workflow state (simulated)
    example_state = {
        "question": "How can survival analysis be applied to predict soccer game timing?",
        "primary_domain": "statistics",
        "secondary_domains": ["applications"],
        "agent_responses": {
            "Statistics Agent": """
            Survival analysis is well-suited for this time-to-event prediction problem.
            Key approaches include:
            1. Cox Proportional Hazards model for hazard function estimation
            2. Kaplan-Meier curves for non-parametric survival estimation
            3. Accelerated Failure Time models for direct time modeling

            The Cox PH model: h(t|X) = h0(t) * exp(beta'X) allows incorporating
            covariates like weather, day of week, and health status.
            """,
            "Applications Agent": """
            Real-world applications of survival analysis for scheduling include:
            1. Customer churn prediction (time until customer leaves)
            2. Equipment maintenance (time until failure)
            3. Sports analytics (time between events)

            Python libraries like lifelines and scikit-survival provide
            ready-to-use implementations.
            """
        },
        "synthesis": """
        Survival analysis provides a robust framework for predicting soccer game timing.
        The Cox Proportional Hazards model can incorporate weather, schedule, and health
        covariates to estimate the hazard of playing. Combined with Kaplan-Meier curves
        for baseline estimation, this approach offers both predictive accuracy and
        interpretable hazard ratios for understanding what drives game timing.
        """,
        "final_response": "...",
        "hallucination_grade": "grounded",
        "answer_grade": "useful",
        "iteration_count": 1
    }

    # Run evaluation
    evaluation = evaluator.evaluate_chain(
        query=example_state["question"],
        workflow_state=example_state,
        verbose=True
    )

    # Show aggregate metrics
    print("\nAggregate Metrics:")
    print(evaluator.get_aggregate_metrics())

    return evaluation


if __name__ == "__main__":
    # Run demo when executed directly
    run_evaluation_demo()
