"""
Session Manager — Multi-turn conversation support
===================================================

Maintains conversation history across collaborate() calls so agents
remember what was discussed previously. Sessions persist to disk.

Usage:
    result = await team.collaborate("Build auth API", session_id="my-session")
    # Later...
    result = await team.collaborate("Now add rate limiting", session_id="my-session")
    # Agents see the full conversation history
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path.home() / ".ai-dev-team" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

MAX_HISTORY_TOKENS = 4000  # Cap injected history to prevent prompt bloat
MAX_TURNS = 50  # Max turns before auto-summarize


@dataclass
class Turn:
    """A single turn in a session conversation."""
    role: str  # "user" or "team"
    content: str
    timestamp: str = ""
    agents: List[str] = field(default_factory=list)
    task_type: str = ""
    confidence: float = 0.0
    task_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class Session:
    """A multi-turn conversation session."""
    session_id: str
    project: str = "default"
    created: str = ""
    updated: str = ""
    turns: List[Turn] = field(default_factory=list)
    summary: str = ""  # Compressed summary of older turns
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created:
            self.created = now
        if not self.updated:
            self.updated = now

    def add_user_turn(self, content: str) -> Turn:
        """Add a user message to the session."""
        turn = Turn(role="user", content=content)
        self.turns.append(turn)
        self.updated = datetime.now(timezone.utc).isoformat()
        return turn

    def add_team_turn(
        self,
        content: str,
        agents: List[str] = None,
        task_type: str = "",
        confidence: float = 0.0,
        task_id: str = "",
    ) -> Turn:
        """Add a team response to the session."""
        turn = Turn(
            role="team",
            content=content,
            agents=agents or [],
            task_type=task_type,
            confidence=confidence,
            task_id=task_id,
        )
        self.turns.append(turn)
        self.updated = datetime.now(timezone.utc).isoformat()
        return turn

    def get_context_block(self, max_chars: int = 8000) -> str:
        """
        Build a context block from session history for prompt injection.

        Returns recent conversation turns formatted for the AI team,
        capped at max_chars to prevent prompt bloat.
        """
        if not self.turns:
            return ""

        lines = ["CONVERSATION HISTORY (you are continuing an ongoing discussion):"]

        # Include summary of older turns if available
        if self.summary:
            lines.append(f"\n[Earlier discussion summary]: {self.summary}")

        # Walk turns from newest to oldest, building up context
        turn_blocks = []
        char_count = len("\n".join(lines))

        for turn in reversed(self.turns):
            if turn.role == "user":
                block = f"\nUser: {turn.content}"
            else:
                # Truncate long team responses to key points
                content = turn.content
                if len(content) > 500:
                    content = content[:500] + "..."
                agents_str = f" [{', '.join(turn.agents)}]" if turn.agents else ""
                block = f"\nTeam{agents_str}: {content}"

            if char_count + len(block) > max_chars:
                break
            turn_blocks.append(block)
            char_count += len(block)

        # Reverse back to chronological order
        turn_blocks.reverse()
        lines.extend(turn_blocks)
        lines.append("\n---")
        lines.append("Continue the conversation. Reference previous discussion when relevant.\n")

        return "\n".join(lines)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def needs_summarize(self) -> bool:
        return self.turn_count > MAX_TURNS


class SessionManager:
    """Manages multi-turn sessions with persistence."""

    def __init__(self):
        self._cache: Dict[str, Session] = {}

    def get_or_create(self, session_id: str, project: str = "default") -> Session:
        """Get an existing session or create a new one."""
        if session_id in self._cache:
            return self._cache[session_id]

        # Try loading from disk
        path = SESSIONS_DIR / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                turns = [Turn(**t) for t in data.get("turns", [])]
                session = Session(
                    session_id=data["session_id"],
                    project=data.get("project", project),
                    created=data.get("created", ""),
                    updated=data.get("updated", ""),
                    turns=turns,
                    summary=data.get("summary", ""),
                    metadata=data.get("metadata", {}),
                )
                self._cache[session_id] = session
                logger.info(f"Loaded session {session_id} ({session.turn_count} turns)")
                return session
            except Exception as e:
                logger.warning(f"Failed to load session {session_id}: {e}")

        # Create new session
        session = Session(session_id=session_id, project=project)
        self._cache[session_id] = session
        logger.info(f"Created new session {session_id}")
        return session

    def save(self, session: Session):
        """Persist session to disk."""
        path = SESSIONS_DIR / f"{session.session_id}.json"
        data = {
            "session_id": session.session_id,
            "project": session.project,
            "created": session.created,
            "updated": session.updated,
            "summary": session.summary,
            "metadata": session.metadata,
            "turns": [asdict(t) for t in session.turns],
        }
        path.write_text(json.dumps(data, indent=2))

    def list_sessions(self, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by project."""
        sessions = []
        for path in SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if project and data.get("project") != project:
                    continue
                sessions.append({
                    "session_id": data["session_id"],
                    "project": data.get("project", "default"),
                    "turns": len(data.get("turns", [])),
                    "created": data.get("created", ""),
                    "updated": data.get("updated", ""),
                })
            except Exception:
                continue
        sessions.sort(key=lambda s: s.get("updated", ""), reverse=True)
        return sessions

    def delete(self, session_id: str):
        """Delete a session."""
        self._cache.pop(session_id, None)
        path = SESSIONS_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()

    async def summarize_session(self, session: Session, agent) -> str:
        """Use an AI agent to compress old turns into a summary."""
        if session.turn_count <= 10:
            return session.summary

        # Grab the oldest turns (keep recent 10 intact)
        old_turns = session.turns[:-10]
        old_text = "\n".join(
            f"{'User' if t.role == 'user' else 'Team'}: {t.content[:300]}"
            for t in old_turns
        )

        prompt = (
            "Summarize this conversation history in 3-5 bullet points. "
            "Focus on decisions made, code discussed, and action items.\n\n"
            f"{old_text[:4000]}"
        )

        try:
            response = await agent.generate_response(prompt)
            if response.success:
                session.summary = response.content
                session.turns = session.turns[-10:]  # Keep only recent turns
                self.save(session)
                logger.info(f"Summarized session {session.session_id}: {len(old_turns)} turns compressed")
                return session.summary
        except Exception as e:
            logger.warning(f"Session summarization failed: {e}")

        return session.summary


# Singleton
_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
