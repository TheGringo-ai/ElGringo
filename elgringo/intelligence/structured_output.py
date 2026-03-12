"""
Structured Output — JSON Schema enforcement for AI agent responses
===================================================================

Closes the gap with CrewAI/AutoGen's structured output capabilities.
Forces agent responses into validated JSON matching a user-defined schema.

Usage:
    enforcer = StructuredOutputEnforcer()
    result = enforcer.enforce(
        raw_response="Here's a JSON: {\"name\": \"test\"}...",
        schema={"type": "object", "properties": {"name": {"type": "string"}}},
    )
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Common reusable schemas
SCHEMAS = {
    "code_review": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "description": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                    "required": ["severity", "description"],
                },
            },
            "score": {"type": "number", "minimum": 0, "maximum": 10},
        },
        "required": ["summary", "issues", "score"],
    },
    "task_plan": {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step": {"type": "integer"},
                        "action": {"type": "string"},
                        "files": {"type": "array", "items": {"type": "string"}},
                        "depends_on": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["step", "action"],
                },
            },
            "estimated_complexity": {"type": "string", "enum": ["simple", "medium", "complex"]},
        },
        "required": ["goal", "steps"],
    },
    "bug_report": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "root_cause": {"type": "string"},
            "affected_files": {"type": "array", "items": {"type": "string"}},
            "fix_steps": {"type": "array", "items": {"type": "string"}},
            "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["title", "root_cause", "fix_steps"],
    },
    "architecture": {
        "type": "object",
        "properties": {
            "recommendation": {"type": "string"},
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "purpose": {"type": "string"},
                        "technology": {"type": "string"},
                    },
                    "required": ["name", "purpose"],
                },
            },
            "trade_offs": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["recommendation", "components"],
    },
}


@dataclass
class EnforcementResult:
    """Result of structured output enforcement."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_response: str = ""
    errors: List[str] = field(default_factory=list)
    retries: int = 0


