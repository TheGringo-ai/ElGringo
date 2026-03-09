"""
Autonomous File Watcher
=======================

Watches directories for new files and automatically processes them
using MLX models. Memory-efficient design for 16GB Macs.

Usage:
    from elgringo.autonomous.file_watcher import FileWatcher

    watcher = FileWatcher()

    # Watch for new documents and summarize them
    watcher.watch(
        path="~/Documents/inbox",
        pattern="*.pdf",
        action="summarize",
        output_dir="~/Documents/summaries"
    )

    # Watch for new code files and review them
    watcher.watch(
        path="~/code/incoming",
        pattern="*.py",
        action="review"
    )
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Storage for processed files
WATCHER_DATA_DIR = Path.home() / ".ai-dev-team" / "file_watcher"
WATCHER_DATA_DIR.mkdir(parents=True, exist_ok=True)


class WatchAction(Enum):
    """Actions to perform on detected files."""
    SUMMARIZE = "summarize"
    REVIEW = "review"
    ANALYZE = "analyze"
    CONVERT = "convert"
    CLEAN = "clean"
    CUSTOM = "custom"


@dataclass
class WatchRule:
    """A rule for watching files."""
    rule_id: str
    path: Path
    pattern: str
    action: WatchAction
    output_dir: Optional[Path] = None
    custom_handler: Optional[Callable] = None
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProcessedFile:
    """Record of a processed file."""
    file_path: str
    file_hash: str
    action: str
    result: str
    output_path: Optional[str] = None
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool = True
    error: Optional[str] = None


class FileWatcher:
    """
    Autonomous file watcher that processes new files using AI.

    Memory-efficient design:
    - Processes one file at a time
    - Uses lightweight MLX models
    - Caches processed file hashes to avoid reprocessing
    """

    def __init__(self, use_mlx: bool = True):
        """
        Initialize file watcher.

        Args:
            use_mlx: Use MLX for processing (recommended for Mac)
        """
        self.use_mlx = use_mlx
        self.rules: Dict[str, WatchRule] = {}
        self.processed_files: Set[str] = set()
        self.running = False
        self._load_state()

        # Lazy-load processors
        self._summarizer = None
        self._reviewer = None

    def _load_state(self):
        """Load processed files state from disk."""
        state_file = WATCHER_DATA_DIR / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                self.processed_files = set(state.get("processed_hashes", []))
                logger.info(f"Loaded {len(self.processed_files)} processed file records")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def _save_state(self):
        """Save state to disk."""
        state_file = WATCHER_DATA_DIR / "state.json"
        with open(state_file, "w") as f:
            json.dump({
                "processed_hashes": list(self.processed_files),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }, f)

    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file for deduplication."""
        hasher = hashlib.md5()
        hasher.update(str(file_path).encode())
        hasher.update(str(file_path.stat().st_mtime).encode())
        return hasher.hexdigest()

    def add_rule(
        self,
        path: str,
        pattern: str = "*",
        action: str = "summarize",
        output_dir: str = None,
        custom_handler: Callable = None
    ) -> str:
        """
        Add a watch rule.

        Args:
            path: Directory to watch
            pattern: File pattern (glob style, e.g., "*.pdf", "*.py")
            action: Action to perform (summarize, review, analyze, convert, clean, custom)
            output_dir: Directory for output files
            custom_handler: Custom function for processing (for action="custom")

        Returns:
            Rule ID
        """
        watch_path = Path(path).expanduser().resolve()
        if not watch_path.exists():
            watch_path.mkdir(parents=True, exist_ok=True)

        rule_id = hashlib.md5(f"{watch_path}{pattern}{action}".encode()).hexdigest()[:8]

        output_path = None
        if output_dir:
            output_path = Path(output_dir).expanduser().resolve()
            output_path.mkdir(parents=True, exist_ok=True)

        self.rules[rule_id] = WatchRule(
            rule_id=rule_id,
            path=watch_path,
            pattern=pattern,
            action=WatchAction(action),
            output_dir=output_path,
            custom_handler=custom_handler
        )

        logger.info(f"Added watch rule {rule_id}: {watch_path}/{pattern} -> {action}")
        return rule_id

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a watch rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def _get_summarizer(self):
        """Lazy-load MLX summarizer."""
        if self._summarizer is None:
            try:
                from ..intelligence.mlx_embeddings import MLXCodeGenerator
                self._summarizer = MLXCodeGenerator()
            except ImportError:
                logger.warning("MLX not available, using basic summarizer")
                self._summarizer = BasicSummarizer()
        return self._summarizer

    def _get_reviewer(self):
        """Lazy-load code reviewer."""
        if self._reviewer is None:
            try:
                from ..validation import get_validator
                self._reviewer = get_validator()
            except ImportError:
                logger.warning("Validator not available")
                self._reviewer = None
        return self._reviewer

    def _process_file(self, file_path: Path, rule: WatchRule) -> ProcessedFile:
        """Process a single file according to the rule."""
        file_hash = self._get_file_hash(file_path)

        # Skip if already processed
        if file_hash in self.processed_files:
            return None

        logger.info(f"Processing: {file_path.name} with action: {rule.action.value}")

        try:
            result = None
            output_path = None

            if rule.action == WatchAction.SUMMARIZE:
                result = self._summarize_file(file_path)
                if rule.output_dir:
                    output_path = rule.output_dir / f"{file_path.stem}_summary.md"
                    output_path.write_text(result)

            elif rule.action == WatchAction.REVIEW:
                result = self._review_file(file_path)
                if rule.output_dir:
                    output_path = rule.output_dir / f"{file_path.stem}_review.md"
                    output_path.write_text(result)

            elif rule.action == WatchAction.ANALYZE:
                result = self._analyze_file(file_path)

            elif rule.action == WatchAction.CLEAN:
                result = self._clean_data(file_path)
                if rule.output_dir:
                    output_path = rule.output_dir / f"{file_path.stem}_clean{file_path.suffix}"
                    output_path.write_text(result)

            elif rule.action == WatchAction.CUSTOM and rule.custom_handler:
                result = rule.custom_handler(file_path)

            # Mark as processed
            self.processed_files.add(file_hash)
            self._save_state()

            # Log result
            processed = ProcessedFile(
                file_path=str(file_path),
                file_hash=file_hash,
                action=rule.action.value,
                result=result[:500] if result else "",
                output_path=str(output_path) if output_path else None,
                success=True
            )

            self._log_processed(processed)
            return processed

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return ProcessedFile(
                file_path=str(file_path),
                file_hash=file_hash,
                action=rule.action.value,
                result="",
                success=False,
                error=str(e)
            )

    def _summarize_file(self, file_path: Path) -> str:
        """Summarize a file using MLX or basic extraction."""
        content = self._read_file(file_path)
        if not content:
            return "Unable to read file."

        # Try MLX summarizer
        summarizer = self._get_summarizer()
        if hasattr(summarizer, 'generate'):
            prompt = f"""Summarize the following document concisely:

{content[:3000]}

Summary:"""
            result = summarizer.generate(prompt, max_tokens=300)
            if result:
                return result

        # Fallback: basic extraction
        return self._basic_summarize(content)

    def _basic_summarize(self, content: str) -> str:
        """Basic summarization without AI."""
        lines = content.split('\n')
        summary_parts = []

        # Get first paragraph
        first_para = []
        for line in lines:
            if line.strip():
                first_para.append(line.strip())
            elif first_para:
                break
        if first_para:
            summary_parts.append(" ".join(first_para[:3]))

        # Get section headers (markdown style)
        headers = [ln.strip() for ln in lines if ln.strip().startswith('#')]
        if headers:
            summary_parts.append("\n\nSections:")
            summary_parts.extend([f"  - {h.lstrip('#').strip()}" for h in headers[:10]])

        # Word count
        word_count = len(content.split())
        summary_parts.append(f"\n\nWord count: {word_count}")

        return "\n".join(summary_parts)

    def _review_file(self, file_path: Path) -> str:
        """Review code file for issues."""
        content = self._read_file(file_path)
        if not content:
            return "Unable to read file."

        # Determine language
        ext = file_path.suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript'
        }
        language = lang_map.get(ext, 'unknown')

        # Use validator
        reviewer = self._get_reviewer()
        if reviewer:
            result = reviewer.validate(content, language)
            review_parts = [f"# Code Review: {file_path.name}\n"]

            if result.valid:
                review_parts.append("**Status:** ✅ Valid\n")
            else:
                review_parts.append("**Status:** ❌ Issues Found\n")

            if result.errors:
                review_parts.append("\n## Errors")
                for err in result.errors[:10]:
                    review_parts.append(f"- {err}")

            if result.warnings:
                review_parts.append("\n## Warnings")
                for warn in result.warnings[:10]:
                    review_parts.append(f"- {warn}")

            if result.suggestions:
                review_parts.append("\n## Suggestions")
                for sug in result.suggestions[:5]:
                    review_parts.append(f"- {sug}")

            return "\n".join(review_parts)

        return f"Code review not available for {file_path.name}"

    def _analyze_file(self, file_path: Path) -> str:
        """Analyze file structure and content."""
        content = self._read_file(file_path)
        if not content:
            return "Unable to read file."

        analysis = {
            "file": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "line_count": len(content.split('\n')),
            "word_count": len(content.split()),
            "char_count": len(content)
        }

        # Code-specific analysis
        if file_path.suffix in ['.py', '.js', '.ts']:
            analysis["functions"] = len(re.findall(r'\bdef\s+\w+|function\s+\w+|\w+\s*=\s*(?:async\s+)?\(', content))
            analysis["classes"] = len(re.findall(r'\bclass\s+\w+', content))
            analysis["imports"] = len(re.findall(r'^import\s+|^from\s+\w+\s+import', content, re.MULTILINE))

        return json.dumps(analysis, indent=2)

    def _clean_data(self, file_path: Path) -> str:
        """Clean and normalize data files."""
        content = self._read_file(file_path)
        if not content:
            return ""

        if file_path.suffix == '.json':
            try:
                data = json.loads(content)
                # Remove empty values
                if isinstance(data, dict):
                    data = {k: v for k, v in data.items() if v is not None and v != ""}
                elif isinstance(data, list):
                    data = [item for item in data if item is not None]
                return json.dumps(data, indent=2)
            except json.JSONDecodeError:
                return content

        # Basic text cleaning
        lines = content.split('\n')
        cleaned = []
        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace
            if line or (cleaned and cleaned[-1]):  # Keep single blank lines
                cleaned.append(line)

        return '\n'.join(cleaned)

    def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding detection."""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return None

    def _log_processed(self, record: ProcessedFile):
        """Log processed file record."""
        log_file = WATCHER_DATA_DIR / "processed_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps({
                "file_path": record.file_path,
                "action": record.action,
                "success": record.success,
                "output_path": record.output_path,
                "processed_at": record.processed_at,
                "error": record.error
            }) + "\n")

    def scan_once(self) -> List[ProcessedFile]:
        """Scan all watched directories once and process new files."""
        results = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # Find matching files
            pattern = rule.pattern if rule.pattern != "*" else "*.*"
            for file_path in rule.path.glob(pattern):
                if file_path.is_file():
                    result = self._process_file(file_path, rule)
                    if result:
                        results.append(result)

        return results

    async def watch_async(self, interval: float = 5.0):
        """
        Watch directories asynchronously.

        Args:
            interval: Seconds between scans
        """
        self.running = True
        logger.info(f"Started file watcher with {len(self.rules)} rules")

        while self.running:
            try:
                results = self.scan_once()
                if results:
                    logger.info(f"Processed {len(results)} files")
            except Exception as e:
                logger.error(f"Watch error: {e}")

            await asyncio.sleep(interval)

    def watch(self, interval: float = 5.0, blocking: bool = True):
        """
        Start watching directories.

        Args:
            interval: Seconds between scans
            blocking: If True, blocks until stopped
        """
        if blocking:
            asyncio.run(self.watch_async(interval))
        else:
            import threading
            thread = threading.Thread(
                target=lambda: asyncio.run(self.watch_async(interval)),
                daemon=True
            )
            thread.start()

    def stop(self):
        """Stop watching."""
        self.running = False
        self._save_state()
        logger.info("File watcher stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get watcher statistics."""
        log_file = WATCHER_DATA_DIR / "processed_log.jsonl"
        total = 0
        successful = 0
        by_action = {}

        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    record = json.loads(line)
                    total += 1
                    if record.get("success"):
                        successful += 1
                    action = record.get("action", "unknown")
                    by_action[action] = by_action.get(action, 0) + 1

        return {
            "rules_count": len(self.rules),
            "processed_count": len(self.processed_files),
            "total_processed": total,
            "successful": successful,
            "by_action": by_action
        }


