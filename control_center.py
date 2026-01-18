#!/usr/bin/env python3
"""
AI Dev Team - Control Center
============================

Launch the self-sustaining AI development platform with:
- System resource monitoring
- Agent health checks
- Apple Intelligence notifications
- Auto-recovery
- Performance optimization

Usage:
    python3 control_center.py          # Start interactive control center
    python3 control_center.py --daemon # Run as background service
    python3 control_center.py --status # Show current status
"""

import argparse
import asyncio
import os
import sys

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam
from ai_dev_team.monitor.control_center import ControlCenter, ControlCenterConfig


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     █████╗ ██╗    ██████╗ ███████╗██╗   ██╗    ████████╗███████╗    ║
║    ██╔══██╗██║    ██╔══██╗██╔════╝██║   ██║    ╚══██╔══╝██╔════╝    ║
║    ███████║██║    ██║  ██║█████╗  ██║   ██║       ██║   █████╗      ║
║    ██╔══██║██║    ██║  ██║██╔══╝  ╚██╗ ██╔╝       ██║   ██╔══╝      ║
║    ██║  ██║██║    ██████╔╝███████╗ ╚████╔╝        ██║   ███████╗    ║
║    ╚═╝  ╚═╝╚═╝    ╚═════╝ ╚══════╝  ╚═══╝         ╚═╝   ╚══════╝    ║
║                                                                      ║
║                    CONTROL CENTER - COMMAND HQ                       ║
║                                                                      ║
║  System Monitor | Health Checks | Auto-Recovery | Apple Intelligence ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


async def interactive_mode(center: ControlCenter):
    """Run interactive control center"""
    print("\nControl Center Commands:")
    print("  status    - Show dashboard")
    print("  system    - System resources")
    print("  health    - Agent health")
    print("  perf      - Performance stats")
    print("  recovery  - Recovery stats")
    print("  resources - Rate limits & costs")
    print("  notify    - Send test notification")
    print("  speak     - Test Siri voice")
    print("  exit      - Shutdown")
    print()

    while center._running:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("control> ").strip().lower()
            )

            if cmd == "exit" or cmd == "quit":
                print("Shutting down...")
                await center.stop()
                break

            elif cmd == "status" or cmd == "dashboard":
                center.print_dashboard()

            elif cmd == "system":
                center.check_system()

            elif cmd == "health":
                center.check_health()

            elif cmd == "perf" or cmd == "performance":
                center.check_performance()

            elif cmd == "recovery":
                center.check_recovery()

            elif cmd == "resources" or cmd == "budget" or cmd == "costs":
                center.check_resources()

            elif cmd == "notify":
                center.notify("Test Notification", "Control Center is working!")
                print("Notification sent!")

            elif cmd == "speak":
                center.speak("AI Development Team Control Center is online and operational.")
                print("Speaking...")

            elif cmd == "help":
                print("\nCommands: status, system, health, perf, recovery, resources, notify, speak, exit")

            elif cmd:
                print(f"Unknown command: {cmd}. Type 'help' for commands.")

        except KeyboardInterrupt:
            print("\nShutting down...")
            await center.stop()
            break
        except EOFError:
            await center.stop()
            break


async def main():
    parser = argparse.ArgumentParser(
        description="AI Dev Team Control Center",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 control_center.py              # Interactive mode
  python3 control_center.py --status     # Show status and exit
  python3 control_center.py --daemon     # Run as background service
  python3 control_center.py --no-notify  # Disable notifications
        """
    )

    parser.add_argument("--daemon", action="store_true", help="Run as background service")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--no-notify", action="store_true", help="Disable Apple notifications")
    parser.add_argument("--no-speak", action="store_true", help="Disable Siri voice alerts")
    parser.add_argument("-p", "--project", default="ai-platform", help="Project name")

    args = parser.parse_args()

    # Print banner
    if not args.status:
        print_banner()

    # Create AI team
    print("Initializing AI Team...")
    team = AIDevTeam(project_name=args.project)

    if not team.agents:
        print("\nNo AI agents available. Set API keys:")
        print("  export OPENAI_API_KEY=your_key")
        print("  export ANTHROPIC_API_KEY=your_key")
        print("  export GEMINI_API_KEY=your_key")
        print("  export XAI_API_KEY=your_key")
        sys.exit(1)

    print(f"AI Team ready: {len(team.agents)} agents online")
    for name in team.agents:
        print(f"  - {name}")

    # Create control center config
    config = ControlCenterConfig(
        enable_apple_notifications=not args.no_notify,
        speak_critical_alerts=not args.no_speak,
    )

    # Create control center
    center = ControlCenter(team=team, config=config)

    if args.status:
        # Just show status
        await center.start()
        await asyncio.sleep(2)  # Wait for initial health checks
        center.print_dashboard()
        await center.stop()
        return

    # Start control center
    await center.start()
    print("\nControl Center is ONLINE")

    if args.daemon:
        # Run as daemon
        print("Running in daemon mode. Use Ctrl+C to stop.")
        try:
            while center._running:
                await asyncio.sleep(60)
                # Periodic dashboard print
                center.print_dashboard()
        except KeyboardInterrupt:
            print("\nShutting down...")
            await center.stop()
    else:
        # Interactive mode
        await interactive_mode(center)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
