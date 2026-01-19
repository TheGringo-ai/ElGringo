"""
Prompt Template Library - Reusable effective prompts
=====================================================

Stores and manages prompt templates for different task types.
Learns from user interactions to suggest better prompts.

Features:
- Pre-built templates for common tasks
- Variable substitution
- Success tracking per template
- Auto-suggestion based on task context
"""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """A reusable prompt template"""
    template_id: str
    name: str
    category: str  # coding, debugging, review, architecture, etc.
    template: str  # The prompt with {variables}
    description: str = ""
    variables: List[str] = field(default_factory=list)  # List of variable names
    tags: List[str] = field(default_factory=list)
    example_values: Dict[str, str] = field(default_factory=dict)

    # Usage stats
    use_count: int = 0
    success_count: int = 0
    last_used: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Metadata
    author: str = "system"
    is_builtin: bool = False

    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.5
        return self.success_count / self.use_count

    def render(self, variables: Dict[str, str]) -> str:
        """Render template with variables"""
        result = self.template
        for var_name, var_value in variables.items():
            result = result.replace(f"{{{var_name}}}", str(var_value))
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "template": self.template,
            "description": self.description,
            "variables": self.variables,
            "tags": self.tags,
            "example_values": self.example_values,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
            "last_used": self.last_used,
            "created_at": self.created_at,
            "author": self.author,
            "is_builtin": self.is_builtin,
        }


# Built-in templates for common tasks
BUILTIN_TEMPLATES = [
    # Coding templates
    PromptTemplate(
        template_id="code_function",
        name="Write Function",
        category="coding",
        template="""Write a {language} function that {description}.

Requirements:
- Include type hints
- Add docstring with examples
- Handle edge cases
- Follow {language} best practices

Function signature suggestion: {signature}""",
        description="Generate a well-documented function",
        variables=["language", "description", "signature"],
        example_values={"language": "Python", "description": "calculates fibonacci numbers", "signature": "def fibonacci(n: int) -> int"},
        tags=["function", "code-generation"],
        is_builtin=True,
    ),
    PromptTemplate(
        template_id="code_class",
        name="Write Class",
        category="coding",
        template="""Design and implement a {language} class for {purpose}.

Requirements:
- Proper encapsulation
- Type hints on all methods
- Comprehensive docstrings
- Consider inheritance/composition as appropriate

Key methods needed: {methods}""",
        description="Generate a well-designed class",
        variables=["language", "purpose", "methods"],
        example_values={"language": "Python", "purpose": "managing user sessions", "methods": "__init__, create, validate, destroy"},
        tags=["class", "oop", "code-generation"],
        is_builtin=True,
    ),
    PromptTemplate(
        template_id="code_api",
        name="Write API Endpoint",
        category="coding",
        template="""Create a {framework} API endpoint for {purpose}.

Endpoint: {method} {path}
Request body: {request_schema}
Response: {response_schema}

Requirements:
- Input validation
- Error handling with appropriate status codes
- Authentication if needed
- Follow REST conventions""",
        description="Generate an API endpoint",
        variables=["framework", "purpose", "method", "path", "request_schema", "response_schema"],
        example_values={
            "framework": "FastAPI",
            "purpose": "creating a new user",
            "method": "POST",
            "path": "/users",
            "request_schema": "{email, password, name}",
            "response_schema": "{id, email, name, created_at}"
        },
        tags=["api", "rest", "endpoint"],
        is_builtin=True,
    ),

    # Debugging templates
    PromptTemplate(
        template_id="debug_error",
        name="Debug Error",
        category="debugging",
        template="""Debug this error:

Error message: {error}

Context:
{context}

Code (if relevant):
```{language}
{code}
```

Please provide:
1. Root cause analysis
2. Step-by-step fix
3. Prevention strategies""",
        description="Debug an error with context",
        variables=["error", "context", "language", "code"],
        example_values={
            "error": "TypeError: cannot unpack non-iterable NoneType object",
            "context": "This happens when processing user data",
            "language": "python",
            "code": "name, email = get_user_info(user_id)"
        },
        tags=["debug", "error", "fix"],
        is_builtin=True,
    ),
    PromptTemplate(
        template_id="debug_performance",
        name="Debug Performance",
        category="debugging",
        template="""Analyze this code for performance issues:

```{language}
{code}
```

Current behavior: {current_behavior}
Expected performance: {expected}

Please identify:
1. Bottlenecks
2. Optimization opportunities
3. Specific fixes with code""",
        description="Optimize slow code",
        variables=["language", "code", "current_behavior", "expected"],
        tags=["performance", "optimization", "debug"],
        is_builtin=True,
    ),

    # Review templates
    PromptTemplate(
        template_id="review_code",
        name="Code Review",
        category="review",
        template="""Review this {language} code for:
{focus_areas}

```{language}
{code}
```

Provide feedback on:
1. Code quality issues (with severity)
2. Bugs or potential bugs
3. Security concerns
4. Suggestions for improvement
5. What's done well""",
        description="Comprehensive code review",
        variables=["language", "code", "focus_areas"],
        example_values={
            "language": "python",
            "code": "def process(data): ...",
            "focus_areas": "- Security\n- Performance\n- Error handling"
        },
        tags=["review", "quality", "security"],
        is_builtin=True,
    ),
    PromptTemplate(
        template_id="review_pr",
        name="PR Review",
        category="review",
        template="""Review this pull request:

Title: {title}
Description: {description}

Changes:
{diff}

Focus on:
1. Does it achieve the stated goal?
2. Are there any bugs or issues?
3. Is the code maintainable?
4. Are tests adequate?""",
        description="Pull request review",
        variables=["title", "description", "diff"],
        tags=["pr", "review", "git"],
        is_builtin=True,
    ),

    # Architecture templates
    PromptTemplate(
        template_id="arch_design",
        name="System Design",
        category="architecture",
        template="""Design a system architecture for: {requirement}

Constraints:
{constraints}

Please provide:
1. High-level architecture diagram (describe)
2. Component breakdown with responsibilities
3. Technology recommendations
4. Data flow
5. Trade-offs and alternatives considered""",
        description="System architecture design",
        variables=["requirement", "constraints"],
        example_values={
            "requirement": "A real-time notification system",
            "constraints": "- Must scale to 1M users\n- < 100ms latency\n- AWS preferred"
        },
        tags=["architecture", "design", "system"],
        is_builtin=True,
    ),

    # Testing templates
    PromptTemplate(
        template_id="test_unit",
        name="Write Unit Tests",
        category="testing",
        template="""Write comprehensive unit tests for this {language} code:

```{language}
{code}
```

Requirements:
- Use {test_framework}
- Cover happy path and edge cases
- Include error scenarios
- Use descriptive test names
- Add comments explaining test purpose""",
        description="Generate unit tests",
        variables=["language", "code", "test_framework"],
        example_values={
            "language": "python",
            "code": "def divide(a, b): return a / b",
            "test_framework": "pytest"
        },
        tags=["testing", "unit-test", "quality"],
        is_builtin=True,
    ),

    # Documentation templates
    PromptTemplate(
        template_id="doc_api",
        name="API Documentation",
        category="documentation",
        template="""Generate API documentation for these endpoints:

{endpoints}

Include:
1. Description of each endpoint
2. Request/response examples
3. Error codes and meanings
4. Authentication requirements
5. Rate limits if applicable""",
        description="Generate API docs",
        variables=["endpoints"],
        tags=["documentation", "api", "openapi"],
        is_builtin=True,
    ),

    # Refactoring templates
    PromptTemplate(
        template_id="refactor_code",
        name="Refactor Code",
        category="refactoring",
        template="""Refactor this {language} code to improve {goal}:

```{language}
{code}
```

Constraints:
- Maintain existing functionality
- Keep the same public interface
- {additional_constraints}

Show the refactored code with explanations.""",
        description="Refactor for specific goal",
        variables=["language", "code", "goal", "additional_constraints"],
        example_values={
            "language": "python",
            "code": "# complex function here",
            "goal": "readability and maintainability",
            "additional_constraints": "No external dependencies"
        },
        tags=["refactor", "clean-code", "improvement"],
        is_builtin=True,
    ),
]


