"""
Context Window Manager
======================

Intelligent context window management for AI agents.

Manages the limited context window of LLMs by:
- Tracking message history
- Prioritizing important context
- Summarizing old messages
- Maintaining critical information
- Sliding window with smart truncation

Features:
- Token-aware context management
- Priority-based message retention
- Automatic summarization of old context
- Pinned messages that never expire
- Context compression techniques
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Role of a message in the context."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class MessagePriority(Enum):
    """Priority level for context retention."""
    CRITICAL = 1     # Never remove (system prompts, pinned)
    HIGH = 2         # Keep as long as possible
    NORMAL = 3       # Standard retention
    LOW = 4          # Remove first when needed
    EPHEMERAL = 5    # Remove immediately after use


@dataclass
class Message:
    """A message in the context window."""
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    priority: MessagePriority = MessagePriority.NORMAL
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    pinned: bool = False
    summary: Optional[str] = None  # Compressed version

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-compatible dict."""
        return {
            "role": self.role.value,
            "content": self.content,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Convert to full dict with metadata."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "token_count": self.token_count,
            "pinned": self.pinned,
            "metadata": self.metadata,
        }


@dataclass
class ContextWindow:
    """
    Represents the current context window state.

    Tracks tokens, messages, and provides analytics.
    """
    messages: List[Message]
    max_tokens: int
    current_tokens: int
    reserved_tokens: int = 0  # For response
    summarized_count: int = 0

    @property
    def available_tokens(self) -> int:
        """Tokens available for new content."""
        return self.max_tokens - self.current_tokens - self.reserved_tokens

    @property
    def utilization(self) -> float:
        """Context utilization percentage."""
        return self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0

    def to_api_messages(self) -> List[Dict[str, str]]:
        """Convert to API message format."""
        return [m.to_dict() for m in self.messages]

    def get_stats(self) -> Dict[str, Any]:
        """Get context window statistics."""
        role_counts = {}
        for msg in self.messages:
            role = msg.role.value
            role_counts[role] = role_counts.get(role, 0) + 1

        priority_counts = {}
        for msg in self.messages:
            p = msg.priority.name
            priority_counts[p] = priority_counts.get(p, 0) + 1

        return {
            "total_messages": len(self.messages),
            "total_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "available_tokens": self.available_tokens,
            "utilization": f"{self.utilization:.1%}",
            "messages_by_role": role_counts,
            "messages_by_priority": priority_counts,
            "pinned_messages": sum(1 for m in self.messages if m.pinned),
            "summarized_messages": self.summarized_count,
        }


