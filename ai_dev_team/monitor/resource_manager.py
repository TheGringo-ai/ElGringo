"""
Resource Manager
================

Comprehensive resource management for the AI Dev Team platform.

Features:
- Rate limiting to prevent API overuse
- Token/cost tracking
- Idle agent shutdown
- Memory pressure handling
- Request deduplication
- Usage analytics
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import os

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Record of API usage"""
    timestamp: datetime
    agent_name: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    cached: bool = False


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 500
    requests_per_day: int = 5000
    tokens_per_minute: int = 100000
    tokens_per_day: int = 1000000
    cooldown_seconds: float = 1.0


# Approximate costs per 1K tokens (as of 2024)
MODEL_COSTS = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "gemini-pro": {"input": 0.00025, "output": 0.0005},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "grok-beta": {"input": 0.005, "output": 0.015},
    "default": {"input": 0.001, "output": 0.002},
}


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._requests: List[float] = []
        self._tokens: List[tuple] = []  # (timestamp, token_count)
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 0) -> bool:
        """
        Try to acquire permission for a request.
        Returns True if allowed, False if rate limited.
        """
        async with self._lock:
            now = time.time()

            # Clean old entries
            minute_ago = now - 60
            hour_ago = now - 3600
            day_ago = now - 86400

            self._requests = [t for t in self._requests if t > day_ago]
            self._tokens = [(t, c) for t, c in self._tokens if t > day_ago]

            # Check request limits
            requests_last_minute = sum(1 for t in self._requests if t > minute_ago)
            requests_last_hour = sum(1 for t in self._requests if t > hour_ago)
            requests_last_day = len(self._requests)

            if requests_last_minute >= self.config.requests_per_minute:
                logger.warning("Rate limit: requests per minute exceeded")
                return False
            if requests_last_hour >= self.config.requests_per_hour:
                logger.warning("Rate limit: requests per hour exceeded")
                return False
            if requests_last_day >= self.config.requests_per_day:
                logger.warning("Rate limit: requests per day exceeded")
                return False

            # Check token limits
            if tokens > 0:
                tokens_last_minute = sum(c for t, c in self._tokens if t > minute_ago)
                tokens_last_day = sum(c for t, c in self._tokens)

                if tokens_last_minute + tokens > self.config.tokens_per_minute:
                    logger.warning("Rate limit: tokens per minute exceeded")
                    return False
                if tokens_last_day + tokens > self.config.tokens_per_day:
                    logger.warning("Rate limit: tokens per day exceeded")
                    return False

            # Record this request
            self._requests.append(now)
            if tokens > 0:
                self._tokens.append((now, tokens))

            return True

    async def wait_if_needed(self, tokens: int = 0):
        """Wait until rate limit allows the request"""
        while not await self.acquire(tokens):
            await asyncio.sleep(self.config.cooldown_seconds)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        return {
            "requests_last_minute": sum(1 for t in self._requests if t > minute_ago),
            "requests_last_hour": sum(1 for t in self._requests if t > hour_ago),
            "requests_last_day": sum(1 for t in self._requests if t > day_ago),
            "tokens_last_minute": sum(c for t, c in self._tokens if t > minute_ago),
            "tokens_last_day": sum(c for t, c in self._tokens if t > day_ago),
            "limits": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "requests_per_day": self.config.requests_per_day,
            }
        }


