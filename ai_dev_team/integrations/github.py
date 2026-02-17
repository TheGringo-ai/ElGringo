"""
GitHub Integration - Auto-review PRs and learn from outcomes
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PRFile:
    """A file changed in a pull request"""
    filename: str
    status: str  # added, removed, modified, renamed
    additions: int
    deletions: int
    patch: Optional[str] = None


@dataclass
class PRReview:
    """AI-generated PR review"""
    pr_number: int
    repo: str
    summary: str
    issues_found: List[Dict[str, Any]]
    suggestions: List[str]
    approval_recommendation: str  # approve, request_changes, comment
    confidence: float
    review_time: float
    agents_used: List[str]


@dataclass
class PROutcome:
    """Outcome of a PR for learning"""
    pr_number: int
    repo: str
    merged: bool
    merge_time: Optional[str]
    review_comments: List[str]
    changes_requested: List[str]


class GitHubIntegration:
    """
    GitHub integration for AI team.

    Provides:
    - Automatic PR review
    - Learning from PR outcomes (merged vs rejected)
    - Issue analysis
    """

    def __init__(
        self,
        token: Optional[str] = None,
        ai_team=None,
        learning_engine=None,
    ):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.ai_team = ai_team
        self.learning_engine = learning_engine
        self._github = None

    def _get_github(self):
        """Get GitHub client"""
        if self._github is None and self.token:
            try:
                from github import Github
                self._github = Github(self.token)
            except ImportError:
                logger.error("PyGithub not installed. Run: pip install PyGithub")
        return self._github

    async def review_pull_request(
        self,
        repo: str,
        pr_number: int,
        focus_areas: Optional[List[str]] = None,
        post_review: bool = False,
    ) -> PRReview:
        """
        Review a pull request with the AI team.

        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            focus_areas: Specific areas to focus on (security, performance, etc.)
            post_review: Whether to post the review as a comment

        Returns:
            PRReview with analysis results
        """
        import time
        start_time = time.time()

        gh = self._get_github()
        if not gh:
            return PRReview(
                pr_number=pr_number,
                repo=repo,
                summary="GitHub API not available - token not configured",
                issues_found=[],
                suggestions=[],
                approval_recommendation="comment",
                confidence=0.0,
                review_time=0.0,
                agents_used=[],
            )

        try:
            # Get PR details
            repository = gh.get_repo(repo)
            pr = repository.get_pull(pr_number)

            # Get files changed
            files = []
            for f in pr.get_files():
                files.append(PRFile(
                    filename=f.filename,
                    status=f.status,
                    additions=f.additions,
                    deletions=f.deletions,
                    patch=f.patch[:2000] if f.patch else None,
                ))

            # Build review prompt
            focus_str = ", ".join(focus_areas) if focus_areas else "code quality, bugs, security, performance"

            files_summary = "\n".join(
                f"- {f.filename} ({f.status}): +{f.additions}/-{f.deletions}"
                for f in files[:20]
            )

            patches = "\n\n".join(
                f"### {f.filename}\n```diff\n{f.patch}\n```"
                for f in files[:10] if f.patch
            )

            review_prompt = f"""Review this Pull Request:

**Title:** {pr.title}
**Description:** {pr.body or 'No description provided'}
**Author:** {pr.user.login}
**Base:** {pr.base.ref} <- {pr.head.ref}

**Files Changed ({len(files)} files):**
{files_summary}

**Focus Areas:** {focus_str}

**Code Changes:**
{patches}

Provide a comprehensive review including:
1. Summary of changes
2. Potential issues or bugs (with severity: low/medium/high/critical)
3. Security concerns
4. Performance implications
5. Code quality observations
6. Specific suggestions for improvement
7. Overall recommendation: APPROVE, REQUEST_CHANGES, or COMMENT"""

            # Use AI team for review
            if self.ai_team:
                result = await self.ai_team.collaborate(
                    review_prompt,
                    mode="parallel",
                )

                # Parse response for structured data
                issues = self._extract_issues(result.final_answer)
                suggestions = self._extract_suggestions(result.final_answer)
                recommendation = self._extract_recommendation(result.final_answer)

                review = PRReview(
                    pr_number=pr_number,
                    repo=repo,
                    summary=result.final_answer[:1000],
                    issues_found=issues,
                    suggestions=suggestions,
                    approval_recommendation=recommendation,
                    confidence=result.confidence_score,
                    review_time=time.time() - start_time,
                    agents_used=result.participating_agents,
                )
            else:
                review = PRReview(
                    pr_number=pr_number,
                    repo=repo,
                    summary="AI team not configured",
                    issues_found=[],
                    suggestions=[],
                    approval_recommendation="comment",
                    confidence=0.0,
                    review_time=time.time() - start_time,
                    agents_used=[],
                )

            # Post review if requested
            if post_review and review.summary:
                review_body = self._format_review_comment(review)
                pr.create_review(body=review_body, event="COMMENT")
                logger.info(f"Posted review to PR #{pr_number}")

            return review

        except Exception as e:
            logger.error(f"Error reviewing PR: {e}")
            return PRReview(
                pr_number=pr_number,
                repo=repo,
                summary=f"Error during review: {str(e)}",
                issues_found=[],
                suggestions=[],
                approval_recommendation="comment",
                confidence=0.0,
                review_time=time.time() - start_time,
                agents_used=[],
            )

    def _extract_issues(self, content: str) -> List[Dict[str, Any]]:
        """Extract issues from review content"""
        issues = []
        lines = content.lower().split("\n")

        severity_keywords = {
            "critical": ["critical", "severe", "vulnerability", "security hole"],
            "high": ["high", "important", "significant", "bug"],
            "medium": ["medium", "moderate", "should fix"],
            "low": ["low", "minor", "nitpick", "suggestion"],
        }

        for line in lines:
            for severity, keywords in severity_keywords.items():
                if any(kw in line for kw in keywords):
                    issues.append({
                        "description": line.strip()[:200],
                        "severity": severity,
                    })
                    break

        return issues[:10]  # Limit to 10 issues

    def _extract_suggestions(self, content: str) -> List[str]:
        """Extract suggestions from review content"""
        suggestions = []
        lines = content.split("\n")

        suggestion_markers = ["suggest", "recommend", "consider", "should", "could", "better to"]

        for line in lines:
            if any(marker in line.lower() for marker in suggestion_markers):
                clean_line = line.strip()
                if len(clean_line) > 20:
                    suggestions.append(clean_line[:300])

        return suggestions[:10]

    def _extract_recommendation(self, content: str) -> str:
        """Extract approval recommendation from content"""
        content_lower = content.lower()

        if "approve" in content_lower and "request" not in content_lower:
            return "approve"
        elif "request_changes" in content_lower or "request changes" in content_lower:
            return "request_changes"
        elif "critical" in content_lower or "security" in content_lower:
            return "request_changes"
        else:
            return "comment"

    def _format_review_comment(self, review: PRReview) -> str:
        """Format review as GitHub comment"""
        emoji = {
            "approve": "✅",
            "request_changes": "⚠️",
            "comment": "💬",
        }

        comment = f"""## 🤖 AI Team Review {emoji.get(review.approval_recommendation, '💬')}

