"""
Structured Tool Framework
=========================

Provides a type-safe, validated tool system for AI agents.

Features:
- JSON Schema-based tool definitions
- Parameter validation
- Async execution support
- Tool registry with discovery
- Automatic documentation generation
- Rate limiting and permissions
"""

import asyncio
import inspect
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: List[Any] = None  # Allowed values
    items_type: ParameterType = None  # For array types
    properties: Dict[str, "ToolParameter"] = None  # For object types

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema = {
            "type": self.type.value,
            "description": self.description,
        }

        if self.enum:
            schema["enum"] = self.enum

        if self.type == ParameterType.ARRAY and self.items_type:
            schema["items"] = {"type": self.items_type.value}

        if self.type == ParameterType.OBJECT and self.properties:
            schema["properties"] = {
                name: param.to_json_schema()
                for name, param in self.properties.items()
            }

        if self.default is not None:
            schema["default"] = self.default

        return schema


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_string(self) -> str:
        """Convert result to string for LLM consumption."""
        if self.success:
            if isinstance(self.output, (dict, list)):
                return json.dumps(self.output, indent=2)
            return str(self.output)
        return f"Error: {self.error}"


@dataclass
class Tool:
    """
    A tool that can be called by AI agents.

    Tools are the primary way agents interact with the external world.
    Each tool has:
    - A unique name
    - A description for the LLM
    - Typed parameters with validation
    - An execution function (sync or async)
    """
    name: str
    description: str
    parameters: List[ToolParameter]
    function: Callable
    category: str = "general"
    requires_confirmation: bool = False
    rate_limit: Optional[int] = None  # Calls per minute
    examples: List[Dict[str, Any]] = field(default_factory=list)

    _call_count: int = field(default=0, repr=False)
    _last_call: Optional[datetime] = field(default=None, repr=False)

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Convert to Anthropic tool use format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against schema. Returns list of errors."""
        errors = []

        param_map = {p.name: p for p in self.parameters}

        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in params:
                if param.default is None:
                    errors.append(f"Missing required parameter: {param.name}")

        # Validate provided parameters
        for name, value in params.items():
            if name not in param_map:
                errors.append(f"Unknown parameter: {name}")
                continue

            param = param_map[name]

            # Type checking
            type_valid = self._check_type(value, param.type)
            if not type_valid:
                errors.append(
                    f"Parameter '{name}' has wrong type. "
                    f"Expected {param.type.value}, got {type(value).__name__}"
                )

            # Enum checking
            if param.enum and value not in param.enum:
                errors.append(
                    f"Parameter '{name}' must be one of: {param.enum}"
                )

        return errors

    def _check_type(self, value: Any, expected: ParameterType) -> bool:
        """Check if value matches expected type."""
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.NUMBER: (int, float),
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: list,
            ParameterType.OBJECT: dict,
        }
        expected_type = type_map.get(expected)
        if expected_type:
            return isinstance(value, expected_type)
        return True

    async def execute(self, **params) -> ToolResult:
        """Execute the tool with given parameters."""
        import time
        start_time = time.time()

        # Validate parameters
        errors = self.validate_params(params)
        if errors:
            return ToolResult(
                success=False,
                output=None,
                error="; ".join(errors),
            )

        # Apply defaults
        for param in self.parameters:
            if param.name not in params and param.default is not None:
                params[param.name] = param.default

        try:
            # Execute function (handle both sync and async)
            if asyncio.iscoroutinefunction(self.function):
                result = await self.function(**params)
            else:
                result = self.function(**params)

            execution_time = time.time() - start_time
            self._call_count += 1
            self._last_call = datetime.now(timezone.utc)

            return ToolResult(
                success=True,
                output=result,
                execution_time=execution_time,
                metadata={"call_count": self._call_count},
            )

        except Exception as e:
            logger.error(f"Tool '{self.name}' execution error: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    def __call__(self, **params) -> ToolResult:
        """Synchronous call wrapper."""
        return asyncio.run(self.execute(**params))


class ToolRegistry:
    """
    Central registry for all available tools.

    Manages tool discovery, validation, and execution.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool

        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)

        logger.debug(f"Registered tool: {tool.name} [{tool.category}]")

    def unregister(self, name: str):
        """Unregister a tool."""
        if name in self._tools:
            tool = self._tools[name]
            del self._tools[name]
            if tool.category in self._categories:
                self._categories[tool.category].remove(name)

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: str = None) -> List[str]:
        """List all tools, optionally filtered by category."""
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())

    def list_categories(self) -> List[str]:
        """List all tool categories."""
        return list(self._categories.keys())

    def get_schemas(
        self,
        format: str = "openai",
        tools: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get tool schemas in specified format.

        Args:
            format: "openai" or "anthropic"
            tools: Specific tools to include (None for all)

        Returns:
            List of tool schemas
        """
        schemas = []
        tool_names = tools or self._tools.keys()

        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                if format == "openai":
                    schemas.append(tool.to_openai_schema())
                elif format == "anthropic":
                    schemas.append(tool.to_anthropic_schema())

        return schemas

    async def execute(self, name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {name}",
            )
        return await tool.execute(**params)

    def generate_documentation(self) -> str:
        """Generate markdown documentation for all tools."""
        lines = ["# Available Tools\n"]

        for category in sorted(self._categories.keys()):
            lines.append(f"\n## {category.title()}\n")

            for name in sorted(self._categories[category]):
                tool = self._tools[name]
                lines.append(f"\n### `{tool.name}`\n")
                lines.append(f"{tool.description}\n")

                if tool.parameters:
                    lines.append("\n**Parameters:**\n")
                    for param in tool.parameters:
                        req = "required" if param.required else "optional"
                        lines.append(f"- `{param.name}` ({param.type.value}, {req}): {param.description}")

                if tool.examples:
                    lines.append("\n**Examples:**\n")
                    for ex in tool.examples:
                        lines.append(f"```json\n{json.dumps(ex, indent=2)}\n```")

        return "\n".join(lines)


def create_tool(
    name: str = None,
    description: str = None,
    category: str = "general",
    requires_confirmation: bool = False,
) -> Callable:
    """
    Decorator to create a tool from a function.

    Usage:
        @create_tool(name="search_code", description="Search codebase")
        def search_code(query: str, limit: int = 10) -> List[str]:
            '''Search for code matching query.'''
            ...
    """
    def decorator(func: Callable) -> Tool:
        # Get function signature
        sig = inspect.signature(func)
        doc = func.__doc__ or ""

        # Build parameters from type hints
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Determine type
            annotation = param.annotation
            param_type = ParameterType.STRING  # Default

            if annotation != inspect.Parameter.empty:
                if annotation == str:
                    param_type = ParameterType.STRING
                elif annotation == int:
                    param_type = ParameterType.INTEGER
                elif annotation in (float, int, float):
                    param_type = ParameterType.NUMBER
                elif annotation == bool:
                    param_type = ParameterType.BOOLEAN
                elif annotation == list or getattr(annotation, "__origin__", None) == list:
                    param_type = ParameterType.ARRAY
                elif annotation == dict:
                    param_type = ParameterType.OBJECT

            # Check if required (has default or not)
            required = param.default == inspect.Parameter.empty
            default = None if required else param.default

            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter: {param_name}",  # Could parse from docstring
                required=required,
                default=default,
            ))

        tool = Tool(
            name=name or func.__name__,
            description=description or doc.strip().split("\n")[0] if doc else func.__name__,
            parameters=parameters,
            function=func,
            category=category,
            requires_confirmation=requires_confirmation,
        )

        return tool

    return decorator


# Global registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _register_builtin_tools(_tool_registry)
    return _tool_registry


def _register_builtin_tools(registry: ToolRegistry):
    """Register built-in tools."""

    # File operations
    @create_tool(
        name="read_file",
        description="Read the contents of a file",
        category="filesystem",
    )
    def read_file(path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    @create_tool(
        name="write_file",
        description="Write content to a file",
        category="filesystem",
        requires_confirmation=True,
    )
    def write_file(path: str, content: str) -> str:
        with open(path, "w") as f:
            f.write(content)
        return f"Written {len(content)} bytes to {path}"

    @create_tool(
        name="list_directory",
        description="List files and directories in a path",
        category="filesystem",
    )
    def list_directory(path: str = ".") -> List[str]:
        import os
        return os.listdir(path)

    # Code execution
    @create_tool(
        name="run_python",
        description="Execute Python code and return the result",
        category="code",
        requires_confirmation=True,
    )
    def run_python(code: str) -> str:
        import io
        from contextlib import redirect_stdout, redirect_stderr

        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                _safe_builtins = {
                    k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k)
                    for k in (
                        "print", "len", "range", "enumerate", "zip", "map", "filter",
                        "sorted", "reversed", "list", "dict", "set", "tuple", "str",
                        "int", "float", "bool", "type", "isinstance", "hasattr",
                        "getattr", "setattr", "repr", "abs", "round", "min", "max",
                        "sum", "any", "all", "Exception", "ValueError", "TypeError",
                    )
                    if (isinstance(__builtins__, dict) and k in __builtins__)
                    or (not isinstance(__builtins__, dict) and hasattr(__builtins__, k))
                }
                exec(code, {"__builtins__": _safe_builtins})
            return stdout.getvalue() or "Code executed successfully"
        except Exception as e:
            return f"Error: {e}\n{stderr.getvalue()}"

    @create_tool(
        name="run_shell",
        description="Execute a shell command",
        category="code",
        requires_confirmation=True,
    )
    def run_shell(command: str, timeout: int = 30) -> str:
        import shlex
        import subprocess
        try:
            cmd_args = shlex.split(command)
            result = subprocess.run(
                cmd_args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nStderr: {result.stderr}"
            return output or "Command completed"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"

    # Search
    @create_tool(
        name="search_files",
        description="Search for files matching a pattern",
        category="search",
    )
    def search_files(pattern: str, path: str = ".") -> List[str]:
        import glob
        return glob.glob(f"{path}/**/{pattern}", recursive=True)

    @create_tool(
        name="search_content",
        description="Search for content in files using grep",
        category="search",
    )
    def search_content(query: str, path: str = ".", file_pattern: str = "*") -> List[str]:
        import subprocess
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", query, "--include", file_pattern, path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip().split("\n") if result.stdout else []
        except Exception:
            return []

    # Web
    @create_tool(
        name="fetch_url",
        description="Fetch content from a URL",
        category="web",
    )
    async def fetch_url(url: str) -> str:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                return await response.text()

    # Web search
    @create_tool(
        name="web_search",
        description="Search the web for current information. Returns titles, URLs, and snippets.",
        category="web",
    )
    async def web_search(query: str, max_results: int = 5) -> List[Dict]:
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            results = []
            for r in DDGS().text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            return results
        except ImportError:
            return [{"error": "ddgs not installed: pip install ddgs"}]
        except Exception as e:
            return [{"error": str(e)}]

    # Register all tools
    for tool in [read_file, write_file, list_directory, run_python,
                 run_shell, search_files, search_content, fetch_url, web_search]:
        registry.register(tool)
