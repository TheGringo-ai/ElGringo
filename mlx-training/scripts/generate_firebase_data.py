#!/usr/bin/env python3
"""
Generate synthetic Firebase/Firestore training data for LLM fine-tuning.
Creates diverse examples covering CRUD, queries, transactions, security rules,
Cloud Functions, and authentication patterns in Python and JavaScript/TypeScript.
"""

import json
import random
from pathlib import Path

# Firebase/Firestore training examples organized by category
FIREBASE_EXAMPLES = []

# =============================================================================
# PYTHON - FIRESTORE CRUD OPERATIONS
# =============================================================================

PYTHON_FIRESTORE_CRUD = [
    {
        "instruction": "Write Python code to initialize Firebase Admin SDK and connect to Firestore",
        "output": '''import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK with service account
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

print("Successfully connected to Firestore")'''
    },
    {
        "instruction": "Write Python code to add a new document to a Firestore collection with auto-generated ID",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Add a new document with auto-generated ID
doc_ref = db.collection('users').add({
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30,
    'created_at': firestore.SERVER_TIMESTAMP
})

print(f"Document added with ID: {doc_ref[1].id}")'''
    },
    {
        "instruction": "Write Python code to set a document with a specific ID in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Set document with specific ID (creates or overwrites)
db.collection('users').document('user_123').set({
    'name': 'Jane Smith',
    'email': 'jane@example.com',
    'role': 'admin',
    'created_at': firestore.SERVER_TIMESTAMP
})

print("Document created/updated successfully")'''
    },
    {
        "instruction": "Write Python code to update specific fields in a Firestore document without overwriting the entire document",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Update specific fields only (merge)
doc_ref = db.collection('users').document('user_123')
doc_ref.update({
    'email': 'newemail@example.com',
    'updated_at': firestore.SERVER_TIMESTAMP,
    'login_count': firestore.Increment(1)
})

print("Document fields updated successfully")'''
    },
    {
        "instruction": "Write Python code to read a single document from Firestore by ID",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Get a single document
doc_ref = db.collection('users').document('user_123')
doc = doc_ref.get()

if doc.exists:
    user_data = doc.to_dict()
    print(f"User: {user_data['name']}, Email: {user_data['email']}")
else:
    print("Document not found")'''
    },
    {
        "instruction": "Write Python code to delete a document from Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Delete a document
db.collection('users').document('user_123').delete()

print("Document deleted successfully")'''
    },
    {
        "instruction": "Write Python code to delete a specific field from a Firestore document",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Delete a specific field from document
doc_ref = db.collection('users').document('user_123')
doc_ref.update({
    'temporary_field': firestore.DELETE_FIELD
})

print("Field deleted successfully")'''
    },
    {
        "instruction": "Write Python code to get all documents from a Firestore collection",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Get all documents from collection
docs = db.collection('users').stream()

users = []
for doc in docs:
    user = doc.to_dict()
    user['id'] = doc.id
    users.append(user)

print(f"Found {len(users)} users")
for user in users:
    print(f"  - {user['name']} ({user['email']})")'''
    },
    {
        "instruction": "Write Python code to check if a Firestore document exists",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def document_exists(collection: str, doc_id: str) -> bool:
    """Check if a document exists in Firestore."""
    doc = db.collection(collection).document(doc_id).get()
    return doc.exists

# Usage
if document_exists('users', 'user_123'):
    print("User exists")
else:
    print("User not found")'''
    },
    {
        "instruction": "Write Python code to add an element to an array field in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Add element to array (won't add if already exists)
doc_ref = db.collection('users').document('user_123')
doc_ref.update({
    'tags': firestore.ArrayUnion(['premium', 'verified'])
})

print("Tags added to user")'''
    },
    {
        "instruction": "Write Python code to remove an element from an array field in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Remove element from array
doc_ref = db.collection('users').document('user_123')
doc_ref.update({
    'tags': firestore.ArrayRemove(['unverified'])
})

print("Tag removed from user")'''
    },
    {
        "instruction": "Write Python code to increment a numeric field in Firestore atomically",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Atomically increment a field
doc_ref = db.collection('products').document('product_123')
doc_ref.update({
    'view_count': firestore.Increment(1),
    'stock': firestore.Increment(-1)  # Decrement by 1
})

print("Counters updated atomically")'''
    },
]

# =============================================================================
# PYTHON - FIRESTORE QUERIES
# =============================================================================

PYTHON_FIRESTORE_QUERIES = [
    {
        "instruction": "Write Python code to query Firestore documents where a field equals a specific value",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query where field equals value
users_ref = db.collection('users')
query = users_ref.where('role', '==', 'admin')
docs = query.stream()

admins = [doc.to_dict() for doc in docs]
print(f"Found {len(admins)} admin users")'''
    },
    {
        "instruction": "Write Python code to query Firestore with multiple where conditions",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Multiple where conditions (AND)
users_ref = db.collection('users')
query = (users_ref
    .where('age', '>=', 18)
    .where('age', '<=', 65)
    .where('status', '==', 'active'))

docs = query.stream()
users = [doc.to_dict() for doc in docs]
print(f"Found {len(users)} active adult users")'''
    },
    {
        "instruction": "Write Python code to query Firestore with ordering and limit",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Order by field and limit results
posts_ref = db.collection('posts')
query = (posts_ref
    .order_by('created_at', direction=firestore.Query.DESCENDING)
    .limit(10))

docs = query.stream()
recent_posts = [doc.to_dict() for doc in docs]
print(f"Latest {len(recent_posts)} posts retrieved")'''
    },
    {
        "instruction": "Write Python code to query Firestore with pagination using start_after",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def get_paginated_users(last_doc=None, page_size=20):
    """Get paginated users from Firestore."""
    query = db.collection('users').order_by('name').limit(page_size)

    if last_doc:
        query = query.start_after(last_doc)

    docs = list(query.stream())
    users = [{'id': doc.id, **doc.to_dict()} for doc in docs]

    # Return users and last document for next page
    last = docs[-1] if docs else None
    return users, last

# Usage: Get first page
users, last_doc = get_paginated_users()

# Get next page
next_users, last_doc = get_paginated_users(last_doc)'''
    },
    {
        "instruction": "Write Python code to query Firestore for documents where array contains a value",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query where array contains value
posts_ref = db.collection('posts')
query = posts_ref.where('tags', 'array_contains', 'python')

docs = query.stream()
python_posts = [doc.to_dict() for doc in docs]
print(f"Found {len(python_posts)} posts tagged with 'python'")'''
    },
    {
        "instruction": "Write Python code to query Firestore where array contains any of multiple values",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query where array contains any of these values
posts_ref = db.collection('posts')
query = posts_ref.where('tags', 'array_contains_any', ['python', 'javascript', 'typescript'])

docs = query.stream()
programming_posts = [doc.to_dict() for doc in docs]
print(f"Found {len(programming_posts)} programming posts")'''
    },
    {
        "instruction": "Write Python code to query Firestore where field value is in a list",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query where field is in list of values
users_ref = db.collection('users')
query = users_ref.where('status', 'in', ['active', 'pending'])

docs = query.stream()
users = [doc.to_dict() for doc in docs]
print(f"Found {len(users)} active or pending users")'''
    },
    {
        "instruction": "Write Python code to query Firestore where field value is not in a list",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query where field is NOT in list
users_ref = db.collection('users')
query = users_ref.where('role', 'not-in', ['banned', 'suspended'])

docs = query.stream()
valid_users = [doc.to_dict() for doc in docs]
print(f"Found {len(valid_users)} non-banned users")'''
    },
    {
        "instruction": "Write Python code to perform a collection group query in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query across all subcollections named 'comments'
# This finds all comments regardless of which post they belong to
comments_ref = db.collection_group('comments')
query = comments_ref.where('author_id', '==', 'user_123')

docs = query.stream()
user_comments = [{'id': doc.id, **doc.to_dict()} for doc in docs]
print(f"User has {len(user_comments)} comments across all posts")'''
    },
    {
        "instruction": "Write Python code to query Firestore with a date range filter",
        "output": '''from firebase_admin import firestore
from datetime import datetime, timedelta

db = firestore.client()

# Query documents within a date range
start_date = datetime.now() - timedelta(days=7)
end_date = datetime.now()

orders_ref = db.collection('orders')
query = (orders_ref
    .where('created_at', '>=', start_date)
    .where('created_at', '<=', end_date)
    .order_by('created_at', direction=firestore.Query.DESCENDING))

docs = query.stream()
recent_orders = [doc.to_dict() for doc in docs]
print(f"Found {len(recent_orders)} orders in the last 7 days")'''
    },
    {
        "instruction": "Write Python code to count documents in a Firestore collection",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Count documents matching a query (Firestore v2)
users_ref = db.collection('users')
query = users_ref.where('status', '==', 'active')

# Get aggregation count
aggregate = query.count().get()
count = aggregate[0][0].value

print(f"Total active users: {count}")'''
    },
]

# =============================================================================
# PYTHON - FIRESTORE TRANSACTIONS AND BATCHES
# =============================================================================

PYTHON_FIRESTORE_TRANSACTIONS = [
    {
        "instruction": "Write Python code to perform a Firestore transaction for transferring money between accounts",
        "output": '''from firebase_admin import firestore

db = firestore.client()

@firestore.transactional
def transfer_funds(transaction, from_account_ref, to_account_ref, amount):
    """Transfer funds between two accounts atomically."""
    from_snapshot = from_account_ref.get(transaction=transaction)
    to_snapshot = to_account_ref.get(transaction=transaction)

    if not from_snapshot.exists or not to_snapshot.exists:
        raise ValueError("One or both accounts don't exist")

    from_balance = from_snapshot.get('balance')
    if from_balance < amount:
        raise ValueError("Insufficient funds")

    # Update both accounts atomically
    transaction.update(from_account_ref, {'balance': from_balance - amount})
    transaction.update(to_account_ref, {
        'balance': to_snapshot.get('balance') + amount
    })

    return True

# Usage
from_ref = db.collection('accounts').document('account_a')
to_ref = db.collection('accounts').document('account_b')

transaction = db.transaction()
try:
    transfer_funds(transaction, from_ref, to_ref, 100.00)
    print("Transfer successful")
except Exception as e:
    print(f"Transfer failed: {e}")'''
    },
    {
        "instruction": "Write Python code to use Firestore batch writes to update multiple documents atomically",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Create a batch
batch = db.batch()

# Add multiple operations to batch
user_ref = db.collection('users').document('user_123')
batch.update(user_ref, {'last_active': firestore.SERVER_TIMESTAMP})

# Create a new document
new_log_ref = db.collection('activity_logs').document()
batch.set(new_log_ref, {
    'user_id': 'user_123',
    'action': 'login',
    'timestamp': firestore.SERVER_TIMESTAMP
})

# Delete old sessions
old_session_ref = db.collection('sessions').document('old_session')
batch.delete(old_session_ref)

# Commit all operations atomically
batch.commit()
print("Batch write completed successfully")'''
    },
    {
        "instruction": "Write Python code to perform batch writes with more than 500 operations in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def batch_write_large(collection_name: str, documents: list):
    """Write large number of documents using multiple batches.
    Firestore limits batches to 500 operations.
    """
    batch_size = 500
    total = len(documents)

    for i in range(0, total, batch_size):
        batch = db.batch()
        chunk = documents[i:i + batch_size]

        for doc_data in chunk:
            doc_ref = db.collection(collection_name).document()
            batch.set(doc_ref, doc_data)

        batch.commit()
        print(f"Committed batch {i // batch_size + 1} ({len(chunk)} documents)")

    print(f"Total {total} documents written")

# Usage
products = [{'name': f'Product {i}', 'price': i * 10} for i in range(1500)]
batch_write_large('products', products)'''
    },
    {
        "instruction": "Write Python code for a Firestore transaction that implements optimistic locking with version numbers",
        "output": '''from firebase_admin import firestore

db = firestore.client()

@firestore.transactional
def update_with_version(transaction, doc_ref, updates, expected_version):
    """Update document only if version matches (optimistic locking)."""
    snapshot = doc_ref.get(transaction=transaction)

    if not snapshot.exists:
        raise ValueError("Document does not exist")

    current_version = snapshot.get('version', 0)
    if current_version != expected_version:
        raise ValueError(f"Version conflict: expected {expected_version}, got {current_version}")

    # Include version increment in updates
    updates['version'] = current_version + 1
    updates['updated_at'] = firestore.SERVER_TIMESTAMP

    transaction.update(doc_ref, updates)
    return updates['version']

# Usage
doc_ref = db.collection('documents').document('doc_123')
transaction = db.transaction()

try:
    new_version = update_with_version(
        transaction,
        doc_ref,
        {'content': 'Updated content'},
        expected_version=5
    )
    print(f"Document updated to version {new_version}")
except ValueError as e:
    print(f"Update failed: {e}")'''
    },
]

# =============================================================================
# PYTHON - FIRESTORE REAL-TIME LISTENERS
# =============================================================================

PYTHON_FIRESTORE_LISTENERS = [
    {
        "instruction": "Write Python code to listen for real-time updates on a Firestore document",
        "output": '''from firebase_admin import firestore
import threading

db = firestore.client()

# Callback function for document changes
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if doc.exists:
            print(f"Document data: {doc.to_dict()}")
        else:
            print("Document was deleted")

# Create a listener
doc_ref = db.collection('users').document('user_123')
doc_watch = doc_ref.on_snapshot(on_snapshot)

# Keep the listener running
print("Listening for changes... Press Ctrl+C to stop")
try:
    threading.Event().wait()
except KeyboardInterrupt:
    doc_watch.unsubscribe()
    print("Listener stopped")'''
    },
    {
        "instruction": "Write Python code to listen for real-time updates on a Firestore collection with query",
        "output": '''from firebase_admin import firestore
import threading

db = firestore.client()

def on_collection_snapshot(col_snapshot, changes, read_time):
    """Handle collection changes with change type detection."""
    for change in changes:
        doc = change.document
        if change.type.name == 'ADDED':
            print(f"New document: {doc.id} => {doc.to_dict()}")
        elif change.type.name == 'MODIFIED':
            print(f"Modified document: {doc.id} => {doc.to_dict()}")
        elif change.type.name == 'REMOVED':
            print(f"Removed document: {doc.id}")

# Listen to query results
query = (db.collection('orders')
    .where('status', '==', 'pending')
    .order_by('created_at'))

query_watch = query.on_snapshot(on_collection_snapshot)

print("Listening for pending orders...")
try:
    threading.Event().wait()
except KeyboardInterrupt:
    query_watch.unsubscribe()'''
    },
]

# =============================================================================
# PYTHON - FIREBASE AUTHENTICATION
# =============================================================================

PYTHON_FIREBASE_AUTH = [
    {
        "instruction": "Write Python code to verify a Firebase ID token on the server side",
        "output": '''from firebase_admin import auth

def verify_firebase_token(id_token: str) -> dict:
    """Verify Firebase ID token and return decoded claims."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email')

        return {
            'valid': True,
            'uid': uid,
            'email': email,
            'claims': decoded_token
        }
    except auth.InvalidIdTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except auth.ExpiredIdTokenError:
        return {'valid': False, 'error': 'Token expired'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

# Usage in Flask/FastAPI
# token = request.headers.get('Authorization', '').replace('Bearer ', '')
# result = verify_firebase_token(token)'''
    },
    {
        "instruction": "Write Python code to create a new Firebase user with email and password",
        "output": '''from firebase_admin import auth

def create_user(email: str, password: str, display_name: str = None) -> dict:
    """Create a new Firebase user."""
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )

        return {
            'success': True,
            'uid': user.uid,
            'email': user.email,
            'display_name': user.display_name
        }
    except auth.EmailAlreadyExistsError:
        return {'success': False, 'error': 'Email already exists'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Usage
result = create_user('newuser@example.com', 'securepassword123', 'John Doe')
if result['success']:
    print(f"Created user with UID: {result['uid']}")'''
    },
    {
        "instruction": "Write Python code to set custom claims on a Firebase user for role-based access control",
        "output": '''from firebase_admin import auth

def set_user_role(uid: str, role: str, permissions: list = None):
    """Set custom claims for role-based access control."""
    custom_claims = {
        'role': role,
        'permissions': permissions or [],
        'admin': role == 'admin'
    }

    auth.set_custom_user_claims(uid, custom_claims)
    print(f"Set {role} role for user {uid}")

def get_user_role(uid: str) -> dict:
    """Get user's custom claims."""
    user = auth.get_user(uid)
    return user.custom_claims or {}

# Usage
set_user_role('user_123', 'admin', ['read', 'write', 'delete'])
set_user_role('user_456', 'editor', ['read', 'write'])

# Verify in security rules or server-side:
# if decoded_token.get('admin'):
#     # Allow admin actions'''
    },
    {
        "instruction": "Write Python code to list all Firebase users with pagination",
        "output": '''from firebase_admin import auth

def list_all_users(max_results: int = 1000):
    """List all Firebase users with pagination."""
    users = []
    page = auth.list_users()

    while page:
        for user in page.users:
            users.append({
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'disabled': user.disabled,
                'email_verified': user.email_verified,
                'created_at': user.user_metadata.creation_timestamp
            })

            if len(users) >= max_results:
                return users

        page = page.get_next_page()

    return users

# Usage
all_users = list_all_users()
print(f"Total users: {len(all_users)}")
for user in all_users[:5]:
    print(f"  - {user['email']} ({user['uid']})")'''
    },
    {
        "instruction": "Write Python code to delete a Firebase user and their associated data",
        "output": '''from firebase_admin import auth, firestore

db = firestore.client()

def delete_user_completely(uid: str):
    """Delete Firebase user and all their associated Firestore data."""
    try:
        # Delete user's Firestore documents
        batch = db.batch()

        # Delete user profile
        batch.delete(db.collection('users').document(uid))

        # Delete user's posts
        posts = db.collection('posts').where('author_id', '==', uid).stream()
        for post in posts:
            batch.delete(post.reference)

        # Delete user's comments
        comments = db.collection_group('comments').where('author_id', '==', uid).stream()
        for comment in comments:
            batch.delete(comment.reference)

        batch.commit()
        print(f"Deleted Firestore data for user {uid}")

        # Delete Firebase Auth user
        auth.delete_user(uid)
        print(f"Deleted Firebase Auth user {uid}")

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Usage
result = delete_user_completely('user_123')'''
    },
    {
        "instruction": "Write Python code to generate a custom Firebase token for service-to-service authentication",
        "output": '''from firebase_admin import auth

def create_custom_token(uid: str, additional_claims: dict = None) -> str:
    """Create a custom token for a user with optional claims."""
    custom_token = auth.create_custom_token(uid, additional_claims)
    return custom_token.decode('utf-8')

# Usage for service accounts or special auth flows
token = create_custom_token('service_account_123', {
    'service': True,
    'permissions': ['read_all', 'write_logs']
})
print(f"Custom token: {token}")

# Client can use this token to sign in:
# firebase.auth().signInWithCustomToken(token)'''
    },
]

