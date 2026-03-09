"""
File Watcher - Auto-index project files on change
===================================================

Uses watchdog to monitor project directories and re-index changed files
in both TF-IDF and vector indexes for real-time RAG updates.

Usage:
    watcher = FileWatcher(rag_system)
    watcher.watch("/path/to/project")
    # ... files get auto-indexed on save ...
    watcher.stop()
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

# File types to index
INDEXABLE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".md"}

# Directories to exclude
EXCLUDE_DIRS = {"node_modules", ".venv", "__pycache__", ".git", "dist", "build", ".tox", "env", ".env"}


class _DebouncedHandler:
    """Debounced file change handler — waits for changes to settle before indexing."""

    def __init__(self, rag, debounce_seconds: float = 2.0):
        self._rag = rag
        self._debounce = debounce_seconds
        self._pending: dict = {}  # path -> timestamp
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def on_change(self, path: str):
        """Record a file change. Actual indexing happens after debounce period."""
        ext = os.path.splitext(path)[1].lower()
        if ext not in INDEXABLE_EXTENSIONS:
            return

        # Check exclusions
        parts = Path(path).parts
        if any(p in EXCLUDE_DIRS for p in parts):
            return

        with self._lock:
            self._pending[path] = time.time()

            # Reset debounce timer
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        """Index all pending files."""
        with self._lock:
            paths = dict(self._pending)
            self._pending.clear()

        if not paths:
            return

        count = 0
        for path in paths:
            try:
                if not os.path.exists(path):
                    # File was deleted — remove from index
                    self._rag._index.remove_document(
                        self._rag._generate_doc_id(path, "file")
                    )
                    logger.debug(f"Removed from index: {path}")
                    continue

                content = Path(path).read_text(encoding="utf-8", errors="ignore")
                if len(content) > 100000:
                    continue  # Skip very large files

                ext = os.path.splitext(path)[1]
                lang_map = {
                    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
                    ".js": "javascript", ".jsx": "javascript", ".md": "markdown",
                }

                from .rag_system import Document
                doc = Document(
                    doc_id=self._rag._generate_doc_id(content, "file"),
                    content=content,
                    source_type="file",
                    source_path=path,
                    title=os.path.basename(path),
                    language=lang_map.get(ext, "text"),
                )
                self._rag._index.add_document(doc)
                count += 1
            except Exception as e:
                logger.debug(f"Error indexing {path}: {e}")

        if count > 0:
            self._rag._save_index()
            logger.info(f"Auto-indexed {count} changed file(s)")


class FileWatcher:
    """
    Watches project directories for file changes and auto-indexes them.

    Requires: pip install watchdog>=4.0.0
    """

    def __init__(self, rag_system, debounce_seconds: float = 2.0):
        self._rag = rag_system
        self._handler = _DebouncedHandler(rag_system, debounce_seconds)
        self._observer = None
        self._watched_paths: Set[str] = set()

    def watch(self, path: str) -> bool:
        """
        Start watching a directory for file changes.

        Args:
            path: Directory path to watch

        Returns:
            True if watching started successfully
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            path = os.path.abspath(os.path.expanduser(path))
            if not os.path.isdir(path):
                logger.warning(f"Not a directory: {path}")
                return False

            if path in self._watched_paths:
                return True  # Already watching

            class _Handler(FileSystemEventHandler):
                def __init__(self, debounced):
                    self._debounced = debounced

                def on_modified(self, event):
                    if not event.is_directory:
                        self._debounced.on_change(event.src_path)

                def on_created(self, event):
                    if not event.is_directory:
                        self._debounced.on_change(event.src_path)

                def on_deleted(self, event):
                    if not event.is_directory:
                        self._debounced.on_change(event.src_path)

            if self._observer is None:
                self._observer = Observer()
                self._observer.daemon = True
                self._observer.start()

            handler = _Handler(self._handler)
            self._observer.schedule(handler, path, recursive=True)
            self._watched_paths.add(path)

            logger.info(f"Watching for file changes: {path}")
            return True

        except ImportError:
            logger.warning(
                "watchdog not installed. Auto-indexing disabled. "
                "Install with: pip install watchdog>=4.0.0"
            )
            return False
        except Exception as e:
            logger.error(f"Could not start file watcher: {e}")
            return False

    def stop(self):
        """Stop watching all directories."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._watched_paths.clear()
            logger.info("File watcher stopped")

    @property
    def is_watching(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    @property
    def watched_paths(self) -> List[str]:
        return list(self._watched_paths)
