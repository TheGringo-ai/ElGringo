"""
Benchmark Runner - Compare agents on standardized prompts
==========================================================

Runs the same prompts through each agent, scores outputs, and builds
a routing table of which agent is best at which task type.

Scoring uses:
- Keyword coverage (30%): Does the response contain expected keywords?
- Structural quality (30%): Code blocks, formatting, length
- Cross-agent evaluation (40%): Use best agent as judge
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.path.expanduser("~/.ai-dev-team/benchmarks"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# Benchmark prompt sets per task type
BENCHMARK_PROMPTS = {
    "coding": [
        {
            "id": "code_01",
            "prompt": "Write a Python function that finds the longest palindromic substring in a string. Include type hints and a docstring.",
            "expected_keywords": ["def", "palindrome", "return", "str", "->"],
        },
        {
            "id": "code_02",
            "prompt": "Implement a thread-safe LRU cache in Python with O(1) get and put operations.",
            "expected_keywords": ["class", "get", "put", "OrderedDict", "Lock", "threading"],
        },
        {
            "id": "code_03",
            "prompt": "Write a FastAPI endpoint that handles CSV file uploads, validates columns, and returns summary statistics.",
            "expected_keywords": ["FastAPI", "UploadFile", "async", "def", "return"],
        },
    ],
    "debugging": [
        {
            "id": "debug_01",
            "prompt": (
                "This Python code has a race condition. Find and fix it:\n"
                "```python\nimport threading\ncounter = 0\n"
                "def increment():\n    global counter\n    for _ in range(100000):\n        counter += 1\n"
                "threads = [threading.Thread(target=increment) for _ in range(4)]\n"
                "for t in threads: t.start()\nfor t in threads: t.join()\nprint(counter)\n```"
            ),
            "expected_keywords": ["Lock", "lock", "acquire", "threading", "race"],
        },
        {
            "id": "debug_02",
            "prompt": (
                "This async function leaks connections. Find the bug and fix it:\n"
                "```python\nasync def fetch_data(urls):\n    results = []\n"
                "    for url in urls:\n        session = aiohttp.ClientSession()\n"
                "        resp = await session.get(url)\n        results.append(await resp.json())\n"
                "    return results\n```"
            ),
            "expected_keywords": ["close", "async with", "session", "context manager"],
        },
    ],
    "architecture": [
        {
            "id": "arch_01",
            "prompt": "Design a microservices architecture for a real-time notification system that handles 10K messages/second. Include service boundaries, communication patterns, and data flow.",
            "expected_keywords": ["queue", "service", "scale", "kafka", "websocket"],
        },
        {
            "id": "arch_02",
            "prompt": "Design the database schema and API for a multi-tenant SaaS application with role-based access control. Consider data isolation strategies.",
            "expected_keywords": ["tenant", "role", "permission", "schema", "isolation"],
        },
    ],
    "security": [
        {
            "id": "sec_01",
            "prompt": "Review this FastAPI authentication code for security issues and suggest fixes:\n```python\n@app.post('/login')\nasync def login(username: str, password: str):\n    user = db.query(f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\")\n    if user:\n        token = base64.b64encode(f'{username}:{time.time()}'.encode()).decode()\n        return {'token': token}\n```",
            "expected_keywords": ["injection", "SQL", "hash", "bcrypt", "parameterized", "JWT"],
        },
    ],
}


@dataclass
class BenchmarkResult:
    """Result from a single agent on a single prompt."""
    agent_name: str
    task_type: str
    prompt_id: str
    response_time: float
    input_tokens: int
    output_tokens: int
    cost: float
    keyword_score: float
    structure_score: float
    eval_score: float
    composite_score: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class BenchmarkSuite:
    """Results from a full benchmark run."""
    suite_id: str
    task_type: str
    timestamp: str
    results: List[BenchmarkResult]
    agent_rankings: Dict[str, float]  # agent_name -> avg composite score


class BenchmarkRunner:
    """
    Runs standardized benchmarks across agents and builds a routing table.

    Usage:
        runner = BenchmarkRunner(team)
        suite = await runner.run_benchmark("coding")
        table = runner.get_routing_table()
    """

    def __init__(self, team: Any):
        self._team = team
        self._results_dir = STORAGE_DIR / "results"
        self._results_dir.mkdir(parents=True, exist_ok=True)

    async def run_benchmark(
        self,
        task_type: str,
        agent_names: Optional[List[str]] = None,
        evaluator_name: Optional[str] = None,
    ) -> BenchmarkSuite:
        """
        Run benchmark for a task type across all available agents.

        Args:
            task_type: One of the BENCHMARK_PROMPTS keys, or "all"
            agent_names: Specific agents to benchmark (default: all available)
            evaluator_name: Agent to use as judge (default: first available cloud agent)
        """
        if task_type == "all":
            all_results = []
            all_rankings = {}
            for tt in BENCHMARK_PROMPTS:
                suite = await self.run_benchmark(tt, agent_names, evaluator_name)
                all_results.extend(suite.results)
                for agent, score in suite.agent_rankings.items():
                    if agent not in all_rankings:
                        all_rankings[agent] = []
                    all_rankings[agent].append(score)

            # Average across task types
            avg_rankings = {
                agent: sum(scores) / len(scores)
                for agent, scores in all_rankings.items()
            }
            combined = BenchmarkSuite(
                suite_id=f"benchmark_all_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                task_type="all",
                timestamp=datetime.now(timezone.utc).isoformat(),
                results=all_results,
                agent_rankings=avg_rankings,
            )
            self._save_suite(combined)
            return combined

        prompts = BENCHMARK_PROMPTS.get(task_type, [])
        if not prompts:
            raise ValueError(f"No benchmark prompts for task type: {task_type}. Available: {list(BENCHMARK_PROMPTS.keys())}")

        # Determine agents to test
        agents = {}
        for name, agent in self._team.agents.items():
            if agent_names and name not in agent_names:
                continue
            try:
                if await agent.is_available():
                    agents[name] = agent
            except Exception:
                pass

        if not agents:
            raise ValueError("No available agents to benchmark")

        # Pick evaluator (prefer ChatGPT or Claude for judging)
        evaluator = None
        if evaluator_name and evaluator_name in agents:
            evaluator = agents[evaluator_name]
        else:
            for pref in ["chatgpt-coder", "claude-analyst", "grok-reasoner"]:
                if pref in agents:
                    evaluator = agents[pref]
                    break

        results = []
        agent_scores: Dict[str, List[float]] = {}

        for prompt_config in prompts:
            for agent_name, agent in agents.items():
                try:
                    result = await self._run_single(
                        agent, prompt_config, task_type, evaluator
                    )
                    results.append(result)
                    if agent_name not in agent_scores:
                        agent_scores[agent_name] = []
                    agent_scores[agent_name].append(result.composite_score)
                except Exception as e:
                    logger.warning(f"Benchmark failed for {agent_name} on {prompt_config['id']}: {e}")

        # Compute rankings
        rankings = {
            name: round(sum(scores) / len(scores), 3)
            for name, scores in agent_scores.items()
            if scores
        }

        suite = BenchmarkSuite(
            suite_id=f"benchmark_{task_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            task_type=task_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=results,
            agent_rankings=rankings,
        )

        self._save_suite(suite)
        return suite

    async def _run_single(
        self,
        agent: Any,
        prompt_config: Dict,
        task_type: str,
        evaluator: Optional[Any],
    ) -> BenchmarkResult:
        """Run a single agent on a single prompt and score it."""
        response = await agent.generate_response(prompt_config["prompt"])

        keyword_score = self._keyword_score(response.content, prompt_config["expected_keywords"])
        structure_score = self._structure_score(response.content)

        # AI evaluation
        eval_score = 0.5  # default if no evaluator
        if evaluator and evaluator.name != agent.name:
            eval_score = await self._ai_eval(evaluator, prompt_config["prompt"], response.content)

        composite = (keyword_score * 0.3) + (structure_score * 0.3) + (eval_score * 0.4)

        # Estimate cost
        from .cost_optimizer import MODEL_COSTS
        model = response.metadata.get("model", "") or ""
        costs = MODEL_COSTS.get(model, (1.0, 5.0))
        cost = (response.input_tokens * costs[0] / 1_000_000) + (response.output_tokens * costs[1] / 1_000_000)

        return BenchmarkResult(
            agent_name=agent.name,
            task_type=task_type,
            prompt_id=prompt_config["id"],
            response_time=response.response_time,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost=round(cost, 6),
            keyword_score=round(keyword_score, 3),
            structure_score=round(structure_score, 3),
            eval_score=round(eval_score, 3),
            composite_score=round(composite, 3),
        )

    def _keyword_score(self, content: str, expected: List[str]) -> float:
        """Score 0-1 based on how many expected keywords appear."""
        if not expected or not content:
            return 0.0
        lower = content.lower()
        hits = sum(1 for kw in expected if kw.lower() in lower)
        return hits / len(expected)

    def _structure_score(self, content: str) -> float:
        """Score 0-1 based on structural quality."""
        if not content:
            return 0.0

        score = 0.0
        # Has code blocks
        if "```" in content:
            score += 0.3
        # Has explanations (not just code)
        non_code = content.split("```")
        text_chars = sum(len(part) for i, part in enumerate(non_code) if i % 2 == 0)
        if text_chars > 100:
            score += 0.2
        # Reasonable length (200-3000 chars is ideal)
        if 200 <= len(content) <= 5000:
            score += 0.3
        elif len(content) > 5000:
            score += 0.15
        # Has structure (headers, bullets, numbered lists)
        if any(marker in content for marker in ["- ", "1.", "##", "**"]):
            score += 0.2

        return min(score, 1.0)

    async def _ai_eval(self, evaluator: Any, original_prompt: str, response_content: str) -> float:
        """Use an agent as judge to score another agent's response."""
        eval_prompt = (
            "Rate this AI response on a scale of 1-10 for correctness, completeness, and code quality.\n\n"
            f"Original prompt: {original_prompt[:500]}\n\n"
            f"Response to evaluate:\n{response_content[:2000]}\n\n"
            'Reply with ONLY a JSON object: {"correctness": X, "completeness": X, "code_quality": X}'
        )
        try:
            eval_response = await evaluator.generate_response(eval_prompt)
            # Parse the score
            text = eval_response.content.strip()
            # Find JSON in response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                scores = json.loads(text[start:end])
                avg = (
                    float(scores.get("correctness", 5))
                    + float(scores.get("completeness", 5))
                    + float(scores.get("code_quality", 5))
                ) / 3.0
                return avg / 10.0  # Normalize to 0-1
        except Exception as e:
            logger.debug(f"AI eval failed: {e}")
        return 0.5  # Default neutral score

    def _save_suite(self, suite: BenchmarkSuite):
        """Save benchmark results to disk."""
        path = self._results_dir / f"{suite.suite_id}.json"
        data = {
            "suite_id": suite.suite_id,
            "task_type": suite.task_type,
            "timestamp": suite.timestamp,
            "results": [asdict(r) for r in suite.results],
            "agent_rankings": suite.agent_rankings,
        }
        path.write_text(json.dumps(data, indent=2))

        # Also update the routing table
        self._update_routing_table(suite)
        logger.info(f"Saved benchmark: {suite.suite_id} ({len(suite.results)} results)")

    def _update_routing_table(self, suite: BenchmarkSuite):
        """Update the persistent routing table with latest benchmark results."""
        table_path = STORAGE_DIR / "routing_table.json"
        table = {}
        if table_path.exists():
            try:
                table = json.loads(table_path.read_text())
            except Exception:
                pass

        table[suite.task_type] = {
            "rankings": suite.agent_rankings,
            "best_agent": max(suite.agent_rankings, key=suite.agent_rankings.get) if suite.agent_rankings else None,
            "updated": suite.timestamp,
        }

        table_path.write_text(json.dumps(table, indent=2))

    def get_routing_table(self) -> Dict[str, Any]:
        """Load the current routing table from disk."""
        table_path = STORAGE_DIR / "routing_table.json"
        if table_path.exists():
            try:
                return json.loads(table_path.read_text())
            except Exception:
                pass
        return {}

    def get_benchmark_history(self, task_type: Optional[str] = None) -> List[Dict]:
        """Load past benchmark results."""
        results = []
        for path in sorted(self._results_dir.glob("benchmark_*.json")):
            try:
                data = json.loads(path.read_text())
                if task_type and data["task_type"] != task_type:
                    continue
                results.append(data)
            except Exception:
                pass
        return results
