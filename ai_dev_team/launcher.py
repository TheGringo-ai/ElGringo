#!/usr/bin/env python3
"""
AI Team Launcher - Run Multiple UIs Together
=============================================

Starts both the Chat UI and Studio UI simultaneously.

Usage:
    python -m ai_dev_team.launcher
    # or
    ai-launcher

Opens:
    - Chat UI: http://localhost:7860
    - Studio: http://localhost:7861
"""

import multiprocessing
import os
import sys
import time
import webbrowser
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv()


def run_chat_ui():
    """Run the chat UI on port 7860."""
    from ai_dev_team.chat_ui import main as chat_main
    chat_main()


def run_studio_ui():
    """Run the studio UI on port 7861."""
    from ai_dev_team.studio_ui import main as studio_main
    studio_main()


def print_banner():
    """Print startup banner."""
    print("\n" + "=" * 60)
    print("🚀 AI TEAM PLATFORM - FULL SUITE")
    print("=" * 60)
    print("""
    Starting both interfaces:

    💬 Chat UI    → http://localhost:7860
       - Quick conversations with AI team
       - Slash commands for common tasks
       - Voice input, screenshots, git automation

    🎨 Studio     → http://localhost:7861
       - Split-window IDE with live preview
       - Real-time code editing
       - HTML/CSS/JS/React/Python preview

    Press Ctrl+C to stop all services
    """)
    print("=" * 60 + "\n")


def open_browsers():
    """Open both UIs in browser after a delay."""
    time.sleep(3)  # Wait for servers to start
    webbrowser.open("http://localhost:7860")
    time.sleep(0.5)
    webbrowser.open("http://localhost:7861")


def main():
    """Launch both UIs together."""
    print_banner()

    # Create processes for each UI
    chat_process = multiprocessing.Process(target=run_chat_ui, name="ChatUI")
    studio_process = multiprocessing.Process(target=run_studio_ui, name="StudioUI")

    # Optional: open browsers automatically
    browser_process = multiprocessing.Process(target=open_browsers, name="Browser")

    try:
        # Start both UIs
        print("Starting Chat UI...")
        chat_process.start()

        print("Starting Studio UI...")
        studio_process.start()

        # Open browsers
        browser_process.start()

        # Wait for both to complete (they run forever until Ctrl+C)
        chat_process.join()
        studio_process.join()

    except KeyboardInterrupt:
        print("\n\nShutting down...")

        # Terminate processes
        if chat_process.is_alive():
            chat_process.terminate()
            chat_process.join(timeout=2)

        if studio_process.is_alive():
            studio_process.terminate()
            studio_process.join(timeout=2)

        if browser_process.is_alive():
            browser_process.terminate()

        print("All services stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