# =============================================================================
# JAVASCRIPT/TYPESCRIPT - FIRESTORE CLIENT SDK
# =============================================================================

JS_FIRESTORE_CRUD = [
    {
        "instruction": "Write JavaScript code to initialize Firebase and Firestore in a web application",
        "output": '''import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project",
  storageBucket: "your-project.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
const db = getFirestore(app);

export { db };'''
    },
    {
        "instruction": "Write TypeScript code to add a document to Firestore with type safety",
        "output": '''import { collection, addDoc, serverTimestamp, Timestamp } from 'firebase/firestore';
import { db } from './firebase';

interface User {
  name: string;
  email: string;
  age: number;
  createdAt: Timestamp;
}

async function addUser(userData: Omit<User, 'createdAt'>): Promise<string> {
  try {
    const usersRef = collection(db, 'users');
    const docRef = await addDoc(usersRef, {
      ...userData,
      createdAt: serverTimestamp()
    });

    console.log('User added with ID:', docRef.id);
    return docRef.id;
  } catch (error) {
    console.error('Error adding user:', error);
    throw error;
  }
}

// Usage
await addUser({ name: 'John Doe', email: 'john@example.com', age: 30 });'''
    },
    {
        "instruction": "Write TypeScript code to get a document from Firestore with proper typing",
        "output": '''import { doc, getDoc, DocumentSnapshot } from 'firebase/firestore';
import { db } from './firebase';

interface User {
  id: string;
  name: string;
  email: string;
  age: number;
}

async function getUser(userId: string): Promise<User | null> {
  const docRef = doc(db, 'users', userId);
  const docSnap: DocumentSnapshot = await getDoc(docRef);

  if (docSnap.exists()) {
    return {
      id: docSnap.id,
      ...docSnap.data()
    } as User;
  }

  return null;
}

// Usage
const user = await getUser('user_123');
if (user) {
  console.log(`Found user: ${user.name}`);
} else {
  console.log('User not found');
}'''
    },
    {
        "instruction": "Write JavaScript code to update a Firestore document with merge option",
        "output": '''import { doc, setDoc, updateDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';

// Update with merge (won't overwrite other fields)
async function updateUserProfile(userId, updates) {
  const userRef = doc(db, 'users', userId);

  await setDoc(userRef, {
    ...updates,
    updatedAt: serverTimestamp()
  }, { merge: true });

  console.log('User profile updated');
}

// Or use updateDoc for partial updates
async function updateUserEmail(userId, newEmail) {
  const userRef = doc(db, 'users', userId);

  await updateDoc(userRef, {
    email: newEmail,
    emailVerified: false,
    updatedAt: serverTimestamp()
  });
}

// Usage
await updateUserProfile('user_123', { bio: 'Software developer' });
await updateUserEmail('user_123', 'newemail@example.com');'''
    },
    {
        "instruction": "Write TypeScript code to delete a document and its subcollections in Firestore",
        "output": '''import { doc, deleteDoc, collection, getDocs, writeBatch } from 'firebase/firestore';
import { db } from './firebase';

async function deleteDocumentWithSubcollections(
  collectionPath: string,
  docId: string,
  subcollections: string[]
): Promise<void> {
  const batch = writeBatch(db);
  const docRef = doc(db, collectionPath, docId);

  // Delete all documents in subcollections
  for (const subcol of subcollections) {
    const subcolRef = collection(docRef, subcol);
    const snapshot = await getDocs(subcolRef);

    snapshot.docs.forEach((subDoc) => {
      batch.delete(subDoc.ref);
    });
  }

  // Delete the parent document
  batch.delete(docRef);

  await batch.commit();
  console.log(`Deleted document ${docId} and its subcollections`);
}

// Usage
await deleteDocumentWithSubcollections('posts', 'post_123', ['comments', 'likes']);'''
    },
    {
        "instruction": "Write JavaScript code to use Firestore arrayUnion and arrayRemove",
        "output": '''import { doc, updateDoc, arrayUnion, arrayRemove } from 'firebase/firestore';
import { db } from './firebase';

// Add items to an array (won't add duplicates)
async function addTagsToPost(postId, newTags) {
  const postRef = doc(db, 'posts', postId);

  await updateDoc(postRef, {
    tags: arrayUnion(...newTags)
  });

  console.log('Tags added to post');
}

// Remove items from an array
async function removeTagFromPost(postId, tagToRemove) {
  const postRef = doc(db, 'posts', postId);

  await updateDoc(postRef, {
    tags: arrayRemove(tagToRemove)
  });

  console.log('Tag removed from post');
}

// Add user to followers array
async function followUser(userId, followerId) {
  const userRef = doc(db, 'users', userId);

  await updateDoc(userRef, {
    followers: arrayUnion(followerId),
    followerCount: increment(1)
  });
}

// Usage
await addTagsToPost('post_123', ['javascript', 'firebase']);
await removeTagFromPost('post_123', 'outdated');'''
    },
]

