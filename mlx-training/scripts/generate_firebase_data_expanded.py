#!/usr/bin/env python3
"""
Expanded Firebase/Firestore synthetic training data generator.
Creates 500+ diverse examples for LLM fine-tuning.
"""

import json
import random
from pathlib import Path

# Additional examples to supplement the base set
ADDITIONAL_EXAMPLES = []

# =============================================================================
# MORE PYTHON FIRESTORE PATTERNS
# =============================================================================

PYTHON_ADVANCED = [
    {
        "instruction": "Write Python code to implement a Firestore repository pattern for a User model",
        "output": '''from firebase_admin import firestore
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

@dataclass
class User:
    id: Optional[str] = None
    email: str = ""
    name: str = ""
    role: str = "user"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserRepository:
    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection('users')

    def create(self, user: User) -> User:
        """Create a new user."""
        data = asdict(user)
        data.pop('id')
        data['created_at'] = firestore.SERVER_TIMESTAMP
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        doc_ref = self.collection.add(data)
        user.id = doc_ref[1].id
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        doc = self.collection.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return User(**data)
        return None

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        docs = self.collection.where('email', '==', email).limit(1).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return User(**data)
        return None

    def update(self, user: User) -> User:
        """Update an existing user."""
        data = asdict(user)
        data.pop('id')
        data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(user.id).update(data)
        return user

    def delete(self, user_id: str) -> bool:
        """Delete a user."""
        self.collection.document(user_id).delete()
        return True

    def list_all(self, limit: int = 100) -> List[User]:
        """List all users."""
        docs = self.collection.limit(limit).stream()
        return [User(id=doc.id, **doc.to_dict()) for doc in docs]

    def find_by_role(self, role: str) -> List[User]:
        """Find users by role."""
        docs = self.collection.where('role', '==', role).stream()
        return [User(id=doc.id, **doc.to_dict()) for doc in docs]'''
    },
    {
        "instruction": "Write Python code to implement caching with Firestore for frequently accessed data",
        "output": '''from firebase_admin import firestore
from functools import lru_cache
from datetime import datetime, timedelta
import threading

class FirestoreCache:
    """Simple in-memory cache for Firestore documents."""

    def __init__(self, ttl_seconds: int = 300):
        self.db = firestore.client()
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = threading.Lock()

    def _is_expired(self, key: str) -> bool:
        if key not in self.cache:
            return True
        cached_at = self.cache[key]['cached_at']
        return datetime.now() - cached_at > self.ttl

    def get(self, collection: str, doc_id: str) -> dict:
        """Get document with caching."""
        cache_key = f"{collection}/{doc_id}"

        with self.lock:
            if not self._is_expired(cache_key):
                return self.cache[cache_key]['data']

        # Fetch from Firestore
        doc = self.db.collection(collection).document(doc_id).get()
        if doc.exists:
            data = {'id': doc.id, **doc.to_dict()}
            with self.lock:
                self.cache[cache_key] = {
                    'data': data,
                    'cached_at': datetime.now()
                }
            return data
        return None

    def invalidate(self, collection: str, doc_id: str):
        """Invalidate cache for a document."""
        cache_key = f"{collection}/{doc_id}"
        with self.lock:
            self.cache.pop(cache_key, None)

    def invalidate_collection(self, collection: str):
        """Invalidate all cached documents in a collection."""
        with self.lock:
            keys_to_remove = [k for k in self.cache if k.startswith(f"{collection}/")]
            for key in keys_to_remove:
                del self.cache[key]

    def set(self, collection: str, doc_id: str, data: dict):
        """Set document and update cache."""
        self.db.collection(collection).document(doc_id).set(data)
        cache_key = f"{collection}/{doc_id}"
        with self.lock:
            self.cache[cache_key] = {
                'data': {'id': doc_id, **data},
                'cached_at': datetime.now()
            }

# Usage
cache = FirestoreCache(ttl_seconds=300)
user = cache.get('users', 'user_123')  # First call hits Firestore
user = cache.get('users', 'user_123')  # Second call uses cache'''
    },
    {
        "instruction": "Write Python code to export Firestore collection to JSON backup",
        "output": '''from firebase_admin import firestore
import json
from datetime import datetime
from pathlib import Path

def export_collection_to_json(collection_name: str, output_path: str = None) -> str:
    """Export a Firestore collection to JSON file."""
    db = firestore.client()

    # Get all documents
    docs = db.collection(collection_name).stream()

    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        doc_data['_id'] = doc.id

        # Convert Firestore types to JSON-serializable
        for key, value in doc_data.items():
            if hasattr(value, 'isoformat'):  # datetime
                doc_data[key] = value.isoformat()
            elif hasattr(value, 'path'):  # DocumentReference
                doc_data[key] = value.path

        data.append(doc_data)

    # Generate output path
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"backup_{collection_name}_{timestamp}.json"

    # Write to file
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Exported {len(data)} documents to {output_path}")
    return output_path


def import_collection_from_json(collection_name: str, json_path: str):
    """Import a JSON file to Firestore collection."""
    db = firestore.client()

    with open(json_path, 'r') as f:
        data = json.load(f)

    batch = db.batch()
    count = 0

    for doc_data in data:
        doc_id = doc_data.pop('_id', None)
        if doc_id:
            ref = db.collection(collection_name).document(doc_id)
        else:
            ref = db.collection(collection_name).document()

        batch.set(ref, doc_data)
        count += 1

        # Commit every 500 docs
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()

    # Commit remaining
    if count % 500 != 0:
        batch.commit()

    print(f"Imported {count} documents to {collection_name}")


# Usage
export_collection_to_json('users')
import_collection_from_json('users_restored', 'backup_users_20240115.json')'''
    },
    {
        "instruction": "Write Python code to implement soft delete with Firestore",
        "output": '''from firebase_admin import firestore
from datetime import datetime
from typing import Optional, List

db = firestore.client()

class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    collection_name: str = None

    @classmethod
    def _get_collection(cls):
        return db.collection(cls.collection_name)

    @classmethod
    def delete(cls, doc_id: str, deleted_by: str = None):
        """Soft delete a document."""
        cls._get_collection().document(doc_id).update({
            'deleted': True,
            'deleted_at': firestore.SERVER_TIMESTAMP,
            'deleted_by': deleted_by
        })

    @classmethod
    def restore(cls, doc_id: str):
        """Restore a soft-deleted document."""
        cls._get_collection().document(doc_id).update({
            'deleted': firestore.DELETE_FIELD,
            'deleted_at': firestore.DELETE_FIELD,
            'deleted_by': firestore.DELETE_FIELD,
            'restored_at': firestore.SERVER_TIMESTAMP
        })

    @classmethod
    def hard_delete(cls, doc_id: str):
        """Permanently delete a document."""
        cls._get_collection().document(doc_id).delete()

    @classmethod
    def get_active(cls, limit: int = 100) -> List[dict]:
        """Get non-deleted documents."""
        docs = cls._get_collection() \\
            .where('deleted', '==', False) \\
            .limit(limit) \\
            .stream()
        return [{'id': d.id, **d.to_dict()} for d in docs]

    @classmethod
    def get_deleted(cls, limit: int = 100) -> List[dict]:
        """Get soft-deleted documents."""
        docs = cls._get_collection() \\
            .where('deleted', '==', True) \\
            .order_by('deleted_at', direction=firestore.Query.DESCENDING) \\
            .limit(limit) \\
            .stream()
        return [{'id': d.id, **d.to_dict()} for d in docs]

    @classmethod
    def purge_old_deleted(cls, days: int = 30):
        """Permanently delete documents deleted more than X days ago."""
        cutoff = datetime.now() - timedelta(days=days)
        docs = cls._get_collection() \\
            .where('deleted', '==', True) \\
            .where('deleted_at', '<', cutoff) \\
            .stream()

        batch = db.batch()
        count = 0
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = db.batch()

        batch.commit()
        print(f"Purged {count} old deleted documents")


# Usage
class Post(SoftDeleteMixin):
    collection_name = 'posts'

Post.delete('post_123', deleted_by='user_456')
Post.restore('post_123')
active_posts = Post.get_active()'''
    },
    {
        "instruction": "Write Python code to handle Firestore connection errors with retry logic",
        "output": '''from firebase_admin import firestore
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded
from google.api_core import retry
import time
from functools import wraps

# Custom retry configuration
FIRESTORE_RETRY = retry.Retry(
    initial=0.1,  # Initial delay
    maximum=60.0,  # Maximum delay
    multiplier=2.0,  # Delay multiplier
    deadline=300.0,  # Total timeout
    predicate=retry.if_exception_type(
        ServiceUnavailable,
        DeadlineExceeded,
    )
)

def with_firestore_retry(max_attempts: int = 3, backoff_factor: float = 2.0):
    """Decorator for Firestore operations with custom retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = 1.0

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (ServiceUnavailable, DeadlineExceeded) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                except Exception as e:
                    # Don't retry other exceptions
                    raise

            raise last_exception

        return wrapper
    return decorator


class FirestoreClient:
    def __init__(self):
        self.db = firestore.client()

    @with_firestore_retry(max_attempts=3)
    def get_document(self, collection: str, doc_id: str) -> dict:
        """Get document with automatic retry."""
        doc = self.db.collection(collection).document(doc_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None

    @with_firestore_retry(max_attempts=3)
    def set_document(self, collection: str, doc_id: str, data: dict):
        """Set document with automatic retry."""
        self.db.collection(collection).document(doc_id).set(data)

    @with_firestore_retry(max_attempts=5)
    def run_transaction(self, update_func):
        """Run transaction with extended retry."""
        transaction = self.db.transaction()
        return update_func(transaction)


# Usage
client = FirestoreClient()
user = client.get_document('users', 'user_123')'''
    },
    {
        "instruction": "Write Python code to implement Firestore data migration between collections",
        "output": '''from firebase_admin import firestore
from typing import Callable, Dict, Any
from datetime import datetime

db = firestore.client()

def migrate_collection(
    source_collection: str,
    target_collection: str,
    transform_func: Callable[[Dict[str, Any]], Dict[str, Any]] = None,
    batch_size: int = 500,
    dry_run: bool = True
) -> dict:
    """
    Migrate documents from one collection to another with optional transformation.

    Args:
        source_collection: Source collection path
        target_collection: Target collection path
        transform_func: Optional function to transform each document
        batch_size: Number of documents per batch
        dry_run: If True, don't actually write documents

    Returns:
        Migration statistics
    """
    stats = {
        'total_read': 0,
        'total_written': 0,
        'errors': [],
        'started_at': datetime.now().isoformat()
    }

    source_ref = db.collection(source_collection)
    target_ref = db.collection(target_collection)

    docs = source_ref.stream()
    batch = db.batch()
    batch_count = 0

    for doc in docs:
        stats['total_read'] += 1

        try:
            data = doc.to_dict()
            doc_id = doc.id

            # Apply transformation if provided
            if transform_func:
                data = transform_func(data)
                if data is None:  # Skip if transform returns None
                    continue

            if not dry_run:
                target_doc_ref = target_ref.document(doc_id)
                batch.set(target_doc_ref, data)
                batch_count += 1

                if batch_count >= batch_size:
                    batch.commit()
                    stats['total_written'] += batch_count
                    print(f"Written {stats['total_written']} documents...")
                    batch = db.batch()
                    batch_count = 0
            else:
                stats['total_written'] += 1

        except Exception as e:
            stats['errors'].append({
                'doc_id': doc.id,
                'error': str(e)
            })

    # Commit remaining documents
    if batch_count > 0 and not dry_run:
        batch.commit()
        stats['total_written'] += batch_count

    stats['completed_at'] = datetime.now().isoformat()
    return stats


# Example: Migrate users with schema transformation
def transform_user_v1_to_v2(data: dict) -> dict:
    """Transform user document from v1 to v2 schema."""
    return {
        'email': data.get('email'),
        'profile': {
            'name': data.get('name', ''),
            'displayName': data.get('display_name', data.get('name', '')),
            'avatar': data.get('avatar_url', data.get('photo', ''))
        },
        'settings': {
            'notifications': data.get('notifications_enabled', True),
            'theme': data.get('theme', 'light')
        },
        'metadata': {
            'createdAt': data.get('created_at'),
            'migratedAt': firestore.SERVER_TIMESTAMP,
            'schemaVersion': 2
        }
    }

# Dry run first
stats = migrate_collection('users', 'users_v2', transform_user_v1_to_v2, dry_run=True)
print(f"Dry run: {stats['total_read']} docs would be migrated")

# Actual migration
stats = migrate_collection('users', 'users_v2', transform_user_v1_to_v2, dry_run=False)
print(f"Migration complete: {stats['total_written']} docs migrated")'''
    },
    {
        "instruction": "Write Python code for Firestore full-text search using a search index",
        "output": '''from firebase_admin import firestore
from typing import List, Set
import re

db = firestore.client()

def tokenize(text: str) -> Set[str]:
    """Tokenize text for search indexing."""
    # Lowercase and split by non-alphanumeric
    words = re.findall(r'\\w+', text.lower())

    tokens = set()
    for word in words:
        tokens.add(word)
        # Add prefixes for prefix search
        for i in range(1, len(word) + 1):
            tokens.add(word[:i])

    return tokens


def create_search_index(doc_data: dict, searchable_fields: List[str]) -> List[str]:
    """Create search tokens from document fields."""
    tokens = set()

    for field in searchable_fields:
        value = doc_data.get(field, '')
        if isinstance(value, str):
            tokens.update(tokenize(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    tokens.update(tokenize(item))

    return list(tokens)


def add_searchable_document(collection: str, doc_id: str, data: dict,
                           searchable_fields: List[str]):
    """Add document with search index."""
    data['_search_tokens'] = create_search_index(data, searchable_fields)
    db.collection(collection).document(doc_id).set(data)


def search_documents(collection: str, query: str, limit: int = 20) -> List[dict]:
    """Search documents using tokens."""
    query_tokens = list(tokenize(query))

    if not query_tokens:
        return []

    # Firestore array-contains can only check one token
    # Use the longest token for most specific search
    search_token = max(query_tokens, key=len)

    docs = db.collection(collection) \\
        .where('_search_tokens', 'array_contains', search_token) \\
        .limit(limit) \\
        .stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        # Remove internal search field from results
        data.pop('_search_tokens', None)
        results.append(data)

    return results


# Usage: Index a product
add_searchable_document('products', 'prod_123', {
    'name': 'Apple MacBook Pro',
    'description': 'Powerful laptop for professionals',
    'tags': ['laptop', 'apple', 'computer']
}, searchable_fields=['name', 'description', 'tags'])

# Search products
results = search_documents('products', 'macbook')
print(f"Found {len(results)} products")'''
    },
    {
        "instruction": "Write Python code to implement Firestore composite index creation helper",
        "output": '''from firebase_admin import firestore
import json
from pathlib import Path

def generate_firestore_indexes(indexes: list) -> dict:
    """
    Generate Firestore indexes configuration.

    Args:
        indexes: List of index definitions

    Returns:
        Firestore indexes configuration dict
    """
    config = {
        "indexes": [],
        "fieldOverrides": []
    }

    for idx in indexes:
        index_config = {
            "collectionGroup": idx["collection"],
            "queryScope": idx.get("scope", "COLLECTION"),
            "fields": []
        }

        for field in idx["fields"]:
            if isinstance(field, str):
                # Simple ascending field
                index_config["fields"].append({
                    "fieldPath": field,
                    "order": "ASCENDING"
                })
            else:
                # Custom field config
                field_config = {"fieldPath": field["path"]}
                if "order" in field:
                    field_config["order"] = field["order"]
                if "arrayConfig" in field:
                    field_config["arrayConfig"] = field["arrayConfig"]
                index_config["fields"].append(field_config)

        config["indexes"].append(index_config)

    return config


def save_firestore_indexes(indexes: list, output_path: str = "firestore.indexes.json"):
    """Save indexes to JSON file for deployment."""
    config = generate_firestore_indexes(indexes)

    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Saved {len(indexes)} index definitions to {output_path}")


# Define indexes for your application
INDEXES = [
    # Posts ordered by date, filtered by author
    {
        "collection": "posts",
        "fields": [
            "authorId",
            {"path": "createdAt", "order": "DESCENDING"}
        ]
    },
    # Posts with tag search
    {
        "collection": "posts",
        "fields": [
            {"path": "tags", "arrayConfig": "CONTAINS"},
            {"path": "createdAt", "order": "DESCENDING"}
        ]
    },
    # Users by role and status
    {
        "collection": "users",
        "fields": [
            "role",
            "status",
            {"path": "createdAt", "order": "DESCENDING"}
        ]
    },
    # Orders for a user by date
    {
        "collection": "orders",
        "fields": [
            "userId",
            "status",
            {"path": "orderDate", "order": "DESCENDING"}
        ]
    },
    # Collection group query for comments
    {
        "collection": "comments",
        "scope": "COLLECTION_GROUP",
        "fields": [
            "authorId",
            {"path": "createdAt", "order": "DESCENDING"}
        ]
    }
]

# Generate and save indexes
save_firestore_indexes(INDEXES)'''
    },
    {
        "instruction": "Write Python code for async Firestore operations using asyncio",
        "output": '''import asyncio
from firebase_admin import firestore
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from functools import partial

db = firestore.client()
executor = ThreadPoolExecutor(max_workers=10)

async def async_get_document(collection: str, doc_id: str) -> Dict[str, Any]:
    """Async wrapper for getting a document."""
    loop = asyncio.get_event_loop()
    doc = await loop.run_in_executor(
        executor,
        lambda: db.collection(collection).document(doc_id).get()
    )
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None


async def async_set_document(collection: str, doc_id: str, data: dict):
    """Async wrapper for setting a document."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        executor,
        lambda: db.collection(collection).document(doc_id).set(data)
    )


async def async_query(collection: str, field: str, op: str, value: Any) -> List[dict]:
    """Async wrapper for querying documents."""
    loop = asyncio.get_event_loop()

    def do_query():
        docs = db.collection(collection).where(field, op, value).stream()
        return [{'id': d.id, **d.to_dict()} for d in docs]

    return await loop.run_in_executor(executor, do_query)


async def async_batch_get(collection: str, doc_ids: List[str]) -> List[dict]:
    """Get multiple documents concurrently."""
    tasks = [async_get_document(collection, doc_id) for doc_id in doc_ids]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


async def async_batch_write(collection: str, documents: List[dict]):
    """Write multiple documents concurrently."""
    tasks = []
    for doc in documents:
        doc_id = doc.pop('id', None) or db.collection(collection).document().id
        tasks.append(async_set_document(collection, doc_id, doc))
    await asyncio.gather(*tasks)


# Usage example
async def main():
    # Get multiple users concurrently
    user_ids = ['user_1', 'user_2', 'user_3']
    users = await async_batch_get('users', user_ids)
    print(f"Fetched {len(users)} users")

    # Query and get related data concurrently
    posts, comments = await asyncio.gather(
        async_query('posts', 'authorId', '==', 'user_1'),
        async_query('comments', 'authorId', '==', 'user_1')
    )
    print(f"User has {len(posts)} posts and {len(comments)} comments")


# Run async code
asyncio.run(main())'''
    },
    {
        "instruction": "Write Python code to implement rate limiting for Firestore operations",
        "output": '''from firebase_admin import firestore
import time
from threading import Lock
from collections import deque
from typing import Optional
from functools import wraps

class RateLimiter:
    """Token bucket rate limiter for Firestore operations."""

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Operations per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self.lock = Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire a token, blocking if necessary."""
        start = time.monotonic()

        while True:
            with self.lock:
                now = time.monotonic()
                # Add tokens based on elapsed time
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

            # Check timeout
            if timeout is not None and (time.monotonic() - start) >= timeout:
                return False

            # Wait before retry
            time.sleep(1 / self.rate)


class RateLimitedFirestore:
    """Firestore client with rate limiting."""

    def __init__(self, reads_per_second: float = 100, writes_per_second: float = 50):
        self.db = firestore.client()
        self.read_limiter = RateLimiter(reads_per_second, burst=10)
        self.write_limiter = RateLimiter(writes_per_second, burst=5)

    def get(self, collection: str, doc_id: str) -> dict:
        """Rate-limited document get."""
        self.read_limiter.acquire()
        doc = self.db.collection(collection).document(doc_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None

    def set(self, collection: str, doc_id: str, data: dict):
        """Rate-limited document set."""
        self.write_limiter.acquire()
        self.db.collection(collection).document(doc_id).set(data)

    def query(self, collection: str, *conditions):
        """Rate-limited query."""
        self.read_limiter.acquire()
        query = self.db.collection(collection)
        for field, op, value in conditions:
            query = query.where(field, op, value)
        docs = query.stream()
        return [{'id': d.id, **d.to_dict()} for d in docs]

    def batch_write(self, operations: list):
        """Rate-limited batch write."""
        batch = self.db.batch()
        for op in operations:
            self.write_limiter.acquire()
            ref = self.db.collection(op['collection']).document(op.get('id', ''))
            if op['type'] == 'set':
                batch.set(ref, op['data'])
            elif op['type'] == 'update':
                batch.update(ref, op['data'])
            elif op['type'] == 'delete':
                batch.delete(ref)
        batch.commit()


# Usage
fs = RateLimitedFirestore(reads_per_second=50, writes_per_second=20)
user = fs.get('users', 'user_123')'''
    },
]

