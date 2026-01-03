"""
Agent Memory Mixin.

Provides a minimal mixin class that can be added to existing agents
to enable memory features with zero breaking changes.

Usage:
    from memory.agent_mixin import MemoryAgentMixin

    class MyAgent(MemoryAgentMixin, BaseAgent):
        def __init__(self):
            super().__init__()
            self.init_memory()  # Optional: call to enable memory

        def chat(self, message):
            # Memory is automatically used if initialized
            return super().chat(message)
"""

from typing import Optional, Dict, Any, List

from .integration import MemorySystem, MemorySystemConfig
from .types import MemoryCategory, MemoryStatus
from .retrieval import RetrievalIntent


class MemoryAgentMixin:
    """
    Mixin class to add memory capabilities to any agent.

    Key features:
    - Zero breaking changes - memory is opt-in
    - Automatic context management
    - Easy hooks for storing/retrieving memories
    - Drift detection

    Simply inherit from this mixin and call init_memory() to enable.
    """

    _memory_system: Optional[MemorySystem] = None
    _memory_enabled: bool = False

    def init_memory(
        self,
        persist_dir: Optional[str] = None,
        config: Optional[MemorySystemConfig] = None,
    ) -> None:
        """
        Initialize the memory system for this agent.

        Call this in __init__ or lazily when memory is first needed.
        """
        if config is None:
            config = MemorySystemConfig(persist_dir=persist_dir)
        self._memory_system = MemorySystem(config)
        self._memory_enabled = True

    @property
    def memory(self) -> Optional[MemorySystem]:
        """Access the memory system (None if not initialized)."""
        return self._memory_system

    @property
    def memory_enabled(self) -> bool:
        """Check if memory is enabled."""
        return self._memory_enabled and self._memory_system is not None

    # =========================================================================
    # Convenience wrappers for common operations
    # =========================================================================

    def remember(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.FACTUAL,
        source: Optional[str] = None,
        confidence: float = 0.8,
    ) -> bool:
        """
        Store something in long-term memory.

        Returns True if stored successfully.
        """
        if not self.memory_enabled:
            return False

        source = source or getattr(self, 'name', 'agent')
        success, _ = self._memory_system.store(
            content=content,
            category=category,
            source=source,
            confidence=confidence,
        )
        return success

    def recall(
        self,
        query: str,
        intent: RetrievalIntent = RetrievalIntent.FACTUAL_QA,
        max_items: int = 5,
    ) -> List[str]:
        """
        Recall relevant memories based on a query.

        Returns list of memory contents.
        """
        if not self.memory_enabled:
            return []

        result = self._memory_system.retrieve(intent=intent, query=query)
        return [s.item.content for s in result.items[:max_items]]

    def note_context(self, content: str) -> None:
        """Add something to ephemeral working context."""
        if self.memory_enabled:
            self._memory_system.add_context(content, source=getattr(self, 'name', 'agent'))

    def note_decision(self, decision: str, rationale: str) -> None:
        """Record a key decision made during processing."""
        if self.memory_enabled:
            self._memory_system.record_decision(decision, rationale)

    def note_user_constraint(self, constraint: str) -> None:
        """Note a constraint specified by the user."""
        if self.memory_enabled:
            self._memory_system.add_user_constraint(constraint)

    def get_context_for_llm(self) -> str:
        """
        Get formatted context to include in LLM prompt.

        Returns a string ready to be appended to the system prompt.
        """
        if not self.memory_enabled:
            return ""

        ctx = self._memory_system.get_context_for_prompt()

        lines = ["=== Agent Memory Context ==="]

        # Current state
        if ctx.get("state_summary"):
            lines.append(ctx["state_summary"])

        # Relevant memories
        if ctx.get("relevant_memories"):
            lines.append("\n--- Relevant Knowledge ---")
            for mem in ctx["relevant_memories"]:
                lines.append(f"- {mem['content'][:200]}")

        # Items needing verification
        if ctx.get("needs_verification"):
            lines.append("\n--- Needs Verification ---")
            for item in ctx["needs_verification"]:
                lines.append(f"- {item['content'][:100]} ({item['reason']})")

        return "\n".join(lines)

    # =========================================================================
    # Hooks for agent lifecycle
    # =========================================================================

    def on_chat_start(self, user_message: str) -> None:
        """Hook: call at the start of chat() to set up context."""
        if self.memory_enabled:
            self._memory_system.add_context(user_message, "user_input")

    def on_chat_end(self, response: str, success: bool = True) -> None:
        """Hook: call at the end of chat() to record outcome."""
        if self.memory_enabled:
            self._memory_system.record_event(
                "chat_response",
                f"Response: {response[:100]}...",
                {"success": success},
            )

    def on_tool_call(self, tool_name: str, result_summary: str) -> None:
        """Hook: call after a tool call to log the result."""
        if self.memory_enabled:
            self._memory_system.log_tool_output(tool_name, result_summary)

    def on_user_correction(self, correction: str) -> None:
        """Hook: call when user corrects the agent."""
        if self.memory_enabled:
            self._memory_system.record_user_correction(correction)

    def get_memory_health(self) -> Dict[str, Any]:
        """Get memory system health status."""
        if not self.memory_enabled:
            return {"enabled": False}

        status = self._memory_system.get_health_status()
        status["enabled"] = True
        return status


class EnhancedBaseAgent(MemoryAgentMixin):
    """
    Example of an enhanced agent base class with memory.

    This shows how to integrate MemoryAgentMixin with an existing
    agent architecture. The memory features are completely optional -
    agents work normally even if init_memory() is never called.
    """

    def __init__(self, enable_memory: bool = False, memory_persist_dir: Optional[str] = None):
        """
        Initialize the enhanced agent.

        Args:
            enable_memory: Whether to enable memory features
            memory_persist_dir: Directory for memory persistence (optional)
        """
        if enable_memory:
            self.init_memory(persist_dir=memory_persist_dir)

    def enhanced_chat(self, user_message: str) -> str:
        """
        Example of a memory-enhanced chat method.

        This shows the pattern for wrapping an existing chat() method
        with memory hooks.
        """
        # Pre-chat hooks
        self.on_chat_start(user_message)

        # Get memory context to enhance the prompt
        memory_context = self.get_context_for_llm()

        # ... existing chat logic would go here ...
        # The memory_context string can be appended to the system prompt
        # or used to enrich the user message

        response = "Example response"  # Placeholder

        # Post-chat hooks
        self.on_chat_end(response)

        return response
