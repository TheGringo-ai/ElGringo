#!/usr/bin/env python3
"""
Firebase Real-World Examples
============================

Demonstrates the AITeamPlatform's Firebase capabilities using real-world scenarios.
These examples showcase:
1. Firebase documentation RAG retrieval
2. Code validation pipeline
3. Security rules analysis
4. Semantic delta for code reviews

Usage:
    python examples/firebase_real_world.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def demo_firebase_rag():
    """Demonstrate Firebase documentation RAG."""
    print("\n" + "="*60)
    print("Demo 1: Firebase Documentation RAG")
    print("="*60)

    from elgringo.knowledge import get_firebase_docs

    docs = get_firebase_docs()

    # Example queries a developer might ask
    queries = [
        "How do I batch write documents in Firestore?",
        "What are security rules best practices?",
        "How to handle authentication state changes?",
        "Cloud Functions trigger types",
        "Firestore transaction example",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        results = docs.search(query, top_k=2)
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}: [{result.category}]")
            print(f"  Score: {result.relevance_score:.3f}")
            preview = result.content[:150].replace('\n', ' ')
            print(f"  Preview: {preview}...")


async def demo_code_validation():
    """Demonstrate code validation pipeline."""
    print("\n" + "="*60)
    print("Demo 2: Code Validation Pipeline")
    print("="*60)

    from elgringo.validation import get_validator

    validator = get_validator()

    # Example code snippets with issues
    examples = [
        # JavaScript with issues
        {
            "language": "javascript",
            "code": """
// Firebase code with potential issues
async function getUserData(userId) {
    const doc = db.collection('users').doc(userId).get();  // Missing await
    return doc.data();
}

function updateUser(userId, data) {
    db.collection('users').doc(userId).set(data);  // Missing await and error handling
}

for (let user of users) {
    db.collection('logs').add({ user: user.id });  // No batch
}
""",
            "description": "JavaScript with missing await and batch writes",
        },
        # Python with issues
        {
            "language": "python",
            "code": """
# Firebase Admin SDK code
def get_user(uid):
    doc = db.collection('users').document(uid).get()
    return doc.to_dict()

def update_users(users):
    for user in users:
        db.collection('users').document(user['id']).set(user)  # Should use batch
