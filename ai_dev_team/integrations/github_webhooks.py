"""
GitHub Webhooks Handler - Process GitHub webhook events
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookEvent:
    """Parsed webhook event"""
    event_type: str
    action: str
    payload: Dict[str, Any]
    delivery_id: str
    signature: Optional[str] = None


class GitHubWebhookHandler:
    """
    Handler for GitHub webhook events.

    Processes webhook payloads and routes them to appropriate handlers.
    """

    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        github_integration=None,
    ):
        self.webhook_secret = webhook_secret
        self.github_integration = github_integration
        self._handlers: Dict[str, List[Callable]] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default event handlers"""
        self.register_handler("pull_request", self._handle_pull_request)
        self.register_handler("pull_request_review", self._handle_pr_review)
        self.register_handler("issues", self._handle_issues)
        self.register_handler("push", self._handle_push)

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for an event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured - skipping verification")
            return True

        if not signature or not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def process_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
        delivery_id: str = "",
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a webhook event.

        Args:
            event_type: GitHub event type (pull_request, push, etc.)
            payload: Webhook payload
            delivery_id: GitHub delivery ID
            signature: Webhook signature for verification

        Returns:
            Processing result
        """
        event = WebhookEvent(
            event_type=event_type,
            action=payload.get("action", ""),
            payload=payload,
            delivery_id=delivery_id,
            signature=signature,
        )

        logger.info(f"Processing webhook: {event_type}/{event.action}")

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return {"status": "ignored", "reason": f"No handlers for {event_type}"}

        results = []
        for handler in handlers:
            try:
                result = await handler(event)
                results.append({"handler": handler.__name__, "result": result})
            except Exception as e:
                logger.error(f"Handler error: {e}")
                results.append({"handler": handler.__name__, "error": str(e)})

        return {"status": "processed", "results": results}

    async def _handle_pull_request(self, event: WebhookEvent) -> Dict[str, Any]:
        """Handle pull request events"""
        action = event.action
        pr = event.payload.get("pull_request", {})
        repo = event.payload.get("repository", {}).get("full_name", "")
        pr_number = pr.get("number", 0)

        if action == "opened" or action == "synchronize":
            # Auto-review new or updated PRs
            if self.github_integration:
                review = await self.github_integration.review_pull_request(
                    repo=repo,
                    pr_number=pr_number,
                    post_review=True,
                )
                return {
                    "action": "reviewed",
                    "pr": pr_number,
                    "confidence": review.confidence,
                }
            return {"action": "skipped", "reason": "No GitHub integration configured"}

        elif action == "closed":
            # Learn from PR outcome
            if self.github_integration:
                merged = pr.get("merged", False)
                learning_id = await self.github_integration.learn_from_pr_outcome(
                    repo=repo,
                    pr_number=pr_number,
                )
                return {
                    "action": "learned",
                    "pr": pr_number,
                    "merged": merged,
                    "learning_id": learning_id,
                }
            return {"action": "skipped", "reason": "No GitHub integration configured"}

        return {"action": "ignored", "pr_action": action}

    async def _handle_pr_review(self, event: WebhookEvent) -> Dict[str, Any]:
        """Handle PR review events"""
        action = event.action
        review = event.payload.get("review", {})
        pr = event.payload.get("pull_request", {})

        if action == "submitted":
            state = review.get("state", "")
            return {
                "action": "review_noted",
                "pr": pr.get("number"),
                "review_state": state,
            }

        return {"action": "ignored", "review_action": action}

    async def _handle_issues(self, event: WebhookEvent) -> Dict[str, Any]:
        """Handle issue events"""
        action = event.action
        issue = event.payload.get("issue", {})
        repo = event.payload.get("repository", {}).get("full_name", "")
        issue_number = issue.get("number", 0)

        if action == "opened":
            # Auto-analyze new issues
            if self.github_integration:
                analysis = await self.github_integration.analyze_issue(
                    repo=repo,
                    issue_number=issue_number,
                )
                return {
                    "action": "analyzed",
                    "issue": issue_number,
                    "analysis": analysis.get("analysis", "")[:200],
                }
            return {"action": "skipped", "reason": "No GitHub integration configured"}

        return {"action": "ignored", "issue_action": action}

    async def _handle_push(self, event: WebhookEvent) -> Dict[str, Any]:
        """Handle push events"""
        ref = event.payload.get("ref", "")
        commits = event.payload.get("commits", [])

        return {
            "action": "logged",
            "ref": ref,
            "commit_count": len(commits),
        }


def create_flask_webhook_route(handler: GitHubWebhookHandler):
    """
    Create a Flask route handler for webhooks.

    Usage:
        from flask import Flask
        app = Flask(__name__)

        webhook_handler = GitHubWebhookHandler(webhook_secret="...")
        app.route('/webhooks/github', methods=['POST'])(
            create_flask_webhook_route(webhook_handler)
        )
    """
    from flask import request, jsonify
    import asyncio

    def webhook_route():
        event_type = request.headers.get('X-GitHub-Event', '')
        delivery_id = request.headers.get('X-GitHub-Delivery', '')
        signature = request.headers.get('X-Hub-Signature-256', '')

        # Verify signature
        if not handler.verify_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401

        payload = request.get_json() or {}

        # Run async handler
        result = asyncio.run(handler.process_webhook(
            event_type=event_type,
            payload=payload,
            delivery_id=delivery_id,
            signature=signature,
        ))

        return jsonify(result)

    return webhook_route