**Recommendation:** {review.approval_recommendation.upper()}
**Confidence:** {review.confidence:.0%}
**Reviewed by:** {', '.join(review.agents_used)}

### Summary
{review.summary[:500]}

"""

        if review.issues_found:
            comment += "### Issues Found\n"
            for issue in review.issues_found[:5]:
                severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                comment += f"- {severity_emoji.get(issue['severity'], '⚪')} **{issue['severity'].upper()}**: {issue['description']}\n"
            comment += "\n"

        if review.suggestions:
            comment += "### Suggestions\n"
            for suggestion in review.suggestions[:5]:
                comment += f"- {suggestion}\n"
            comment += "\n"

        comment += "\n---\n*Generated by AI Team Platform*"

        return comment

    async def learn_from_pr_outcome(
        self,
        repo: str,
        pr_number: int,
    ) -> Optional[str]:
        """
        Learn from PR outcome (merged or rejected).

        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number

        Returns:
            Learning record ID or None
        """
        gh = self._get_github()
        if not gh or not self.learning_engine:
            return None

        try:
            repository = gh.get_repo(repo)
            pr = repository.get_pull(pr_number)

            # Get review comments
            comments = []
            for comment in pr.get_review_comments():
                comments.append(comment.body[:200])

            outcome = PROutcome(
                pr_number=pr_number,
                repo=repo,
                merged=pr.merged,
                merge_time=pr.merged_at.isoformat() if pr.merged_at else None,
                review_comments=comments[:10],
                changes_requested=[],
            )

            if outcome.merged:
                # Learn from success
                return await self.learning_engine.learn_from_success(
                    result=type('obj', (object,), {
                        'success': True,
                        'confidence_score': 0.8,
                        'agent_responses': [],
                    })(),
                    problem_description=f"PR #{pr_number}: {pr.title}",
                    project=repo,
                )
            else:
                # Learn from rejection
                context = {
                    "pr_number": pr_number,
                    "title": pr.title,
                    "comments": comments,
                }
                return await self.learning_engine.learn_from_error(
                    Exception(f"PR #{pr_number} was not merged"),
                    context,
                    repo,
                )

        except Exception as e:
            logger.error(f"Error learning from PR outcome: {e}")
            return None

    async def analyze_issue(
        self,
        repo: str,
        issue_number: int,
    ) -> Dict[str, Any]:
        """
        Analyze a GitHub issue with the AI team.

        Args:
            repo: Repository in format "owner/repo"
            issue_number: Issue number

        Returns:
            Analysis results
        """
        gh = self._get_github()
        if not gh:
            return {"error": "GitHub API not available"}

        try:
            repository = gh.get_repo(repo)
            issue = repository.get_issue(issue_number)

            # Get comments
            comments = []
            for comment in issue.get_comments():
                comments.append({
                    "user": comment.user.login,
                    "body": comment.body[:500],
                })

            analysis_prompt = f"""Analyze this GitHub issue:

**Title:** {issue.title}
**State:** {issue.state}
**Labels:** {', '.join(l.name for l in issue.labels)}
**Created by:** {issue.user.login}

**Description:**
{issue.body or 'No description'}

**Comments ({len(comments)}):**
{chr(10).join(f"- {c['user']}: {c['body'][:200]}" for c in comments[:5])}

Provide:
1. Issue type (bug, feature, question, etc.)
2. Priority assessment
3. Suggested approach to resolve
4. Estimated complexity
5. Related areas of the codebase that might be affected"""

            if self.ai_team:
                result = await self.ai_team.collaborate(analysis_prompt, mode="parallel")
                return {
                    "issue_number": issue_number,
                    "repo": repo,
                    "analysis": result.final_answer,
                    "confidence": result.confidence_score,
                    "agents_used": result.participating_agents,
                }

            return {"error": "AI team not configured"}

        except Exception as e:
            logger.error(f"Error analyzing issue: {e}")
            return {"error": str(e)}
