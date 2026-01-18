"""
Performance Optimizer
=====================

Optimizes AI team performance through caching, request batching,
connection pooling, and intelligent load balancing.
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached response entry"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0
    size_bytes: int = 0


class CacheManager:
    """
    Intelligent Cache Manager

    Features:
    - LRU eviction with TTL
    - Size-based limits
    - Cache statistics
    - Automatic cleanup
    """

    def __init__(
        self,
        max_size_mb: float = 100.0,
        max_entries: int = 1000,
        default_ttl_seconds: float = 3600.0,  # 1 hour
    ):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_entries = max_entries
        self.default_ttl = default_ttl_seconds

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._current_size = 0
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired": 0,
        }
        self._lock = asyncio.Lock()

    def _make_key(self, prompt: str, context: str = "", agent: str = "") -> str:
        """Create cache key from request parameters"""
        content = f"{agent}:{context}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            # Check expiration
            if time.time() > entry.expires_at:
                self._remove_entry(key)
                self._stats["expired"] += 1
                self._stats["misses"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats["hits"] += 1

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None
    ):
        """Set value in cache"""
        async with self._lock:
            ttl = ttl_seconds or self.default_ttl
            now = time.time()

            # Estimate size (rough approximation)
            size = len(str(value).encode())

            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)

            # Evict if necessary
            await self._evict_if_needed(size)

            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl,
                size_bytes=size,
            )

            self._cache[key] = entry
            self._current_size += size

    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_size -= entry.size_bytes

    async def _evict_if_needed(self, needed_size: int):
        """Evict entries if cache is full"""
        # Evict by count
        while len(self._cache) >= self.max_entries:
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            self._stats["evictions"] += 1

        # Evict by size
        while self._current_size + needed_size > self.max_size_bytes and self._cache:
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            self._stats["evictions"] += 1

    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._current_size = 0

    async def cleanup_expired(self):
        """Remove expired entries"""
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                self._remove_entry(key)
                self._stats["expired"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "entries": len(self._cache),
            "size_mb": self._current_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "expired": self._stats["expired"],
        }


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    agent_name: str
    prompt_length: int
    response_length: int
    response_time_ms: float
    cached: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceOptimizer:
    """
    Performance Optimizer

    Optimizes AI team performance through:
    - Response caching
    - Request deduplication
    - Load balancing
    - Performance tracking
    - Automatic optimization recommendations
    """

    def __init__(
        self,
        enable_caching: bool = True,
        cache_similar_threshold: float = 0.9,
    ):
        self.enable_caching = enable_caching
        self.cache_similar_threshold = cache_similar_threshold

        self.cache = CacheManager() if enable_caching else None
        self._metrics: List[RequestMetrics] = []
        self._max_metrics = 10000
        self._agent_stats: Dict[str, Dict[str, Any]] = {}
        self._pending_requests: Dict[str, asyncio.Event] = {}

    async def get_cached_response(
        self,
        prompt: str,
        context: str = "",
        agent: str = ""
    ) -> Optional[Any]:
        """Try to get a cached response"""
        if not self.cache:
            return None

        key = self.cache._make_key(prompt, context, agent)
        return await self.cache.get(key)

    async def cache_response(
        self,
        prompt: str,
        response: Any,
        context: str = "",
        agent: str = "",
        ttl_seconds: Optional[float] = None
    ):
        """Cache a response"""
        if not self.cache:
            return

        key = self.cache._make_key(prompt, context, agent)
        await self.cache.set(key, response, ttl_seconds)

    def record_request(
        self,
        agent_name: str,
        prompt_length: int,
        response_length: int,
        response_time_ms: float,
        cached: bool = False
    ):
        """Record request metrics"""
        metric = RequestMetrics(
            agent_name=agent_name,
            prompt_length=prompt_length,
            response_length=response_length,
            response_time_ms=response_time_ms,
            cached=cached,
        )

        self._metrics.append(metric)
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics:]

        # Update agent stats
        if agent_name not in self._agent_stats:
            self._agent_stats[agent_name] = {
                "total_requests": 0,
                "total_time_ms": 0,
                "cached_requests": 0,
            }

        stats = self._agent_stats[agent_name]
        stats["total_requests"] += 1
        stats["total_time_ms"] += response_time_ms
        if cached:
            stats["cached_requests"] += 1

    def get_agent_performance(self, agent_name: str) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        stats = self._agent_stats.get(agent_name, {})
        if not stats or stats["total_requests"] == 0:
            return {
                "avg_response_time_ms": 0,
                "total_requests": 0,
                "cache_hit_rate": 0,
            }

        return {
            "avg_response_time_ms": stats["total_time_ms"] / stats["total_requests"],
            "total_requests": stats["total_requests"],
            "cache_hit_rate": (stats["cached_requests"] / stats["total_requests"]) * 100,
        }

    def get_fastest_agent(self, available_agents: List[str]) -> Optional[str]:
        """Get the fastest responding agent from available ones"""
        best_agent = None
        best_time = float('inf')

        for agent in available_agents:
            perf = self.get_agent_performance(agent)
            if perf["total_requests"] > 0 and perf["avg_response_time_ms"] < best_time:
                best_time = perf["avg_response_time_ms"]
                best_agent = agent

        return best_agent

    def get_optimization_recommendations(self) -> List[str]:
        """Get recommendations for improving performance"""
        recommendations = []

        # Check cache stats
        if self.cache:
            cache_stats = self.cache.get_stats()
            if cache_stats["hit_rate"] < 20 and cache_stats["hits"] + cache_stats["misses"] > 100:
                recommendations.append(
                    "Low cache hit rate ({:.0f}%). Consider increasing cache TTL or size.".format(
                        cache_stats["hit_rate"]
                    )
                )

            if cache_stats["evictions"] > cache_stats["hits"]:
                recommendations.append(
                    "High cache eviction rate. Consider increasing cache size."
                )

        # Check agent performance
        for agent, stats in self._agent_stats.items():
            if stats["total_requests"] > 10:
                avg_time = stats["total_time_ms"] / stats["total_requests"]
                if avg_time > 10000:  # > 10 seconds
                    recommendations.append(
                        f"Agent {agent} has slow average response time ({avg_time/1000:.1f}s). "
                        "Consider using faster alternatives for time-sensitive tasks."
                    )

        # Check overall metrics
        if len(self._metrics) > 100:
            recent = self._metrics[-100:]
            avg_time = sum(m.response_time_ms for m in recent) / len(recent)
            if avg_time > 5000:
                recommendations.append(
                    f"Overall average response time is high ({avg_time/1000:.1f}s). "
                    "Consider enabling caching or using parallel mode."
                )

        if not recommendations:
            recommendations.append("System is performing optimally.")

        return recommendations

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        cache_stats = self.cache.get_stats() if self.cache else {}

        total_requests = sum(s["total_requests"] for s in self._agent_stats.values())
        total_time = sum(s["total_time_ms"] for s in self._agent_stats.values())

        return {
            "total_requests": total_requests,
            "avg_response_time_ms": total_time / total_requests if total_requests > 0 else 0,
            "cache": cache_stats,
            "agents": {
                name: self.get_agent_performance(name)
                for name in self._agent_stats.keys()
            },
            "recommendations": self.get_optimization_recommendations(),
        }

    def print_performance_report(self):
        """Print performance report to console"""
        summary = self.get_performance_summary()

        print("\n" + "=" * 60)
        print("  PERFORMANCE REPORT")
        print("=" * 60)

        print(f"\n  Total Requests: {summary['total_requests']}")
        print(f"  Avg Response Time: {summary['avg_response_time_ms']:.0f}ms")

        if summary.get('cache'):
            cache = summary['cache']
            print(f"\n  Cache Stats:")
            print(f"    Entries: {cache['entries']}")
            print(f"    Size: {cache['size_mb']:.1f}MB / {cache['max_size_mb']:.0f}MB")
            print(f"    Hit Rate: {cache['hit_rate']:.1f}%")

        print(f"\n  Agent Performance:")
        for name, perf in summary.get('agents', {}).items():
            print(f"    {name}: {perf['avg_response_time_ms']:.0f}ms avg, {perf['total_requests']} requests")

        print(f"\n  Recommendations:")
        for rec in summary.get('recommendations', []):
            print(f"    - {rec}")

        print("=" * 60)
