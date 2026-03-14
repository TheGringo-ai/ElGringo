"""
Benchmark Endpoints
====================

Run prompts through agents and compare speed, cost, and quality.

POST /v1/benchmark       — Run a benchmark (all agents or specific ones)
GET  /v1/benchmark/history — Last 50 benchmark results
GET  /v1/leaderboard      — Agent leaderboard from accumulated benchmarks
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# ── In-memory storage ────────────────────────────────────────────────

_benchmark_history: List[Dict[str, Any]] = []
_MAX_HISTORY = 200


# ── Models ───────────────────────────────────────────────────────────

class BenchmarkRequest(BaseModel):
    task: str = Field(..., description="Prompt / task to benchmark")
    agents: Optional[List[str]] = Field(None, description="Agents to test (None = all available)")
    mode: str = Field("turbo", description="Collaboration mode per agent (turbo = single agent)")


class AgentBenchmark(BaseModel):
    agent: str
    response_time: float
    input_tokens: int
    output_tokens: int
    confidence: float
    success: bool
    error: Optional[str] = None
    snippet: str = Field("", description="First 200 chars of response")


class BenchmarkResponse(BaseModel):
    benchmark_id: str
    task: str
    total_time: float
    agent_count: int
    results: List[AgentBenchmark]
    winner: Optional[str] = None
    timestamp: str


class LeaderboardEntry(BaseModel):
    agent: str
    runs: int
    avg_time: float
    avg_confidence: float
    success_rate: float
    total_tokens: int
    wins: int


# ── Helpers ──────────────────────────────────────────────────────────

def _get_team():
    """Lazy import to avoid circular deps."""
    from elgringo.orchestrator import AIDevTeam
    return AIDevTeam(enable_memory=False)


async def _benchmark_single_agent(team, agent_name: str, task: str, mode: str) -> AgentBenchmark:
    """Run a single agent and capture metrics."""
    t0 = time.time()
    try:
        result = await team.collaborate(task, mode=mode, agents=[agent_name])
        elapsed = time.time() - t0
        return AgentBenchmark(
            agent=agent_name,
            response_time=round(elapsed, 3),
            input_tokens=result.metadata.get("input_tokens", 0) if result.metadata else 0,
            output_tokens=result.metadata.get("output_tokens", 0) if result.metadata else 0,
            confidence=round(result.confidence_score, 3),
            success=result.success,
            error=None if result.success else (result.final_answer or "unknown error")[:200],
            snippet=(result.final_answer or "")[:200],
        )
    except Exception as e:
        elapsed = time.time() - t0
        return AgentBenchmark(
            agent=agent_name,
            response_time=round(elapsed, 3),
            input_tokens=0,
            output_tokens=0,
            confidence=0.0,
            success=False,
            error=str(e)[:200],
        )


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/v1/benchmark", response_model=BenchmarkResponse)
async def run_benchmark(request: BenchmarkRequest):
    """Run a prompt through multiple agents in parallel and compare results."""
    team = _get_team()
    available = list(team.agents.keys())

    if not available:
        raise HTTPException(status_code=503, detail="No agents available")

    target_agents = request.agents or available
    # Filter to only available agents
    target_agents = [a for a in target_agents if a in team.agents]
    if not target_agents:
        raise HTTPException(status_code=400, detail=f"None of the requested agents are available. Available: {available}")

    benchmark_id = str(uuid.uuid4())[:8]
    t0 = time.time()

    # Run all agents in parallel
    tasks = [
        _benchmark_single_agent(team, agent, request.task, request.mode)
        for agent in target_agents
    ]
    results = await asyncio.gather(*tasks)
    total_time = round(time.time() - t0, 3)

    # Determine winner (fastest successful response with highest confidence)
    successful = [r for r in results if r.success]
    winner = None
    if successful:
        # Score = confidence / response_time (higher is better)
        winner = max(successful, key=lambda r: r.confidence / max(r.response_time, 0.01)).agent

    # Store in history
    entry = {
        "benchmark_id": benchmark_id,
        "task": request.task[:200],
        "total_time": total_time,
        "agent_count": len(results),
        "results": [r.model_dump() for r in results],
        "winner": winner,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _benchmark_history.append(entry)
    if len(_benchmark_history) > _MAX_HISTORY:
        _benchmark_history.pop(0)

    return BenchmarkResponse(
        benchmark_id=benchmark_id,
        task=request.task[:200],
        total_time=total_time,
        agent_count=len(results),
        results=results,
        winner=winner,
        timestamp=entry["timestamp"],
    )


@router.get("/v1/benchmark/history")
async def get_benchmark_history(limit: int = 50):
    """Return recent benchmark results."""
    return {
        "history": _benchmark_history[-limit:],
        "count": len(_benchmark_history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/v1/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard():
    """Aggregate leaderboard from all stored benchmarks."""
    if not _benchmark_history:
        return []

    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "runs": 0, "total_time": 0.0, "total_confidence": 0.0,
        "successes": 0, "total_tokens": 0, "wins": 0,
    })

    for entry in _benchmark_history:
        winner = entry.get("winner")
        for r in entry.get("results", []):
            agent = r["agent"]
            s = stats[agent]
            s["runs"] += 1
            s["total_time"] += r["response_time"]
            s["total_confidence"] += r["confidence"]
            s["total_tokens"] += r.get("input_tokens", 0) + r.get("output_tokens", 0)
            if r["success"]:
                s["successes"] += 1
            if agent == winner:
                s["wins"] += 1

    leaderboard = []
    for agent, s in stats.items():
        runs = s["runs"]
        leaderboard.append(LeaderboardEntry(
            agent=agent,
            runs=runs,
            avg_time=round(s["total_time"] / max(runs, 1), 3),
            avg_confidence=round(s["total_confidence"] / max(runs, 1), 3),
            success_rate=round(s["successes"] / max(runs, 1), 3),
            total_tokens=s["total_tokens"],
            wins=s["wins"],
        ))

    # Sort by wins desc, then avg_confidence desc
    leaderboard.sort(key=lambda x: (-x.wins, -x.avg_confidence))
    return leaderboard
