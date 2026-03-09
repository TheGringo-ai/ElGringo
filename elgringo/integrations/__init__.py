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

from .github import (
    GitHubIntegration,
    PRFile,
    PRReview,
    PROutcome,
)

__all__ = [
    'ChatterFixConnector',
    'get_connector',
    'check_against_learnings',
    'find_solution',
    'Lesson',
    'KnowledgeBase',
    'GitHubIntegration',
    'PRFile',
    'PRReview',
    'PROutcome',
]
