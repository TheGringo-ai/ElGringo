"""
Apple Intelligence Integration
==============================

Native macOS integration for notifications, Siri, Shortcuts,
and system-level intelligence features.
"""

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """macOS notification"""
    title: str
    message: str
    subtitle: Optional[str] = None
    sound: bool = True
    priority: NotificationPriority = NotificationPriority.NORMAL


class AppleIntelligence:
    """
    Apple Intelligence Integration

    Provides native macOS integration:
    - Notification Center alerts
    - System sounds
    - Siri Shortcuts integration
    - Focus mode awareness
    - Menu bar status
    """

    # Sound mappings
    SOUNDS = {
        NotificationPriority.LOW: "Pop",
        NotificationPriority.NORMAL: "Glass",
        NotificationPriority.HIGH: "Ping",
        NotificationPriority.CRITICAL: "Sosumi",
    }

    def __init__(self, app_name: str = "AI Dev Team"):
        self.app_name = app_name
        self._notification_history: List[Dict[str, Any]] = []
        self._max_history = 100

    def notify(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None,
        sound: bool = True,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """
        Send a native macOS notification

        Uses osascript to display notifications through Notification Center.
        """
        try:
            # Build AppleScript
            sound_name = self.SOUNDS.get(priority, "Glass")

            script_parts = [
                f'display notification "{self._escape(message)}"',
                f'with title "{self._escape(title)}"',
            ]

            if subtitle:
                script_parts.append(f'subtitle "{self._escape(subtitle)}"')

            if sound:
                script_parts.append(f'sound name "{sound_name}"')

            script = " ".join(script_parts)

            # Execute
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )

            success = result.returncode == 0

            # Log
            self._notification_history.append({
                "title": title,
                "message": message,
                "priority": priority.value,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            if len(self._notification_history) > self._max_history:
                self._notification_history = self._notification_history[-self._max_history:]

            if not success:
                logger.warning(f"Notification failed: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def notify_alert(self, title: str, message: str):
        """Send a high-priority alert notification"""
        return self.notify(
            title=f"[ALERT] {title}",
            message=message,
            priority=NotificationPriority.HIGH,
        )

    def notify_critical(self, title: str, message: str):
        """Send a critical notification with dialog"""
        try:
            script = f'''
            display dialog "{self._escape(message)}" with title "{self._escape(title)}" with icon caution buttons {{"OK"}} default button "OK"
            '''
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=30
            )
            return True
        except Exception as e:
            logger.error(f"Critical notification failed: {e}")
            return False

    def play_sound(self, sound_name: str = "Glass"):
        """Play a system sound"""
        try:
            # Use afplay for system sounds
            sound_path = f"/System/Library/Sounds/{sound_name}.aiff"
            if os.path.exists(sound_path):
                subprocess.run(["afplay", sound_path], timeout=5)
            else:
                # Fallback to say command beep
                subprocess.run(["osascript", "-e", 'beep'], timeout=5)
        except Exception as e:
            logger.warning(f"Failed to play sound: {e}")

    def speak(self, text: str, voice: str = "Samantha"):
        """Use text-to-speech (Siri voice)"""
        try:
            subprocess.run(
                ["say", "-v", voice, text],
                timeout=30
            )
        except Exception as e:
            logger.warning(f"Text-to-speech failed: {e}")

    async def speak_async(self, text: str, voice: str = "Samantha"):
        """Async text-to-speech"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.speak(text, voice))

    def get_system_appearance(self) -> str:
        """Get current system appearance (light/dark mode)"""
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "Dark" in result.stdout:
                return "dark"
            return "light"
        except Exception:
            return "light"

    def is_focus_mode_active(self) -> bool:
        """Check if Focus/Do Not Disturb is active"""
        try:
            # Check DND status
            result = subprocess.run(
                ["defaults", "read", "com.apple.controlcenter", "NSStatusItem Visible FocusModes"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "1" in result.stdout
        except Exception:
            return False

    def create_shortcut_command(self, shortcut_name: str, input_data: Optional[str] = None) -> bool:
        """Run a Siri Shortcut"""
        try:
            cmd = ["shortcuts", "run", shortcut_name]
            if input_data:
                cmd.extend(["-i", input_data])

            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Shortcut execution failed: {e}")
            return False

    def open_app(self, app_name: str) -> bool:
        """Open a macOS application"""
        try:
            subprocess.run(["open", "-a", app_name], timeout=10)
            return True
        except Exception:
            return False

    def set_clipboard(self, text: str) -> bool:
        """Copy text to clipboard"""
        try:
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
            )
            process.communicate(text.encode())
            return process.returncode == 0
        except Exception:
            return False

    def get_clipboard(self) -> str:
        """Get text from clipboard"""
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception:
            return ""

    def show_menu_bar_alert(self, message: str):
        """Show alert in menu bar area (requires additional setup)"""
        # This is a placeholder - full implementation would require
        # a native macOS menu bar app
        self.notify("AI Dev Team", message, priority=NotificationPriority.HIGH)

    def _escape(self, text: str) -> str:
        """Escape text for AppleScript"""
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    def get_notification_history(self) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        return self._notification_history[-20:]

    # Convenience methods for common notifications

    def notify_task_complete(self, task_name: str, duration: float):
        """Notify that a task completed"""
        self.notify(
            title="Task Complete",
            message=f"{task_name} finished in {duration:.1f}s",
            subtitle=self.app_name,
            priority=NotificationPriority.NORMAL,
        )

    def notify_agent_offline(self, agent_name: str):
        """Notify that an agent went offline"""
        self.notify(
            title="Agent Offline",
            message=f"{agent_name} is not responding",
            subtitle="Health Check Failed",
            priority=NotificationPriority.HIGH,
        )

    def notify_agent_recovered(self, agent_name: str):
        """Notify that an agent recovered"""
        self.notify(
            title="Agent Recovered",
            message=f"{agent_name} is back online",
            subtitle="Health Check Passed",
            priority=NotificationPriority.NORMAL,
        )

    def notify_memory_warning(self, percent: float):
        """Notify about high memory usage"""
        self.notify(
            title="Memory Warning",
            message=f"Memory usage at {percent:.0f}%",
            subtitle="Consider closing some applications",
            priority=NotificationPriority.HIGH,
        )

    def notify_error(self, error: str):
        """Notify about an error"""
        self.notify(
            title="Error",
            message=error[:100],
            priority=NotificationPriority.HIGH,
        )

    def notify_success(self, message: str):
        """Notify about success"""
        self.notify(
            title="Success",
            message=message,
            priority=NotificationPriority.NORMAL,
        )
