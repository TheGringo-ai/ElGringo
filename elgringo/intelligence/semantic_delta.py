"""
Semantic Delta Extraction
=========================

Extracts the "semantic delta" from file changes to reduce context size.
Instead of sending 5,000 lines to agents, sends only what matters.

16GB RAM Optimization:
- Uses MLX embeddings for lightweight semantic analysis
- Compresses large file changes to essential deltas
- Integrates with Mistake Prevention for early warning

Usage:
    from elgringo.intelligence.semantic_delta import SemanticDeltaExtractor

    extractor = SemanticDeltaExtractor()

    # Extract delta from file change
    delta = extractor.extract_delta(
        old_content="...",
        new_content="...",
        file_path="logic.py"
    )

    # Get risk assessment
    risk = extractor.assess_risk(delta)
"""

import difflib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of semantic changes."""
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    REFACTOR = "refactor"
    COMMENT = "comment"
    IMPORT = "import"
    FUNCTION = "function"
    CLASS = "class"
    CONFIG = "config"
    TEST = "test"


class RiskLevel(Enum):
    """Risk level of a change."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SemanticChange:
    """A semantic change extracted from a diff."""
    change_type: ChangeType
    description: str
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    context: str = ""
    risk_indicators: List[str] = field(default_factory=list)


@dataclass
class SemanticDelta:
    """The semantic delta of a file change."""
    file_path: str
    file_type: str
    total_lines_changed: int
    compressed_size: int  # Characters in delta vs original
    original_size: int
    compression_ratio: float
    changes: List[SemanticChange] = field(default_factory=list)
    summary: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reasons: List[str] = field(default_factory=list)
    similar_past_mistakes: List[Dict] = field(default_factory=list)

    def to_context(self, max_chars: int = 2000) -> str:
        """Convert to LLM context string, respecting size limit."""
        parts = [
            f"## File Change: {self.file_path}",
            f"**Summary:** {self.summary}",
            f"**Risk Level:** {self.risk_level.name}",
            f"**Lines Changed:** {self.total_lines_changed} | Compression: {self.compression_ratio:.1%}",
        ]

        if self.risk_reasons:
            parts.append(f"**Risk Factors:** {', '.join(self.risk_reasons[:3])}")

        if self.similar_past_mistakes:
            parts.append("\n**Similar Past Issues:**")
            for mistake in self.similar_past_mistakes[:2]:
                parts.append(f"- {mistake.get('description', 'Unknown issue')}")

        parts.append("\n### Key Changes:")
        char_count = sum(len(p) for p in parts)

        for change in self.changes:
            change_text = f"\n**{change.change_type.value.title()}:** {change.description}"
            if change.new_code and len(change.new_code) < 200:
                change_text += f"\n```\n{change.new_code}\n```"

            if char_count + len(change_text) > max_chars:
                parts.append("\n... (additional changes truncated)")
                break

            parts.append(change_text)
            char_count += len(change_text)

        return "\n".join(parts)