class BasicSummarizer:
    """Fallback summarizer when MLX is not available."""

    def generate(self, prompt: str, max_tokens: int = 300) -> Optional[str]:
        return None


# Convenience function
def create_document_watcher(
    inbox_dir: str,
    output_dir: str,
    patterns: List[str] = None
) -> FileWatcher:
    """
    Create a document watcher for common file types.

    Args:
        inbox_dir: Directory to watch for new files
        output_dir: Directory for processed outputs
        patterns: File patterns to watch (default: common document types)

    Returns:
        Configured FileWatcher instance
    """
    watcher = FileWatcher()

    patterns = patterns or ["*.pdf", "*.txt", "*.md", "*.json", "*.csv"]

    for pattern in patterns:
        watcher.add_rule(
            path=inbox_dir,
            pattern=pattern,
            action="summarize",
            output_dir=output_dir
        )

    return watcher


def create_code_watcher(code_dir: str, output_dir: str = None) -> FileWatcher:
    """
    Create a code watcher that reviews new code files.

    Args:
        code_dir: Directory to watch for code files
        output_dir: Directory for review outputs

    Returns:
        Configured FileWatcher instance
    """
    watcher = FileWatcher()

    code_patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"]

    for pattern in code_patterns:
        watcher.add_rule(
            path=code_dir,
            pattern=pattern,
            action="review",
            output_dir=output_dir
        )

    return watcher


