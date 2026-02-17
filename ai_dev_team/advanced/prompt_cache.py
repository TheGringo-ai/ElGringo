"""
Prompt Cache Manager - 90% Cost Reduction

SECRET WEAPON #3: Anthropic's prompt caching feature allows you to cache
large contexts (like entire codebases) and reuse them across requests
at a 90% discount!

How it works:
1. First request with a large context: Full price
2. Subsequent requests with same context: 90% off!
3. Cache lasts 5 minutes (extended with each use)

This is HUGE for:
- Codebase-aware coding assistants
- Documentation Q&A
- Long conversation contexts
- Repeated analysis tasks

Most developers don't know this exists and are paying 10x more than necessary!
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached prompt/context entry"""
    cache_key: str
    content: str
    token_count: int
    created_at: datetime
    last_used: datetime
    hit_count: int = 0
    estimated_savings: float = 0.0


@dataclass
class CacheStats:
    """Statistics about cache usage"""
    total_entries: int
    total_tokens_cached: int
    total_hits: int
    total_misses: int
    estimated_savings_usd: float
    cache_hit_rate: float


class PromptCacheManager:
    """
    Intelligent Prompt Cache Manager

    Automatically caches large contexts and manages cache lifecycle
    to maximize cost savings with Anthropic's prompt caching.

    Usage:
        cache = PromptCacheManager()

        # Cache a large context (like your codebase)
        cache.cache_context("codebase", codebase_content)

        # Use cached context in requests (90% cheaper!)
        response = await cache.generate_with_cache(
            "codebase",
            "How does the authentication work?"
        )

        # Check savings
        print(cache.get_stats())
    """

    # Anthropic pricing (per 1M tokens)
    PRICING = {
        "input": 3.00,  # $3 per 1M input tokens
        "cache_write": 3.75,  # $3.75 per 1M tokens (25% premium to write)
        "cache_read": 0.30,  # $0.30 per 1M tokens (90% discount!)
    }

    # Minimum tokens for caching to be worthwhile
    MIN_CACHE_TOKENS = 1024
    # Cache TTL (Anthropic's is 5 min, extended on use)
    CACHE_TTL_MINUTES = 5

    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            persist_path: Optional path to persist cache metadata
        """
        self._client = None
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "total_savings": 0.0
        }
        self.persist_path = persist_path

        if persist_path:
            self._load_cache_metadata()

    async def _get_client(self):
        """Get Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                logger.error("Anthropic SDK not installed")
        return self._client

    def _compute_hash(self, content: str) -> str:
        """Compute hash of content for cache key"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _estimate_tokens(self, content: str) -> int:
        """Rough token estimation (4 chars per token)"""
        return len(content) // 4

    def cache_context(
        self,
        name: str,
        content: str,
        force: bool = False
    ) -> CacheEntry:
        """
        Cache a context for later use.

        Args:
            name: Identifier for this context
            content: The content to cache
            force: Force cache even if under minimum tokens

        Returns:
            CacheEntry with cache information
        """
        token_count = self._estimate_tokens(content)

        if token_count < self.MIN_CACHE_TOKENS and not force:
            logger.warning(
                f"Context '{name}' has only {token_count} tokens. "
                f"Minimum {self.MIN_CACHE_TOKENS} recommended for caching."
            )

        cache_key = f"{name}:{self._compute_hash(content)}"
        now = datetime.now()

        entry = CacheEntry(
            cache_key=cache_key,
            content=content,
            token_count=token_count,
            created_at=now,
            last_used=now,
            hit_count=0
        )

        self._cache[name] = entry
        logger.info(f"Cached context '{name}': {token_count} tokens")

        return entry

    def cache_codebase(self, directory: str, extensions: List[str] = None) -> CacheEntry:
        """
        Cache an entire codebase directory.

        Args:
            directory: Path to code directory
            extensions: File extensions to include (default: common code files)

        Returns:
            CacheEntry with the combined codebase
        """
        extensions = extensions or [
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go',
            '.rs', '.cpp', '.c', '.h', '.cs', '.rb', '.php'
        ]

        codebase_content = []
        total_files = 0

        for ext in extensions:
            for filepath in Path(directory).rglob(f"*{ext}"):
                # Skip common non-essential directories
                if any(skip in str(filepath) for skip in [
                    'node_modules', '__pycache__', '.git', 'venv',
                    'dist', 'build', '.next', 'target'
                ]):
                    continue

                try:
                    relative_path = filepath.relative_to(directory)
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    codebase_content.append(f"### {relative_path}\n```\n{content}\n```\n")
                    total_files += 1
                except Exception as e:
                    logger.warning(f"Could not read {filepath}: {e}")

        combined = "\n".join(codebase_content)
        logger.info(f"Loaded {total_files} files from {directory}")

        return self.cache_context("codebase", combined)

    async def generate_with_cache(
        self,
        cache_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate response using cached context.

        This is where the magic happens! If the context is cached,
        you pay only 10% of the normal input token cost.

        Args:
            cache_name: Name of cached context
            prompt: User's question/request
            system_prompt: Optional system prompt
            max_tokens: Maximum response tokens

        Returns:
            Tuple of (response_text, usage_info)
        """
        client = await self._get_client()
        if not client:
            return ("Prompt caching requires ANTHROPIC_API_KEY", {})

        if cache_name not in self._cache:
            self._stats["misses"] += 1
            return (f"Cache '{cache_name}' not found. Use cache_context() first.", {})

        entry = self._cache[cache_name]
        entry.last_used = datetime.now()
        entry.hit_count += 1
        self._stats["hits"] += 1

        # Build message with cache control
        # The cached content uses cache_control to enable caching
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": entry.content,
                    "cache_control": {"type": "ephemeral"}  # Enable caching!
                },
                {
                    "type": "text",
                    "text": f"\n\n---\n\nBased on the above context, please help with:\n{prompt}"
                }
            ]
        }]

        system = system_prompt or "You are an expert assistant with access to a codebase/context. Answer questions accurately based on the provided context."

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system,
                messages=messages
            )

            # Calculate savings
            usage = response.usage
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0

            # If we had a cache read, we saved money!
            if cache_read > 0:
                # Normal cost vs cached cost
                normal_cost = (cache_read / 1_000_000) * self.PRICING["input"]
                cached_cost = (cache_read / 1_000_000) * self.PRICING["cache_read"]
                savings = normal_cost - cached_cost

                entry.estimated_savings += savings
                self._stats["total_savings"] += savings

                logger.info(f"Cache hit! Saved ${savings:.4f} on this request")

            usage_info = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_creation_tokens": cache_creation,
                "cache_read_tokens": cache_read,
                "estimated_savings": entry.estimated_savings
            }

            return (response.content[0].text, usage_info)

        except Exception as e:
            logger.error(f"Cached generation error: {e}")
            return (f"Error: {e}", {})

    async def ask_codebase(self, question: str) -> str:
        """
        Quick helper to ask questions about cached codebase.

        Make sure to call cache_codebase() first!
        """
        response, _ = await self.generate_with_cache("codebase", question)
        return response

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        total_tokens = sum(e.token_count for e in self._cache.values())
        total_hits = self._stats["hits"]
        total_misses = self._stats["misses"]
        total = total_hits + total_misses

        return CacheStats(
            total_entries=len(self._cache),
            total_tokens_cached=total_tokens,
            total_hits=total_hits,
            total_misses=total_misses,
            estimated_savings_usd=round(self._stats["total_savings"], 4),
            cache_hit_rate=round(total_hits / max(total, 1), 2)
        )

    def clear_cache(self, name: Optional[str] = None):
        """Clear cache entries"""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()

    def list_cached_contexts(self) -> List[Dict[str, Any]]:
        """List all cached contexts"""
        return [{
            "name": name,
            "tokens": entry.token_count,
            "hits": entry.hit_count,
            "created": entry.created_at.isoformat(),
            "last_used": entry.last_used.isoformat(),
            "savings": f"${entry.estimated_savings:.4f}"
        } for name, entry in self._cache.items()]

    def _load_cache_metadata(self):
        """Load cache metadata from disk"""
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                with open(self.persist_path) as f:
                    data = json.load(f)
                    self._stats = data.get("stats", self._stats)
            except Exception as e:
                logger.warning(f"Could not load cache metadata: {e}")

    def _save_cache_metadata(self):
        """Save cache metadata to disk"""
        if self.persist_path:
            try:
                data = {
                    "stats": self._stats,
                    "entries": [e.cache_key for e in self._cache.values()]
                }
                with open(self.persist_path, 'w') as f:
                    json.dump(data, f)
            except Exception as e:
                logger.warning(f"Could not save cache metadata: {e}")


# Convenience functions
async def quick_codebase_qa(directory: str, question: str) -> str:
    """
    Quick codebase Q&A with automatic caching.

    First call caches the codebase, subsequent calls are 90% cheaper!
    """
    cache = PromptCacheManager()
    cache.cache_codebase(directory)
    return await cache.ask_codebase(question)
