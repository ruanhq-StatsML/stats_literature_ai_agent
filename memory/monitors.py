"""
Drift Monitors and Contradiction Detection.

Adaptive procedures to prevent context rot:
- Decay + refresh (time-aware memory)
- Contradiction detection + reconciliation
- Summary discipline (anti-drift summarization)
- Focus window for long tasks
- Drift monitors (online performance triggers)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from collections import deque
from enum import Enum
import re

from .types import MemoryItem, MemoryCategory, MemoryStatus
from .tiers import ThreeTierMemory, LongTermMemory
from .agent_state import AgentState, PolicyVersion


class DriftSignal(Enum):
    """Types of drift signals to monitor."""
    USER_CORRECTION = "user_correction"
    TOOL_RETRY = "tool_retry"
    VERIFICATION_FAILURE = "verification_failure"
    CONTRADICTION = "contradiction"
    HALLUCINATION_FLAG = "hallucination_flag"
    LOOP_DETECTED = "loop_detected"


@dataclass
class QualitySignal:
    """A single quality signal observation."""
    signal_type: DriftSignal
    timestamp: datetime = field(default_factory=datetime.now)
    details: str = ""
    severity: int = 1  # 1-3


class ContradictionDetector:
    """
    Lightweight contradiction detection.

    Checks if new evidence conflicts with stored memories.
    Marks conflicting items as "contested" and either:
    - Supersedes with new version (keeps both with status)
    - Demotes confidence until verified
    """

    def __init__(self, memory: LongTermMemory):
        self.memory = memory
        # Simple negation patterns
        self.negation_patterns = [
            (r"(\w+) is not", r"\1 is"),
            (r"(\w+) are not", r"\1 are"),
            (r"(\w+) cannot", r"\1 can"),
            (r"(\w+) does not", r"\1 does"),
            (r"(\w+) will not", r"\1 will"),
            (r"no (\w+)", r"\1"),
            (r"never (\w+)", r"always \1"),
        ]

    def check_contradiction(
        self,
        new_content: str,
        category: Optional[MemoryCategory] = None,
    ) -> List[Tuple[MemoryItem, str]]:
        """
        Check if new content contradicts existing memories.

        Returns list of (contradicted_item, reason) tuples.
        """
        contradictions = []

        # Get relevant memories to check
        filters = {"status": MemoryStatus.ACTIVE}
        if category:
            filters["category"] = category

        candidates = self.memory.query(**filters)

        for item in candidates:
            contradiction = self._detect_contradiction(new_content, item.content)
            if contradiction:
                contradictions.append((item, contradiction))

        return contradictions

    def _detect_contradiction(self, new_content: str, old_content: str) -> Optional[str]:
        """
        Detect if two pieces of content contradict each other.

        Uses simple heuristics:
        - Negation patterns
        - Numeric value conflicts
        - Keyword conflicts
        """
        new_lower = new_content.lower()
        old_lower = old_content.lower()

        # Check negation patterns
        for neg_pattern, pos_pattern in self.negation_patterns:
            neg_match = re.search(neg_pattern, new_lower)
            if neg_match:
                # Check if old content has the positive form
                pos_form = re.sub(neg_pattern, pos_pattern, new_lower)
                if self._content_overlap(pos_form, old_lower) > 0.5:
                    return f"negation conflict: '{neg_match.group()}'"

        # Check numeric conflicts (e.g., "X = 5" vs "X = 10")
        new_numbers = self._extract_numbers(new_lower)
        old_numbers = self._extract_numbers(old_lower)
        for key in new_numbers.keys() & old_numbers.keys():
            if new_numbers[key] != old_numbers[key]:
                return f"numeric conflict for '{key}': {new_numbers[key]} vs {old_numbers[key]}"

        # Check for explicit contradiction keywords
        contradiction_phrases = [
            ("was", "was not"),
            ("is", "is not"),
            ("can", "cannot"),
            ("true", "false"),
            ("correct", "incorrect"),
            ("valid", "invalid"),
        ]
        for pos, neg in contradiction_phrases:
            if pos in new_lower and neg in old_lower:
                # Check if they're about the same subject
                if self._content_overlap(new_lower, old_lower) > 0.3:
                    return f"potential conflict: '{pos}' vs '{neg}'"

        return None

    def _content_overlap(self, content1: str, content2: str) -> float:
        """Simple word overlap similarity."""
        words1 = set(content1.split())
        words2 = set(content2.split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / max(len(words1), len(words2))

    def _extract_numbers(self, text: str) -> Dict[str, float]:
        """Extract number associations from text."""
        # Pattern: word/phrase = number or word/phrase is number
        patterns = [
            r"(\w+)\s*[=:]\s*([\d.]+)",
            r"(\w+)\s+is\s+([\d.]+)",
            r"(\w+)\s+are\s+([\d.]+)",
        ]
        numbers = {}
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                try:
                    numbers[match.group(1)] = float(match.group(2))
                except ValueError:
                    pass
        return numbers

    def reconcile(
        self,
        item: MemoryItem,
        new_content: str,
        new_source: str,
        supersede: bool = False,
    ) -> MemoryItem:
        """
        Reconcile a contradiction.

        Either supersedes the old memory or marks it contested.
        """
        if supersede:
            new_item = MemoryItem(
                content=new_content,
                category=item.category,
                source=new_source,
                confidence=0.8,
                scope=item.scope,
                supersedes=item.id,
            )
            self.memory.supersede(item.id, new_item)
            return new_item
        else:
            self.memory.mark_contested(item.id, f"Contested by: {new_content[:100]}")
            item.confidence *= 0.5  # Demote confidence
            return item


class DriftMonitor:
    """
    Online drift detection with adaptive response.

    Monitors quality signals and triggers policy changes when:
    - User corrections increase
    - Tool call loops detected
    - Verification failures rise
    """

    def __init__(
        self,
        state: AgentState,
        window_size: int = 20,
        alert_threshold: int = 3,
    ):
        self.state = state
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        self._signal_window: deque = deque(maxlen=window_size)
        self._last_check = datetime.now()

    def record_signal(self, signal: DriftSignal, details: str = "", severity: int = 1) -> None:
        """Record a quality signal."""
        self._signal_window.append(QualitySignal(
            signal_type=signal,
            details=details,
            severity=severity,
        ))
        self._check_drift()

    def _check_drift(self) -> Optional[Dict[str, Any]]:
        """Check if drift threshold is exceeded."""
        if len(self._signal_window) < 5:
            return None

        # Count signals by type
        signal_counts = {}
        total_severity = 0
        for sig in self._signal_window:
            signal_counts[sig.signal_type] = signal_counts.get(sig.signal_type, 0) + 1
            total_severity += sig.severity

        # Check thresholds
        drift_detected = False
        reasons = []

        if signal_counts.get(DriftSignal.USER_CORRECTION, 0) >= 2:
            drift_detected = True
            reasons.append("multiple user corrections")

        if signal_counts.get(DriftSignal.LOOP_DETECTED, 0) >= 1:
            drift_detected = True
            reasons.append("tool loop detected")

        if total_severity >= self.alert_threshold * 2:
            drift_detected = True
            reasons.append(f"high severity ({total_severity})")

        if signal_counts.get(DriftSignal.CONTRADICTION, 0) >= 2:
            drift_detected = True
            reasons.append("multiple contradictions")

        if drift_detected:
            return self._trigger_drift_response(reasons)

        return None

    def _trigger_drift_response(self, reasons: List[str]) -> Dict[str, Any]:
        """Trigger adaptive response to detected drift."""
        response = {
            "timestamp": datetime.now().isoformat(),
            "reasons": reasons,
            "actions": [],
        }

        # Switch to conservative policy
        if self.state.policy_version != PolicyVersion.CONSERVATIVE:
            self.state.policy_version = PolicyVersion.CONSERVATIVE
            response["actions"].append("switched to conservative policy")

        # Record quality signals in state
        for reason in reasons:
            if "user correction" in reason.lower():
                self.state.record_quality_signal("user_correction")
            elif "loop" in reason.lower():
                self.state.record_quality_signal("tool_retry")

        response["actions"].append("state re-derivation recommended")

        return response

    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health summary."""
        signal_counts = {}
        for sig in self._signal_window:
            signal_counts[sig.signal_type.value] = signal_counts.get(sig.signal_type.value, 0) + 1

        total_severity = sum(s.severity for s in self._signal_window)

        return {
            "window_size": len(self._signal_window),
            "signal_counts": signal_counts,
            "total_severity": total_severity,
            "policy": self.state.policy_version.value,
            "health": "healthy" if total_severity < self.alert_threshold else "degraded",
        }

    def reset(self) -> None:
        """Reset the monitor (after successful task completion)."""
        self._signal_window.clear()
        self.state.reset_quality_signals()


