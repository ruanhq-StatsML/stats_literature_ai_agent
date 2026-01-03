"""
Explicit Agent State Management.

Maintains a separate "agent state" object distinct from memory:
- Goals, constraints, assumptions, open questions
- Environment flags and versioned policies
- This state is what you UPDATE, while memory is what you RETRIEVE
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import json
import hashlib


class PolicyVersion(Enum):
    """Versioned policy states for adaptive behavior."""
    NORMAL = "normal"
    CONSERVATIVE = "conservative"  # Tighter retrieval, more verification
    AGGRESSIVE = "aggressive"       # More exploration, less verification


@dataclass
class Assumption:
    """An explicit assumption with confidence and source."""
    content: str
    confidence: float  # 0.0 to 1.0
    source: str
    created: datetime = field(default_factory=datetime.now)
    verified: bool = False

    def __hash__(self):
        return hash(self.content)


@dataclass
class OpenQuestion:
    """An unresolved question that may need user clarification."""
    question: str
    context: str
    priority: int = 1  # 1=low, 2=medium, 3=high
    created: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class AgentState:
    """
    Explicit agent state object - separate from memory.

    This is what the agent UPDATES to track current context.
    Memory is what the agent RETRIEVES for knowledge.

    Attributes:
        goals: Current active goals (ordered by priority)
        constraints: Hard constraints that must be respected
        assumptions: Working assumptions with confidence
        open_questions: Questions needing resolution
        environment_flags: Current environment state
        policy_version: Current policy mode
        focus_window: Last N key decisions for long tasks
        version: State version for change tracking
    """
    # Core state
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)
    open_questions: List[OpenQuestion] = field(default_factory=list)

    # Environment and policy
    environment_flags: Dict[str, Any] = field(default_factory=dict)
    policy_version: PolicyVersion = PolicyVersion.NORMAL

    # Focus window for long tasks (rotating)
    focus_window: List[Dict[str, Any]] = field(default_factory=list)
    focus_window_size: int = 10

    # Versioning
    version: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    # Quality signals for drift detection
    _user_corrections: int = 0
    _tool_retries: int = 0
    _verification_failures: int = 0

    def set_goal(self, goal: str, priority: int = 0) -> None:
        """Set a goal at given priority (0 = highest)."""
        if goal not in self.goals:
            self.goals.insert(priority, goal)
            self._bump_version()

    def complete_goal(self, goal: str) -> bool:
        """Mark a goal as completed. Returns True if goal existed."""
        if goal in self.goals:
            self.goals.remove(goal)
            self._bump_version()
            return True
        return False

    def add_constraint(self, constraint: str) -> None:
        """Add a hard constraint."""
        if constraint not in self.constraints:
            self.constraints.append(constraint)
            self._bump_version()

    def add_assumption(
        self,
        content: str,
        confidence: float = 0.7,
        source: str = "inferred"
    ) -> None:
        """Add a working assumption."""
        assumption = Assumption(content=content, confidence=confidence, source=source)
        # Check for duplicate
        for existing in self.assumptions:
            if existing.content == content:
                existing.confidence = max(existing.confidence, confidence)
                return
        self.assumptions.append(assumption)
        self._bump_version()

    def verify_assumption(self, content: str) -> bool:
        """Mark an assumption as verified."""
        for assumption in self.assumptions:
            if assumption.content == content:
                assumption.verified = True
                self._bump_version()
                return True
        return False

    def invalidate_assumption(self, content: str) -> bool:
        """Remove an invalidated assumption."""
        for i, assumption in enumerate(self.assumptions):
            if assumption.content == content:
                self.assumptions.pop(i)
                self._bump_version()
                return True
        return False

    def add_question(
        self,
        question: str,
        context: str = "",
        priority: int = 2
    ) -> None:
        """Add an open question."""
        q = OpenQuestion(question=question, context=context, priority=priority)
        self.open_questions.append(q)
        self._bump_version()

    def resolve_question(self, question: str, resolution: str) -> bool:
        """Resolve an open question."""
        for q in self.open_questions:
            if q.question == question:
                q.resolved = True
                q.resolution = resolution
                self._bump_version()
                return True
        return False

    def set_env_flag(self, key: str, value: Any) -> None:
        """Set an environment flag."""
        self.environment_flags[key] = value
        self._bump_version()

    def add_to_focus(self, decision: str, rationale: str) -> None:
        """Add a key decision to the rotating focus window."""
        self.focus_window.append({
            "decision": decision,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat(),
        })
        # Rotate if exceeds size
        if len(self.focus_window) > self.focus_window_size:
            self.focus_window = self.focus_window[-self.focus_window_size:]
        self._bump_version()

    def record_quality_signal(self, signal_type: str) -> None:
        """Record a quality signal for drift detection."""
        if signal_type == "user_correction":
            self._user_corrections += 1
        elif signal_type == "tool_retry":
            self._tool_retries += 1
        elif signal_type == "verification_failure":
            self._verification_failures += 1
        self._check_drift()

    def _check_drift(self) -> None:
        """Check if quality signals indicate drift - adjust policy."""
        total_issues = self._user_corrections + self._tool_retries + self._verification_failures
        if total_issues >= 3 and self.policy_version != PolicyVersion.CONSERVATIVE:
            self.policy_version = PolicyVersion.CONSERVATIVE
            self._bump_version()

    def reset_quality_signals(self) -> None:
        """Reset quality signals (after successful task completion)."""
        self._user_corrections = 0
        self._tool_retries = 0
        self._verification_failures = 0
        if self.policy_version == PolicyVersion.CONSERVATIVE:
            self.policy_version = PolicyVersion.NORMAL
            self._bump_version()

    def _bump_version(self) -> None:
        """Increment version and update timestamp."""
        self.version += 1
        self.last_updated = datetime.now()

    def consolidate(self) -> Dict[str, Any]:
        """
        Run state consolidation pass:
        - Prune resolved items
        - Promote durable facts
        - Expire stale assumptions
        Returns summary of changes.
        """
        changes = {"pruned": 0, "expired": 0}

        # Prune resolved questions
        self.open_questions = [q for q in self.open_questions if not q.resolved]
        changes["pruned"] = len([q for q in self.open_questions if q.resolved])

        # Expire old unverified assumptions (>24h)
        now = datetime.now()
        expired = []
        for assumption in self.assumptions:
            age_hours = (now - assumption.created).total_seconds() / 3600
            if not assumption.verified and age_hours > 24:
                expired.append(assumption)
        for a in expired:
            self.assumptions.remove(a)
        changes["expired"] = len(expired)

        self._bump_version()
        return changes

    def get_summary(self) -> str:
        """Get a structured summary of current state."""
        lines = [
            f"=== Agent State (v{self.version}) ===",
            f"Policy: {self.policy_version.value}",
            f"Goals: {len(self.goals)}",
            f"Constraints: {len(self.constraints)}",
            f"Assumptions: {len(self.assumptions)} ({sum(1 for a in self.assumptions if a.verified)} verified)",
            f"Open Questions: {len([q for q in self.open_questions if not q.resolved])}",
            f"Focus Window: {len(self.focus_window)} decisions",
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "goals": self.goals,
            "constraints": self.constraints,
            "assumptions": [
                {"content": a.content, "confidence": a.confidence, "source": a.source, "verified": a.verified}
                for a in self.assumptions
            ],
            "open_questions": [
                {"question": q.question, "context": q.context, "priority": q.priority, "resolved": q.resolved}
                for q in self.open_questions
            ],
            "environment_flags": self.environment_flags,
            "policy_version": self.policy_version.value,
            "focus_window": self.focus_window,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Deserialize from dictionary."""
        state = cls()
        state.goals = data.get("goals", [])
        state.constraints = data.get("constraints", [])
        state.assumptions = [
            Assumption(content=a["content"], confidence=a["confidence"], source=a["source"], verified=a["verified"])
            for a in data.get("assumptions", [])
        ]
        state.open_questions = [
            OpenQuestion(
                question=q["question"], context=q["context"],
                priority=q["priority"], resolved=q["resolved"]
            )
            for q in data.get("open_questions", [])
        ]
        state.environment_flags = data.get("environment_flags", {})
        state.policy_version = PolicyVersion(data.get("policy_version", "normal"))
        state.focus_window = data.get("focus_window", [])
        state.version = data.get("version", 0)
        if data.get("last_updated"):
            state.last_updated = datetime.fromisoformat(data["last_updated"])
        return state