JS_FIRESTORE_QUERIES = [
    {
        "instruction": "Write TypeScript code to query Firestore with complex filters and ordering",
        "output": '''import {
  collection, query, where, orderBy, limit,
  getDocs, QueryConstraint
} from 'firebase/firestore';
import { db } from './firebase';

interface Post {
  id: string;
  title: string;
  authorId: string;
  published: boolean;
  createdAt: Date;
  tags: string[];
}

async function getPublishedPosts(
  authorId?: string,
  tag?: string,
  maxResults: number = 10
): Promise<Post[]> {
  const postsRef = collection(db, 'posts');
  const constraints: QueryConstraint[] = [
    where('published', '==', true),
    orderBy('createdAt', 'desc'),
    limit(maxResults)
  ];

  if (authorId) {
    constraints.push(where('authorId', '==', authorId));
  }

  if (tag) {
    constraints.push(where('tags', 'array-contains', tag));
  }

  const q = query(postsRef, ...constraints);
  const snapshot = await getDocs(q);

  return snapshot.docs.map(doc => ({
    id: doc.id,
    ...doc.data()
  } as Post));
}

// Usage
const recentPosts = await getPublishedPosts();
const userPosts = await getPublishedPosts('user_123');
const pythonPosts = await getPublishedPosts(undefined, 'python');'''
    },
    {
        "instruction": "Write TypeScript code for Firestore cursor-based pagination",
        "output": '''import {
  collection, query, orderBy, limit, startAfter,
  getDocs, QueryDocumentSnapshot, DocumentData
} from 'firebase/firestore';
import { db } from './firebase';

interface PaginatedResult<T> {
  items: T[];
  lastDoc: QueryDocumentSnapshot<DocumentData> | null;
  hasMore: boolean;
}

async function getPaginatedUsers(
  pageSize: number = 20,
  lastDoc?: QueryDocumentSnapshot<DocumentData>
): Promise<PaginatedResult<User>> {
  const usersRef = collection(db, 'users');

  let q = query(
    usersRef,
    orderBy('createdAt', 'desc'),
    limit(pageSize + 1) // Fetch one extra to check if there's more
  );

  if (lastDoc) {
    q = query(q, startAfter(lastDoc));
  }

  const snapshot = await getDocs(q);
  const docs = snapshot.docs;

  const hasMore = docs.length > pageSize;
  const items = docs.slice(0, pageSize).map(doc => ({
    id: doc.id,
    ...doc.data()
  })) as User[];

  return {
    items,
    lastDoc: docs.length > 0 ? docs[Math.min(docs.length - 1, pageSize - 1)] : null,
    hasMore
  };
}

// Usage with React state
// const [users, setUsers] = useState<User[]>([]);
// const [lastDoc, setLastDoc] = useState<QueryDocumentSnapshot | null>(null);
//
// const loadMore = async () => {
//   const result = await getPaginatedUsers(20, lastDoc);
//   setUsers(prev => [...prev, ...result.items]);
//   setLastDoc(result.lastDoc);
// };'''
    },
    {
        "instruction": "Write JavaScript code to perform a collection group query in Firestore",
        "output": '''import { collectionGroup, query, where, orderBy, getDocs } from 'firebase/firestore';
import { db } from './firebase';

// Query all 'comments' subcollections across all posts
async function getUserCommentsAcrossAllPosts(userId) {
  const commentsQuery = query(
    collectionGroup(db, 'comments'),
    where('authorId', '==', userId),
    orderBy('createdAt', 'desc')
  );

  const snapshot = await getDocs(commentsQuery);

  return snapshot.docs.map(doc => ({
    id: doc.id,
    postId: doc.ref.parent.parent?.id, // Get parent post ID
    ...doc.data()
  }));
}

// Find all reviews with 5 stars across all products
async function getFiveStarReviews() {
  const reviewsQuery = query(
    collectionGroup(db, 'reviews'),
    where('rating', '==', 5),
    orderBy('createdAt', 'desc')
  );

  const snapshot = await getDocs(reviewsQuery);
  return snapshot.docs.map(doc => ({
    id: doc.id,
    productId: doc.ref.parent.parent?.id,
    ...doc.data()
  }));
}

// Note: Collection group queries require a composite index in Firestore'''
    },
]