# =============================================================================
# MORE JAVASCRIPT/TYPESCRIPT PATTERNS
# =============================================================================

JS_ADVANCED = [
    {
        "instruction": "Write TypeScript code to create a typed Firestore service with generics",
        "output": '''import {
  collection, doc, getDoc, setDoc, updateDoc, deleteDoc,
  query, where, orderBy, limit, getDocs,
  DocumentData, QueryConstraint, Timestamp
} from 'firebase/firestore';
import { db } from './firebase';

interface BaseDocument {
  id?: string;
  createdAt?: Timestamp;
  updatedAt?: Timestamp;
}

class FirestoreService<T extends BaseDocument> {
  constructor(private collectionName: string) {}

  private get collectionRef() {
    return collection(db, this.collectionName);
  }

  async create(data: Omit<T, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    const docRef = doc(this.collectionRef);
    await setDoc(docRef, {
      ...data,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now()
    });
    return docRef.id;
  }

  async getById(id: string): Promise<T | null> {
    const docRef = doc(db, this.collectionName, id);
    const snapshot = await getDoc(docRef);

    if (!snapshot.exists()) return null;

    return { id: snapshot.id, ...snapshot.data() } as T;
  }

  async update(id: string, data: Partial<T>): Promise<void> {
    const docRef = doc(db, this.collectionName, id);
    await updateDoc(docRef, {
      ...data,
      updatedAt: Timestamp.now()
    } as DocumentData);
  }

  async delete(id: string): Promise<void> {
    const docRef = doc(db, this.collectionName, id);
    await deleteDoc(docRef);
  }

  async find(constraints: QueryConstraint[]): Promise<T[]> {
    const q = query(this.collectionRef, ...constraints);
    const snapshot = await getDocs(q);

    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    } as T));
  }

  async findOne(constraints: QueryConstraint[]): Promise<T | null> {
    const results = await this.find([...constraints, limit(1)]);
    return results[0] || null;
  }
}

// Usage
interface User extends BaseDocument {
  email: string;
  name: string;
  role: 'admin' | 'user';
}

const userService = new FirestoreService<User>('users');

// Create user
const userId = await userService.create({
  email: 'john@example.com',
  name: 'John Doe',
  role: 'user'
});

// Get user
const user = await userService.getById(userId);

// Find users
const admins = await userService.find([
  where('role', '==', 'admin'),
  orderBy('createdAt', 'desc')
]);'''
    },
    {
        "instruction": "Write TypeScript code to implement optimistic updates with Firestore in React",
        "output": '''import { useState, useCallback } from 'react';
import { doc, updateDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';

interface OptimisticUpdateOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error, previousData: T) => void;
  onSettled?: () => void;
}

function useOptimisticUpdate<T extends { id: string }>(
  collectionName: string
) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const updateDocument = useCallback(
    async (
      currentData: T,
      updates: Partial<T>,
      options: OptimisticUpdateOptions<T> = {}
    ): Promise<T> => {
      const previousData = { ...currentData };
      const optimisticData = { ...currentData, ...updates };

      setIsUpdating(true);
      setError(null);

      try {
        // Return optimistic data immediately
        const docRef = doc(db, collectionName, currentData.id);

        // Perform actual update
        await updateDoc(docRef, {
          ...updates,
          updatedAt: serverTimestamp()
        });

        options.onSuccess?.(optimisticData);
        return optimisticData;
      } catch (err) {
        const error = err as Error;
        setError(error);
        options.onError?.(error, previousData);

        // Return previous data on failure
        return previousData;
      } finally {
        setIsUpdating(false);
        options.onSettled?.();
      }
    },
    [collectionName]
  );

  return { updateDocument, isUpdating, error };
}

// Usage in component
function TodoItem({ todo }: { todo: Todo }) {
  const [localTodo, setLocalTodo] = useState(todo);
  const { updateDocument, isUpdating } = useOptimisticUpdate<Todo>('todos');

  const toggleComplete = async () => {
    const newTodo = await updateDocument(
      localTodo,
      { completed: !localTodo.completed },
      {
        onSuccess: (data) => setLocalTodo(data),
        onError: (error, prevData) => {
          setLocalTodo(prevData);
          alert('Failed to update: ' + error.message);
        }
      }
    );

    // Optimistically update UI
    setLocalTodo(newTodo);
  };

  return (
    <div style={{ opacity: isUpdating ? 0.5 : 1 }}>
      <input
        type="checkbox"
        checked={localTodo.completed}
        onChange={toggleComplete}
        disabled={isUpdating}
      />
      <span>{localTodo.title}</span>
    </div>
  );
}'''
    },
    {
        "instruction": "Write TypeScript code to implement Firestore offline persistence with sync status",
        "output": '''import { useState, useEffect } from 'react';
import {
  enableIndexedDbPersistence,
  disableNetwork,
  enableNetwork,
  onSnapshotsInSync,
  collection,
  onSnapshot
} from 'firebase/firestore';
import { db } from './firebase';

// Enable offline persistence
async function initializeOfflineSupport() {
  try {
    await enableIndexedDbPersistence(db);
    console.log('Offline persistence enabled');
  } catch (err: any) {
    if (err.code === 'failed-precondition') {
      console.warn('Multiple tabs open, persistence enabled in another tab');
    } else if (err.code === 'unimplemented') {
      console.warn('Browser does not support offline persistence');
    }
  }
}

// Hook to track online/offline and sync status
function useFirestoreConnection() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isSynced, setIsSynced] = useState(true);
  const [pendingWrites, setPendingWrites] = useState(0);

  useEffect(() => {
    // Track browser online status
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Track Firestore sync status
    const unsubscribe = onSnapshotsInSync(db, () => {
      setIsSynced(true);
      setPendingWrites(0);
    });

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      unsubscribe();
    };
  }, []);

  const goOffline = async () => {
    await disableNetwork(db);
    setIsOnline(false);
  };

  const goOnline = async () => {
    await enableNetwork(db);
    setIsOnline(true);
  };

  return { isOnline, isSynced, pendingWrites, goOffline, goOnline };
}

// Hook for collection with offline support
function useOfflineCollection<T>(collectionName: string) {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [fromCache, setFromCache] = useState(false);

  useEffect(() => {
    const unsubscribe = onSnapshot(
      collection(db, collectionName),
      { includeMetadataChanges: true },
      (snapshot) => {
        const items = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        })) as T[];

        setData(items);
        setFromCache(snapshot.metadata.fromCache);
        setLoading(false);

        // Log pending writes
        const hasPendingWrites = snapshot.docs.some(
          doc => doc.metadata.hasPendingWrites
        );
        if (hasPendingWrites) {
          console.log('Some documents have pending writes');
        }
      }
    );

    return unsubscribe;
  }, [collectionName]);

  return { data, loading, fromCache };
}

// Usage
function App() {
  const { isOnline, isSynced } = useFirestoreConnection();
  const { data: todos, fromCache } = useOfflineCollection<Todo>('todos');

  return (
    <div>
      <div className="status-bar">
        {!isOnline && <span>📴 Offline</span>}
        {!isSynced && <span>🔄 Syncing...</span>}
        {fromCache && <span>📦 From cache</span>}
      </div>
      {todos.map(todo => <TodoItem key={todo.id} todo={todo} />)}
    </div>
  );
}'''
    },
    {
        "instruction": "Write TypeScript code to implement Firestore data validation with Zod",
        "output": '''import { z } from 'zod';
import { doc, setDoc, updateDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';

// Define schemas with Zod
const UserSchema = z.object({
  email: z.string().email('Invalid email address'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
  age: z.number().min(0).max(150).optional(),
  role: z.enum(['admin', 'user', 'guest']).default('user'),
  profile: z.object({
    bio: z.string().max(500).optional(),
    website: z.string().url().optional(),
    social: z.record(z.string()).optional()
  }).optional()
});

type User = z.infer<typeof UserSchema>;

const ProductSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().max(5000),
  price: z.number().positive('Price must be positive'),
  currency: z.enum(['USD', 'EUR', 'GBP']).default('USD'),
  inventory: z.number().int().min(0),
  tags: z.array(z.string()).max(10),
  active: z.boolean().default(true)
});

type Product = z.infer<typeof ProductSchema>;

// Validated Firestore operations
class ValidatedFirestore<T extends z.ZodType> {
  constructor(
    private collectionName: string,
    private schema: T
  ) {}

  async create(data: z.input<T>): Promise<string> {
    // Validate data
    const validatedData = this.schema.parse(data);

    const docRef = doc(collection(db, this.collectionName));
    await setDoc(docRef, {
      ...validatedData,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    });

    return docRef.id;
  }

  async update(id: string, data: Partial<z.input<T>>): Promise<void> {
    // Validate partial data
    const partialSchema = this.schema.partial();
    const validatedData = partialSchema.parse(data);

    const docRef = doc(db, this.collectionName, id);
    await updateDoc(docRef, {
      ...validatedData,
      updatedAt: serverTimestamp()
    });
  }

  validateOrThrow(data: unknown): z.output<T> {
    return this.schema.parse(data);
  }

  validateSafe(data: unknown): z.SafeParseReturnType<z.input<T>, z.output<T>> {
    return this.schema.safeParse(data);
  }
}

// Usage
const userService = new ValidatedFirestore('users', UserSchema);
const productService = new ValidatedFirestore('products', ProductSchema);

// Create with validation
try {
  const userId = await userService.create({
    email: 'john@example.com',
    name: 'John Doe',
    role: 'user'
  });
  console.log('Created user:', userId);
} catch (error) {
  if (error instanceof z.ZodError) {
    console.error('Validation errors:', error.errors);
  }
}

// Validate before form submission
function handleSubmit(formData: unknown) {
  const result = productService.validateSafe(formData);

  if (!result.success) {
    return { errors: result.error.flatten().fieldErrors };
  }

  return productService.create(result.data);
}'''
    },
    {
        "instruction": "Write JavaScript code to implement Firestore aggregation queries",
        "output": '''import {
  collection, query, where, getAggregateFromServer,
  count, sum, average
} from 'firebase/firestore';
import { db } from './firebase';

// Count documents matching a query
async function countActiveUsers() {
  const usersRef = collection(db, 'users');
  const activeQuery = query(usersRef, where('status', '==', 'active'));

  const snapshot = await getAggregateFromServer(activeQuery, {
    activeCount: count()
  });

  return snapshot.data().activeCount;
}

// Sum values across documents
async function getTotalRevenue(startDate, endDate) {
  const ordersRef = collection(db, 'orders');
  const revenueQuery = query(
    ordersRef,
    where('status', '==', 'completed'),
    where('createdAt', '>=', startDate),
    where('createdAt', '<=', endDate)
  );

  const snapshot = await getAggregateFromServer(revenueQuery, {
    totalRevenue: sum('amount'),
    orderCount: count()
  });

  const data = snapshot.data();
  return {
    total: data.totalRevenue,
    count: data.orderCount,
    average: data.orderCount > 0 ? data.totalRevenue / data.orderCount : 0
  };
}

// Get average rating
async function getProductAverageRating(productId) {
  const reviewsRef = collection(db, 'products', productId, 'reviews');

  const snapshot = await getAggregateFromServer(query(reviewsRef), {
    averageRating: average('rating'),
    reviewCount: count()
  });

  const data = snapshot.data();
  return {
    average: data.averageRating || 0,
    count: data.reviewCount
  };
}

// Dashboard statistics
async function getDashboardStats() {
  const [users, orders, products] = await Promise.all([
    getAggregateFromServer(
      query(collection(db, 'users'), where('status', '==', 'active')),
      { count: count() }
    ),
    getAggregateFromServer(
      query(collection(db, 'orders'), where('status', '==', 'pending')),
      { count: count(), total: sum('amount') }
    ),
    getAggregateFromServer(
      query(collection(db, 'products'), where('inventory', '>', 0)),
      { count: count() }
    )
  ]);

  return {
    activeUsers: users.data().count,
    pendingOrders: orders.data().count,
    pendingRevenue: orders.data().total,
    productsInStock: products.data().count
  };
}

// Usage
const stats = await getDashboardStats();
console.log('Dashboard:', stats);'''
    },
    {
        "instruction": "Write TypeScript code for a Firestore backup/restore system using Cloud Functions",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import { Storage } from '@google-cloud/storage';

admin.initializeApp();
const db = admin.firestore();
const storage = new Storage();
const bucketName = process.env.BACKUP_BUCKET || 'your-backup-bucket';

interface BackupMetadata {
  backupId: string;
  timestamp: Date;
  collections: string[];
  documentCount: number;
  sizeBytes: number;
}

// Scheduled backup function
export const scheduledBackup = functions.pubsub
  .schedule('0 2 * * *') // Daily at 2 AM
  .timeZone('UTC')
  .onRun(async (context) => {
    const backupId = `backup_${Date.now()}`;
    const collections = ['users', 'orders', 'products', 'posts'];

    const metadata: BackupMetadata = {
      backupId,
      timestamp: new Date(),
      collections,
      documentCount: 0,
      sizeBytes: 0
    };

    const bucket = storage.bucket(bucketName);

    for (const collectionName of collections) {
      const snapshot = await db.collection(collectionName).get();
      const documents = snapshot.docs.map(doc => ({
        id: doc.id,
        data: doc.to_dict()
      }));

      const content = JSON.stringify(documents, null, 2);
      const filePath = `${backupId}/${collectionName}.json`;

      await bucket.file(filePath).save(content, {
        contentType: 'application/json',
        metadata: {
          backupId,
          collection: collectionName,
          documentCount: documents.length.toString()
        }
      });

      metadata.documentCount += documents.length;
      metadata.sizeBytes += Buffer.byteLength(content);
    }

    // Save backup metadata
    await db.collection('backups').doc(backupId).set(metadata);

    console.log(`Backup ${backupId} completed: ${metadata.documentCount} documents`);
    return null;
  });

// Manual backup trigger
export const triggerBackup = functions.https.onCall(async (data, context) => {
  // Check admin permission
  if (!context.auth?.token.admin) {
    throw new functions.https.HttpsError('permission-denied', 'Admin only');
  }

  const collections = data.collections || ['users', 'orders', 'products'];
  // Trigger backup logic...
  return { message: 'Backup started', collections };
});

// Restore from backup
export const restoreFromBackup = functions.https.onCall(async (data, context) => {
  if (!context.auth?.token.admin) {
    throw new functions.https.HttpsError('permission-denied', 'Admin only');
  }

  const { backupId, collections, targetPrefix } = data;
  const bucket = storage.bucket(bucketName);

  for (const collectionName of collections) {
    const filePath = `${backupId}/${collectionName}.json`;
    const [content] = await bucket.file(filePath).download();
    const documents = JSON.parse(content.toString());

    const targetCollection = targetPrefix
      ? `${targetPrefix}_${collectionName}`
      : collectionName;

    // Batch restore
    const batch = db.batch();
    let count = 0;

    for (const doc of documents) {
      const ref = db.collection(targetCollection).doc(doc.id);
      batch.set(ref, doc.data);
      count++;

      if (count % 500 === 0) {
        await batch.commit();
      }
    }

    await batch.commit();
    console.log(`Restored ${count} documents to ${targetCollection}`);
  }

  return { message: 'Restore completed', collections };
});'''
    },
    {
        "instruction": "Write TypeScript code for a Firestore change data capture (CDC) system",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import { PubSub } from '@google-cloud/pubsub';

admin.initializeApp();
const db = admin.firestore();
const pubsub = new PubSub();

interface ChangeEvent {
  eventType: 'CREATE' | 'UPDATE' | 'DELETE';
  collection: string;
  documentId: string;
  timestamp: string;
  before?: Record<string, any>;
  after?: Record<string, any>;
  changedFields?: string[];
  userId?: string;
}

// Publish change events to Pub/Sub
async function publishChangeEvent(event: ChangeEvent) {
  const topicName = `firestore-changes-${event.collection}`;

  try {
    const topic = pubsub.topic(topicName);
    const [exists] = await topic.exists();

    if (!exists) {
      await pubsub.createTopic(topicName);
    }

    await topic.publishMessage({
      data: Buffer.from(JSON.stringify(event)),
      attributes: {
        eventType: event.eventType,
        collection: event.collection,
        documentId: event.documentId
      }
    });
  } catch (error) {
    console.error('Failed to publish event:', error);
    // Store failed events for retry
    await db.collection('_cdc_failed_events').add({
      ...event,
      error: (error as Error).message,
      retryCount: 0
    });
  }
}

// Get changed fields between two objects
function getChangedFields(before: any, after: any): string[] {
  const allKeys = new Set([...Object.keys(before), ...Object.keys(after)]);
  const changed: string[] = [];

  for (const key of allKeys) {
    if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) {
      changed.push(key);
    }
  }

  return changed;
}

// CDC trigger for users collection
export const usersChangeCapture = functions.firestore
  .document('users/{userId}')
  .onWrite(async (change, context) => {
    const userId = context.params.userId;
    const before = change.before.exists ? change.before.data() : null;
    const after = change.after.exists ? change.after.data() : null;

    let eventType: ChangeEvent['eventType'];
    if (!before) eventType = 'CREATE';
    else if (!after) eventType = 'DELETE';
    else eventType = 'UPDATE';

    const event: ChangeEvent = {
      eventType,
      collection: 'users',
      documentId: userId,
      timestamp: context.timestamp,
      before: before || undefined,
      after: after || undefined,
      changedFields: before && after ? getChangedFields(before, after) : undefined
    };

    await publishChangeEvent(event);

    // Also log to audit collection
    await db.collection('_audit_log').add({
      ...event,
      createdAt: admin.firestore.FieldValue.serverTimestamp()
    });

    return null;
  });

// CDC trigger for orders collection
export const ordersChangeCapture = functions.firestore
  .document('orders/{orderId}')
  .onWrite(async (change, context) => {
    const orderId = context.params.orderId;
    const before = change.before.data();
    const after = change.after.data();

    // Check for status changes specifically
    if (before?.status !== after?.status) {
      await db.collection('order_status_history').add({
        orderId,
        fromStatus: before?.status,
        toStatus: after?.status,
        changedAt: admin.firestore.FieldValue.serverTimestamp(),
        changedBy: after?.lastModifiedBy || 'system'
      });
    }

    // Publish generic change event
    await publishChangeEvent({
      eventType: !before ? 'CREATE' : !after ? 'DELETE' : 'UPDATE',
      collection: 'orders',
      documentId: orderId,
      timestamp: context.timestamp,
      before,
      after,
      changedFields: before && after ? getChangedFields(before, after) : undefined
    });

    return null;
  });'''
    },
]

