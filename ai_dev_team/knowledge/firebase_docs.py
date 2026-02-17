"""
Firebase Documentation RAG System
=================================

Retrieval-augmented generation for Firebase/Firestore documentation.
Provides context-aware documentation retrieval for AI code generation.

Usage:
    from ai_dev_team.knowledge.firebase_docs import FirebaseDocumentation, get_firebase_docs

    docs = get_firebase_docs()

    # Search for relevant documentation
    results = docs.search("firestore batch write")

    # Get context for a coding task
    context = docs.get_context_for_task("Write code to batch update users")
"""

import hashlib
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Storage directory
FIREBASE_DOCS_DIR = Path.home() / ".ai-dev-team" / "firebase_docs"
FIREBASE_DOCS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DocChunk:
    """A chunk of Firebase documentation."""
    id: str
    content: str
    title: str
    category: str  # firestore, auth, storage, functions, rules, etc.
    language: Optional[str] = None  # python, javascript, typescript
    tags: List[str] = field(default_factory=list)
    source: str = "embedded"
    relevance_score: float = 0.0


class TFIDFIndex:
    """Simple TF-IDF index for document retrieval."""

    def __init__(self):
        self.documents: Dict[str, str] = {}  # id -> content
        self.doc_tokens: Dict[str, Counter] = {}  # id -> token counts
        self.idf: Dict[str, float] = {}  # token -> idf score
        self.total_docs = 0

    def add_document(self, doc_id: str, content: str):
        """Add document to index."""
        tokens = self._tokenize(content)
        self.documents[doc_id] = content
        self.doc_tokens[doc_id] = Counter(tokens)
        self.total_docs = len(self.documents)
        self._update_idf()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for indexing."""
        text = text.lower()
        # Keep code-relevant punctuation
        text = re.sub(r'[^\w\s._-]', ' ', text)
        tokens = text.split()
        # Filter very short and very long tokens
        return [t for t in tokens if 2 <= len(t) <= 50]

    def _update_idf(self):
        """Update IDF scores."""
        doc_freq = Counter()
        for tokens in self.doc_tokens.values():
            doc_freq.update(tokens.keys())

        self.idf = {}
        for token, freq in doc_freq.items():
            self.idf[token] = math.log(self.total_docs / (1 + freq))

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for documents matching query."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = {}
        for doc_id, doc_tokens in self.doc_tokens.items():
            score = 0.0
            for token in query_tokens:
                if token in doc_tokens:
                    tf = doc_tokens[token] / sum(doc_tokens.values())
                    idf = self.idf.get(token, 0)
                    score += tf * idf

            if score > 0:
                scores[doc_id] = score

        # Sort by score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:top_k]


class FirebaseDocumentation:
    """
    Firebase documentation RAG system.

    Provides embedded Firebase documentation and search capabilities
    for enhancing AI code generation with relevant context.
    """

    def __init__(self):
        self.chunks: Dict[str, DocChunk] = {}
        self.index = TFIDFIndex()
        self._load_embedded_docs()
        self._load_cached_docs()
        self._build_index()

    def _load_embedded_docs(self):
        """Load embedded Firebase documentation."""
        # Embedded documentation covering key Firebase concepts
        embedded_docs = [
            # Firestore CRUD
            {
                "title": "Firestore Document Creation",
                "category": "firestore",
                "language": "python",
                "tags": ["crud", "create", "add", "set"],
                "content": """
## Creating Documents in Firestore

### Using add() - Auto-generated ID
```python
from firebase_admin import firestore

db = firestore.client()

# Add document with auto-generated ID
doc_ref = db.collection('users').add({
    'name': 'John Doe',
    'email': 'john@example.com',
    'created_at': firestore.SERVER_TIMESTAMP
})
print(f"Document ID: {doc_ref[1].id}")
```

