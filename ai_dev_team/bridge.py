"""
Claude Bridge Client
====================

Allows Claude to execute commands through the bridge daemon.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

BRIDGE_DIR = Path.home() / ".claude_bridge"
COMMAND_FILE = BRIDGE_DIR / "command.json"
RESULT_FILE = BRIDGE_DIR / "result.json"
STATUS_FILE = BRIDGE_DIR / "status.json"


def is_bridge_running() -> bool:
    """Check if the bridge daemon is running"""
    if not STATUS_FILE.exists():
        return False
    try:
        import os
        status = json.loads(STATUS_FILE.read_text())
        pid = status.get("pid")
        if pid:
            os.kill(pid, 0)
            return True
    except:
        pass
    return False


def execute(
    command: str,
    cwd: str = None,
    timeout: int = 300,
    wait_timeout: int = 320
) -> Dict[str, Any]:
    """
    Execute a command through the bridge.

    Args:
        command: Shell command to execute
        cwd: Working directory
        timeout: Command timeout in seconds
        wait_timeout: How long to wait for result

    Returns:
        Dict with success, stdout, stderr, exit_code, duration
    """
    if not is_bridge_running():
        return {
            "success": False,
            "error": "Bridge not running. Start it with: python3 claude_bridge.py",
            "stdout": "",
            "stderr": "Bridge not running",
            "exit_code": -1,
        }

    # Create command request
    cmd_id = str(uuid.uuid4())[:8]
    cmd_data = {
        "id": cmd_id,
        "command": command,
        "cwd": cwd,
        "timeout": timeout,
        "timestamp": time.time(),
    }

    # Write command
    BRIDGE_DIR.mkdir(exist_ok=True)
    with open(COMMAND_FILE, 'w') as f:
        json.dump(cmd_data, f)

    # Wait for result
    start_time = time.time()
    while time.time() - start_time < wait_timeout:
        if RESULT_FILE.exists():
            try:
                result = json.loads(RESULT_FILE.read_text())
                if result.get("id") == cmd_id:
                    RESULT_FILE.unlink()  # Clean up
                    return result
            except:
                pass
        time.sleep(0.5)

    return {
        "success": False,
        "error": "Timeout waiting for result",
        "stdout": "",
        "stderr": "Timeout waiting for bridge result",
        "exit_code": -1,
    }


def run(command: str, cwd: str = None) -> str:
    """
    Simple run - returns stdout or raises exception.
    """
    result = execute(command, cwd)
    if result["success"]:
        return result["stdout"]
    else:
        raise RuntimeError(f"Command failed: {result.get('stderr', result.get('error'))}")
