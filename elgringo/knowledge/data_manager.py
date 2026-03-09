"""
Data Manager - Keeps the learning system lean and fast
======================================================

Prevents unbounded growth through:
- Size limits with automatic pruning
- Smart retention (keep valuable, discard low-value)
- Data compression and archiving
- Lazy loading for large datasets
- Performance monitoring
"""

import gzip
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class DataLimits:
    """Configuration for data retention limits"""
    # Maximum items to keep in memory
    max_prompts: int = 500
    max_insights: int = 1000
    max_conversations: int = 200
    max_lessons: int = 500
    max_patterns: int = 100

    # Age limits (days)
    max_conversation_age_days: int = 90
    max_insight_age_days: int = 180
    archive_after_days: int = 30

    # Size limits (bytes)
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB per file
    max_total_storage_bytes: int = 100 * 1024 * 1024  # 100MB total

    # Minimum retention (always keep at least these)
    min_prompts_to_keep: int = 50
    min_insights_to_keep: int = 100
    min_conversations_to_keep: int = 20

    # Performance thresholds
    load_time_warning_ms: int = 500
    memory_warning_mb: int = 50


@dataclass
class DataStats:
    """Statistics about stored data"""
    total_items: int = 0
    total_size_bytes: int = 0
    oldest_item_date: Optional[str] = None
    newest_item_date: Optional[str] = None
    items_by_type: Dict[str, int] = field(default_factory=dict)
    last_cleanup: Optional[str] = None
    last_archive: Optional[str] = None
    load_time_ms: float = 0.0


