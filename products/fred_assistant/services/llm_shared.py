"""
Shared LLM layer — routes through ModelRouter (multi-provider with fallback).
Falls back to direct Gemini if ModelRouter is unavailable.

All calls are tracked in the ai_usage table for the usage dashboard.
"""

import logging
import os

logger = logging.getLogger(__name__)

_gemini_agent = None


def get_gemini():
    """Lazy-init a shared Gemini agent. Kept for backward compat."""
    global _gemini_agent
    if _gemini_agent is None:
        try:
            from elgringo.agents.gemini import GeminiAgent
            from elgringo.agents.base import AgentConfig, ModelType

            model = os.getenv("FRED_CHAT_MODEL", "gemini-2.5-flash")
            _gemini_agent = GeminiAgent(AgentConfig(
                name="fred",
                model_type=ModelType.GEMINI,
                role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat",
                              "code_review", "security", "analysis", "architecture"],
                model_name=model,
                temperature=0.7,
                max_tokens=4000,
            ))
        except Exception as e:
            logger.warning("Gemini agent init failed: %s", e)
    return _gemini_agent


async def llm_response(prompt: str, system_prompt: str, feature: str = "chat") -> str:
    """Get a response from the best available LLM provider.

    Tries ModelRouter first (multi-provider with fallback chain).
    Falls back to direct Gemini if router is unavailable.
    Returns empty string on failure.
    """
    # Try ModelRouter (Phase 2)
    try:
        from products.fred_assistant.services.model_router import get_router
        router = get_router()
        result = await router.route(prompt, system_prompt=system_prompt, feature=feature)
        if result:
            return result
    except Exception as e:
        logger.debug("ModelRouter unavailable, falling back to Gemini: %s", e)

    # Fallback: direct Gemini
    agent = get_gemini()
    if not agent:
        return ""
    try:
        resp = await agent.generate_response(prompt, system_override=system_prompt)
        model_name = getattr(agent.config, "model_name", None) or "gemini-2.5-flash"
        _record(model_name, "gemini", resp, feature)
        if resp.error:
            logger.warning("Gemini error: %s", resp.error)
            return ""
        return resp.content or ""
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return ""


def _record(model: str, provider: str, resp, feature: str):
    """Best-effort record usage — never let tracking break the actual call."""
    try:
        from products.fred_assistant.database import record_ai_usage
        record_ai_usage(
            model=model,
            provider=provider,
            input_tokens=getattr(resp, "input_tokens", 0) or 0,
            output_tokens=getattr(resp, "output_tokens", 0) or 0,
            latency_ms=(getattr(resp, "response_time", 0) or 0) * 1000,
            feature=feature,
            error=getattr(resp, "error", None),
        )
    except Exception as e:
        logger.debug("Usage recording failed (non-fatal): %s", e)
