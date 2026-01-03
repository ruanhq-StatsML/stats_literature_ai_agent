"""
Gated Retrieval System.

Retrieval that does not rot: "policy + gating"
- Intent-conditioned retrieval
- Relevance x reliability scoring
- Memory budget + diversity
- Verification triggers
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from .types import MemoryItem, MemoryCategory, MemoryScope, MemoryStatus
from .tiers import ThreeTierMemory
from .agent_state import AgentState, PolicyVersion


class RetrievalIntent(Enum):
    """Intent-conditioned retrieval modes."""
    PLANNING = "planning"           # Strategic decisions, past choices
    FACTUAL_QA = "factual_qa"       # Verified facts, citations
    TOOL_ORCHESTRATION = "tool_orchestration"  # Procedural, environmental
    CONSTRAINT_CHECK = "constraint_check"       # User constraints, policies
    CONTEXT_RECALL = "context_recall"          # Recent context, working memory


# Intent -> Category mapping for filtering
INTENT_CATEGORY_MAP = {
    RetrievalIntent.PLANNING: [MemoryCategory.DECISION, MemoryCategory.CONTEXTUAL],
    RetrievalIntent.FACTUAL_QA: [MemoryCategory.FACTUAL],
    RetrievalIntent.TOOL_ORCHESTRATION: [MemoryCategory.PROCEDURAL, MemoryCategory.ENVIRONMENTAL],
    RetrievalIntent.CONSTRAINT_CHECK: [MemoryCategory.CONTEXTUAL],
    RetrievalIntent.CONTEXT_RECALL: [MemoryCategory.CONTEXTUAL, MemoryCategory.DECISION],
}


@dataclass
class ScoredMemory:
    """Memory item with retrieval score."""
    item: MemoryItem
    score: float
    needs_verification: bool = False
    verification_reason: Optional[str] = None


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    items: List[ScoredMemory]
    working_context: Dict[str, Any]
    verification_required: List[ScoredMemory]
    budget_exceeded: bool = False


class GatedRetrieval:
    """
    Gated retrieval system with policy-aware scoring.

    Avoids "top-k similarity" alone. Uses:
    - Intent-conditioned retrieval
    - Relevance x reliability scoring
    - Memory budget + diversity
    - Verification gating
    """

    def __init__(
        self,
        memory: ThreeTierMemory,
        state: AgentState,
        max_tokens: int = 2000,
        max_items: int = 10,
    ):
        self.memory = memory
        self.state = state
        self.max_tokens = max_tokens
        self.max_items = max_items

    def retrieve(
        self,
        intent: RetrievalIntent,
        query: Optional[str] = None,
        min_confidence: Optional[float] = None,
        include_working: bool = True,
    ) -> RetrievalResult:
        """
        Retrieve memories based on intent and policy.

        Args:
            intent: The retrieval intent (determines category filter)
            query: Optional query for relevance scoring
            min_confidence: Minimum confidence threshold (policy-adjusted)
            include_working: Whether to include working context

        Returns:
            RetrievalResult with scored items and verification requirements
        """
        # Adjust thresholds based on policy
        confidence_threshold = self._get_confidence_threshold(min_confidence)
        verification_threshold = self._get_verification_threshold()

        # Get category filter from intent
        categories = INTENT_CATEGORY_MAP.get(intent, list(MemoryCategory))

        # Query long-term memory
        candidates = []
        for category in categories:
            items = self.memory.long_term.query(
                category=category,
                status=MemoryStatus.ACTIVE,
                min_confidence=confidence_threshold,
            )
            candidates.extend(items)

        # Score candidates
        scored = []
        for item in candidates:
            score = self._compute_score(item, query, intent)
            needs_verify = (
                item.needs_verification or
                score < verification_threshold or
                item.decay_factor < 0.5
            )
            verify_reason = None
            if needs_verify:
                verify_reason = self._get_verification_reason(item)

            scored.append(ScoredMemory(
                item=item,
                score=score,
                needs_verification=needs_verify,
                verification_reason=verify_reason,
            ))

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)

        # Apply diversity filter (avoid near-duplicates)
        diverse = self._apply_diversity(scored)

        # Apply budget constraints
        final, budget_exceeded = self._apply_budget(diverse)

        # Separate items needing verification
        verification_required = [s for s in final if s.needs_verification]

        # Get working context if requested
        working_ctx = {}
        if include_working:
            working_ctx = self.memory.working.get_context_window()

        return RetrievalResult(
            items=final,
            working_context=working_ctx,
            verification_required=verification_required,
            budget_exceeded=budget_exceeded,
        )

    def _compute_score(
        self,
        item: MemoryItem,
        query: Optional[str],
        intent: RetrievalIntent,
    ) -> float:
        """
        Compute retrieval score: relevance x reliability.

        Components:
        - Semantic relevance (simple word overlap if query provided)
        - Recency (decay factor)
        - Source quality (based on source type)
        - Confidence
        - Scope match
        """
        score = 0.0

        # Base confidence score
        score += item.confidence * 0.3

        # Recency (decay factor)
        score += item.decay_factor * 0.25

        # Source quality
        source_scores = {
            "user_input": 1.0,
            "verified_tool": 0.9,
            "web_search": 0.6,
            "inferred": 0.5,
            "unknown": 0.3,
        }
        source_type = item.source.split(":")[0] if ":" in item.source else item.source
        score += source_scores.get(source_type, 0.5) * 0.2

        # Access frequency (popular items are likely useful)
        access_score = min(item.access_count / 10, 1.0)
        score += access_score * 0.1

        # Relevance to query (simple word overlap)
        if query:
            query_words = set(query.lower().split())
            content_words = set(item.content.lower().split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)
            score += overlap * 0.15

        return min(score, 1.0)

    def _get_confidence_threshold(self, override: Optional[float]) -> float:
        """Get confidence threshold based on policy."""
        if override is not None:
            return override

        policy_thresholds = {
            PolicyVersion.NORMAL: 0.5,
            PolicyVersion.CONSERVATIVE: 0.7,
            PolicyVersion.AGGRESSIVE: 0.3,
        }
        return policy_thresholds[self.state.policy_version]

    def _get_verification_threshold(self) -> float:
        """Get verification threshold based on policy."""
        policy_thresholds = {
            PolicyVersion.NORMAL: 0.6,
            PolicyVersion.CONSERVATIVE: 0.8,
            PolicyVersion.AGGRESSIVE: 0.4,
        }
        return policy_thresholds[self.state.policy_version]

    def _get_verification_reason(self, item: MemoryItem) -> str:
        """Get reason why verification is needed."""
        reasons = []
        if item.status == MemoryStatus.CONTESTED:
            reasons.append("contested by new evidence")
        if item.decay_factor < 0.5:
            reasons.append(f"aged ({item.age_hours:.0f}h old)")
        if item.confidence < 0.6:
            reasons.append(f"low confidence ({item.confidence:.2f})")
        if not item.evidence_refs:
            reasons.append("no evidence refs")
        return "; ".join(reasons) if reasons else "policy requirement"

    def _apply_diversity(self, scored: List[ScoredMemory]) -> List[ScoredMemory]:
        """Remove near-duplicate memories, keeping highest scored."""
        if len(scored) <= 1:
            return scored

        diverse = [scored[0]]
        for candidate in scored[1:]:
            is_duplicate = False
            for existing in diverse:
                similarity = self._content_similarity(
                    candidate.item.content,
                    existing.item.content
                )
                if similarity > 0.8:
                    is_duplicate = True
                    break
            if not is_duplicate:
                diverse.append(candidate)
        return diverse

    def _content_similarity(self, content1: str, content2: str) -> float:
        """Simple word overlap similarity."""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        if not words1 or not words2:
            return 0.0
        overlap = len(words1 & words2)
        return overlap / max(len(words1), len(words2))

    def _apply_budget(
        self,
        scored: List[ScoredMemory]
    ) -> Tuple[List[ScoredMemory], bool]:
        """Apply token and item budget constraints."""
        result = []
        total_tokens = 0
        budget_exceeded = False

        for item in scored[:self.max_items * 2]:  # Consider more than max
            item_tokens = len(item.item.content.split()) * 1.3  # Rough estimate
            if total_tokens + item_tokens <= self.max_tokens:
                result.append(item)
                total_tokens += item_tokens
            else:
                budget_exceeded = True

            if len(result) >= self.max_items:
                break

        return result, budget_exceeded


class VerificationGate:
    """
    Verification gate for memories that need freshness check.

    Triggers verification when:
    - Memory is past half-life
    - Status is contested
    - Policy requires verification
    """

    def __init__(self, state: AgentState):
        self.state = state

    def should_verify(self, item: MemoryItem) -> Tuple[bool, str]:
        """Check if memory should be verified before use."""
        # Always verify contested items
        if item.status == MemoryStatus.CONTESTED:
            return True, "contested"

        # Check decay
        if item.decay_factor < 0.5:
            return True, f"decayed ({item.decay_factor:.2f})"

        # Policy-based verification
        if self.state.policy_version == PolicyVersion.CONSERVATIVE:
            if item.confidence < 0.8:
                return True, "policy: conservative mode"
            if not item.evidence_refs:
                return True, "policy: no evidence"

        # Environmental items need frequent verification
        if item.category == MemoryCategory.ENVIRONMENTAL:
            if item.age_hours > 12:
                return True, "environmental: needs refresh"

        return False, ""

    def create_verification_prompt(self, item: MemoryItem) -> str:
        """Create a prompt for verifying a memory item."""
        return f"""Please verify the following information is still accurate:

"{item.content}"

Source: {item.source}
Last verified: {item.timestamp.strftime('%Y-%m-%d %H:%M')}
Age: {item.age_hours:.1f} hours

Please confirm if this is still valid, needs updating, or should be invalidated."""