### Using set() - Specific ID
```python
# Set document with specific ID (creates or overwrites)
db.collection('users').document('user_123').set({
    'name': 'Jane Doe',
    'email': 'jane@example.com'
})

# Set with merge (partial update)
db.collection('users').document('user_123').set({
    'phone': '555-1234'
}, merge=True)
```

### Best Practices
- Use `add()` when you don't need a specific ID
- Use `set()` when you need a deterministic ID
- Use `set(data, merge=True)` to update only specific fields
- Always include timestamps for tracking
"""
            },
            {
                "title": "Firestore Document Reading",
                "category": "firestore",
                "language": "python",
                "tags": ["crud", "read", "get", "query"],
                "content": """
## Reading Documents from Firestore

### Get Single Document
```python
from firebase_admin import firestore

db = firestore.client()

# Get document by ID
doc_ref = db.collection('users').document('user_123')
doc = doc_ref.get()

if doc.exists:
    data = doc.to_dict()
    print(f"Name: {data['name']}")
else:
    print("Document not found")
```

### Get All Documents
```python
# Stream all documents in collection
docs = db.collection('users').stream()

for doc in docs:
    print(f"{doc.id} => {doc.to_dict()}")
```

### Error Handling
- Always check `doc.exists` before accessing data
- Use `doc.to_dict()` to convert to Python dictionary
- Handle `google.cloud.exceptions.NotFound` for missing docs
"""
            },
            {
                "title": "Firestore Queries",
                "category": "firestore",
                "language": "python",
                "tags": ["query", "where", "filter", "orderby"],
                "content": """
## Querying Firestore

### Basic Where Queries
```python
from firebase_admin import firestore

db = firestore.client()

# Equality query
users = db.collection('users').where('status', '==', 'active')

# Comparison operators: ==, !=, <, <=, >, >=
adults = db.collection('users').where('age', '>=', 18)

# Array contains
tagged = db.collection('posts').where('tags', 'array_contains', 'python')

# In query (up to 10 values)
admins = db.collection('users').where('role', 'in', ['admin', 'superadmin'])
```

### Compound Queries
```python
# Multiple conditions (AND)
query = (db.collection('users')
         .where('status', '==', 'active')
         .where('age', '>=', 18)
         .order_by('created_at', direction=firestore.Query.DESCENDING))

# Requires composite index for range queries on different fields
```

### Ordering and Limiting
```python
# Order by field
users = db.collection('users').order_by('name').limit(10)

# Descending order
posts = db.collection('posts').order_by('created_at', direction=firestore.Query.DESCENDING)

# Pagination with start_after
first_page = db.collection('users').order_by('name').limit(20).get()
last_doc = first_page[-1]
second_page = db.collection('users').order_by('name').start_after(last_doc).limit(20)
```

### Index Requirements
- Single-field queries: Automatic indexes
- Range queries on same field: Automatic
- Compound queries: Require composite index
- Create indexes in Firebase Console or via CLI
"""
            },
            {
                "title": "Firestore Update and Delete",
                "category": "firestore",
                "language": "python",
                "tags": ["crud", "update", "delete"],
                "content": """
## Updating and Deleting Documents

### Update Specific Fields
```python
from firebase_admin import firestore

db = firestore.client()

# Update only specified fields
doc_ref = db.collection('users').document('user_123')
doc_ref.update({
    'email': 'newemail@example.com',
    'updated_at': firestore.SERVER_TIMESTAMP
})
```

### Special Update Operations
```python
# Increment a number
doc_ref.update({
    'login_count': firestore.Increment(1),
    'score': firestore.Increment(-5)  # Decrement
})

# Array operations
doc_ref.update({
    'tags': firestore.ArrayUnion(['new_tag']),  # Add unique
    'old_tags': firestore.ArrayRemove(['deprecated'])  # Remove
})

# Delete a field
doc_ref.update({
    'deprecated_field': firestore.DELETE_FIELD
})
```

