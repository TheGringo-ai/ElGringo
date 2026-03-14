#!/usr/bin/env python3
"""
El Gringo Stress Test / Load Test
==================================

Concurrent load testing for the El Gringo API using asyncio + aiohttp.

Usage:
    python3 tests/stress_test.py --url http://127.0.0.1:8090
    python3 tests/stress_test.py --url http://127.0.0.1:8090 --concurrency 20 --requests 100
    python3 tests/stress_test.py --url http://127.0.0.1:8090 --api-key MY_KEY

Test scenarios:
    1. GET  /v1/health      - Baseline latency
    2. GET  /v1/agents      - Read performance
    3. POST /v1/ask         - Single agent performance
    4. POST /v1/collaborate - Turbo mode (routing + single agent)
    5. POST /v1/collaborate - Parallel mode (multi-agent)
"""

import argparse
import asyncio
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import aiohttp
except ImportError:
    print("aiohttp is required: pip install aiohttp")
    sys.exit(1)


# -- ANSI colors ---------------------------------------------------------------

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    BG_RED  = "\033[41m"
    BG_GREEN = "\033[42m"


def colored(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"


# -- Data structures -----------------------------------------------------------

@dataclass
class RequestResult:
    success: bool
    status_code: int
    latency_ms: float
    error: Optional[str] = None


@dataclass
class ScenarioResult:
    name: str
    results: List[RequestResult] = field(default_factory=list)

    @property
    def successes(self) -> List[RequestResult]:
        return [r for r in self.results if r.success]

    @property
    def failures(self) -> List[RequestResult]:
        return [r for r in self.results if not r.success]

    @property
    def latencies(self) -> List[float]:
        return [r.latency_ms for r in self.successes]

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * p / 100)
        idx = min(idx, len(sorted_lat) - 1)
        return sorted_lat[idx]


# -- Scenarios ------------------------------------------------------------------

SCENARIOS = [
    {
        "name": "Health Check",
        "method": "GET",
        "path": "/v1/health",
        "body": None,
        "timeout": 10,
    },
    {
        "name": "Agent List",
        "method": "GET",
        "path": "/v1/agents",
        "body": None,
        "timeout": 15,
    },
    {
        "name": "Single Ask",
        "method": "POST",
        "path": "/v1/ask",
        "body": {
            "prompt": "What is 2+2? Reply with just the number.",
            "agent": "chatgpt",
        },
        "timeout": 60,
    },
    {
        "name": "Collaborate (turbo)",
        "method": "POST",
        "path": "/v1/collaborate",
        "body": {
            "prompt": "What is the capital of France? One word answer.",
            "mode": "turbo",
        },
        "timeout": 60,
    },
    {
        "name": "Collaborate (parallel)",
        "method": "POST",
        "path": "/v1/collaborate",
        "body": {
            "prompt": "Explain recursion in one sentence.",
            "mode": "parallel",
            "agents": ["chatgpt", "gemini"],
        },
        "timeout": 120,
    },
]


# -- Runner ---------------------------------------------------------------------

async def run_single_request(
    session: aiohttp.ClientSession,
    base_url: str,
    scenario: dict,
    headers: dict,
) -> RequestResult:
    url = f"{base_url}{scenario['path']}"
    method = scenario["method"]
    timeout = aiohttp.ClientTimeout(total=scenario["timeout"])

    start = time.perf_counter()
    try:
        if method == "GET":
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                await resp.read()
                latency = (time.perf_counter() - start) * 1000
                return RequestResult(
                    success=resp.status < 400,
                    status_code=resp.status,
                    latency_ms=latency,
                    error=None if resp.status < 400 else f"HTTP {resp.status}",
                )
        else:
            async with session.post(
                url, json=scenario["body"], headers=headers, timeout=timeout
            ) as resp:
                await resp.read()
                latency = (time.perf_counter() - start) * 1000
                return RequestResult(
                    success=resp.status < 400,
                    status_code=resp.status,
                    latency_ms=latency,
                    error=None if resp.status < 400 else f"HTTP {resp.status}",
                )
    except asyncio.TimeoutError:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(False, 0, latency, "Timeout")
    except aiohttp.ClientConnectorError:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(False, 0, latency, "Connection refused")
    except aiohttp.ClientError as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(False, 0, latency, str(e))
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(False, 0, latency, f"Unexpected: {e}")


