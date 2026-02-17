#!/usr/bin/env python3
"""
ChatterFix AI Platform
======================

Run the AI-powered CMMS analysis dashboard.

Usage:
    python run.py              # Start the dashboard
    streamlit run dashboard/app.py  # Alternative
"""

import subprocess
import sys

def main():
    print("🤖 Starting ChatterFix AI...")
    print("   Dashboard will open in your browser\n")
    subprocess.run(["streamlit", "run", "dashboard/app.py"] + sys.argv[1:])

if __name__ == "__main__":
    main()
