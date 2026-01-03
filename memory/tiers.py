"""Three-tier memory system: Working, Long-term, Episodic."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
import json
import os

from .types import (
    MemoryItem, EpisodicTrace, MemoryCategory, MemoryScope,
    MemoryStatus, DO_NOT_STORE_PATTERNS
)


@dataclass
class WorkingContext:
    """
    Tier 1: Ephemeral working context.

    - Current task state, latest user constraints, immediate tool outputs
    - Strict size budget; always overwritten
    - Never store raw long logs - store pointers + structured deltas
    """
    max_items: int = 20
    max_tokens_estimate: int = 4000

    _items: deque = field(default_factory=lambda: deque(maxlen=20))
    _current_task: Optional[str] = None
    _user_constraints: List[str] = field(default_factory=list)
    _tool_outputs: deque = field(default_factory=lambda: deque(maxlen=5))

    def add(self, content: str, source: str = "context") -> None:
        """Add item to working context, respecting size budget."""
        # Truncate if too long
        if len(content) > 500:
            content = content[:500] + "... [truncated, see episodic trace]"

        self._items.append({
            "content": content,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        })

    def set_task(self, task: str) -> None:
        """Set current task focus."""
        self._current_task = task

    def add_constraint(self, constraint: str) -> None:
        """Add user constraint (limit to last 5)."""
        self._user_constraints.append(constraint)
        if len(self._user_constraints) > 5:
            self._user_constraints = self._user_constraints[-5:]

    def add_tool_output(self, tool_name: str, output_summary: str) -> None:
        """Add summarized tool output (not raw)."""
        self._tool_outputs.append({
            "tool": tool_name,
            "summary": output_summary[:200],  # Max 200 chars
            "timestamp": datetime.now().isoformat(),
        })

    def get_context_window(self) -> Dict[str, Any]:
        """Get current working context for retrieval."""
        return {
            "current_task": self._current_task,
            "user_constraints": self._user_constraints,
            "recent_items": list(self._items)[-10:],
            "tool_outputs": list(self._tool_outputs),
        }

    def clear(self) -> None:
        """Clear working context (start new task)."""
        self._items.clear()
        self._current_task = None
        self._user_constraints = []
        self._tool_outputs.clear()


class LongTermMemory:
    """
    Tier 2: Stable, curated long-term memory.

    - Only store items that are: (a) durable, (b) user-approved or high-confidence, (c) frequently reused
    - Store in structured form: {claim, source, timestamp, confidence, scope, decay_policy}
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._store: Dict[str, MemoryItem] = {}
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load()

    def _should_store(self, content: str) -> bool:
        """Check if content should be stored (filter transient items)."""
        content_lower = content.lower()
        for pattern in DO_NOT_STORE_PATTERNS:
            if pattern in content_lower:
                return False
        return True

    def store(self, item: MemoryItem) -> bool:
        """
        Store a memory item if it passes filters.
        Returns True if stored, False if rejected.
        """
        if not self._should_store(item.content):
            return False

        # Check for duplicates
        for existing in self._store.values():
            if self._is_similar(item.content, existing.content):
                # Update existing instead of creating duplicate
                existing.access_count += 1
                existing.last_accessed = datetime.now()
                return False

        self._store[item.id] = item
        self._persist()
        return True

    def _is_similar(self, content1: str, content2: str, threshold: float = 0.8) -> bool:
        """Simple similarity check to avoid near-duplicates."""
        # Basic word overlap similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        return overlap > threshold

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID."""
        item = self._store.get(memory_id)
        if item:
            item.access_count += 1
            item.last_accessed = datetime.now()
        return item

    def query(
        self,
        category: Optional[MemoryCategory] = None,
        scope: Optional[MemoryScope] = None,
        status: Optional[MemoryStatus] = None,
        min_confidence: float = 0.0,
        max_age_hours: Optional[float] = None,
    ) -> List[MemoryItem]:
        """Query memories with filters."""
        results = []
        for item in self._store.values():
            if category and item.category != category:
                continue
            if scope and item.scope != scope:
                continue
            if status and item.status != status:
                continue
            if item.confidence < min_confidence:
                continue
            if max_age_hours and item.age_hours > max_age_hours:
                continue
            results.append(item)
        return results

    def mark_contested(self, memory_id: str, reason: str) -> None:
        """Mark a memory as contested due to conflicting evidence."""
        item = self._store.get(memory_id)
        if item:
            item.status = MemoryStatus.CONTESTED
            item.evidence_refs.append(f"contested: {reason}")
            self._persist()

    def supersede(self, old_id: str, new_item: MemoryItem) -> None:
        """Supersede an old memory with a new version."""
        old_item = self._store.get(old_id)
        if old_item:
            old_item.status = MemoryStatus.SUPERSEDED
            new_item.supersedes = old_id
            self._store[new_item.id] = new_item
            self._persist()

    def prune_expired(self) -> List[MemoryItem]:
        """Prune expired items, return them for archival."""
        expired = []
        for item in list(self._store.values()):
            if item.decay_factor < 0.25:  # Very decayed
                item.status = MemoryStatus.EXPIRED
                expired.append(item)
                del self._store[item.id]
        self._persist()
        return expired

    def _persist(self) -> None:
        """Persist to disk if path configured."""
        if self._persist_path:
            data = {k: v.to_dict() for k, v in self._store.items()}
            with open(self._persist_path, 'w') as f:
                json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load from disk."""
        try:
            with open(self._persist_path, 'r') as f:
                data = json.load(f)
            self._store = {k: MemoryItem.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, FileNotFoundError):
            self._store = {}