async def run_scenario(
    base_url: str,
    scenario: dict,
    concurrency: int,
    num_requests: int,
    headers: dict,
) -> ScenarioResult:
    result = ScenarioResult(name=scenario["name"])
    sem = asyncio.Semaphore(concurrency)

    async def bounded_request(session: aiohttp.ClientSession):
        async with sem:
            r = await run_single_request(session, base_url, scenario, headers)
            result.results.append(r)

    connector = aiohttp.TCPConnector(limit=concurrency, force_close=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [bounded_request(session) for _ in range(num_requests)]
        await asyncio.gather(*tasks)

    return result


# -- Reporting ------------------------------------------------------------------

def print_header(text: str):
    width = 72
    print()
    print(colored("=" * width, C.CYAN))
    print(colored(f"  {text}", C.BOLD + C.CYAN))
    print(colored("=" * width, C.CYAN))


def print_scenario_header(name: str, idx: int, total: int):
    print()
    label = f"[{idx}/{total}] {name}"
    print(colored(f"--- {label} ", C.BOLD + C.YELLOW) + colored("-" * (60 - len(label)), C.DIM))


def print_progress(done: int, total: int, scenario: str):
    bar_len = 30
    filled = int(bar_len * done / total)
    bar = colored("#" * filled, C.GREEN) + colored("-" * (bar_len - filled), C.DIM)
    sys.stdout.write(f"\r  [{bar}] {done}/{total}  {scenario}")
    sys.stdout.flush()


def format_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.1f}ms"
    return f"{ms / 1000:.2f}s"


def print_scenario_report(sr: ScenarioResult):
    total = len(sr.results)
    ok = len(sr.successes)
    fail = len(sr.failures)
    rate = (ok / total * 100) if total > 0 else 0

    status_color = C.GREEN if rate == 100 else (C.YELLOW if rate >= 80 else C.RED)

    print(f"  {colored('Requests:', C.BOLD)}  {total}  |  "
          f"{colored('OK:', C.GREEN)} {ok}  |  "
          f"{colored('Fail:', C.RED)} {fail}  |  "
          f"Success rate: {colored(f'{rate:.1f}%', status_color)}")

    if sr.latencies:
        avg = statistics.mean(sr.latencies)
        mn = min(sr.latencies)
        mx = max(sr.latencies)
        p95 = sr.percentile(95)
        p99 = sr.percentile(99)
        med = statistics.median(sr.latencies)

        print(f"  {colored('Latency:', C.BOLD)}   "
              f"min={colored(format_ms(mn), C.GREEN)}  "
              f"avg={colored(format_ms(avg), C.CYAN)}  "
              f"med={colored(format_ms(med), C.CYAN)}  "
              f"max={colored(format_ms(mx), C.MAGENTA)}")
        print(f"              "
              f"p95={colored(format_ms(p95), C.YELLOW)}  "
              f"p99={colored(format_ms(p99), C.RED)}")

    if sr.failures:
        error_counts: Dict[str, int] = {}
        for f in sr.failures:
            err = f.error or "Unknown"
            error_counts[err] = error_counts.get(err, 0) + 1
        print(f"  {colored('Errors:', C.RED)}")
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"    {colored(str(count) + 'x', C.RED)} {err}")


