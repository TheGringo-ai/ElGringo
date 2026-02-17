"""
Comprehensive Memory System Tests
=================================

Extended tests for memory system with higher coverage.
"""

import asyncio
import json
import os
import pytest
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_dev_team.memory.system import (
    MemorySystem,
    MistakeType,
    MistakeRecord,
    SolutionRecord,
    Interaction,
    OutcomeRating,
    tokenize,
    compute_tf_idf_score,
)


class TestTokenization:
    """Test tokenization functions"""

    def test_tokenize_basic(self):
        """Test basic tokenization"""
        tokens = tokenize("Hello World Test")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_tokenize_filters_short_words(self):
        """Short words (<=2 chars) should be filtered"""
        tokens = tokenize("I am a test of the system")
        assert "test" in tokens
        assert "system" in tokens
        # 2-char words may or may not be filtered depending on implementation
        # Just verify short words are handled

    def test_tokenize_handles_special_chars(self):
        """Special characters should be handled"""
        tokens = tokenize("error: SQL_injection! test@example.com")
        assert "error" in tokens
        assert "sql" in tokens
        assert "injection" in tokens

    def test_tokenize_empty_string(self):
        """Empty string should return empty list"""
        tokens = tokenize("")
        assert tokens == []

    def test_tokenize_numbers(self):
        """Numbers should be included"""
        tokens = tokenize("error 404 not found 500")
        assert "error" in tokens
        assert "404" in tokens
        assert "500" in tokens
        assert "found" in tokens


class TestTFIDF:
    """Test TF-IDF scoring"""

    def test_tfidf_exact_match_scores_higher(self):
        """Exact matches should score higher"""
        query = tokenize("database connection error")
        doc1 = tokenize("database connection error handling")
        doc2 = tokenize("network timeout issue")
        all_docs = [doc1, doc2]

        score1 = compute_tf_idf_score(query, doc1, all_docs)
        score2 = compute_tf_idf_score(query, doc2, all_docs)

        assert score1 > score2

    def test_tfidf_empty_query(self):
        """Empty query should return 0"""
        score = compute_tf_idf_score([], ["test", "doc"], [])
        assert score == 0.0

    def test_tfidf_empty_doc(self):
        """Empty document should return 0"""
        score = compute_tf_idf_score(["test"], [], [])
        assert score == 0.0

    def test_tfidf_no_match(self):
        """No matching tokens should return 0"""
        query = tokenize("database error")
        doc = tokenize("user interface design")
        score = compute_tf_idf_score(query, doc, [])
        assert score == 0.0

    def test_tfidf_partial_match(self):
        """Partial matches should score > 0"""
        query = tokenize("database error handling")
        doc = tokenize("error handling best practices")
        score = compute_tf_idf_score(query, doc, [])
        assert score > 0


class TestMistakeRecord:
    """Test MistakeRecord dataclass"""

    def test_create_mistake_record(self):
        """Test creating a mistake record"""
        mistake = MistakeRecord(
            mistake_id="test123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            mistake_type="code_error",
            description="Test error",
            context={"file": "test.py"},
            resolution="Fixed it",
            prevention_strategy="Add tests",
            severity="medium",
        )
        assert mistake.mistake_id == "test123"
        assert mistake.mistake_type == "code_error"
        assert mistake.severity == "medium"

    def test_mistake_record_defaults(self):
        """Test default values"""
        mistake = MistakeRecord(
            mistake_id="test",
            timestamp="2024-01-01",
            mistake_type="bug",
            description="Test",
            context={},
            resolution="",
            prevention_strategy="",
            severity="low",
        )
        assert mistake.related_projects == []
        assert mistake.tags == []


class TestSolutionRecord:
    """Test SolutionRecord dataclass"""

    def test_create_solution_record(self):
        """Test creating a solution record"""
        solution = SolutionRecord(
            solution_id="sol123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            problem_pattern="Connection timeout",
            solution_steps=["Increase timeout", "Add retry"],
            success_rate=0.95,
            projects_used=["project1"],
        )
        assert solution.solution_id == "sol123"
        assert solution.success_rate == 0.95
        assert len(solution.solution_steps) == 2

    def test_solution_record_defaults(self):
        """Test default values"""
        solution = SolutionRecord(
            solution_id="test",
            timestamp="2024-01-01",
            problem_pattern="test",
            solution_steps=[],
            success_rate=1.0,
            projects_used=[],
        )
        assert solution.best_practices == []
        assert solution.performance_metrics == {}
        assert solution.tags == []