### Delete Document
```python
# Delete a single document
db.collection('users').document('user_123').delete()

# Delete document and subcollections
def delete_collection(coll_ref, batch_size=500):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)
```
"""
            },
            {
                "title": "Firestore Batch Operations",
                "category": "firestore",
                "language": "python",
                "tags": ["batch", "transaction", "atomic"],
                "content": """
## Batch Operations in Firestore

### Batch Writes
```python
from firebase_admin import firestore

db = firestore.client()

# Create a batch
batch = db.batch()

# Add operations (max 500 per batch)
batch.set(db.collection('users').document('user_1'), {'name': 'User 1'})
batch.update(db.collection('users').document('user_2'), {'status': 'active'})
batch.delete(db.collection('users').document('user_3'))

# Commit atomically
batch.commit()
```

### Large Batch Writes
```python
def batch_write_large(collection, documents):
    \"\"\"Write large number of documents in multiple batches.\"\"\"
    batch_size = 500
    total = len(documents)

    for i in range(0, total, batch_size):
        batch = db.batch()
        chunk = documents[i:i + batch_size]

        for doc_data in chunk:
            ref = db.collection(collection).document()
            batch.set(ref, doc_data)

        batch.commit()
        print(f"Committed batch {i // batch_size + 1}")
```

### Transactions
```python
@firestore.transactional
def transfer_funds(transaction, from_ref, to_ref, amount):
    from_doc = from_ref.get(transaction=transaction)
    to_doc = to_ref.get(transaction=transaction)

    from_balance = from_doc.get('balance')
    if from_balance < amount:
        raise ValueError("Insufficient funds")

    transaction.update(from_ref, {'balance': from_balance - amount})
    transaction.update(to_ref, {'balance': to_doc.get('balance') + amount})

# Execute transaction
transaction = db.transaction()
transfer_funds(transaction, from_account_ref, to_account_ref, 100)
```

### Best Practices
- Batch limit: 500 operations
- Use batches for multiple independent writes
- Use transactions for reads + writes that must be consistent
- Transactions may retry on conflicts
"""
            },
            {
                "title": "Firebase Authentication - Python Admin SDK",
                "category": "auth",
                "language": "python",
                "tags": ["auth", "users", "admin", "verification"],
                "content": """
## Firebase Authentication with Python Admin SDK

### Create User
```python
from firebase_admin import auth

# Create user with email/password
user = auth.create_user(
    email='user@example.com',
    password='secretPassword',
    display_name='John Doe',
    email_verified=False
)
print(f"Created user: {user.uid}")
```

### Verify ID Token
```python
def verify_token(id_token):
    \"\"\"Verify Firebase ID token from client.\"\"\"
    try:
        decoded = auth.verify_id_token(id_token)
        return {
            'uid': decoded['uid'],
            'email': decoded.get('email'),
            'valid': True
        }
    except auth.InvalidIdTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except auth.ExpiredIdTokenError:
        return {'valid': False, 'error': 'Token expired'}
```

### Custom Claims for RBAC
```python
# Set custom claims
auth.set_custom_user_claims(uid, {
    'role': 'admin',
    'permissions': ['read', 'write', 'delete']
})

# Claims are included in ID tokens
# Access in security rules: request.auth.token.role == 'admin'
```

### Get User Information
```python
# Get by UID
user = auth.get_user(uid)

# Get by email
user = auth.get_user_by_email('user@example.com')

# List all users
for user in auth.list_users().iterate_all():
    print(f"{user.uid}: {user.email}")
```
"""
            },
            {
                "title": "Firestore Security Rules",
                "category": "rules",
                "language": "firestore",
                "tags": ["security", "rules", "permissions"],
                "content": """
## Firestore Security Rules

### Basic Structure
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Rules go here
  }
}
```

### Common Patterns
```javascript
// Allow authenticated users only
match /users/{userId} {
  allow read, write: if request.auth != null;
}

// Allow users to access only their own data
match /users/{userId} {
  allow read, write: if request.auth.uid == userId;
}

