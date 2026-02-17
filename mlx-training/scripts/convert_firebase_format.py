#!/usr/bin/env python3
"""
Convert Firebase training data from messages format to text format.
"""

import json
from pathlib import Path

def messages_to_text(messages: list) -> str:
    """Convert messages array to Qwen chat format text."""
    parts = []
    for msg in messages:
        role = msg['role']
        content = msg['content']
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    return '\n'.join(parts)

def convert_file(input_path: str, output_path: str):
    """Convert a JSONL file from messages to text format."""
    converted = []

    with open(input_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)

            if 'messages' in data:
                # Convert to text format
                text = messages_to_text(data['messages'])
                converted.append({'text': text})
            elif 'text' in data:
                # Already in correct format
                converted.append(data)

    with open(output_path, 'w') as f:
        for item in converted:
            f.write(json.dumps(item) + '\n')

    return len(converted)

def main():
    base_dir = Path("/Users/fredtaylor/Development/Projects/AITeamPlatform/mlx-training")

    # Convert Firebase data to text format
    firebase_dir = base_dir / "data/firebase"

    train_count = convert_file(
        firebase_dir / "train.jsonl",
        firebase_dir / "train_text.jsonl"
    )
    valid_count = convert_file(
        firebase_dir / "valid.jsonl",
        firebase_dir / "valid_text.jsonl"
    )

    print(f"Converted {train_count} training examples")
    print(f"Converted {valid_count} validation examples")

    # Now merge with existing data
    print("\nMerging with existing training data...")

    # Load existing data
    existing_train = []
    with open(base_dir / "data/train.jsonl", 'r') as f:
        for line in f:
            if line.strip():
                existing_train.append(json.loads(line))

    existing_valid = []
    with open(base_dir / "data/valid.jsonl", 'r') as f:
        for line in f:
            if line.strip():
                existing_valid.append(json.loads(line))

    # Load converted Firebase data
    firebase_train = []
    with open(firebase_dir / "train_text.jsonl", 'r') as f:
        for line in f:
            if line.strip():
                firebase_train.append(json.loads(line))

    firebase_valid = []
    with open(firebase_dir / "valid_text.jsonl", 'r') as f:
        for line in f:
            if line.strip():
                firebase_valid.append(json.loads(line))

    # Merge
    merged_train = existing_train + firebase_train
    merged_valid = existing_valid + firebase_valid

    # Shuffle
    import random
    random.shuffle(merged_train)
    random.shuffle(merged_valid)

    # Save to merged directory
    merged_dir = base_dir / "data/merged"
    merged_dir.mkdir(parents=True, exist_ok=True)

    with open(merged_dir / "train.jsonl", 'w') as f:
        for item in merged_train:
            f.write(json.dumps(item) + '\n')

    with open(merged_dir / "valid.jsonl", 'w') as f:
        for item in merged_valid:
            f.write(json.dumps(item) + '\n')

    print(f"\nMerged training: {len(merged_train)} examples")
    print(f"Merged validation: {len(merged_valid)} examples")
    print(f"Firebase ratio: {len(firebase_train) / len(merged_train) * 100:.2f}%")

    # Verify format
    print("\nSample merged entry:")
    sample = merged_train[0]['text'][:200] + "..."
    print(sample)

if __name__ == "__main__":
    main()
