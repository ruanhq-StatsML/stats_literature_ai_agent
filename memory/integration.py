"""
Memory System Integration Layer.

Provides a unified, minimal-overhead interface for integrating the
context-rot prevention system with existing agents.

Design Principles:
1. Minimal intervention - agents can opt-in to memory features
2. Backward compatible - doesn't break existing agent behavior
3. Lightweight hooks - simple method calls, no major refactoring
4. Automatic management - handles decay, contradictions, drift automatically
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from .types import MemoryItem, MemoryCategory, MemoryScope, MemoryStatus
from .tiers import ThreeTierMemory, LongTermMemory, EpisodicTraces, WorkingContext
from .agent_state import AgentState, PolicyVersion
from .retrieval import GatedRetrieval, RetrievalIntent, RetrievalResult
from .monitors import (
    DriftMonitor,
    DriftSignal,
    ContradictionDetector,
    SummaryDiscipline,
    FocusWindowManager,
)


@dataclass
class MemorySystemConfig:
    """Configuration for the memory system."""
    persist_dir: Optional[str] = None
    max_working_items: int = 20
    max_retrieval_tokens: int = 2000
    max_retrieval_items: int = 10
    focus_window_size: int = 10
    consolidation_interval: int = 20
    enable_persistence: bool = True
    enable_drift_monitoring: bool = True
    enable_contradiction_detection: bool = True


class MemorySystem:
    """
    Unified memory system interface.

    Provides a simple API for agents to:
    - Store and retrieve memories with decay
    - Maintain explicit state (goals, constraints, assumptions)
    - Detect contradictions and drift
    - Generate fresh summaries

    Minimal integration example:
        memory = MemorySystem()
        memory.add_context("user said X", "user_input")
        result = memory.retrieve(RetrievalIntent.FACTUAL_QA, "query")
        memory.record_decision("did Y", "because Z")
    """

    def __init__(self, config: Optional[MemorySystemConfig] = None):
        self.config = config or MemorySystemConfig()
        self._setup_components()

    def _setup_components(self) -> None:
        """Initialize all memory components."""
        # Persistence paths
        persist_dir = self.config.persist_dir
        ltm_path = None
        episodic_path = None

        if persist_dir and self.config.enable_persistence:
            os.makedirs(persist_dir, exist_ok=True)
            ltm_path = os.path.join(persist_dir, "long_term_memory.json")
            episodic_path = os.path.join(persist_dir, "episodic_traces.json")

        # Core components
        self.memory = ThreeTierMemory(
            working=WorkingContext(max_items=self.config.max_working_items),
            long_term=LongTermMemory(persist_path=ltm_path),
            episodic=EpisodicTraces(persist_path=episodic_path),
        )

        self.state = AgentState(focus_window_size=self.config.focus_window_size)

        self.retrieval = GatedRetrieval(
            memory=self.memory,
            state=self.state,
            max_tokens=self.config.max_retrieval_tokens,
            max_items=self.config.max_retrieval_items,
        )

        # Monitors (optional)
        if self.config.enable_drift_monitoring:
            self.drift_monitor = DriftMonitor(self.state)
        else:
            self.drift_monitor = None

        if self.config.enable_contradiction_detection:
            self.contradiction_detector = ContradictionDetector(self.memory.long_term)
        else:
            self.contradiction_detector = None

        self.summary_discipline = SummaryDiscipline(self.state, self.memory)
        self.focus_manager = FocusWindowManager(
            self.state,
            self.memory,
            max_decisions=self.config.focus_window_size,
            consolidation_interval=self.config.consolidation_interval,
        )

    # =========================================================================
    # WORKING CONTEXT (Tier 1) - Ephemeral, always overwritten
    # =========================================================================

    def add_context(self, content: str, source: str = "context") -> None:
        """Add to ephemeral working context."""
        self.memory.add_working(content, source)

    def set_current_task(self, task: str) -> None:
        """Set the current task focus."""
        self.memory.working.set_task(task)
        self.state.set_goal(task, priority=0)

    def add_user_constraint(self, constraint: str) -> None:
        """Add a user-specified constraint."""
        self.memory.working.add_constraint(constraint)
        self.state.add_constraint(constraint)

    def log_tool_output(self, tool_name: str, summary: str) -> None:
        """Log a summarized tool output (not raw)."""
        self.memory.working.add_tool_output(tool_name, summary)

    # =========================================================================
    # LONG-TERM MEMORY (Tier 2) - Curated, with decay
    # =========================================================================

    def store(
        self,
        content: str,
        category: MemoryCategory,
        source: str,
        confidence: float = 0.8,
        check_contradictions: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Store a memory item with optional contradiction checking.

        Returns (success, memory_id or None).
        """
        # Check for contradictions first
        if check_contradictions and self.contradiction_detector:
            contradictions = self.contradiction_detector.check_contradiction(
                content, category
            )
            for item, reason in contradictions:
                # Record the contradiction
                if self.drift_monitor:
                    self.drift_monitor.record_signal(
                        DriftSignal.CONTRADICTION,
                        f"New content contradicts {item.id}: {reason}",
                    )
                # Mark as contested
                self.memory.long_term.mark_contested(item.id, reason)

        # Store the new memory
        memory_id = self.memory.store_long_term(
            content=content,
            category=category,
            source=source,
            confidence=confidence,
        )

        return (memory_id is not None, memory_id)

    def check_and_store(
        self,
        content: str,
        category: MemoryCategory,
        source: str,
        supersede_on_conflict: bool = False,
    ) -> Dict[str, Any]:
        """
        Check for contradictions and store, with conflict resolution.

        Returns dict with status and any resolved conflicts.
        """
        result = {
            "stored": False,
            "memory_id": None,
            "conflicts": [],
            "superseded": [],
        }

        # Check contradictions
        if self.contradiction_detector:
            contradictions = self.contradiction_detector.check_contradiction(
                content, category
            )

            for item, reason in contradictions:
                if supersede_on_conflict:
                    new_item = self.contradiction_detector.reconcile(
                        item, content, source, supersede=True
                    )
                    result["superseded"].append({
                        "old_id": item.id,
                        "new_id": new_item.id,
                        "reason": reason,
                    })
                else:
                    result["conflicts"].append({
                        "memory_id": item.id,
                        "reason": reason,
                    })

        # Store if no unresolved conflicts
        if not result["conflicts"]:
            success, memory_id = self.store(
                content, category, source, check_contradictions=False
            )
            result["stored"] = success
            result["memory_id"] = memory_id

        return result

    # =========================================================================
    # RETRIEVAL - Intent-conditioned, gated
    # =========================================================================

    def retrieve(
        self,
        intent: RetrievalIntent,
        query: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Retrieve memories based on intent.

        Intent options:
        - PLANNING: Strategic decisions, past choices
        - FACTUAL_QA: Verified facts, citations
        - TOOL_ORCHESTRATION: Procedural, environmental
        - CONSTRAINT_CHECK: User constraints, policies
        - CONTEXT_RECALL: Recent context, working memory
        """
        return self.retrieval.retrieve(
            intent=intent,
            query=query,
            min_confidence=min_confidence,
        )

    def get_verified_facts(self, query: Optional[str] = None) -> List[MemoryItem]:
        """Convenience method: get only high-confidence factual memories."""
        result = self.retrieve(RetrievalIntent.FACTUAL_QA, query, min_confidence=0.8)
        return [s.item for s in result.items if not s.needs_verification]

    def get_decisions(self) -> List[Dict[str, Any]]:
        """Get recent key decisions from focus window."""
        return self.state.focus_window.copy()

    # =========================================================================
    # STATE MANAGEMENT - Explicit, separate from memory
    # =========================================================================

    def set_goal(self, goal: str, priority: int = 0) -> None:
        """Set an explicit goal."""
        self.state.set_goal(goal, priority)

    def complete_goal(self, goal: str) -> None:
        """Mark a goal as completed."""
        self.state.complete_goal(goal)

    def add_assumption(
        self,
        content: str,
        confidence: float = 0.7,
        source: str = "inferred"
    ) -> None:
        """Add a working assumption."""
        self.state.add_assumption(content, confidence, source)

    def verify_assumption(self, content: str) -> None:
        """Mark an assumption as verified."""
        self.state.verify_assumption(content)

    def add_question(self, question: str, context: str = "", priority: int = 2) -> None:
        """Add an open question that may need user clarification."""
        self.state.add_question(question, context, priority)

    def resolve_question(self, question: str, resolution: str) -> None:
        """Resolve an open question."""
        self.state.resolve_question(question, resolution)

    def record_decision(self, decision: str, rationale: str) -> None:
        """Record a key decision to the focus window."""
        self.focus_manager.add_decision(decision, rationale)

    def get_state_summary(self) -> str:
        """Get current state summary."""
        return self.state.get_summary()

    # =========================================================================
    # EPISODIC TRACES (Tier 3) - Audit trail, not retrieved by default
    # =========================================================================

    def record_event(
        self,
        event_type: str,
        summary: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Record an event trace for debugging/audit."""
        return self.memory.record_event(event_type, summary, metadata)

    def diagnose(self, keyword: str) -> List[Any]:
        """Search episodic traces for diagnostic purposes."""
        return self.memory.episodic.diagnose(keyword)

    # =========================================================================
    # QUALITY SIGNALS & DRIFT DETECTION
    # =========================================================================

    def record_user_correction(self, details: str = "") -> None:
        """Record that the user corrected the agent."""
        if self.drift_monitor:
            self.drift_monitor.record_signal(
                DriftSignal.USER_CORRECTION, details, severity=2
            )
        self.state.record_quality_signal("user_correction")

    def record_tool_retry(self, details: str = "") -> None:
        """Record a tool call retry (potential loop)."""
        if self.drift_monitor:
            self.drift_monitor.record_signal(
                DriftSignal.TOOL_RETRY, details, severity=1
            )
        self.state.record_quality_signal("tool_retry")

    def record_verification_failure(self, details: str = "") -> None:
        """Record a verification failure."""
        if self.drift_monitor:
            self.drift_monitor.record_signal(
                DriftSignal.VERIFICATION_FAILURE, details, severity=2
            )
        self.state.record_quality_signal("verification_failure")

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status including drift signals."""
        status = {
            "policy": self.state.policy_version.value,
            "state_version": self.state.version,
            "active_memories": len(self.memory.long_term.query(status=MemoryStatus.ACTIVE)),
            "working_context_size": len(self.memory.working._items),
        }
        if self.drift_monitor:
            status["drift_health"] = self.drift_monitor.get_health_summary()
        return status

    # =========================================================================
    # SUMMARIZATION & CONSOLIDATION
    # =========================================================================

    def generate_summary(self, title: str = "Current State") -> str:
        """Generate a fresh summary from atomic facts (anti-drift)."""
        return self.summary_discipline.generate_fresh_summary(title)

    def consolidate(self) -> Dict[str, Any]:
        """Run consolidation pass to prune/promote/expire items."""
        return self.focus_manager.consolidate()

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    def on_task_start(self, task: str) -> None:
        """Call at the start of a new task."""
        self.set_current_task(task)
        self.record_event("task_start", f"Started: {task}")

    def on_task_complete(self, success: bool = True) -> None:
        """Call when a task completes."""
        if success:
            # Reset quality signals on success
            if self.drift_monitor:
                self.drift_monitor.reset()
            self.state.reset_quality_signals()

        # Run consolidation
        self.consolidate()
        self.record_event("task_complete", f"Success: {success}")

    def clear_working_context(self) -> None:
        """Clear ephemeral working context (between tasks)."""
        self.memory.working.clear()

    def get_context_for_prompt(self) -> Dict[str, Any]:
        """
        Get combined context for including in LLM prompt.

        Returns a structured dict with:
        - working_context: Recent ephemeral items
        - relevant_memories: Retrieved long-term memories
        - state_summary: Current goals/constraints/assumptions
        """
        # Get working context
        working = self.memory.working.get_context_window()

        # Get relevant memories (general retrieval)
        retrieval = self.retrieve(RetrievalIntent.CONTEXT_RECALL)

        # Get state summary
        summary = self.state.get_summary()

        return {
            "working_context": working,
            "relevant_memories": [
                {"content": s.item.content, "source": s.item.source, "score": s.score}
                for s in retrieval.items[:5]
            ],
            "state_summary": summary,
            "needs_verification": [
                {"content": s.item.content, "reason": s.verification_reason}
                for s in retrieval.verification_required[:3]
            ],
        }


# Convenience factory functions

def create_memory_system(persist_dir: Optional[str] = None) -> MemorySystem:
    """Create a memory system with default configuration."""
    config = MemorySystemConfig(persist_dir=persist_dir)
    return MemorySystem(config)


def create_lightweight_memory_system() -> MemorySystem:
    """Create a minimal memory system without persistence or monitoring."""
    config = MemorySystemConfig(
        enable_persistence=False,
        enable_drift_monitoring=False,
        enable_contradiction_detection=False,
    )
    return MemorySystem(config)
