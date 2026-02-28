"""
RAG Service — Semantic retrieval for Fred Assistant context building.

Uses sentence-transformers (local, zero-cost) + ChromaDB (in-process, persistent)
to replace dump-everything context with relevant-only retrieval.

Graceful degradation: if ChromaDB or embeddings unavailable, callers fall back
to the old _build_context() approach.
"""

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_rag_instance: Optional["RAGService"] = None
_rag_lock = threading.Lock()

CHROMA_DIR = os.path.expanduser("~/.fred-assistant/chroma/")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class RAGService:
    """Semantic index and retrieval for memories, tasks, chat, and service results."""

    def __init__(self, chroma_dir: str = CHROMA_DIR, model_name: str = EMBEDDING_MODEL):
        self._chroma_dir = chroma_dir
        self._model_name = model_name
        self._model = None
        self._client = None
        self._collections: dict = {}
        self._initialized = False
        self._init_lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._initialized

    def _ensure_initialized(self) -> bool:
        """Lazy-load model + ChromaDB on first use. Returns True if ready."""
        if self._initialized:
            return True
        with self._init_lock:
            if self._initialized:
                return True
            try:
                from sentence_transformers import SentenceTransformer
                import chromadb

                self._model = SentenceTransformer(self._model_name)
                os.makedirs(self._chroma_dir, exist_ok=True)
                self._client = chromadb.PersistentClient(path=self._chroma_dir)

                collection_names = [
                    "fred_memories",
                    "fred_tasks",
                    "fred_chat",
                    "fred_service_results",
                    "fred_projects",
                    "fred_meetings",
                ]
                for name in collection_names:
                    self._collections[name] = self._client.get_or_create_collection(
                        name=name,
                        metadata={"hnsw:space": "cosine"},
                    )

                self._initialized = True
                logger.info("RAG service initialized (%s, %s)", self._model_name, self._chroma_dir)
                return True
            except Exception as e:
                logger.warning("RAG service init failed: %s", e)
                return False

    # ── Embedding ─────────────────────────────────────────────────

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Batch encode texts into embeddings."""
        return self._model.encode(texts, show_progress_bar=False).tolist()

    def _embed_single(self, text: str) -> list[float]:
        return self._embed([text])[0]

    # ── Index methods ─────────────────────────────────────────────

    def index_memory(self, memory_dict: dict) -> bool:
        """Index a single memory. Idempotent via upsert."""
        if not self._ensure_initialized():
            return False
        try:
            mid = str(memory_dict["id"])
            cat = memory_dict.get("category", "")
            key = memory_dict.get("key", "")
            value = memory_dict.get("value", "")
            context = memory_dict.get("context", "")
            doc = f"{cat}: {key} = {value}"
            if context:
                doc += f" ({context})"

            self._collections["fred_memories"].upsert(
                ids=[mid],
                documents=[doc],
                embeddings=[self._embed_single(doc)],
                metadatas=[{
                    "category": cat,
                    "key": key,
                    "importance": memory_dict.get("importance", 5),
                    "updated_at": memory_dict.get("updated_at", ""),
                }],
            )
            return True
        except Exception as e:
            logger.debug("index_memory failed: %s", e)
            return False

    def index_task(self, task_dict: dict) -> bool:
        """Index a task. Skips/deletes done tasks."""
        if not self._ensure_initialized():
            return False
        try:
            tid = str(task_dict["id"])
            status = task_dict.get("status", "todo")

            if status == "done":
                self.delete_task(tid)
                return True

            title = task_dict.get("title", "")
            desc = task_dict.get("description", "")
            notes = task_dict.get("notes", "")
            tags = task_dict.get("tags", [])
            if isinstance(tags, list):
                tags = ", ".join(tags)

            doc = title
            if desc:
                doc += f": {desc}"
            if notes:
                doc += f" Notes: {notes}"
            if tags:
                doc += f" Tags: {tags}"

            self._collections["fred_tasks"].upsert(
                ids=[tid],
                documents=[doc],
                embeddings=[self._embed_single(doc)],
                metadatas=[{
                    "board_id": task_dict.get("board_id", ""),
                    "status": status,
                    "priority": task_dict.get("priority", 3),
                    "due_date": task_dict.get("due_date") or "",
                }],
            )
            return True
        except Exception as e:
            logger.debug("index_task failed: %s", e)
            return False

    def index_chat_message(self, msg_id: str, role: str, content: str, persona: str = "fred") -> bool:
        """Index a chat message."""
        if not self._ensure_initialized():
            return False
        try:
            if not content or not content.strip():
                return False
            doc = content[:2000]  # cap length
            self._collections["fred_chat"].upsert(
                ids=[str(msg_id)],
                documents=[doc],
                embeddings=[self._embed_single(doc)],
                metadatas=[{"role": role, "persona": persona}],
            )
            return True
        except Exception as e:
            logger.debug("index_chat_message failed: %s", e)
            return False

    def index_service_result(self, result_dict: dict) -> bool:
        """Index a service result."""
        if not self._ensure_initialized():
            return False
        try:
            rid = str(result_dict["id"])
            service = result_dict.get("service", "")
            action = result_dict.get("action", "")
            project = result_dict.get("project_name", "")
            input_summary = result_dict.get("input_summary", "")
            result_text = str(result_dict.get("result", ""))[:500]

            doc = f"{service} {action}"
            if project:
                doc += f" on {project}"
            if input_summary:
                doc += f": {input_summary}"
            if result_text:
                doc += f" Result: {result_text}"

            self._collections["fred_service_results"].upsert(
                ids=[rid],
                documents=[doc],
                embeddings=[self._embed_single(doc)],
                metadatas=[{
                    "service": service,
                    "action": action,
                    "project_name": project,
                }],
            )
            return True
        except Exception as e:
            logger.debug("index_service_result failed: %s", e)
            return False

    def index_meeting(self, meeting_dict: dict) -> bool:
        """Index a meeting item (agenda, daily brief, or meeting note).

        meeting_dict keys:
            id: unique identifier
            type: "agenda" | "daily_brief" | "meeting_note"
            client_id: client identifier
            title/summary: main text content
            content: detailed content (topics, talking points, notes)
            date: date string
        """
        if not self._ensure_initialized():
            return False
        try:
            mid = str(meeting_dict["id"])
            mtype = meeting_dict.get("type", "meeting")
            client_id = meeting_dict.get("client_id", "")
            date = meeting_dict.get("date", "")
            title = meeting_dict.get("title", meeting_dict.get("summary", ""))
            content = meeting_dict.get("content", "")

            doc = f"[{mtype}] {title}"
            if content:
                doc += f": {content[:1500]}"
            if date:
                doc += f" (date: {date})"

            self._collections["fred_meetings"].upsert(
                ids=[mid],
                documents=[doc],
                embeddings=[self._embed_single(doc)],
                metadatas=[{
                    "type": mtype,
                    "client_id": client_id,
                    "date": date,
                }],
            )
            return True
        except Exception as e:
            logger.debug("index_meeting failed: %s", e)
            return False

    def delete_meeting(self, meeting_id: str) -> bool:
        if not self._ensure_initialized():
            return False
        try:
            self._collections["fred_meetings"].delete(ids=[str(meeting_id)])
            return True
        except Exception as e:
            logger.debug("delete_meeting failed: %s", e)
            return False

    def index_project(self, project_id: str, project_dict: dict) -> int:
        """Index a project from the manifest. Creates multiple chunks for rich retrieval.

        Returns the number of chunks indexed.
        """
        if not self._ensure_initialized():
            return 0

        name = project_dict.get("name", project_id)
        status = project_dict.get("status", "unknown")
        intention = project_dict.get("intention", "").strip()
        domain = project_dict.get("domain", "")
        features = project_dict.get("features", [])
        roadmap = project_dict.get("roadmap", [])
        principles = project_dict.get("principles", [])
        tech = project_dict.get("tech_stack", {})

        col = self._collections["fred_projects"]
        indexed = 0

        try:
            # Chunk 1: Overview (intention + status + tech stack)
            tech_summary = ", ".join(f"{k}: {v}" for k, v in tech.items()) if isinstance(tech, dict) else str(tech)
            overview_doc = f"{name} ({status}): {intention}"
            if domain:
                overview_doc += f" Domain: {domain}."
            if tech_summary:
                overview_doc += f" Tech: {tech_summary}."

            col.upsert(
                ids=[f"{project_id}_overview"],
                documents=[overview_doc],
                embeddings=[self._embed_single(overview_doc)],
                metadatas=[{"project": project_id, "chunk": "overview", "status": status}],
            )
            indexed += 1

            # Chunk 2: Features
            if features:
                features_doc = f"{name} features: " + "; ".join(features)
                col.upsert(
                    ids=[f"{project_id}_features"],
                    documents=[features_doc],
                    embeddings=[self._embed_single(features_doc)],
                    metadatas=[{"project": project_id, "chunk": "features", "status": status}],
                )
                indexed += 1

            # Chunk 3: Roadmap
            if roadmap:
                roadmap_doc = f"{name} roadmap and next steps: " + "; ".join(roadmap)
                col.upsert(
                    ids=[f"{project_id}_roadmap"],
                    documents=[roadmap_doc],
                    embeddings=[self._embed_single(roadmap_doc)],
                    metadatas=[{"project": project_id, "chunk": "roadmap", "status": status}],
                )
                indexed += 1

            # Chunk 4: Principles
            if principles:
                principles_doc = f"{name} principles and rules: " + "; ".join(principles)
                col.upsert(
                    ids=[f"{project_id}_principles"],
                    documents=[principles_doc],
                    embeddings=[self._embed_single(principles_doc)],
                    metadatas=[{"project": project_id, "chunk": "principles", "status": status}],
                )
                indexed += 1

        except Exception as e:
            logger.debug("index_project %s failed: %s", project_id, e)

        return indexed

    def sync_projects_manifest(self) -> int:
        """Load projects.yaml and index all projects. Returns total chunks indexed."""
        if not self._ensure_initialized():
            return 0

        manifest_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "projects.yaml"
        )
        if not os.path.isfile(manifest_path):
            logger.warning("projects.yaml not found at %s", manifest_path)
            return 0

        try:
            import yaml
            with open(manifest_path, "r") as f:
                data = yaml.safe_load(f)
        except ImportError:
            # Fallback: parse YAML-like structure manually if PyYAML not installed
            logger.warning("PyYAML not installed, trying json fallback for projects manifest")
            return 0
        except Exception as e:
            logger.warning("Failed to load projects.yaml: %s", e)
            return 0

        projects = data.get("projects", {})
        total = 0
        for pid, pdata in projects.items():
            total += self.index_project(pid, pdata)

        logger.info("Projects manifest indexed: %d chunks from %d projects", total, len(projects))
        return total

    # ── Delete methods ────────────────────────────────────────────

    def delete_memory(self, memory_id: str) -> bool:
        if not self._ensure_initialized():
            return False
        try:
            self._collections["fred_memories"].delete(ids=[str(memory_id)])
            return True
        except Exception as e:
            logger.debug("delete_memory failed: %s", e)
            return False

    def delete_task(self, task_id: str) -> bool:
        if not self._ensure_initialized():
            return False
        try:
            self._collections["fred_tasks"].delete(ids=[str(task_id)])
            return True
        except Exception as e:
            logger.debug("delete_task failed: %s", e)
            return False

    # ── Query methods ─────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        collections: list[str] | None = None,
        n_results: int = 10,
        where: dict | None = None,
    ) -> list[dict]:
        """Search across specified collections. Returns sorted by distance."""
        if not self._ensure_initialized():
            return []

        target_names = collections or list(self._collections.keys())
        embedding = self._embed_single(query_text)
        results = []

        for name in target_names:
            col = self._collections.get(name)
            if not col:
                continue
            try:
                count = col.count()
                if count == 0:
                    continue
                n = min(n_results, count)
                kwargs = {
                    "query_embeddings": [embedding],
                    "n_results": n,
                }
                if where:
                    kwargs["where"] = where
                res = col.query(**kwargs)

                ids = res.get("ids", [[]])[0]
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0]

                for i in range(len(ids)):
                    results.append({
                        "id": ids[i],
                        "document": docs[i],
                        "metadata": metas[i] if i < len(metas) else {},
                        "distance": dists[i] if i < len(dists) else 999,
                        "collection": name,
                    })
            except Exception as e:
                logger.debug("query collection %s failed: %s", name, e)

        results.sort(key=lambda r: r["distance"])
        return results

    def query_for_context(
        self,
        user_message: str,
        n_memories: int = 15,
        n_tasks: int = 10,
        n_service_results: int = 5,
        n_projects: int = 5,
        n_meetings: int = 5,
        relevance_threshold: float = 1.2,
    ) -> dict:
        """Purpose-built query for context building. Returns categorized results."""
        if not self._ensure_initialized():
            return {"memories": [], "tasks": [], "service_results": [], "projects": [], "meetings": []}

        embedding = self._embed_single(user_message)

        def _query_collection(name: str, n: int) -> list[dict]:
            col = self._collections.get(name)
            if not col:
                return []
            try:
                count = col.count()
                if count == 0:
                    return []
                n = min(n, count)
                res = col.query(query_embeddings=[embedding], n_results=n)
                items = []
                ids = res.get("ids", [[]])[0]
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0]
                for i in range(len(ids)):
                    dist = dists[i] if i < len(dists) else 999
                    if dist <= relevance_threshold:
                        items.append({
                            "id": ids[i],
                            "document": docs[i],
                            "metadata": metas[i] if i < len(metas) else {},
                            "distance": dist,
                        })
                return items
            except Exception:
                return []

        return {
            "memories": _query_collection("fred_memories", n_memories),
            "tasks": _query_collection("fred_tasks", n_tasks),
            "service_results": _query_collection("fred_service_results", n_service_results),
            "projects": _query_collection("fred_projects", n_projects),
            "meetings": _query_collection("fred_meetings", n_meetings),
        }

    # ── Background sync ──────────────────────────────────────────

    def full_sync(self) -> dict:
        """Re-index all SQLite data into ChromaDB."""
        if not self._ensure_initialized():
            return {"error": "not initialized"}

        from products.fred_assistant.services import memory_service, task_service
        from products.fred_assistant.services import platform_services
        from products.fred_assistant.database import get_conn

        counts = {"memories": 0, "tasks": 0, "chat_messages": 0, "service_results": 0, "projects": 0}

        # Memories
        try:
            memories = memory_service.list_memories()
            for m in memories:
                if self.index_memory(m):
                    counts["memories"] += 1
        except Exception as e:
            logger.warning("RAG sync memories failed: %s", e)

        # Active tasks
        try:
            tasks = task_service.list_tasks()
            for t in tasks:
                if t.get("status") != "done":
                    if self.index_task(t):
                        counts["tasks"] += 1
        except Exception as e:
            logger.warning("RAG sync tasks failed: %s", e)

        # Recent chat messages
        try:
            with get_conn() as conn:
                rows = conn.execute(
                    "SELECT id, role, content, persona FROM chat_messages ORDER BY id DESC LIMIT 200"
                ).fetchall()
            for r in rows:
                row = dict(r)
                if self.index_chat_message(str(row["id"]), row["role"], row["content"], row.get("persona", "fred")):
                    counts["chat_messages"] += 1
        except Exception as e:
            logger.warning("RAG sync chat failed: %s", e)

        # Service results
        try:
            results = platform_services.get_recent_results(limit=50)
            for sr in results:
                if self.index_service_result(sr):
                    counts["service_results"] += 1
        except Exception as e:
            logger.warning("RAG sync service results failed: %s", e)

        # Projects manifest
        try:
            counts["projects"] = self.sync_projects_manifest()
        except Exception as e:
            logger.warning("RAG sync projects failed: %s", e)

        logger.info("RAG full sync complete: %s", counts)
        return counts

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Collection counts for health/debug."""
        if not self._initialized:
            return {"ready": False}
        try:
            return {
                "ready": True,
                "collections": {
                    name: col.count() for name, col in self._collections.items()
                },
            }
        except Exception:
            return {"ready": False}


# ── Module-level access ──────────────────────────────────────────

def get_rag() -> RAGService:
    """Thread-safe singleton access."""
    global _rag_instance
    if _rag_instance is None:
        with _rag_lock:
            if _rag_instance is None:
                _rag_instance = RAGService()
    return _rag_instance


def _set_rag(instance: RAGService):
    """Replace singleton (for testing)."""
    global _rag_instance
    _rag_instance = instance


def start_background_sync():
    """Spawn a daemon thread to run full_sync()."""
    def _sync():
        try:
            rag = get_rag()
            if rag._ensure_initialized():
                counts = rag.full_sync()
                logger.info("Background RAG sync done: %s", counts)
        except Exception as e:
            logger.warning("Background RAG sync failed: %s", e)

    t = threading.Thread(target=_sync, daemon=True, name="rag-sync")
    t.start()
    return t


def get_stats() -> dict:
    """Collection counts for health endpoint."""
    return get_rag().get_stats()
