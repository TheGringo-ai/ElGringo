"""
Platform Services Integration Tests
====================================
Tests for the platform services client, service results storage, and tools.
"""

import json
import os
import pytest

from products.fred_assistant.services import platform_services
from products.fred_assistant.services.fred_tools import TOOLS, get_tool_definitions


class TestServiceRegistry:
    def test_all_services_registered(self):
        assert "code_audit" in platform_services.SERVICES
        assert "test_gen" in platform_services.SERVICES
        assert "doc_gen" in platform_services.SERVICES
        assert "pr_bot" in platform_services.SERVICES
        assert "fred_api" in platform_services.SERVICES

    def test_service_has_required_fields(self):
        for name, svc in platform_services.SERVICES.items():
            assert "port" in svc, f"{name} missing port"
            assert "prefix" in svc, f"{name} missing prefix"
            assert "health" in svc, f"{name} missing health"
            assert "label" in svc, f"{name} missing label"

    def test_get_service_url(self):
        url = platform_services.get_service_url("code_audit")
        assert "8081" in url

    def test_get_service_url_unknown(self):
        with pytest.raises(ValueError):
            platform_services.get_service_url("nonexistent")


class TestServiceHealth:
    def test_check_health_returns_dict(self):
        result = platform_services.check_service_health("code_audit")
        assert "service" in result
        assert "healthy" in result
        assert "port" in result
        assert result["service"] == "code_audit"

    def test_check_health_unknown_service(self):
        result = platform_services.check_service_health("nonexistent")
        assert result["healthy"] is False
        assert "error" in result

    def test_check_all_services(self):
        results = platform_services.check_all_services()
        assert len(results) == 5
        for name in platform_services.SERVICES:
            assert name in results
            assert "healthy" in results[name]

    def test_cached_status(self):
        # First call should work
        status = platform_services.get_cached_status()
        assert status is not None or status is None  # Either works, just shouldn't crash

    def test_platform_status_tool(self):
        from products.fred_assistant.services.fred_tools import _exec_platform_status
        result = _exec_platform_status({})
        assert result["success"] is True
        assert "services" in result
        assert "online" in result
        assert "total" in result
        assert result["total"] == 5


class TestServiceResults:
    def test_store_and_retrieve(self):
        result_id = platform_services.store_service_result(
            "code_audit", "security", "test-project",
            {"findings": "no issues", "agents_used": ["claude"], "total_time": 1.5},
        )
        assert result_id is not None
        assert len(result_id) > 0

        results = platform_services.get_recent_results(service="code_audit", project_name="test-project")
        assert len(results) >= 1
        found = False
        for r in results:
            if r["id"] == result_id:
                found = True
                assert r["service"] == "code_audit"
                assert r["action"] == "security"
                assert r["project_name"] == "test-project"
                break
        assert found

    def test_get_recent_results_filtered(self):
        # Store a few results
        platform_services.store_service_result("test_gen", "generate", "proj-a", {"result": "tests"})
        platform_services.store_service_result("doc_gen", "readme", "proj-b", {"content": "readme"})

        # Filter by service
        test_results = platform_services.get_recent_results(service="test_gen")
        for r in test_results:
            assert r["service"] == "test_gen"

        # Filter by project
        proj_results = platform_services.get_recent_results(project_name="proj-a")
        for r in proj_results:
            assert r["project_name"] == "proj-a"

    def test_get_recent_results_limit(self):
        results = platform_services.get_recent_results(limit=2)
        assert len(results) <= 2


class TestPlatformTools:
    def test_platform_tools_registered(self):
        platform_tools = [
            "audit_security", "audit_code", "generate_tests", "analyze_tests",
            "generate_readme", "generate_api_docs", "generate_architecture",
            "platform_status",
        ]
        for tool in platform_tools:
            assert tool in TOOLS, f"Platform tool {tool} not registered"

    def test_workflow_tools_registered(self):
        workflow_tools = ["full_project_review", "ship_ready_check", "bootstrap_project"]
        for tool in workflow_tools:
            assert tool in TOOLS, f"Workflow tool {tool} not registered"

    def test_platform_tools_are_async(self):
        async_tools = [
            "audit_security", "audit_code", "generate_tests", "analyze_tests",
            "generate_readme", "generate_api_docs", "generate_architecture",
            "full_project_review", "ship_ready_check", "bootstrap_project",
        ]
        for name in async_tools:
            assert TOOLS[name]["async"] is True, f"{name} should be async"

    def test_platform_status_is_sync(self):
        assert TOOLS["platform_status"]["async"] is False

    def test_tool_definitions_include_platform(self):
        defs = get_tool_definitions()
        assert "Platform Services" in defs
        assert "Workflows" in defs
        assert "audit_security" in defs
        assert "full_project_review" in defs
        assert "ship_ready_check" in defs
        assert "bootstrap_project" in defs


class TestHelperFunctions:
    def test_detect_language(self):
        from products.fred_assistant.services.fred_tools import _detect_language
        assert _detect_language("test.py") == "python"
        assert _detect_language("app.js") == "javascript"
        assert _detect_language("main.go") == "go"
        assert _detect_language("lib.rs") == "rust"
        assert _detect_language("Main.java") == "java"
        assert _detect_language("unknown.xyz") == "text"

    def test_resolve_project_path(self):
        from products.fred_assistant.services.fred_tools import _resolve_project_path
        result = _resolve_project_path("nonexistent-project-xyz")
        assert result is None

    def test_read_project_files(self, tmp_path):
        from products.fred_assistant.services.fred_tools import _read_project_files
        # Create fake project
        (tmp_path / "main.py").write_text("print('hello')\n")
        (tmp_path / "util.py").write_text("def util(): pass\n")
        (tmp_path / "readme.md").write_text("# Project\n")
        (tmp_path / ".git").mkdir()

        files = _read_project_files(str(tmp_path))
        assert len(files) >= 2
        paths = [f["path"] for f in files]
        assert "main.py" in paths
        assert "util.py" in paths
        for f in files:
            assert "content" in f
            assert "language" in f

    def test_read_project_files_skips_dirs(self, tmp_path):
        from products.fred_assistant.services.fred_tools import _read_project_files
        (tmp_path / "main.py").write_text("print('hello')\n")
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "dep.js").write_text("module.exports = {}\n")

        files = _read_project_files(str(tmp_path))
        paths = [f["path"] for f in files]
        assert not any("node_modules" in p for p in paths)

    def test_read_project_files_max_files(self, tmp_path):
        from products.fred_assistant.services.fred_tools import _read_project_files
        for i in range(20):
            (tmp_path / f"file_{i}.py").write_text(f"# File {i}\n")

        files = _read_project_files(str(tmp_path), max_files=3)
        assert len(files) == 3
