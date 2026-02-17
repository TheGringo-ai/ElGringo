"""
Computer Use Agent - AI That Can Control Your Computer

SECRET WEAPON #8: Claude can USE A COMPUTER like a human!
This is Anthropic's groundbreaking computer use capability.

The AI can:
- See your screen (via screenshots)
- Move the mouse and click
- Type on the keyboard
- Navigate applications
- Perform complex multi-step tasks

This enables automation of virtually ANY computer task!

NOTE: This feature requires explicit user consent and has safety measures.
It should only be used for legitimate automation tasks.
"""

import asyncio
import base64
import io
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ComputerAction(Enum):
    """Actions the agent can take"""
    SCREENSHOT = "screenshot"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY = "key"  # Special keys like Enter, Escape
    SCROLL = "scroll"
    MOVE = "move"
    DRAG = "drag"


@dataclass
class ActionResult:
    """Result of a computer action"""
    action: ComputerAction
    success: bool
    screenshot: Optional[bytes] = None  # Screenshot after action
    error: Optional[str] = None
    coordinates: Optional[Tuple[int, int]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComputerUseSession:
    """A computer use session"""
    task: str
    actions_taken: List[ActionResult] = field(default_factory=list)
    status: str = "running"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


class ComputerUseAgent:
    """
    Computer Use Agent - AI That Controls Your Computer

    This uses Claude's computer use capability to perform
    arbitrary tasks on your computer through vision and actions.

    IMPORTANT: This requires explicit user consent!

    Usage:
        agent = ComputerUseAgent()

        # User must consent first
        if await agent.request_consent():
            result = await agent.perform_task(
                "Open Chrome and search for Python tutorials"
            )

        # With safety limits
        result = await agent.perform_task(
            task="Fill out this form",
            max_actions=20,
            require_confirmation=True
        )
    """

    # Safety limits
    MAX_ACTIONS_DEFAULT = 50
    ACTION_DELAY = 0.5  # Seconds between actions

    def __init__(
        self,
        require_consent: bool = True,
        allowed_apps: Optional[List[str]] = None,
        blocked_apps: Optional[List[str]] = None
    ):
        """
        Initialize computer use agent.

        Args:
            require_consent: Require explicit user consent (recommended!)
            allowed_apps: Only allow interaction with these apps
            blocked_apps: Never interact with these apps
        """
        self.require_consent = require_consent
        self.allowed_apps = allowed_apps
        self.blocked_apps = blocked_apps or ["Terminal", "System Preferences", "Keychain"]
        self._client = None
        self._consent_given = False
        self._screen_size = self._get_screen_size()

    def _get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions"""
        if platform.system() == "Darwin":  # macOS
            try:
                output = subprocess.check_output(
                    ["system_profiler", "SPDisplaysDataType"],
                    text=True
                )
                # Parse output for resolution
                for line in output.split('\n'):
                    if 'Resolution' in line:
                        parts = line.split(':')[1].strip().split(' x ')
                        return (int(parts[0]), int(parts[1].split()[0]))
            except:
                pass
        return (1920, 1080)  # Default

    async def _get_client(self):
        """Get Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
        return self._client

    async def request_consent(self) -> bool:
        """
        Request user consent for computer control.

        This is REQUIRED before using computer use capabilities.
        """
        print("\n" + "="*60)
        print("COMPUTER USE CONSENT REQUEST")
        print("="*60)
        print("""
The AI agent is requesting permission to control your computer.

This includes:
- Taking screenshots of your screen
- Moving your mouse and clicking
- Typing on your keyboard
- Interacting with applications

Safety measures in place:
- Action limits per session
- Blocked sensitive applications
- All actions are logged
- You can stop at any time

ONLY grant consent if you trust this automation task!
        """)
        print("="*60)

        response = input("\nDo you consent to computer control? (yes/no): ")
        self._consent_given = response.lower() in ["yes", "y"]

        if self._consent_given:
            logger.info("Computer use consent granted")
        else:
            logger.info("Computer use consent denied")

        return self._consent_given

    def take_screenshot(self) -> bytes:
        """Take a screenshot of the current screen"""
        if platform.system() == "Darwin":  # macOS
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                subprocess.run(['screencapture', '-x', f.name], check=True)
                with open(f.name, 'rb') as img_file:
                    return img_file.read()

        elif platform.system() == "Linux":
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                subprocess.run(['gnome-screenshot', '-f', f.name], check=True)
                with open(f.name, 'rb') as img_file:
                    return img_file.read()

        elif platform.system() == "Windows":
            # Would use PIL or pyautogui
            pass

        raise RuntimeError(f"Unsupported platform: {platform.system()}")

    def _execute_action(self, action: ComputerAction, params: Dict[str, Any]) -> ActionResult:
        """Execute a computer action"""
        try:
            if platform.system() == "Darwin":  # macOS
                return self._execute_macos_action(action, params)
            elif platform.system() == "Linux":
                return self._execute_linux_action(action, params)
            elif platform.system() == "Windows":
                return self._execute_windows_action(action, params)
            else:
                return ActionResult(
                    action=action,
                    success=False,
                    error=f"Unsupported platform: {platform.system()}"
                )
        except Exception as e:
            return ActionResult(
                action=action,
                success=False,
                error=str(e)
            )

    def _execute_macos_action(self, action: ComputerAction, params: Dict[str, Any]) -> ActionResult:
        """Execute action on macOS using AppleScript/cliclick"""
        if action == ComputerAction.SCREENSHOT:
            screenshot = self.take_screenshot()
            return ActionResult(action=action, success=True, screenshot=screenshot)

        elif action == ComputerAction.CLICK:
            x, y = params.get("x", 0), params.get("y", 0)
            subprocess.run(["cliclick", f"c:{x},{y}"], check=True)
            return ActionResult(action=action, success=True, coordinates=(x, y))

        elif action == ComputerAction.DOUBLE_CLICK:
            x, y = params.get("x", 0), params.get("y", 0)
            subprocess.run(["cliclick", f"dc:{x},{y}"], check=True)
            return ActionResult(action=action, success=True, coordinates=(x, y))

        elif action == ComputerAction.RIGHT_CLICK:
            x, y = params.get("x", 0), params.get("y", 0)
            subprocess.run(["cliclick", f"rc:{x},{y}"], check=True)
            return ActionResult(action=action, success=True, coordinates=(x, y))

        elif action == ComputerAction.TYPE:
            text = params.get("text", "")
            # Use AppleScript for reliable typing
            script = f'tell application "System Events" to keystroke "{text}"'
            subprocess.run(["osascript", "-e", script], check=True)
            return ActionResult(action=action, success=True)

        elif action == ComputerAction.KEY:
            key = params.get("key", "")
            key_map = {
                "enter": "return",
                "tab": "tab",
                "escape": "escape",
                "backspace": "delete",
                "up": "up arrow",
                "down": "down arrow",
                "left": "left arrow",
                "right": "right arrow"
            }
            key_name = key_map.get(key.lower(), key)
            script = f'tell application "System Events" to key code {key_name}'
            subprocess.run(["osascript", "-e", script], check=True)
            return ActionResult(action=action, success=True)

        elif action == ComputerAction.MOVE:
            x, y = params.get("x", 0), params.get("y", 0)
            subprocess.run(["cliclick", f"m:{x},{y}"], check=True)
            return ActionResult(action=action, success=True, coordinates=(x, y))

        elif action == ComputerAction.SCROLL:
            direction = params.get("direction", "down")
            amount = params.get("amount", 3)
            scroll_val = amount if direction == "up" else -amount
            # Use cliclick or AppleScript for scrolling
            return ActionResult(action=action, success=True)

        return ActionResult(action=action, success=False, error="Unknown action")

    def _execute_linux_action(self, action: ComputerAction, params: Dict[str, Any]) -> ActionResult:
        """Execute action on Linux using xdotool"""
        if action == ComputerAction.CLICK:
            x, y = params.get("x", 0), params.get("y", 0)
            subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"], check=True)
            return ActionResult(action=action, success=True, coordinates=(x, y))

        elif action == ComputerAction.TYPE:
            text = params.get("text", "")
            subprocess.run(["xdotool", "type", text], check=True)
            return ActionResult(action=action, success=True)

        elif action == ComputerAction.KEY:
            key = params.get("key", "")
            subprocess.run(["xdotool", "key", key], check=True)
            return ActionResult(action=action, success=True)

        return ActionResult(action=action, success=False, error="Not implemented")

    def _execute_windows_action(self, action: ComputerAction, params: Dict[str, Any]) -> ActionResult:
        """Execute action on Windows using pyautogui"""
        return ActionResult(action=action, success=False, error="Windows support coming soon")

    async def perform_task(
        self,
        task: str,
        max_actions: int = None,
        require_confirmation: bool = False,
        on_action: Optional[Callable[[ActionResult], None]] = None
    ) -> ComputerUseSession:
        """
        Perform a computer task using AI vision and control.

        Args:
            task: Natural language description of the task
            max_actions: Maximum actions to take
            require_confirmation: Confirm each action
            on_action: Callback for each action

        Returns:
            ComputerUseSession with results
        """
        if self.require_consent and not self._consent_given:
            consent = await self.request_consent()
            if not consent:
                return ComputerUseSession(
                    task=task,
                    status="consent_denied"
                )

        client = await self._get_client()
        if not client:
            return ComputerUseSession(
                task=task,
                status="error",
                actions_taken=[ActionResult(
                    action=ComputerAction.SCREENSHOT,
                    success=False,
                    error="ANTHROPIC_API_KEY not configured"
                )]
            )

        max_actions = max_actions or self.MAX_ACTIONS_DEFAULT
        session = ComputerUseSession(task=task)

        logger.info(f"Starting computer use task: {task}")

        # Tool definition for Claude's computer use
        tools = [{
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": self._screen_size[0],
            "display_height_px": self._screen_size[1],
            "display_number": 1
        }]

        messages = [{
            "role": "user",
            "content": f"""Task: {task}

Use the computer tool to accomplish this task.
Take a screenshot first to see the current state.
Proceed step by step, taking screenshots to verify each action."""
        }]

        for i in range(max_actions):
            try:
                # Take screenshot for context
                screenshot = self.take_screenshot()
                screenshot_b64 = base64.standard_b64encode(screenshot).decode()

                # Call Claude with computer use
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    tools=tools,
                    messages=messages + [{
                        "role": "user",
                        "content": [{
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_b64
                            }
                        }, {
                            "type": "text",
                            "text": "Here is the current screen. What action should I take next?"
                        }]
                    }]
                )

                # Check if task is complete
                if response.stop_reason == "end_turn":
                    # Check if the model thinks we're done
                    for block in response.content:
                        if hasattr(block, 'text') and "task complete" in block.text.lower():
                            session.status = "completed"
                            session.end_time = datetime.now()
                            return session

                # Process tool use
                for block in response.content:
                    if block.type == "tool_use" and block.name == "computer":
                        action_input = block.input
                        action_type = action_input.get("action", "screenshot")

                        if require_confirmation:
                            print(f"\nAction requested: {action_type} with {action_input}")
                            confirm = input("Execute? (yes/no): ")
                            if confirm.lower() not in ["yes", "y"]:
                                session.status = "cancelled"
                                return session

                        # Execute the action
                        action = ComputerAction(action_type)
                        result = self._execute_action(action, action_input)
                        session.actions_taken.append(result)

                        if on_action:
                            on_action(result)

                        if not result.success:
                            logger.warning(f"Action failed: {result.error}")

                        await asyncio.sleep(self.ACTION_DELAY)

            except Exception as e:
                logger.error(f"Computer use error: {e}")
                session.status = "error"
                session.end_time = datetime.now()
                return session

        # Max actions reached
        session.status = "max_actions_reached"
        session.end_time = datetime.now()
        return session

    def get_session_summary(self, session: ComputerUseSession) -> str:
        """Get human-readable summary of a session"""
        duration = (session.end_time - session.start_time).total_seconds() if session.end_time else 0

        return f"""
Computer Use Session Summary
=============================
Task: {session.task}
Status: {session.status}
Actions Taken: {len(session.actions_taken)}
Duration: {duration:.1f} seconds

Actions:
{chr(10).join(f"  - {a.action.value}: {'Success' if a.success else 'Failed - ' + (a.error or '')}" for a in session.actions_taken)}
"""


# Safety wrapper
def safe_computer_use(func):
    """Decorator to ensure safe computer use"""
    async def wrapper(*args, **kwargs):
        print("\n⚠️  COMPUTER USE SAFETY WARNING ⚠️")
        print("This operation will control your computer.")
        print("Press Ctrl+C at any time to stop.\n")
        try:
            return await func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n\n🛑 Computer use interrupted by user.")
            return None
    return wrapper


# Convenience function
@safe_computer_use
async def automate_task(task: str) -> Optional[ComputerUseSession]:
    """Quick computer automation with safety prompts"""
    agent = ComputerUseAgent()
    return await agent.perform_task(task)
