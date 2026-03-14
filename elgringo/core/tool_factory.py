"""
Dynamic Tool Factory — Build new MCP tools at runtime
=======================================================

Create custom tools from natural language descriptions. Each tool is a
templated collaboration call — it constructs a prompt from parameters
and sends it to the collaborate API with a specific mode and context.

This is sandboxed by design: tools can only call the collaborate API,
not execute arbitrary code.

Usage:
    factory = get_tool_factory()
    factory.create_tool(
        name="analyze_api_spec",
        description="Analyze an API spec for design issues",
        parameters=[{"name": "spec", "type": "string", "description": "The API spec"}],
        prompt_template="Analyze this API spec for design issues:\n${spec}",
        mode="expert_panel",
    )
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

TOOLS_DIR = Path.home() / ".ai-dev-team" / "custom_tools"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DynamicToolDef:
    """A dynamically created tool definition."""
    name: str
    description: str
    parameters: List[Dict[str, str]]  # [{"name": ..., "type": ..., "description": ...}]
    prompt_template: str              # Uses ${param_name} for substitution
    mode: str = "parallel"
    system_context: str = ""          # Extra context prepended to prompt
    team: str = ""                    # Optional: run with a specific team
    created: str = ""

    def __post_init__(self):
        if not self.created:
            from datetime import datetime, timezone
            self.created = datetime.now(timezone.utc).isoformat()


class ToolFactory:
    """Creates, persists, and registers dynamic MCP tools."""

    def __init__(self):
        self._tools: Dict[str, DynamicToolDef] = {}
        self._load_all()

    def _load_all(self):
        """Load all tool definitions from disk."""
        for path in TOOLS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                tool_def = DynamicToolDef(**data)
                self._tools[tool_def.name] = tool_def
            except Exception as e:
                logger.warning(f"Failed to load tool {path.name}: {e}")
        if self._tools:
            logger.info(f"Loaded {len(self._tools)} custom tool definitions")

    def _save(self, tool_def: DynamicToolDef):
        """Persist a tool definition to disk."""
        path = TOOLS_DIR / f"{tool_def.name}.json"
        path.write_text(json.dumps(asdict(tool_def), indent=2))

    def create_tool(
        self,
        name: str,
        description: str,
        parameters: List[Dict[str, str]],
        prompt_template: str,
        mode: str = "parallel",
        system_context: str = "",
        team: str = "",
    ) -> DynamicToolDef:
        """Create and persist a new dynamic tool."""
        # Sanitize name for safety
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)

        tool_def = DynamicToolDef(
            name=safe_name,
            description=description,
            parameters=parameters,
            prompt_template=prompt_template,
            mode=mode,
            system_context=system_context,
            team=team,
        )
        self._tools[safe_name] = tool_def
        self._save(tool_def)
        logger.info(f"Created dynamic tool: {safe_name}")
        return tool_def

    def get_tool(self, name: str) -> Optional[DynamicToolDef]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all dynamic tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": [p["name"] for p in t.parameters],
                "mode": t.mode,
                "team": t.team or "(default)",
                "created": t.created,
            }
            for t in self._tools.values()
        ]

    def delete_tool(self, name: str):
        """Delete a dynamic tool."""
        self._tools.pop(name, None)
        path = TOOLS_DIR / f"{name}.json"
        if path.exists():
            path.unlink()

    def build_executor(self, tool_def: DynamicToolDef, api_fn: Callable) -> Callable:
        """Build an executor function for a dynamic tool.

        The executor substitutes parameters into the prompt template
        and calls the collaborate API. Fully sandboxed.

        Args:
            tool_def: The tool definition
            api_fn: The _api() function from mcp_server.py
        """
        def executor(**kwargs) -> str:
            # Substitute parameters into prompt template
            prompt = tool_def.prompt_template
            for param in tool_def.parameters:
                key = param["name"]
                value = str(kwargs.get(key, ""))
                prompt = prompt.replace(f"${{{key}}}", value)

            # Build collaborate request
            body: Dict[str, Any] = {"prompt": prompt, "mode": tool_def.mode}
            if tool_def.system_context:
                body["context"] = tool_def.system_context
            body["budget"] = "standard"

            # Call collaborate API
            result = api_fn("POST", "/v1/collaborate", body)

            if isinstance(result, dict) and "error" in result:
                return f"Error: {result['error']}"

            # Format result
            answer = result.get("answer", "") if isinstance(result, dict) else str(result)
            agents = ", ".join(result.get("agents_used", [])) if isinstance(result, dict) else ""
            confidence = result.get("confidence", 0) if isinstance(result, dict) else 0

            return f"[Tool: {tool_def.name} | Agents: {agents} | Confidence: {confidence:.0%}]\n\n{answer}"

        executor.__name__ = f"custom_{tool_def.name}"
        executor.__doc__ = tool_def.description
        return executor

    def register_all_on_mcp(self, mcp_instance, api_fn: Callable):
        """Register all persisted dynamic tools as MCP tools.

        Called once at server startup.
        """
        count = 0
        for tool_def in self._tools.values():
            if self._register_single(tool_def, mcp_instance, api_fn):
                count += 1
        if count:
            logger.info(f"Registered {count} custom dynamic tools on MCP")

    def _register_single(self, tool_def: DynamicToolDef, mcp_instance, api_fn: Callable) -> bool:
        """Register a single dynamic tool on MCP."""
        try:
            executor = self.build_executor(tool_def, api_fn)

            # Build parameter annotations for MCP introspection
            # We create a simple wrapper with string params
            param_names = [p["name"] for p in tool_def.parameters]
            param_descs = {p["name"]: p.get("description", "") for p in tool_def.parameters}

            # Build docstring with Args section for MCP
            doc_parts = [tool_def.description, "", "Args:"]
            for p in tool_def.parameters:
                doc_parts.append(f"    {p['name']}: {p.get('description', p['name'])}")

            # Create a wrapper that accepts keyword string args
            def make_wrapper(exec_fn, params):
                def wrapper(**kwargs) -> str:
                    return exec_fn(**kwargs)
                wrapper.__name__ = f"custom_{tool_def.name}"
                wrapper.__doc__ = "\n".join(doc_parts)
                # Set annotations for FastMCP parameter discovery
                wrapper.__annotations__ = {p: str for p in params}
                wrapper.__annotations__["return"] = str
                return wrapper

            wrapper = make_wrapper(executor, param_names)
            mcp_instance.tool()(wrapper)
            return True
        except Exception as e:
            logger.error(f"Failed to register dynamic tool {tool_def.name}: {e}")
            return False

    def register_new(self, tool_def: DynamicToolDef, mcp_instance, api_fn: Callable) -> bool:
        """Register a newly created tool at runtime (hot-register)."""
        return self._register_single(tool_def, mcp_instance, api_fn)


# Singleton
_factory: Optional[ToolFactory] = None


def get_tool_factory() -> ToolFactory:
    """Get the global tool factory."""
    global _factory
    if _factory is None:
        _factory = ToolFactory()
    return _factory
