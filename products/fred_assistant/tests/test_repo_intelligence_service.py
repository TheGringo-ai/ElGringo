"""
Repo Intelligence Service Tests
================================
Tests for analysis engine, health scoring, and task generation.
"""

import os
import json
import pytest
import tempfile
import shutil

from products.fred_assistant.services import repo_intelligence_service as ris


@pytest.fixture
def fake_project(tmp_path):
    """Create a minimal fake project for testing."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create a git-like structure
    (project_dir / ".git").mkdir()
    (project_dir / "README.md").write_text("# Test Project")
    (project_dir / "requirements.txt").write_text("fastapi\npydantic\n")
    (project_dir / "src").mkdir()
    (project_dir / "src" / "main.py").write_text("def main():\n    pass\n")
    (project_dir / "tests").mkdir()
    (project_dir / "tests" / "test_main.py").write_text("def test_main():\n    assert True\n")
    (project_dir / ".github").mkdir()
    (project_dir / ".github" / "workflows").mkdir()
    (project_dir / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")

    return project_dir


@pytest.fixture
def bare_project(tmp_path):
    """Create a bare project with no tests, no CI, no README."""
    project_dir = tmp_path / "bare-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()
    (project_dir / "main.py").write_text("# TODO: implement this\n# FIXME: broken\nprint('hello')\n")
    return project_dir


class TestEmptyFindings:
    def test_returns_all_categories(self):
        findings = ris._empty_findings()
        assert "missing_tests" in findings
        assert "missing_ci" in findings
        assert "todo_fixme" in findings
        assert "large_files" in findings
        assert "security_patterns" in findings
        assert "dependency_issues" in findings
        assert "code_smells" in findings
        assert "missing_docs" in findings
        assert "dead_code_hints" in findings

    def test_default_severities(self):
        findings = ris._empty_findings()
        assert findings["missing_tests"]["severity"] == "high"
        assert findings["security_patterns"]["severity"] == "high"
        assert findings["missing_ci"]["severity"] == "medium"
        assert findings["todo_fixme"]["severity"] == "low"


class TestChecks:
    def test_check_ci_found(self, fake_project):
        entries = set(os.listdir(fake_project))
        result = ris._check_ci(str(fake_project), entries)
        assert result["detected"] is True
        assert ".github/workflows" in result["details"]

    def test_check_ci_not_found(self, bare_project):
        entries = set(os.listdir(bare_project))
        result = ris._check_ci(str(bare_project), entries)
        assert result["detected"] is False

    def test_check_tests_found(self, fake_project):
        entries = set(os.listdir(fake_project))
        result = ris._check_tests(str(fake_project), entries)
        assert result["count"] == 0  # count=0 means tests EXIST
        assert "tests" in result["details"]

    def test_check_tests_not_found(self, bare_project):
        entries = set(os.listdir(bare_project))
        result = ris._check_tests(str(bare_project), entries)
        assert result["count"] == 1  # count=1 means no tests

    def test_check_docs_found(self, fake_project):
        entries = set(os.listdir(fake_project))
        result = ris._check_docs(str(fake_project), entries)
        assert result["detected"] is True

    def test_check_docs_not_found(self, bare_project):
        entries = set(os.listdir(bare_project))
        result = ris._check_docs(str(bare_project), entries)
        assert result["detected"] is False

    def test_check_large_files(self, fake_project):
        result = ris._check_large_files(str(fake_project))
        assert result["count"] == 0  # no large files in our test project

    def test_check_large_files_detects_big_file(self, fake_project):
        big_file = fake_project / "big.dat"
        big_file.write_bytes(b"x" * 2_000_000)
        result = ris._check_large_files(str(fake_project))
        assert result["count"] == 1
        assert result["items"][0]["size_mb"] == 2.0


class TestHealthScore:
    def test_perfect_project(self):
        findings = ris._empty_findings()
        findings["missing_ci"]["detected"] = True
        findings["missing_docs"]["detected"] = True
        findings["missing_tests"]["count"] = 0
        git_health = {"uncommitted_changes": 0, "days_since_last_commit": 1}
        score = ris._compute_health_score(findings, git_health, "quick")
        assert score == 100

    def test_bare_project_score(self):
        findings = ris._empty_findings()
        findings["missing_tests"]["count"] = 1
        findings["missing_ci"]["detected"] = False
        findings["missing_docs"]["detected"] = False
        git_health = {"uncommitted_changes": 0, "days_since_last_commit": 1}
        score = ris._compute_health_score(findings, git_health, "quick")
        assert score == 50  # -25 (tests) -15 (CI) -10 (docs) = 50

    def test_security_deduction(self):
        findings = ris._empty_findings()
        findings["missing_ci"]["detected"] = True
        findings["missing_docs"]["detected"] = True
        findings["security_patterns"]["count"] = 3
        git_health = {"uncommitted_changes": 0, "days_since_last_commit": 1}
        score = ris._compute_health_score(findings, git_health, "quick")
        assert score == 80  # -20 for security

    def test_stale_repo_deduction(self):
        findings = ris._empty_findings()
        findings["missing_ci"]["detected"] = True
        findings["missing_docs"]["detected"] = True
        git_health = {"uncommitted_changes": 0, "days_since_last_commit": 60}
        score = ris._compute_health_score(findings, git_health, "quick")
        assert score == 90  # -10 for stale

    def test_score_floor_at_zero(self):
        findings = ris._empty_findings()
        findings["missing_tests"]["count"] = 1
        findings["missing_ci"]["detected"] = False
        findings["missing_docs"]["detected"] = False
        findings["security_patterns"]["count"] = 5
        findings["todo_fixme"]["count"] = 50
        findings["large_files"]["count"] = 10
        git_health = {"uncommitted_changes": 30, "days_since_last_commit": 90}
        score = ris._compute_health_score(findings, git_health, "quick")
        assert score == 0


class TestGenerateSummary:
    def test_summary_includes_score(self):
        findings = ris._empty_findings()
        findings["missing_ci"]["detected"] = True
        findings["missing_docs"]["detected"] = True
        summary = ris._generate_summary(findings, 85, ["Python", "React"], {})
        assert "85/100" in summary
        assert "Python" in summary

    def test_summary_lists_issues(self):
        findings = ris._empty_findings()
        findings["missing_tests"]["count"] = 1
        findings["missing_ci"]["detected"] = False
        findings["missing_docs"]["detected"] = False
        summary = ris._generate_summary(findings, 50, [], {})
        assert "no tests" in summary
        assert "no CI/CD" in summary
        assert "no README" in summary


class TestAnalyzeRepo:
    def test_analyze_nonexistent_project(self):
        result = ris.analyze_repo("nonexistent-project-xyz")
        assert "error" in result

    def test_analyze_real_project(self, fake_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(fake_project.parent))
        result = ris.analyze_repo("test-project", depth="quick")
        assert "error" not in result
        assert result["health_score"] >= 0
        assert result["health_score"] <= 100
        assert "findings" in result
        assert result["project_name"] == "test-project"
        assert result["depth"] == "quick"

    def test_analyze_saves_to_db(self, fake_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(fake_project.parent))
        result = ris.analyze_repo("test-project")
        analysis_id = result["id"]
        stored = ris.get_analysis(analysis_id)
        assert stored is not None
        assert stored["project_name"] == "test-project"
        assert stored["health_score"] == result["health_score"]


class TestGetAnalysis:
    def test_get_nonexistent(self):
        result = ris.get_analysis("nonexistent-id")
        assert result is None

    def test_get_latest_nonexistent(self):
        result = ris.get_latest_analysis("no-such-project")
        assert result is None


class TestListAnalyses:
    def test_list_empty(self):
        result = ris.list_analyses()
        assert isinstance(result, list)

    def test_list_after_analyze(self, fake_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(fake_project.parent))
        ris.analyze_repo("test-project")
        result = ris.list_analyses(project_name="test-project")
        assert len(result) >= 1
        assert result[0]["project_name"] == "test-project"


class TestGenerateTasks:
    def test_generate_from_nonexistent(self):
        result = ris.generate_tasks_from_analysis("nope")
        assert result == []

    def test_generate_tasks_from_bare_project(self, bare_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(bare_project.parent))
        analysis = ris.analyze_repo("bare-project")
        tasks = ris.generate_tasks_from_analysis(analysis["id"])
        # Bare project should generate tasks for missing tests, CI, docs
        task_titles = [t["title"] for t in tasks]
        assert any("test" in t.lower() for t in task_titles)
        assert any("ci" in t.lower() or "pipeline" in t.lower() for t in task_titles)
        assert any("readme" in t.lower() or "doc" in t.lower() for t in task_titles)

    def test_tasks_have_priority_and_board(self, bare_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(bare_project.parent))
        analysis = ris.analyze_repo("bare-project")
        tasks = ris.generate_tasks_from_analysis(analysis["id"])
        for t in tasks:
            assert "priority" in t
            assert "board" in t
            assert t["priority"] in (1, 2, 3)


class TestReviewRepo:
    def test_review_nonexistent(self):
        result = ris.review_repo("nonexistent-xyz")
        assert "error" in result

    def test_review_returns_structured_data(self, fake_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(fake_project.parent))
        result = ris.review_repo("test-project")
        assert "error" not in result
        assert "health_score" in result
        assert "todo_items" in result
        assert "action_items" in result
        assert "todo_count" in result
        assert "action_count" in result
        assert isinstance(result["todo_items"], list)
        assert isinstance(result["action_items"], list)

    def test_review_bare_project_has_action_items(self, bare_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(bare_project.parent))
        result = ris.review_repo("bare-project")
        assert result["action_count"] > 0
        # Bare project should flag missing tests, CI, docs
        categories = [a["category"] for a in result["action_items"]]
        assert "testing" in categories
        assert "devops" in categories
        assert "documentation" in categories

    def test_review_action_items_sorted_by_severity(self, bare_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(bare_project.parent))
        result = ris.review_repo("bare-project")
        actions = result["action_items"]
        severity_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(actions) - 1):
            assert severity_order[actions[i]["severity"]] <= severity_order[actions[i + 1]["severity"]]

    def test_review_todo_items_parsed(self, bare_project, monkeypatch):
        monkeypatch.setattr(ris, "PROJECTS_DIR", str(bare_project.parent))
        result = ris.review_repo("bare-project")
        # bare_project has "# TODO: implement this" and "# FIXME: broken"
        assert result["todo_count"] >= 1
        types = [t["type"] for t in result["todo_items"]]
        assert "TODO" in types or "FIXME" in types
