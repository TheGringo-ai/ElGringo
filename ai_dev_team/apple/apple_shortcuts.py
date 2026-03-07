"""
Apple Shortcuts Integration
============================

Integrates AI Team with Apple Shortcuts for:
- Siri voice commands
- Automation workflows
- Quick actions
- Widget support

Enables natural language interaction via "Hey Siri, ask AI Team..."
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class ShortcutAction:
    """Represents an action in an Apple Shortcut."""
    identifier: str
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShortcutDefinition:
    """Definition of an Apple Shortcut."""
    name: str
    description: str
    actions: List[ShortcutAction]
    icon_color: str = "blue"
    icon_glyph: str = "brain"  # SF Symbol name
    accepts_input: bool = True
    input_type: str = "text"


class ShortcutsIntegration:
    """
    Integrates AI Team Platform with Apple Shortcuts.

    Features:
    - Create shortcuts for common AI tasks
    - Voice activation via Siri
    - Share sheet integration
    - Widget quick actions
    - Automation triggers

    Example Shortcuts:
    - "Ask AI Team" - General AI assistant
    - "Review Code" - Code review with AI team
    - "Debug Error" - Debug assistance
    - "Generate Code" - Code generation
    """

    SHORTCUTS_DIR = Path.home() / ".ai-dev-team" / "shortcuts"

    # Pre-defined shortcuts for common tasks
    BUILT_IN_SHORTCUTS = {
        "ask-ai-team": ShortcutDefinition(
            name="Ask AI Team",
            description="Ask your AI development team anything",
            actions=[
                ShortcutAction(
                    identifier="is.workflow.actions.ask",
                    name="Ask for Input",
                    parameters={"question": "What would you like to ask the AI Team?"}
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.runshellscript",
                    name="Run AI Team",
                    parameters={
                        "script": 'ai-team "$1"',
                        "input": "Shortcut Input"
                    }
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.showresult",
                    name="Show Result",
                    parameters={}
                ),
            ],
            icon_color="purple",
            icon_glyph="sparkles",
        ),
        "review-code": ShortcutDefinition(
            name="Review Code",
            description="Get AI code review from clipboard or share sheet",
            actions=[
                ShortcutAction(
                    identifier="is.workflow.actions.getclipboard",
                    name="Get Clipboard",
                    parameters={}
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.runshellscript",
                    name="Review Code",
                    parameters={
                        "script": 'ai-team "Review this code for bugs and improvements:\\n$1"',
                        "input": "Clipboard"
                    }
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.showresult",
                    name="Show Review",
                    parameters={}
                ),
            ],
            icon_color="green",
            icon_glyph="eye",
        ),
        "debug-error": ShortcutDefinition(
            name="Debug Error",
            description="Get help debugging an error message",
            actions=[
                ShortcutAction(
                    identifier="is.workflow.actions.ask",
                    name="Ask for Error",
                    parameters={"question": "Paste the error message:"}
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.runshellscript",
                    name="Debug Error",
                    parameters={
                        "script": 'ai-team "Debug this error and explain how to fix it:\\n$1"',
                        "input": "Shortcut Input"
                    }
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.showresult",
                    name="Show Solution",
                    parameters={}
                ),
            ],
            icon_color="red",
            icon_glyph="ladybug",
        ),
        "generate-code": ShortcutDefinition(
            name="Generate Code",
            description="Generate code from a description",
            actions=[
                ShortcutAction(
                    identifier="is.workflow.actions.ask",
                    name="Ask for Description",
                    parameters={"question": "Describe the code you want to generate:"}
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.runshellscript",
                    name="Generate Code",
                    parameters={
                        "script": 'ai-team "Generate code for: $1"',
                        "input": "Shortcut Input"
                    }
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.setclipboard",
                    name="Copy to Clipboard",
                    parameters={}
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.showresult",
                    name="Show Code",
                    parameters={}
                ),
            ],
            icon_color="blue",
            icon_glyph="chevron.left.forwardslash.chevron.right",
        ),
        "explain-code": ShortcutDefinition(
            name="Explain Code",
            description="Get an explanation of code from clipboard",
            actions=[
                ShortcutAction(
                    identifier="is.workflow.actions.getclipboard",
                    name="Get Clipboard",
                    parameters={}
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.runshellscript",
                    name="Explain Code",
                    parameters={
                        "script": 'ai-team "Explain this code in detail:\\n$1"',
                        "input": "Clipboard"
                    }
                ),
                ShortcutAction(
                    identifier="is.workflow.actions.showresult",
                    name="Show Explanation",
                    parameters={}
                ),
            ],
            icon_color="orange",
            icon_glyph="book",
        ),
    }

    def __init__(self):
        self.SHORTCUTS_DIR.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        """Check if Shortcuts app is available."""
        try:
            result = subprocess.run(
                ["shortcuts", "list"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def list_shortcuts(self) -> List[str]:
        """List all installed shortcuts."""
        try:
            result = subprocess.run(
                ["shortcuts", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except Exception as e:
            logger.error(f"Failed to list shortcuts: {e}")
        return []

    def run_shortcut(self, name: str, input_text: Optional[str] = None) -> Optional[str]:
        """
        Run a shortcut by name.

        Args:
            name: Shortcut name
            input_text: Optional input to pass to shortcut

        Returns:
            Output from the shortcut, or None if failed
        """
        try:
            cmd = ["shortcuts", "run", name]
            input_data = input_text.encode() if input_text else None

            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Shortcut failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Failed to run shortcut: {e}")
            return None

    def create_shortcut_url(self, definition: ShortcutDefinition) -> str:
        """
        Generate a shortcuts:// URL to create a shortcut.

        This opens the Shortcuts app with the shortcut ready to save.
        """
        # Build the shortcut URL scheme
        # Note: Full programmatic shortcut creation requires signed shortcuts
        # This creates a URL that opens Shortcuts with a template

        params = {
            "name": definition.name,
            "description": definition.description,
        }

        base_url = "shortcuts://create-shortcut"
        query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())

        return f"{base_url}?{query}"

    def export_shortcut_json(self, definition: ShortcutDefinition) -> Dict[str, Any]:
        """
        Export shortcut definition as JSON for manual import.

        This can be used with shortcut signing tools or for documentation.
        """
        return {
            "WFWorkflowName": definition.name,
            "WFWorkflowDescription": definition.description,
            "WFWorkflowIcon": {
                "WFWorkflowIconStartColor": self._color_to_value(definition.icon_color),
                "WFWorkflowIconGlyphNumber": definition.icon_glyph,
            },
            "WFWorkflowInputContentItemClasses": [
                "WFStringContentItem" if definition.input_type == "text" else "WFGenericFileContentItem"
            ],
            "WFWorkflowActions": [
                {
                    "WFWorkflowActionIdentifier": action.identifier,
                    "WFWorkflowActionParameters": action.parameters,
                }
                for action in definition.actions
            ],
        }

    def _color_to_value(self, color: str) -> int:
        """Convert color name to Shortcuts color value."""
        colors = {
            "red": 4282601983,
            "orange": 4292093695,
            "yellow": 4294967040,
            "green": 4292338431,
            "teal": 4280623615,
            "blue": 4282400831,
            "purple": 4290330879,
            "pink": 4291690495,
            "gray": 4285098975,
        }
        return colors.get(color.lower(), colors["blue"])

    def generate_installation_guide(self) -> str:
        """Generate a guide for installing AI Team shortcuts."""
        guide = """
