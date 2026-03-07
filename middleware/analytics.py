"""
Usage Analytics Middleware
==========================

Lightweight, in-memory request analytics for all El Gringo services.

For FastAPI (ASGI):
    from middleware.analytics import UsageAnalyticsMiddleware, get_analytics_store
    app.add_middleware(UsageAnalyticsMiddleware, store=get_analytics_store())

For Flask:
    from middleware.analytics import flask_analytics_hooks, get_analytics_store
    flask_analytics_hooks(app, store=get_analytics_store())

The AnalyticsStore uses bounded deques so memory stays capped regardless
of traffic volume.  No database, no disk I/O, no blocking.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum number of individual request records kept (roughly 7 days at
# moderate traffic).  Each record is ~200 bytes, so 100k records ~ 20 MB.
MAX_RECORDS = 100_000

# Per-endpoint rolling window size
MAX_ENDPOINT_RECORDS = 10_000

# Seconds in time windows
SECONDS_1H = 3_600
SECONDS_24H = 86_400
SECONDS_7D = 604_800


# ---------------------------------------------------------------------------
# Request Record
# ---------------------------------------------------------------------------

class RequestRecord:
    """Compact record for a single HTTP request."""

    __slots__ = ("timestamp", "endpoint", "method", "status_code", "duration_ms", "api_key")

    def __init__(
        self,
        timestamp: float,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        api_key: Optional[str] = None,
    ):
        self.timestamp = timestamp
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.duration_ms = duration_ms
        self.api_key = api_key

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "duration_ms": round(self.duration_ms, 2),
            "api_key": self.api_key,
        }


# ---------------------------------------------------------------------------
# Analytics Store (thread-safe, bounded)
# ---------------------------------------------------------------------------

class AnalyticsStore:
    """In-memory analytics store with bounded deques.

    Thread-safe via a single lock.  All public methods acquire it briefly
    so request handling is never blocked for long.
    """

    def __init__(self, max_records: int = MAX_RECORDS, max_per_endpoint: int = MAX_ENDPOINT_RECORDS):
        self._lock = threading.Lock()
        self._all_records: Deque[RequestRecord] = deque(maxlen=max_records)
        self._by_endpoint: Dict[str, Deque[RequestRecord]] = defaultdict(
            lambda: deque(maxlen=max_per_endpoint)
        )
        self._total_requests = 0
        self._total_errors = 0  # 5xx responses
        self._start_time = time.time()

    # ── Recording ──────────────────────────────────────────────────────

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        api_key: Optional[str] = None,
    ) -> None:
        """Record a completed request.  Designed to be fast and non-blocking."""
        record = RequestRecord(
            timestamp=time.time(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            api_key=api_key,
        )
        with self._lock:
            self._all_records.append(record)
            self._by_endpoint[endpoint].append(record)
            self._total_requests += 1
            if status_code >= 500:
                self._total_errors += 1

    # ── Queries ────────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """High-level usage summary."""
        now = time.time()
        cutoff_24h = now - SECONDS_24H
        cutoff_7d = now - SECONDS_7D

        with self._lock:
            records_24h = [r for r in self._all_records if r.timestamp >= cutoff_24h]
            records_7d = [r for r in self._all_records if r.timestamp >= cutoff_7d]

            total = self._total_requests
            errors = self._total_errors

            if records_24h:
                avg_response_24h = sum(r.duration_ms for r in records_24h) / len(records_24h)
            else:
                avg_response_24h = 0.0

            # Top endpoints by call count in last 24h
            endpoint_counts: Dict[str, int] = defaultdict(int)
            for r in records_24h:
                endpoint_counts[r.endpoint] += 1

            top_endpoints = sorted(endpoint_counts.items(), key=lambda x: -x[1])[:10]

            # Error rate (last 24h)
            errors_24h = sum(1 for r in records_24h if r.status_code >= 500)
            error_rate_24h = (errors_24h / len(records_24h) * 100) if records_24h else 0.0

        return {
            "total_requests": total,
            "total_errors": errors,
            "requests_24h": len(records_24h),
            "requests_7d": len(records_7d),
            "avg_response_time_ms_24h": round(avg_response_24h, 2),
            "error_rate_24h_pct": round(error_rate_24h, 2),
            "top_endpoints": [
                {"endpoint": ep, "count": cnt} for ep, cnt in top_endpoints
            ],
            "uptime_seconds": round(now - self._start_time, 0),
        }

    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """Detailed statistics for a single endpoint."""
        now = time.time()
        cutoff_24h = now - SECONDS_24H
        cutoff_7d = now - SECONDS_7D

        with self._lock:
            records = list(self._by_endpoint.get(endpoint, []))

        if not records:
            return {
                "endpoint": endpoint,
                "total_requests": 0,
                "message": "No data for this endpoint",
            }

        records_24h = [r for r in records if r.timestamp >= cutoff_24h]
        records_7d = [r for r in records if r.timestamp >= cutoff_7d]

        def _stats(subset: List[RequestRecord]) -> Dict[str, Any]:
            if not subset:
                return {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0, "error_count": 0}
            durations = sorted(r.duration_ms for r in subset)
            p95_idx = int(len(durations) * 0.95)
            return {
                "count": len(subset),
                "avg_ms": round(sum(durations) / len(durations), 2),
                "min_ms": round(durations[0], 2),
                "max_ms": round(durations[-1], 2),
                "p95_ms": round(durations[min(p95_idx, len(durations) - 1)], 2),
                "error_count": sum(1 for r in subset if r.status_code >= 500),
            }

        # Status code distribution (24h)
        status_dist: Dict[int, int] = defaultdict(int)
        for r in records_24h:
            status_dist[r.status_code] += 1

        # Method distribution (24h)
        method_dist: Dict[str, int] = defaultdict(int)
        for r in records_24h:
            method_dist[r.method] += 1

        return {
            "endpoint": endpoint,
            "total_requests": len(records),
            "last_24h": _stats(records_24h),
            "last_7d": _stats(records_7d),
            "status_codes_24h": dict(status_dist),
            "methods_24h": dict(method_dist),
        }

    def get_all_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Stats for every tracked endpoint."""
        with self._lock:
            endpoints = list(self._by_endpoint.keys())

        results = []
        for ep in sorted(endpoints):
            results.append(self.get_endpoint_stats(ep))
        return results

    def get_hourly_breakdown(self) -> List[Dict[str, Any]]:
        """Request counts per hour for the last 24 hours.

        Returns a list of 24 dicts (oldest first), one per hour bucket.
        """
        now = time.time()
        cutoff = now - SECONDS_24H

        with self._lock:
            records_24h = [r for r in self._all_records if r.timestamp >= cutoff]

        # Build 24 hour-buckets
        buckets: Dict[int, Dict[str, Any]] = {}
        for hour_offset in range(24):
            bucket_start = cutoff + hour_offset * SECONDS_1H
            bucket_end = bucket_start + SECONDS_1H
            hour_label = datetime.fromtimestamp(bucket_start, tz=timezone.utc).strftime("%Y-%m-%d %H:00 UTC")
            buckets[hour_offset] = {
                "hour": hour_label,
                "bucket_start": bucket_start,
                "bucket_end": bucket_end,
                "requests": 0,
                "errors": 0,
                "avg_ms": 0.0,
            }

        for r in records_24h:
            offset = int((r.timestamp - cutoff) / SECONDS_1H)
            offset = min(offset, 23)  # clamp
            buckets[offset]["requests"] += 1
            if r.status_code >= 500:
                buckets[offset]["errors"] += 1

        # Calculate averages
        for hour_offset in range(24):
            bucket = buckets[hour_offset]
            bucket_start = bucket["bucket_start"]
            bucket_end = bucket["bucket_end"]
            bucket_records = [r for r in records_24h if bucket_start <= r.timestamp < bucket_end]
            if bucket_records:
                bucket["avg_ms"] = round(
                    sum(r.duration_ms for r in bucket_records) / len(bucket_records), 2
                )
            # Remove internal fields
            del bucket["bucket_start"]
            del bucket["bucket_end"]

        return [buckets[i] for i in range(24)]


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