# =============================================================================
# ERROR HANDLING EXAMPLES
# =============================================================================

ERROR_HANDLING = [
    {
        "instruction": "Write Python code to handle all common Firestore errors gracefully",
        "output": '''from firebase_admin import firestore
from google.api_core.exceptions import (
    NotFound, AlreadyExists, PermissionDenied,
    InvalidArgument, ResourceExhausted, Aborted,
    DeadlineExceeded, Cancelled, Unknown
)
from enum import Enum
from typing import Optional, TypeVar, Generic
from dataclasses import dataclass

class FirestoreErrorType(Enum):
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    PERMISSION_DENIED = "permission_denied"
    INVALID_ARGUMENT = "invalid_argument"
    RATE_LIMITED = "rate_limited"
    TRANSACTION_ABORTED = "transaction_aborted"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"

@dataclass
class FirestoreError:
    type: FirestoreErrorType
    message: str
    original_error: Optional[Exception] = None
    retry_after: Optional[int] = None

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[FirestoreError] = None

def handle_firestore_error(e: Exception) -> FirestoreError:
    """Convert Firestore exceptions to FirestoreError."""
    if isinstance(e, NotFound):
        return FirestoreError(
            type=FirestoreErrorType.NOT_FOUND,
            message="Document or collection not found",
            original_error=e
        )
    elif isinstance(e, AlreadyExists):
        return FirestoreError(
            type=FirestoreErrorType.ALREADY_EXISTS,
            message="Document already exists",
            original_error=e
        )
    elif isinstance(e, PermissionDenied):
        return FirestoreError(
            type=FirestoreErrorType.PERMISSION_DENIED,
            message="Permission denied. Check security rules.",
            original_error=e
        )
    elif isinstance(e, InvalidArgument):
        return FirestoreError(
            type=FirestoreErrorType.INVALID_ARGUMENT,
            message=f"Invalid argument: {str(e)}",
            original_error=e
        )
    elif isinstance(e, ResourceExhausted):
        return FirestoreError(
            type=FirestoreErrorType.RATE_LIMITED,
            message="Rate limit exceeded. Retry later.",
            original_error=e,
            retry_after=60
        )
    elif isinstance(e, Aborted):
        return FirestoreError(
            type=FirestoreErrorType.TRANSACTION_ABORTED,
            message="Transaction was aborted. Retry.",
            original_error=e
        )
    elif isinstance(e, DeadlineExceeded):
        return FirestoreError(
            type=FirestoreErrorType.TIMEOUT,
            message="Operation timed out",
            original_error=e
        )
    elif isinstance(e, Cancelled):
        return FirestoreError(
            type=FirestoreErrorType.CANCELLED,
            message="Operation was cancelled",
            original_error=e
        )
    else:
        return FirestoreError(
            type=FirestoreErrorType.UNKNOWN,
            message=str(e),
            original_error=e
        )


class SafeFirestore:
    """Firestore client with automatic error handling."""

    def __init__(self):
        self.db = firestore.client()

    def get_document(self, collection: str, doc_id: str) -> Result[dict]:
        """Get document with error handling."""
        try:
            doc = self.db.collection(collection).document(doc_id).get()
            if doc.exists:
                return Result(success=True, data={'id': doc.id, **doc.to_dict()})
            return Result(
                success=False,
                error=FirestoreError(
                    type=FirestoreErrorType.NOT_FOUND,
                    message=f"Document {doc_id} not found in {collection}"
                )
            )
        except Exception as e:
            return Result(success=False, error=handle_firestore_error(e))

    def set_document(self, collection: str, doc_id: str, data: dict) -> Result[str]:
        """Set document with error handling."""
        try:
            self.db.collection(collection).document(doc_id).set(data)
            return Result(success=True, data=doc_id)
        except Exception as e:
            return Result(success=False, error=handle_firestore_error(e))


# Usage
fs = SafeFirestore()
result = fs.get_document('users', 'user_123')

if result.success:
    print(f"User: {result.data}")
else:
    print(f"Error: {result.error.type.value} - {result.error.message}")'''
    },
    {
        "instruction": "Write JavaScript code to implement error boundaries for Firestore operations in React",
        "output": '''import React, { Component, useState, useEffect } from 'react';
import { FirestoreError } from 'firebase/firestore';

// Error type definitions
type FirestoreErrorCode =
  | 'cancelled'
  | 'unknown'
  | 'invalid-argument'
  | 'deadline-exceeded'
  | 'not-found'
  | 'already-exists'
  | 'permission-denied'
  | 'resource-exhausted'
  | 'failed-precondition'
  | 'aborted'
  | 'out-of-range'
  | 'unimplemented'
  | 'internal'
  | 'unavailable'
  | 'data-loss'
  | 'unauthenticated';

interface ErrorInfo {
  code: FirestoreErrorCode;
  message: string;
  userMessage: string;
  canRetry: boolean;
}

// Map Firestore errors to user-friendly messages
function getErrorInfo(error: FirestoreError): ErrorInfo {
  const errorMap: Record<string, Partial<ErrorInfo>> = {
    'permission-denied': {
      userMessage: 'You don\\'t have permission to perform this action.',
      canRetry: false
    },
    'not-found': {
      userMessage: 'The requested data was not found.',
      canRetry: false
    },
    'already-exists': {
      userMessage: 'This item already exists.',
      canRetry: false
    },
    'resource-exhausted': {
      userMessage: 'Too many requests. Please wait a moment.',
      canRetry: true
    },
    'unavailable': {
      userMessage: 'Service temporarily unavailable. Please try again.',
      canRetry: true
    },
    'unauthenticated': {
      userMessage: 'Please sign in to continue.',
      canRetry: false
    }
  };

  const info = errorMap[error.code] || {
    userMessage: 'An unexpected error occurred. Please try again.',
    canRetry: true
  };

  return {
    code: error.code as FirestoreErrorCode,
    message: error.message,
    userMessage: info.userMessage!,
    canRetry: info.canRetry!
  };
}

// Error Boundary Component
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class FirestoreErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.props.onError?.(error);

    if (error instanceof FirestoreError) {
      this.setState({ errorInfo: getErrorInfo(error) });
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { errorInfo } = this.state;

      return (
        <div className="error-container">
          <h2>Something went wrong</h2>
          <p>{errorInfo?.userMessage || 'An error occurred'}</p>
          {errorInfo?.canRetry && (
            <button onClick={this.handleRetry}>Try Again</button>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook for handling async Firestore errors
function useFirestoreError() {
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleError = (err: unknown) => {
    if (err instanceof FirestoreError) {
      setError(getErrorInfo(err));
    } else if (err instanceof Error) {
      setError({
        code: 'unknown',
        message: err.message,
        userMessage: 'An unexpected error occurred.',
        canRetry: true
      });
    }
  };

  const clearError = () => setError(null);

  return { error, handleError, clearError };
}

// Usage
function UserList() {
  const { error, handleError, clearError } = useFirestoreError();
  const [users, setUsers] = useState([]);

  const loadUsers = async () => {
    try {
      clearError();
      // Firestore operation
    } catch (err) {
      handleError(err);
    }
  };

  return (
    <FirestoreErrorBoundary onError={console.error}>
      {error && (
        <div className="error-banner">
          {error.userMessage}
          {error.canRetry && <button onClick={loadUsers}>Retry</button>}
        </div>
      )}
      {/* User list content */}
    </FirestoreErrorBoundary>
  );
}'''
    },
]