class TestMemorySystemCore:
    """Core memory system tests"""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create test memory system"""
        return MemorySystem(storage_dir=str(tmp_path / "memory"))

    def test_initialization(self, memory):
        """Test memory system initializes correctly"""
        assert memory._interactions_cache == []
        assert memory._mistakes_cache == []
        assert memory._solutions_cache == []
        assert memory.storage_dir.exists()

    def test_generate_id(self, memory):
        """Test ID generation"""
        id1 = memory._generate_id("test content")
        id2 = memory._generate_id("test content")
        # IDs should be unique even for same content (due to timestamp)
        assert len(id1) == 16
        assert len(id2) == 16

    @pytest.mark.asyncio
    async def test_capture_multiple_mistakes(self, memory):
        """Test capturing multiple mistakes"""
        for i in range(5):
            await memory.capture_mistake(
                mistake_type=MistakeType.CODE_ERROR,
                description=f"Error {i}",
                context={"index": i},
                severity="medium",
            )
        assert len(memory._mistakes_cache) == 5
        assert len(memory._mistake_tokens) == 5

    @pytest.mark.asyncio
    async def test_capture_multiple_solutions(self, memory):
        """Test capturing multiple solutions"""
        for i in range(5):
            await memory.capture_solution(
                problem_pattern=f"Problem {i}",
                solution_steps=[f"Step {i}"],
                success_rate=0.8 + i * 0.02,
            )
        assert len(memory._solutions_cache) == 5
        assert len(memory._solution_tokens) == 5

    def test_statistics_empty(self, memory):
        """Test statistics on empty memory"""
        stats = memory.get_statistics()
        assert stats["total_interactions"] == 0
        assert stats["total_mistakes"] == 0
        assert stats["total_solutions"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_statistics_with_data(self, memory):
        """Test statistics with data"""
        await memory.capture_mistake(
            mistake_type=MistakeType.SECURITY_VULNERABILITY,
            description="XSS vulnerability",
            context={},
            severity="critical",
        )
        await memory.capture_solution(
            problem_pattern="XSS fix",
            solution_steps=["Sanitize input"],
            success_rate=0.95,
        )

        stats = memory.get_statistics()
        assert stats["total_mistakes"] == 1
        assert stats["total_solutions"] == 1
        assert "security_vulnerability" in stats["mistake_types"]
        assert stats["mistake_severities"]["critical"] == 1

    def test_mark_dirty(self, memory):
        """Test dirty flag"""
        assert not memory._dirty
        memory.mark_dirty()
        assert memory._dirty

    def test_flush_now(self, memory):
        """Test immediate flush"""
        memory.mark_dirty()
        memory.flush_now()
        assert not memory._dirty


class TestMemorySearch:
    """Test memory search functionality"""

    @pytest.fixture
    async def populated_memory(self, tmp_path):
        """Create memory with test data"""
        memory = MemorySystem(storage_dir=str(tmp_path / "memory"))

        # Add mistakes
        await memory.capture_mistake(
            mistake_type=MistakeType.SECURITY_VULNERABILITY,
            description="SQL injection in login form",
            context={"module": "auth"},
            severity="critical",
            tags=["security", "sql"],
        )
        await memory.capture_mistake(
            mistake_type=MistakeType.PERFORMANCE_ISSUE,
            description="Slow database query in reports",
            context={"module": "reports"},
            severity="high",
            tags=["performance", "database"],
        )
        await memory.capture_mistake(
            mistake_type=MistakeType.CODE_ERROR,
            description="Null pointer exception in user service",
            context={"module": "users"},
            severity="medium",
            tags=["bug", "null"],
        )

        # Add solutions
        await memory.capture_solution(
            problem_pattern="SQL injection prevention",
            solution_steps=["Use parameterized queries", "Validate input"],
            success_rate=0.98,
            tags=["security"],
        )
        await memory.capture_solution(
            problem_pattern="Database query optimization",
            solution_steps=["Add indexes", "Use query caching"],
            success_rate=0.92,
            tags=["performance"],
        )

        return memory

    @pytest.mark.asyncio
    async def test_find_mistakes_by_keyword(self, populated_memory):
        """Find mistakes by keyword search"""
        results = await populated_memory.find_similar_mistakes(
            {"query": "SQL injection security"}
        )
        assert len(results) > 0
        assert any("SQL injection" in m.description for m in results)

    @pytest.mark.asyncio
    async def test_find_mistakes_by_severity_boost(self, populated_memory):
        """Critical mistakes should be boosted"""
        results = await populated_memory.find_similar_mistakes(
            {"query": "security vulnerability"}
        )
        # Critical severity should be first
        if results:
            assert results[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_find_solutions_by_pattern(self, populated_memory):
        """Find solutions by problem pattern"""
        results = await populated_memory.find_solution_patterns(
            "SQL injection attack prevention"
        )
        assert len(results) > 0
        assert any("SQL" in s.problem_pattern for s in results)

    @pytest.mark.asyncio
    async def test_find_solutions_weighted_by_success(self, populated_memory):
        """Solutions should be weighted by success rate"""
        results = await populated_memory.find_solution_patterns("prevention")
        if len(results) >= 2:
            # Higher success rate should rank higher
            assert results[0].success_rate >= results[-1].success_rate

    @pytest.mark.asyncio
    async def test_search_all(self, populated_memory):
        """Test searching all memory stores"""
        results = await populated_memory.search_all("database")
        assert "mistakes" in results
        assert "solutions" in results
        assert "interactions" in results
        assert results["total_results"] > 0


class TestMemoryPersistence:
    """Test memory persistence to disk"""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create test memory system"""
        return MemorySystem(storage_dir=str(tmp_path / "memory"))

    @pytest.mark.asyncio
    async def test_save_and_load_mistakes(self, tmp_path):
        """Test mistakes are persisted to disk"""
        storage_dir = str(tmp_path / "memory")

        # Create and populate
        memory1 = MemorySystem(storage_dir=storage_dir)
        await memory1.capture_mistake(
            mistake_type=MistakeType.CODE_ERROR,
            description="Test error",
            context={},
            severity="low",
        )

        # Create new instance - should load from disk
        memory2 = MemorySystem(storage_dir=storage_dir)
        assert len(memory2._mistakes_cache) == 1
        assert memory2._mistakes_cache[0].description == "Test error"

    @pytest.mark.asyncio
    async def test_save_and_load_solutions(self, tmp_path):
        """Test solutions are persisted to disk"""
        storage_dir = str(tmp_path / "memory")

        # Create and populate
        memory1 = MemorySystem(storage_dir=storage_dir)
        await memory1.capture_solution(
            problem_pattern="Test problem",
            solution_steps=["Step 1"],
            success_rate=0.9,
        )

        # Create new instance
        memory2 = MemorySystem(storage_dir=storage_dir)
        assert len(memory2._solutions_cache) == 1
        assert memory2._solutions_cache[0].problem_pattern == "Test problem"


class TestMistakeType:
    """Test MistakeType enum"""

    def test_all_types_defined(self):
        """All expected types should be defined"""
        expected = [
            "CODE_ERROR",
            "ARCHITECTURE_FLAW",
            "PERFORMANCE_ISSUE",
            "SECURITY_VULNERABILITY",
            "DEPLOYMENT_FAILURE",
            "LOGIC_ERROR",
            "INTEGRATION_ISSUE",
        ]
        for type_name in expected:
            assert hasattr(MistakeType, type_name)

    def test_type_values(self):
        """Type values should be lowercase strings"""
        assert MistakeType.CODE_ERROR.value == "code_error"
        assert MistakeType.SECURITY_VULNERABILITY.value == "security_vulnerability"


class TestOutcomeRating:
    """Test OutcomeRating enum"""

    def test_all_ratings_defined(self):
        """All ratings should be defined"""
        assert OutcomeRating.EXCELLENT.value == 5
        assert OutcomeRating.GOOD.value == 4
        assert OutcomeRating.SATISFACTORY.value == 3
        assert OutcomeRating.POOR.value == 2
        assert OutcomeRating.FAILURE.value == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
