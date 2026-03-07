"""Tests for rag_service — semantic retrieval for Fred Assistant."""

import os
import sys
import shutil
import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from products.fred_assistant.services import memory_service, task_service
from products.fred_assistant.services.platform_services import store_service_result
from products.fred_assistant.services import rag_service as rag_mod
from products.fred_assistant.services.rag_service import RAGService, _set_rag, get_rag


# ── Fixtures ─────────────────────────────────────────────────────

DIM = 384  # all-MiniLM-L6-v2 output dimension


def _deterministic_encode(texts, **kwargs):
    """Return deterministic 384-dim vectors based on text hash."""
    vecs = []
    for t in texts:
        rng = np.random.RandomState(hash(t) % (2**31))
        vec = rng.randn(DIM).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vecs.append(vec)
    return np.array(vecs)


@pytest.fixture
def rag(tmp_path):
    """RAGService with temp ChromaDB dir + mock sentence-transformers model."""
    chroma_dir = str(tmp_path / "chroma")
    service = RAGService(chroma_dir=chroma_dir, model_name="mock")

    mock_model = MagicMock()
    mock_model.encode = _deterministic_encode

    # Patch lazy init to use mock model + real chromadb
    import chromadb

    service._model = mock_model
    service._client = chromadb.PersistentClient(path=chroma_dir)
    for name in ["fred_memories", "fred_tasks", "fred_chat", "fred_service_results", "fred_projects"]:
        service._collections[name] = service._client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )
    service._initialized = True

    # Install as module singleton
    _set_rag(service)
    yield service
    _set_rag(None)


# ── Index: memory ─────────────────────────────────────────────────

def test_index_memory(rag):
    ok = rag.index_memory({
        "id": "mem1",
        "category": "preferences",
        "key": "editor",
        "value": "VS Code",
        "context": "Primary IDE",
        "importance": 8,
        "updated_at": "2026-01-01T00:00:00",
    })
    assert ok is True
    assert rag._collections["fred_memories"].count() == 1


def test_index_memory_with_no_context(rag):
    ok = rag.index_memory({
        "id": "mem2",
        "category": "tech",
        "key": "language",
        "value": "Python",
    })
    assert ok is True


def test_upsert_memory_same_id(rag):
    rag.index_memory({"id": "dup1", "category": "a", "key": "k", "value": "v1"})
    rag.index_memory({"id": "dup1", "category": "a", "key": "k", "value": "v2"})
    assert rag._collections["fred_memories"].count() == 1


# ── Index: task ───────────────────────────────────────────────────

def test_index_task(rag):
    ok = rag.index_task({
        "id": "t1",
        "title": "Deploy RAG service",
        "description": "Add semantic search to Fred",
        "status": "in_progress",
        "board_id": "elgringo",
        "priority": 1,
        "tags": ["backend", "ai"],
    })
    assert ok is True
    assert rag._collections["fred_tasks"].count() == 1


def test_index_done_task_skips(rag):
    rag.index_task({"id": "tdone", "title": "Old task", "status": "done"})
    assert rag._collections["fred_tasks"].count() == 0


def test_index_task_then_done_deletes(rag):
    rag.index_task({"id": "t2", "title": "Active", "status": "todo"})
    assert rag._collections["fred_tasks"].count() == 1
    rag.index_task({"id": "t2", "title": "Active", "status": "done"})
    assert rag._collections["fred_tasks"].count() == 0


def test_upsert_task_same_id(rag):
    rag.index_task({"id": "u1", "title": "V1", "status": "todo"})
    rag.index_task({"id": "u1", "title": "V2", "status": "in_progress"})
    assert rag._collections["fred_tasks"].count() == 1


# ── Index: chat ───────────────────────────────────────────────────

def test_index_chat_message(rag):
    ok = rag.index_chat_message("c1", "user", "What are my tasks for today?")
    assert ok is True
    assert rag._collections["fred_chat"].count() == 1


def test_index_empty_chat_message_skips(rag):
    ok = rag.index_chat_message("c2", "user", "")
    assert ok is False
    assert rag._collections["fred_chat"].count() == 0


# ── Index: service result ────────────────────────────────────────

def test_index_service_result(rag):
    ok = rag.index_service_result({
        "id": "sr1",
        "service": "code_audit",
        "action": "full_audit",
        "project_name": "ElGringo",
        "input_summary": "Full security audit",
        "result": "No critical issues found",
    })
    assert ok is True
    assert rag._collections["fred_service_results"].count() == 1


