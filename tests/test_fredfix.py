"""
FredFix Tests
=============

Comprehensive tests for the autonomous code fixer.
"""

import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elgringo.workflows.fredfix import (
    FredFix,
    FixResult,
    Issue,
    LANGUAGE_CONFIG,
    create_fredfix,
)


class TestLanguageConfig:
    """Test language configuration"""

    def test_python_config(self):
        """Python should be configured"""
        assert "python" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["python"]
        assert ".py" in config["extensions"]
        assert "__pycache__" in config["exclude_dirs"]

    def test_javascript_config(self):
        """JavaScript should be configured"""
        assert "javascript" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["javascript"]
        assert ".js" in config["extensions"]
        assert "node_modules" in config["exclude_dirs"]

    def test_typescript_config(self):
        """TypeScript should be configured"""
        assert "typescript" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["typescript"]
        assert ".ts" in config["extensions"]
        assert ".tsx" in config["extensions"]

    def test_go_config(self):
        """Go should be configured"""
        assert "go" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["go"]
        assert ".go" in config["extensions"]
        assert "vendor" in config["exclude_dirs"]

    def test_rust_config(self):
        """Rust should be configured"""
        assert "rust" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["rust"]
        assert ".rs" in config["extensions"]
        assert "target" in config["exclude_dirs"]

    def test_java_config(self):
        """Java should be configured"""
        assert "java" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["java"]
        assert ".java" in config["extensions"]

    def test_cpp_config(self):
        """C++ should be configured"""
        assert "cpp" in LANGUAGE_CONFIG
        config = LANGUAGE_CONFIG["cpp"]
        assert ".cpp" in config["extensions"]
        assert ".h" in config["extensions"]

    def test_all_configs_have_required_fields(self):
        """All configs should have required fields"""
        for lang, config in LANGUAGE_CONFIG.items():
            assert "extensions" in config, f"{lang} missing extensions"
            assert "exclude_dirs" in config, f"{lang} missing exclude_dirs"
            assert "comment_prefix" in config, f"{lang} missing comment_prefix"


class TestIssue:
    """Test Issue dataclass"""

    def test_create_issue(self):
        """Test creating an issue"""
        issue = Issue(
            file_path="test.py",
            line_number=10,
            issue_type="bug",
            severity="high",
            description="Null pointer",
            suggested_fix="Add null check",
            confidence=0.9,
        )
        assert issue.file_path == "test.py"
        assert issue.line_number == 10
        assert issue.severity == "high"

    def test_issue_optional_line(self):
        """Line number can be None"""
        issue = Issue(
            file_path="test.py",
            line_number=None,
            issue_type="style",
            severity="low",
            description="Missing docstring",
            suggested_fix="Add docstring",
            confidence=0.7,
        )
        assert issue.line_number is None


class TestFixResult:
    """Test FixResult dataclass"""

    def test_create_fix_result(self):
        """Test creating a fix result"""
        result = FixResult(
            fix_id="abc123",
            success=True,
            issues_found=[{"file": "test.py"}],
            fixes_applied=[{"fix": "test"}],
            fixes_skipped=[],
            total_time=5.5,
            confidence=0.85,
            summary="Found 1 issue, applied 1 fix",
        )
        assert result.success
        assert result.fix_id == "abc123"
        assert len(result.issues_found) == 1


class TestFredFix:
    """Test FredFix class"""

    @pytest.fixture
    def fixer(self, tmp_path):
        """Create FredFix without team"""
        from elgringo.memory import MemorySystem
        memory = MemorySystem(storage_dir=str(tmp_path / "memory"))
        return FredFix(memory=memory, safe_mode=True)

    def test_initialization(self, fixer):
        """Test FredFix initializes correctly"""
        assert fixer.AGENT_NAME == "FredFix"
        assert fixer.safe_mode is True
        assert fixer._fix_count == 0

    def test_get_stats(self, fixer):
        """Test getting statistics"""
        stats = fixer.get_stats()
        assert stats["agent_name"] == "FredFix"
        assert "supported_languages" in stats
        assert len(stats["supported_languages"]) >= 8

    def test_memory_log(self, fixer):
        """Test memory logging"""
        # Should not raise
        fixer.memory_log("Test message")


