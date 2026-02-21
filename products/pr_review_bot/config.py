"""
PR Review Bot configuration.
"""

from pydantic_settings import BaseSettings
from typing import Optional

from products.base import ProductConfig


class PRReviewBotSettings(BaseSettings):
    """Settings loaded from environment variables."""

    github_app_id: str = ""
    github_private_key_path: str = ""
    github_private_key: str = ""  # Inline PEM content (Cloud Run; takes priority over path)
    github_webhook_secret: str = ""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Review settings
    max_diff_lines: int = 5000
    review_timeout: int = 300

    # AI API keys (inherited from FredAI env)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None

    model_config = {"env_prefix": "", "case_sensitive": False}


PRODUCT_CONFIG = ProductConfig(
    name="pr-review-bot",
    display_name="PR Review Bot",
    version="1.0.0",
    description="AI-powered GitHub PR reviewer using multi-agent collaboration",
    entry_module="products.pr_review_bot.server",
    status="active",
    port=8000,
    env_vars=[
        "GITHUB_APP_ID",
        "GITHUB_PRIVATE_KEY_PATH",
        "GITHUB_WEBHOOK_SECRET",
    ],
    dependencies=[
        "PyJWT>=2.8.0",
        "cryptography>=42.0.0",
        "httpx>=0.27.0",
        "pydantic-settings>=2.0.0",
    ],
)