JS_FIRESTORE_REALTIME = [
    {
        "instruction": "Write TypeScript code to listen for real-time updates on a Firestore document with React hooks",
        "output": '''import { useState, useEffect } from 'react';
import { doc, onSnapshot, DocumentData } from 'firebase/firestore';
import { db } from './firebase';

interface User {
  id: string;
  name: string;
  email: string;
  online: boolean;
}

function useDocument<T>(collectionName: string, docId: string): {
  data: T | null;
  loading: boolean;
  error: Error | null;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const docRef = doc(db, collectionName, docId);

    const unsubscribe = onSnapshot(
      docRef,
      (snapshot) => {
        if (snapshot.exists()) {
          setData({ id: snapshot.id, ...snapshot.data() } as T);
        } else {
          setData(null);
        }
        setLoading(false);
      },
      (err) => {
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, [collectionName, docId]);

  return { data, loading, error };
}

// Usage in component
function UserProfile({ userId }: { userId: string }) {
  const { data: user, loading, error } = useDocument<User>('users', userId);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!user) return <div>User not found</div>;

  return <div>{user.name} - {user.online ? 'Online' : 'Offline'}</div>;
}'''
    },
    {
        "instruction": "Write TypeScript code to listen for real-time updates on a Firestore collection query",
        "output": '''import { useState, useEffect } from 'react';
import {
  collection, query, where, orderBy, limit,
  onSnapshot, QueryConstraint
} from 'firebase/firestore';
import { db } from './firebase';

interface Message {
  id: string;
  text: string;
  senderId: string;
  createdAt: Date;
}

function useChatMessages(chatId: string, messageLimit: number = 50) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const messagesRef = collection(db, 'chats', chatId, 'messages');
    const q = query(
      messagesRef,
      orderBy('createdAt', 'desc'),
      limit(messageLimit)
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const newMessages: Message[] = [];

      snapshot.docChanges().forEach((change) => {
        if (change.type === 'added') {
          console.log('New message:', change.doc.data());
        }
      });

      snapshot.docs.forEach((doc) => {
        newMessages.push({
          id: doc.id,
          ...doc.data()
        } as Message);
      });

      setMessages(newMessages.reverse()); // Oldest first
      setLoading(false);
    });

    return () => unsubscribe();
  }, [chatId, messageLimit]);

  return { messages, loading };
}

// Usage
function ChatRoom({ chatId }: { chatId: string }) {
  const { messages, loading } = useChatMessages(chatId);

  return (
    <div>
      {messages.map(msg => (
        <div key={msg.id}>{msg.text}</div>
      ))}
    </div>
  );
}'''
    },
    {
        "instruction": "Write JavaScript code to implement presence detection with Firestore and Realtime Database",
        "output": '''import { getDatabase, ref, onDisconnect, set, serverTimestamp as rtdbTimestamp } from 'firebase/database';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { db } from './firebase';

const rtdb = getDatabase();
const auth = getAuth();

function setupPresence() {
  onAuthStateChanged(auth, (user) => {
    if (!user) return;

    const uid = user.uid;

    // Realtime Database presence
    const userStatusRef = ref(rtdb, `/status/${uid}`);
    const firestoreUserRef = doc(db, 'users', uid);

    // When user disconnects, update status
    onDisconnect(userStatusRef).set({
      state: 'offline',
      lastSeen: rtdbTimestamp()
    });

    // Set user as online
    set(userStatusRef, {
      state: 'online',
      lastSeen: rtdbTimestamp()
    });

    // Also update Firestore for querying online users
    setDoc(firestoreUserRef, {
      online: true,
      lastSeen: serverTimestamp()
    }, { merge: true });

    // Listen for RTDB changes and sync to Firestore
    // This creates a bridge between RTDB presence and Firestore
  });
}

// Call on app initialization
setupPresence();'''
    },
]