class ContextManager:
    """
    Manages context window for AI conversations.

    Features:
    - Token counting and tracking
    - Smart message truncation
    - Priority-based retention
    - Automatic summarization
    - Context compression

    Example:
        manager = ContextManager(max_tokens=8000)
        manager.add_system("You are a helpful assistant")
        manager.add_user("Hello!")
        manager.add_assistant("Hi! How can I help?")

        window = manager.get_context_window()
        messages = window.to_api_messages()
    """

    # Approximate tokens per character (varies by model)
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        max_tokens: int = 8000,
        reserved_for_response: int = 1000,
        tokenizer: Callable[[str], int] = None,
        summarizer: Callable[[str], str] = None,
        auto_summarize: bool = True,
        summarize_threshold: float = 0.8,  # Summarize at 80% capacity
    ):
        """
        Initialize context manager.

        Args:
            max_tokens: Maximum tokens in context window
            reserved_for_response: Tokens reserved for model response
            tokenizer: Function to count tokens (defaults to char estimate)
            summarizer: Async function to summarize text
            auto_summarize: Automatically summarize old messages
            summarize_threshold: Utilization threshold to trigger summarization
        """
        self.max_tokens = max_tokens
        self.reserved_for_response = reserved_for_response
        self.tokenizer = tokenizer or self._estimate_tokens
        self.summarizer = summarizer
        self.auto_summarize = auto_summarize
        self.summarize_threshold = summarize_threshold

        self._messages: List[Message] = []
        self._total_tokens = 0
        self._summarized_count = 0

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return len(text) // self.CHARS_PER_TOKEN + 1

    def _count_message_tokens(self, message: Message) -> int:
        """Count tokens in a message."""
        # Add overhead for role and formatting
        overhead = 4
        content_tokens = self.tokenizer(message.content)
        return content_tokens + overhead

    def add_message(
        self,
        role: MessageRole,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        pinned: bool = False,
        metadata: Dict[str, Any] = None,
    ) -> Message:
        """
        Add a message to the context.

        Args:
            role: Message role
            content: Message content
            priority: Retention priority
            pinned: If True, never remove
            metadata: Additional metadata

        Returns:
            The created Message
        """
        message = Message(
            role=role,
            content=content,
            priority=priority,
            pinned=pinned,
            metadata=metadata or {},
        )
        message.token_count = self._count_message_tokens(message)

        self._messages.append(message)
        self._total_tokens += message.token_count

        # Check if we need to manage context
        if self._needs_compression():
            asyncio.create_task(self._compress_context())

        return message

    def add_system(self, content: str, pinned: bool = True) -> Message:
        """Add a system message (pinned by default)."""
        return self.add_message(
            MessageRole.SYSTEM,
            content,
            priority=MessagePriority.CRITICAL,
            pinned=pinned,
        )

    def add_user(self, content: str, priority: MessagePriority = MessagePriority.NORMAL) -> Message:
        """Add a user message."""
        return self.add_message(MessageRole.USER, content, priority)

    def add_assistant(self, content: str, priority: MessagePriority = MessagePriority.NORMAL) -> Message:
        """Add an assistant message."""
        return self.add_message(MessageRole.ASSISTANT, content, priority)

    def add_tool_result(self, content: str, tool_name: str = None) -> Message:
        """Add a tool/function result."""
        return self.add_message(
            MessageRole.TOOL,
            content,
            priority=MessagePriority.NORMAL,
            metadata={"tool_name": tool_name} if tool_name else {},
        )

    def pin_message(self, index: int):
        """Pin a message so it won't be removed."""
        if 0 <= index < len(self._messages):
            self._messages[index].pinned = True
            self._messages[index].priority = MessagePriority.CRITICAL

    def unpin_message(self, index: int):
        """Unpin a message."""
        if 0 <= index < len(self._messages):
            self._messages[index].pinned = False
            if self._messages[index].priority == MessagePriority.CRITICAL:
                self._messages[index].priority = MessagePriority.HIGH

    def _needs_compression(self) -> bool:
        """Check if context needs compression."""
        available = self.max_tokens - self._total_tokens - self.reserved_for_response
        threshold = self.max_tokens * (1 - self.summarize_threshold)
        return available < threshold

    async def _compress_context(self):
        """Compress context to fit within limits."""
        target_tokens = int(self.max_tokens * 0.7)  # Compress to 70%

        while self._total_tokens > target_tokens:
            # Find lowest priority, oldest, non-pinned message
            candidate_idx = self._find_removal_candidate()

            if candidate_idx is None:
                logger.warning("Cannot compress further - all messages pinned or critical")
                break

            message = self._messages[candidate_idx]

            if self.auto_summarize and self.summarizer and not message.summary:
                # Try to summarize instead of remove
                try:
                    summary = await self.summarizer(message.content)
                    old_tokens = message.token_count
                    message.summary = message.content
                    message.content = f"[Summarized] {summary}"
                    message.token_count = self._count_message_tokens(message)
                    self._total_tokens -= (old_tokens - message.token_count)
                    self._summarized_count += 1
                except Exception as e:
                    logger.warning(f"Summarization failed: {e}")
                    self._remove_message(candidate_idx)
            else:
                self._remove_message(candidate_idx)

    def _find_removal_candidate(self) -> Optional[int]:
        """Find the best message to remove or summarize."""
        candidates = []

        for i, msg in enumerate(self._messages):
            if msg.pinned or msg.priority == MessagePriority.CRITICAL:
                continue
            candidates.append((i, msg))

        if not candidates:
            return None

        # Sort by priority (highest value = lowest priority) then by timestamp (oldest first)
        candidates.sort(key=lambda x: (x[1].priority.value, x[1].timestamp))

        return candidates[0][0]

    def _remove_message(self, index: int):
        """Remove a message from context."""
        if 0 <= index < len(self._messages):
            message = self._messages.pop(index)
            self._total_tokens -= message.token_count
            logger.debug(f"Removed message: {message.content[:50]}...")

    def get_context_window(self) -> ContextWindow:
        """Get current context window."""
        return ContextWindow(
            messages=list(self._messages),
            max_tokens=self.max_tokens,
            current_tokens=self._total_tokens,
            reserved_tokens=self.reserved_for_response,
            summarized_count=self._summarized_count,
        )

    def get_messages(
        self,
        roles: List[MessageRole] = None,
        limit: int = None,
    ) -> List[Message]:
        """
        Get messages, optionally filtered.

        Args:
            roles: Filter by roles
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        messages = self._messages

        if roles:
            messages = [m for m in messages if m.role in roles]

        if limit:
            messages = messages[-limit:]

        return messages

    def get_api_messages(self) -> List[Dict[str, str]]:
        """Get messages in API format."""
        return [m.to_dict() for m in self._messages]

    def clear(self, keep_system: bool = True, keep_pinned: bool = True):
        """
        Clear context.

        Args:
            keep_system: Keep system messages
            keep_pinned: Keep pinned messages
        """
        if keep_system or keep_pinned:
            self._messages = [
                m for m in self._messages
                if (keep_system and m.role == MessageRole.SYSTEM) or
                   (keep_pinned and m.pinned)
            ]
            self._total_tokens = sum(m.token_count for m in self._messages)
        else:
            self._messages = []
            self._total_tokens = 0

        self._summarized_count = 0

    def get_last_n_messages(self, n: int) -> List[Message]:
        """Get last N messages."""
        return self._messages[-n:] if n > 0 else []

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation."""
        if not self._messages:
            return "No messages in context."

        lines = []
        lines.append(f"Conversation with {len(self._messages)} messages:")

        for msg in self._messages[-5:]:  # Last 5 messages
            role = msg.role.value.upper()
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"  [{role}] {content}")

        return "\n".join(lines)

    def export_context(self) -> Dict[str, Any]:
        """Export full context state."""
        return {
            "messages": [m.to_full_dict() for m in self._messages],
            "total_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "summarized_count": self._summarized_count,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def import_context(self, data: Dict[str, Any]):
        """Import context from exported data."""
        self._messages = []
        self._total_tokens = 0

        for msg_data in data.get("messages", []):
            message = Message(
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                timestamp=msg_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                priority=MessagePriority(msg_data.get("priority", 3)),
                token_count=msg_data.get("token_count", 0),
                pinned=msg_data.get("pinned", False),
                metadata=msg_data.get("metadata", {}),
            )

            if message.token_count == 0:
                message.token_count = self._count_message_tokens(message)

            self._messages.append(message)
            self._total_tokens += message.token_count

        self._summarized_count = data.get("summarized_count", 0)

    def fork(self) -> "ContextManager":
        """Create a fork of this context (for branching conversations)."""
        new_manager = ContextManager(
            max_tokens=self.max_tokens,
            reserved_for_response=self.reserved_for_response,
            tokenizer=self.tokenizer,
            summarizer=self.summarizer,
            auto_summarize=self.auto_summarize,
            summarize_threshold=self.summarize_threshold,
        )

        # Deep copy messages
        for msg in self._messages:
            new_msg = Message(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                priority=msg.priority,
                token_count=msg.token_count,
                pinned=msg.pinned,
                metadata=dict(msg.metadata),
                summary=msg.summary,
            )
            new_manager._messages.append(new_msg)

        new_manager._total_tokens = self._total_tokens
        new_manager._summarized_count = self._summarized_count

        return new_manager


class ConversationTracker:
    """
    Track multiple conversations with shared context.

    Useful for multi-turn interactions with branching.
    """

    def __init__(self, base_context: ContextManager = None):
        self.base_context = base_context or ContextManager()
        self.branches: Dict[str, ContextManager] = {}
        self.current_branch: str = "main"

    def create_branch(self, name: str, from_branch: str = None) -> ContextManager:
        """Create a new conversation branch."""
        source = self.branches.get(from_branch) if from_branch else self.base_context
        self.branches[name] = source.fork()
        return self.branches[name]

    def switch_branch(self, name: str) -> ContextManager:
        """Switch to a different branch."""
        if name not in self.branches:
            raise ValueError(f"Branch '{name}' does not exist")
        self.current_branch = name
        return self.branches[name]

    def get_current(self) -> ContextManager:
        """Get current branch context."""
        if self.current_branch == "main":
            return self.base_context
        return self.branches.get(self.current_branch, self.base_context)

    def merge_branch(self, source: str, target: str = "main"):
        """Merge messages from one branch into another."""
        source_ctx = self.branches.get(source)
        target_ctx = self.branches.get(target) if target != "main" else self.base_context

        if not source_ctx:
            raise ValueError(f"Source branch '{source}' does not exist")

        # Add non-duplicate messages
        existing_contents = {m.content for m in target_ctx._messages}
        for msg in source_ctx._messages:
            if msg.content not in existing_contents:
                target_ctx.add_message(
                    msg.role,
                    msg.content,
                    msg.priority,
                    msg.pinned,
                    msg.metadata,
                )

    def list_branches(self) -> List[str]:
        """List all branches."""
        return ["main"] + list(self.branches.keys())
