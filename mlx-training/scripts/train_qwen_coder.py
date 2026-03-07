#!/usr/bin/env python3
"""
MLX Fine-tuning Script for Qwen Coder on Apple Silicon
Optimized for M3 Pro with 18GB RAM using LoRA
"""

import os
import sys
import subprocess
import psutil

def check_memory():
    """Check available memory before training"""
    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024**3)
    total_gb = mem.total / (1024**3)
    print(f"Memory: {available_gb:.1f}GB available / {total_gb:.1f}GB total")

    if available_gb < 10:
        print("WARNING: Less than 10GB available. Close other apps for best results.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    return available_gb

def main():
    print("=" * 60)
    print("MLX Fine-tuning: Qwen 2.5 Coder 7B")
    print("Using LoRA for memory-efficient training")
    print("=" * 60)
    print()

    # Check memory
    check_memory()
    print()

    # Training parameters optimized for 18GB RAM
    model = "Qwen/Qwen2.5-Coder-7B-Instruct"
    data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_data = os.path.join(data_dir, "data", "train.jsonl")
    adapter_path = os.path.join(data_dir, "models", "qwen-coder-lora")

    # Verify training data exists
    if not os.path.exists(train_data):
        print(f"ERROR: Training data not found at {train_data}")
        print("Please add your training data in JSONL format.")
        sys.exit(1)

    # Count training examples
    with open(train_data) as f:
        num_examples = sum(1 for _ in f)
    print(f"Training examples: {num_examples}")

    if num_examples < 10:
        print("WARNING: Very few training examples. Consider adding more data.")

    print()
    print("Starting fine-tuning with LoRA...")
    print(f"  Model: {model}")
    print(f"  Data: {train_data}")
    print(f"  Output: {adapter_path}")
    print()

    # Build the MLX-LM fine-tuning command
    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", model,
        "--train",
        "--data", os.path.dirname(train_data),
        "--adapter-path", adapter_path,
        "--batch-size", "1",           # Conservative for 18GB
        "--lora-layers", "16",         # Fine-tune 16 layers
        "--lora-rank", "8",            # Rank 8 for efficiency
        "--iters", "100",              # Start small, increase if needed
        "--learning-rate", "1e-5",
        "--save-every", "50",
    ]

    print("Command:", " ".join(cmd))
    print()
    print("-" * 60)

    try:
        # Run training
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Stream output
        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode == 0:
            print()
            print("=" * 60)
            print("SUCCESS! LoRA adapter saved to:", adapter_path)
            print()
            print("To use the fine-tuned model:")
            print(f"  python -m mlx_lm.generate --model {model} --adapter-path {adapter_path}")
            print()
            print("To convert to Ollama format, run:")
            print("  python scripts/convert_to_ollama.py")
            print("=" * 60)
        else:
            print(f"Training failed with exit code {process.returncode}")

    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        process.terminate()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