class CostTracker:
    """
    Tracks API usage costs across all agents.
    """

    def __init__(self, daily_budget_usd: float = 10.0):
        self.daily_budget = daily_budget_usd
        self._records: List[UsageRecord] = []
        self._lock = asyncio.Lock()

    async def record_usage(
        self,
        agent_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cached: bool = False
    ) -> float:
        """Record API usage and return cost"""
        async with self._lock:
            # Get cost rates
            costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])

            # Calculate cost (per 1K tokens)
            if cached:
                cost = 0.0  # Cached responses are free
            else:
                cost = (tokens_in * costs["input"] / 1000) + \
                       (tokens_out * costs["output"] / 1000)

            record = UsageRecord(
                timestamp=datetime.now(timezone.utc),
                agent_name=agent_name,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                cached=cached
            )
            self._records.append(record)

            # Keep only last 30 days
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            self._records = [r for r in self._records if r.timestamp > cutoff]

            return cost

    def get_daily_spend(self) -> float:
        """Get total spend for today"""
        today = datetime.now(timezone.utc).date()
        return sum(
            r.cost_usd for r in self._records
            if r.timestamp.date() == today
        )

    def get_monthly_spend(self) -> float:
        """Get total spend for this month"""
        now = datetime.now(timezone.utc)
        return sum(
            r.cost_usd for r in self._records
            if r.timestamp.year == now.year and r.timestamp.month == now.month
        )

    def is_over_budget(self) -> bool:
        """Check if daily budget exceeded"""
        return self.get_daily_spend() >= self.daily_budget

    def get_budget_remaining(self) -> float:
        """Get remaining daily budget"""
        return max(0, self.daily_budget - self.get_daily_spend())

    def get_usage_by_agent(self) -> Dict[str, Dict[str, Any]]:
        """Get usage breakdown by agent"""
        today = datetime.now(timezone.utc).date()
        by_agent: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"requests": 0, "tokens": 0, "cost": 0.0, "cached": 0}
        )

        for record in self._records:
            if record.timestamp.date() == today:
                agent = by_agent[record.agent_name]
                agent["requests"] += 1
                agent["tokens"] += record.tokens_in + record.tokens_out
                agent["cost"] += record.cost_usd
                if record.cached:
                    agent["cached"] += 1

        return dict(by_agent)

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary"""
        return {
            "daily_spend_usd": self.get_daily_spend(),
            "monthly_spend_usd": self.get_monthly_spend(),
            "daily_budget_usd": self.daily_budget,
            "budget_remaining_usd": self.get_budget_remaining(),
            "over_budget": self.is_over_budget(),
            "by_agent": self.get_usage_by_agent(),
            "total_requests_today": sum(
                1 for r in self._records
                if r.timestamp.date() == datetime.now(timezone.utc).date()
            ),
        }


class IdleManager:
    """
    Manages agent idle states to save resources.
    """

    def __init__(
        self,
        idle_timeout_seconds: float = 300.0,  # 5 minutes
        shutdown_callback: Optional[Callable[[str], None]] = None
    ):
        self.idle_timeout = idle_timeout_seconds
        self.shutdown_callback = shutdown_callback
        self._last_activity: Dict[str, float] = {}
        self._active_agents: set = set()
        self._lock = asyncio.Lock()

    async def mark_active(self, agent_name: str):
        """Mark an agent as active"""
        async with self._lock:
            self._last_activity[agent_name] = time.time()
            self._active_agents.add(agent_name)

    async def check_idle_agents(self) -> List[str]:
        """Check for and return list of idle agents"""
        async with self._lock:
            now = time.time()
            idle_agents = []

            for agent, last_time in self._last_activity.items():
                if agent in self._active_agents:
                    if now - last_time > self.idle_timeout:
                        idle_agents.append(agent)

            return idle_agents

    async def shutdown_idle_agents(self) -> List[str]:
        """Shutdown idle agents and return list of shutdown agents"""
        idle_agents = await self.check_idle_agents()

        for agent in idle_agents:
            async with self._lock:
                self._active_agents.discard(agent)

            if self.shutdown_callback:
                try:
                    self.shutdown_callback(agent)
                    logger.info(f"Shutdown idle agent: {agent}")
                except Exception as e:
                    logger.error(f"Error shutting down {agent}: {e}")

        return idle_agents

    def get_agent_states(self) -> Dict[str, Dict[str, Any]]:
        """Get state of all tracked agents"""
        now = time.time()
        states = {}

        for agent, last_time in self._last_activity.items():
            idle_seconds = now - last_time
            states[agent] = {
                "active": agent in self._active_agents,
                "idle_seconds": idle_seconds,
                "will_shutdown_in": max(0, self.idle_timeout - idle_seconds)
                    if agent in self._active_agents else None,
            }

        return states


class RequestDeduplicator:
    """
    Deduplicates concurrent identical requests.
    """

    def __init__(self, window_seconds: float = 2.0):
        self.window = window_seconds
        self._pending: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, prompt: str, agent: str) -> str:
        """Create dedup key"""
        import hashlib
        return hashlib.md5(f"{agent}:{prompt}".encode()).hexdigest()

    async def get_or_create(
        self,
        prompt: str,
        agent: str,
        create_fn: Callable
    ) -> Any:
        """
        Get result from pending request or create new one.
        Deduplicates concurrent identical requests.
        """
        key = self._make_key(prompt, agent)

        async with self._lock:
            if key in self._pending:
                # Wait for existing request
                logger.debug(f"Deduplicating request for {agent}")
                return await self._pending[key]

            # Create new future for this request
            future = asyncio.get_event_loop().create_future()
            self._pending[key] = future

        try:
            # Execute the actual request
            result = await create_fn()
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            # Cleanup after window
            async def cleanup():
                await asyncio.sleep(self.window)
                async with self._lock:
                    self._pending.pop(key, None)
            asyncio.create_task(cleanup())


class ResourceManager:
    """
    Unified resource manager for the AI Dev Team platform.

    Combines rate limiting, cost tracking, idle management,
    and request deduplication into a single interface.
    """

    def __init__(
        self,
        rate_limit_config: RateLimitConfig = None,
        daily_budget_usd: float = 10.0,
        idle_timeout_seconds: float = 300.0,
        enable_rate_limiting: bool = True,
        enable_cost_tracking: bool = True,
        enable_idle_management: bool = True,
        enable_deduplication: bool = True,
    ):
        self.rate_limiter = RateLimiter(rate_limit_config) if enable_rate_limiting else None
        self.cost_tracker = CostTracker(daily_budget_usd) if enable_cost_tracking else None
        self.idle_manager = IdleManager(idle_timeout_seconds) if enable_idle_management else None
        self.deduplicator = RequestDeduplicator() if enable_deduplication else None

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start resource management"""
        self._running = True
        if self.idle_manager:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource manager started")

    async def stop(self):
        """Stop resource management"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource manager stopped")

    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                # Check for idle agents
                if self.idle_manager:
                    shutdown = await self.idle_manager.shutdown_idle_agents()
                    if shutdown:
                        logger.info(f"Shutdown {len(shutdown)} idle agents")

                # Check budget
                if self.cost_tracker and self.cost_tracker.is_over_budget():
                    logger.warning("Daily budget exceeded!")

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitor error: {e}")
                await asyncio.sleep(60)

    async def can_make_request(self, estimated_tokens: int = 0) -> tuple[bool, str]:
        """
        Check if a request can be made.
        Returns (allowed, reason).
        """
        # Check rate limit
        if self.rate_limiter:
            if not await self.rate_limiter.acquire(estimated_tokens):
                return False, "Rate limit exceeded"

        # Check budget
        if self.cost_tracker and self.cost_tracker.is_over_budget():
            return False, "Daily budget exceeded"

        return True, "OK"

    async def record_request(
        self,
        agent_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cached: bool = False
    ) -> float:
        """Record a completed request"""
        cost = 0.0

        # Track cost
        if self.cost_tracker:
            cost = await self.cost_tracker.record_usage(
                agent_name, model, tokens_in, tokens_out, cached
            )

        # Mark agent active
        if self.idle_manager:
            await self.idle_manager.mark_active(agent_name)

        return cost

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive resource status"""
        status = {}

        if self.rate_limiter:
            status["rate_limits"] = self.rate_limiter.get_usage_stats()

        if self.cost_tracker:
            status["costs"] = self.cost_tracker.get_cost_summary()

        if self.idle_manager:
            status["agents"] = self.idle_manager.get_agent_states()

        return status

    def print_status(self):
        """Print resource status to console"""
        status = self.get_status()

        print("\n" + "=" * 60)
        print("  RESOURCE STATUS")
        print("=" * 60)

        if "rate_limits" in status:
            rl = status["rate_limits"]
            print(f"\n  Rate Limits:")
            print(f"    Requests: {rl['requests_last_minute']}/{rl['limits']['requests_per_minute']}/min")
            print(f"    Requests: {rl['requests_last_hour']}/{rl['limits']['requests_per_hour']}/hour")
            print(f"    Tokens: {rl['tokens_last_minute']:,}/min")

        if "costs" in status:
            c = status["costs"]
            print(f"\n  Costs:")
            print(f"    Today: ${c['daily_spend_usd']:.4f} / ${c['daily_budget_usd']:.2f}")
            print(f"    Month: ${c['monthly_spend_usd']:.4f}")
            print(f"    Remaining: ${c['budget_remaining_usd']:.4f}")
            if c["over_budget"]:
                print("    ⚠️  OVER BUDGET")

        if "agents" in status:
            print(f"\n  Agents:")
            for name, state in status["agents"].items():
                idle = state["idle_seconds"]
                active = "ACTIVE" if state["active"] else "IDLE"
                print(f"    {name}: {active} (idle {idle:.0f}s)")

        print("=" * 60)