class SummaryDiscipline:
    """
    Anti-drift summarization.

    Instead of repeatedly summarizing summaries:
    - Store atomic facts + pointers to original evidence
    - Regenerate fresh summary from atomic facts when needed
    - Use structured templates
    """

    SUMMARY_TEMPLATE = """=== {title} ===
Goal: {goal}
Constraints: {constraints}
Key Decisions: {decisions}
Evidence: {evidence}
Open Questions: {questions}
"""

    def __init__(self, state: AgentState, memory: ThreeTierMemory):
        self.state = state
        self.memory = memory

    def generate_fresh_summary(self, title: str = "Current State") -> str:
        """
        Generate a fresh summary from atomic facts.

        Does NOT summarize existing summaries - always from source.
        """
        # Get atomic facts from state
        goal = self.state.goals[0] if self.state.goals else "None defined"
        constraints = "; ".join(self.state.constraints[:5]) if self.state.constraints else "None"

        # Get key decisions from focus window
        decisions = []
        for item in self.state.focus_window[-5:]:
            decisions.append(f"- {item['decision']}")
        decisions_str = "\n".join(decisions) if decisions else "None recorded"

        # Get evidence from recent memories
        recent = self.memory.long_term.query(
            status=MemoryStatus.ACTIVE,
            min_confidence=0.7,
        )
        evidence = []
        for item in sorted(recent, key=lambda x: x.timestamp, reverse=True)[:5]:
            evidence.append(f"- [{item.category.value}] {item.content[:100]}")
        evidence_str = "\n".join(evidence) if evidence else "None stored"

        # Get open questions
        open_qs = [q for q in self.state.open_questions if not q.resolved]
        questions = []
        for q in open_qs[:3]:
            questions.append(f"- {q.question}")
        questions_str = "\n".join(questions) if questions else "None"

        return self.SUMMARY_TEMPLATE.format(
            title=title,
            goal=goal,
            constraints=constraints,
            decisions=decisions_str,
            evidence=evidence_str,
            questions=questions_str,
        )

    def extract_atomic_facts(self, text: str) -> List[str]:
        """
        Extract atomic facts from text for storage.

        Breaks down compound statements into individual facts.
        """
        facts = []

        # Split by sentence
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # Skip meta-statements
            skip_patterns = ["I think", "maybe", "perhaps", "might be", "could be"]
            if any(p in sentence.lower() for p in skip_patterns):
                continue

            # Clean and add
            facts.append(sentence)

        return facts