def print_summary(
    all_results: List[ScenarioResult],
    total_time: float,
    concurrency: int,
):
    print_header("SUMMARY")

    total_reqs = sum(len(sr.results) for sr in all_results)
    total_ok = sum(len(sr.successes) for sr in all_results)
    total_fail = sum(len(sr.failures) for sr in all_results)
    rps = total_reqs / total_time if total_time > 0 else 0
    overall_rate = (total_ok / total_reqs * 100) if total_reqs > 0 else 0

    print(f"""
  {colored('Total requests:', C.BOLD)}    {total_reqs}
  {colored('Successful:', C.GREEN)}        {total_ok}
  {colored('Failed:', C.RED)}             {total_fail}
  {colored('Total time:', C.BOLD)}         {total_time:.2f}s
  {colored('Requests/sec:', C.BOLD)}       {colored(f'{rps:.1f}', C.CYAN)}
  {colored('Concurrency:', C.BOLD)}        {concurrency}
  {colored('Success rate:', C.BOLD)}       {colored(f'{overall_rate:.1f}%', C.GREEN if overall_rate >= 95 else C.RED)}
""")

    # Per-scenario summary table
    print(f"  {colored('Scenario', C.BOLD):<40} {'Avg':>10} {'p95':>10} {'p99':>10} {'Rate':>8}")
    print(f"  {'-' * 78}")
    for sr in all_results:
        avg = format_ms(statistics.mean(sr.latencies)) if sr.latencies else "N/A"
        p95 = format_ms(sr.percentile(95)) if sr.latencies else "N/A"
        p99 = format_ms(sr.percentile(99)) if sr.latencies else "N/A"
        rate = f"{len(sr.successes) / len(sr.results) * 100:.0f}%" if sr.results else "N/A"
        rate_color = C.GREEN if rate == "100%" else (C.YELLOW if rate != "N/A" else C.DIM)
        print(f"  {sr.name:<38} {avg:>10} {p95:>10} {p99:>10} {colored(rate, rate_color):>17}")

    print()
    print(colored("  NOTE: ", C.BG_RED + C.WHITE + C.BOLD) +
          colored(" Check server memory usage (htop / docker stats) during and after the test.", C.YELLOW))
    print(colored("         High memory under load may indicate connection/response leaks.", C.DIM))
    print()


# -- Main -----------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="El Gringo API Stress Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--url", default="http://127.0.0.1:8090", help="Base API URL (default: http://127.0.0.1:8090)")
    parser.add_argument("--concurrency", type=int, default=10, help="Max concurrent requests (default: 10)")
    parser.add_argument("--requests", type=int, default=50, help="Requests per scenario (default: 50)")
    parser.add_argument("--api-key", default=None, help="API key for authenticated endpoints")
    parser.add_argument("--skip-slow", action="store_true", help="Skip collaborate/ask scenarios (test infra only)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"
        headers["X-API-Key"] = args.api_key

    scenarios = SCENARIOS
    if args.skip_slow:
        scenarios = [s for s in scenarios if s["method"] == "GET"]

    print_header("EL GRINGO STRESS TEST")
    print(f"""
  {colored('Target:', C.BOLD)}       {colored(base_url, C.CYAN)}
  {colored('Concurrency:', C.BOLD)}  {args.concurrency}
  {colored('Requests:', C.BOLD)}     {args.requests} per scenario
  {colored('Scenarios:', C.BOLD)}    {len(scenarios)}
  {colored('Total:', C.BOLD)}        {args.requests * len(scenarios)} requests
  {colored('API Key:', C.BOLD)}      {'set' if args.api_key else colored('not set', C.DIM)}
""")

    # Quick connectivity check
    print(colored("  Checking connectivity...", C.DIM), end="", flush=True)
    try:
        connector = aiohttp.TCPConnector(limit=1)
        async with aiohttp.ClientSession(connector=connector) as session:
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.get(f"{base_url}/v1/health", timeout=timeout) as resp:
                if resp.status < 400:
                    print(colored(" OK", C.GREEN))
                else:
                    print(colored(f" HTTP {resp.status} (continuing anyway)", C.YELLOW))
    except Exception as e:
        print(colored(f" FAILED: {e}", C.RED))
        print(colored("  Server may be down. Results will show connection errors.", C.YELLOW))
        print()

    all_results: List[ScenarioResult] = []
    overall_start = time.perf_counter()

    for idx, scenario in enumerate(scenarios, 1):
        print_scenario_header(scenario["name"], idx, len(scenarios))

        start = time.perf_counter()
        sr = await run_scenario(
            base_url, scenario, args.concurrency, args.requests, headers
        )
        elapsed = time.perf_counter() - start

        all_results.append(sr)
        rps = len(sr.results) / elapsed if elapsed > 0 else 0
        print(f"  Completed in {elapsed:.2f}s ({rps:.1f} req/s)")
        print_scenario_report(sr)

    overall_time = time.perf_counter() - overall_start
    print_summary(all_results, overall_time, args.concurrency)


if __name__ == "__main__":
    asyncio.run(main())