""",
            "description": "Python with no batching",
        },
        # Security rules with issues
        {
            "language": "firestore_rules",
            "code": """
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if true;  // DANGEROUS!
    }
    match /public/{doc} {
      allow read: if true;
      allow write: if request.auth != null;  // OK but no validation
    }
  }
}
""",
            "description": "Security rules with vulnerabilities",
        },
    ]

    for example in examples:
        print(f"\n{example['description']}:")
        print("-" * 40)
        print(f"Language: {example['language']}")

        result = validator.validate(example['code'], example['language'])

        if result.valid:
            print("Status: VALID")
        else:
            print("Status: ISSUES FOUND")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors[:3]:
                print(f"  - Line {err.line}: {err.message}")

        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warn in result.warnings[:3]:
                print(f"  - {warn.message}")

        if result.suggestions:
            print(f"\nSuggestions ({len(result.suggestions)}):")
            for sug in result.suggestions[:2]:
                print(f"  - {sug}")


async def demo_semantic_delta():
    """Demonstrate semantic delta for code reviews."""
    print("\n" + "="*60)
    print("Demo 3: Semantic Delta for Code Reviews")
    print("="*60)

    from elgringo.intelligence import SemanticDeltaExtractor

    extractor = SemanticDeltaExtractor(use_mlx=False)

    # Simulate a code change
    old_code = '''
class UserService:
    """Handles user operations."""

    def __init__(self, db):
        self.db = db

    def get_user(self, uid: str) -> dict:
        """Get user by ID."""
        doc = self.db.collection("users").document(uid).get()
        return doc.to_dict()

    def create_user(self, data: dict) -> str:
        """Create a new user."""
        ref = self.db.collection("users").add(data)
        return ref.id
'''

    new_code = '''
class UserService:
    """Handles user operations with validation."""

    def __init__(self, db, validator=None):
        self.db = db
        self.validator = validator

    def get_user(self, uid: str) -> dict:
        """Get user by ID with error handling."""
        try:
            doc = self.db.collection("users").document(uid).get()
            if not doc.exists:
                return None
            return doc.to_dict()
        except Exception as e:
            logger.error(f"Failed to get user {uid}: {e}")
            raise

    def create_user(self, data: dict) -> str:
        """Create a new user with validation."""
        if self.validator:
            self.validator.validate(data)

        ref = self.db.collection("users").add(data)
        return ref.id

    def update_user(self, uid: str, data: dict) -> None:
        """Update an existing user."""
        self.db.collection("users").document(uid).update(data)
'''

    print("Analyzing code change...")
    delta = extractor.extract_delta(old_code, new_code, "services/user_service.py")

    print(f"\nFile: {delta.file_path}")
    print(f"Compression: {delta.compression_ratio:.1%}")
    print(f"Risk Level: {delta.risk_level.value}")
    print(f"Changes: {len(delta.changes)}")

    print("\nChange Summary:")
    for change in delta.changes:
        print(f"  - [{change.change_type}] {change.name}: {change.description}")

    print("\nContext for LLM (compressed):")
    print("-" * 40)
    context = delta.to_context(max_chars=500)
    print(context)


async def demo_negative_space():
    """Demonstrate negative-space detection."""
    print("\n" + "="*60)
    print("Demo 4: Negative-Space Detection")
    print("="*60)

    from elgringo.autonomous import NegativeSpaceWatcher

    # Create watcher for a hypothetical project
    watcher = NegativeSpaceWatcher(project_root=".")

    # Add custom expectation for Firebase projects
    watcher.add_expectation(
        path_pattern="firestore.rules",
        related_to="*.ts",
        description="Firestore security rules",
        required=True,
    )

    print("Checking for expected files in a Firebase project...")
    print("Default expectations include:")
    for exp in watcher.expectations[:5]:
        print(f"  - {exp.path_pattern}: {exp.description}")

    # Check (will find missing files based on project state)
    print("\nChecking for stale/missing files...")
    alerts = watcher.check_negative_space()

    if alerts:
        print(f"\nFound {len(alerts)} alerts:")
        for alert in alerts[:5]:
            print(f"  - [{alert.alert_type}] {alert.expected_pattern}")
            print(f"    {alert.suggestion}")
    else:
        print("All expected files are present and up-to-date!")

    if watcher.should_trigger_review():
        print("\nWARNING: Critical files missing - peer review recommended!")


async def demo_coding_context():
    """Demonstrate integrated coding context generation."""
    print("\n" + "="*60)
    print("Demo 5: Integrated Coding Context")
    print("="*60)

    from elgringo.knowledge import get_coding_hub

    hub = get_coding_hub()

    # Simulate a coding task
    task = "Create a Firestore trigger that validates user data on write"

    print(f"Task: {task}")
    print("-" * 40)

    # Generate context
    context = hub.generate_coding_context(
        task_description=task,
        language="python",
        frameworks=["firebase", "cloud-functions"],
    )

    print("\nGenerated Context for AI:")
    print("=" * 40)
    # Show first 1500 chars
    if len(context) > 1500:
        print(context[:1500] + "\n...[truncated]...")
    else:
        print(context)


async def main():
    """Run all demos."""
    print("\n" + "#"*60)
    print("#  AITeamPlatform - Firebase Real-World Examples")
    print("#"*60)

    # Run demos in sequence
    try:
        await demo_firebase_rag()
    except Exception as e:
        print(f"Firebase RAG demo error: {e}")

    try:
        await demo_code_validation()
    except Exception as e:
        print(f"Validation demo error: {e}")

    try:
        await demo_semantic_delta()
    except Exception as e:
        print(f"Semantic delta demo error: {e}")

    try:
        await demo_negative_space()
    except Exception as e:
        print(f"Negative space demo error: {e}")

    try:
        await demo_coding_context()
    except Exception as e:
        print(f"Coding context demo error: {e}")

    print("\n" + "#"*60)
    print("#  Demos Complete")
    print("#"*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
