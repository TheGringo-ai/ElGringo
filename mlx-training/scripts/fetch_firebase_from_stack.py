#!/usr/bin/env python3
"""
Fetch Firebase/Firestore code examples from TheStack dataset.
Filters for files containing Firebase imports and formats for training.
"""

import json
from pathlib import Path
from datasets import load_dataset
import re
from typing import List, Dict, Optional

# Firebase-related patterns to search for
FIREBASE_PATTERNS = [
    # Python
    r'from firebase_admin import',
    r'import firebase_admin',
    r'firestore\.client\(\)',
    # JavaScript/TypeScript
    r'from [\'"]firebase/',
    r'import.*firebase/',
    r'getFirestore\(',
    r'initializeApp\(',
    r'collection\s*\(',
    r'doc\s*\(',
    r'firebase\.firestore\(',
    r'admin\.firestore\(',
    # Security Rules
    r'rules_version',
    r'service cloud\.firestore',
]

def contains_firebase(content: str) -> bool:
    """Check if content contains Firebase-related code."""
    for pattern in FIREBASE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    return False

def extract_firebase_snippet(content: str) -> Optional[str]:
    """Extract a meaningful Firebase code snippet."""
    lines = content.split('\n')

    # Find lines with Firebase imports/usage
    firebase_lines = []
    in_firebase_block = False
    block_start = 0

    for i, line in enumerate(lines):
        for pattern in FIREBASE_PATTERNS:
            if re.search(pattern, line):
                in_firebase_block = True
                block_start = max(0, i - 2)
                break

        if in_firebase_block:
            firebase_lines.append(line)
            # Continue block until we hit an empty line or end
            if i > block_start + 5 and (line.strip() == '' or i - block_start > 50):
                break

    if firebase_lines:
        return '\n'.join(firebase_lines[:60])  # Limit to 60 lines
    return None

def create_instruction_from_code(code: str, lang: str) -> str:
    """Generate an instruction based on code content."""
    code_lower = code.lower()

    # Detect what the code does
    if 'add(' in code_lower or 'adddoc(' in code_lower:
        return f"Write {lang} code to add a document to Firestore"
    elif 'get(' in code_lower or 'getdoc(' in code_lower:
        return f"Write {lang} code to read a document from Firestore"
    elif 'update(' in code_lower or 'updatedoc(' in code_lower:
        return f"Write {lang} code to update a Firestore document"
    elif 'delete(' in code_lower or 'deletedoc(' in code_lower:
        return f"Write {lang} code to delete a Firestore document"
    elif 'where(' in code_lower:
        return f"Write {lang} code to query Firestore with filters"
    elif 'transaction' in code_lower:
        return f"Write {lang} code for a Firestore transaction"
    elif 'batch' in code_lower or 'writebatch' in code_lower:
        return f"Write {lang} code for Firestore batch operations"
    elif 'onsnapshot' in code_lower or 'on_snapshot' in code_lower:
        return f"Write {lang} code for real-time Firestore listeners"
    elif 'auth' in code_lower and 'verify' in code_lower:
        return f"Write {lang} code to verify Firebase authentication"
    elif 'createuser' in code_lower or 'create_user' in code_lower:
        return f"Write {lang} code to create a Firebase user"
    elif 'rules_version' in code_lower:
        return "Write Firestore security rules"
    elif 'functions.' in code_lower:
        return "Write a Firebase Cloud Function"
    else:
        return f"Write {lang} code for Firebase/Firestore operations"

def fetch_from_thestack(max_examples: int = 500) -> List[Dict]:
    """Fetch Firebase examples from TheStack dataset."""
    examples = []

    # Load subsets for Python and JavaScript
    languages = [
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('typescript', 'TypeScript'),
    ]

    for lang_code, lang_name in languages:
        print(f"Fetching {lang_name} examples...")

        try:
            # Load a sample of the dataset
            dataset = load_dataset(
                "bigcode/the-stack",
                data_dir=f"data/{lang_code}",
                split="train",
                streaming=True,
                trust_remote_code=True
            )

            count = 0
            for sample in dataset:
                if count >= max_examples // len(languages):
                    break

                content = sample.get('content', '')

                if len(content) < 100 or len(content) > 10000:
                    continue

                if not contains_firebase(content):
                    continue

                snippet = extract_firebase_snippet(content)
                if not snippet or len(snippet) < 50:
                    continue

                instruction = create_instruction_from_code(snippet, lang_name)

                examples.append({
                    "messages": [
                        {"role": "system", "content": "You are an expert Firebase and Firestore developer. Write clean, efficient code."},
                        {"role": "user", "content": instruction},
                        {"role": "assistant", "content": snippet}
                    ]
                })
                count += 1

                if count % 10 == 0:
                    print(f"  Found {count} {lang_name} examples...")

        except Exception as e:
            print(f"Error loading {lang_name}: {e}")
            continue

    return examples

def main():
    print("Fetching Firebase examples from TheStack...")
    print("Note: This requires Hugging Face authentication for TheStack")
    print("Run: huggingface-cli login")

    try:
        examples = fetch_from_thestack(max_examples=300)
    except Exception as e:
        print(f"Could not fetch from TheStack: {e}")
        print("Using synthetic data only...")
        examples = []

    if examples:
        output_dir = Path(__file__).resolve().parent.parent / "data" / "firebase_stack"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Split 90/10
        split_idx = int(len(examples) * 0.9)
        train = examples[:split_idx]
        valid = examples[split_idx:]

        with open(output_dir / "train.jsonl", "w") as f:
            for ex in train:
                f.write(json.dumps(ex) + "\n")

        with open(output_dir / "valid.jsonl", "w") as f:
            for ex in valid:
                f.write(json.dumps(ex) + "\n")

        print(f"Saved {len(train)} training examples")
        print(f"Saved {len(valid)} validation examples")
    else:
        print("No examples fetched - proceeding with synthetic data only")

if __name__ == "__main__":
    main()
