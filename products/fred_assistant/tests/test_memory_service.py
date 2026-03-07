"""Tests for memory_service — persistent memory system."""

from products.fred_assistant.services import memory_service


# ── remember / get ────────────────────────────────────────────────

def test_remember_creates_memory():
    mem = memory_service.remember("preferences", "editor", "VS Code")
    assert mem["category"] == "preferences"
    assert mem["key"] == "editor"
    assert mem["value"] == "VS Code"
    assert mem["id"]


def test_remember_with_context_and_importance():
    mem = memory_service.remember("tech", "language", "Python", context="Primary language", importance=9)
    assert mem["context"] == "Primary language"
    assert mem["importance"] == 9


def test_remember_upserts_on_same_category_key():
    mem1 = memory_service.remember("prefs", "theme", "dark")
    mem2 = memory_service.remember("prefs", "theme", "light")
    assert mem1["id"] == mem2["id"]
    assert mem2["value"] == "light"


def test_get_memory():
    mem = memory_service.remember("test", "key1", "value1")
    fetched = memory_service.get_memory(mem["id"])
    assert fetched["value"] == "value1"


def test_get_memory_not_found():
    assert memory_service.get_memory("nonexistent") is None


# ── forget ────────────────────────────────────────────────────────

def test_forget():
    mem = memory_service.remember("tmp", "delete_me", "gone")
    memory_service.forget(mem["id"])
    assert memory_service.get_memory(mem["id"]) is None


# ── listing + filtering ──────────────────────────────────────────

def test_list_memories_empty():
    assert memory_service.list_memories() == []


def test_list_memories_returns_all():
    memory_service.remember("cat1", "k1", "v1")
    memory_service.remember("cat2", "k2", "v2")
    assert len(memory_service.list_memories()) == 2


def test_list_memories_filter_by_category():
    memory_service.remember("work", "project", "ElGringo")
    memory_service.remember("personal", "pet", "dog")
    work = memory_service.list_memories(category="work")
    assert len(work) == 1
    assert work[0]["category"] == "work"


# ── search ────────────────────────────────────────────────────────

def test_search_memories_by_value():
    memory_service.remember("tech", "db", "PostgreSQL is great")
    results = memory_service.search_memories("PostgreSQL")
    assert len(results) >= 1


def test_search_memories_by_key():
    memory_service.remember("tech", "favorite_editor", "vim")
    results = memory_service.search_memories("favorite_editor")
    assert len(results) >= 1


def test_search_memories_by_context():
    memory_service.remember("notes", "meeting", "discussed roadmap", context="Q1 planning session")
    results = memory_service.search_memories("Q1 planning")
    assert len(results) >= 1


def test_search_memories_no_match():
    memory_service.remember("test", "key", "value")
    results = memory_service.search_memories("zzz_no_match_zzz")
    assert results == []


def test_search_memories_respects_limit():
    for i in range(5):
        memory_service.remember("bulk", f"key_{i}", f"bulk value {i}")
    results = memory_service.search_memories("bulk", limit=2)
    assert len(results) == 2


# ── context for chat ─────────────────────────────────────────────

def test_get_context_for_chat_empty():
    assert memory_service.get_context_for_chat() == ""


def test_get_context_for_chat_with_memories():
    memory_service.remember("preferences", "timezone", "PST")
    ctx = memory_service.get_context_for_chat()
    assert "timezone" in ctx
    assert "PST" in ctx


# ── categories ────────────────────────────────────────────────────

def test_get_categories_empty():
    assert memory_service.get_categories() == []


def test_get_categories():
    memory_service.remember("work", "project", "ElGringo")
    memory_service.remember("personal", "pet", "dog")
    cats = memory_service.get_categories()
    assert "work" in cats
    assert "personal" in cats