class StructuredOutputEnforcer:
    """
    Enforces JSON schema on AI agent responses.

    Strategy:
    1. Try to extract JSON from the raw response
    2. Validate against schema
    3. If invalid, attempt auto-repair (fill defaults, coerce types)
    4. If still invalid, return errors for retry
    """

    def __init__(self):
        self._type_coercers = {
            "string": str,
            "integer": lambda v: int(float(v)) if v is not None else 0,
            "number": lambda v: float(v) if v is not None else 0.0,
            "boolean": lambda v: bool(v) if v is not None else False,
            "array": lambda v: v if isinstance(v, list) else [v] if v else [],
        }

    def enforce(
        self,
        raw_response: str,
        schema: Dict[str, Any],
        auto_repair: bool = True,
    ) -> EnforcementResult:
        """
        Enforce a JSON schema on an AI response.

        Args:
            raw_response: Raw text from AI agent
            schema: JSON Schema to validate against
            auto_repair: Attempt to fix minor issues automatically

        Returns:
            EnforcementResult with validated data or errors
        """
        result = EnforcementResult(success=False, raw_response=raw_response)

        # Step 1: Extract JSON from response
        data = self._extract_json(raw_response)
        if data is None:
            result.errors.append("No valid JSON found in response")
            return result

        # Step 2: Validate against schema
        errors = self._validate(data, schema)
        if not errors:
            result.success = True
            result.data = data
            return result

        # Step 3: Auto-repair if enabled
        if auto_repair:
            repaired = self._auto_repair(data, schema)
            errors = self._validate(repaired, schema)
            if not errors:
                result.success = True
                result.data = repaired
                result.retries = 1
                return result

        result.errors = errors
        return result

    def build_prompt_suffix(self, schema: Dict[str, Any]) -> str:
        """
        Generate a prompt suffix that instructs the AI to return structured output.

        Args:
            schema: JSON Schema

        Returns:
            Prompt text to append
        """
        # Build a simplified example from schema
        example = self._schema_to_example(schema)
        example_json = json.dumps(example, indent=2)

        return (
            "\n\nIMPORTANT: Return your response as valid JSON matching this exact schema.\n"
            "Do NOT include any text before or after the JSON.\n\n"
            f"Expected format:\n```json\n{example_json}\n```"
        )

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a built-in schema by name."""
        return SCHEMAS.get(name)

    def list_schemas(self) -> List[str]:
        """List all built-in schema names."""
        return list(SCHEMAS.keys())

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text, handling markdown code blocks."""
        # Try code block extraction first
        patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'\{[\s\S]*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    candidate = match.group(1) if match.lastindex else match.group(0)
                    return json.loads(candidate.strip())
                except (json.JSONDecodeError, IndexError):
                    continue

        # Direct parse attempt
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None

    def _validate(self, data: Any, schema: Dict[str, Any], path: str = "") -> List[str]:
        """Simple JSON schema validation (no external dependency)."""
        errors = []
        schema_type = schema.get("type")

        if schema_type == "object" and isinstance(data, dict):
            # Check required fields
            for req in schema.get("required", []):
                if req not in data:
                    errors.append(f"{path}.{req}: required field missing")

            # Validate properties
            props = schema.get("properties", {})
            for key, prop_schema in props.items():
                if key in data:
                    errors.extend(self._validate(data[key], prop_schema, f"{path}.{key}"))

        elif schema_type == "array" and isinstance(data, list):
            items_schema = schema.get("items", {})
            for i, item in enumerate(data):
                errors.extend(self._validate(item, items_schema, f"{path}[{i}]"))

        elif schema_type == "string" and not isinstance(data, str):
            errors.append(f"{path}: expected string, got {type(data).__name__}")

        elif schema_type == "integer" and not isinstance(data, int):
            errors.append(f"{path}: expected integer, got {type(data).__name__}")

        elif schema_type == "number" and not isinstance(data, (int, float)):
            errors.append(f"{path}: expected number, got {type(data).__name__}")

        elif schema_type == "boolean" and not isinstance(data, bool):
            errors.append(f"{path}: expected boolean, got {type(data).__name__}")

        # Check enum
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: value '{data}' not in enum {schema['enum']}")

        # Check min/max
        if isinstance(data, (int, float)):
            if "minimum" in schema and data < schema["minimum"]:
                errors.append(f"{path}: {data} < minimum {schema['minimum']}")
            if "maximum" in schema and data > schema["maximum"]:
                errors.append(f"{path}: {data} > maximum {schema['maximum']}")

        return errors

    def _auto_repair(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to auto-repair data to match schema."""
        if schema.get("type") != "object" or not isinstance(data, dict):
            return data

        repaired = dict(data)
        props = schema.get("properties", {})

        # Fill missing required fields with defaults
        for req in schema.get("required", []):
            if req not in repaired:
                prop_schema = props.get(req, {})
                repaired[req] = self._default_for_type(prop_schema)

        # Coerce types
        for key, prop_schema in props.items():
            if key in repaired:
                prop_type = prop_schema.get("type")
                if prop_type and prop_type in self._type_coercers:
                    try:
                        expected_type = {"string": str, "integer": int, "number": (int, float),
                                         "boolean": bool, "array": list, "object": dict}
                        if not isinstance(repaired[key], expected_type.get(prop_type, object)):
                            repaired[key] = self._type_coercers[prop_type](repaired[key])
                    except (ValueError, TypeError):
                        pass

                # Repair nested objects
                if prop_schema.get("type") == "object" and isinstance(repaired[key], dict):
                    repaired[key] = self._auto_repair(repaired[key], prop_schema)

        return repaired

    def _default_for_type(self, schema: Dict[str, Any]) -> Any:
        """Generate a default value for a schema type."""
        defaults = {
            "string": "",
            "integer": 0,
            "number": 0.0,
            "boolean": False,
            "array": [],
            "object": {},
        }
        return defaults.get(schema.get("type"), "")

    def _schema_to_example(self, schema: Dict[str, Any]) -> Any:
        """Generate an example value from a schema."""
        schema_type = schema.get("type")

        if schema_type == "object":
            obj = {}
            for key, prop in schema.get("properties", {}).items():
                obj[key] = self._schema_to_example(prop)
            return obj
        elif schema_type == "array":
            return [self._schema_to_example(schema.get("items", {"type": "string"}))]
        elif schema_type == "string":
            if "enum" in schema:
                return schema["enum"][0]
            return "..."
        elif schema_type == "integer":
            return 0
        elif schema_type == "number":
            return 0.0
        elif schema_type == "boolean":
            return True
        return "..."


def get_structured_enforcer() -> StructuredOutputEnforcer:
    """Get singleton enforcer instance."""
    if not hasattr(get_structured_enforcer, "_instance"):
        get_structured_enforcer._instance = StructuredOutputEnforcer()
    return get_structured_enforcer._instance
