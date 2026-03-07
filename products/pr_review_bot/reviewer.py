"""
Core PR review bridge: diff -> AIDevTeam.collaborate() -> ReviewResult.
"""

import json
import logging
import re
import time
from typing import Optional

from .models import PRInfo, ReviewResult, ReviewVerdict, InlineComment

logger = logging.getLogger(__name__)

REVIEW_PROMPT_TEMPLATE = """\
You are an expert code reviewer. Review the following pull request and provide structured feedback.

## Pull Request
- **Title**: {title}
- **Author**: {author}
- **Files changed**: {files_changed}

## Description
{description}

## Diff
```diff
{diff}
```

## Instructions
Analyze the diff for:
1. **Bugs and logic errors** - incorrect behavior, off-by-one, null/undefined access
2. **Security vulnerabilities** - injection, XSS, auth bypass, secrets in code
3. **Performance issues** - unnecessary allocations, N+1 queries, blocking calls
4. **Code quality** - naming, DRY violations, overly complex logic
5. **Best practices** - error handling, typing, test coverage gaps

## Required Output Format
Respond with ONLY a JSON object (no markdown fences, no extra text):
{{
  "verdict": "APPROVE" | "REQUEST_CHANGES" | "COMMENT",
  "summary": "1-3 paragraph review summary",
  "inline_comments": [
    {{"path": "file.py", "line": 42, "body": "Issue description"}},
  ],
  "confidence": 0.0-1.0
}}

If the diff is clean with no issues, use verdict "APPROVE" with a brief positive summary.
If there are blocking issues, use "REQUEST_CHANGES".
For minor suggestions only, use "COMMENT".
"""


class PRReviewer:
    """Bridge between GitHub PR data and the El Gringo orchestrator."""

    def __init__(self, max_diff_lines: int = 5000):
        self._max_diff_lines = max_diff_lines

    async def review_diff(
        self,
        diff: str,
        pr_title: str = "Code Review",
        pr_author: str = "unknown",
        description: str = "",
    ) -> ReviewResult:
        """Convenience method: review a raw diff string without a full PRInfo object.

        Args:
            diff: Unified diff text or raw code to review.
            pr_title: Title for the review context.
            pr_author: Author name.
            description: Optional description of the change.

        Returns:
            ReviewResult with verdict, summary, and inline comments.
        """
        pr = PRInfo(
            owner="local",
            repo="local",
            number=0,
            title=pr_title,
            author=pr_author,
            head_sha="local",
            diff=diff,
            description=description,
        )
        return await self.review(pr)

    async def review(self, pr: PRInfo) -> ReviewResult:
        """Run a multi-agent review on a PR."""
        start = time.time()

        # Truncate very large diffs
        diff = pr.diff
        lines = diff.split("\n")
        if len(lines) > self._max_diff_lines:
            diff = "\n".join(lines[: self._max_diff_lines])
            diff += f"\n\n... (truncated, {len(lines) - self._max_diff_lines} lines omitted)"

        prompt = REVIEW_PROMPT_TEMPLATE.format(
            title=pr.title,
            author=pr.author,
            files_changed=", ".join(pr.files_changed) or "see diff",
            description=pr.description or "No description provided.",
            diff=diff,
        )

        # Import orchestrator lazily to avoid circular deps at module level
        from ai_dev_team.orchestrator import AIDevTeam

        team = AIDevTeam(project_name="pr-review-bot", enable_memory=False)
        collab_result = await team.collaborate(
            prompt=prompt,
            context="GitHub PR code review",
            mode="parallel",
        )

        elapsed = time.time() - start

        result = self._parse_review(
            collab_result.final_answer,
            agents_used=collab_result.participating_agents,
            confidence_fallback=collab_result.confidence_score,
            review_time=elapsed,
        )
        return result

    @staticmethod
    def _parse_review(
        raw: str,
        agents_used: Optional[list] = None,
        confidence_fallback: float = 0.5,
        review_time: float = 0.0,
    ) -> ReviewResult:
        """Parse the AI's JSON response into a ReviewResult."""
        # Try to extract JSON from the response
        text = raw.strip()

        # Strip markdown code fences if present
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            # Try to find raw JSON object
            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start != -1 and brace_end != -1:
                text = text[brace_start : brace_end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI review response as JSON, falling back")
            return ReviewResult(
                verdict=ReviewVerdict.COMMENT,
                summary=raw[:2000],
                confidence=confidence_fallback,
                agents_used=agents_used or [],
                review_time=review_time,
            )

        # Map verdict string
        verdict_str = data.get("verdict", "COMMENT").upper()
        try:
            verdict = ReviewVerdict(verdict_str)
        except ValueError:
            verdict = ReviewVerdict.COMMENT

        # Parse inline comments
        inline_comments = []
        for c in data.get("inline_comments", []):
            if "path" in c and "line" in c and "body" in c:
                inline_comments.append(
                    InlineComment(
                        path=c["path"],
                        line=int(c["line"]),
                        body=c["body"],
                        side=c.get("side", "RIGHT"),
                    )
                )

        return ReviewResult(
            verdict=verdict,
            summary=data.get("summary", ""),
            inline_comments=inline_comments,
            confidence=float(data.get("confidence", confidence_fallback)),
            agents_used=agents_used or [],
            review_time=review_time,
        )