class PromptLibrary:
    """
    Library of reusable prompt templates.

    Features:
    - Pre-built templates for common tasks
    - Custom template creation
    - Success tracking and ranking
    - Auto-suggestion based on context
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/prompts"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._templates: Dict[str, PromptTemplate] = {}
        self._load_builtins()
        self._load_custom()

    def _load_builtins(self):
        """Load built-in templates"""
        for template in BUILTIN_TEMPLATES:
            self._templates[template.template_id] = template

    def _load_custom(self):
        """Load custom templates from disk"""
        try:
            custom_file = self.storage_dir / "custom_templates.json"
            if custom_file.exists():
                with open(custom_file) as f:
                    data = json.load(f)
                    for item in data.get("templates", []):
                        template = PromptTemplate(**item)
                        self._templates[template.template_id] = template
                logger.info(f"Loaded {len(data.get('templates', []))} custom templates")
        except Exception as e:
            logger.warning(f"Error loading custom templates: {e}")

    def _save_custom(self):
        """Save custom templates to disk"""
        try:
            custom_templates = [
                t.to_dict() for t in self._templates.values()
                if not t.is_builtin
            ]
            data = {
                "templates": custom_templates,
                "last_saved": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.storage_dir / "custom_templates.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving custom templates: {e}")

    def add_template(
        self,
        name: str,
        category: str,
        template: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        example_values: Optional[Dict[str, str]] = None,
        author: str = "user",
    ) -> str:
        """
        Add a new custom template.

        Returns:
            Template ID
        """
        # Extract variables from template
        variables = re.findall(r'\{(\w+)\}', template)
        variables = list(set(variables))  # Deduplicate

        # Generate ID
        import uuid
        template_id = f"custom_{uuid.uuid4().hex[:8]}"

        new_template = PromptTemplate(
            template_id=template_id,
            name=name,
            category=category,
            template=template,
            description=description,
            variables=variables,
            tags=tags or [],
            example_values=example_values or {},
            author=author,
            is_builtin=False,
        )

        self._templates[template_id] = new_template
        self._save_custom()

        logger.info(f"Added custom template: {name} ({template_id})")
        return template_id

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID"""
        return self._templates.get(template_id)

    def use_template(
        self,
        template_id: str,
        variables: Dict[str, str],
        success: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Use a template and track usage.

        Args:
            template_id: Template to use
            variables: Variable values
            success: Whether the result was successful (for tracking)

        Returns:
            Rendered prompt or None if template not found
        """
        template = self._templates.get(template_id)
        if not template:
            return None

        # Update usage stats
        template.use_count += 1
        template.last_used = datetime.now(timezone.utc).isoformat()
        if success is not None and success:
            template.success_count += 1

        # Save if custom
        if not template.is_builtin:
            self._save_custom()

        return template.render(variables)

    def record_success(self, template_id: str, success: bool):
        """Record success/failure for a template"""
        template = self._templates.get(template_id)
        if template:
            if success:
                template.success_count += 1
            if not template.is_builtin:
                self._save_custom()

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PromptTemplate]:
        """
        Search for templates.

        Args:
            query: Search in name and description
            category: Filter by category
            tags: Filter by tags (any match)

        Returns:
            List of matching templates
        """
        results = []

        for template in self._templates.values():
            # Filter by category
            if category and template.category != category:
                continue

            # Filter by tags
            if tags and not any(t in template.tags for t in tags):
                continue

            # Filter by query
            if query:
                query_lower = query.lower()
                if not (
                    query_lower in template.name.lower() or
                    query_lower in template.description.lower() or
                    any(query_lower in tag.lower() for tag in template.tags)
                ):
                    continue

            results.append(template)

        # Sort by success rate and usage
        results.sort(key=lambda t: (t.success_rate, t.use_count), reverse=True)
        return results

    def get_by_category(self, category: str) -> List[PromptTemplate]:
        """Get all templates in a category"""
        return self.search(category=category)

    def suggest_template(self, task_description: str) -> Optional[PromptTemplate]:
        """
        Suggest a template based on task description.

        Uses keyword matching to find the best template.
        """
        task_lower = task_description.lower()

        # Category keywords
        category_keywords = {
            "coding": ["write", "create", "implement", "function", "class", "api", "code"],
            "debugging": ["debug", "fix", "error", "bug", "issue", "problem", "crash"],
            "review": ["review", "check", "analyze", "audit", "pr", "pull request"],
            "testing": ["test", "unit test", "coverage", "spec"],
            "architecture": ["design", "architect", "system", "structure", "scale"],
            "refactoring": ["refactor", "improve", "clean", "optimize", "restructure"],
            "documentation": ["document", "docs", "readme", "api docs"],
        }

        # Find best category
        best_category = None
        best_score = 0
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > best_score:
                best_score = score
                best_category = category

        if not best_category:
            return None

        # Get best template in category
        templates = self.get_by_category(best_category)
        if templates:
            return templates[0]  # Return highest rated

        return None

    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(set(t.category for t in self._templates.values()))

    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        total = len(self._templates)
        builtin = sum(1 for t in self._templates.values() if t.is_builtin)
        custom = total - builtin

        total_uses = sum(t.use_count for t in self._templates.values())
        total_successes = sum(t.success_count for t in self._templates.values())

        # By category
        by_category = {}
        for t in self._templates.values():
            if t.category not in by_category:
                by_category[t.category] = {"count": 0, "uses": 0}
            by_category[t.category]["count"] += 1
            by_category[t.category]["uses"] += t.use_count

        # Top templates
        top_templates = sorted(
            self._templates.values(),
            key=lambda t: t.use_count,
            reverse=True
        )[:5]

        return {
            "total_templates": total,
            "builtin_templates": builtin,
            "custom_templates": custom,
            "total_uses": total_uses,
            "total_successes": total_successes,
            "overall_success_rate": round(total_successes / max(total_uses, 1), 3),
            "by_category": by_category,
            "categories": self.get_categories(),
            "top_templates": [
                {"id": t.template_id, "name": t.name, "uses": t.use_count}
                for t in top_templates
            ],
        }

    def list_all(self) -> List[Dict[str, Any]]:
        """List all templates"""
        return [t.to_dict() for t in self._templates.values()]


# Global instance
_prompt_library: Optional[PromptLibrary] = None


def get_prompt_library() -> PromptLibrary:
    """Get or create the global prompt library"""
    global _prompt_library
    if _prompt_library is None:
        _prompt_library = PromptLibrary()
    return _prompt_library
