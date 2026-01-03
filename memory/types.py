"""Memory item types and enums for the context-rot prevention system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import hashlib


class MemoryScope(Enum):
    """Scope of a memory item - determines visibility and persistence."""
    SYSTEM = "system"       # Agent-wide, stable
    PROJECT = "project"     # Current project/session
    USER = "user"           # User-specific preferences
    EPHEMERAL = "ephemeral" # Task-specific, short-lived


class MemoryStatus(Enum):
    """Status of a memory item."""
    ACTIVE = "active"
    CONTESTED = "contested"   # Contradicted by new evidence
    SUPERSEDED = "superseded" # Replaced by newer version
    EXPIRED = "expired"       # Past half-life, needs verification
    ARCHIVED = "archived"     # Moved to episodic traces


class MemoryCategory(Enum):
    """Category of memory for intent-conditioned retrieval."""
    FACTUAL = "factual"           # Verified facts, citations
    PROCEDURAL = "procedural"     # How-to knowledge, workflows
    CONTEXTUAL = "contextual"     # User preferences, constraints
    ENVIRONMENTAL = "environmental"  # API behavior, system state
    DECISION = "decision"         # Past decisions with rationale


# Half-life configurations (in hours)
HALF_LIFE_CONFIG = {
    MemoryCategory.FACTUAL: 168,        # 7 days
    MemoryCategory.PROCEDURAL: 336,     # 14 days
    MemoryCategory.CONTEXTUAL: 72,      # 3 days
    MemoryCategory.ENVIRONMENTAL: 24,   # 1 day
    MemoryCategory.DECISION: 48,        # 2 days
}


@dataclass
class MemoryItem:
    """
    A single memory item with metadata for decay and retrieval.

    Attributes:
        content: The actual memory content (claim, fact, decision, etc.)
        category: Type of memory for intent-conditioned retrieval
        scope: Visibility scope (system/project/user/ephemeral)
        source: Provenance (tool name, citation, user input)
        timestamp: When the memory was created
        confidence: Confidence score [0.0, 1.0]
        status: Current status of the memory
        half_life_hours: Custom half-life override (uses category default if None)
        evidence_refs: Pointers to supporting evidence (not full content)
        supersedes: ID of the memory this supersedes (if any)
        access_count: Number of times retrieved
        last_accessed: Last retrieval timestamp
    """
    content: str
    category: MemoryCategory
    scope: MemoryScope = MemoryScope.PROJECT
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.8
    status: MemoryStatus = MemoryStatus.ACTIVE
    half_life_hours: Optional[float] = None
    evidence_refs: List[str] = field(default_factory=list)
    supersedes: Optional[str] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    _id: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        if self._id is None:
            # Generate deterministic ID from content + timestamp
            hash_input = f"{self.content}{self.timestamp.isoformat()}"
            self._id = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    @property
    def id(self) -> str:
        return self._id

    @property
    def effective_half_life(self) -> float:
        """Get effective half-life in hours."""
        if self.half_life_hours is not None:
            return self.half_life_hours
        return HALF_LIFE_CONFIG.get(self.category, 72)

    @property
    def age_hours(self) -> float:
        """Age of the memory in hours."""
        delta = datetime.now() - self.timestamp
        return delta.total_seconds() / 3600

    @property
    def decay_factor(self) -> float:
        """
        Decay factor based on exponential decay: e^(-lambda * t)
        Returns value between 0 and 1.
        """
        import math
        lambda_decay = 0.693 / self.effective_half_life  # ln(2) / half_life
        return math.exp(-lambda_decay * self.age_hours)

    @property
    def needs_verification(self) -> bool:
        """Whether the memory should be verified before use."""
        return (
            self.status == MemoryStatus.EXPIRED or
            self.decay_factor < 0.5 or
            self.status == MemoryStatus.CONTESTED
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self._id,
            "content": self.content,
            "category": self.category.value,
            "scope": self.scope.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "status": self.status.value,
            "half_life_hours": self.half_life_hours,
            "evidence_refs": self.evidence_refs,
            "supersedes": self.supersedes,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        """Deserialize from dictionary."""
        return cls(
            content=data["content"],
            category=MemoryCategory(data["category"]),
            scope=MemoryScope(data["scope"]),
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            confidence=data["confidence"],
            status=MemoryStatus(data["status"]),
            half_life_hours=data.get("half_life_hours"),
            evidence_refs=data.get("evidence_refs", []),
            supersedes=data.get("supersedes"),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            _id=data["id"],
        )


@dataclass
class EpisodicTrace:
    """
    Compressed event trace for debugging/replay.
    Not retrieved by default - only for diagnostics.
    """
    trace_id: str
    event_type: str  # "tool_call", "decision", "error", "state_change"
    summary: str     # Compressed summary, not raw content
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "event_type": self.event_type,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# Items that should NEVER be stored
DO_NOT_STORE_PATTERNS = [
    "intermediate chain-of-thought",
    "speculative reasoning",
    "unverified web claim",
    "one-off tool error",
    "transient preference",
]