@dataclass
class ExpectedFile:
    """An expected file that should exist or be updated."""
    path_pattern: str  # Pattern like "tests/test_*.py" or "docs/README.md"
    related_to: str  # Pattern of files that should trigger this expectation
    description: str
    max_staleness_commits: int = 5  # How many commits before it's stale
    required: bool = True


@dataclass
class NegativeSpaceAlert:
    """Alert for a missing or stale expected file."""
    expected: ExpectedFile
    alert_type: str  # "missing", "stale", "outdated"
    message: str
    related_changes: List[str] = field(default_factory=list)
    suggested_action: str = ""


class NegativeSpaceWatcher:
    """
    Watches for the ABSENCE of expected files.

    Gemini's "Negative-Space Automation" concept:
    - Detects when tests aren't updated despite code changes
    - Alerts when documentation falls behind
    - Triggers Peer Review for suspicious patterns
    """

    def __init__(self, project_root: str):
        """
        Initialize negative-space watcher.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root).expanduser().resolve()
        self.expectations: List[ExpectedFile] = []
        self.alerts: List[NegativeSpaceAlert] = []

        # Default expectations
        self._add_default_expectations()

    def _add_default_expectations(self):
        """Add common expectations for code projects."""
        # Tests should be updated with code
        self.add_expectation(
            path_pattern="tests/test_*.py",
            related_to="*.py",
            description="Test files should be updated when code changes",
            max_staleness_commits=5
        )

        self.add_expectation(
            path_pattern="**/*_test.py",
            related_to="*.py",
            description="Test files should accompany code changes",
            max_staleness_commits=5
        )

        # TypeScript/JavaScript tests
        self.add_expectation(
            path_pattern="**/*.test.ts",
            related_to="**/*.ts",
            description="TypeScript tests should be updated",
            max_staleness_commits=5
        )

        self.add_expectation(
            path_pattern="**/*.test.js",
            related_to="**/*.js",
            description="JavaScript tests should be updated",
            max_staleness_commits=5
        )

        # Documentation
        self.add_expectation(
            path_pattern="**/README.md",
            related_to="**/*.py",
            description="README should reflect significant changes",
            max_staleness_commits=20,
            required=False
        )

        # Type hints
        self.add_expectation(
            path_pattern="**/*.pyi",
            related_to="**/*.py",
            description="Type stubs may need updating",
            max_staleness_commits=10,
            required=False
        )

    def add_expectation(
        self,
        path_pattern: str,
        related_to: str,
        description: str,
        max_staleness_commits: int = 5,
        required: bool = True
    ):
        """Add a file expectation."""
        self.expectations.append(ExpectedFile(
            path_pattern=path_pattern,
            related_to=related_to,
            description=description,
            max_staleness_commits=max_staleness_commits,
            required=required
        ))

    def check_negative_space(self) -> List[NegativeSpaceAlert]:
        """
        Check for missing or stale expected files.

        Returns:
            List of alerts for missing/stale files
        """
        self.alerts = []

        # Get recent git changes
        recent_changes = self._get_recent_changes()

        for expectation in self.expectations:
            alerts = self._check_expectation(expectation, recent_changes)
            self.alerts.extend(alerts)

        return self.alerts

    def _get_recent_changes(self) -> Dict[str, int]:
        """Get files changed in recent commits with commit counts."""
        import subprocess

        try:
            # Get files changed in last N commits
            result = subprocess.run(
                ["git", "log", "--name-only", "--pretty=format:", "-n", "20"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {}

            file_counts = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    file_counts[line.strip()] = file_counts.get(line.strip(), 0) + 1

            return file_counts
        except Exception as e:
            logger.warning(f"Failed to get git changes: {e}")
            return {}

    def _check_expectation(
        self,
        expectation: ExpectedFile,
        recent_changes: Dict[str, int]
    ) -> List[NegativeSpaceAlert]:
        """Check a single expectation against recent changes."""
        alerts = []

        # Find related files that changed
        related_pattern = expectation.related_to.replace('**/', '').replace('*', '')
        related_changes = [
            f for f in recent_changes.keys()
            if related_pattern in f or f.endswith(related_pattern.lstrip('*'))
        ]

        if not related_changes:
            return []  # No related changes, nothing to check

        # Count commits affecting related files
        total_related_commits = sum(recent_changes.get(f, 0) for f in related_changes)

        # Find expected files
        expected_pattern = expectation.path_pattern
        expected_files = list(self.project_root.glob(expected_pattern))

        if not expected_files:
            if expectation.required:
                alerts.append(NegativeSpaceAlert(
                    expected=expectation,
                    alert_type="missing",
                    message=f"Expected files matching '{expected_pattern}' not found",
                    related_changes=related_changes[:5],
                    suggested_action=f"Create tests/documentation for: {', '.join(related_changes[:3])}"
                ))
            return alerts

        # Check staleness of expected files
        expected_changes = [
            f for f in recent_changes.keys()
            if any(Path(f).match(expected_pattern.replace('**/', '')) for f in [f])
        ]

        if not expected_changes and total_related_commits > expectation.max_staleness_commits:
            alerts.append(NegativeSpaceAlert(
                expected=expectation,
                alert_type="stale",
                message=f"'{expected_pattern}' not updated in {total_related_commits} commits to related files",
                related_changes=related_changes[:5],
                suggested_action=f"Review and update: {expectation.description}"
            ))

        return alerts

    def get_summary(self) -> str:
        """Get a summary of all negative-space alerts."""
        if not self.alerts:
            return "No negative-space issues detected."

        parts = ["## Negative-Space Analysis\n"]
        parts.append(f"Found {len(self.alerts)} potential issues:\n")

        for alert in self.alerts:
            icon = "⚠️" if alert.expected.required else "ℹ️"
            parts.append(f"\n### {icon} {alert.alert_type.upper()}: {alert.expected.path_pattern}")
            parts.append(f"**Issue:** {alert.message}")
            parts.append(f"**Related to:** {', '.join(alert.related_changes[:3])}")
            parts.append(f"**Suggested Action:** {alert.suggested_action}")

        return "\n".join(parts)

    def should_trigger_review(self) -> bool:
        """Check if alerts warrant triggering Peer Review mode."""
        required_alerts = [a for a in self.alerts if a.expected.required]
        return len(required_alerts) >= 2 or any(a.alert_type == "missing" for a in required_alerts)


def create_smart_watcher(
    project_root: str,
    inbox_dir: str = None,
    output_dir: str = None
) -> Tuple[FileWatcher, NegativeSpaceWatcher]:
    """
    Create a smart watcher with both positive and negative-space detection.

    Args:
        project_root: Root directory of the project
        inbox_dir: Directory for incoming files (optional)
        output_dir: Directory for processed outputs (optional)

    Returns:
        Tuple of (FileWatcher, NegativeSpaceWatcher)
    """
    # Create file watcher
    file_watcher = FileWatcher()

    if inbox_dir:
        inbox_dir = Path(inbox_dir).expanduser()
        output = Path(output_dir).expanduser() if output_dir else inbox_dir / "processed"

        # Watch for documents
        file_watcher.add_rule(
            path=str(inbox_dir),
            pattern="*.md",
            action="summarize",
            output_dir=str(output)
        )

        # Watch for code
        for pattern in ["*.py", "*.js", "*.ts"]:
            file_watcher.add_rule(
                path=str(inbox_dir),
                pattern=pattern,
                action="review",
                output_dir=str(output)
            )

    # Create negative-space watcher
    negative_watcher = NegativeSpaceWatcher(project_root)

    return file_watcher, negative_watcher


if __name__ == "__main__":
    # Demo usage
    print("=== File Watcher Demo ===\n")

    watcher = FileWatcher()

    # Add a rule to summarize text files
    watcher.add_rule(
        path="~/Documents/inbox",
        pattern="*.txt",
        action="summarize",
        output_dir="~/Documents/summaries"
    )

    # Add a rule to review Python files
    watcher.add_rule(
        path="~/code/incoming",
        pattern="*.py",
        action="review",
        output_dir="~/code/reviews"
    )

    print(f"Configured {len(watcher.rules)} watch rules")
    print(f"Stats: {watcher.get_stats()}")

    # Demo negative-space watcher
    print("\n=== Negative-Space Watcher Demo ===\n")
    neg_watcher = NegativeSpaceWatcher(".")
    alerts = neg_watcher.check_negative_space()
    print(neg_watcher.get_summary())