class EpisodicTraces:
    """
    Tier 3: Compressed event traces for debugging/replay.

    - Not retrieved by default
    - Retrieval only when diagnostics indicate inconsistency or missing context
    """

    def __init__(self, max_traces: int = 1000, persist_path: Optional[str] = None):
        self._traces: deque = deque(maxlen=max_traces)
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load()

    def record(self, event_type: str, summary: str, metadata: Optional[Dict] = None) -> str:
        """Record a compressed event trace."""
        import hashlib
        trace_id = hashlib.sha256(
            f"{event_type}{summary}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        trace = EpisodicTrace(
            trace_id=trace_id,
            event_type=event_type,
            summary=summary[:300],  # Compress
            metadata=metadata or {},
        )
        self._traces.append(trace)
        self._persist()
        return trace_id

    def get_recent(self, n: int = 10, event_type: Optional[str] = None) -> List[EpisodicTrace]:
        """Get recent traces, optionally filtered by type."""
        traces = list(self._traces)
        if event_type:
            traces = [t for t in traces if t.event_type == event_type]
        return traces[-n:]

    def diagnose(self, keyword: str) -> List[EpisodicTrace]:
        """Search traces for diagnostic purposes."""
        return [
            t for t in self._traces
            if keyword.lower() in t.summary.lower()
        ]

    def _persist(self) -> None:
        if self._persist_path:
            data = [t.to_dict() for t in self._traces]
            with open(self._persist_path, 'w') as f:
                json.dump(data, f)

    def _load(self) -> None:
        try:
            with open(self._persist_path, 'r') as f:
                data = json.load(f)
            for item in data:
                trace = EpisodicTrace(
                    trace_id=item["trace_id"],
                    event_type=item["event_type"],
                    summary=item["summary"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    metadata=item.get("metadata", {}),
                )
                self._traces.append(trace)
        except (json.JSONDecodeError, FileNotFoundError):
            pass


@dataclass
class ThreeTierMemory:
    """
    Unified three-tier memory system.

    Provides a single interface to all memory tiers with appropriate
    routing based on item characteristics.
    """
    working: WorkingContext = field(default_factory=WorkingContext)
    long_term: LongTermMemory = field(default_factory=LongTermMemory)
    episodic: EpisodicTraces = field(default_factory=EpisodicTraces)

    def add_working(self, content: str, source: str = "context") -> None:
        """Add to working context."""
        self.working.add(content, source)

    def store_long_term(
        self,
        content: str,
        category: MemoryCategory,
        source: str,
        confidence: float = 0.8,
        scope: MemoryScope = MemoryScope.PROJECT,
        evidence_refs: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Store to long-term memory. Returns ID if stored, None if rejected."""
        item = MemoryItem(
            content=content,
            category=category,
            source=source,
            confidence=confidence,
            scope=scope,
            evidence_refs=evidence_refs or [],
        )
        if self.long_term.store(item):
            return item.id
        return None

    def record_event(self, event_type: str, summary: str, metadata: Optional[Dict] = None) -> str:
        """Record an episodic trace."""
        return self.episodic.record(event_type, summary, metadata)

    def get_context_for_retrieval(self) -> Dict[str, Any]:
        """Get combined context for retrieval decisions."""
        return {
            "working": self.working.get_context_window(),
            "active_memories": len(self.long_term.query(status=MemoryStatus.ACTIVE)),
            "recent_traces": len(self.episodic.get_recent(10)),
        }
