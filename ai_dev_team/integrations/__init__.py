"""
AI Dev Team - Integrations
==========================

External integrations for knowledge sharing and tool connectivity.
"""

from .chatterfix import (
    ChatterFixConnector,
    get_connector,
    check_against_learnings,
    find_solution,
    Lesson,
    KnowledgeBase
)

__all__ = [
    'ChatterFixConnector',
    'get_connector',
    'check_against_learnings',
    'find_solution',
    'Lesson',
    'KnowledgeBase'
]