class TestLanguageDetection:
    """Test language detection"""

    @pytest.fixture
    def fixer(self):
        return FredFix()

    def test_detect_python(self, fixer):
        """Detect Python files"""
        assert fixer._detect_language(Path("test.py")) == "python"

    def test_detect_javascript(self, fixer):
        """Detect JavaScript files"""
        assert fixer._detect_language(Path("test.js")) == "javascript"
        assert fixer._detect_language(Path("component.jsx")) == "javascript"

    def test_detect_typescript(self, fixer):
        """Detect TypeScript files"""
        assert fixer._detect_language(Path("test.ts")) == "typescript"
        assert fixer._detect_language(Path("component.tsx")) == "typescript"

    def test_detect_go(self, fixer):
        """Detect Go files"""
        assert fixer._detect_language(Path("main.go")) == "go"

    def test_detect_rust(self, fixer):
        """Detect Rust files"""
        assert fixer._detect_language(Path("lib.rs")) == "rust"

    def test_detect_java(self, fixer):
        """Detect Java files"""
        assert fixer._detect_language(Path("Main.java")) == "java"

    def test_detect_cpp(self, fixer):
        """Detect C++ files"""
        assert fixer._detect_language(Path("main.cpp")) == "cpp"
        assert fixer._detect_language(Path("header.h")) == "cpp"

    def test_detect_unknown(self, fixer):
        """Unknown extensions return 'unknown'"""
        assert fixer._detect_language(Path("file.xyz")) == "unknown"
        assert fixer._detect_language(Path("file.abc")) == "unknown"


class TestIssueParsing:
    """Test issue parsing"""

    @pytest.fixture
    def fixer(self):
        return FredFix()

    def test_parse_json_array(self, fixer):
        """Parse JSON array format"""
        response = '''[
            {
                "file_path": "src/main.py",
                "severity": "high",
                "issue_type": "security",
                "description": "SQL injection vulnerability",
                "suggested_fix": "Use parameterized queries",
                "line_number": 42
            },
            {
                "file_path": "src/utils.py",
                "severity": "medium",
                "issue_type": "performance",
                "description": "Inefficient loop",
                "suggested_fix": "Use list comprehension"
            }
        ]'''
        issues = fixer._parse_issues(response, "/project")
        assert len(issues) == 2
        assert issues[0].file_path == "src/main.py"
        assert issues[0].severity == "high"
        assert issues[1].issue_type == "performance"

    def test_parse_json_with_markdown(self, fixer):
        """Parse JSON wrapped in markdown"""
        response = '''Here are the issues I found:

```json
[
    {
        "file_path": "app.py",
        "severity": "critical",
        "issue_type": "security",
        "description": "Hardcoded credentials"
    }
]
```

Please fix these issues.'''
        issues = fixer._parse_issues(response, "/project")
        assert len(issues) == 1
        assert issues[0].severity == "critical"

    def test_parse_text_format(self, fixer):
        """Parse text/markdown format"""
        response = '''
file_path: src/auth.py
severity: high
issue_type: security
description: Password not hashed
suggested_fix: Use bcrypt for hashing

file_path: src/api.py
severity: medium
issue_type: bug
description: Missing error handling
suggested_fix: Add try-except block
'''
        issues = fixer._parse_issues(response, "/project")
        assert len(issues) == 2
        assert issues[0].file_path == "src/auth.py"
        assert issues[1].description == "Missing error handling"

    def test_parse_alternative_field_names(self, fixer):
        """Parse with alternative field names"""
        response = '''
file: routes.py
type: bug
severity: low
issue: Deprecated function used
recommendation: Use new API
line: 25
'''
        issues = fixer._parse_issues(response, "/project")
        assert len(issues) == 1
        assert issues[0].file_path == "routes.py"
        assert issues[0].issue_type == "bug"

    def test_parse_empty_response(self, fixer):
        """Empty response should return empty list"""
        issues = fixer._parse_issues("", "/project")
        assert issues == []

    def test_parse_no_issues_found(self, fixer):
        """'No issues' response should return empty list"""
        response = "I analyzed the code and found no issues."
        issues = fixer._parse_issues(response, "/project")
        assert issues == []

    def test_parse_json_with_trailing_comma(self, fixer):
        """Handle JSON with trailing commas"""
        response = '''[
            {
                "file_path": "test.py",
                "description": "Test issue",
            },
        ]'''
        fixer._parse_issues(response, "/project")
        # Should handle gracefully (either parse or fall back to text)
        # The cleaned JSON parser should handle this