_global_store: Optional[AnalyticsStore] = None
_store_lock = threading.Lock()


def get_analytics_store() -> AnalyticsStore:
    """Return the global singleton AnalyticsStore."""
    global _global_store
    if _global_store is None:
        with _store_lock:
            if _global_store is None:
                _global_store = AnalyticsStore()
    return _global_store


# ---------------------------------------------------------------------------
# FastAPI / Starlette ASGI Middleware
# ---------------------------------------------------------------------------

class UsageAnalyticsMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records request metrics into an AnalyticsStore.

    Usage:
        from middleware.analytics import UsageAnalyticsMiddleware, get_analytics_store
        app.add_middleware(UsageAnalyticsMiddleware, store=get_analytics_store())
    """

    def __init__(self, app: ASGIApp, store: Optional[AnalyticsStore] = None):
        super().__init__(app)
        self.store = store or get_analytics_store()

    async def dispatch(self, request: StarletteRequest, call_next) -> StarletteResponse:
        start = time.perf_counter()
        response: StarletteResponse = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        # Extract endpoint path (use route pattern if available, else raw path)
        endpoint = request.url.path

        # Extract method
        method = request.method

        # Extract API key hint (first 8 chars) for per-key tracking
        auth_header = request.headers.get("authorization", "")
        api_key_hint = None
        if auth_header.startswith("Bearer ") and len(auth_header) > 15:
            api_key_hint = auth_header[7:15] + "..."

        # Record (non-blocking -- the store lock is very brief)
        self.store.record_request(
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            api_key=api_key_hint,
        )

        return response


# ---------------------------------------------------------------------------
# Flask hooks
# ---------------------------------------------------------------------------

def flask_analytics_hooks(flask_app, store: Optional[AnalyticsStore] = None):
    """Register before/after_request hooks on a Flask app for analytics.

    Usage:
        from middleware.analytics import flask_analytics_hooks, get_analytics_store
        flask_analytics_hooks(app, store=get_analytics_store())
    """
    _store = store or get_analytics_store()

    @flask_app.before_request
    def _analytics_before():
        from flask import request, g
        g._analytics_start = time.perf_counter()

    @flask_app.after_request
    def _analytics_after(response):
        from flask import request, g
        start = getattr(g, "_analytics_start", None)
        if start is None:
            return response

        duration_ms = (time.perf_counter() - start) * 1000.0

        auth_header = request.headers.get("Authorization", "")
        api_key_hint = None
        if auth_header.startswith("Bearer ") and len(auth_header) > 15:
            api_key_hint = auth_header[7:15] + "..."

        _store.record_request(
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            api_key=api_key_hint,
        )

        return response

    logger.info("Flask analytics hooks registered")