JS_FIRESTORE_TRANSACTIONS = [
    {
        "instruction": "Write TypeScript code to perform a Firestore transaction for liking a post",
        "output": '''import { doc, runTransaction, increment } from 'firebase/firestore';
import { db } from './firebase';

async function likePost(postId: string, userId: string): Promise<boolean> {
  const postRef = doc(db, 'posts', postId);
  const likeRef = doc(db, 'posts', postId, 'likes', userId);

  try {
    await runTransaction(db, async (transaction) => {
      const likeDoc = await transaction.get(likeRef);

      if (likeDoc.exists()) {
        throw new Error('Already liked');
      }

      // Add like document
      transaction.set(likeRef, {
        userId,
        createdAt: new Date()
      });

      // Increment like count
      transaction.update(postRef, {
        likeCount: increment(1)
      });
    });

    console.log('Post liked successfully');
    return true;
  } catch (error) {
    if (error.message === 'Already liked') {
      console.log('User already liked this post');
      return false;
    }
    throw error;
  }
}

async function unlikePost(postId: string, userId: string): Promise<void> {
  const postRef = doc(db, 'posts', postId);
  const likeRef = doc(db, 'posts', postId, 'likes', userId);

  await runTransaction(db, async (transaction) => {
    const likeDoc = await transaction.get(likeRef);

    if (!likeDoc.exists()) {
      throw new Error('Not liked');
    }

    transaction.delete(likeRef);
    transaction.update(postRef, {
      likeCount: increment(-1)
    });
  });
}'''
    },
    {
        "instruction": "Write TypeScript code for batch writes in Firestore",
        "output": '''import { writeBatch, doc, collection, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';

interface BatchOperation {
  type: 'set' | 'update' | 'delete';
  collection: string;
  docId: string;
  data?: Record<string, any>;
}

async function executeBatchOperations(operations: BatchOperation[]): Promise<void> {
  // Firestore batch limit is 500 operations
  const BATCH_LIMIT = 500;

  for (let i = 0; i < operations.length; i += BATCH_LIMIT) {
    const batch = writeBatch(db);
    const chunk = operations.slice(i, i + BATCH_LIMIT);

    for (const op of chunk) {
      const docRef = doc(db, op.collection, op.docId);

      switch (op.type) {
        case 'set':
          batch.set(docRef, { ...op.data, updatedAt: serverTimestamp() });
          break;
        case 'update':
          batch.update(docRef, { ...op.data, updatedAt: serverTimestamp() });
          break;
        case 'delete':
          batch.delete(docRef);
          break;
      }
    }

    await batch.commit();
    console.log(`Committed batch ${Math.floor(i / BATCH_LIMIT) + 1}`);
  }
}

// Usage: Archive old posts
async function archiveOldPosts(postIds: string[]) {
  const operations: BatchOperation[] = postIds.map(id => ({
    type: 'update',
    collection: 'posts',
    docId: id,
    data: { archived: true, archivedAt: new Date() }
  }));

  await executeBatchOperations(operations);
}'''
    },
]

