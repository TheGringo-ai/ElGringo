"""
Memory System - Persistent Learning and Knowledge Management
=============================================================

Provides:
- Conversation history storage
- Mistake pattern tracking
- Solution knowledge base
- Cross-project learning
"""

from .system import MemorySystem
from .prevention import MistakePrevention
from .learning import LearningEngine

__all__ = [
    "MemorySystem",
    "MistakePrevention",
    "LearningEngine",
]