class TestIssueNormalization:
    """Test issue field normalization"""

    @pytest.fixture
    def fixer(self):
        return FredFix()

    def test_normalize_severity(self, fixer):
        """Severity should be normalized"""
        data = {"description": "Test", "severity": "HIGH"}
        issue = fixer._create_issue(data, "/project")
        assert issue.severity == "high"

    def test_default_severity(self, fixer):
        """Missing severity defaults to medium"""
        data = {"description": "Test"}
        issue = fixer._create_issue(data, "/project")
        assert issue.severity == "medium"

    def test_invalid_severity(self, fixer):
        """Invalid severity defaults to medium"""
        data = {"description": "Test", "severity": "UNKNOWN"}
        issue = fixer._create_issue(data, "/project")
        assert issue.severity == "medium"

    def test_normalize_issue_type(self, fixer):
        """Issue type should be normalized"""
        data = {"description": "Test", "issue_type": "BUG"}
        issue = fixer._create_issue(data, "/project")
        assert issue.issue_type == "bug"

    def test_security_type_detection(self, fixer):
        """Security-related types should be categorized"""
        data = {"description": "Test", "issue_type": "sql_injection_vulnerability"}
        issue = fixer._create_issue(data, "/project")
        assert issue.issue_type == "security"

    def test_performance_type_detection(self, fixer):
        """Performance-related types should be categorized"""
        data = {"description": "Test", "issue_type": "slow_query"}
        issue = fixer._create_issue(data, "/project")
        assert issue.issue_type == "performance"

    def test_confidence_parsing(self, fixer):
        """Confidence should be parsed from string"""
        data = {"description": "Test", "confidence": "0.85"}
        issue = fixer._create_issue(data, "/project")
        assert issue.confidence == pytest.approx(0.85, rel=0.01)

    def test_default_confidence(self, fixer):
        """Missing confidence defaults to 0.7"""
        data = {"description": "Test"}
        issue = fixer._create_issue(data, "/project")
        assert issue.confidence == 0.7


class TestFileGathering:
    """Test file gathering"""

    @pytest.fixture
    def fixer(self):
        return FredFix()

    def test_gather_files_python(self, tmp_path, fixer):
        """Gather Python files"""
        # Create test files
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("def util(): pass")
        (tmp_path / "README.md").write_text("# Readme")

        files = fixer._gather_files(tmp_path, languages=["python"])
        file_names = [f.name for f in files]
        assert "main.py" in file_names
        assert "utils.py" in file_names
        assert "README.md" not in file_names

    def test_gather_files_excludes_dirs(self, tmp_path, fixer):
        """Should exclude configured directories"""
        # Create files in excluded dir
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("cached")

        # Create normal file
        (tmp_path / "main.py").write_text("main")

        files = fixer._gather_files(tmp_path, languages=["python"])
        file_names = [f.name for f in files]
        assert "main.py" in file_names
        assert "cached.py" not in file_names

    def test_gather_files_multiple_languages(self, tmp_path, fixer):
        """Gather files from multiple languages"""
        (tmp_path / "app.py").write_text("python")
        (tmp_path / "app.js").write_text("javascript")
        (tmp_path / "app.go").write_text("golang")

        files = fixer._gather_files(tmp_path, languages=["python", "javascript"])
        file_names = [f.name for f in files]
        assert "app.py" in file_names
        assert "app.js" in file_names
        assert "app.go" not in file_names

    def test_gather_files_limit(self, tmp_path, fixer):
        """Should limit number of files"""
        # Create many files
        for i in range(200):
            (tmp_path / f"file{i}.py").write_text(f"# File {i}")

        files = fixer._gather_files(tmp_path, languages=["python"])
        assert len(files) <= 100


class TestCreateFredfix:
    """Test create_fredfix convenience function"""

    def test_create_without_team(self):
        """Create FredFix without team"""
        fixer = create_fredfix()
        assert fixer is not None
        assert fixer.team is None

    def test_create_with_options(self):
        """Create FredFix with options"""
        fixer = create_fredfix(safe_mode=True, min_confidence=0.8)
        assert fixer.safe_mode is True
        assert fixer.min_confidence == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
