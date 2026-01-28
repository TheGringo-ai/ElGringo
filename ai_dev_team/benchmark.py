#!/usr/bin/env python3
"""
AI Team Platform - Benchmark Suite
===================================

Validates system performance and capabilities.
Run with: python -m ai_dev_team.benchmark
"""

import asyncio
import time
from dataclasses import dataclass
from typing import List, Dict, Any
import sys


@dataclass
class BenchmarkResult:
    """Result from a benchmark test"""
    name: str
    success: bool
    tokens_per_second: float
    latency_seconds: float
    backend: str
    notes: str = ""


class AITeamBenchmark:
    """Comprehensive benchmark suite for AI Team Platform"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    async def run_all(self, verbose: bool = True) -> Dict[str, Any]:
        """Run all benchmarks"""
        print("=" * 60)
        print("🔥 AI TEAM PLATFORM - BENCHMARK SUITE")
        print("=" * 60)
        print()

        # Run each benchmark
        await self.bench_mlx_short(verbose)
        await self.bench_mlx_long(verbose)
        await self.bench_ollama(verbose)
        await self.bench_code_review(verbose)
        await self.bench_multi_agent(verbose)

        # Print summary
        self._print_summary()

        return self._get_report()

    async def bench_mlx_short(self, verbose: bool = True):
        """Benchmark: MLX short prompt"""
        if verbose:
            print("📊 Test 1: MLX Short Prompt (Neural Engine)")
            print("-" * 40)

        try:
            from .monitor import get_apple_coreml
            coreml = get_apple_coreml()

            if not coreml.mlx_available:
                self.results.append(BenchmarkResult(
                    name="MLX Short",
                    success=False,
                    tokens_per_second=0,
                    latency_seconds=0,
                    backend="MLX",
                    notes="MLX not available"
                ))
                if verbose:
                    print("   ⚠️  MLX not installed\n")
                return

            start = time.time()
            result = await coreml.run_local_llm(
                prompt="What is Python? Answer in one sentence.",
                model='mlx-community/Llama-3.2-1B-Instruct-4bit',
                max_tokens=50
            )
            latency = time.time() - start

            self.results.append(BenchmarkResult(
                name="MLX Short",
                success=result.success,
                tokens_per_second=result.tokens_per_second,
                latency_seconds=latency,
                backend="MLX Neural Engine",
                notes=f"{result.tokens_generated} tokens"
            ))

            if verbose:
                print(f"   ✅ {result.tokens_per_second:.1f} tok/s | {latency:.2f}s\n")

        except Exception as e:
            self.results.append(BenchmarkResult(
                name="MLX Short",
                success=False,
                tokens_per_second=0,
                latency_seconds=0,
                backend="MLX",
                notes=str(e)
            ))
            if verbose:
                print(f"   ❌ Error: {e}\n")

    async def bench_mlx_long(self, verbose: bool = True):
        """Benchmark: MLX long prompt (stress test)"""
        if verbose:
            print("📊 Test 2: MLX Long Prompt (Stress Test)")
            print("-" * 40)

        try:
            from .monitor import get_apple_coreml
            coreml = get_apple_coreml()

            if not coreml.mlx_available:
                self.results.append(BenchmarkResult(
                    name="MLX Long",
                    success=False,
                    tokens_per_second=0,
                    latency_seconds=0,
                    backend="MLX",
                    notes="MLX not available"
                ))
                if verbose:
                    print("   ⚠️  MLX not installed\n")
                return

            start = time.time()
            result = await coreml.run_local_llm(
                prompt="Explain the Linux kernel scheduler in detail with numbered sections.",
                model='mlx-community/Llama-3.2-1B-Instruct-4bit',
                max_tokens=300
            )
            latency = time.time() - start

            self.results.append(BenchmarkResult(
                name="MLX Long",
                success=result.success,
                tokens_per_second=result.tokens_per_second,
                latency_seconds=latency,
                backend="MLX Neural Engine",
                notes=f"{result.tokens_generated} tokens"
            ))

            if verbose:
                print(f"   ✅ {result.tokens_per_second:.1f} tok/s | {latency:.2f}s\n")

        except Exception as e:
            self.results.append(BenchmarkResult(
                name="MLX Long",
                success=False,
                tokens_per_second=0,
                latency_seconds=0,
                backend="MLX",
                notes=str(e)
            ))
            if verbose:
                print(f"   ❌ Error: {e}\n")

    async def bench_ollama(self, verbose: bool = True):
        """Benchmark: Ollama local inference"""
        if verbose:
            print("📊 Test 3: Ollama (Local LLM)")
            print("-" * 40)

        try:
            from .agents import OllamaAgent

            agent = OllamaAgent()
            if not await agent.is_available():
                self.results.append(BenchmarkResult(
                    name="Ollama",
                    success=False,
                    tokens_per_second=0,
                    latency_seconds=0,
                    backend="Ollama",
                    notes="Ollama not running"
                ))
                if verbose:
                    print("   ⚠️  Ollama not running\n")
                return

            start = time.time()
            response = await agent.generate_response(
                "What is 2+2? Answer in one word."
            )
            latency = time.time() - start

            # Estimate tokens (rough)
            tokens = len(response.content.split()) * 1.3
            tps = tokens / latency if latency > 0 else 0

            self.results.append(BenchmarkResult(
                name="Ollama",
                success=response.success,
                tokens_per_second=tps,
                latency_seconds=latency,
                backend="Ollama (llama3)",
                notes=f"Response: {response.content[:50]}"
            ))

            if verbose:
                print(f"   ✅ {latency:.2f}s latency\n")

        except Exception as e:
            self.results.append(BenchmarkResult(
                name="Ollama",
                success=False,
                tokens_per_second=0,
                latency_seconds=0,
                backend="Ollama",
                notes=str(e)
            ))
            if verbose:
                print(f"   ❌ Error: {e}\n")

    async def bench_code_review(self, verbose: bool = True):
        """Benchmark: Code review task"""
        if verbose:
            print("📊 Test 4: Code Review (Qwen Coder)")
            print("-" * 40)

        try:
            from . import AIDevTeam

            team = AIDevTeam(project_name='benchmark', auto_setup=True)

            if 'local-qwen-coder-7b' not in team.available_agents:
                self.results.append(BenchmarkResult(
                    name="Code Review",
                    success=False,
                    tokens_per_second=0,
                    latency_seconds=0,
                    backend="Qwen Coder",
                    notes="Agent not available"
                ))
                if verbose:
                    print("   ⚠️  Qwen Coder not available\n")
                return

            code = "def add(a, b): return a + b"
            start = time.time()
            response = await team.ask(
                f"Review this code briefly: {code}",
                agent='local-qwen-coder-7b'
            )
            latency = time.time() - start

            self.results.append(BenchmarkResult(
                name="Code Review",
                success=response.success,
                tokens_per_second=0,
                latency_seconds=latency,
                backend="Qwen Coder 7B",
                notes=f"Confidence: {response.confidence}"
            ))

            if verbose:
                print(f"   ✅ {latency:.2f}s latency\n")

        except Exception as e:
            self.results.append(BenchmarkResult(
                name="Code Review",
                success=False,
                tokens_per_second=0,
                latency_seconds=0,
                backend="Qwen Coder",
                notes=str(e)
            ))
            if verbose:
                print(f"   ❌ Error: {e}\n")

    async def bench_multi_agent(self, verbose: bool = True):
        """Benchmark: Multi-agent collaboration"""
        if verbose:
            print("📊 Test 5: Multi-Agent Collaboration")
            print("-" * 40)

        try:
            from . import AIDevTeam

            team = AIDevTeam(project_name='benchmark', auto_setup=True)

            start = time.time()
            result = await team.collaborate(
                prompt="What are the pros and cons of Python?",
                agents=['local-llama3', 'local-qwen-coder-7b'][:len(team.available_agents)],
                mode='parallel'
            )
            latency = time.time() - start

            self.results.append(BenchmarkResult(
                name="Multi-Agent",
                success=result.success,
                tokens_per_second=0,
                latency_seconds=latency,
                backend=f"{len(result.participating_agents)} agents",
                notes=f"Confidence: {result.confidence_score:.2f}"
            ))

            if verbose:
                print(f"   ✅ {latency:.2f}s | {len(result.participating_agents)} agents\n")

        except Exception as e:
            self.results.append(BenchmarkResult(
                name="Multi-Agent",
                success=False,
                tokens_per_second=0,
                latency_seconds=0,
                backend="Multi-Agent",
                notes=str(e)
            ))
            if verbose:
                print(f"   ❌ Error: {e}\n")

    def _print_summary(self):
        """Print benchmark summary"""
        print("=" * 60)
        print("📋 BENCHMARK SUMMARY")
        print("=" * 60)
        print()
        print(f"{'Test':<20} {'Status':<8} {'Speed':<15} {'Latency':<10} {'Backend'}")
        print("-" * 70)

        for r in self.results:
            status = "✅" if r.success else "❌"
            speed = f"{r.tokens_per_second:.1f} tok/s" if r.tokens_per_second > 0 else "-"
            latency = f"{r.latency_seconds:.2f}s" if r.latency_seconds > 0 else "-"
            print(f"{r.name:<20} {status:<8} {speed:<15} {latency:<10} {r.backend}")

        print()
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        print(f"Results: {passed}/{total} tests passed")
        print()

    def _get_report(self) -> Dict[str, Any]:
        """Get benchmark report as dict"""
        return {
            "tests": [
                {
                    "name": r.name,
                    "success": r.success,
                    "tokens_per_second": r.tokens_per_second,
                    "latency_seconds": r.latency_seconds,
                    "backend": r.backend,
                    "notes": r.notes,
                }
                for r in self.results
            ],
            "summary": {
                "passed": sum(1 for r in self.results if r.success),
                "total": len(self.results),
            }
        }


async def main():
    """Run benchmarks from command line"""
    benchmark = AITeamBenchmark()
    await benchmark.run_all(verbose=True)


if __name__ == "__main__":
    asyncio.run(main())
