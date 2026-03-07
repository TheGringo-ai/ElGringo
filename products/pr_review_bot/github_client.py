"""
GitHub API client for fetching PR data and posting reviews.
"""

import logging

import httpx

from .models import PRInfo, ReviewResult, ReviewVerdict

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"


class GitHubClient:
    """Thin wrapper around the GitHub REST API for PR operations."""

    def __init__(self, token: str):
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr_info(self, owner: str, repo: str, number: int) -> PRInfo:
        """Fetch PR metadata."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/repos/{owner}/{repo}/pulls/{number}",
                headers=self._headers,
            )
            resp.raise_for_status()

        data = resp.json()
        return PRInfo(
            owner=owner,
            repo=repo,
            number=number,
            title=data["title"],
            author=data["user"]["login"],
            head_sha=data["head"]["sha"],
            description=data.get("body") or "",
        )

    async def get_pr_diff(self, owner: str, repo: str, number: int) -> str:
        """Fetch the unified diff for a PR."""
        headers = {**self._headers, "Accept": "application/vnd.github.diff"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/repos/{owner}/{repo}/pulls/{number}",
                headers=headers,
            )
            resp.raise_for_status()

        return resp.text

    async def get_pr_files(self, owner: str, repo: str, number: int) -> list[str]:
        """Get list of files changed in a PR."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/repos/{owner}/{repo}/pulls/{number}/files",
                headers=self._headers,
            )
            resp.raise_for_status()

        return [f["filename"] for f in resp.json()]

    async def post_review(
        self,
        owner: str,
        repo: str,
        number: int,
        head_sha: str,
        result: ReviewResult,
    ) -> dict:
        """Post a review with optional inline comments."""
        # Build inline comments payload
        comments = []
        for c in result.inline_comments:
            comments.append({
                "path": c.path,
                "line": c.line,
                "body": c.body,
                "side": c.side,
            })

        # Map verdict to GitHub event
        event_map = {
            ReviewVerdict.APPROVE: "APPROVE",
            ReviewVerdict.REQUEST_CHANGES: "REQUEST_CHANGES",
            ReviewVerdict.COMMENT: "COMMENT",
        }

        body = {
            "commit_id": head_sha,
            "body": result.summary,
            "event": event_map[result.verdict],
        }
        if comments:
            body["comments"] = comments

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/repos/{owner}/{repo}/pulls/{number}/reviews",
                headers=self._headers,
                json=body,
            )
            resp.raise_for_status()

        logger.info(
            "Posted %s review on %s/%s#%d with %d inline comments",
            result.verdict.value, owner, repo, number, len(comments),
        )
        return resp.json()