# =============================================================================
# FIREBASE SECURITY RULES
# =============================================================================

FIREBASE_SECURITY_RULES = [
    {
        "instruction": "Write Firestore security rules for a basic user profile system",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users collection
    match /users/{userId} {
      // Anyone can read user profiles
      allow read: if true;

      // Users can only create/update their own profile
      allow create: if request.auth != null && request.auth.uid == userId;
      allow update: if request.auth != null && request.auth.uid == userId;

      // Only admins can delete users
      allow delete: if request.auth != null &&
                       request.auth.token.admin == true;
    }
  }
}'''
    },
    {
        "instruction": "Write Firestore security rules for a blog with posts and comments",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Helper function to check if user is authenticated
    function isAuthenticated() {
      return request.auth != null;
    }

    // Helper function to check if user owns the resource
    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    // Helper function to check if user is admin
    function isAdmin() {
      return isAuthenticated() && request.auth.token.admin == true;
    }

    // Posts collection
    match /posts/{postId} {
      // Anyone can read published posts
      allow read: if resource.data.published == true || isOwner(resource.data.authorId);

      // Authenticated users can create posts
      allow create: if isAuthenticated() &&
                       request.resource.data.authorId == request.auth.uid;

      // Authors can update their own posts
      allow update: if isOwner(resource.data.authorId) || isAdmin();

      // Authors and admins can delete
      allow delete: if isOwner(resource.data.authorId) || isAdmin();

      // Comments subcollection
      match /comments/{commentId} {
        allow read: if true;
        allow create: if isAuthenticated();
        allow update: if isOwner(resource.data.authorId);
        allow delete: if isOwner(resource.data.authorId) || isAdmin();
      }
    }
  }
}'''
    },
    {
        "instruction": "Write Firestore security rules with data validation",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function isAuthenticated() {
      return request.auth != null;
    }

    // Validate string length
    function isValidString(field, minLen, maxLen) {
      return field is string &&
             field.size() >= minLen &&
             field.size() <= maxLen;
    }

    // Validate email format (basic)
    function isValidEmail(email) {
      return email.matches('^[^@]+@[^@]+\\.[^@]+$');
    }

    match /products/{productId} {
      // Validate product data structure
      function isValidProduct() {
        let data = request.resource.data;
        return data.keys().hasAll(['name', 'price', 'category']) &&
               isValidString(data.name, 1, 100) &&
               data.price is number &&
               data.price > 0 &&
               data.price < 1000000 &&
               data.category in ['electronics', 'clothing', 'books', 'other'];
      }

      allow read: if true;
      allow create: if isAuthenticated() && isValidProduct();
      allow update: if isAuthenticated() && isValidProduct();
      allow delete: if isAuthenticated() &&
                       request.auth.token.admin == true;
    }

    match /orders/{orderId} {
      function isValidOrder() {
        let data = request.resource.data;
        return data.keys().hasAll(['userId', 'items', 'total']) &&
               data.userId == request.auth.uid &&
               data.items is list &&
               data.items.size() > 0 &&
               data.items.size() <= 100 &&
               data.total is number &&
               data.total > 0;
      }

      allow read: if isAuthenticated() &&
                     resource.data.userId == request.auth.uid;
      allow create: if isAuthenticated() && isValidOrder();
      allow update: if false; // Orders cannot be modified
      allow delete: if false; // Orders cannot be deleted
    }
  }
}'''
    },
    {
        "instruction": "Write Firestore security rules for a multi-tenant application",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function isAuthenticated() {
      return request.auth != null;
    }

    function getUserOrg() {
      return get(/databases/$(database)/documents/users/$(request.auth.uid)).data.organizationId;
    }

    function belongsToOrg(orgId) {
      return isAuthenticated() && getUserOrg() == orgId;
    }

    function hasOrgRole(orgId, role) {
      let membership = get(/databases/$(database)/documents/organizations/$(orgId)/members/$(request.auth.uid));
      return membership.exists && membership.data.role == role;
    }

    // Organizations
    match /organizations/{orgId} {
      allow read: if belongsToOrg(orgId);
      allow create: if isAuthenticated();
      allow update: if hasOrgRole(orgId, 'admin');
      allow delete: if hasOrgRole(orgId, 'owner');

      // Organization members
      match /members/{memberId} {
        allow read: if belongsToOrg(orgId);
        allow write: if hasOrgRole(orgId, 'admin');
      }

      // Organization projects
      match /projects/{projectId} {
        allow read: if belongsToOrg(orgId);
        allow create: if belongsToOrg(orgId);
        allow update: if belongsToOrg(orgId) &&
                         (resource.data.createdBy == request.auth.uid ||
                          hasOrgRole(orgId, 'admin'));
        allow delete: if hasOrgRole(orgId, 'admin');
      }
    }
  }
}'''
    },
]

# =============================================================================
# CLOUD FUNCTIONS
# =============================================================================

