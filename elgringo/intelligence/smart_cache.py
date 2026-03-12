"""
Smart Response Cache — Fuzzy Prompt Matching
==============================================

Moat feature: No competitor (CrewAI, AutoGen, LangGraph) has this.
Caches AI responses and serves them for similar prompts, saving money and time.

Uses difflib.SequenceMatcher for fuzzy matching — no heavy dependencies.

Usage:
    cache = get_smart_cache()
    hit = cache.get("How do I fix CORS in FastAPI?")
    if hit:
        return hit  # $0.00, <1ms
    else:
        response = await ai_team.collaborate(prompt)
        cache.put(prompt, response, cost=0.03, tokens=1500)
"""

import difflib
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response."""
    entry_id: str
    prompt_hash: str
    prompt: str  # original prompt (truncated for storage)
    response: str
    agent: str = ""
    mode: str = ""
    task_type: str = ""
    cost: float = 0.0
    tokens: int = 0
    confidence: float = 0.0
    created_at: float = 0.0
    ttl_seconds: int = 3600  # default 1 hour
    hit_count: int = 0
    last_hit_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_entries: int = 0
    hits: int = 0
    misses: int = 0
    fuzzy_hits: int = 0
    exact_hits: int = 0
    cost_saved: float = 0.0
    tokens_saved: int = 0
    hit_rate: float = 0.0
    avg_response_time_saved_ms: float = 0.0


class SmartResponseCache:
    """
    Intelligent cache for AI responses with fuzzy prompt matching.

    Features:
    - Exact match via SHA256 hash (O(1) lookup)
    - Fuzzy match via SequenceMatcher for similar prompts
    - TTL-based expiry with configurable defaults per task type
    - Hit/miss tracking with cost savings calculation
    - Persistent storage to disk
    - Automatic eviction of expired entries
    """

    # TTL defaults by task type (seconds)
    TTL_BY_TYPE = {
        "code_review": 7200,      # 2 hours — reviews don't change fast
        "code_generation": 1800,   # 30 min — code tasks vary more
        "debugging": 3600,         # 1 hour
        "documentation": 14400,    # 4 hours — docs are stable
        "architecture": 7200,      # 2 hours
        "testing": 3600,           # 1 hour
        "security": 3600,          # 1 hour
        "general": 1800,           # 30 min default
    }

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/cache",
        max_entries: int = 500,
        default_similarity: float = 0.85,
    ):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self.default_similarity = default_similarity
        self._entries: Dict[str, CacheEntry] = {}  # hash -> entry
        self._prompts: List[Tuple[str, str]] = []  # (hash, prompt) for fuzzy search
        self._stats = CacheStats()
        self._load()

    def get(
        self,
        prompt: str,
        task_type: str = "",
        similarity_threshold: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a cached response for a prompt.

        Returns dict with response, metadata, and match info, or None on miss.
        """
        threshold = similarity_threshold or self.default_similarity

        # Step 1: Exact match (fast path)
        prompt_hash = self._hash(prompt)
        entry = self._entries.get(prompt_hash)
        if entry and not entry.is_expired:
            entry.hit_count += 1
            entry.last_hit_at = time.time()
            self._stats.hits += 1
            self._stats.exact_hits += 1
            self._stats.cost_saved += entry.cost
            self._stats.tokens_saved += entry.tokens
            self._save_stats()
            return {
                "response": entry.response,
                "match_type": "exact",
                "similarity": 1.0,
                "cost_saved": entry.cost,
                "original_agent": entry.agent,
                "cached_at": entry.created_at,
                "hit_count": entry.hit_count,
            }

        # Step 2: Fuzzy match (slower, but catches rephrased prompts)
        best_match = self._fuzzy_search(prompt, threshold)
        if best_match:
            entry, similarity = best_match
            if not entry.is_expired:
                entry.hit_count += 1
                entry.last_hit_at = time.time()
                self._stats.hits += 1
                self._stats.fuzzy_hits += 1
                self._stats.cost_saved += entry.cost
                self._stats.tokens_saved += entry.tokens
                self._save_stats()
                return {
                    "response": entry.response,
                    "match_type": "fuzzy",
                    "similarity": round(similarity, 3),
                    "cost_saved": entry.cost,
                    "original_agent": entry.agent,
                    "original_prompt": entry.prompt[:200],
                    "cached_at": entry.created_at,
                    "hit_count": entry.hit_count,
                }

        self._stats.misses += 1
        return None

    def put(
        self,
        prompt: str,
        response: str,
        cost: float = 0.0,
        tokens: int = 0,
        agent: str = "",
        mode: str = "",
        task_type: str = "",
        confidence: float = 0.0,
        ttl_seconds: int = 0,
    ):
        """Store a response in the cache."""
        # Don't cache low-confidence responses
        if confidence > 0 and confidence < 0.4:
            return

        # Don't cache very short responses (likely errors)
        if len(response) < 50:
            return

        prompt_hash = self._hash(prompt)
        ttl = ttl_seconds or self.TTL_BY_TYPE.get(task_type, 1800)

        entry = CacheEntry(
            entry_id=f"cache-{uuid.uuid4().hex[:8]}",
            prompt_hash=prompt_hash,
            prompt=prompt[:500],  # truncate for storage
            response=response,
            agent=agent,
            mode=mode,
            task_type=task_type,
            cost=cost,
            tokens=tokens,
            confidence=confidence,
            created_at=time.time(),
            ttl_seconds=ttl,
        )

        self._entries[prompt_hash] = entry
        self._prompts.append((prompt_hash, prompt[:500]))

        # Evict expired + LRU if over limit
        self._evict()
        self._save()

    def invalidate(self, prompt: str) -> bool:
        """Remove a specific prompt from cache."""
        prompt_hash = self._hash(prompt)
        if prompt_hash in self._entries:
            del self._entries[prompt_hash]
            self._prompts = [(h, p) for h, p in self._prompts if h != prompt_hash]
            self._save()
            return True
        return False

    def clear(self):
        """Clear all cache entries."""
        self._entries.clear()
        self._prompts.clear()
        self._stats = CacheStats()
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total = self._stats.hits + self._stats.misses
        self._stats.total_entries = len(self._entries)
        self._stats.hit_rate = (self._stats.hits / total * 100) if total > 0 else 0.0

        return {
            "total_entries": self._stats.total_entries,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "exact_hits": self._stats.exact_hits,
            "fuzzy_hits": self._stats.fuzzy_hits,
            "hit_rate": f"{self._stats.hit_rate:.1f}%",
            "cost_saved": f"${self._stats.cost_saved:.4f}",
            "tokens_saved": self._stats.tokens_saved,
            "max_entries": self.max_entries,
            "similarity_threshold": self.default_similarity,
        }

    def get_top_hits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently hit cache entries."""
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: e.hit_count,
            reverse=True,
        )
        return [
            {
                "prompt": e.prompt[:100],
                "hit_count": e.hit_count,
                "agent": e.agent,
                "task_type": e.task_type,
                "cost_per_hit": e.cost,
                "total_saved": round(e.cost * e.hit_count, 4),
            }
            for e in sorted_entries[:limit]
            if e.hit_count > 0
        ]

    def _hash(self, prompt: str) -> str:
        """SHA256 hash of normalized prompt."""
        normalized = prompt.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _fuzzy_search(
        self, prompt: str, threshold: float
    ) -> Optional[Tuple[CacheEntry, float]]:
        """Find best fuzzy match above threshold."""
        if not self._prompts:
            return None

        prompt_lower = prompt.strip().lower()
        best_entry = None
        best_score = 0.0

        # Use SequenceMatcher with autojunk for speed on longer prompts
        matcher = difflib.SequenceMatcher(autojunk=True)
        matcher.set_seq1(prompt_lower)

        for cached_hash, cached_prompt in self._prompts:
            # Skip expired
            entry = self._entries.get(cached_hash)
            if not entry or entry.is_expired:
                continue

            matcher.set_seq2(cached_prompt.strip().lower())

            # Quick ratio check first (fast rejection)
            if matcher.quick_ratio() < threshold:
                continue
            if matcher.real_quick_ratio() < threshold:
                continue

            ratio = matcher.ratio()
            if ratio >= threshold and ratio > best_score:
                best_score = ratio
                best_entry = entry

        if best_entry:
            return (best_entry, best_score)
        return None

    def _evict(self):
        """Remove expired entries and LRU if over limit."""
        # Remove expired
        expired = [h for h, e in self._entries.items() if e.is_expired]
        for h in expired:
            del self._entries[h]

        # LRU eviction if still over limit
        if len(self._entries) > self.max_entries:
            sorted_by_use = sorted(
                self._entries.items(),
                key=lambda x: x[1].last_hit_at or x[1].created_at,
            )
            to_remove = len(self._entries) - self.max_entries
            for h, _ in sorted_by_use[:to_remove]:
                del self._entries[h]

        # Rebuild prompt list
        self._prompts = [(h, e.prompt) for h, e in self._entries.items()]

    def _save(self):
        """Save cache to disk."""
        try:
            data = {h: asdict(e) for h, e in self._entries.items()}
            with open(self.storage_dir / "cache.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug(f"Cache save skipped: {e}")

    def _save_stats(self):
        """Save stats periodically (every 10 hits)."""
        if (self._stats.hits + self._stats.misses) % 10 == 0:
            try:
                with open(self.storage_dir / "stats.json", "w") as f:
                    json.dump(asdict(self._stats), f, indent=2)
            except Exception:
                pass

    def _load(self):
        """Load cache from disk."""
        cache_file = self.storage_dir / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                for h, entry_data in data.items():
                    entry = CacheEntry(**entry_data)
                    if not entry.is_expired:
                        self._entries[h] = entry
                        self._prompts.append((h, entry.prompt))
            except Exception as e:
                logger.warning(f"Error loading cache: {e}")

        stats_file = self.storage_dir / "stats.json"
        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    data = json.load(f)
                self._stats = CacheStats(**data)
            except Exception:
                pass


def get_smart_cache() -> SmartResponseCache:
    """Get singleton cache instance."""
    if not hasattr(get_smart_cache, "_instance"):
        get_smart_cache._instance = SmartResponseCache()
    return get_smart_cache._instance