class DataManager:
    """
    Manages learning data to prevent unbounded growth.

    Features:
    - Automatic pruning when limits exceeded
    - Smart retention based on value (success rate, usage)
    - Compression for archived data
    - Lazy loading for large files
    - Performance monitoring
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team",
        limits: Optional[DataLimits] = None,
        auto_cleanup: bool = True
    ):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.limits = limits or DataLimits()
        self.auto_cleanup = auto_cleanup

        # Subdirectories
        self.active_dir = self.storage_dir / "active"
        self.archive_dir = self.storage_dir / "archive"
        self.index_dir = self.storage_dir / "index"

        # Ensure directories exist
        for d in [self.active_dir, self.archive_dir, self.index_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # In-memory index for fast lookups (loaded lazily)
        self._index: Optional[Dict[str, Any]] = None
        self._index_dirty = False

        # Stats
        self._stats = DataStats()

    def _load_index(self) -> Dict[str, Any]:
        """Lazily load the index"""
        if self._index is None:
            index_file = self.index_dir / "main_index.json"
            if index_file.exists():
                try:
                    with open(index_file) as f:
                        self._index = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load index: {e}")
                    self._index = self._create_empty_index()
            else:
                self._index = self._create_empty_index()
        return self._index

    def _create_empty_index(self) -> Dict[str, Any]:
        """Create empty index structure"""
        return {
            "prompts": {},      # prompt_id -> {file, offset, size, success_rate, usage}
            "insights": {},     # insight_id -> {file, offset, size, confidence, type}
            "conversations": {},  # conv_id -> {file, offset, size, date, outcome}
            "metadata": {
                "created": datetime.now(timezone.utc).isoformat(),
                "last_cleanup": None,
                "last_archive": None,
                "version": 1
            }
        }

    def _save_index(self):
        """Save index to disk"""
        if self._index and self._index_dirty:
            index_file = self.index_dir / "main_index.json"
            try:
                with open(index_file, "w") as f:
                    json.dump(self._index, f)
                self._index_dirty = False
            except Exception as e:
                logger.error(f"Failed to save index: {e}")

    def get_stats(self) -> DataStats:
        """Get current data statistics"""
        import time
        start = time.time()

        index = self._load_index()

        stats = DataStats(
            total_items=sum(len(index[k]) for k in ["prompts", "insights", "conversations"]),
            items_by_type={
                "prompts": len(index["prompts"]),
                "insights": len(index["insights"]),
                "conversations": len(index["conversations"])
            },
            last_cleanup=index["metadata"].get("last_cleanup"),
            last_archive=index["metadata"].get("last_archive"),
        )

        # Calculate total size
        for data_dir in [self.active_dir, self.archive_dir]:
            if data_dir.exists():
                for f in data_dir.rglob("*"):
                    if f.is_file():
                        stats.total_size_bytes += f.stat().st_size

        stats.load_time_ms = (time.time() - start) * 1000

        # Warn if slow
        if stats.load_time_ms > self.limits.load_time_warning_ms:
            logger.warning(
                f"Data load time {stats.load_time_ms:.0f}ms exceeds threshold "
                f"{self.limits.load_time_warning_ms}ms - consider cleanup"
            )

        return stats

    def check_limits(self) -> Dict[str, bool]:
        """Check if any limits are exceeded"""
        index = self._load_index()
        stats = self.get_stats()

        return {
            "prompts_exceeded": len(index["prompts"]) > self.limits.max_prompts,
            "insights_exceeded": len(index["insights"]) > self.limits.max_insights,
            "conversations_exceeded": len(index["conversations"]) > self.limits.max_conversations,
            "storage_exceeded": stats.total_size_bytes > self.limits.max_total_storage_bytes,
            "any_exceeded": (
                len(index["prompts"]) > self.limits.max_prompts or
                len(index["insights"]) > self.limits.max_insights or
                len(index["conversations"]) > self.limits.max_conversations or
                stats.total_size_bytes > self.limits.max_total_storage_bytes
            )
        }

    def cleanup(self, force: bool = False) -> Dict[str, int]:
        """
        Clean up old and low-value data.

        Returns dict of items removed by type.
        """
        limits_check = self.check_limits()
        if not force and not limits_check["any_exceeded"]:
            return {"prompts": 0, "insights": 0, "conversations": 0}

        logger.info("Starting data cleanup...")
        removed = {"prompts": 0, "insights": 0, "conversations": 0}
        index = self._load_index()

        # Clean prompts - keep high success rate, high usage
        if limits_check.get("prompts_exceeded") or force:
            removed["prompts"] = self._cleanup_prompts(index)

        # Clean insights - keep high confidence, recent
        if limits_check.get("insights_exceeded") or force:
            removed["insights"] = self._cleanup_insights(index)

        # Clean conversations - keep recent, successful
        if limits_check.get("conversations_exceeded") or force:
            removed["conversations"] = self._cleanup_conversations(index)

        # Update metadata
        index["metadata"]["last_cleanup"] = datetime.now(timezone.utc).isoformat()
        self._index_dirty = True
        self._save_index()

        logger.info(f"Cleanup complete: removed {sum(removed.values())} items")
        return removed

    def _cleanup_prompts(self, index: Dict) -> int:
        """Clean up prompts, keeping valuable ones"""
        prompts = index["prompts"]
        if len(prompts) <= self.limits.min_prompts_to_keep:
            return 0

        # Score each prompt: success_rate * 0.6 + usage_normalized * 0.4
        max_usage = max((p.get("usage", 1) for p in prompts.values()), default=1)

        scored = []
        for pid, data in prompts.items():
            success = data.get("success_rate", 0.5)
            usage_norm = data.get("usage", 1) / max_usage
            score = success * 0.6 + usage_norm * 0.4
            scored.append((pid, score))

        # Sort by score, keep top N
        scored.sort(key=lambda x: x[1], reverse=True)
        keep_ids = set(pid for pid, _ in scored[:self.limits.max_prompts])

        # Remove low-scoring prompts
        removed = 0
        for pid in list(prompts.keys()):
            if pid not in keep_ids:
                del prompts[pid]
                removed += 1
                self._index_dirty = True

        return removed

    def _cleanup_insights(self, index: Dict) -> int:
        """Clean up insights, keeping valuable ones"""
        insights = index["insights"]
        if len(insights) <= self.limits.min_insights_to_keep:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.limits.max_insight_age_days)
        cutoff_str = cutoff.isoformat()

        # Score: confidence * 0.5 + recency * 0.3 + type_weight * 0.2
        type_weights = {"solution": 1.0, "pattern": 0.9, "lesson": 0.8, "mistake": 0.7, "prompt": 0.6}

        scored = []
        for iid, data in insights.items():
            confidence = data.get("confidence", 0.5)
            created = data.get("created", "")
            recency = 1.0 if created > cutoff_str else 0.3
            type_weight = type_weights.get(data.get("type", ""), 0.5)
            score = confidence * 0.5 + recency * 0.3 + type_weight * 0.2
            scored.append((iid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        keep_ids = set(iid for iid, _ in scored[:self.limits.max_insights])

        removed = 0
        for iid in list(insights.keys()):
            if iid not in keep_ids:
                del insights[iid]
                removed += 1
                self._index_dirty = True

        return removed

    def _cleanup_conversations(self, index: Dict) -> int:
        """Clean up conversations, keeping recent and successful"""
        conversations = index["conversations"]
        if len(conversations) <= self.limits.min_conversations_to_keep:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.limits.max_conversation_age_days)
        cutoff_str = cutoff.isoformat()

        # Score: recency * 0.5 + success * 0.5
        scored = []
        for cid, data in conversations.items():
            date = data.get("date", "")
            recency = 1.0 if date > cutoff_str else 0.2
            success = 1.0 if data.get("outcome") == "success" else 0.3
            score = recency * 0.5 + success * 0.5
            scored.append((cid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        keep_ids = set(cid for cid, _ in scored[:self.limits.max_conversations])

        removed = 0
        for cid in list(conversations.keys()):
            if cid not in keep_ids:
                del conversations[cid]
                removed += 1
                self._index_dirty = True

        return removed

    def archive_old_data(self) -> Dict[str, int]:
        """
        Archive old data to compressed storage.

        Returns dict of items archived by type.
        """
        logger.info("Starting data archival...")
        archived = {"prompts": 0, "insights": 0, "conversations": 0}

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.limits.archive_after_days)
        cutoff_str = cutoff.isoformat()

        # Archive old conversations
        index = self._load_index()

        old_conversations = {
            cid: data for cid, data in index["conversations"].items()
            if data.get("date", "") < cutoff_str
        }

        if old_conversations:
            # Create archive file
            archive_name = f"conversations_{datetime.now().strftime('%Y%m')}.json.gz"
            archive_path = self.archive_dir / archive_name

            # Load existing archive or create new
            existing = []
            if archive_path.exists():
                with gzip.open(archive_path, 'rt') as f:
                    existing = json.load(f)

            # Add old conversations
            existing.extend([
                {"id": cid, **data}
                for cid, data in old_conversations.items()
            ])

            # Write compressed archive
            with gzip.open(archive_path, 'wt') as f:
                json.dump(existing, f)

            # Remove from active index
            for cid in old_conversations:
                del index["conversations"][cid]
                archived["conversations"] += 1
                self._index_dirty = True

        index["metadata"]["last_archive"] = datetime.now(timezone.utc).isoformat()
        self._save_index()

        logger.info(f"Archival complete: {sum(archived.values())} items archived")
        return archived

    def compact_storage(self) -> int:
        """
        Compact storage by removing orphaned data.

        Returns bytes freed.
        """
        bytes_freed = 0
        index = self._load_index()

        # Get all referenced files
        referenced_files = set()
        for data_type in ["prompts", "insights", "conversations"]:
            for item in index[data_type].values():
                if "file" in item:
                    referenced_files.add(item["file"])

        # Find and remove orphaned files
        for f in self.active_dir.rglob("*.json"):
            if f.name not in referenced_files and f.name != "main_index.json":
                bytes_freed += f.stat().st_size
                f.unlink()
                logger.info(f"Removed orphaned file: {f.name}")

        return bytes_freed

    def register_item(
        self,
        item_type: str,
        item_id: str,
        metadata: Dict[str, Any]
    ):
        """Register an item in the index for tracking"""
        index = self._load_index()

        if item_type not in index:
            index[item_type] = {}

        index[item_type][item_id] = {
            **metadata,
            "registered": datetime.now(timezone.utc).isoformat()
        }
        self._index_dirty = True

        # Auto-cleanup if limits exceeded
        if self.auto_cleanup:
            limits = self.check_limits()
            if limits["any_exceeded"]:
                self.cleanup()

        self._save_index()

    def get_item_count(self, item_type: str) -> int:
        """Get count of items by type"""
        index = self._load_index()
        return len(index.get(item_type, {}))

    def should_accept_new_item(self, item_type: str) -> bool:
        """Check if we should accept a new item (before hitting hard limit)"""
        index = self._load_index()
        current = len(index.get(item_type, {}))

        limits_map = {
            "prompts": self.limits.max_prompts,
            "insights": self.limits.max_insights,
            "conversations": self.limits.max_conversations,
        }

        max_allowed = limits_map.get(item_type, 1000)

        # Allow if under 90% of limit, otherwise trigger cleanup first
        if current < max_allowed * 0.9:
            return True

        # At 90%+, cleanup and then allow
        if self.auto_cleanup:
            self.cleanup()

        return True

    def get_health_report(self) -> Dict[str, Any]:
        """Get a health report for the data system"""
        stats = self.get_stats()
        limits = self.check_limits()

        # Calculate health score (0-100)
        health_factors = []

        # Storage usage (40% weight)
        storage_pct = stats.total_size_bytes / self.limits.max_total_storage_bytes
        health_factors.append((1 - min(storage_pct, 1)) * 40)

        # Item counts (30% weight)
        index = self._load_index()
        prompt_pct = len(index["prompts"]) / self.limits.max_prompts
        insight_pct = len(index["insights"]) / self.limits.max_insights
        conv_pct = len(index["conversations"]) / self.limits.max_conversations
        avg_item_pct = (prompt_pct + insight_pct + conv_pct) / 3
        health_factors.append((1 - min(avg_item_pct, 1)) * 30)

        # Load time (30% weight)
        load_pct = stats.load_time_ms / self.limits.load_time_warning_ms
        health_factors.append((1 - min(load_pct, 1)) * 30)

        health_score = sum(health_factors)

        return {
            "health_score": round(health_score, 1),
            "status": "healthy" if health_score > 70 else "warning" if health_score > 40 else "critical",
            "stats": {
                "total_items": stats.total_items,
                "total_size_mb": round(stats.total_size_bytes / (1024 * 1024), 2),
                "load_time_ms": round(stats.load_time_ms, 1),
            },
            "limits_exceeded": limits,
            "recommendations": self._get_recommendations(health_score, limits, stats)
        }

    def _get_recommendations(
        self,
        health_score: float,
        limits: Dict[str, bool],
        stats: DataStats
    ) -> List[str]:
        """Generate recommendations based on current state"""
        recommendations = []

        if limits["storage_exceeded"]:
            recommendations.append("Run cleanup() and archive_old_data() to free storage")

        if limits["prompts_exceeded"]:
            recommendations.append("Prompt limit exceeded - low-value prompts will be pruned")

        if limits["insights_exceeded"]:
            recommendations.append("Insight limit exceeded - old insights will be pruned")

        if limits["conversations_exceeded"]:
            recommendations.append("Conversation limit exceeded - old conversations will be archived")

        if stats.load_time_ms > self.limits.load_time_warning_ms:
            recommendations.append("Load time is slow - consider running compact_storage()")

        if health_score > 80 and not recommendations:
            recommendations.append("System is healthy - no action needed")

        return recommendations


# Singleton instance for easy access
_data_manager: Optional[DataManager] = None


def get_data_manager(storage_dir: str = "~/.ai-dev-team") -> DataManager:
    """Get or create the global DataManager instance"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(storage_dir=storage_dir)
    return _data_manager
