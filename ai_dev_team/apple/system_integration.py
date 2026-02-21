"""
Apple System Integration
========================

Deep integration with macOS and Apple Intelligence features:
- Writing Tools API (system-wide AI writing assistance)
- Siri Intent handling
- Spotlight integration
- Menu bar quick access
- Notification Center integration
- Focus modes awareness
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WritingToolAction(Enum):
    """Apple Writing Tools actions."""
    PROOFREAD = "proofread"
    REWRITE = "rewrite"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CONCISE = "concise"
    SUMMARY = "summary"
    KEY_POINTS = "key_points"
    LIST = "list"
    TABLE = "table"


@dataclass
class WritingToolsResult:
    """Result from Writing Tools processing."""
    original: str
    transformed: str
    action: WritingToolAction
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class SiriIntent:
    """Represents a Siri intent for AI Team."""
    name: str
    description: str
    parameters: Dict[str, str]
    handler: Optional[Callable] = None
    example_phrases: List[str] = field(default_factory=list)


class WritingToolsProvider:
    """
    Provides Apple Writing Tools functionality using AI Team.

    Writing Tools is Apple's system-wide AI writing assistance
    available in macOS Sequoia and iOS 18. This provider enables
    AI Team to power these features.

    Features:
    - Proofread: Fix grammar and spelling
    - Rewrite: Transform tone and style
    - Summarize: Create summaries
    - Key Points: Extract main points
    - List/Table: Convert to structured format
    """

    def __init__(self):
        self._orchestrator = None

    async def _get_orchestrator(self):
        """Lazy load orchestrator."""
        if self._orchestrator is None:
            try:
                from ..orchestrator import AIDevTeam
                self._orchestrator = AIDevTeam(
                    project_name="writing-tools",
                    enable_memory=False,  # Stateless for writing tools
                )
            except Exception as e:
                logger.error(f"Failed to initialize orchestrator: {e}")
        return self._orchestrator

    async def process(
        self,
        text: str,
        action: WritingToolAction,
        context: Optional[str] = None,
    ) -> WritingToolsResult:
        """
        Process text with a Writing Tools action.

        Args:
            text: Input text to transform
            action: Writing Tools action to apply
            context: Optional context about the text

        Returns:
            WritingToolsResult with transformed text
        """
        prompts = {
            WritingToolAction.PROOFREAD: (
                "Proofread this text. Fix any grammar, spelling, and punctuation errors. "
                "Keep the original meaning and tone. Only return the corrected text:\n\n"
            ),
            WritingToolAction.REWRITE: (
                "Rewrite this text to improve clarity and flow while keeping the same meaning. "
                "Only return the rewritten text:\n\n"
            ),
            WritingToolAction.FRIENDLY: (
                "Rewrite this text in a friendly, casual tone. "
                "Only return the rewritten text:\n\n"
            ),
            WritingToolAction.PROFESSIONAL: (
                "Rewrite this text in a professional, formal tone. "
                "Only return the rewritten text:\n\n"
            ),
            WritingToolAction.CONCISE: (
                "Rewrite this text to be more concise while preserving key information. "
                "Only return the shortened text:\n\n"
            ),
            WritingToolAction.SUMMARY: (
                "Write a brief summary of this text in 2-3 sentences. "
                "Only return the summary:\n\n"
            ),
            WritingToolAction.KEY_POINTS: (
                "Extract the key points from this text as a bulleted list. "
                "Only return the bullet points:\n\n"
            ),
            WritingToolAction.LIST: (
                "Convert this text into a well-organized bulleted list. "
                "Only return the list:\n\n"
            ),
            WritingToolAction.TABLE: (
                "Convert this text into a markdown table if it contains tabular data. "
                "Only return the table:\n\n"
            ),
        }

        prompt = prompts.get(action, prompts[WritingToolAction.REWRITE])
        full_prompt = prompt + text

        if context:
            full_prompt = f"Context: {context}\n\n{full_prompt}"

        try:
            orchestrator = await self._get_orchestrator()
            if orchestrator is None:
                return WritingToolsResult(
                    original=text,
                    transformed=text,
                    action=action,
                    confidence=0,
                )

            result = await orchestrator.collaborate(full_prompt)

            transformed = result.final_answer if hasattr(result, 'final_answer') else str(result)

            return WritingToolsResult(
                original=text,
                transformed=transformed.strip(),
                action=action,
                confidence=result.confidence_score if hasattr(result, 'confidence_score') else 1.0,
            )

        except Exception as e:
            logger.error(f"Writing Tools error: {e}")
            return WritingToolsResult(
                original=text,
                transformed=text,
                action=action,
                confidence=0,
            )

    async def proofread(self, text: str) -> str:
        """Proofread text for grammar and spelling."""
        result = await self.process(text, WritingToolAction.PROOFREAD)
        return result.transformed

    async def rewrite(self, text: str, tone: str = "neutral") -> str:
        """Rewrite text with optional tone adjustment."""
        tone_map = {
            "friendly": WritingToolAction.FRIENDLY,
            "professional": WritingToolAction.PROFESSIONAL,
            "concise": WritingToolAction.CONCISE,
            "neutral": WritingToolAction.REWRITE,
        }
        action = tone_map.get(tone.lower(), WritingToolAction.REWRITE)
        result = await self.process(text, action)
        return result.transformed

    async def summarize(self, text: str) -> str:
        """Create a summary of the text."""
        result = await self.process(text, WritingToolAction.SUMMARY)
        return result.transformed

    async def key_points(self, text: str) -> List[str]:
        """Extract key points from text."""
        result = await self.process(text, WritingToolAction.KEY_POINTS)
        # Parse bullet points
        points = []
        for line in result.transformed.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "• ", "* ", "· ")):
                points.append(line[2:].strip())
            elif line:
                points.append(line)
        return points


class SiriIntentHandler:
    """
    Handles Siri intents for AI Team.

    Enables voice-activated AI assistance through Siri.
    Supports custom intents for common development tasks.
    """

    # Built-in intents
    INTENTS = {
        "AskAITeam": SiriIntent(
            name="AskAITeam",
            description="Ask the AI development team a question",
            parameters={"query": "The question to ask"},
            example_phrases=[
                "Ask AI Team",
                "Ask my AI team",
                "Ask the development team",
            ],
        ),
        "ReviewCode": SiriIntent(
            name="ReviewCode",
            description="Request a code review",
            parameters={"code": "Code from clipboard"},
            example_phrases=[
                "Review my code",
                "Check this code",
                "Code review",
            ],
        ),
        "DebugError": SiriIntent(
            name="DebugError",
            description="Get help debugging an error",
            parameters={"error": "Error message"},
            example_phrases=[
                "Debug this error",
                "Help me fix this error",
                "What does this error mean",
            ],
        ),
        "GenerateCode": SiriIntent(
            name="GenerateCode",
            description="Generate code from description",
            parameters={"description": "What to generate"},
            example_phrases=[
                "Generate code for",
                "Write code that",
                "Create a function",
            ],
        ),
        "ExplainCode": SiriIntent(
            name="ExplainCode",
            description="Explain code from clipboard",
            parameters={"code": "Code to explain"},
            example_phrases=[
                "Explain this code",
                "What does this code do",
                "How does this work",
            ],
        ),
    }

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._orchestrator = None

    async def _get_orchestrator(self):
        """Lazy load orchestrator."""
        if self._orchestrator is None:
            from ..orchestrator import AIDevTeam
            self._orchestrator = AIDevTeam(project_name="siri-intents")
        return self._orchestrator

    def register_handler(self, intent_name: str, handler: Callable):
        """Register a custom handler for an intent."""
        self._handlers[intent_name] = handler

    async def handle_intent(
        self,
        intent_name: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        Handle a Siri intent.

        Args:
            intent_name: Name of the intent
            parameters: Intent parameters

        Returns:
            Response text for Siri to speak
        """
        # Check for custom handler
        if intent_name in self._handlers:
            return await self._handlers[intent_name](parameters)

        # Default handling
        orchestrator = await self._get_orchestrator()

        if intent_name == "AskAITeam":
            query = parameters.get("query", "")
            result = await orchestrator.collaborate(query)
            return result.final_answer if hasattr(result, 'final_answer') else str(result)

        elif intent_name == "ReviewCode":
            code = parameters.get("code", "")
            result = await orchestrator.collaborate(
                f"Review this code and provide feedback:\n\n{code}"
            )
            return result.final_answer if hasattr(result, 'final_answer') else str(result)

        elif intent_name == "DebugError":
            error = parameters.get("error", "")
            result = await orchestrator.collaborate(
                f"Help me debug this error:\n\n{error}"
            )
            return result.final_answer if hasattr(result, 'final_answer') else str(result)

        elif intent_name == "GenerateCode":
            description = parameters.get("description", "")
            result = await orchestrator.collaborate(
                f"Generate code for: {description}"
            )
            return result.final_answer if hasattr(result, 'final_answer') else str(result)

        elif intent_name == "ExplainCode":
            code = parameters.get("code", "")
            result = await orchestrator.collaborate(
                f"Explain this code:\n\n{code}"
            )
            return result.final_answer if hasattr(result, 'final_answer') else str(result)

        return "I don't know how to handle that intent."

    def generate_intents_definition(self) -> Dict[str, Any]:
        """Generate Siri Intents definition file."""
        return {
            "INIntentDefinitionSystemVersion": "22A5266r",
            "INIntentDefinitionToolsVersion": "22A5266r",
            "INIntents": [
                {
                    "INIntentCategory": "generic",
                    "INIntentConfigurable": True,
                    "INIntentDescription": intent.description,
                    "INIntentName": intent.name,
                    "INIntentParameters": [
                        {
                            "INIntentParameterName": name,
                            "INIntentParameterDisplayName": name.replace("_", " ").title(),
                            "INIntentParameterType": "String",
                        }
                        for name in intent.parameters
                    ],
                    "INIntentResponse": {
                        "INIntentResponseCodes": [
                            {"INIntentResponseCodeName": "success"},
                            {"INIntentResponseCodeName": "failure"},
                        ]
                    },
                }
                for intent in self.INTENTS.values()
            ],
        }


