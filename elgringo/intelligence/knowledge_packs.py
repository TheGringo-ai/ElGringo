"""
Team Memory Export — TeamMemoryExporter
=========================================

Moat feature #4: No competitor (CrewAI, AutoGen, LangGraph) has this.
Export/import portable knowledge packs to share team intelligence across projects.

Usage:
    exporter = get_exporter()
    pack_id = exporter.export_pack("fastapi-patterns", description="FastAPI best practices")
    exporter.import_pack("/path/to/pack.json")
    packs = exporter.list_packs()
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PackFilter:
    """Filter for knowledge pack export."""
    projects: List[str] = field(default_factory=list)  # filter by project name
    tags: List[str] = field(default_factory=list)  # filter by tags
    categories: List[str] = field(default_factory=list)  # solution, mistake, pattern, lesson
    min_confidence: float = 0.0
    since: str = ""  # ISO date string


@dataclass
class PackMetadata:
    """Metadata for a knowledge pack."""
    pack_id: str
    name: str
    description: str = ""
    version: str = "1.0"
    created_at: str = ""
    created_by: str = "el-gringo"
    item_count: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    source_projects: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.pack_id:
            self.pack_id = f"pack-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgeItem:
    """A single knowledge item in a pack."""
    item_id: str
    item_type: str  # solution, mistake, pattern, lesson
    content: str
    context: str = ""
    tags: List[str] = field(default_factory=list)
    source_project: str = ""
    confidence: float = 1.0
    created_at: str = ""

    def __post_init__(self):
        if not self.item_id:
            self.item_id = f"item-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgePack:
    """A portable knowledge pack."""
    version: str = "1.0"
    metadata: Optional[PackMetadata] = None
    items: List[KnowledgeItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "metadata": asdict(self.metadata) if self.metadata else {},
            "items": [asdict(i) for i in self.items],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgePack":
        meta = PackMetadata(**data.get("metadata", {})) if data.get("metadata") else None
        items = [KnowledgeItem(**i) for i in data.get("items", [])]
        return cls(version=data.get("version", "1.0"), metadata=meta, items=items)


@dataclass
class MergeResult:
    """Result of merging knowledge packs."""
    merged_pack_id: str
    total_items: int
    new_items: int
    duplicate_items: int
    conflicts_resolved: int


class TeamMemoryExporter:
    """
    Exports and imports portable knowledge packs.

    Features:
    - Export team knowledge as shareable JSON packs
    - Import packs to bootstrap new projects
    - Merge multiple packs with deduplication
    - Filter exports by project, tag, category
    - Version tracking
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/packs"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._packs: Dict[str, PackMetadata] = {}
        self._items: List[KnowledgeItem] = []
        self._load()

    def _load(self):
        """Load state from disk."""
        index_file = self.storage_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file) as f:
                    data = json.load(f)
                self._packs = {p["pack_id"]: PackMetadata(**p) for p in data.get("packs", [])}
                self._items = [KnowledgeItem(**i) for i in data.get("items", [])]
            except Exception as e:
                logger.warning(f"Error loading packs index: {e}")

    def _save(self):
        """Save state to disk."""
        try:
            with open(self.storage_dir / "index.json", "w") as f:
                json.dump({
                    "packs": [asdict(p) for p in self._packs.values()],
                    "items": [asdict(i) for i in self._items],
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving packs index: {e}")

    def add_knowledge(
        self, item_type: str, content: str, context: str = "",
        tags: Optional[List[str]] = None, source_project: str = "",
        confidence: float = 1.0,
    ) -> str:
        """Add a knowledge item to the store. Returns item_id."""
        item = KnowledgeItem(
            item_id=f"item-{uuid.uuid4().hex[:8]}",
            item_type=item_type, content=content, context=context,
            tags=tags or [], source_project=source_project, confidence=confidence,
        )
        self._items.append(item)
        self._save()
        return item.item_id

    def export_pack(
        self, name: str, description: str = "",
        filters: Optional[PackFilter] = None,
    ) -> str:
        """Export knowledge as a portable pack. Returns pack_id."""
        pack_id = f"pack-{uuid.uuid4().hex[:8]}"

        # Filter items
        items = self._filter_items(filters) if filters else list(self._items)

        # Build category counts
        categories: Dict[str, int] = {}
        all_tags: set = set()
        source_projects: set = set()
        for item in items:
            categories[item.item_type] = categories.get(item.item_type, 0) + 1
            all_tags.update(item.tags)
            if item.source_project:
                source_projects.add(item.source_project)

        metadata = PackMetadata(
            pack_id=pack_id, name=name, description=description,
            item_count=len(items), categories=categories,
            tags=sorted(all_tags), source_projects=sorted(source_projects),
        )

        pack = KnowledgePack(metadata=metadata, items=items)

        # Save to file
        pack_file = self.storage_dir / f"{pack_id}.json"
        with open(pack_file, "w") as f:
            json.dump(pack.to_dict(), f, indent=2)

        self._packs[pack_id] = metadata
        self._save()
        logger.info(f"Exported pack '{name}' ({pack_id}): {len(items)} items")
        return pack_id

    def import_pack(self, pack_path: str) -> Dict[str, Any]:
        """Import a knowledge pack from file."""
        path = Path(os.path.expanduser(pack_path))
        if not path.exists():
            return {"error": f"Pack file not found: {pack_path}"}

        try:
            with open(path) as f:
                data = json.load(f)
            pack = KnowledgePack.from_dict(data)
        except Exception as e:
            return {"error": f"Failed to parse pack: {e}"}

        # Deduplicate against existing items
        existing_contents = {i.content for i in self._items}
        new_items = []
        duplicates = 0

        for item in pack.items:
            if item.content in existing_contents:
                duplicates += 1
            else:
                item.item_id = f"item-{uuid.uuid4().hex[:8]}"  # New ID to avoid collisions
                new_items.append(item)
                existing_contents.add(item.content)

        self._items.extend(new_items)

        # Register the pack
        if pack.metadata:
            pack.metadata.item_count = len(pack.items)
            self._packs[pack.metadata.pack_id] = pack.metadata

        self._save()

        return {
            "imported": len(new_items),
            "duplicates_skipped": duplicates,
            "total_items_now": len(self._items),
            "pack_name": pack.metadata.name if pack.metadata else "unknown",
        }

    def merge_packs(self, pack_ids: List[str]) -> Dict[str, Any]:
        """Merge multiple packs into one."""
        all_items: List[KnowledgeItem] = []
        seen_contents: set = set()
        duplicates = 0

        for pack_id in pack_ids:
            pack_file = self.storage_dir / f"{pack_id}.json"
            if not pack_file.exists():
                continue
            try:
                with open(pack_file) as f:
                    pack = KnowledgePack.from_dict(json.load(f))
                for item in pack.items:
                    if item.content in seen_contents:
                        duplicates += 1
                    else:
                        all_items.append(item)
                        seen_contents.add(item.content)
            except Exception as e:
                logger.warning(f"Error loading pack {pack_id}: {e}")

        if not all_items:
            return {"error": "No items found in specified packs"}

        # Create merged pack
        merged_name = f"merged-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
        merged_pack = KnowledgePack(
            metadata=PackMetadata(
                pack_id=f"pack-{uuid.uuid4().hex[:8]}",
                name=merged_name,
                description=f"Merged from {len(pack_ids)} packs",
                item_count=len(all_items),
            ),
            items=all_items,
        )

        pack_file = self.storage_dir / f"{merged_pack.metadata.pack_id}.json"
        with open(pack_file, "w") as f:
            json.dump(merged_pack.to_dict(), f, indent=2)

        self._packs[merged_pack.metadata.pack_id] = merged_pack.metadata
        self._save()

        return {
            "merged_pack_id": merged_pack.metadata.pack_id,
            "total_items": len(all_items),
            "duplicates_removed": duplicates,
            "source_packs": len(pack_ids),
        }

    def list_packs(self) -> List[Dict[str, Any]]:
        """List all available packs."""
        return [asdict(p) for p in sorted(self._packs.values(), key=lambda p: p.created_at, reverse=True)]

    def get_pack_info(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a pack."""
        meta = self._packs.get(pack_id)
        if not meta:
            return None
        result = asdict(meta)

        # Check if pack file exists and get size
        pack_file = self.storage_dir / f"{pack_id}.json"
        if pack_file.exists():
            result["file_size_kb"] = round(pack_file.stat().st_size / 1024, 1)

        return result

    def delete_pack(self, pack_id: str) -> bool:
        """Delete a pack."""
        if pack_id not in self._packs:
            return False

        del self._packs[pack_id]
        pack_file = self.storage_dir / f"{pack_id}.json"
        if pack_file.exists():
            pack_file.unlink()
        self._save()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge store statistics."""
        categories: Dict[str, int] = {}
        for item in self._items:
            categories[item.item_type] = categories.get(item.item_type, 0) + 1

        return {
            "total_items": len(self._items),
            "total_packs": len(self._packs),
            "categories": categories,
            "storage_dir": str(self.storage_dir),
        }

    def _filter_items(self, filters: PackFilter) -> List[KnowledgeItem]:
        """Filter items based on PackFilter criteria."""
        result = self._items

        if filters.projects:
            result = [i for i in result if i.source_project in filters.projects]
        if filters.tags:
            filter_tags = set(filters.tags)
            result = [i for i in result if set(i.tags) & filter_tags]
        if filters.categories:
            result = [i for i in result if i.item_type in filters.categories]
        if filters.min_confidence > 0:
            result = [i for i in result if i.confidence >= filters.min_confidence]
        if filters.since:
            result = [i for i in result if i.created_at >= filters.since]

        return result


def get_exporter() -> TeamMemoryExporter:
    """Get singleton exporter instance."""
    if not hasattr(get_exporter, "_instance"):
        get_exporter._instance = TeamMemoryExporter()
    return get_exporter._instance