# ── Delete ────────────────────────────────────────────────────────

def test_delete_memory(rag):
    rag.index_memory({"id": "del1", "category": "tmp", "key": "k", "value": "v"})
    assert rag._collections["fred_memories"].count() == 1
    rag.delete_memory("del1")
    assert rag._collections["fred_memories"].count() == 0


def test_delete_task(rag):
    rag.index_task({"id": "del2", "title": "Delete me", "status": "todo"})
    assert rag._collections["fred_tasks"].count() == 1
    rag.delete_task("del2")
    assert rag._collections["fred_tasks"].count() == 0


def test_delete_nonexistent_returns_true(rag):
    # ChromaDB silently ignores deletes of unknown IDs
    assert rag.delete_memory("ghost") is True


# ── Query ─────────────────────────────────────────────────────────

def test_query_returns_results(rag):
    rag.index_memory({"id": "q1", "category": "tech", "key": "db", "value": "PostgreSQL"})
    rag.index_memory({"id": "q2", "category": "tech", "key": "cache", "value": "Redis"})
    results = rag.query("database systems")
    assert len(results) >= 1
    assert "id" in results[0]
    assert "document" in results[0]
    assert "distance" in results[0]
    assert "metadata" in results[0]
    assert "collection" in results[0]


def test_query_empty_collection(rag):
    results = rag.query("anything")
    assert results == []


def test_query_specific_collection(rag):
    rag.index_memory({"id": "sc1", "category": "test", "key": "k", "value": "v"})
    rag.index_task({"id": "sc2", "title": "A task", "status": "todo"})
    results = rag.query("test", collections=["fred_memories"])
    assert all(r["collection"] == "fred_memories" for r in results)


def test_query_sorted_by_distance(rag):
    rag.index_memory({"id": "s1", "category": "a", "key": "k1", "value": "Python programming"})
    rag.index_memory({"id": "s2", "category": "b", "key": "k2", "value": "Cooking pasta"})
    results = rag.query("Python code")
    if len(results) >= 2:
        assert results[0]["distance"] <= results[1]["distance"]


# ── query_for_context ─────────────────────────────────────────────

def test_query_for_context_returns_categorized(rag):
    rag.index_memory({"id": "ctx1", "category": "prefs", "key": "lang", "value": "Python"})
    rag.index_task({"id": "ctx2", "title": "Write tests", "status": "todo"})
    rag.index_service_result({
        "id": "ctx3", "service": "test_gen", "action": "generate",
        "project_name": "ElGringo", "result": "10 tests generated",
    })

    result = rag.query_for_context("What tests have been generated?")
    assert "memories" in result
    assert "tasks" in result
    assert "service_results" in result
    assert "projects" in result
    assert isinstance(result["memories"], list)
    assert isinstance(result["tasks"], list)
    assert isinstance(result["service_results"], list)
    assert isinstance(result["projects"], list)


def test_query_for_context_empty(rag):
    result = rag.query_for_context("anything")
    assert result == {"memories": [], "tasks": [], "service_results": [], "projects": []}


def test_query_for_context_respects_threshold(rag):
    rag.index_memory({"id": "th1", "category": "x", "key": "y", "value": "z"})
    # Threshold 0.0 should filter out everything
    result = rag.query_for_context("totally unrelated", relevance_threshold=0.0)
    assert result["memories"] == []


# ── Index: project ────────────────────────────────────────────────

def test_index_project(rag):
    count = rag.index_project("chatterfix", {
        "name": "ChatterFix CMMS",
        "status": "production",
        "intention": "AI-powered maintenance management for field technicians.",
        "domain": "https://chatterfix.com",
        "tech_stack": {"backend": "FastAPI", "frontend": "React Native"},
        "features": ["Voice commands", "OCR scanning", "Work orders"],
        "roadmap": ["AR repair guides", "Predictive maintenance"],
        "principles": ["Technician-first", "Hands-free default"],
    })
    assert count == 4  # overview + features + roadmap + principles
    assert rag._collections["fred_projects"].count() == 4


def test_index_project_minimal(rag):
    count = rag.index_project("tiny", {
        "name": "Tiny Project",
        "intention": "A small test project.",
    })
    assert count == 1  # overview only


def test_index_project_upsert(rag):
    rag.index_project("p1", {"name": "V1", "intention": "Old intent."})
    rag.index_project("p1", {"name": "V2", "intention": "New intent."})
    # Should still be 1 chunk (overview), not 2
    assert rag._collections["fred_projects"].count() == 1


