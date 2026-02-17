#!/usr/bin/env python3
"""
Memory Monitor for MLX Training
===============================
Run this in a separate terminal while training to watch memory usage.

Usage:
    python monitor_memory.py

Safe zones:
    GREEN (< 10GB): Safe for training
    YELLOW (10-12GB): Training zone - normal during fine-tuning
    RED (> 14GB): Danger - consider stopping training
"""

import time
import sys

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil", "-q"])
    import psutil


def get_memory_bar(percent, width=40):
    """Create a visual memory bar"""
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)

    if percent < 60:
        color = "\033[92m"  # Green
    elif percent < 80:
        color = "\033[93m"  # Yellow
    else:
        color = "\033[91m"  # Red

    reset = "\033[0m"
    return f"{color}{bar}{reset}"


def get_python_processes():
    """Find Python processes using significant memory"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if 'python' in proc.info['name'].lower():
                mem_gb = proc.info['memory_info'].rss / (1024**3)
                if mem_gb > 0.5:  # Only show processes using > 0.5GB
                    processes.append({
                        'pid': proc.info['pid'],
                        'mem_gb': mem_gb,
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(processes, key=lambda x: x['mem_gb'], reverse=True)


def main():
    print("\033[2J\033[H")  # Clear screen
    print("=" * 60)
    print("🔍 MLX Training Memory Monitor")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print()
    print("Safe zones for 16GB Mac:")
    print("  \033[92m< 10GB\033[0m : Safe")
    print("  \033[93m10-12GB\033[0m: Training zone (normal)")
    print("  \033[91m> 14GB\033[0m : Danger - may crash!")
    print()
    print("-" * 60)

    try:
        while True:
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            available_gb = mem.available / (1024**3)
            percent = mem.percent

            # Move cursor up and clear lines
            print(f"\033[2K\rMemory: {get_memory_bar(percent)} {percent:.1f}%")
            print(f"\033[2K\rUsed: {used_gb:.1f}GB / {total_gb:.1f}GB | Available: {available_gb:.1f}GB")

            # Status message
            if available_gb < 2:
                print(f"\033[2K\r\033[91m⚠️  CRITICAL: Only {available_gb:.1f}GB available! STOP TRAINING!\033[0m")
            elif available_gb < 4:
                print(f"\033[2K\r\033[91m⚠️  WARNING: Memory pressure high. Consider stopping.\033[0m")
            elif available_gb < 6:
                print(f"\033[2K\r\033[93m⚡ Training zone - monitor closely.\033[0m")
            else:
                print(f"\033[2K\r\033[92m✓ Memory looks good.\033[0m")

            # Show Python processes
            python_procs = get_python_processes()
            if python_procs:
                print(f"\033[2K\r")
                print(f"\033[2K\rPython processes:")
                for proc in python_procs[:3]:
                    print(f"\033[2K\r  PID {proc['pid']}: {proc['mem_gb']:.1f}GB")

            # Move cursor back up for next iteration
            lines_to_move = 5 + min(len(python_procs), 3)
            print(f"\033[{lines_to_move}A", end='')

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n" * 10)  # Clear monitor output
        print("Monitor stopped.")


if __name__ == "__main__":
    main()