class AppleIntelligenceHub:
    """
    Central hub for all Apple Intelligence integrations.

    Coordinates:
    - Writing Tools
    - Siri Intents
    - Shortcuts
    - System-wide AI features
    - Privacy controls
    """

    def __init__(self):
        self.writing_tools = WritingToolsProvider()
        self.siri_handler = SiriIntentHandler()
        self._shortcuts = None
        self._coreml = None
        self._mlx = None

    @property
    def shortcuts(self):
        """Get Shortcuts integration (lazy load)."""
        if self._shortcuts is None:
            from .apple_shortcuts import ShortcutsIntegration
            self._shortcuts = ShortcutsIntegration()
        return self._shortcuts

    @property
    def coreml(self):
        """Get Core ML agent (lazy load)."""
        if self._coreml is None:
            from .coreml_agent import get_coreml_agent
            self._coreml = get_coreml_agent()
        return self._coreml

    @property
    def mlx(self):
        """Get MLX inference (lazy load)."""
        if self._mlx is None:
            from .mlx_inference import get_mlx_inference
            self._mlx = get_mlx_inference()
        return self._mlx

    def get_system_info(self) -> Dict[str, Any]:
        """Get information about Apple Intelligence capabilities."""
        info = {
            "platform": "macOS",
            "apple_silicon": False,
            "neural_engine": False,
            "coreml_available": False,
            "mlx_available": False,
            "shortcuts_available": False,
            "chip_info": {},
        }

        # Check Apple Silicon
        info["chip_info"] = self.coreml.get_chip_info()
        info["apple_silicon"] = info["chip_info"].get("is_apple_silicon", False)
        info["neural_engine"] = info["chip_info"].get("neural_engine_cores", 0) > 0

        # Check Core ML
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            info["coreml_available"] = loop.run_until_complete(self.coreml.is_available())
        except Exception:
            info["coreml_available"] = False

        # Check MLX
        info["mlx_available"] = self.mlx.is_available

        # Check Shortcuts
        info["shortcuts_available"] = self.shortcuts.is_available()

        return info

    async def quick_action(self, action: str, input_text: str) -> str:
        """
        Execute a quick AI action.

        Args:
            action: Action name (proofread, summarize, explain, etc.)
            input_text: Input text

        Returns:
            Result text
        """
        action_map = {
            "proofread": lambda t: self.writing_tools.proofread(t),
            "rewrite": lambda t: self.writing_tools.rewrite(t),
            "summarize": lambda t: self.writing_tools.summarize(t),
            "friendly": lambda t: self.writing_tools.rewrite(t, "friendly"),
            "professional": lambda t: self.writing_tools.rewrite(t, "professional"),
            "concise": lambda t: self.writing_tools.rewrite(t, "concise"),
        }

        handler = action_map.get(action.lower())
        if handler:
            return await handler(input_text)

        # Default: pass to Siri handler
        return await self.siri_handler.handle_intent(
            "AskAITeam",
            {"query": f"{action}: {input_text}"}
        )

    def setup_all(self):
        """Set up all Apple Intelligence integrations."""
        print("Setting up Apple Intelligence integrations...")

        # Save shortcut definitions
        self.shortcuts.save_definitions()
        print("  ✓ Shortcut definitions saved")

        # Generate Siri intents
        intents = self.siri_handler.generate_intents_definition()
        intents_path = Path.home() / ".ai-dev-team" / "siri_intents.json"
        intents_path.parent.mkdir(parents=True, exist_ok=True)
        with open(intents_path, "w") as f:
            json.dump(intents, f, indent=2)
        print(f"  ✓ Siri intents definition saved to {intents_path}")

        # Show system info
        info = self.get_system_info()
        print(f"\nSystem Capabilities:")
        print(f"  Apple Silicon: {'✓' if info['apple_silicon'] else '✗'}")
        print(f"  Neural Engine: {'✓' if info['neural_engine'] else '✗'}")
        print(f"  Core ML: {'✓' if info['coreml_available'] else '✗'}")
        print(f"  MLX: {'✓' if info['mlx_available'] else '✗'}")
        print(f"  Shortcuts: {'✓' if info['shortcuts_available'] else '✗'}")

        if info['chip_info'].get('chip'):
            print(f"\nChip: {info['chip_info']['chip']}")
            print(f"  Neural Engine Cores: {info['chip_info'].get('neural_engine_cores', 'N/A')}")
            print(f"  GPU Cores: {info['chip_info'].get('gpu_cores', 'N/A')}")


# Global instance
_apple_hub: Optional[AppleIntelligenceHub] = None


def get_apple_hub() -> AppleIntelligenceHub:
    """Get or create the global Apple Intelligence hub."""
    global _apple_hub
    if _apple_hub is None:
        _apple_hub = AppleIntelligenceHub()
    return _apple_hub


if __name__ == "__main__":
    import sys

    hub = get_apple_hub()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "info":
            info = hub.get_system_info()
            print(json.dumps(info, indent=2))

        elif command == "setup":
            hub.setup_all()

        elif command == "writing-tools" and len(sys.argv) > 3:
            action = sys.argv[2]
            text = " ".join(sys.argv[3:])

            async def run_action():
                result = await hub.quick_action(action, text)
                print(result)

            asyncio.run(run_action())

    else:
        print("Apple Intelligence Hub")
        print()
        print("Usage:")
        print("  python -m ai_dev_team.apple.system_integration info")
        print("  python -m ai_dev_team.apple.system_integration setup")
        print("  python -m ai_dev_team.apple.system_integration writing-tools <action> <text>")
        print()
        print("Actions: proofread, rewrite, summarize, friendly, professional, concise")
