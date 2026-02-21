"""
GitHub App authentication and webhook verification.
"""

import hashlib
import hmac
import time
from pathlib import Path
from typing import Optional

import jwt
import httpx


class GitHubAppAuth:
    """Handles GitHub App JWT generation and installation token exchange."""

    def __init__(self, app_id: str, private_key_path: str = "", private_key: str = ""):
        self.app_id = app_id
        if private_key and private_key.startswith("-----BEGIN"):
            self._private_key = private_key
        elif private_key_path:
            self._private_key = Path(private_key_path).read_text()
        else:
            raise ValueError("Either private_key (PEM content) or private_key_path must be provided")
        self._install_token: Optional[str] = None
        self._token_expires_at: float = 0

    def _generate_jwt(self) -> str:
        """Generate a short-lived JWT for the GitHub App."""
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),  # 10 minutes max
            "iss": self.app_id,
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        """Exchange JWT for an installation access token (cached ~58 min)."""
        if self._install_token and time.time() < self._token_expires_at:
            return self._install_token

        app_jwt = self._generate_jwt()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            resp.raise_for_status()

        data = resp.json()
        self._install_token = data["token"]
        # Cache for 58 minutes (tokens last 60 min)
        self._token_expires_at = time.time() + (58 * 60)
        return self._install_token


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header (sha256=...).
        secret: Webhook secret configured in GitHub App settings.

    Returns:
        True if signature is valid.
    """
    if not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
