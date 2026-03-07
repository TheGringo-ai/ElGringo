"""
PR Review Bot webhook server.

Receives GitHub webhook events, verifies signatures, and launches
background review tasks using the El Gringo orchestrator.
"""

import asyncio
import logging
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .auth import GitHubAppAuth, verify_webhook_signature
from .config import PRReviewBotSettings
from .github_client import GitHubClient
from .reviewer import PRReviewer

logger = logging.getLogger(__name__)

app = FastAPI(title="El Gringo PR Review Bot", version="1.0.0")

# Initialized on startup
_settings: PRReviewBotSettings | None = None
_auth: GitHubAppAuth | None = None


@app.on_event("startup")
async def startup():
    global _settings, _auth
    _settings = PRReviewBotSettings()
    if _settings.github_app_id and (_settings.github_private_key or _settings.github_private_key_path):
        try:
            _auth = GitHubAppAuth(
                app_id=_settings.github_app_id,
                private_key_path=_settings.github_private_key_path,
                private_key=_settings.github_private_key,
            )
            logger.info("GitHub App auth initialized (app_id=%s)", _settings.github_app_id)
        except Exception as e:
            logger.warning("GitHub App auth not available: %s", e)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "product": "pr-review-bot",
        "version": "1.0.0",
        "auth_configured": _auth is not None,
    }


@app.post("/webhook")
async def webhook(request: Request):
    """Receive GitHub webhook events."""
    body = await request.body()

    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    secret = (_settings.github_webhook_secret if _settings else "") or os.getenv(
        "GITHUB_WEBHOOK_SECRET", ""
    )

    if secret:
        if not verify_webhook_signature(body, signature, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type == "ping":
        return {"status": "pong"}

    if event_type != "pull_request":
        return {"status": "ignored", "event": event_type}

    payload = await request.json()
    action = payload.get("action", "")

    # Only review on open or sync (new commits pushed)
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "action": action}

    pr_data = payload.get("pull_request", {})
    installation_id = payload.get("installation", {}).get("id")
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    number = pr_data["number"]

    logger.info("PR event: %s/%s#%d action=%s", owner, repo, number, action)

    # Launch review in background so we respond 200 quickly
    asyncio.create_task(
        _run_review(owner, repo, number, installation_id)
    )

    return {"status": "review_started", "pr": f"{owner}/{repo}#{number}"}


async def _run_review(owner: str, repo: str, number: int, installation_id: int | None):
    """Background task: fetch diff, run AI review, post results."""
    try:
        # Get installation token
        if _auth and installation_id:
            token = await _auth.get_installation_token(installation_id)
        else:
            token = os.getenv("GITHUB_TOKEN", "")

        if not token:
            logger.error("No GitHub token available for %s/%s#%d", owner, repo, number)
            return

        client = GitHubClient(token)

        # Fetch PR data
        pr_info = await client.get_pr_info(owner, repo, number)
        pr_info.diff = await client.get_pr_diff(owner, repo, number)
        pr_info.files_changed = await client.get_pr_files(owner, repo, number)

        # Run multi-agent review
        settings = _settings or PRReviewBotSettings()
        reviewer = PRReviewer(max_diff_lines=settings.max_diff_lines)
        result = await reviewer.review(pr_info)

        # Post review back to GitHub
        await client.post_review(owner, repo, number, pr_info.head_sha, result)

        logger.info(
            "Review complete: %s/%s#%d verdict=%s confidence=%.0f%% time=%.1fs agents=%s",
            owner, repo, number,
            result.verdict.value,
            result.confidence * 100,
            result.review_time,
            ", ".join(result.agents_used),
        )

        # Notify Fred Assistant about the review result
        try:
            import httpx
            fred_url = os.getenv("FRED_ASSISTANT_URL", "http://localhost:7870")
            async with httpx.AsyncClient(timeout=5) as http:
                await http.post(f"{fred_url}/platform/pr-review-callback", json={
                    "repo": f"{owner}/{repo}",
                    "pr_number": number,
                    "verdict": result.verdict.value,
                    "summary": result.summary[:1000] if hasattr(result, "summary") else "",
                    "confidence": result.confidence,
                    "agents_used": result.agents_used,
                    "review_time": result.review_time,
                })
                logger.info("PR review result sent to Fred Assistant")
        except Exception as cb_err:
            logger.debug("Fred Assistant callback failed (non-critical): %s", cb_err)

    except Exception:
        logger.exception("Review failed for %s/%s#%d", owner, repo, number)


def main():
    """Entry point for fred-pr-bot CLI command."""
    import uvicorn

    settings = PRReviewBotSettings()
    print(f"Starting El Gringo PR Review Bot on {settings.host}:{settings.port}")
    uvicorn.run(
        "products.pr_review_bot.server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
