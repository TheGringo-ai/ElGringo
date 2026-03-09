"""
Advanced Agent Framework
========================

State-of-the-art agent patterns and capabilities:
- ReAct (Reasoning + Acting) agents
- Structured tool use with validation
- Chain-of-thought prompting
- Multi-step planning and execution
- Context-aware memory management
- Streaming responses with tool calls
"""

from .tools import (
    Tool,
    ToolRegistry,
    ToolResult,
    ToolParameter,
    create_tool,
    get_tool_registry,
)
from .react_agent import (
    ReActAgent,
    ReActStep,
    ReActTrace,
    ThoughtType,
)
from .planner import (
    TaskPlanner,
    ExecutionPlan,
    PlanStep,
    PlanStatus,
)
from .chain_of_thought import (
    ChainOfThought,
    ReasoningChain,
    ReasoningStep,
    ReasoningType,
    reason_through,
)
from .context_manager import (
    ContextManager,
    ContextWindow,
    ConversationTracker,
    Message,
    MessagePriority,
    MessageRole,
)

__all__ = [
    # Tools
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "ToolParameter",
    "create_tool",
    "get_tool_registry",
    # ReAct
    "ReActAgent",
    "ReActStep",
    "ReActTrace",
    "ThoughtType",
    # Planner
    "TaskPlanner",
    "ExecutionPlan",
    "PlanStep",
    "PlanStatus",
    # Chain of Thought
    "ChainOfThought",
    "ReasoningChain",
    "ReasoningStep",
    "ReasoningType",
    "reason_through",
    # Context
    "ContextManager",
    "ContextWindow",
    "ConversationTracker",
    "Message",
    "MessagePriority",
    "MessageRole",
]
