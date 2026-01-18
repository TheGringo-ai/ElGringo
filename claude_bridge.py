#!/usr/bin/env python3
"""
Claude Command Bridge
======================

A daemon that allows Claude to execute commands in your terminal.
Claude writes commands to a queue file, this daemon executes them
and writes results back.

Usage:
    python3 claude_bridge.py          # Start the bridge daemon
    python3 claude_bridge.py --status # Check if running

Once running, Claude can execute commands through this bridge.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import signal

# Bridge files
BRIDGE_DIR = Path.home() / ".claude_bridge"
COMMAND_FILE = BRIDGE_DIR / "command.json"
RESULT_FILE = BRIDGE_DIR / "result.json"
STATUS_FILE = BRIDGE_DIR / "status.json"
LOG_FILE = BRIDGE_DIR / "bridge.log"

# Ensure bridge directory exists
BRIDGE_DIR.mkdir(exist_ok=True)


def log(message: str):
    """Log message to file and stdout"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + "\n")


def update_status(running: bool, pid: int = None):
    """Update status file"""
    status = {
        "running": running,
        "pid": pid or os.getpid(),
        "started": datetime.now().isoformat(),
        "bridge_dir": str(BRIDGE_DIR),
    }
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)


def check_status():
    """Check if bridge is running"""
    if STATUS_FILE.exists():
        try:
            status = json.loads(STATUS_FILE.read_text())
            pid = status.get("pid")
            # Check if process is actually running
            if pid:
                try:
                    os.kill(pid, 0)  # Doesn't kill, just checks
                    print(f"Bridge is RUNNING (PID: {pid})")
                    print(f"  Directory: {status.get('bridge_dir')}")
                    print(f"  Started: {status.get('started')}")
                    return True
                except OSError:
                    print("Bridge is NOT running (stale status file)")
                    return False
        except:
            pass
    print("Bridge is NOT running")
    return False


def execute_command(cmd: str, timeout: int = 300, cwd: str = None) -> dict:
    """Execute a shell command and return result"""
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or str(Path.home() / "Development/Projects"),
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": time.time() - start_time,
            "command": cmd,
            "timestamp": datetime.now().isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "duration": timeout,
            "command": cmd,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "duration": time.time() - start_time,
            "command": cmd,
            "timestamp": datetime.now().isoformat(),
        }


async def bridge_loop():
    """Main bridge loop - watch for commands and execute them"""
    log("Claude Bridge started")
    log(f"Watching: {COMMAND_FILE}")
    log(f"Results: {RESULT_FILE}")

    update_status(running=True)

    # Clear any old commands
    if COMMAND_FILE.exists():
        COMMAND_FILE.unlink()

    last_command_id = None

    while True:
        try:
            # Check for new command
            if COMMAND_FILE.exists():
                try:
                    cmd_data = json.loads(COMMAND_FILE.read_text())
                    cmd_id = cmd_data.get("id")

                    # Only process new commands
                    if cmd_id and cmd_id != last_command_id:
                        last_command_id = cmd_id
                        command = cmd_data.get("command", "")
                        cwd = cmd_data.get("cwd")
                        timeout = cmd_data.get("timeout", 300)

                        log(f"Executing: {command[:100]}...")

                        # Execute command
                        result = execute_command(command, timeout, cwd)
                        result["id"] = cmd_id

                        # Write result
                        with open(RESULT_FILE, 'w') as f:
                            json.dump(result, f, indent=2)

                        # Clear command file
                        COMMAND_FILE.unlink()

                        status = "SUCCESS" if result["success"] else "FAILED"
                        log(f"Result: {status} (exit code: {result['exit_code']})")

                except json.JSONDecodeError:
                    pass  # Invalid JSON, wait for complete write

            await asyncio.sleep(0.5)  # Check every 500ms

        except asyncio.CancelledError:
            break
        except Exception as e:
            log(f"Error: {e}")
            await asyncio.sleep(1)

    log("Bridge stopped")
    update_status(running=False)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log("Received shutdown signal")
    update_status(running=False)
    sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude Command Bridge")
    parser.add_argument("--status", action="store_true", help="Check bridge status")
    parser.add_argument("--stop", action="store_true", help="Stop the bridge")
    args = parser.parse_args()

    if args.status:
        check_status()
        return

    if args.stop:
        if STATUS_FILE.exists():
            status = json.loads(STATUS_FILE.read_text())
            pid = status.get("pid")
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent stop signal to bridge (PID: {pid})")
                except OSError:
                    print("Bridge not running")
        return

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           CLAUDE COMMAND BRIDGE - ACTIVE                     ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  Claude can now execute commands in your terminal!           ║")
    print("║                                                              ║")
    print("║  Keep this running in the background.                        ║")
    print("║  Press Ctrl+C to stop.                                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Run the bridge
    asyncio.run(bridge_loop())


if __name__ == "__main__":
    main()
