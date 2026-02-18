"""
Tool Manager - Extracted from AIDevTeam orchestrator
=====================================================

Handles tool access, permissions, agentic tool execution,
and tool call parsing/formatting.
"""

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from ..security import validate_tool_call, get_security_validator

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages tool access, permissions, and agentic tool execution.

    Extracted from AIDevTeam to reduce orchestrator complexity.
    Takes a reference to the orchestrator for access to agents, tools, and learning.
    """

    def __init__(self, orchestrator):
        self._orchestrator = orchestrator

    @property
    def _tools(self):
        return self._orchestrator._tools

    @property
    def _permission_manager(self):
        return self._orchestrator._permission_manager

    @property
    def _auto_learner(self):
        return self._orchestrator._auto_learner

    @property
    def _task_router(self):
        return self._orchestrator._task_router

    @property
    def agents(self):
        return self._orchestrator.agents

    # =================
    # Tool Access Methods
    # =================

    def get_tools(self) -> Dict[str, Any]:
        """Get all available tools"""
        return self._tools

    def get_tool_capabilities(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get capabilities of all registered tools.

        Returns:
            Dict mapping tool names to their operations
        """
        capabilities = {}
        for name, tool in self._tools.items():
            capabilities[name] = tool.get_capabilities()
        return capabilities

    async def execute_tool(
        self,
        tool_name: str,
        operation: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool operation.

        Args:
            tool_name: Name of tool (filesystem, browser, shell)
            operation: Operation to perform
            **kwargs: Operation parameters

        Returns:
            Dict with success, output, error keys
        """
        # Security validation before execution
        security_result = validate_tool_call({
            "tool": tool_name,
            "operation": operation,
            "params": kwargs
        })

        if not security_result.is_valid:
            logger.warning(
                f"SECURITY BLOCKED: {tool_name}.{operation} - "
                f"Threat: {security_result.threat_level.name}, Issues: {security_result.issues}"
            )
            return {
                "success": False,
                "output": None,
                "error": f"Security validation failed: {'; '.join(security_result.issues)}",
                "threat_level": security_result.threat_level.name,
            }

        if tool_name not in self._tools:
            return {
                "success": False,
                "output": None,
                "error": f"Unknown tool: {tool_name}. Available: {list(self._tools.keys())}"
            }

        tool = self._tools[tool_name]
        result = await tool.execute(operation, **kwargs)

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata,
            "execution_time": result.execution_time,
        }

    def grant_tool_permission(
        self,
        tool_name: str,
        operation: str,
        level: str = "session"
    ):
        """
        Grant permission for a tool operation.

        Args:
            tool_name: Tool name
            operation: Operation to grant
            level: "session" (temporary) or "always" (persistent)
        """
        from ..tools.base import PermissionLevel

        perm_level = PermissionLevel.SESSION if level == "session" else PermissionLevel.ALWAYS
        self._permission_manager.grant_permission(tool_name, operation, perm_level)
        logger.info(f"Granted {level} permission for {tool_name}.{operation}")

    def revoke_tool_permission(self, tool_name: str, operation: str):
        """Revoke permission for a tool operation"""
        self._permission_manager.revoke_permission(tool_name, operation)
        logger.info(f"Revoked permission for {tool_name}.{operation}")

    def list_tool_permissions(self) -> List[Dict[str, Any]]:
        """List all granted tool permissions"""
        permissions = self._permission_manager.get_all_permissions()
        return [
            {
                "tool": p.tool_name,
                "operation": p.operation,
                "level": p.level.name,
                "granted_at": p.granted_at,
            }
            for p in permissions
        ]

    # =================
    # Agentic Tool Execution
    # =================

    async def agentic_task(
        self,
        task: str,
        allowed_tools: Optional[List[str]] = None,
        max_tool_calls: int = 10,
        agent_name: Optional[str] = None,
    ):
        """
        Execute a task where the AI agent can autonomously use tools.

        The agent will analyze the task, decide which tools to use,
        execute them, and synthesize results.

        Args:
            task: Task description
            allowed_tools: List of allowed tool names (default: all)
            max_tool_calls: Maximum tool calls allowed
            agent_name: Specific agent to use (auto-select if None)

        Returns:
            CollaborationResult with task outcome
        """
        from ..orchestrator import CollaborationResult

        start_time = time.time()
        task_id = str(uuid.uuid4())[:8]
        collaboration_log = []

        # Select agent
        if agent_name and agent_name in self.agents:
            agent = self.agents[agent_name]
        else:
            # Use task router to select best agent
            classification = self._task_router.classify(task, "")
            agent_name = classification.recommended_agents[0] if classification.recommended_agents else None
            agent = self.agents.get(agent_name) if agent_name else list(self.agents.values())[0]

        collaboration_log.append(f"Selected agent: {agent.name}")

        # Build tool context
        available_tools = allowed_tools or list(self._tools.keys())
        tool_info = self._build_tool_context(available_tools)

        # Initial prompt with tool capabilities
        agentic_prompt = f"""You are an AI agent with DIRECT ACCESS to real tools. You MUST use these tools to complete the task.
DO NOT write code to solve the problem - USE THE TOOLS DIRECTLY.

AVAILABLE TOOLS (you MUST use these):
{tool_info}

TASK: {task}

IMPORTANT: To use a tool, output EXACTLY this format (one per line):
TOOL_CALL: filesystem.list(path=".", pattern="*.py")
TOOL_CALL: filesystem.read(path="./file.py")
TOOL_CALL: shell.run_safe(command="pwd")

Start by making tool calls to gather information. Output your tool calls now:"""

        responses = []
        tool_calls_made = 0
        tool_results = []

        # Initial agent response
        response = await agent.generate_response(agentic_prompt)
        responses.append(response)
        collaboration_log.append("Agent initial response received")

        # Parse and execute tool calls
        while tool_calls_made < max_tool_calls:
            tool_calls = self._parse_tool_calls(response.content)

            if not tool_calls:
                break  # No more tool calls

            for call in tool_calls:
                if tool_calls_made >= max_tool_calls:
                    break

                tool_name_call = call.get("tool")
                operation = call.get("operation")
                params = call.get("params", {})

                if tool_name_call not in available_tools:
                    tool_results.append({
                        "call": call,
                        "result": {"success": False, "error": f"Tool {tool_name_call} not allowed"}
                    })
                    continue

                collaboration_log.append(f"Executing: {tool_name_call}.{operation}")
                result = await self.execute_tool(tool_name_call, operation, **params)
                tool_results.append({"call": call, "result": result})
                tool_calls_made += 1

            # If we made tool calls, send results back to agent
            if tool_results:
                results_str = self._format_tool_results(tool_results[-len(tool_calls):])
                followup_prompt = f"""Tool execution results:
{results_str}

Continue with the task. Make more tool calls if needed, or provide your final answer."""

                response = await agent.generate_response(followup_prompt, context=response.content)
                responses.append(response)

        # Get final answer
        final_answer = response.content

        # Record in auto-learner
        if self._auto_learner:
            await self._auto_learner.capture_interaction(
                user_prompt=task,
                ai_responses=[{"agent": agent.name, "content": final_answer}],
                outcome="completed",
                task_type="agentic_task",
                metadata={
                    "tools_used": [tr["call"]["tool"] for tr in tool_results],
                    "tool_calls_count": tool_calls_made,
                }
            )

        return CollaborationResult(
            task_id=task_id,
            success=True,
            final_answer=final_answer,
            agent_responses=responses,
            collaboration_log=collaboration_log,
            total_time=time.time() - start_time,
            confidence_score=response.confidence if hasattr(response, 'confidence') else 0.8,
            participating_agents=[agent.name],
            metadata={
                "tool_calls": tool_calls_made,
                "tool_results": tool_results,
                "mode": "agentic",
            }
        )

    def _build_tool_context(self, allowed_tools: List[str]) -> str:
        """Build tool context string for agent prompt"""
        lines = []
        for tool_name in allowed_tools:
            if tool_name in self._tools:
                tool = self._tools[tool_name]
                lines.append(f"\n{tool_name.upper()}:")
                for cap in tool.get_capabilities():
                    lines.append(f"  - {cap['operation']}: {cap['description']}")
        return "\n".join(lines)

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from agent response with security validation"""
        calls = []
        security_validator = get_security_validator()

        # Pattern: TOOL_CALL: tool.operation(param=value, ...)
        pattern = r'TOOL_CALL:\s*(\w+)\.(\w+)\(([^)]*)\)'
        matches = re.findall(pattern, content)

        for tool, operation, params_str in matches:
            params = {}
            if params_str.strip():
                # Parse params like: param1=value1, param2="value2"
                param_pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))'
                for match in re.findall(param_pattern, params_str):
                    key = match[0]
                    value = match[1] or match[2] or match[3]
                    # Try to convert to appropriate type
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    params[key] = value

            # Build the call dict
            call = {
                "tool": tool,
                "operation": operation,
                "params": params,
            }

            # Security validation at parse time
            validation = security_validator.validate_tool_call(call)
            if validation.is_valid:
                calls.append(call)
            else:
                # Log blocked calls but don't include them
                logger.warning(
                    f"SECURITY: Blocked parsed tool call {tool}.{operation} - "
                    f"Threat: {validation.threat_level.name}, Issues: {validation.issues}"
                )

        return calls

    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Format tool results for agent"""
        lines = []
        for tr in tool_results:
            call = tr["call"]
            result = tr["result"]
            lines.append(f"\n{call['tool']}.{call['operation']}:")
            if result["success"]:
                output = result.get("output", "")
                if isinstance(output, dict):
                    output = json.dumps(output, indent=2)[:1000]
                elif isinstance(output, list):
                    output = json.dumps(output[:10], indent=2)[:1000]
                else:
                    output = str(output)[:1000]
                lines.append(f"  SUCCESS: {output}")
            else:
                lines.append(f"  ERROR: {result.get('error', 'Unknown error')}")
        return "\n".join(lines)
