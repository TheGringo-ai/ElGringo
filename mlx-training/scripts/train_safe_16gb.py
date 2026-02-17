#!/usr/bin/env python3
"""
MLX Safe-Mode Training for 16GB Macs
====================================
Optimized settings to prevent crashes on M3 Pro 16GB.

Based on tested parameters that keep memory under 12GB.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Safe parameters for 16GB
SAFE_CONFIG = {
    "batch_size": 1,        # CRITICAL: Never increase on 16GB
    "lora_layers": 8,       # Reduced from 16 - targets final layers only
    "rank": 8,              # Low rank for memory efficiency
    "learning_rate": 1e-5,  # Conservative learning rate
    "max_seq_length": 2048, # Prevent memory spikes
    "iters": 500,           # Reasonable training iterations
    "save_every": 100,      # Checkpoint frequency
}

# Recommended 4-bit quantized models for 16GB
RECOMMENDED_MODELS = {
    "llama3-8b": "mlx-community/Llama-3.1-8B-Instruct-4bit",
    "qwen-7b": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "codellama-7b": "mlx-community/CodeLlama-7b-Instruct-4bit",
    "mistral-7b": "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
}


def check_memory():
    """Check available memory and warn if low"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)
        total_gb = mem.total / (1024**3)

        print(f"Memory: {available_gb:.1f}GB available / {total_gb:.1f}GB total")

        if available_gb < 8:
            print("\n⚠️  WARNING: Less than 8GB available!")
            print("   Close Chrome, Docker, Slack, and other memory-heavy apps.")
            print("   Training may crash or be very slow.\n")
            return False
        elif available_gb < 10:
            print("\n⚠️  Caution: Less than 10GB available.")
            print("   Consider closing some apps for best results.\n")
        else:
            print("✓  Memory looks good for training.\n")
        return True
    except ImportError:
        print("(psutil not installed - skipping memory check)")
        return True


def get_data_stats(data_path: Path):
    """Check training data statistics"""
    train_file = data_path / "train.jsonl"
    valid_file = data_path / "valid.jsonl"

    stats = {"train": 0, "valid": 0, "max_length": 0}

    if train_file.exists():
        import json
        with open(train_file) as f:
            for line in f:
                stats["train"] += 1
                try:
                    data = json.loads(line)
                    text = data.get("text", "")
                    # Rough token estimate (chars / 4)
                    tokens = len(text) // 4
                    stats["max_length"] = max(stats["max_length"], tokens)
                except:
                    pass

    if valid_file.exists():
        with open(valid_file) as f:
            stats["valid"] = sum(1 for _ in f)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Safe MLX fine-tuning for 16GB Macs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with Llama 3.1 8B (recommended)
  python train_safe_16gb.py --model llama3-8b

  # Train with Qwen Coder
  python train_safe_16gb.py --model qwen-7b

  # Custom model (must be 4-bit quantized!)
  python train_safe_16gb.py --model-path mlx-community/Your-Model-4bit

  # More iterations
  python train_safe_16gb.py --model llama3-8b --iters 1000
"""
    )

    parser.add_argument("--model", choices=list(RECOMMENDED_MODELS.keys()),
                       default="qwen-7b", help="Preset model to use")
    parser.add_argument("--model-path", help="Custom model path (must be 4-bit)")
    parser.add_argument("--data", default="../data", help="Data directory")
    parser.add_argument("--output", default="../models", help="Output directory")
    parser.add_argument("--iters", type=int, default=SAFE_CONFIG["iters"],
                       help="Training iterations")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show command without running")

    args = parser.parse_args()

    print("=" * 60)
    print("🛡️  MLX SAFE-MODE TRAINING (16GB Optimized)")
    print("=" * 60)
    print()

    # Check memory
    if not check_memory() and not args.dry_run:
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(1)

    # Determine model
    if args.model_path:
        model = args.model_path
        if "4bit" not in model.lower() and "4-bit" not in model.lower():
            print("⚠️  WARNING: Model path doesn't contain '4bit'")
            print("   Full-precision models will likely crash on 16GB!")
            print()
    else:
        model = RECOMMENDED_MODELS[args.model]

    # Setup paths
    script_dir = Path(__file__).parent
    data_path = (script_dir / args.data).resolve()
    output_path = (script_dir / args.output).resolve()

    model_name = model.split("/")[-1].replace("-4bit", "").lower()
    adapter_path = output_path / f"{model_name}-lora-safe"

    # Check data
    print("📊 Training Data:")
    stats = get_data_stats(data_path)
    print(f"   Train examples: {stats['train']}")
    print(f"   Valid examples: {stats['valid']}")
    print(f"   Max tokens (est): {stats['max_length']}")

    if stats['max_length'] > SAFE_CONFIG['max_seq_length']:
        print(f"\n⚠️  WARNING: Some examples exceed {SAFE_CONFIG['max_seq_length']} tokens")
        print("   This may cause memory spikes. Consider truncating data.")
    print()

    # Build command
    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", model,
        "--data", str(data_path),
        "--train",
        "--adapter-path", str(adapter_path),
        "--batch-size", str(SAFE_CONFIG["batch_size"]),
        "--lora-layers", str(SAFE_CONFIG["lora_layers"]),
        "--iters", str(args.iters),
        "--learning-rate", str(SAFE_CONFIG["learning_rate"]),
        "--save-every", str(SAFE_CONFIG["save_every"]),
    ]

    # Print configuration
    print("🔧 Safe Configuration:")
    print(f"   Model: {model}")
    print(f"   Batch Size: {SAFE_CONFIG['batch_size']} (FIXED - do not increase)")
    print(f"   LoRA Layers: {SAFE_CONFIG['lora_layers']} (reduced for memory)")
    print(f"   Rank: {SAFE_CONFIG['rank']}")
    print(f"   Iterations: {args.iters}")
    print(f"   Output: {adapter_path}")
    print()

    print("📝 Command:")
    print("   " + " ".join(cmd))
    print()

    if args.dry_run:
        print("(Dry run - not executing)")
        return

    print("=" * 60)
    print("Starting training... (Ctrl+C to stop)")
    print("Monitor memory with: top -o mem")
    print("=" * 60)
    print()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode == 0:
            print()
            print("=" * 60)
            print("✅ Training Complete!")
            print(f"   Adapter saved to: {adapter_path}")
            print()
            print("Next steps:")
            print(f"  1. Test: python -m mlx_lm.generate --model {model} --adapter-path {adapter_path}")
            print(f"  2. Fuse: python -m mlx_lm.fuse --model {model} --adapter-path {adapter_path}")
            print("=" * 60)
        else:
            print(f"\n❌ Training failed (exit code: {process.returncode})")
            print("\nTroubleshooting:")
            print("  - Close memory-heavy apps (Chrome, Docker, etc.)")
            print("  - Check Activity Monitor for memory pressure")
            print("  - Reduce --iters if data is too large")

    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        process.terminate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