# AI Team Shortcuts Installation Guide

## Quick Install (Recommended)

Run this command to install all AI Team shortcuts:

```bash
python -m ai_dev_team.apple.apple_shortcuts install
```

## Manual Installation

### 1. "Ask AI Team" Shortcut
Create a new shortcut with these actions:
1. Ask for Input: "What would you like to ask the AI Team?"
2. Run Shell Script: `ai-team "$1"`
3. Show Result

### 2. "Review Code" Shortcut
1. Get Clipboard
2. Run Shell Script: `ai-team "Review this code:\\n$1"`
3. Show Result

### 3. "Debug Error" Shortcut
1. Ask for Input: "Paste the error message:"
2. Run Shell Script: `ai-team "Debug this error:\\n$1"`
3. Show Result

### 4. "Generate Code" Shortcut
1. Ask for Input: "Describe the code:"
2. Run Shell Script: `ai-team "Generate code for: $1"`
3. Copy to Clipboard
4. Show Result

## Using with Siri

Once shortcuts are installed, you can say:
- "Hey Siri, Ask AI Team"
- "Hey Siri, Review Code"
- "Hey Siri, Debug Error"
- "Hey Siri, Generate Code"

## Widget Setup

1. Long press on your home screen
2. Tap the + button
3. Search for "Shortcuts"
4. Add the Shortcuts widget
5. Tap the widget to configure
6. Select your AI Team shortcuts
"""
        return guide

    def save_definitions(self):
        """Save shortcut definitions to JSON files for reference."""
        for name, definition in self.BUILT_IN_SHORTCUTS.items():
            filepath = self.SHORTCUTS_DIR / f"{name}.json"
            with open(filepath, "w") as f:
                json.dump(self.export_shortcut_json(definition), f, indent=2)
            logger.info(f"Saved shortcut definition: {filepath}")


def create_shortcut(name: str) -> bool:
    """
    Create a built-in AI Team shortcut.

    Args:
        name: Shortcut name (e.g., "ask-ai-team")

    Returns:
        True if shortcut was created successfully
    """
    integration = ShortcutsIntegration()

    if name not in integration.BUILT_IN_SHORTCUTS:
        logger.error(f"Unknown shortcut: {name}")
        logger.info(f"Available: {list(integration.BUILT_IN_SHORTCUTS.keys())}")
        return False

    definition = integration.BUILT_IN_SHORTCUTS[name]

    # Generate URL to create shortcut
    url = integration.create_shortcut_url(definition)

    # Open in Shortcuts app
    try:
        subprocess.run(["open", url], check=True)
        logger.info(f"Opened Shortcuts app for: {definition.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to open Shortcuts: {e}")
        return False


if __name__ == "__main__":
    import sys

    integration = ShortcutsIntegration()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "available":
            print(f"Shortcuts Available: {integration.is_available()}")

        elif command == "list":
            shortcuts = integration.list_shortcuts()
            print("Installed Shortcuts:")
            for s in shortcuts:
                print(f"  - {s}")

        elif command == "builtins":
            print("Built-in AI Team Shortcuts:")
            for name, defn in integration.BUILT_IN_SHORTCUTS.items():
                print(f"  {name}: {defn.name}")
                print(f"    {defn.description}")

        elif command == "install":
            if len(sys.argv) > 2:
                name = sys.argv[2]
                create_shortcut(name)
            else:
                print("Installing all AI Team shortcuts...")
                for name in integration.BUILT_IN_SHORTCUTS:
                    create_shortcut(name)
                    print(f"  Created: {name}")

        elif command == "guide":
            print(integration.generate_installation_guide())

        elif command == "save":
            integration.save_definitions()
            print(f"Saved shortcut definitions to {integration.SHORTCUTS_DIR}")

        elif command == "run" and len(sys.argv) > 2:
            shortcut_name = sys.argv[2]
            input_text = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
            result = integration.run_shortcut(shortcut_name, input_text)
            if result:
                print(result)

    else:
        print("AI Team Shortcuts Integration")
        print()
        print("Usage:")
        print("  python -m ai_dev_team.apple.apple_shortcuts available")
        print("  python -m ai_dev_team.apple.apple_shortcuts list")
        print("  python -m ai_dev_team.apple.apple_shortcuts builtins")
        print("  python -m ai_dev_team.apple.apple_shortcuts install [name]")
        print("  python -m ai_dev_team.apple.apple_shortcuts guide")
        print("  python -m ai_dev_team.apple.apple_shortcuts run <name> [input]")