class SemanticDeltaExtractor:
    """
    Extracts semantic deltas from file changes.

    Memory-efficient design for 16GB Macs:
    - Processes diffs line-by-line
    - Uses regex for pattern detection (no heavy ML)
    - Optional MLX enhancement for embeddings
    """

    def __init__(self, use_mlx: bool = True):
        """
        Initialize extractor.

        Args:
            use_mlx: Use MLX for semantic similarity (optional enhancement)
        """
        self.use_mlx = use_mlx
        self._embeddings = None
        self._mistake_prevention = None

        # Pattern detectors for semantic classification
        self._patterns = {
            ChangeType.FUNCTION: [
                r'^\s*def\s+(\w+)\s*\(',
                r'^\s*async\s+def\s+(\w+)\s*\(',
                r'^function\s+(\w+)\s*\(',
                r'^const\s+(\w+)\s*=\s*(?:async\s+)?\(',
            ],
            ChangeType.CLASS: [
                r'^\s*class\s+(\w+)',
                r'^export\s+class\s+(\w+)',
            ],
            ChangeType.IMPORT: [
                r'^import\s+',
                r'^from\s+\w+\s+import',
                r'^const\s+\{.*\}\s*=\s*require',
            ],
            ChangeType.TEST: [
                r'^\s*def\s+test_',
                r'^\s*it\s*\(',
                r'^\s*describe\s*\(',
                r'^\s*@pytest',
            ],
            ChangeType.COMMENT: [
                r'^\s*#',
                r'^\s*//',
                r'^\s*/\*',
                r'^\s*"""',
                r"^\s*'''",
            ],
            ChangeType.CONFIG: [
                r'^\s*[A-Z_]+\s*=',
                r'^\s*"?\w+"?\s*:\s*',
            ],
        }

        # Risk patterns
        self._risk_patterns = {
            RiskLevel.CRITICAL: [
                (r'password|secret|api_key|token|credential', "Contains sensitive data pattern"),
                (r'eval\s*\(|exec\s*\(', "Uses dangerous eval/exec"),
                (r'DELETE\s+FROM|DROP\s+TABLE', "Contains destructive SQL"),
                (r'rm\s+-rf|rmdir', "Contains destructive file operations"),
            ],
            RiskLevel.HIGH: [
                (r'\.delete\(|\.remove\(', "Deletes data"),
                (r'transaction|commit|rollback', "Modifies transactions"),
                (r'auth|login|session', "Touches authentication"),
                (r'payment|billing|charge', "Touches payment logic"),
            ],
            RiskLevel.MEDIUM: [
                (r'async|await|Promise', "Async code (concurrency risk)"),
                (r'try\s*:|except|catch', "Error handling changes"),
                (r'if\s+.*else', "Conditional logic changes"),
            ],
        }

    def _get_embeddings(self):
        """Lazy-load MLX embeddings."""
        if self._embeddings is None and self.use_mlx:
            try:
                from .mlx_embeddings import MLXCodeEmbeddings
                self._embeddings = MLXCodeEmbeddings()
            except ImportError:
                logger.warning("MLX embeddings not available")
        return self._embeddings

    def _get_mistake_prevention(self):
        """Lazy-load mistake prevention system."""
        if self._mistake_prevention is None:
            try:
                from ..memory import MemorySystem, MistakePrevention
                memory = MemorySystem()
                self._mistake_prevention = MistakePrevention(memory)
            except Exception as e:
                logger.warning(f"Mistake prevention not available: {e}")
        return self._mistake_prevention

    def extract_delta(
        self,
        old_content: str,
        new_content: str,
        file_path: str
    ) -> SemanticDelta:
        """
        Extract semantic delta from file change.

        Args:
            old_content: Previous file content
            new_content: New file content
            file_path: Path to the file

        Returns:
            SemanticDelta with compressed change information
        """
        # Detect file type
        file_type = self._detect_file_type(file_path)

        # Generate diff
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))

        # Extract semantic changes
        changes = self._extract_changes(diff, file_type)

        # Calculate sizes
        original_size = len(old_content) + len(new_content)
        compressed = self._create_summary(changes)
        compressed_size = len(compressed)
        compression_ratio = 1 - (compressed_size / max(original_size, 1))

        # Create delta
        delta = SemanticDelta(
            file_path=file_path,
            file_type=file_type,
            total_lines_changed=len([ln for ln in diff if ln.startswith('+') or ln.startswith('-')]),
            compressed_size=compressed_size,
            original_size=original_size,
            compression_ratio=compression_ratio,
            changes=changes,
            summary=compressed
        )

        # Assess risk
        self._assess_risk(delta, new_content)

        # Check for similar past mistakes
        self._check_past_mistakes(delta)

        return delta

    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from path."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
        }
        ext = '.' + file_path.split('.')[-1].lower() if '.' in file_path else ''
        return ext_map.get(ext, 'text')

    def _extract_changes(self, diff: List[str], file_type: str) -> List[SemanticChange]:
        """Extract semantic changes from diff."""
        changes = []
        current_hunk = []
        hunk_start = 0

        for line in diff:
            if line.startswith('@@'):
                # Process previous hunk
                if current_hunk:
                    changes.extend(self._analyze_hunk(current_hunk, hunk_start, file_type))

                # Parse hunk header
                match = re.search(r'@@ -\d+(?:,\d+)? \+(\d+)', line)
                hunk_start = int(match.group(1)) if match else 0
                current_hunk = []

            elif line.startswith('+') or line.startswith('-'):
                current_hunk.append(line)

        # Process last hunk
        if current_hunk:
            changes.extend(self._analyze_hunk(current_hunk, hunk_start, file_type))

        return changes

    def _analyze_hunk(self, hunk: List[str], start_line: int, file_type: str) -> List[SemanticChange]:
        """Analyze a diff hunk and extract semantic changes."""
        changes = []

        additions = [ln[1:] for ln in hunk if ln.startswith('+')]
        deletions = [ln[1:] for ln in hunk if ln.startswith('-')]

        # Classify the change
        added_text = '\n'.join(additions)
        deleted_text = '\n'.join(deletions)

        # Check for specific change types
        change_type = ChangeType.MODIFICATION

        for ctype, patterns in self._patterns.items():
            for pattern in patterns:
                if re.search(pattern, added_text, re.MULTILINE) or re.search(pattern, deleted_text, re.MULTILINE):
                    change_type = ctype
                    break

        # Generate description
        if additions and not deletions:
            change_type = ChangeType.ADDITION
            description = self._describe_addition(additions, file_type)
        elif deletions and not additions:
            change_type = ChangeType.DELETION
            description = self._describe_deletion(deletions, file_type)
        else:
            description = self._describe_modification(additions, deletions, file_type)

        # Extract risk indicators
        risk_indicators = []
        for level, patterns in self._risk_patterns.items():
            for pattern, reason in patterns:
                if re.search(pattern, added_text, re.IGNORECASE):
                    risk_indicators.append(reason)

        changes.append(SemanticChange(
            change_type=change_type,
            description=description,
            old_code=deleted_text[:500] if deleted_text else None,
            new_code=added_text[:500] if added_text else None,
            line_start=start_line,
            line_end=start_line + len(hunk),
            risk_indicators=risk_indicators
        ))

        return changes

    def _describe_addition(self, lines: List[str], file_type: str) -> str:
        """Describe added code."""
        # Check for function/class additions
        for line in lines:
            if match := re.search(r'def\s+(\w+)|function\s+(\w+)|class\s+(\w+)', line):
                name = match.group(1) or match.group(2) or match.group(3)
                return f"Added {'function' if 'def' in line or 'function' in line else 'class'} `{name}`"

        if len(lines) == 1:
            return f"Added: {lines[0][:80].strip()}"
        return f"Added {len(lines)} lines"

    def _describe_deletion(self, lines: List[str], file_type: str) -> str:
        """Describe deleted code."""
        for line in lines:
            if match := re.search(r'def\s+(\w+)|function\s+(\w+)|class\s+(\w+)', line):
                name = match.group(1) or match.group(2) or match.group(3)
                return f"Removed {'function' if 'def' in line or 'function' in line else 'class'} `{name}`"

        if len(lines) == 1:
            return f"Removed: {lines[0][:80].strip()}"
        return f"Removed {len(lines)} lines"

    def _describe_modification(self, additions: List[str], deletions: List[str], file_type: str) -> str:
        """Describe modified code."""
        # Check for function/class modification
        for line in additions + deletions:
            if match := re.search(r'def\s+(\w+)|function\s+(\w+)', line):
                name = match.group(1) or match.group(2)
                return f"Modified function `{name}`"

        return f"Modified {len(deletions)} -> {len(additions)} lines"

    def _create_summary(self, changes: List[SemanticChange]) -> str:
        """Create a summary of all changes."""
        if not changes:
            return "No significant changes detected"

        # Group by type
        by_type = {}
        for change in changes:
            key = change.change_type.value
            by_type.setdefault(key, []).append(change.description)

        parts = []
        for change_type, descriptions in by_type.items():
            if len(descriptions) == 1:
                parts.append(descriptions[0])
            else:
                parts.append(f"{len(descriptions)} {change_type}s")

        return "; ".join(parts)

    def _assess_risk(self, delta: SemanticDelta, content: str):
        """Assess the risk level of the change."""
        risk_reasons = []
        max_risk = RiskLevel.LOW

        # Check all changes for risk indicators
        for change in delta.changes:
            risk_reasons.extend(change.risk_indicators)

        # Check content directly for risk patterns
        for level, patterns in self._risk_patterns.items():
            for pattern, reason in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    if level.value > max_risk.value:
                        max_risk = level
                    if reason not in risk_reasons:
                        risk_reasons.append(reason)

        delta.risk_level = max_risk
        delta.risk_reasons = risk_reasons[:5]

    def _check_past_mistakes(self, delta: SemanticDelta):
        """Check for similar past mistakes."""
        prevention = self._get_mistake_prevention()
        if prevention and hasattr(prevention, 'check_for_similar'):
            # Create a context string from the changes
            context = delta.to_context(max_chars=1000)
            try:
                similar = prevention.check_for_similar(context)
                delta.similar_past_mistakes = similar[:3] if similar else []
            except Exception as e:
                logger.warning(f"Failed to check past mistakes: {e}")

    def extract_from_git_diff(self, diff_output: str) -> List[SemanticDelta]:
        """
        Extract semantic deltas from git diff output.

        Args:
            diff_output: Output from `git diff`

        Returns:
            List of SemanticDelta for each changed file
        """
        deltas = []
        current_file = None
        old_content = []
        new_content = []

        for line in diff_output.split('\n'):
            if line.startswith('diff --git'):
                # Save previous file
                if current_file:
                    delta = self.extract_delta(
                        '\n'.join(old_content),
                        '\n'.join(new_content),
                        current_file
                    )
                    deltas.append(delta)

                # Parse new file
                match = re.search(r'b/(.+)$', line)
                current_file = match.group(1) if match else "unknown"
                old_content = []
                new_content = []

            elif line.startswith('-') and not line.startswith('---'):
                old_content.append(line[1:])
            elif line.startswith('+') and not line.startswith('+++'):
                new_content.append(line[1:])

        # Save last file
        if current_file:
            delta = self.extract_delta(
                '\n'.join(old_content),
                '\n'.join(new_content),
                current_file
            )
            deltas.append(delta)

        return deltas


