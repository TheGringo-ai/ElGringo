"""NLP parser for quick capture — AI-powered with heuristic fallback."""

import json
import logging
import re
from datetime import date, timedelta

from products.fred_assistant.services import task_service

logger = logging.getLogger(__name__)

# ── Public API ───────────────────────────────────────────────────────


async def parse_capture_text(text: str, default_board_id: str | None = None) -> dict:
    """Parse free-text into structured task fields.

    Runs heuristic first (instant), then AI, merges results.
    AI wins for non-null fields; heuristic fills gaps.
    Returns dict compatible with task_service.create_task().
    """
    board_id = default_board_id or "work"
    heuristic = _heuristic_parse(text, board_id)

    ai_result = await _ai_parse(text, board_id)

    if ai_result:
        merged = {**heuristic, **{k: v for k, v in ai_result.items() if v is not None}}
        # Validate board_id against actual boards
        valid_boards = {b["id"] for b in task_service.list_boards()}
        if merged.get("board_id") not in valid_boards:
            merged["board_id"] = board_id
        # Clamp priority
        if merged.get("priority") is not None:
            merged["priority"] = max(1, min(5, merged["priority"]))
        merged["_parsed_by"] = "ai"
        return merged

    heuristic["_parsed_by"] = "heuristic"
    return heuristic


# ── AI parser ────────────────────────────────────────────────────────


async def _ai_parse(text: str, default_board_id: str) -> dict | None:
    """Use Gemini to parse capture text. Returns dict or None on failure."""
    try:
        from products.fred_assistant.services.assistant import _get_gemini
    except ImportError:
        logger.debug("assistant module not available")
        return None

    agent = _get_gemini()
    if not agent:
        return None

    today = date.today()
    weekday = today.strftime("%A")

    # Pre-compute date anchors (LLMs are bad at date math)
    anchors = _date_anchors(today)

    boards = task_service.list_boards()
    board_list = ", ".join(f'"{b["id"]}"' for b in boards) if boards else '"work"'

    system_prompt = (
        "You are a task parser. Extract structured data from the user's quick capture text.\n"
        f"Today is {today.isoformat()} ({weekday}).\n"
        f"Available boards: [{board_list}]\n\n"
        "Return ONLY valid JSON with these fields:\n"
        '{"title", "description", "board_id", "priority", "due_date", "due_time", '
        '"tags", "recurring", "category"}\n\n'
        "Rules:\n"
        '- "urgent"/"asap"/"critical" → priority 1, "important"/"high" → 2, '
        '"low"/"eventually"/"someday" → 5\n'
        "- No priority mentioned → null\n"
        f'- "tomorrow" → "{anchors["tomorrow"]}"\n'
        f'- "today" → "{anchors["today"]}"\n'
        f'- "by Friday"/"on Friday" → "{anchors["friday"]}"\n'
        f'- "by Monday"/"on Monday"/"next Monday" → "{anchors["monday"]}"\n'
        f'- "end of month" → "{anchors["end_of_month"]}"\n'
        f'- "next week" → "{anchors["next_week"]}"\n'
        '- "#tag" in text → extract as tag, remove from title\n'
        '- "every day" → recurring: "daily", "every week" → "weekly", '
        '"every month" → "monthly"\n'
        "- title should be the clean task description without metadata words\n"
        "- If unsure about any field → null (don't guess)\n"
        '- due_date format: "YYYY-MM-DD", due_time format: "HH:MM"\n'
    )

    try:
        resp = await agent.generate_response(text, system_override=system_prompt)
        if resp.error:
            logger.debug("Gemini error in NLP parse: %s", resp.error)
            return None
        raw = resp.content or ""
    except Exception as e:
        logger.debug("AI parse failed: %s", e)
        return None

    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed, dict):
        return None

    # Normalize types
    result = {}
    if parsed.get("title"):
        result["title"] = str(parsed["title"]).strip()
    if parsed.get("description"):
        result["description"] = str(parsed["description"]).strip()
    if parsed.get("board_id"):
        result["board_id"] = str(parsed["board_id"]).strip()
    if parsed.get("priority") is not None:
        try:
            result["priority"] = int(parsed["priority"])
        except (ValueError, TypeError):
            pass
    if parsed.get("due_date"):
        result["due_date"] = str(parsed["due_date"]).strip()
    if parsed.get("due_time"):
        result["due_time"] = str(parsed["due_time"]).strip()
    if parsed.get("tags") and isinstance(parsed["tags"], list):
        result["tags"] = [str(t).strip() for t in parsed["tags"] if t]
    if parsed.get("recurring"):
        result["recurring"] = str(parsed["recurring"]).strip()
    if parsed.get("category"):
        result["category"] = str(parsed["category"]).strip()

    return result if result else None