// Role-based access
match /admin/{document} {
  allow read, write: if request.auth.token.role == 'admin';
}

// Validate data
match /posts/{postId} {
  allow create: if request.resource.data.title is string
    && request.resource.data.title.size() <= 200;
}
```

### Helper Functions
```javascript
function isSignedIn() {
  return request.auth != null;
}

function isOwner(userId) {
  return request.auth.uid == userId;
}

function hasRole(role) {
  return request.auth.token[role] == true;
}
```

### Best Practices
- Start with deny-all, then whitelist
- Never allow write:true without conditions
- Validate all incoming data
- Use functions for reusable logic
- Test with Firebase Emulator
"""
            },
            {
                "title": "Firebase Cloud Storage - Python",
                "category": "storage",
                "language": "python",
                "tags": ["storage", "files", "upload", "download"],
                "content": """
## Firebase Cloud Storage with Python

### Upload Files
```python
from firebase_admin import storage

bucket = storage.bucket()

# Upload from file
blob = bucket.blob('uploads/image.jpg')
blob.upload_from_filename('/local/path/image.jpg')

# Upload from string/bytes
blob = bucket.blob('data/config.json')
blob.upload_from_string(json.dumps(config), content_type='application/json')

# Make public
blob.make_public()
print(f"Public URL: {blob.public_url}")
```

### Download Files
```python
# Download to file
blob = bucket.blob('uploads/image.jpg')
blob.download_to_filename('/local/download.jpg')

# Download as bytes
content = blob.download_as_bytes()
```

### Generate Signed URLs
```python
from datetime import timedelta

# Signed URL for temporary access
url = blob.generate_signed_url(
    version='v4',
    expiration=timedelta(hours=1),
    method='GET'
)
```

### List and Delete
```python
# List files in folder
blobs = bucket.list_blobs(prefix='uploads/')
for blob in blobs:
    print(blob.name)

# Delete file
blob.delete()
```
"""
            },
            {
                "title": "Cloud Functions with Python (2nd Gen)",
                "category": "functions",
                "language": "python",
                "tags": ["functions", "serverless", "triggers"],
                "content": """
## Firebase Cloud Functions (Python - 2nd Gen)

### HTTP Function
```python
from firebase_functions import https_fn
from firebase_admin import initialize_app

initialize_app()

@https_fn.on_request()
def hello_world(req: https_fn.Request) -> https_fn.Response:
    return https_fn.Response("Hello from Firebase!")
```

### Firestore Trigger
```python
from firebase_functions import firestore_fn
from firebase_admin import firestore

@firestore_fn.on_document_created(document="users/{userId}")
def on_user_created(event: firestore_fn.Event) -> None:
    user_id = event.params["userId"]
    user_data = event.data.to_dict()

    # Create profile, send welcome email, etc.
    db = firestore.client()
    db.collection("profiles").document(user_id).set({
        "displayName": user_data.get("name"),
        "createdAt": firestore.SERVER_TIMESTAMP
    })
```

### Scheduled Function
```python
from firebase_functions import scheduler_fn

@scheduler_fn.on_schedule(schedule="0 0 * * *")  # Daily at midnight
def daily_cleanup(event: scheduler_fn.ScheduledEvent) -> None:
    # Cleanup logic
    pass
```

### Best Practices
- Keep functions small and focused
- Use environment variables for config
- Handle errors gracefully
- Set appropriate timeout and memory
"""
            },
            # JavaScript/TypeScript examples
            {
                "title": "Firestore with JavaScript/TypeScript",
                "category": "firestore",
                "language": "typescript",
                "tags": ["javascript", "typescript", "web", "client"],
                "content": """
## Firestore with JavaScript/TypeScript (Web SDK v9)

### Initialize
```typescript
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, doc, setDoc, getDoc } from 'firebase/firestore';

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
```

### Add/Set Document
```typescript
// Add with auto-ID
import { addDoc } from 'firebase/firestore';

