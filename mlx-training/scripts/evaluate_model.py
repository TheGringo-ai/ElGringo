#!/usr/bin/env python3
"""
Evaluate the fine-tuned model against test cases.
Compares custom model vs base model on Firebase/Firestore tasks.
"""

import subprocess
import json
import time
from typing import Dict, List, Tuple

# Test cases with expected patterns (things the response SHOULD contain)
TEST_CASES = [
    {
        "name": "Firestore Add Document",
        "prompt": "Write Python code to add a document to Firestore with auto-generated ID",
        "expected_patterns": [
            "firestore",
            ".add(",
            "collection",
        ],
        "forbidden_patterns": [
            "mongodb",
            "sql",
        ]
    },
    {
        "name": "Firestore Query with Filter",
        "prompt": "Write Python code to query Firestore for users where age is greater than 18",
        "expected_patterns": [
            ".where(",
            ">=",
            "stream()",
        ],
        "forbidden_patterns": []
    },
    {
        "name": "Firestore Transaction",
        "prompt": "Write Python code for a Firestore transaction that transfers money between accounts",
        "expected_patterns": [
            "transaction",
            "@firestore.transactional",
            "update",
        ],
        "forbidden_patterns": []
    },
    {
        "name": "Security Rules",
        "prompt": "Write Firestore security rules where users can only read their own data",
        "expected_patterns": [
            "rules_version",
            "request.auth",
            "allow read",
        ],
        "forbidden_patterns": []
    },
    {
        "name": "Cloud Function Trigger",
        "prompt": "Write a Firebase Cloud Function that triggers when a document is created",
        "expected_patterns": [
            "functions.firestore",
            "onCreate",
            "snapshot",
        ],
        "forbidden_patterns": []
    },
    {
        "name": "JavaScript Firestore",
        "prompt": "Write TypeScript code to get a document from Firestore in a React app",
        "expected_patterns": [
            "getDoc",
            "doc(",
            "firestore",
        ],
        "forbidden_patterns": []
    },
    {
        "name": "Batch Write",
        "prompt": "Write Python code to batch write 1000 documents to Firestore efficiently",
        "expected_patterns": [
            "batch",
            "commit",
            "500",  # Should mention 500 limit
        ],
        "forbidden_patterns": []
    },
    {
        "name": "Real-time Listener",
        "prompt": "Write JavaScript code to listen for real-time updates on a Firestore collection",
        "expected_patterns": [
            "onSnapshot",
            "collection",
        ],
        "forbidden_patterns": []
    },
    # General coding (to ensure no degradation)
    {
        "name": "General Python",
        "prompt": "Write a Python function to find the longest palindrome in a string",
        "expected_patterns": [
            "def ",
            "return",
            "palindrome",
        ],
        "forbidden_patterns": []
    },
    {
        "name": "General Algorithm",
        "prompt": "Write Python code to implement binary search",
        "expected_patterns": [
            "def ",
            "mid",
            "left",
            "right",
        ],
        "forbidden_patterns": []
    },
]


def query_model(model: str, prompt: str, timeout: int = 120) -> str:
    """Query Ollama model and return response."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate", "-d",
             json.dumps({"model": model, "prompt": prompt, "stream": False})],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        response = json.loads(result.stdout)
        return response.get("response", "")
    except Exception as e:
        return f"ERROR: {e}"


def evaluate_response(response: str, expected: List[str], forbidden: List[str]) -> Tuple[float, List[str]]:
    """
    Evaluate response against expected and forbidden patterns.
    Returns (score, issues)
    """
    response_lower = response.lower()
    issues = []

    # Check expected patterns
    expected_found = 0
    for pattern in expected:
        if pattern.lower() in response_lower:
            expected_found += 1
        else:
            issues.append(f"Missing: '{pattern}'")

    # Check forbidden patterns
    forbidden_found = 0
    for pattern in forbidden:
        if pattern.lower() in response_lower:
            forbidden_found += 1
            issues.append(f"Forbidden: '{pattern}'")

    # Calculate score
    if not expected:
        score = 1.0 if not forbidden_found else 0.5
    else:
        score = expected_found / len(expected)
        if forbidden_found:
            score *= 0.5  # Penalty for forbidden patterns

    return score, issues


def run_evaluation(models: List[str]):
    """Run evaluation on all test cases for given models."""
    results = {model: {"scores": [], "details": []} for model in models}

    print("=" * 70)
    print("MODEL EVALUATION")
    print("=" * 70)

    for i, test in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] {test['name']}")
        print(f"  Prompt: {test['prompt'][:60]}...")

        for model in models:
            print(f"  Testing {model}...", end=" ", flush=True)

            start = time.time()
            response = query_model(model, test["prompt"])
            elapsed = time.time() - start

            score, issues = evaluate_response(
                response,
                test["expected_patterns"],
                test.get("forbidden_patterns", [])
            )

            results[model]["scores"].append(score)
            results[model]["details"].append({
                "name": test["name"],
                "score": score,
                "issues": issues,
                "time": elapsed,
                "response_length": len(response)
            })

            status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
            print(f"{status} Score: {score:.2f} ({elapsed:.1f}s)")

            if issues and score < 1.0:
                for issue in issues[:2]:  # Show first 2 issues
                    print(f"    - {issue}")

    return results


def print_summary(results: Dict):
    """Print evaluation summary."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for model, data in results.items():
        scores = data["scores"]
        avg_score = sum(scores) / len(scores) if scores else 0
        passed = sum(1 for s in scores if s >= 0.8)

        print(f"\n{model}:")
        print(f"  Average Score: {avg_score:.2%}")
        print(f"  Tests Passed (≥80%): {passed}/{len(scores)}")

        # Category breakdown
        firebase_scores = scores[:8]  # First 8 are Firebase tests
        general_scores = scores[8:]   # Last 2 are general coding

        if firebase_scores:
            print(f"  Firebase Tasks: {sum(firebase_scores)/len(firebase_scores):.2%}")
        if general_scores:
            print(f"  General Coding: {sum(general_scores)/len(general_scores):.2%}")

    # Comparison
    if len(results) > 1:
        models = list(results.keys())
        scores1 = results[models[0]]["scores"]
        scores2 = results[models[1]]["scores"]

        improvement = sum(s1 - s2 for s1, s2 in zip(scores1, scores2)) / len(scores1)

        print(f"\n{'=' * 70}")
        if improvement > 0:
            print(f"✅ {models[0]} is {improvement:.1%} better than {models[1]}")
        elif improvement < 0:
            print(f"⚠️ {models[0]} is {-improvement:.1%} worse than {models[1]}")
        else:
            print("➡️ Both models perform equally")


def main():
    print("Checking available models...")

    # Check which models are available
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    available = result.stdout

    models_to_test = []

    if "qwen-coder-custom" in available:
        models_to_test.append("qwen-coder-custom")

    # Try to find base model for comparison
    base_models = ["qwen2.5-coder:7b", "qwen2.5-coder:7b-instruct", "codellama:7b"]
    for base in base_models:
        if base in available:
            models_to_test.append(base)
            break

    if not models_to_test:
        print("No models found! Make sure Ollama is running with your models.")
        return

    print(f"Testing models: {', '.join(models_to_test)}")

    results = run_evaluation(models_to_test)
    print_summary(results)

    # Save detailed results
    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results saved to evaluation_results.json")


if __name__ == "__main__":
    main()