# =============================================================================
# TESTING EXAMPLES
# =============================================================================

TESTING_EXAMPLES = [
    {
        "instruction": "Write Python code to test Firestore operations using the Firestore emulator",
        "output": '''import pytest
import os
from firebase_admin import firestore, initialize_app, credentials
from unittest.mock import patch

# Configure emulator
os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'

@pytest.fixture(scope='session')
def db():
    """Initialize Firestore client for testing."""
    # Use emulator - no credentials needed
    if not firebase_admin._apps:
        initialize_app(options={'projectId': 'test-project'})
    return firestore.client()


@pytest.fixture(autouse=True)
def clear_firestore(db):
    """Clear all collections before each test."""
    # Note: In real tests, use the emulator's REST API to clear data
    yield
    # Cleanup after test


class TestUserRepository:
    def test_create_user(self, db):
        """Test creating a new user."""
        user_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'role': 'user'
        }

        # Create user
        doc_ref = db.collection('users').add(user_data)
        user_id = doc_ref[1].id

        # Verify
        doc = db.collection('users').document(user_id).get()
        assert doc.exists
        assert doc.to_dict()['email'] == 'test@example.com'

    def test_get_user_by_email(self, db):
        """Test querying user by email."""
        # Setup
        db.collection('users').add({
            'email': 'findme@example.com',
            'name': 'Find Me'
        })

        # Query
        docs = db.collection('users') \\
            .where('email', '==', 'findme@example.com') \\
            .limit(1) \\
            .stream()

        users = list(docs)
        assert len(users) == 1
        assert users[0].to_dict()['name'] == 'Find Me'

    def test_update_user(self, db):
        """Test updating a user."""
        # Setup
        doc_ref = db.collection('users').add({'name': 'Original'})
        user_id = doc_ref[1].id

        # Update
        db.collection('users').document(user_id).update({
            'name': 'Updated'
        })

        # Verify
        doc = db.collection('users').document(user_id).get()
        assert doc.to_dict()['name'] == 'Updated'

    def test_delete_user(self, db):
        """Test deleting a user."""
        # Setup
        doc_ref = db.collection('users').add({'name': 'Delete Me'})
        user_id = doc_ref[1].id

        # Delete
        db.collection('users').document(user_id).delete()

        # Verify
        doc = db.collection('users').document(user_id).get()
        assert not doc.exists

    def test_transaction(self, db):
        """Test transaction functionality."""
        # Setup accounts
        db.collection('accounts').document('a').set({'balance': 100})
        db.collection('accounts').document('b').set({'balance': 50})

        @firestore.transactional
        def transfer(transaction, from_ref, to_ref, amount):
            from_doc = from_ref.get(transaction=transaction)
            to_doc = to_ref.get(transaction=transaction)

            from_balance = from_doc.get('balance')
            to_balance = to_doc.get('balance')

            transaction.update(from_ref, {'balance': from_balance - amount})
            transaction.update(to_ref, {'balance': to_balance + amount})

        from_ref = db.collection('accounts').document('a')
        to_ref = db.collection('accounts').document('b')

        transaction = db.transaction()
        transfer(transaction, from_ref, to_ref, 30)

        # Verify
        assert db.collection('accounts').document('a').get().get('balance') == 70
        assert db.collection('accounts').document('b').get().get('balance') == 80


# Run with: pytest test_firestore.py -v'''
    },
    {
        "instruction": "Write TypeScript code to test Firestore with Jest and Firebase emulators",
        "output": '''import {
  initializeTestEnvironment,
  RulesTestEnvironment,
  assertFails,
  assertSucceeds
} from '@firebase/rules-unit-testing';
import { doc, setDoc, getDoc, deleteDoc, collection, getDocs } from 'firebase/firestore';
import * as fs from 'fs';

let testEnv: RulesTestEnvironment;

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: 'test-project',
    firestore: {
      rules: fs.readFileSync('firestore.rules', 'utf8'),
      host: 'localhost',
      port: 8080
    }
  });
});

afterAll(async () => {
  await testEnv.cleanup();
});

beforeEach(async () => {
  await testEnv.clearFirestore();
});

describe('Firestore Security Rules', () => {
  describe('Users collection', () => {
    it('allows users to read their own profile', async () => {
      const userId = 'user123';
      const context = testEnv.authenticatedContext(userId);
      const db = context.firestore();

      // Setup: Create user document
      await testEnv.withSecurityRulesDisabled(async (adminContext) => {
        const adminDb = adminContext.firestore();
        await setDoc(doc(adminDb, 'users', userId), {
          name: 'Test User',
          email: 'test@example.com'
        });
      });

      // Test: User can read their own profile
      await assertSucceeds(getDoc(doc(db, 'users', userId)));
    });

    it('denies users from reading other profiles', async () => {
      const context = testEnv.authenticatedContext('user123');
      const db = context.firestore();

      // Setup
      await testEnv.withSecurityRulesDisabled(async (adminContext) => {
        const adminDb = adminContext.firestore();
        await setDoc(doc(adminDb, 'users', 'other-user'), {
          name: 'Other User',
          private: true
        });
      });

      // Test: Cannot read other user's profile
      await assertFails(getDoc(doc(db, 'users', 'other-user')));
    });

    it('allows users to create their own profile', async () => {
      const userId = 'newuser';
      const context = testEnv.authenticatedContext(userId);
      const db = context.firestore();

      await assertSucceeds(
        setDoc(doc(db, 'users', userId), {
          name: 'New User',
          email: 'new@example.com'
        })
      );
    });

    it('denies unauthenticated access', async () => {
      const context = testEnv.unauthenticatedContext();
      const db = context.firestore();

      await assertFails(getDoc(doc(db, 'users', 'anyuser')));
    });
  });

  describe('Posts collection', () => {
    it('allows anyone to read published posts', async () => {
      // Setup
      await testEnv.withSecurityRulesDisabled(async (adminContext) => {
        const adminDb = adminContext.firestore();
        await setDoc(doc(adminDb, 'posts', 'post1'), {
          title: 'Public Post',
          published: true,
          authorId: 'author1'
        });
      });

      const context = testEnv.unauthenticatedContext();
      const db = context.firestore();

      await assertSucceeds(getDoc(doc(db, 'posts', 'post1')));
    });

    it('denies reading unpublished posts from non-authors', async () => {
      await testEnv.withSecurityRulesDisabled(async (adminContext) => {
        const adminDb = adminContext.firestore();
        await setDoc(doc(adminDb, 'posts', 'draft'), {
          title: 'Draft Post',
          published: false,
          authorId: 'author1'
        });
      });

      const context = testEnv.authenticatedContext('not-the-author');
      const db = context.firestore();

      await assertFails(getDoc(doc(db, 'posts', 'draft')));
    });

    it('validates post data on create', async () => {
      const context = testEnv.authenticatedContext('user123');
      const db = context.firestore();

      // Missing required title field should fail
      await assertFails(
        setDoc(doc(db, 'posts', 'invalid'), {
          authorId: 'user123',
          published: false
          // missing 'title'
        })
      );

      // Valid post should succeed
      await assertSucceeds(
        setDoc(doc(db, 'posts', 'valid'), {
          title: 'Valid Post',
          authorId: 'user123',
          published: false
        })
      );
    });
  });
});

describe('Firestore Operations', () => {
  it('handles batch writes correctly', async () => {
    await testEnv.withSecurityRulesDisabled(async (context) => {
      const db = context.firestore();

      // Create multiple documents
      const batch = writeBatch(db);
      batch.set(doc(db, 'items', '1'), { name: 'Item 1' });
      batch.set(doc(db, 'items', '2'), { name: 'Item 2' });
      batch.set(doc(db, 'items', '3'), { name: 'Item 3' });
      await batch.commit();

      // Verify all documents exist
      const snapshot = await getDocs(collection(db, 'items'));
      expect(snapshot.size).toBe(3);
    });
  });
});'''
    },
]