# Convenience function
def get_semantic_delta(old: str, new: str, path: str) -> SemanticDelta:
    """Quick extraction of semantic delta."""
    extractor = SemanticDeltaExtractor(use_mlx=False)  # Fast mode
    return extractor.extract_delta(old, new, path)


if __name__ == "__main__":
    # Demo
    old_code = '''
def process_data(data):
    """Process input data."""
    result = []
    for item in data:
        result.append(item * 2)
    return result
'''

    new_code = '''
def process_data(data):
    """Process input data with validation."""
    if not data:
        raise ValueError("Data cannot be empty")

    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def validate_input(data):
    """Validate input before processing."""
    return all(isinstance(x, int) for x in data)
'''

    extractor = SemanticDeltaExtractor(use_mlx=False)
    delta = extractor.extract_delta(old_code, new_code, "processor.py")

    print("=== Semantic Delta Demo ===\n")
    print(f"File: {delta.file_path}")
    print(f"Compression: {delta.compression_ratio:.1%}")
    print(f"Risk Level: {delta.risk_level.name}")
    print(f"\nSummary: {delta.summary}")
    print(f"\nChanges: {len(delta.changes)}")
    for change in delta.changes:
        print(f"  - [{change.change_type.value}] {change.description}")

    print("\n=== Context for LLM ===")
    print(delta.to_context(max_chars=1000))
