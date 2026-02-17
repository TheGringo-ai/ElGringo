"""
Coding Knowledge Hub - AI Team's Institutional Coding Memory
=============================================================

Central repository for coding knowledge that the AI team learns and shares.
This helps the team:
- Remember solutions that worked
- Never repeat the same coding mistakes
- Share patterns across languages/frameworks
- Build up expertise over time

Usage:
    hub = CodingKnowledgeHub()

    # Store a working solution
    hub.store_code_snippet(
        language="python",
        category="firebase",
        title="Firestore batch write",
        code="...",
        description="How to batch write to Firestore",
        tags=["firebase", "firestore", "batch"]
    )

    # Find solutions
    snippets = hub.search_snippets("firestore batch write")

    # Store error->fix mapping
    hub.store_error_fix(
        error_pattern="ModuleNotFoundError: No module named 'xyz'",
        fix_steps=["pip install xyz", "Verify virtual environment is active"],
        language="python"
    )

    # Query when encountering an error
    fixes = hub.find_fix_for_error("ModuleNotFoundError: No module named 'flask'")
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class CodeSnippet:
    """A reusable code snippet"""
    snippet_id: str
    language: str  # python, typescript, javascript, sql, etc.
    category: str  # firebase, api, database, auth, testing, etc.
    title: str
    description: str
    code: str
    tags: List[str] = field(default_factory=list)
    use_count: int = 0
    success_count: int = 0
    last_used: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "manual"  # manual, auto_learned, code_review


@dataclass
class ErrorFix:
    """Mapping from error pattern to fix"""
    fix_id: str
    error_pattern: str  # Regex or string pattern
    error_type: str  # runtime, syntax, import, type, etc.
    language: str
    fix_steps: List[str]
    fix_code: Optional[str] = None
    explanation: str = ""
    success_count: int = 0
    failure_count: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FrameworkPattern:
    """Pattern for a specific framework/library"""
    pattern_id: str
    framework: str  # react, fastapi, firebase, etc.
    pattern_name: str
    description: str
    code_template: str
    use_cases: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)  # What NOT to do
    related_patterns: List[str] = field(default_factory=list)
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class APIKnowledge:
    """Knowledge about how to use an API"""
    api_id: str
    api_name: str  # openai, firebase, stripe, etc.
    endpoint_or_method: str
    description: str
    example_code: str
    parameters: Dict[str, str] = field(default_factory=dict)
    common_errors: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CodingKnowledgeHub:
    """
    Central hub for all coding knowledge the AI team accumulates.

    Features:
    - Store and search code snippets by language/category
    - Error->Fix mappings for quick debugging
    - Framework-specific patterns
    - API usage knowledge
    - Automatic learning from successful solutions
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/coding_hub"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Template registry integration
        self._template_registry = None
        try:
            from templates.registry import TemplateRegistry
            self._template_registry = TemplateRegistry()
            logger.info("Template registry loaded")
        except ImportError:
            logger.debug("Template registry not available")

        # In-memory storage
        self._snippets: List[CodeSnippet] = []
        self._error_fixes: List[ErrorFix] = []
        self._patterns: List[FrameworkPattern] = []
        self._api_knowledge: List[APIKnowledge] = []

        # Indexes for fast lookup
        self._snippet_by_language: Dict[str, List[str]] = {}
        self._snippet_by_category: Dict[str, List[str]] = {}
        self._error_fix_by_language: Dict[str, List[str]] = {}
        self._pattern_by_framework: Dict[str, List[str]] = {}

        self._load_all()

    def _generate_id(self, *args) -> str:
        """Generate unique ID from content"""
        content = "".join(str(a) for a in args) + datetime.now().isoformat()
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for search"""
        return [w.lower() for w in re.split(r'[^a-zA-Z0-9]+', text) if len(w) > 2]

    def _compute_relevance(self, query_tokens: List[str], target_tokens: List[str]) -> float:
        """Compute relevance score between query and target"""
        if not query_tokens or not target_tokens:
            return 0.0

        target_set = set(target_tokens)
        matches = sum(1 for t in query_tokens if t in target_set)
        return matches / len(query_tokens)

    # ==================== Storage ====================

    def _load_all(self):
        """Load all knowledge from disk"""
        try:
            # Load snippets
            snippets_file = self.storage_dir / "snippets.json"
            if snippets_file.exists():
                with open(snippets_file) as f:
                    self._snippets = [CodeSnippet(**s) for s in json.load(f)]

            # Load error fixes
            fixes_file = self.storage_dir / "error_fixes.json"
            if fixes_file.exists():
                with open(fixes_file) as f:
                    self._error_fixes = [ErrorFix(**e) for e in json.load(f)]

            # Load patterns
            patterns_file = self.storage_dir / "patterns.json"
            if patterns_file.exists():
                with open(patterns_file) as f:
                    self._patterns = [FrameworkPattern(**p) for p in json.load(f)]

            # Load API knowledge
            api_file = self.storage_dir / "api_knowledge.json"
            if api_file.exists():
                with open(api_file) as f:
                    self._api_knowledge = [APIKnowledge(**a) for a in json.load(f)]

            # Rebuild indexes
            self._rebuild_indexes()

            logger.info(f"Loaded coding hub: {len(self._snippets)} snippets, "
                       f"{len(self._error_fixes)} error fixes, "
                       f"{len(self._patterns)} patterns, "
                       f"{len(self._api_knowledge)} API docs")

        except Exception as e:
            logger.warning(f"Error loading coding hub: {e}")

    def _save_all(self):
        """Save all knowledge to disk"""
        try:
            with open(self.storage_dir / "snippets.json", "w") as f:
                json.dump([asdict(s) for s in self._snippets], f, indent=2)

            with open(self.storage_dir / "error_fixes.json", "w") as f:
                json.dump([asdict(e) for e in self._error_fixes], f, indent=2)

            with open(self.storage_dir / "patterns.json", "w") as f:
                json.dump([asdict(p) for p in self._patterns], f, indent=2)

            with open(self.storage_dir / "api_knowledge.json", "w") as f:
                json.dump([asdict(a) for a in self._api_knowledge], f, indent=2)

        except Exception as e:
            logger.error(f"Error saving coding hub: {e}")

    def _rebuild_indexes(self):
        """Rebuild lookup indexes"""
        self._snippet_by_language = {}
        self._snippet_by_category = {}
        self._error_fix_by_language = {}
        self._pattern_by_framework = {}

        for s in self._snippets:
            self._snippet_by_language.setdefault(s.language, []).append(s.snippet_id)
            self._snippet_by_category.setdefault(s.category, []).append(s.snippet_id)

        for e in self._error_fixes:
            self._error_fix_by_language.setdefault(e.language, []).append(e.fix_id)

        for p in self._patterns:
            self._pattern_by_framework.setdefault(p.framework, []).append(p.pattern_id)

    # ==================== Code Snippets ====================

    def store_code_snippet(
        self,
        language: str,
        category: str,
        title: str,
        code: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        source: str = "manual",
    ) -> str:
        """
        Store a reusable code snippet.

        Args:
            language: Programming language (python, typescript, etc.)
            category: Category (firebase, auth, testing, etc.)
            title: Short descriptive title
            code: The actual code
            description: Explanation of what it does
            tags: Additional tags for searchability
            source: Where this came from (manual, auto_learned, code_review)

        Returns:
            snippet_id
        """
        snippet_id = self._generate_id(language, category, title, code)

        snippet = CodeSnippet(
            snippet_id=snippet_id,
            language=language.lower(),
            category=category.lower(),
            title=title,
            description=description,
            code=code,
            tags=tags or [],
            source=source,
        )

        self._snippets.append(snippet)
        self._snippet_by_language.setdefault(language.lower(), []).append(snippet_id)
        self._snippet_by_category.setdefault(category.lower(), []).append(snippet_id)

        self._save_all()
        logger.info(f"Stored snippet: {title} ({language}/{category})")

        return snippet_id

    def search_snippets(
        self,
        query: str,
        language: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[CodeSnippet]:
        """
        Search for code snippets.

        Args:
            query: Search query
            language: Filter by language
            category: Filter by category
            limit: Max results to return

        Returns:
            List of matching snippets, sorted by relevance
        """
        query_tokens = self._tokenize(query)

        # Filter candidates
        candidates = self._snippets
        if language:
            ids = set(self._snippet_by_language.get(language.lower(), []))
            candidates = [s for s in candidates if s.snippet_id in ids]
        if category:
            ids = set(self._snippet_by_category.get(category.lower(), []))
            candidates = [s for s in candidates if s.snippet_id in ids]

        # Score and rank
        scored = []
        for snippet in candidates:
            target_tokens = (
                self._tokenize(snippet.title) +
                self._tokenize(snippet.description) +
                [t.lower() for t in snippet.tags]
            )
            score = self._compute_relevance(query_tokens, target_tokens)

            # Boost by usage
            score += min(snippet.use_count * 0.01, 0.2)
            score += min(snippet.success_count * 0.02, 0.3)

            if score > 0:
                scored.append((score, snippet))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    def record_snippet_usage(self, snippet_id: str, was_successful: bool = True):
        """Record that a snippet was used"""
        for snippet in self._snippets:
            if snippet.snippet_id == snippet_id:
                snippet.use_count += 1
                if was_successful:
                    snippet.success_count += 1
                snippet.last_used = datetime.now(timezone.utc).isoformat()
                self._save_all()
                break

    # ==================== Error Fixes ====================

    def store_error_fix(
        self,
        error_pattern: str,
        fix_steps: List[str],
        language: str,
        error_type: str = "runtime",
        fix_code: Optional[str] = None,
        explanation: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store an error -> fix mapping.

        Args:
            error_pattern: The error message pattern (can be regex)
            fix_steps: Steps to fix the error
            language: Programming language
            error_type: Type of error (runtime, syntax, import, type, etc.)
            fix_code: Optional code that fixes the issue
            explanation: Why this fix works
            tags: Additional tags

        Returns:
            fix_id
        """
        fix_id = self._generate_id(error_pattern, language)

        error_fix = ErrorFix(
            fix_id=fix_id,
            error_pattern=error_pattern,
            error_type=error_type,
            language=language.lower(),
            fix_steps=fix_steps,
            fix_code=fix_code,
            explanation=explanation,
            tags=tags or [],
        )

        self._error_fixes.append(error_fix)
        self._error_fix_by_language.setdefault(language.lower(), []).append(fix_id)

        self._save_all()
        logger.info(f"Stored error fix: {error_pattern[:50]}... ({language})")

        return fix_id

    def find_fix_for_error(
        self,
        error_message: str,
        language: Optional[str] = None,
        limit: int = 5,
    ) -> List[ErrorFix]:
        """
        Find fixes for an error message.

        Args:
            error_message: The error message
            language: Optional language filter
            limit: Max results

        Returns:
            List of potential fixes, sorted by relevance
        """
        candidates = self._error_fixes
        if language:
            ids = set(self._error_fix_by_language.get(language.lower(), []))
            candidates = [e for e in candidates if e.fix_id in ids]

        scored = []
        error_lower = error_message.lower()
        error_tokens = self._tokenize(error_message)

        for fix in candidates:
            score = 0.0

            # Check regex/pattern match
            try:
                if re.search(fix.error_pattern, error_message, re.IGNORECASE):
                    score += 1.0
            except re.error:
                # Invalid regex, try string match
                if fix.error_pattern.lower() in error_lower:
                    score += 0.8

            # Token overlap
            pattern_tokens = self._tokenize(fix.error_pattern)
            token_score = self._compute_relevance(error_tokens, pattern_tokens)
            score += token_score * 0.5

            # Boost by success rate
            total = fix.success_count + fix.failure_count
            if total > 0:
                success_rate = fix.success_count / total
                score += success_rate * 0.2

            if score > 0.1:
                scored.append((score, fix))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    def record_fix_outcome(self, fix_id: str, was_successful: bool):
        """Record whether a fix worked"""
        for fix in self._error_fixes:
            if fix.fix_id == fix_id:
                if was_successful:
                    fix.success_count += 1
                else:
                    fix.failure_count += 1
                self._save_all()
                break

    # ==================== Framework Patterns ====================

    def store_framework_pattern(
        self,
        framework: str,
        pattern_name: str,
        description: str,
        code_template: str,
        use_cases: Optional[List[str]] = None,
        anti_patterns: Optional[List[str]] = None,
    ) -> str:
        """
        Store a framework-specific pattern.

        Args:
            framework: Framework name (react, fastapi, firebase, etc.)
            pattern_name: Name of the pattern
            description: What it does
            code_template: Template code
            use_cases: When to use this
            anti_patterns: What NOT to do

        Returns:
            pattern_id
        """
        pattern_id = self._generate_id(framework, pattern_name)

        pattern = FrameworkPattern(
            pattern_id=pattern_id,
            framework=framework.lower(),
            pattern_name=pattern_name,
            description=description,
            code_template=code_template,
            use_cases=use_cases or [],
            anti_patterns=anti_patterns or [],
        )

        self._patterns.append(pattern)
        self._pattern_by_framework.setdefault(framework.lower(), []).append(pattern_id)

        self._save_all()
        logger.info(f"Stored pattern: {pattern_name} ({framework})")

        return pattern_id

    def get_patterns_for_framework(self, framework: str) -> List[FrameworkPattern]:
        """Get all patterns for a framework"""
        ids = set(self._pattern_by_framework.get(framework.lower(), []))
        return [p for p in self._patterns if p.pattern_id in ids]

    def search_patterns(self, query: str, framework: Optional[str] = None, limit: int = 10) -> List[FrameworkPattern]:
        """Search for patterns"""
        query_tokens = self._tokenize(query)

        candidates = self._patterns
        if framework:
            ids = set(self._pattern_by_framework.get(framework.lower(), []))
            candidates = [p for p in candidates if p.pattern_id in ids]

        scored = []
        for pattern in candidates:
            target_tokens = (
                self._tokenize(pattern.pattern_name) +
                self._tokenize(pattern.description) +
                [uc.lower() for uc in pattern.use_cases]
            )
            score = self._compute_relevance(query_tokens, target_tokens)
            score += min(pattern.use_count * 0.02, 0.3)

            if score > 0:
                scored.append((score, pattern))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    # ==================== API Knowledge ====================

    def store_api_knowledge(
        self,
        api_name: str,
        endpoint_or_method: str,
        description: str,
        example_code: str,
        parameters: Optional[Dict[str, str]] = None,
        common_errors: Optional[List[str]] = None,
        tips: Optional[List[str]] = None,
    ) -> str:
        """
        Store knowledge about an API.

        Args:
            api_name: Name of the API (openai, firebase, stripe, etc.)
            endpoint_or_method: Specific endpoint or method
            description: What it does
            example_code: Working example
            parameters: Parameter descriptions
            common_errors: Common errors with this API
            tips: Usage tips

        Returns:
            api_id
        """
        api_id = self._generate_id(api_name, endpoint_or_method)

        knowledge = APIKnowledge(
            api_id=api_id,
            api_name=api_name.lower(),
            endpoint_or_method=endpoint_or_method,
            description=description,
            example_code=example_code,
            parameters=parameters or {},
            common_errors=common_errors or [],
            tips=tips or [],
        )

        self._api_knowledge.append(knowledge)
        self._save_all()

        logger.info(f"Stored API knowledge: {api_name} - {endpoint_or_method}")
        return api_id

    def get_api_knowledge(self, api_name: str, query: Optional[str] = None) -> List[APIKnowledge]:
        """Get knowledge about an API"""
        matches = [a for a in self._api_knowledge if a.api_name == api_name.lower()]

        if query:
            query_tokens = self._tokenize(query)
            scored = []
            for api in matches:
                target_tokens = (
                    self._tokenize(api.endpoint_or_method) +
                    self._tokenize(api.description)
                )
                score = self._compute_relevance(query_tokens, target_tokens)
                if score > 0:
                    scored.append((score, api))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s[1] for s in scored]

        return matches

    # ==================== Context Generation ====================

    def generate_coding_context(
        self,
        task_description: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        include_snippets: bool = True,
        include_patterns: bool = True,
        include_error_fixes: bool = True,
        max_items: int = 5,
    ) -> str:
        """
        Generate context for AI prompts based on relevant knowledge.

        Args:
            task_description: What the AI is trying to do
            language: Target language
            framework: Target framework
            include_snippets: Include relevant code snippets
            include_patterns: Include relevant patterns
            include_error_fixes: Include potentially relevant error fixes
            max_items: Max items per category

        Returns:
            Context string to prepend to prompts
        """
        context_parts = ["## CODING KNOWLEDGE HUB CONTEXT\n"]

        if include_snippets:
            snippets = self.search_snippets(task_description, language=language, limit=max_items)
            if snippets:
                context_parts.append("### Relevant Code Snippets\n")
                for s in snippets:
                    context_parts.append(f"**{s.title}** ({s.language}/{s.category})")
                    if s.description:
                        context_parts.append(f"{s.description}")
                    context_parts.append(f"```{s.language}\n{s.code[:500]}\n```\n")

        if include_patterns and framework:
            patterns = self.search_patterns(task_description, framework=framework, limit=max_items)
            if patterns:
                context_parts.append("### Framework Patterns\n")
                for p in patterns:
                    context_parts.append(f"**{p.pattern_name}** ({p.framework})")
                    context_parts.append(f"{p.description}")
                    if p.anti_patterns:
                        context_parts.append(f"⚠️ Avoid: {'; '.join(p.anti_patterns[:2])}")
                    context_parts.append("")

        # Add template suggestions
        templates = self.suggest_templates(task_description)
        if templates:
            context_parts.append("### Suggested Templates\n")
            for t in templates[:3]:
                context_parts.append(f"**{t['name']}** (`{t['id']}`)")
                context_parts.append(f"{t['description']}")
                context_parts.append(f"Tags: {', '.join(t.get('tags', []))}\n")

        return "\n".join(context_parts) if len(context_parts) > 1 else ""

    def suggest_templates(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Suggest templates for a given task.

        Args:
            task_description: What the task needs to accomplish

        Returns:
            List of template info dicts
        """
        if not self._template_registry:
            return []

        try:
            templates = self._template_registry.suggest_for_task(task_description)
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "language": t.language,
                    "tags": t.tags,
                    "dependencies": t.dependencies,
                }
                for t in templates
            ]
        except Exception as e:
            logger.debug(f"Template suggestion error: {e}")
            return []

    def get_template(self, template_id: str) -> Optional[str]:
        """
        Get template content by ID.

        Args:
            template_id: Template ID (e.g., "backend/fastapi/crud_api")

        Returns:
            Template content or None
        """
        if not self._template_registry:
            return None
        return self._template_registry.get_content(template_id)

    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """
        Search templates by query.

        Args:
            query: Search query

        Returns:
            List of matching template info dicts
        """
        if not self._template_registry:
            return []

        try:
            templates = self._template_registry.search(query)
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "language": t.language,
                    "tags": t.tags,
                }
                for t in templates
            ]
        except Exception as e:
            logger.debug(f"Template search error: {e}")
            return []

    def list_all_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        if not self._template_registry:
            return []

        try:
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category,
                    "description": t.description,
                    "language": t.language,
                }
                for t in self._template_registry.list_all()
            ]
        except Exception as e:
            logger.debug(f"Template list error: {e}")
            return []

    # ==================== Auto-Learning ====================

    def learn_from_successful_code(
        self,
        code: str,
        language: str,
        task_description: str,
        framework: Optional[str] = None,
    ) -> Optional[str]:
        """
        Automatically learn from successful code.

        Called when code is approved/works. Extracts patterns and stores them.

        Returns:
            snippet_id if stored, None if not significant enough
        """
        # Only store non-trivial code
        if len(code.strip()) < 50:
            return None

        # Determine category from code content
        category = self._detect_category(code, language)

        # Generate title from task
        title = task_description[:50] if len(task_description) > 50 else task_description

        return self.store_code_snippet(
            language=language,
            category=category,
            title=title,
            code=code,
            description=task_description,
            tags=[framework] if framework else [],
            source="auto_learned",
        )

    def learn_from_error_resolution(
        self,
        error_message: str,
        fix_applied: str,
        language: str,
    ) -> str:
        """
        Learn from a resolved error.

        Called when an error is fixed. Stores the pattern for future use.
        """
        # Extract core error pattern
        pattern = self._extract_error_pattern(error_message)

        return self.store_error_fix(
            error_pattern=pattern,
            fix_steps=[fix_applied],
            language=language,
            explanation="Auto-learned from successful fix",
        )

    def _detect_category(self, code: str, language: str) -> str:
        """Detect category from code content"""
        code_lower = code.lower()

        # Check for common patterns
        if any(k in code_lower for k in ['firebase', 'firestore', 'realtime']):
            return "firebase"
        if any(k in code_lower for k in ['fetch', 'axios', 'request', 'http']):
            return "api"
        if any(k in code_lower for k in ['test', 'assert', 'expect', 'mock']):
            return "testing"
        if any(k in code_lower for k in ['auth', 'login', 'password', 'token', 'jwt']):
            return "auth"
        if any(k in code_lower for k in ['sql', 'query', 'select', 'insert', 'database']):
            return "database"
        if any(k in code_lower for k in ['async', 'await', 'promise', 'concurrent']):
            return "async"
        if any(k in code_lower for k in ['react', 'component', 'usestate', 'useeffect']):
            return "react"
        if any(k in code_lower for k in ['fastapi', 'flask', 'django', 'express']):
            return "web-framework"

        return "general"

    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract a reusable pattern from an error message"""
        # Remove specific file paths
        pattern = re.sub(r'/[^\s]+\.(py|js|ts|tsx)', '<file>', error_message)
        # Remove line numbers
        pattern = re.sub(r'line \d+', 'line <N>', pattern)
        # Remove specific variable names in quotes
        pattern = re.sub(r"'[^']+' ", "'<name>' ", pattern)

        return pattern[:200]  # Limit length

    # ==================== Statistics ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get hub statistics"""
        return {
            "total_snippets": len(self._snippets),
            "total_error_fixes": len(self._error_fixes),
            "total_patterns": len(self._patterns),
            "total_api_docs": len(self._api_knowledge),
            "languages": list(self._snippet_by_language.keys()),
            "categories": list(self._snippet_by_category.keys()),
            "frameworks": list(self._pattern_by_framework.keys()),
            "snippets_by_language": {
                lang: len(ids) for lang, ids in self._snippet_by_language.items()
            },
            "most_used_snippets": [
                {"title": s.title, "use_count": s.use_count}
                for s in sorted(self._snippets, key=lambda x: x.use_count, reverse=True)[:5]
            ],
            "error_fix_success_rates": {
                f.error_pattern[:30]: f.success_count / max(f.success_count + f.failure_count, 1)
                for f in self._error_fixes[:10]
            },
        }


# Global instance
_coding_hub: Optional[CodingKnowledgeHub] = None


def get_coding_hub() -> CodingKnowledgeHub:
    """Get or create the global coding hub instance"""
    global _coding_hub
    if _coding_hub is None:
        _coding_hub = CodingKnowledgeHub()
    return _coding_hub