const docRef = await addDoc(collection(db, 'users'), {
  name: 'John',
  email: 'john@example.com'
});

// Set with specific ID
await setDoc(doc(db, 'users', 'user123'), {
  name: 'Jane',
  email: 'jane@example.com'
});
```

### Read Document
```typescript
import { getDoc } from 'firebase/firestore';

const docSnap = await getDoc(doc(db, 'users', 'user123'));

if (docSnap.exists()) {
  console.log(docSnap.data());
} else {
  console.log('No such document');
}
```

### Query
```typescript
import { query, where, orderBy, limit, getDocs } from 'firebase/firestore';

const q = query(
  collection(db, 'users'),
  where('status', '==', 'active'),
  orderBy('createdAt', 'desc'),
  limit(10)
);

const snapshot = await getDocs(q);
snapshot.forEach(doc => console.log(doc.data()));
```

### Real-time Listener
```typescript
import { onSnapshot } from 'firebase/firestore';

const unsubscribe = onSnapshot(doc(db, 'users', 'user123'), (doc) => {
  console.log('Current data:', doc.data());
});

// Stop listening
unsubscribe();
```
"""
            },
            {
                "title": "Error Handling Best Practices",
                "category": "general",
                "language": "python",
                "tags": ["errors", "exceptions", "retry", "resilience"],
                "content": """
## Firebase Error Handling Best Practices

### Common Firestore Errors
```python
from google.cloud.exceptions import NotFound, PermissionDenied
from firebase_admin.exceptions import FirebaseError

try:
    doc = db.collection('users').document('user_123').get()
except NotFound:
    print("Document not found")
except PermissionDenied:
    print("Access denied - check security rules")
except FirebaseError as e:
    print(f"Firebase error: {e}")
```

### Retry Logic
```python
import time
from functools import wraps

def with_retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@with_retry(max_retries=3)
def get_user(user_id):
    return db.collection('users').document(user_id).get()
