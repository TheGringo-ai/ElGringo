"""
Data models for the PR Review Bot.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ReviewVerdict(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


@dataclass
class PRInfo:
    """Pull request metadata and diff."""

    owner: str
    repo: str
    number: int
    title: str
    author: str
    head_sha: str
    diff: str = ""
    files_changed: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class InlineComment:
    """A review comment on a specific line."""

    path: str
    line: int
    body: str
    side: str = "RIGHT"


@dataclass
class ReviewResult:
    """Result of a PR review."""

    verdict: ReviewVerdict
    summary: str
    inline_comments: List[InlineComment] = field(default_factory=list)
    confidence: float = 0.0
    agents_used: List[str] = field(default_factory=list)
    review_time: float = 0.0
