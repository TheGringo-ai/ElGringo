"""One-Click Publish — Content approval gates and publish pipeline."""

import logging
from datetime import datetime

from products.fred_assistant.database import get_conn, log_activity

logger = logging.getLogger(__name__)


def approve_content(content_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM content_items WHERE id=?", (content_id,)).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE content_items SET approval_status='approved', updated_at=? WHERE id=?",
            (datetime.now().isoformat(), content_id),
        )
    log_activity("content_approved", "content", content_id)
    return _get_content(content_id)


def reject_content(content_id: str, reason: str = "") -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM content_items WHERE id=?", (content_id,)).fetchone()
        if not row:
            return None
        notes = reason or "Rejected"
        conn.execute(
            "UPDATE content_items SET approval_status='rejected', updated_at=? WHERE id=?",
            (datetime.now().isoformat(), content_id),
        )
    log_activity("content_rejected", "content", content_id, {"reason": reason})
    return _get_content(content_id)


def publish_content(content_id: str, platform: str = None, dry_run: bool = True) -> dict | None:
    content = _get_content(content_id)
    if not content:
        return None

    target_platform = platform or content.get("platform", "linkedin")

    if dry_run:
        return {
            "content_id": content_id,
            "title": content["title"],
            "platform": target_platform,
            "dry_run": True,
            "status": "would_publish",
            "message": f"[DRY RUN] Would publish '{content['title']}' to {target_platform}. Set dry_run=false to actually publish.",
        }

    # Real publish — stub implementations (log + mark as published)
    result = _dispatch_publish(content, target_platform)

    if result.get("success"):
        now = datetime.now().isoformat()
        published_url = result.get("url", "")
        with get_conn() as conn:
            conn.execute(
                "UPDATE content_items SET status='published', published_at=?, published_url=?, updated_at=? WHERE id=?",
                (now, published_url, now, content_id),
            )
        log_activity("content_published", "content", content_id, {"platform": target_platform})

    return {
        "content_id": content_id,
        "title": content["title"],
        "platform": target_platform,
        "dry_run": False,
        **result,
    }


def get_publish_status(content_id: str) -> dict | None:
    content = _get_content(content_id)
    if not content:
        return None
    return {
        "content_id": content_id,
        "title": content["title"],
        "status": content.get("status"),
        "approval_status": content.get("approval_status", "pending"),
        "published_at": content.get("published_at"),
        "published_url": content.get("published_url", ""),
    }


def _dispatch_publish(content: dict, platform: str) -> dict:
    """Route to platform-specific publisher. Stubs for now."""
    publishers = {
        "linkedin": _publish_linkedin,
        "twitter": _publish_twitter,
        "newsletter": _send_newsletter,
        "blog": _publish_blog,
    }
    publisher = publishers.get(platform, _publish_generic)
    return publisher(content)


def _publish_linkedin(content: dict) -> dict:
    logger.info(f"[STUB] Publishing to LinkedIn: {content['title']}")
    return {
        "success": True,
        "status": "published",
        "url": "",
        "message": "Published to LinkedIn (stub — configure API keys for real publishing)",
    }


def _publish_twitter(content: dict) -> dict:
    logger.info(f"[STUB] Publishing to Twitter/X: {content['title']}")
    return {
        "success": True,
        "status": "published",
        "url": "",
        "message": "Published to Twitter/X (stub — configure API keys for real publishing)",
    }


def _send_newsletter(content: dict) -> dict:
    logger.info(f"[STUB] Sending newsletter: {content['title']}")
    return {
        "success": True,
        "status": "published",
        "url": "",
        "message": "Newsletter sent (stub — configure email service for real sending)",
    }


def _publish_blog(content: dict) -> dict:
    logger.info(f"[STUB] Publishing blog post: {content['title']}")
    return {
        "success": True,
        "status": "published",
        "url": "",
        "message": "Blog post published (stub — configure CMS for real publishing)",
    }


def _publish_generic(content: dict) -> dict:
    logger.info(f"[STUB] Generic publish: {content['title']}")
    return {
        "success": True,
        "status": "published",
        "url": "",
        "message": "Content published (generic stub)",
    }


def _get_content(content_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM content_items WHERE id=?", (content_id,)).fetchone()
        if row:
            return dict(row)
    return None