```

### Transaction Retry
- Firestore transactions automatically retry on conflicts
- Set appropriate timeout for long operations
- Avoid too many reads in single transaction
"""
            },
        ]

        # Convert to DocChunks
        for i, doc in enumerate(embedded_docs):
            chunk_id = hashlib.md5(doc["title"].encode()).hexdigest()[:12]
            self.chunks[chunk_id] = DocChunk(
                id=chunk_id,
                content=doc["content"],
                title=doc["title"],
                category=doc["category"],
                language=doc.get("language"),
                tags=doc.get("tags", []),
                source="embedded"
            )

    def _load_cached_docs(self):
        """Load cached documentation from disk."""
        cache_file = FIREBASE_DOCS_DIR / "cached_docs.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cached = json.load(f)
                for doc_data in cached:
                    chunk = DocChunk(**doc_data)
                    self.chunks[chunk.id] = chunk
                logger.info(f"Loaded {len(cached)} cached docs")
            except Exception as e:
                logger.warning(f"Failed to load cached docs: {e}")

    def _build_index(self):
        """Build TF-IDF index for all chunks."""
        for chunk_id, chunk in self.chunks.items():
            searchable = f"{chunk.title} {chunk.content} {' '.join(chunk.tags)}"
            self.index.add_document(chunk_id, searchable)
        logger.info(f"Built index with {len(self.chunks)} documents")

    def search(self, query: str, top_k: int = 5, category: str = None) -> List[DocChunk]:
        """
        Search for relevant documentation.

        Args:
            query: Search query
            top_k: Number of results to return
            category: Optional category filter (firestore, auth, storage, etc.)

        Returns:
            List of relevant DocChunks
        """
        results = self.index.search(query, top_k=top_k * 2)

        chunks = []
        for chunk_id, score in results:
            chunk = self.chunks.get(chunk_id)
            if chunk:
                if category and chunk.category != category:
                    continue
                chunk.relevance_score = score
                chunks.append(chunk)

        return chunks[:top_k]

    def get_context_for_task(
        self,
        task_description: str,
        max_context_length: int = 3000
    ) -> str:
        """
        Generate documentation context for a coding task.

        Args:
            task_description: Description of the coding task
            max_context_length: Maximum characters of context to return

        Returns:
            Formatted context string for LLM prompt
        """
        # Detect relevant categories
        categories = self._detect_categories(task_description)

        # Search for relevant docs
        results = self.search(task_description, top_k=5)

        # Filter by detected categories if any
        if categories:
            results = [r for r in results if r.category in categories] or results[:3]

        # Build context
        context_parts = ["## Firebase Documentation Context\n"]

        total_length = 0
        for chunk in results:
            chunk_text = f"\n### {chunk.title}\n{chunk.content}\n"
            if total_length + len(chunk_text) > max_context_length:
                break
            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        return "".join(context_parts)

    def _detect_categories(self, text: str) -> List[str]:
        """Detect Firebase categories mentioned in text."""
        categories = []
        text_lower = text.lower()

        category_keywords = {
            "firestore": ["firestore", "document", "collection", "query", "batch"],
            "auth": ["auth", "authentication", "user", "login", "token", "claims"],
            "storage": ["storage", "file", "upload", "download", "bucket", "blob"],
            "functions": ["function", "cloud function", "trigger", "scheduled", "http"],
            "rules": ["rule", "security", "permission", "allow", "deny"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                categories.append(category)

        return categories

    def add_documentation(
        self,
        title: str,
        content: str,
        category: str,
        language: str = None,
        tags: List[str] = None
    ) -> str:
        """
        Add custom documentation to the system.

        Args:
            title: Document title
            content: Documentation content
            category: Category (firestore, auth, storage, etc.)
            language: Programming language
            tags: Search tags

        Returns:
            Chunk ID
        """
        chunk_id = hashlib.md5(f"{title}{content[:100]}".encode()).hexdigest()[:12]

        chunk = DocChunk(
            id=chunk_id,
            content=content,
            title=title,
            category=category,
            language=language,
            tags=tags or [],
            source="custom"
        )

        self.chunks[chunk_id] = chunk

        # Update index
        searchable = f"{title} {content} {' '.join(tags or [])}"
        self.index.add_document(chunk_id, searchable)

        return chunk_id

    def save_cache(self):
        """Save cached documentation to disk."""
        cache_file = FIREBASE_DOCS_DIR / "cached_docs.json"
        custom_docs = [
            {
                "id": c.id,
                "content": c.content,
                "title": c.title,
                "category": c.category,
                "language": c.language,
                "tags": c.tags,
                "source": c.source
            }
            for c in self.chunks.values()
            if c.source == "custom"
        ]

        with open(cache_file, "w") as f:
            json.dump(custom_docs, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the documentation."""
        categories = Counter(c.category for c in self.chunks.values())
        languages = Counter(c.language for c in self.chunks.values() if c.language)

        return {
            "total_chunks": len(self.chunks),
            "categories": dict(categories),
            "languages": dict(languages),
            "indexed_tokens": len(self.index.idf)
        }


# Global instance
_firebase_docs: Optional[FirebaseDocumentation] = None


def get_firebase_docs() -> FirebaseDocumentation:
    """Get global Firebase documentation instance."""
    global _firebase_docs
    if _firebase_docs is None:
        _firebase_docs = FirebaseDocumentation()
    return _firebase_docs


if __name__ == "__main__":
    # Test the documentation system
    docs = get_firebase_docs()

    print("=== Firebase Documentation Stats ===")
    stats = docs.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== Search Test: 'batch write firestore' ===")
    results = docs.search("batch write firestore", top_k=3)
    for r in results:
        print(f"  [{r.category}] {r.title} (score: {r.relevance_score:.3f})")

    print("\n=== Context Generation Test ===")
    context = docs.get_context_for_task(
        "Write Python code to batch update multiple users in Firestore"
    )
    print(context[:500] + "...")