# =============================================================================
# COMBINE ALL ADDITIONAL EXAMPLES
# =============================================================================

def get_all_examples():
    """Get all examples from all categories."""
    from generate_firebase_data import (
        PYTHON_FIRESTORE_CRUD, PYTHON_FIRESTORE_QUERIES,
        PYTHON_FIRESTORE_TRANSACTIONS, PYTHON_FIRESTORE_LISTENERS,
        PYTHON_FIREBASE_AUTH, JS_FIRESTORE_CRUD, JS_FIRESTORE_QUERIES,
        JS_FIRESTORE_REALTIME, JS_FIRESTORE_TRANSACTIONS,
        FIREBASE_SECURITY_RULES, CLOUD_FUNCTIONS, JS_FIREBASE_AUTH
    )

    all_categories = [
        # Original categories
        ("Python Firestore CRUD", PYTHON_FIRESTORE_CRUD),
        ("Python Firestore Queries", PYTHON_FIRESTORE_QUERIES),
        ("Python Firestore Transactions", PYTHON_FIRESTORE_TRANSACTIONS),
        ("Python Firestore Listeners", PYTHON_FIRESTORE_LISTENERS),
        ("Python Firebase Auth", PYTHON_FIREBASE_AUTH),
        ("JavaScript Firestore CRUD", JS_FIRESTORE_CRUD),
        ("JavaScript Firestore Queries", JS_FIRESTORE_QUERIES),
        ("JavaScript Firestore Realtime", JS_FIRESTORE_REALTIME),
        ("JavaScript Firestore Transactions", JS_FIRESTORE_TRANSACTIONS),
        ("Firebase Security Rules", FIREBASE_SECURITY_RULES),
        ("Cloud Functions", CLOUD_FUNCTIONS),
        ("JavaScript Firebase Auth", JS_FIREBASE_AUTH),
        # New categories
        ("Python Advanced Patterns", PYTHON_ADVANCED),
        ("JavaScript Advanced Patterns", JS_ADVANCED),
        ("Error Handling", ERROR_HANDLING),
        ("Testing", TESTING_EXAMPLES),
    ]

    examples = []
    for category_name, category_examples in all_categories:
        for example in category_examples:
            formatted = {
                "messages": [
                    {"role": "system", "content": "You are an expert Firebase and Firestore developer. Write clean, efficient, and well-documented code."},
                    {"role": "user", "content": example["instruction"]},
                    {"role": "assistant", "content": example["output"]}
                ]
            }
            examples.append(formatted)

    return examples


def main():
    from pathlib import Path
    import sys

    # Add parent directory to path to import from generate_firebase_data
    sys.path.insert(0, str(Path(__file__).parent))

    examples = get_all_examples()

    print(f"Total examples: {len(examples)}")

    # Split into train/valid (90/10)
    random.shuffle(examples)
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    output_dir = Path("/Users/fredtaylor/Development/Projects/AITeamPlatform/mlx-training/data/firebase")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write training data
    train_path = output_dir / "train.jsonl"
    with open(train_path, "w") as f:
        for example in train_examples:
            f.write(json.dumps(example) + "\n")

    # Write validation data
    valid_path = output_dir / "valid.jsonl"
    with open(valid_path, "w") as f:
        for example in valid_examples:
            f.write(json.dumps(example) + "\n")

    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(valid_examples)}")
    print(f"Saved to: {output_dir}")


if __name__ == "__main__":
    main()
