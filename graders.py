"""LLM-based graders for routing, hallucination checking, and answer quality."""

import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from state import AVAILABLE_DOMAINS


# Initialize LLM for grading (using GPT-3.5-turbo for speed/cost efficiency)
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0.0,
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================================
# Question Router
# ============================================================================
router_prompt = PromptTemplate(
    template="""You are an expert at classifying research questions to appropriate domain specialists.

Analyze the following research question and determine which domain(s) should handle it.

Available domains:
- statistics: Statistical methodology, inference, machine learning theory, causal methods
- biology: Biological sciences, molecular biology, genetics, ecology, neurobiology
- psychology: Psychological research, cognitive science, social psychology, clinical psychology
- philosophy: Philosophical inquiry, ethics, epistemology, philosophy of science
- psychiatry: Psychiatric research, mental disorders, psychopharmacology, clinical treatments
- applications: Real-world use cases, industry implementations, practical applications
- product_manager: Product strategy, user needs, market fit, research-to-product translation
- writing: Documentation creation, PRDs, research papers, technical reports, white papers, academic manuscripts

Guidelines:
- Most questions have ONE primary domain
- Use secondary_domains for cross-disciplinary questions (e.g., "causal inference in psychiatric trials" = statistics + psychiatry)
- Set needs_web_search to true for questions about recent developments, specific papers, or current state-of-the-art
- applications domain should be included when the question asks about practical use, industry examples, or real-world implementations
- product_manager domain should be included when asking about product strategy, user requirements, market opportunities, or how to productize research
- writing domain should be included when the question involves creating documentation, writing PRDs, research papers, technical reports, or any formal written output
- For full research-to-product pipeline questions, include: domain expert + applications + product_manager
- For comprehensive documentation workflows, include: domain expert + product_manager + writing

Question: {question}

Output a JSON object with this exact structure:
{{
    "primary_domain": "one of: statistics, biology, psychology, philosophy, psychiatry, applications, product_manager, writing",
    "secondary_domains": ["list of additional relevant domains, can be empty"],
    "needs_web_search": true or false,
    "reasoning": "brief explanation of classification"
}}""",
    input_variables=["question"]
)

question_router = router_prompt | llm | JsonOutputParser()


# ============================================================================
# Hallucination Grader
# ============================================================================
hallucination_prompt = PromptTemplate(
    template="""You are a grader assessing whether a response is grounded in the provided source documents.

Your task is to check if the claims made in the response are supported by the sources.

Source Documents:
{documents}

Response to evaluate:
{generation}

Evaluation criteria:
1. Are factual claims in the response supported by the source documents?
2. Does the response avoid making up information not in the sources?
3. Are citations/references accurate?

If the response makes reasonable inferences or general knowledge statements that don't contradict sources, that's acceptable.
Only flag as not grounded if there are clear fabrications or unsupported specific claims.

Output a JSON object with this exact structure:
{{
    "score": "yes" if response is grounded, "no" if not grounded,
    "unsupported_claims": ["list of specific claims that are not supported, if any"],
    "reasoning": "brief explanation"
}}""",
    input_variables=["documents", "generation"]
)

hallucination_grader = hallucination_prompt | llm | JsonOutputParser()


# ============================================================================
# Answer Grader
# ============================================================================
answer_prompt = PromptTemplate(
    template="""You are a grader assessing whether a response adequately addresses the user's question.

Question: {question}

Response: {generation}

Evaluation criteria:
1. Does the response directly address what was asked?
2. Is the response complete enough to be useful?
3. Does it provide actionable information or clear explanations?

A response doesn't need to be exhaustive, but should meaningfully address the core of the question.

Output a JSON object with this exact structure:
{{
    "score": "yes" if response adequately addresses the question, "no" otherwise,
    "missing_aspects": ["list of aspects the response should have covered but didn't"],
    "reasoning": "brief explanation"
}}""",
    input_variables=["question", "generation"]
)

answer_grader = answer_prompt | llm | JsonOutputParser()


# ============================================================================
# Document Relevance Grader
# ============================================================================
relevance_prompt = PromptTemplate(
    template="""You are a grader assessing the relevance of a retrieved document to a research question.

Question: {question}

Document content:
{document}

Evaluate how relevant this document is to answering the question.

Output a JSON object with this exact structure:
{{
    "score": integer from 0 to 100 (0=completely irrelevant, 100=highly relevant),
    "reasoning": "brief explanation of relevance"
}}""",
    input_variables=["question", "document"]
)

relevance_grader = relevance_prompt | llm | JsonOutputParser()


# ============================================================================
# Query Refinement
# ============================================================================
refine_prompt = PromptTemplate(
    template="""The previous response to a research question was inadequate.

Original question: {question}

Previous response: {generation}

Issues identified: {issues}

Generate an improved, more specific search query that would help find better information to answer the original question.

Output a JSON object with this exact structure:
{{
    "refined_query": "improved search query",
    "focus_areas": ["list of specific aspects to focus on"],
    "reasoning": "why this refinement should help"
}}""",
    input_variables=["question", "generation", "issues"]
)

query_refiner = refine_prompt | llm | JsonOutputParser()


# ============================================================================
# Response Synthesizer
# ============================================================================
synthesis_prompt = PromptTemplate(
    template="""You are synthesizing responses from multiple domain experts into a coherent answer.

Original question: {question}

Expert responses:
{agent_responses}

Web search results (if any):
{web_results}

Create a unified response that:
1. Integrates insights from all experts coherently
2. Resolves any contradictions between experts
3. Attributes key insights to their source domain
4. Maintains academic rigor while being accessible
5. Includes relevant citations and sources

Output a comprehensive, well-structured response that addresses the original question using all available information.""",
    input_variables=["question", "agent_responses", "web_results"]
)

response_synthesizer = synthesis_prompt | llm