class FocusWindowManager:
    """
    Manages the rotating focus window for long tasks.

    - Keeps only the last N key decisions + current objective
    - Archives the rest as episodic trace
    - Periodically runs state consolidation
    """

    def __init__(
        self,
        state: AgentState,
        memory: ThreeTierMemory,
        max_decisions: int = 10,
        consolidation_interval: int = 20,
    ):
        self.state = state
        self.memory = memory
        self.max_decisions = max_decisions
        self.consolidation_interval = consolidation_interval
        self._operation_count = 0

    def add_decision(self, decision: str, rationale: str) -> None:
        """Add a key decision to the focus window."""
        self.state.add_to_focus(decision, rationale)
        self._operation_count += 1

        # Check if consolidation needed
        if self._operation_count >= self.consolidation_interval:
            self.consolidate()

    def consolidate(self) -> Dict[str, Any]:
        """
        Run state consolidation pass:
        - Prune resolved items
        - Promote durable facts to long-term memory
        - Expire stale assumptions
        - Archive overflow to episodic traces
        """
        report = {
            "archived": 0,
            "promoted": 0,
            "expired": 0,
        }

        # Archive old focus window items
        if len(self.state.focus_window) > self.max_decisions:
            overflow = self.state.focus_window[:-self.max_decisions]
            self.state.focus_window = self.state.focus_window[-self.max_decisions:]

            for item in overflow:
                self.memory.episodic.record(
                    "decision_archived",
                    f"Decision: {item['decision']}",
                    {"rationale": item["rationale"], "timestamp": item["timestamp"]},
                )
                report["archived"] += 1

        # Promote frequently accessed, high-confidence assumptions to memory
        for assumption in list(self.state.assumptions):
            if assumption.verified and assumption.confidence >= 0.9:
                self.memory.store_long_term(
                    content=assumption.content,
                    category=MemoryCategory.FACTUAL,
                    source=assumption.source,
                    confidence=assumption.confidence,
                )
                report["promoted"] += 1

        # Run state consolidation
        state_changes = self.state.consolidate()
        report["expired"] = state_changes.get("expired", 0)

        # Prune expired long-term memories
        expired_memories = self.memory.long_term.prune_expired()
        for mem in expired_memories:
            self.memory.episodic.record(
                "memory_expired",
                f"Expired: {mem.content[:100]}",
                {"category": mem.category.value, "age_hours": mem.age_hours},
            )

        self._operation_count = 0
        return report