def test_query_projects(rag):
    rag.index_project("chatterfix", {
        "name": "ChatterFix CMMS",
        "intention": "Maintenance management for field technicians with voice commands.",
        "features": ["Work orders", "Asset tracking", "Voice commands"],
    })
    rag.index_project("artproof", {
        "name": "ArtProof Studio",
        "intention": "NFT certificates of authenticity for artwork on Polygon blockchain.",
        "features": ["Photo processing", "Blockchain minting"],
    })
    results = rag.query("maintenance work orders", collections=["fred_projects"])
    assert len(results) >= 1
    # ChatterFix should be more relevant than ArtProof for maintenance queries
    assert any("ChatterFix" in r["document"] for r in results)


def test_sync_projects_manifest(rag):
    count = rag.sync_projects_manifest()
    # projects.yaml has 9 projects, each with 1-4 chunks
    assert count >= 9  # at least 1 chunk per project


def test_query_for_context_includes_projects(rag):
    rag.index_project("elgringo", {
        "name": "El Gringo Platform",
        "intention": "Multi-agent AI orchestration platform.",
        "features": ["Model routing", "PR review", "Code audit"],
    })
    result = rag.query_for_context("What AI models does the platform support?")
    assert "projects" in result
    assert isinstance(result["projects"], list)


# ── full_sync ─────────────────────────────────────────────────────

def test_full_sync(rag, fresh_db):
    """Create data in SQLite, run sync, verify indexed."""
    memory_service.remember("tech", "db", "PostgreSQL")
    memory_service.remember("prefs", "editor", "VS Code")
    # "work" board is seeded by init_db(), no need to create
    task_service.create_task({"title": "Test task 1", "board_id": "work"})
    task_service.create_task({"title": "Test task 2", "board_id": "work"})

    counts = rag.full_sync()
    assert counts["memories"] == 2
    assert counts["tasks"] == 2


def test_full_sync_skips_done_tasks(rag, fresh_db):
    # "work" board is seeded by init_db()
    task_service.create_task({"title": "Done task", "board_id": "work", "status": "done"})
    counts = rag.full_sync()
    assert counts["tasks"] == 0


# ── get_stats ─────────────────────────────────────────────────────

def test_get_stats_ready(rag):
    stats = rag.get_stats()
    assert stats["ready"] is True
    assert "collections" in stats
    assert "fred_memories" in stats["collections"]


def test_get_stats_not_ready():
    uninitialized = RAGService(chroma_dir="/tmp/nonexistent_rag_test")
    stats = uninitialized.get_stats()
    assert stats["ready"] is False


# ── Graceful fallback ────────────────────────────────────────────

def test_uninitialized_index_returns_false():
    """When _ensure_initialized fails, index should return False."""
    uninit = RAGService(chroma_dir="/tmp/nonexistent_rag_test")
    # Force init failure by patching imports
    with patch.dict("sys.modules", {"sentence_transformers": None}):
        uninit._initialized = False
        assert uninit.index_memory({"id": "x", "category": "a", "key": "b", "value": "c"}) is False


def test_uninitialized_query_returns_empty():
    uninit = RAGService(chroma_dir="/tmp/nonexistent_rag_test")
    with patch.dict("sys.modules", {"sentence_transformers": None}):
        uninit._initialized = False
        assert uninit.query("test") == []


def test_uninitialized_query_for_context_returns_empty():
    uninit = RAGService(chroma_dir="/tmp/nonexistent_rag_test")
    with patch.dict("sys.modules", {"sentence_transformers": None}):
        uninit._initialized = False
        result = uninit.query_for_context("test")
        assert result == {"memories": [], "tasks": [], "service_results": [], "projects": []}


def test_uninitialized_delete_returns_false():
    uninit = RAGService(chroma_dir="/tmp/nonexistent_rag_test")
    with patch.dict("sys.modules", {"sentence_transformers": None}):
        uninit._initialized = False
        assert uninit.delete_memory("x") is False


# ── start_background_sync ────────────────────────────────────────

def test_start_background_sync(rag, fresh_db):
    """Smoke test — thread completes without error."""
    memory_service.remember("sync", "test", "background")
    t = rag_mod.start_background_sync()
    t.join(timeout=10)
    assert not t.is_alive()


# ── get_rag singleton ────────────────────────────────────────────

def test_get_rag_returns_same_instance():
    _set_rag(None)
    r1 = get_rag()
    r2 = get_rag()
    assert r1 is r2
    _set_rag(None)
