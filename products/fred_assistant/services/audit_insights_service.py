"""
Audit Insights Service — Parse raw audit findings into structured JSON,
apply fixes to project files, and stream contextual chat about findings.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


def _resolve_project_path(name):
    from products.fred_assistant.services.fred_tools import _resolve_project_path as _rpp
    return _rpp(name)


def _validate_path(path):
    from products.fred_assistant.services.fred_tools import validate_path
    return validate_path(path)


# ── LLM helper (shared singleton from llm_shared.py) ────────────────


def _get_gemini():
    from products.fred_assistant.services.llm_shared import get_gemini
    return get_gemini()


async def _llm_response(prompt: str, system_prompt: str) -> str:
    from products.fred_assistant.services.llm_shared import llm_response
    return await llm_response(prompt, system_prompt)


# ── Parse audit findings ─────────────────────────────────────────────

PARSE_SYSTEM_PROMPT = """You are a code audit analyst. Extract structured findings from raw audit markdown.

Return ONLY a JSON array. Each finding object must have:
- id: string (f1, f2, f3...)
- severity: "critical" | "high" | "medium" | "low" | "info"
- title: short descriptive title
- description: detailed explanation
- category: "security" | "performance" | "quality" | "bug" | "style" | "best-practice"
- file: file path if mentioned (empty string if not)
- line: line number if mentioned (0 if not)
- code_snippet: relevant code if shown (empty string if not)
- suggested_fix: corrected code or fix description (empty string if not available)
- explanation: why the fix works

If no findings can be extracted, return a single info-level finding summarizing the content.
Return ONLY the JSON array, no markdown fences, no explanation."""


async def parse_audit_findings(raw_findings: str, project_name: str, language: str = "python") -> list[dict]:
    """Parse raw markdown audit findings into structured JSON."""
    truncated = raw_findings[:8000]

    prompt = f"""Project: {project_name}
Language: {language}

Raw audit output:
{truncated}"""

    response = await _llm_response(prompt, PARSE_SYSTEM_PROMPT)
    if not response:
        return [_fallback_finding(raw_findings)]

    # Try to extract JSON from the response
    try:
        # Strip markdown fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        findings = json.loads(cleaned)
        if isinstance(findings, list) and len(findings) > 0:
            return findings
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse LLM findings JSON, using fallback")

    return [_fallback_finding(raw_findings)]


def _fallback_finding(raw: str) -> dict:
    return {
        "id": "f1",
        "severity": "info",
        "title": "Audit Results",
        "description": raw[:2000],
        "category": "quality",
        "file": "",
        "line": 0,
        "code_snippet": "",
        "suggested_fix": "",
        "explanation": "Raw audit output — AI parsing unavailable.",
    }


# ── Apply fix to file ───────────────────────────────────────────────

FIX_SYSTEM_PROMPT = """You are a code fix applicator. You receive:
1. The FULL current file content
2. A code snippet that has a problem
3. The suggested fix for that snippet

Your job: return the COMPLETE file with the fix applied at the correct location.
Return ONLY the full corrected file content — no markdown fences, no explanation, no commentary.
If you can't find where to apply the fix, return the original file unchanged."""

MAX_FIX_FILE_SIZE = 100_000


