#!/usr/bin/env python3
"""
Download and prepare Hugging Face datasets for MLX fine-tuning
"""

import json
import os
import sys
from datasets import load_dataset

# Available datasets
DATASETS = {
    "1": {
        "name": "iamtarun/python_code_instructions_18k",
        "desc": "18k Python instructions (recommended for Python focus)",
        "size": "~50MB",
        "format": "instruction"
    },
    "2": {
        "name": "sahil2801/CodeAlpaca-20k",
        "desc": "20k code instructions (multi-language)",
        "size": "~30MB",
        "format": "alpaca"
    },
    "3": {
        "name": "nickrosh/Evol-Instruct-Code-80k",
        "desc": "80k evolved code instructions (larger, higher quality)",
        "size": "~150MB",
        "format": "evol"
    },
    "4": {
        "name": "TokenBender/code_instructions_122k",
        "desc": "122k code instructions (largest)",
        "size": "~200MB",
        "format": "instruction"
    },
}

def format_for_qwen(instruction: str, output: str, input_text: str = "") -> str:
    """Format example for Qwen chat template"""
    system = "You are an expert programmer. Write clean, efficient, well-documented code."

    user_content = instruction
    if input_text and input_text.strip():
        user_content = f"{instruction}\n\nInput:\n{input_text}"

    return json.dumps({
        "text": f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n{output}<|im_end|>"
    })

def download_and_prepare(dataset_key: str, max_examples: int = 5000):
    """Download dataset and convert to MLX format"""

    if dataset_key not in DATASETS:
        print(f"Invalid choice: {dataset_key}")
        return

    ds_info = DATASETS[dataset_key]
    ds_name = ds_info["name"]
    ds_format = ds_info["format"]

    print(f"Downloading: {ds_name}")
    print(f"This may take a few minutes...")
    print()

    try:
        dataset = load_dataset(ds_name, split="train")
        print(f"Total examples in dataset: {len(dataset)}")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    # Limit examples
    if len(dataset) > max_examples:
        print(f"Using first {max_examples} examples (of {len(dataset)})")
        dataset = dataset.select(range(max_examples))

    # Prepare output
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_file = os.path.join(base_dir, "data", "train.jsonl")
    valid_file = os.path.join(base_dir, "data", "valid.jsonl")

    # Convert to MLX format
    print(f"Converting to Qwen chat format...")

    train_examples = []
    valid_examples = []

    for i, example in enumerate(dataset):
        try:
            # Handle different dataset formats
            if ds_format == "alpaca":
                instruction = example.get("instruction", "")
                input_text = example.get("input", "")
                output = example.get("output", "")
            elif ds_format == "evol":
                instruction = example.get("instruction", "")
                input_text = ""
                output = example.get("output", "")
            else:  # instruction format
                instruction = example.get("instruction", example.get("prompt", ""))
                input_text = example.get("input", "")
                output = example.get("output", example.get("response", ""))

            if not instruction or not output:
                continue

            formatted = format_for_qwen(instruction, output, input_text)

            # 90% train, 10% validation
            if i % 10 == 0:
                valid_examples.append(formatted)
            else:
                train_examples.append(formatted)

        except Exception as e:
            continue

    # Write files
    with open(output_file, "w") as f:
        f.write("\n".join(train_examples))

    with open(valid_file, "w") as f:
        f.write("\n".join(valid_examples))

    print()
    print("=" * 60)
    print(f"SUCCESS!")
    print(f"  Training examples: {len(train_examples)}")
    print(f"  Validation examples: {len(valid_examples)}")
    print(f"  Saved to: {output_file}")
    print("=" * 60)
    print()
    print("Next step: Run training with:")
    print("  python scripts/train_qwen_coder.py")

def main():
    print("=" * 60)
    print("Hugging Face Dataset Downloader for MLX Fine-tuning")
    print("=" * 60)
    print()

    print("Available datasets:")
    print()
    for key, info in DATASETS.items():
        print(f"  [{key}] {info['name']}")
        print(f"      {info['desc']}")
        print(f"      Size: {info['size']}")
        print()

    choice = input("Select dataset (1-4): ").strip()

    if choice not in DATASETS:
        print("Invalid choice")
        return

    # Ask for max examples
    max_str = input("Max examples to use (default 5000, press Enter for default): ").strip()
    max_examples = int(max_str) if max_str else 5000

    print()
    download_and_prepare(choice, max_examples)

if __name__ == "__main__":
    main()
