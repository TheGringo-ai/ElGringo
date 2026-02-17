#!/usr/bin/env python3
"""
Merge Firebase data with existing training data.
Validates quality and maintains proper ratio.
"""

import json
from pathlib import Path
import random

def load_jsonl(path: str) -> list:
    """Load JSONL file."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def save_jsonl(data: list, path: str):
    """Save to JSONL file."""
    with open(path, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

def validate_example(example: dict) -> bool:
    """Validate a training example has proper structure."""
    if 'messages' not in example:
        return False
    messages = example['messages']
    if len(messages) < 2:
        return False
    # Check for user and assistant messages
    roles = [m.get('role') for m in messages]
    if 'user' not in roles or 'assistant' not in roles:
        return False
    # Check content length
    for msg in messages:
        content = msg.get('content', '')
        if len(content) < 10:
            return False
    return True

def main():
    base_dir = Path("/Users/fredtaylor/Development/Projects/AITeamPlatform/mlx-training")

    # Load existing training data
    print("Loading existing training data...")
    existing_train = load_jsonl(base_dir / "data/train.jsonl")
    existing_valid = load_jsonl(base_dir / "data/valid.jsonl")
    print(f"  Existing: {len(existing_train)} train, {len(existing_valid)} valid")

    # Load Firebase data
    print("Loading Firebase data...")
    firebase_train = load_jsonl(base_dir / "data/firebase/train.jsonl")
    firebase_valid = load_jsonl(base_dir / "data/firebase/valid.jsonl")
    print(f"  Firebase: {len(firebase_train)} train, {len(firebase_valid)} valid")

    # Validate Firebase examples
    print("\nValidating Firebase examples...")
    valid_firebase_train = [ex for ex in firebase_train if validate_example(ex)]
    valid_firebase_valid = [ex for ex in firebase_valid if validate_example(ex)]
    print(f"  Valid: {len(valid_firebase_train)} train, {len(valid_firebase_valid)} valid")

    # Calculate ratio
    total_after = len(existing_train) + len(valid_firebase_train)
    firebase_ratio = len(valid_firebase_train) / total_after * 100
    print(f"\nFirebase ratio: {firebase_ratio:.2f}% (target: <20%)")

    # Merge data
    print("\nMerging data...")
    merged_train = existing_train + valid_firebase_train
    merged_valid = existing_valid + valid_firebase_valid

    # Shuffle
    random.shuffle(merged_train)
    random.shuffle(merged_valid)

    # Save merged data
    output_dir = base_dir / "data/merged"
    output_dir.mkdir(parents=True, exist_ok=True)

    save_jsonl(merged_train, output_dir / "train.jsonl")
    save_jsonl(merged_valid, output_dir / "valid.jsonl")

    print(f"\nSaved merged data to {output_dir}")
    print(f"  Training: {len(merged_train)} examples")
    print(f"  Validation: {len(merged_valid)} examples")

    # Show sample Firebase examples
    print("\n--- Sample Firebase Examples ---")
    for i, ex in enumerate(valid_firebase_train[:3]):
        user_msg = ex['messages'][1]['content']
        print(f"\n{i+1}. {user_msg[:80]}...")

if __name__ == "__main__":
    main()
