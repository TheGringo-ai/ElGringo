"""
El Gringo MCP Server — Entry Point
====================================
Exposes El Gringo's multi-agent AI team as native MCP tools.
Claude Code can call these directly — no curl needed.

Setup in ~/.claude/mcp.json or project .mcp.json:
{
  "mcpServers": {
    "el-gringo": {
      "command": "python3",
      "args": ["/Users/fredtaylor/Development/Projects/ElGringo/elgringo/server/mcp_server.py"],
      "env": {
        "ELGRINGO_API_URL": "https://ai.chatterfix.com",
        "ELGRINGO_API_KEY": "your-api-key-here"
      }
    }
  }
}

Architecture:
  mcp_server.py  — This file. Shared utils (mcp, _api, formatters) + imports tool modules.
  tools_api.py   — 28 API-based tools (elgringo_*, ai_team_* that call REST API)
  tools_local.py — Local tools (memory, verify, costs, ROI, context, reflect)
  tools_moat.py  — Moat features + tier 1-3 + gap closers (guardian, nexus, cache, watchdog)
"""

import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("el-gringo-mcp")

mcp = FastMCP("el-gringo")

BASE_URL = os.environ.get("ELGRINGO_API_URL", "https://ai.chatterfix.com")
API_KEY = os.environ.get("ELGRINGO_API_KEY", "")

if not API_KEY:
    logger.warning("ELGRINGO_API_KEY not set — API calls will fail. Set it in your MCP config.")


# ── Shared Utilities ─────────────────────────────────────────────


def _api(method: str, path: str, body: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    """Make an API call to El Gringo. Uses urllib so we have zero extra deps."""
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    logger.info(f"{method} {path}")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        logger.error(f"HTTP {e.code} from {path}: {error_body[:200]}")
        return {"error": f"HTTP {e.code}: {error_body}"}
    except urllib.error.URLError as e:
        logger.error(f"Connection failed for {path}: {e.reason}")
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        logger.error(f"Unexpected error for {path}: {e}")
        return {"error": str(e)}


def _run_async(coro):
    """Run an async coroutine from sync code, even inside a running event loop.

    The MCP server already runs an event loop, so asyncio.run() / new_event_loop()
    will raise 'Cannot run the event loop while another loop is running'.
    Instead, spin up a *new* loop in a background thread.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=30)


def _get_memory():
    """Lazy-load memory system."""
    from elgringo.memory import MemorySystem
    if not hasattr(_get_memory, "_instance"):
        _get_memory._instance = MemorySystem()
    return _get_memory._instance


# ── Response Formatters ──────────────────────────────────────────

def _fmt_collaborate(result: dict) -> str:
    """Format a /v1/collaborate response."""
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    confidence = result.get("confidence", 0)
    answer = result.get("answer", "")
    return f"[Agents: {agents} | Confidence: {confidence:.0%}]\n\n{answer}"


def _fmt_code_task(result: dict) -> str:
    """Format a /v1/code/task response."""
    if "error" in result:
        return f"Error: {result['error']}"
    status = result.get("status", "unknown")
    summary = result.get("summary", "")
    agents = ", ".join(result.get("agents_used", []))
    iterations = result.get("iterations", 0)
    files_changed = result.get("files_changed", [])
    errors = result.get("errors", [])
    parts = [f"Status: {status}", f"Summary: {summary}", f"Agents: {agents}", f"Iterations: {iterations}"]
    if files_changed:
        parts.append(f"Files changed: {len(files_changed)}")
        for fc in files_changed:
            parts.append(f"  - {fc.get('path', '?')} ({fc.get('action', '?')})")
    if result.get("test_results"):
        tr = result["test_results"]
        parts.append(f"Tests: {'PASS' if tr.get('passed') else 'FAIL'} -- {tr.get('command', '')}")
    if errors:
        parts.append(f"Errors: {'; '.join(errors[:3])}")
    return "\n".join(parts)


def _fmt_review(result: dict) -> str:
    """Format a /v1/code/review response."""
    if "error" in result:
        return f"Error: {result['error']}"
    agents = ", ".join(result.get("agents_used", []))
    files = result.get("files_reviewed", 0)
    return f"[{files} files reviewed by {agents}]\n\n{result.get('findings', 'No findings')}"


# ── Import Tool Modules ──────────────────────────────────────────
# Each module registers its @mcp.tool() functions on import.
# Import order matters — FastMCP keeps the FIRST registration for each name.
from . import tools_api      # noqa: E402, F401 — 28 API tools
from . import tools_local    # noqa: E402, F401 — memory, validation, costs, context
from . import tools_moat     # noqa: E402, F401 — tier 1-3, gap closers, moat features


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