async def apply_fix_to_file(project_name: str, file_path: str, code_snippet: str, suggested_fix: str, description: str = "") -> dict:
    """Read the actual file, use LLM to apply the fix at the right location, write back."""
    proj_path = _resolve_project_path(project_name)
    if not proj_path:
        return {"success": False, "error": f"Project not found: {project_name}"}

    full_path = os.path.join(proj_path, file_path)
    try:
        resolved = _validate_path(full_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if not os.path.isfile(resolved):
        return {"success": False, "error": f"File not found: {file_path}"}

    # Read current file content
    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            original = f.read(MAX_FIX_FILE_SIZE)
    except Exception as e:
        return {"success": False, "error": f"Cannot read file: {e}"}

    # If the suggested_fix is empty, nothing to do
    if not suggested_fix.strip():
        return {"success": False, "error": "No fix content provided"}

    # Try simple string replacement first (fastest, no LLM needed)
    if code_snippet and code_snippet.strip() in original:
        patched = original.replace(code_snippet.strip(), suggested_fix.strip(), 1)
        try:
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(patched)
            return {"success": True, "path": resolved, "method": "direct_replace"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Fallback: use LLM to apply the fix intelligently
    prompt = f"""Current file ({file_path}):
```
{original[:6000]}
```

Problem code:
```
{code_snippet}
```

Suggested fix:
```
{suggested_fix}
```

{f"Description: {description}" if description else ""}

Return the COMPLETE corrected file."""

    patched = await _llm_response(prompt, FIX_SYSTEM_PROMPT)
    if not patched or patched.strip() == original.strip():
        return {"success": False, "error": "AI could not determine where to apply the fix"}

    # Strip markdown fences if LLM wrapped the output
    cleaned = patched.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]

    try:
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(cleaned)
        return {"success": True, "path": resolved, "method": "ai_patch"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Stream audit chat ────────────────────────────────────────────────

AUDIT_CHAT_SYSTEM = """You are Fred, an AI code audit specialist. You're discussing code audit findings with a developer.

Context — these are the audit findings for the project:
{findings_context}

Be concise, actionable, and specific. Reference file paths and line numbers when relevant.
If asked to fix something, provide the complete corrected code.
If asked to explain, give clear technical explanations."""


REVIEW_CHAT_SYSTEM = """You are Fred, an AI code review specialist. You're discussing code review results with a developer.

Project: {project_name}
Health Score: {health_score}/100

Action Items:
{action_items}

TODOs/FIXMEs found:
{todo_items}

Be concise, actionable, and specific. Reference file paths and line numbers.
When asked to fix something, provide the complete corrected code.
When asked to prioritize, consider severity and business impact."""


async def stream_audit_chat(message: str, project_name: str, findings: list[dict], finding_id: str | None = None):
    """Stream an AI response about audit findings. Yields {type, data} dicts."""
    # Build findings context
    if finding_id:
        focused = [f for f in findings if f.get("id") == finding_id]
        if focused:
            context = json.dumps(focused[0], indent=2)
        else:
            context = json.dumps(findings[:5], indent=2)
    else:
        context = json.dumps(findings[:5], indent=2)

    system = AUDIT_CHAT_SYSTEM.format(findings_context=context)
    full_prompt = f"Project: {project_name}\n\nUser question: {message}"

    agent = _get_gemini()
    if not agent:
        yield {"type": "token", "data": "AI service unavailable. Please try again later."}
        yield {"type": "done", "data": ""}
        return

    try:
        # Check if agent supports streaming
        if hasattr(agent, "stream_response"):
            async for chunk in agent.stream_response(full_prompt, system_override=system):
                if hasattr(chunk, "content") and chunk.content:
                    yield {"type": "token", "data": chunk.content}
                elif isinstance(chunk, str):
                    yield {"type": "token", "data": chunk}
        else:
            # Fallback: get full response and yield at once
            resp = await agent.generate_response(full_prompt, system_override=system)
            content = resp.content or "I couldn't generate a response. Please try again."
            # Yield in chunks to simulate streaming
            chunk_size = 20
            for i in range(0, len(content), chunk_size):
                yield {"type": "token", "data": content[i:i + chunk_size]}
    except Exception as e:
        logger.warning("Audit chat error: %s", e)
        yield {"type": "token", "data": f"Error: {e}"}

    yield {"type": "done", "data": ""}


# ── Stream review chat (for CodeReviewPanel) ─────────────────────────

async def stream_review_chat(message: str, project_name: str, review_data: dict):
    """Stream an AI response about code review findings. Yields {type, data} dicts."""
    action_items = review_data.get("action_items", [])
    todo_items = review_data.get("todo_items", [])
    health_score = review_data.get("health_score", "N/A")

    actions_text = "\n".join(
        f"- [{a.get('severity', 'medium')}] {a.get('title', '')} — {a.get('detail', '')}"
        for a in action_items[:10]
    ) or "None"

    todos_text = "\n".join(
        f"- [{t.get('type', 'TODO')}] {t.get('file', '')}:{t.get('line', '')} — {t.get('text', '')}"
        for t in todo_items[:10]
    ) or "None"

    system = REVIEW_CHAT_SYSTEM.format(
        project_name=project_name,
        health_score=health_score,
        action_items=actions_text,
        todo_items=todos_text,
    )
    full_prompt = f"User question: {message}"

    agent = _get_gemini()
    if not agent:
        yield {"type": "token", "data": "AI service unavailable. Please try again later."}
        yield {"type": "done", "data": ""}
        return

    try:
        if hasattr(agent, "stream_response"):
            async for chunk in agent.stream_response(full_prompt, system_override=system):
                if hasattr(chunk, "content") and chunk.content:
                    yield {"type": "token", "data": chunk.content}
                elif isinstance(chunk, str):
                    yield {"type": "token", "data": chunk}
        else:
            resp = await agent.generate_response(full_prompt, system_override=system)
            content = resp.content or "I couldn't generate a response. Please try again."
            chunk_size = 20
            for i in range(0, len(content), chunk_size):
                yield {"type": "token", "data": content[i:i + chunk_size]}
    except Exception as e:
        logger.warning("Review chat error: %s", e)
        yield {"type": "token", "data": f"Error: {e}"}

    yield {"type": "done", "data": ""}