def _date_anchors(today: date) -> dict:
    """Pre-compute common date references from today."""
    anchors = {
        "today": today.isoformat(),
        "tomorrow": (today + timedelta(days=1)).isoformat(),
        "end_of_month": (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
    }
    anchors["end_of_month"] = anchors["end_of_month"].isoformat()

    # Next occurrence of each weekday
    for name, target_weekday in [("monday", 0), ("friday", 4)]:
        days_ahead = (target_weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # always next occurrence, not today
        anchors[name] = (today + timedelta(days=days_ahead)).isoformat()

    anchors["next_week"] = anchors["monday"]
    return anchors


# ── Heuristic parser ─────────────────────────────────────────────────

# Priority keywords
_PRIORITY_RULES = [
    (1, ["urgent", "asap", "critical", "emergency"]),
    (2, ["important", "high", "high priority"]),
    (5, ["low", "eventually", "someday", "whenever", "low priority"]),
]

# Board detection keywords
_BOARD_RULES = [
    ("health", ["gym", "workout", "run", "health", "doctor", "exercise", "diet"]),
    ("ideas", ["idea", "research", "explore", "investigate", "brainstorm"]),
    ("personal", ["personal", "home", "groceries", "call", "appointment", "family"]),
    ("fredai", ["fredai", "deploy", "code", "fix", "build", "feature", "bug", "api"]),
]

# Recurring patterns (pre-compiled)
_RECURRING_PATTERNS = [
    ("daily", re.compile(r"\bevery\s+day\b")),
    ("weekly", re.compile(r"\bevery\s+week\b")),
    ("monthly", re.compile(r"\bevery\s+month\b")),
    ("daily", re.compile(r"\bdaily\b")),
    ("weekly", re.compile(r"\bweekly\b")),
    ("monthly", re.compile(r"\bmonthly\b")),
]

# Day name → weekday number (Monday=0)
_DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# Pre-compiled regexes used in parsing
_RE_HASHTAG = re.compile(r"#(\w+)")
_RE_HASHTAG_STRIP = re.compile(r"\s*#\w+")
_RE_TODAY = re.compile(r"\btoday\b")
_RE_DAY_REF = re.compile(r"\b(?:by|on|next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")
_RE_PRIORITY = re.compile(r"\b(urgent|asap|critical|important|high priority|low priority)\b", re.IGNORECASE)
_RE_DATE_REF = re.compile(r"\b(by|on|next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)\b", re.IGNORECASE)
_RE_RECURRING = re.compile(r"\b(every\s+(?:day|week|month)|daily|weekly|monthly)\b", re.IGNORECASE)
_RE_WHITESPACE = re.compile(r"\s{2,}")
_RE_FENCED_JSON = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
_RE_EMBEDDED_JSON = re.compile(r"\{.*\}", re.DOTALL)


def _heuristic_parse(text: str, default_board_id: str) -> dict:
    """Fast keyword-based parsing. Enhanced from original capture.py heuristics."""
    lower = text.lower()
    result: dict = {
        "title": text.strip(),
        "status": "todo",
        "board_id": default_board_id,
    }

    # ── Priority ──
    priority = None
    for level, keywords in _PRIORITY_RULES:
        if any(w in lower for w in keywords):
            priority = level
            break
    if priority is not None:
        result["priority"] = priority

    # ── Board ──
    for board_id, keywords in _BOARD_RULES:
        if any(w in lower for w in keywords):
            result["board_id"] = board_id
            break

    # ── Tags (#hashtag extraction) ──
    tags = _RE_HASHTAG.findall(text)
    if tags:
        result["tags"] = [t.lower() for t in tags]
        # Remove hashtags from title
        result["title"] = _RE_HASHTAG_STRIP.sub("", result["title"]).strip()

    # ── Due date (day names) ──
    due_date = _parse_day_reference(lower)
    if due_date:
        result["due_date"] = due_date

    # ── Recurring ──
    for recurrence, pattern in _RECURRING_PATTERNS:
        if pattern.search(lower):
            result["recurring"] = recurrence
            break

    # ── Title cleanup ──
    result["title"] = _clean_title(result["title"])

    return result


def _parse_day_reference(text: str) -> str | None:
    """Extract due date from day-name references like 'by Friday' or 'tomorrow'."""
    today = date.today()

    if "tomorrow" in text:
        return (today + timedelta(days=1)).isoformat()
    if _RE_TODAY.search(text):
        return today.isoformat()

    # "by <day>" or "on <day>" or "next <day>"
    m = _RE_DAY_REF.search(text)
    if m:
        target_day = _DAY_NAMES[m.group(1)]
        days_ahead = (target_day - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()

    return None


def _clean_title(title: str) -> str:
    """Remove metadata words from title to keep it clean."""
    # Remove priority markers
    title = _RE_PRIORITY.sub("", title)
    # Remove date references
    title = _RE_DATE_REF.sub("", title)
    # Remove recurring markers
    title = _RE_RECURRING.sub("", title)
    # Collapse whitespace and trim
    title = _RE_WHITESPACE.sub(" ", title).strip()
    # Remove leading/trailing punctuation left over
    title = title.strip(" ,.-")
    return title


# ── JSON extraction ──────────────────────────────────────────────────


def _extract_json(text: str) -> dict | None:
    """Extract JSON from AI response — handles plain, fenced, or embedded JSON."""
    if not text or not text.strip():
        return None

    text = text.strip()

    # Try plain JSON
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try markdown-fenced JSON (```json ... ``` or ``` ... ```)
    m = _RE_FENCED_JSON.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Try finding first { ... } block
    m = _RE_EMBEDDED_JSON.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None