CLOUD_FUNCTIONS = [
    {
        "instruction": "Write a Firebase Cloud Function that triggers on Firestore document creation",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

export const onUserCreated = functions.firestore
  .document('users/{userId}')
  .onCreate(async (snapshot, context) => {
    const userId = context.params.userId;
    const userData = snapshot.data();

    console.log(`New user created: ${userId}`);

    // Send welcome email
    await db.collection('mail').add({
      to: userData.email,
      template: {
        name: 'welcome',
        data: {
          userName: userData.displayName || 'there'
        }
      }
    });

    // Create default user settings
    await db.collection('userSettings').doc(userId).set({
      notifications: true,
      theme: 'light',
      language: 'en',
      createdAt: admin.firestore.FieldValue.serverTimestamp()
    });

    // Increment user count in stats
    await db.collection('stats').doc('users').update({
      totalCount: admin.firestore.FieldValue.increment(1)
    });

    return null;
  });'''
    },
    {
        "instruction": "Write a Firebase Cloud Function that triggers on Firestore document update",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

export const onOrderStatusChanged = functions.firestore
  .document('orders/{orderId}')
  .onUpdate(async (change, context) => {
    const orderId = context.params.orderId;
    const beforeData = change.before.data();
    const afterData = change.after.data();

    // Check if status changed
    if (beforeData.status === afterData.status) {
      return null;
    }

    console.log(`Order ${orderId} status: ${beforeData.status} -> ${afterData.status}`);

    // Add to status history
    await change.after.ref.update({
      statusHistory: admin.firestore.FieldValue.arrayUnion({
        status: afterData.status,
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
        updatedBy: afterData.lastUpdatedBy || 'system'
      })
    });

    // Send notification based on new status
    const userId = afterData.userId;
    const userDoc = await db.collection('users').doc(userId).get();
    const userEmail = userDoc.data()?.email;

    if (userEmail) {
      await db.collection('mail').add({
        to: userEmail,
        template: {
          name: 'order-status-update',
          data: {
            orderId,
            oldStatus: beforeData.status,
            newStatus: afterData.status
          }
        }
      });
    }

    return null;
  });'''
    },
    {
        "instruction": "Write a Firebase Cloud Function HTTP endpoint with authentication",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

// Verify Firebase ID token middleware
async function verifyAuth(req: functions.https.Request): Promise<admin.auth.DecodedIdToken | null> {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }

  const token = authHeader.split('Bearer ')[1];

  try {
    return await admin.auth().verifyIdToken(token);
  } catch (error) {
    console.error('Token verification failed:', error);
    return null;
  }
}

export const createProject = functions.https.onRequest(async (req, res) => {
  // Enable CORS
  res.set('Access-Control-Allow-Origin', '*');

  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.status(204).send('');
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  // Verify authentication
  const decodedToken = await verifyAuth(req);
  if (!decodedToken) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }

  try {
    const { name, description } = req.body;

    if (!name) {
      res.status(400).json({ error: 'Name is required' });
      return;
    }

    const projectRef = await db.collection('projects').add({
      name,
      description: description || '',
      ownerId: decodedToken.uid,
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
      members: [decodedToken.uid]
    });

    res.status(201).json({
      success: true,
      projectId: projectRef.id
    });
  } catch (error) {
    console.error('Error creating project:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});'''
    },
    {
        "instruction": "Write a Firebase Cloud Function that runs on a schedule (cron job)",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

// Run every day at midnight UTC
export const dailyCleanup = functions.pubsub
  .schedule('0 0 * * *')
  .timeZone('UTC')
  .onRun(async (context) => {
    console.log('Starting daily cleanup...');

    const now = admin.firestore.Timestamp.now();
    const thirtyDaysAgo = new Date(now.toDate().getTime() - 30 * 24 * 60 * 60 * 1000);

    // Delete old unverified users
    const unverifiedUsers = await db.collection('users')
      .where('emailVerified', '==', false)
      .where('createdAt', '<', thirtyDaysAgo)
      .get();

    const batch = db.batch();
    let deleteCount = 0;

    for (const doc of unverifiedUsers.docs) {
      batch.delete(doc.ref);
      deleteCount++;

      // Commit batch every 500 operations
      if (deleteCount % 500 === 0) {
        await batch.commit();
      }
    }

    if (deleteCount % 500 !== 0) {
      await batch.commit();
    }

    console.log(`Deleted ${deleteCount} unverified users`);

    // Archive old notifications
    const oldNotifications = await db.collection('notifications')
      .where('read', '==', true)
      .where('createdAt', '<', thirtyDaysAgo)
      .get();

    for (const doc of oldNotifications.docs) {
      await db.collection('archivedNotifications').doc(doc.id).set(doc.data());
      await doc.ref.delete();
    }

    console.log(`Archived ${oldNotifications.size} old notifications`);

    return null;
  });

// Run every hour to check for expired sessions
export const hourlySessionCheck = functions.pubsub
  .schedule('0 * * * *')
  .onRun(async (context) => {
    const now = admin.firestore.Timestamp.now();

    const expiredSessions = await db.collection('sessions')
      .where('expiresAt', '<', now)
      .get();

    const batch = db.batch();
    expiredSessions.docs.forEach(doc => batch.delete(doc.ref));
    await batch.commit();

    console.log(`Cleaned up ${expiredSessions.size} expired sessions`);
    return null;
  });'''
    },
    {
        "instruction": "Write a Firebase Cloud Function for image processing with Cloud Storage",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';
import sharp from 'sharp';

admin.initializeApp();
const db = admin.firestore();
const storage = admin.storage();

export const processUploadedImage = functions.storage
  .object()
  .onFinalize(async (object) => {
    const filePath = object.name;
    const contentType = object.contentType;

    // Only process images
    if (!contentType?.startsWith('image/')) {
      console.log('Not an image, skipping');
      return null;
    }

    // Skip if already processed (has 'thumb_' prefix)
    const fileName = path.basename(filePath!);
    if (fileName.startsWith('thumb_')) {
      console.log('Already a thumbnail, skipping');
      return null;
    }

    const bucket = storage.bucket(object.bucket);
    const tempFilePath = path.join(os.tmpdir(), fileName);
    const thumbFileName = `thumb_${fileName}`;
    const thumbFilePath = path.join(path.dirname(filePath!), thumbFileName);
    const tempThumbPath = path.join(os.tmpdir(), thumbFileName);

    try {
      // Download original image
      await bucket.file(filePath!).download({ destination: tempFilePath });

      // Generate thumbnail
      await sharp(tempFilePath)
        .resize(200, 200, { fit: 'cover' })
        .jpeg({ quality: 80 })
        .toFile(tempThumbPath);

      // Upload thumbnail
      await bucket.upload(tempThumbPath, {
        destination: thumbFilePath,
        metadata: {
          contentType: 'image/jpeg',
          metadata: {
            originalFile: filePath
          }
        }
      });

      // Get public URLs
      const [originalUrl] = await bucket.file(filePath!).getSignedUrl({
        action: 'read',
        expires: '01-01-2100'
      });

      const [thumbUrl] = await bucket.file(thumbFilePath).getSignedUrl({
        action: 'read',
        expires: '01-01-2100'
      });

      // Update Firestore with image URLs
      // Assuming file path is like: users/{userId}/images/{imageId}
      const pathParts = filePath!.split('/');
      if (pathParts[0] === 'users' && pathParts[2] === 'images') {
        const userId = pathParts[1];
        await db.collection('users').doc(userId).collection('images').add({
          originalUrl,
          thumbnailUrl: thumbUrl,
          fileName,
          uploadedAt: admin.firestore.FieldValue.serverTimestamp()
        });
      }

      // Cleanup temp files
      fs.unlinkSync(tempFilePath);
      fs.unlinkSync(tempThumbPath);

      console.log(`Processed image: ${filePath}`);
      return null;
    } catch (error) {
      console.error('Error processing image:', error);
      throw error;
    }
  });'''
    },
]

# =============================================================================
# FIREBASE AUTHENTICATION (Client-side JavaScript)
# =============================================================================

JS_FIREBASE_AUTH = [
    {
        "instruction": "Write TypeScript code to implement Firebase email/password authentication with React",
        "output": '''import { useState } from 'react';
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  sendEmailVerification,
  User
} from 'firebase/auth';

const auth = getAuth();

interface AuthError {
  code: string;
  message: string;
}

// Sign up with email/password
async function signUp(email: string, password: string): Promise<User> {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);

    // Send verification email
    await sendEmailVerification(userCredential.user);

    return userCredential.user;
  } catch (error) {
    const authError = error as AuthError;
    switch (authError.code) {
      case 'auth/email-already-in-use':
        throw new Error('Email already registered');
      case 'auth/weak-password':
        throw new Error('Password should be at least 6 characters');
      case 'auth/invalid-email':
        throw new Error('Invalid email address');
      default:
        throw new Error('Failed to create account');
    }
  }
}

// Sign in with email/password
async function signIn(email: string, password: string): Promise<User> {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error) {
    const authError = error as AuthError;
    switch (authError.code) {
      case 'auth/user-not-found':
      case 'auth/wrong-password':
        throw new Error('Invalid email or password');
      case 'auth/too-many-requests':
        throw new Error('Too many attempts. Try again later.');
      default:
        throw new Error('Failed to sign in');
    }
  }
}

// Sign out
async function logOut(): Promise<void> {
  await signOut(auth);
}

// Password reset
async function resetPassword(email: string): Promise<void> {
  await sendPasswordResetEmail(auth, email);
}

// React hook for auth state
function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  return { user, loading, signUp, signIn, logOut, resetPassword };
}'''
    },
    {
        "instruction": "Write JavaScript code to implement Google Sign-In with Firebase",
        "output": '''import {
  getAuth,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  GoogleAuthProvider
} from 'firebase/auth';

const auth = getAuth();
const googleProvider = new GoogleAuthProvider();

// Add scopes for additional permissions
googleProvider.addScope('https://www.googleapis.com/auth/userinfo.email');
googleProvider.addScope('https://www.googleapis.com/auth/userinfo.profile');

// Force account selection
googleProvider.setCustomParameters({
  prompt: 'select_account'
});

// Sign in with popup (desktop)
async function signInWithGoogle() {
  try {
    const result = await signInWithPopup(auth, googleProvider);

    // Get Google access token
    const credential = GoogleAuthProvider.credentialFromResult(result);
    const token = credential?.accessToken;

    const user = result.user;
    console.log('Signed in as:', user.displayName);
    console.log('Email:', user.email);
    console.log('Photo URL:', user.photoURL);

    return user;
  } catch (error) {
    if (error.code === 'auth/popup-closed-by-user') {
      console.log('Sign-in cancelled');
      return null;
    }
    throw error;
  }
}

// Sign in with redirect (mobile-friendly)
async function signInWithGoogleRedirect() {
  await signInWithRedirect(auth, googleProvider);
}

// Handle redirect result (call on page load)
async function handleRedirectResult() {
  try {
    const result = await getRedirectResult(auth);
    if (result) {
      const user = result.user;
      console.log('Redirect sign-in successful:', user.email);
      return user;
    }
    return null;
  } catch (error) {
    console.error('Redirect sign-in error:', error);
    throw error;
  }
}

// Usage
// Desktop: await signInWithGoogle();
// Mobile: signInWithGoogleRedirect();
// On page load: await handleRedirectResult();'''
    },
    {
        "instruction": "Write TypeScript code for a protected route component with Firebase Auth in React",
        "output": '''import { useEffect, useState } from 'react';
import { getAuth, onAuthStateChanged, User } from 'firebase/auth';
import { Navigate, useLocation } from 'react-router-dom';

interface AuthContextType {
  user: User | null;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({ user: null, loading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const auth = getAuth();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      setLoading(false);
    });

    return unsubscribe;
  }, [auth]);

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

// Protected Route component
interface ProtectedRouteProps {
  children: React.ReactNode;
  requireEmailVerified?: boolean;
}

export function ProtectedRoute({ children, requireEmailVerified = false }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireEmailVerified && !user.emailVerified) {
    return <Navigate to="/verify-email" replace />;
  }

  return <>{children}</>;
}

// Usage in App.tsx
// <Routes>
//   <Route path="/login" element={<LoginPage />} />
//   <Route path="/dashboard" element={
//     <ProtectedRoute>
//       <DashboardPage />
//     </ProtectedRoute>
//   } />
// </Routes>'''
    },
]

# =============================================================================
# COMBINE ALL EXAMPLES
# =============================================================================

def create_training_examples():
    """Combine all examples into training format."""
    all_examples = []

    categories = [
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
    ]

    for category_name, examples in categories:
        for example in examples:
            # Format for Qwen chat template
            formatted = {
                "messages": [
                    {"role": "system", "content": "You are an expert Firebase and Firestore developer. Write clean, efficient, and well-documented code."},
                    {"role": "user", "content": example["instruction"]},
                    {"role": "assistant", "content": example["output"]}
                ]
            }
            all_examples.append(formatted)

    return all_examples


def main():
    # Create output directory
    output_dir = Path("/Users/fredtaylor/Development/Projects/AITeamPlatform/mlx-training/data/firebase")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate examples
    examples = create_training_examples()

    print(f"Generated {len(examples)} synthetic Firebase/Firestore examples")

    # Split into train/valid (90/10)
    random.shuffle(examples)
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

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

    # Print category breakdown
    print("\nCategory breakdown:")
    categories = [
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
    ]
    for name, examples in categories:
        print(f"  {name}: {len(examples)}")


if __name__ == "__main__":
    main()
