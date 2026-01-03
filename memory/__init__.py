"""
Context-Rot Prevention Memory System.

A three-tier memory system with explicit state management, gated retrieval,
and adaptive drift detection. Designed for minimal integration overhead
with existing agent architectures.

Usage:
    from memory import MemorySystem

    # Initialize
    memory_system = MemorySystem(persist_dir="./memory_store")

    # Add to agent
    class MyAgent(BaseAgent):
        def __init__(self):
            super().__init__()
            self.memory_system = MemorySystem()

        def chat(self, message):
            # Store context
            self.memory_system.add_context(message, "user_input")

            # Retrieve relevant memories
            result = self.memory_system.retrieve(
                intent=RetrievalIntent.FACTUAL_QA,
                query=message
            )

            # ... use result.items in prompt ...

            # Record decision
            self.memory_system.record_decision("chose approach X", "because Y")

            # Check for contradictions before storing
            if new_fact:
                self.memory_system.check_and_store(new_fact, category, source)
"""

from .types import (
    MemoryItem,
    MemoryCategory,
    MemoryScope,
    MemoryStatus,
    EpisodicTrace,
    HALF_LIFE_CONFIG,
    DO_NOT_STORE_PATTERNS,
)

from .tiers import (
    WorkingContext,
    LongTermMemory,
    EpisodicTraces,
    ThreeTierMemory,
)

from .agent_state import (
    AgentState,
    PolicyVersion,
    Assumption,
    OpenQuestion,
)

from .retrieval import (
    GatedRetrieval,
    RetrievalIntent,
    RetrievalResult,
    ScoredMemory,
    VerificationGate,
)

from .monitors import (
    DriftMonitor,
    DriftSignal,
    ContradictionDetector,
    SummaryDiscipline,
    FocusWindowManager,
)

from .integration import MemorySystem, create_memory_system, create_lightweight_memory_system
from .agent_mixin import MemoryAgentMixin, EnhancedBaseAgent


__all__ = [
    # Types
    "MemoryItem",
    "MemoryCategory",
    "MemoryScope",
    "MemoryStatus",
    "EpisodicTrace",
    "HALF_LIFE_CONFIG",

    # Tiers
    "WorkingContext",
    "LongTermMemory",
    "EpisodicTraces",
    "ThreeTierMemory",

    # State
    "AgentState",
    "PolicyVersion",
    "Assumption",
    "OpenQuestion",

    # Retrieval
    "GatedRetrieval",
    "RetrievalIntent",
    "RetrievalResult",
    "ScoredMemory",
    "VerificationGate",

    # Monitors
    "DriftMonitor",
    "DriftSignal",
    "ContradictionDetector",
    "SummaryDiscipline",
    "FocusWindowManager",

    # Integration
    "MemorySystem",
    "create_memory_system",
    "create_lightweight_memory_system",

    # Agent Mixin
    "MemoryAgentMixin",
    "EnhancedBaseAgent",
]
