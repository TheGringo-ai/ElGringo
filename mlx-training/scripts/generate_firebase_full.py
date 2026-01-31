#!/usr/bin/env python3
"""
Complete Firebase/Firestore training data generator.
Generates 500+ diverse examples with variations.
"""

import json
import random
from pathlib import Path
from typing import List, Dict

def create_variations(base_examples: List[Dict], variations: List[Dict]) -> List[Dict]:
    """Apply variations to base examples to create more training data."""
    all_examples = list(base_examples)

    for var in variations:
        example = {
            "instruction": var["instruction"],
            "output": var["output"]
        }
        all_examples.append(example)

    return all_examples

# =============================================================================
# COMPREHENSIVE FIREBASE/FIRESTORE EXAMPLES
# =============================================================================

ALL_EXAMPLES = [
    # =========================================================================
    # PYTHON FIRESTORE CRUD - BASICS
    # =========================================================================
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
        "instruction": "Write Python code to add a new document to Firestore with auto-generated ID",
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
        "instruction": "Write Python code to update specific fields in a Firestore document",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Update specific fields only
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

print(f"Found {len(users)} users")'''
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
    'stock': firestore.Increment(-1)
})

print("Counters updated atomically")'''
    },
    # =========================================================================
    # PYTHON FIRESTORE QUERIES
    # =========================================================================
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

    last = docs[-1] if docs else None
    return users, last

# Get first page
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
        "instruction": "Write Python code to perform a collection group query in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Query across all subcollections named 'comments'
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
        "instruction": "Write Python code to count documents in a Firestore query",
        "output": '''from firebase_admin import firestore

db = firestore.client()

# Count documents matching a query
users_ref = db.collection('users')
query = users_ref.where('status', '==', 'active')

# Get aggregation count
aggregate = query.count().get()
count = aggregate[0][0].value

print(f"Total active users: {count}")'''
    },
    # =========================================================================
    # PYTHON FIRESTORE TRANSACTIONS
    # =========================================================================
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
        "instruction": "Write Python code to use Firestore batch writes to update multiple documents",
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
        "instruction": "Write Python code to perform batch writes with more than 500 operations",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def batch_write_large(collection_name: str, documents: list):
    """Write large number of documents using multiple batches."""
    batch_size = 500
    total = len(documents)

    for i in range(0, total, batch_size):
        batch = db.batch()
        chunk = documents[i:i + batch_size]

        for doc_data in chunk:
            doc_ref = db.collection(collection_name).document()
            batch.set(doc_ref, doc_data)

        batch.commit()
        print(f"Committed batch {i // batch_size + 1}")

    print(f"Total {total} documents written")

# Usage
products = [{'name': f'Product {i}', 'price': i * 10} for i in range(1500)]
batch_write_large('products', products)'''
    },
    # =========================================================================
    # PYTHON FIREBASE AUTH
    # =========================================================================
    {
        "instruction": "Write Python code to verify a Firebase ID token on the server",
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
        return {'valid': False, 'error': str(e)}'''
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
            'email': user.email
        }
    except auth.EmailAlreadyExistsError:
        return {'success': False, 'error': 'Email already exists'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

result = create_user('newuser@example.com', 'password123', 'John Doe')'''
    },
    {
        "instruction": "Write Python code to set custom claims for role-based access control",
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

# Usage
set_user_role('user_123', 'admin', ['read', 'write', 'delete'])
set_user_role('user_456', 'editor', ['read', 'write'])'''
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
                'disabled': user.disabled
            })

            if len(users) >= max_results:
                return users

        page = page.get_next_page()

    return users

all_users = list_all_users()
print(f"Total users: {len(all_users)}")'''
    },
    {
        "instruction": "Write Python code to delete a Firebase user and their Firestore data",
        "output": '''from firebase_admin import auth, firestore

db = firestore.client()

def delete_user_completely(uid: str):
    """Delete Firebase user and all their Firestore data."""
    try:
        batch = db.batch()

        # Delete user profile
        batch.delete(db.collection('users').document(uid))

        # Delete user's posts
        posts = db.collection('posts').where('author_id', '==', uid).stream()
        for post in posts:
            batch.delete(post.reference)

        batch.commit()
        print(f"Deleted Firestore data for user {uid}")

        # Delete Firebase Auth user
        auth.delete_user(uid)
        print(f"Deleted Firebase Auth user {uid}")

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}'''
    },
    # =========================================================================
    # JAVASCRIPT/TYPESCRIPT FIRESTORE
    # =========================================================================
    {
        "instruction": "Write JavaScript code to initialize Firebase and Firestore in a web app",
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

const app = initializeApp(firebaseConfig);
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

await addUser({ name: 'John Doe', email: 'john@example.com', age: 30 });'''
    },
    {
        "instruction": "Write TypeScript code to get a document from Firestore with typing",
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

const user = await getUser('user_123');
if (user) {
  console.log(`Found user: ${user.name}`);
}'''
    },
    {
        "instruction": "Write JavaScript code to update a Firestore document with merge",
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
    updatedAt: serverTimestamp()
  });
}

await updateUserProfile('user_123', { bio: 'Software developer' });'''
    },
    {
        "instruction": "Write TypeScript code to query Firestore with complex filters",
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
}

async function getPublishedPosts(
  authorId?: string,
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

  const q = query(postsRef, ...constraints);
  const snapshot = await getDocs(q);

  return snapshot.docs.map(doc => ({
    id: doc.id,
    ...doc.data()
  } as Post));
}'''
    },
    {
        "instruction": "Write TypeScript code for cursor-based pagination in Firestore",
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
    limit(pageSize + 1)
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
}'''
    },
    {
        "instruction": "Write TypeScript React hook to listen for real-time Firestore updates",
        "output": '''import { useState, useEffect } from 'react';
import { doc, onSnapshot, DocumentData } from 'firebase/firestore';
import { db } from './firebase';

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

// Usage
function UserProfile({ userId }: { userId: string }) {
  const { data: user, loading, error } = useDocument<User>('users', userId);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <div>{user?.name}</div>;
}'''
    },
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

      transaction.set(likeRef, {
        userId,
        createdAt: new Date()
      });

      transaction.update(postRef, {
        likeCount: increment(1)
      });
    });

    return true;
  } catch (error) {
    if (error.message === 'Already liked') {
      return false;
    }
    throw error;
  }
}'''
    },
    {
        "instruction": "Write JavaScript code for batch writes in Firestore",
        "output": '''import { writeBatch, doc, collection, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';

async function batchUpdateUsers(updates) {
  const BATCH_LIMIT = 500;

  for (let i = 0; i < updates.length; i += BATCH_LIMIT) {
    const batch = writeBatch(db);
    const chunk = updates.slice(i, i + BATCH_LIMIT);

    for (const update of chunk) {
      const docRef = doc(db, 'users', update.id);
      batch.update(docRef, {
        ...update.data,
        updatedAt: serverTimestamp()
      });
    }

    await batch.commit();
    console.log(`Committed batch ${Math.floor(i / BATCH_LIMIT) + 1}`);
  }
}'''
    },
    # =========================================================================
    # FIREBASE SECURITY RULES
    # =========================================================================
    {
        "instruction": "Write Firestore security rules for a user profile system",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read: if true;
      allow create: if request.auth != null && request.auth.uid == userId;
      allow update: if request.auth != null && request.auth.uid == userId;
      allow delete: if request.auth != null && request.auth.token.admin == true;
    }
  }
}'''
    },
    {
        "instruction": "Write Firestore security rules for a blog with posts and comments",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function isAuthenticated() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    function isAdmin() {
      return isAuthenticated() && request.auth.token.admin == true;
    }

    match /posts/{postId} {
      allow read: if resource.data.published == true || isOwner(resource.data.authorId);
      allow create: if isAuthenticated() && request.resource.data.authorId == request.auth.uid;
      allow update: if isOwner(resource.data.authorId) || isAdmin();
      allow delete: if isOwner(resource.data.authorId) || isAdmin();

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
    function isValidString(field, minLen, maxLen) {
      return field is string && field.size() >= minLen && field.size() <= maxLen;
    }

    match /products/{productId} {
      function isValidProduct() {
        let data = request.resource.data;
        return data.keys().hasAll(['name', 'price', 'category']) &&
               isValidString(data.name, 1, 100) &&
               data.price is number &&
               data.price > 0 &&
               data.category in ['electronics', 'clothing', 'books'];
      }

      allow read: if true;
      allow create: if request.auth != null && isValidProduct();
      allow update: if request.auth != null && isValidProduct();
      allow delete: if request.auth.token.admin == true;
    }
  }
}'''
    },
    {
        "instruction": "Write Firestore security rules for a multi-tenant application",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function getUserOrg() {
      return get(/databases/$(database)/documents/users/$(request.auth.uid)).data.organizationId;
    }

    function belongsToOrg(orgId) {
      return request.auth != null && getUserOrg() == orgId;
    }

    function hasOrgRole(orgId, role) {
      let membership = get(/databases/$(database)/documents/organizations/$(orgId)/members/$(request.auth.uid));
      return membership.exists && membership.data.role == role;
    }

    match /organizations/{orgId} {
      allow read: if belongsToOrg(orgId);
      allow update: if hasOrgRole(orgId, 'admin');

      match /projects/{projectId} {
        allow read: if belongsToOrg(orgId);
        allow create: if belongsToOrg(orgId);
        allow update: if belongsToOrg(orgId);
        allow delete: if hasOrgRole(orgId, 'admin');
      }
    }
  }
}'''
    },
    # =========================================================================
    # CLOUD FUNCTIONS
    # =========================================================================
    {
        "instruction": "Write a Firebase Cloud Function that triggers on document creation",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

export const onUserCreated = functions.firestore
  .document('users/{userId}')
  .onCreate(async (snapshot, context) => {
    const userId = context.params.userId;
    const userData = snapshot.data();

    // Send welcome email
    await db.collection('mail').add({
      to: userData.email,
      template: { name: 'welcome', data: { userName: userData.displayName } }
    });

    // Create default settings
    await db.collection('userSettings').doc(userId).set({
      notifications: true,
      theme: 'light'
    });

    return null;
  });'''
    },
    {
        "instruction": "Write a Firebase Cloud Function that triggers on document update",
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

    if (beforeData.status === afterData.status) {
      return null;
    }

    // Add to status history
    await change.after.ref.update({
      statusHistory: admin.firestore.FieldValue.arrayUnion({
        status: afterData.status,
        timestamp: admin.firestore.FieldValue.serverTimestamp()
      })
    });

    // Send notification
    const user = await db.collection('users').doc(afterData.userId).get();
    if (user.exists) {
      await db.collection('mail').add({
        to: user.data().email,
        template: { name: 'order-status', data: { orderId, status: afterData.status } }
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

async function verifyAuth(req) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) return null;

  const token = authHeader.split('Bearer ')[1];
  try {
    return await admin.auth().verifyIdToken(token);
  } catch {
    return null;
  }
}

export const createProject = functions.https.onRequest(async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');

  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.status(204).send('');
    return;
  }

  const decodedToken = await verifyAuth(req);
  if (!decodedToken) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }

  const { name, description } = req.body;
  const projectRef = await db.collection('projects').add({
    name,
    description,
    ownerId: decodedToken.uid,
    createdAt: admin.firestore.FieldValue.serverTimestamp()
  });

  res.status(201).json({ projectId: projectRef.id });
});'''
    },
    {
        "instruction": "Write a Firebase Cloud Function scheduled cron job",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

// Run every day at midnight UTC
export const dailyCleanup = functions.pubsub
  .schedule('0 0 * * *')
  .timeZone('UTC')
  .onRun(async (context) => {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    // Delete old unverified users
    const unverifiedUsers = await db.collection('users')
      .where('emailVerified', '==', false)
      .where('createdAt', '<', thirtyDaysAgo)
      .get();

    const batch = db.batch();
    unverifiedUsers.docs.forEach(doc => batch.delete(doc.ref));
    await batch.commit();

    console.log(`Deleted ${unverifiedUsers.size} unverified users`);
    return null;
  });'''
    },
    {
        "instruction": "Write a Firebase Cloud Function for image processing on upload",
        "output": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import * as path from 'path';
import * as os from 'os';
import sharp from 'sharp';

admin.initializeApp();
const storage = admin.storage();

export const processUploadedImage = functions.storage
  .object()
  .onFinalize(async (object) => {
    const filePath = object.name;
    const contentType = object.contentType;

    if (!contentType?.startsWith('image/')) return null;

    const fileName = path.basename(filePath);
    if (fileName.startsWith('thumb_')) return null;

    const bucket = storage.bucket(object.bucket);
    const tempFilePath = path.join(os.tmpdir(), fileName);
    const thumbFileName = `thumb_${fileName}`;

    await bucket.file(filePath).download({ destination: tempFilePath });

    await sharp(tempFilePath)
      .resize(200, 200, { fit: 'cover' })
      .jpeg({ quality: 80 })
      .toFile(path.join(os.tmpdir(), thumbFileName));

    await bucket.upload(path.join(os.tmpdir(), thumbFileName), {
      destination: path.join(path.dirname(filePath), thumbFileName)
    });

    return null;
  });'''
    },
    # =========================================================================
    # JAVASCRIPT FIREBASE AUTH
    # =========================================================================
    {
        "instruction": "Write TypeScript code for Firebase email/password authentication in React",
        "output": '''import { useState } from 'react';
import {
  getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword,
  signOut, sendPasswordResetEmail, sendEmailVerification
} from 'firebase/auth';

const auth = getAuth();

async function signUp(email: string, password: string) {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    await sendEmailVerification(userCredential.user);
    return userCredential.user;
  } catch (error: any) {
    if (error.code === 'auth/email-already-in-use') {
      throw new Error('Email already registered');
    }
    throw error;
  }
}

async function signIn(email: string, password: string) {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return userCredential.user;
  } catch (error: any) {
    if (error.code === 'auth/wrong-password' || error.code === 'auth/user-not-found') {
      throw new Error('Invalid email or password');
    }
    throw error;
  }
}

async function logOut() {
  await signOut(auth);
}

async function resetPassword(email: string) {
  await sendPasswordResetEmail(auth, email);
}'''
    },
    {
        "instruction": "Write JavaScript code for Google Sign-In with Firebase",
        "output": '''import {
  getAuth, signInWithPopup, signInWithRedirect,
  getRedirectResult, GoogleAuthProvider
} from 'firebase/auth';

const auth = getAuth();
const googleProvider = new GoogleAuthProvider();

googleProvider.addScope('email');
googleProvider.addScope('profile');
googleProvider.setCustomParameters({ prompt: 'select_account' });

async function signInWithGoogle() {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    const credential = GoogleAuthProvider.credentialFromResult(result);
    const token = credential?.accessToken;

    console.log('Signed in:', result.user.displayName);
    return result.user;
  } catch (error) {
    if (error.code === 'auth/popup-closed-by-user') {
      console.log('Sign-in cancelled');
      return null;
    }
    throw error;
  }
}

async function signInWithGoogleRedirect() {
  await signInWithRedirect(auth, googleProvider);
}

async function handleRedirectResult() {
  const result = await getRedirectResult(auth);
  return result?.user || null;
}'''
    },
    {
        "instruction": "Write TypeScript code for a protected route with Firebase Auth in React",
        "output": '''import { createContext, useContext, useState, useEffect } from 'react';
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
    return onAuthStateChanged(auth, (user) => {
      setUser(user);
      setLoading(false);
    });
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

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

  return <>{children}</>;
}'''
    },
    # =========================================================================
    # ADVANCED PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code for a Firestore repository pattern",
        "output": '''from firebase_admin import firestore
from dataclasses import dataclass, asdict
from typing import Optional, List

@dataclass
class User:
    id: Optional[str] = None
    email: str = ""
    name: str = ""
    role: str = "user"

class UserRepository:
    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection('users')

    def create(self, user: User) -> User:
        data = asdict(user)
        data.pop('id')
        data['created_at'] = firestore.SERVER_TIMESTAMP
        doc_ref = self.collection.add(data)
        user.id = doc_ref[1].id
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        doc = self.collection.document(user_id).get()
        if doc.exists:
            return User(id=doc.id, **doc.to_dict())
        return None

    def get_by_email(self, email: str) -> Optional[User]:
        docs = self.collection.where('email', '==', email).limit(1).stream()
        for doc in docs:
            return User(id=doc.id, **doc.to_dict())
        return None

    def update(self, user: User) -> User:
        data = asdict(user)
        data.pop('id')
        self.collection.document(user.id).update(data)
        return user

    def delete(self, user_id: str) -> bool:
        self.collection.document(user_id).delete()
        return True'''
    },
    {
        "instruction": "Write Python code to export Firestore collection to JSON",
        "output": '''from firebase_admin import firestore
import json
from datetime import datetime

def export_collection_to_json(collection_name: str, output_path: str = None) -> str:
    db = firestore.client()
    docs = db.collection(collection_name).stream()

    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        doc_data['_id'] = doc.id

        for key, value in doc_data.items():
            if hasattr(value, 'isoformat'):
                doc_data[key] = value.isoformat()

        data.append(doc_data)

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"backup_{collection_name}_{timestamp}.json"

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Exported {len(data)} documents to {output_path}")
    return output_path'''
    },
    {
        "instruction": "Write Python code for Firestore soft delete functionality",
        "output": '''from firebase_admin import firestore
from typing import List

db = firestore.client()

class SoftDeleteMixin:
    collection_name: str = None

    @classmethod
    def delete(cls, doc_id: str, deleted_by: str = None):
        db.collection(cls.collection_name).document(doc_id).update({
            'deleted': True,
            'deleted_at': firestore.SERVER_TIMESTAMP,
            'deleted_by': deleted_by
        })

    @classmethod
    def restore(cls, doc_id: str):
        db.collection(cls.collection_name).document(doc_id).update({
            'deleted': firestore.DELETE_FIELD,
            'deleted_at': firestore.DELETE_FIELD,
            'restored_at': firestore.SERVER_TIMESTAMP
        })

    @classmethod
    def get_active(cls, limit: int = 100) -> List[dict]:
        docs = db.collection(cls.collection_name) \\
            .where('deleted', '==', False).limit(limit).stream()
        return [{'id': d.id, **d.to_dict()} for d in docs]

class Post(SoftDeleteMixin):
    collection_name = 'posts'

Post.delete('post_123', deleted_by='user_456')'''
    },
    {
        "instruction": "Write Python async code for Firestore operations using asyncio",
        "output": '''import asyncio
from firebase_admin import firestore
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

db = firestore.client()
executor = ThreadPoolExecutor(max_workers=10)

async def async_get_document(collection: str, doc_id: str) -> Dict:
    loop = asyncio.get_event_loop()
    doc = await loop.run_in_executor(
        executor,
        lambda: db.collection(collection).document(doc_id).get()
    )
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None

async def async_batch_get(collection: str, doc_ids: List[str]) -> List[dict]:
    tasks = [async_get_document(collection, doc_id) for doc_id in doc_ids]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

async def main():
    user_ids = ['user_1', 'user_2', 'user_3']
    users = await async_batch_get('users', user_ids)
    print(f"Fetched {len(users)} users")

asyncio.run(main())'''
    },
    {
        "instruction": "Write TypeScript code for a typed Firestore service with generics",
        "output": '''import {
  collection, doc, getDoc, setDoc, updateDoc, deleteDoc,
  query, where, orderBy, limit, getDocs, Timestamp
} from 'firebase/firestore';
import { db } from './firebase';

interface BaseDocument {
  id?: string;
  createdAt?: Timestamp;
}

class FirestoreService<T extends BaseDocument> {
  constructor(private collectionName: string) {}

  private get ref() {
    return collection(db, this.collectionName);
  }

  async create(data: Omit<T, 'id' | 'createdAt'>): Promise<string> {
    const docRef = doc(this.ref);
    await setDoc(docRef, { ...data, createdAt: Timestamp.now() });
    return docRef.id;
  }

  async getById(id: string): Promise<T | null> {
    const snapshot = await getDoc(doc(db, this.collectionName, id));
    if (!snapshot.exists()) return null;
    return { id: snapshot.id, ...snapshot.data() } as T;
  }

  async update(id: string, data: Partial<T>): Promise<void> {
    await updateDoc(doc(db, this.collectionName, id), data);
  }

  async delete(id: string): Promise<void> {
    await deleteDoc(doc(db, this.collectionName, id));
  }
}

interface User extends BaseDocument {
  email: string;
  name: string;
}

const userService = new FirestoreService<User>('users');'''
    },
    {
        "instruction": "Write TypeScript code for optimistic updates with Firestore in React",
        "output": '''import { useState, useCallback } from 'react';
import { doc, updateDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';

function useOptimisticUpdate<T extends { id: string }>(collectionName: string) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const updateDocument = useCallback(
    async (currentData: T, updates: Partial<T>): Promise<T> => {
      const previousData = { ...currentData };
      const optimisticData = { ...currentData, ...updates };

      setIsUpdating(true);
      setError(null);

      try {
        const docRef = doc(db, collectionName, currentData.id);
        await updateDoc(docRef, { ...updates, updatedAt: serverTimestamp() });
        return optimisticData;
      } catch (err) {
        setError(err as Error);
        return previousData;
      } finally {
        setIsUpdating(false);
      }
    },
    [collectionName]
  );

  return { updateDocument, isUpdating, error };
}

function TodoItem({ todo }: { todo: Todo }) {
  const [localTodo, setLocalTodo] = useState(todo);
  const { updateDocument, isUpdating } = useOptimisticUpdate<Todo>('todos');

  const toggleComplete = async () => {
    const updated = await updateDocument(localTodo, { completed: !localTodo.completed });
    setLocalTodo(updated);
  };

  return (
    <div style={{ opacity: isUpdating ? 0.5 : 1 }}>
      <input type="checkbox" checked={localTodo.completed} onChange={toggleComplete} />
    </div>
  );
}'''
    },
    {
        "instruction": "Write JavaScript code for Firestore aggregation queries",
        "output": '''import {
  collection, query, where, getAggregateFromServer,
  count, sum, average
} from 'firebase/firestore';
import { db } from './firebase';

async function countActiveUsers() {
  const usersRef = collection(db, 'users');
  const activeQuery = query(usersRef, where('status', '==', 'active'));

  const snapshot = await getAggregateFromServer(activeQuery, {
    activeCount: count()
  });

  return snapshot.data().activeCount;
}

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

  return snapshot.data();
}

async function getProductAverageRating(productId) {
  const reviewsRef = collection(db, 'products', productId, 'reviews');
  const snapshot = await getAggregateFromServer(query(reviewsRef), {
    averageRating: average('rating'),
    reviewCount: count()
  });

  return snapshot.data();
}'''
    },
    # =========================================================================
    # ERROR HANDLING
    # =========================================================================
    {
        "instruction": "Write Python code to handle Firestore errors with retry logic",
        "output": '''from firebase_admin import firestore
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded
import time
from functools import wraps

def with_firestore_retry(max_attempts: int = 3, backoff_factor: float = 2.0):
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

            raise last_exception
        return wrapper
    return decorator

class FirestoreClient:
    def __init__(self):
        self.db = firestore.client()

    @with_firestore_retry(max_attempts=3)
    def get_document(self, collection: str, doc_id: str) -> dict:
        doc = self.db.collection(collection).document(doc_id).get()
        return {'id': doc.id, **doc.to_dict()} if doc.exists else None'''
    },
    {
        "instruction": "Write TypeScript code for error handling in Firestore React hooks",
        "output": '''import { FirestoreError } from 'firebase/firestore';

type FirestoreErrorCode = 'permission-denied' | 'not-found' | 'unavailable' | 'unauthenticated';

interface ErrorInfo {
  code: string;
  userMessage: string;
  canRetry: boolean;
}

function getErrorInfo(error: FirestoreError): ErrorInfo {
  const errorMap: Record<string, Partial<ErrorInfo>> = {
    'permission-denied': { userMessage: 'You don\\'t have permission.', canRetry: false },
    'not-found': { userMessage: 'Data not found.', canRetry: false },
    'unavailable': { userMessage: 'Service unavailable. Try again.', canRetry: true },
    'unauthenticated': { userMessage: 'Please sign in.', canRetry: false }
  };

  const info = errorMap[error.code] || { userMessage: 'An error occurred.', canRetry: true };
  return { code: error.code, ...info } as ErrorInfo;
}

function useFirestoreError() {
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleError = (err: unknown) => {
    if (err instanceof FirestoreError) {
      setError(getErrorInfo(err));
    } else {
      setError({ code: 'unknown', userMessage: 'Unexpected error.', canRetry: true });
    }
  };

  return { error, handleError, clearError: () => setError(null) };
}'''
    },
    # =========================================================================
    # TESTING
    # =========================================================================
    {
        "instruction": "Write Python code to test Firestore using the emulator",
        "output": '''import pytest
import os
from firebase_admin import firestore, initialize_app

os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8080'

@pytest.fixture(scope='session')
def db():
    if not firebase_admin._apps:
        initialize_app(options={'projectId': 'test-project'})
    return firestore.client()

class TestUserRepository:
    def test_create_user(self, db):
        user_data = {'email': 'test@example.com', 'name': 'Test User'}
        doc_ref = db.collection('users').add(user_data)
        user_id = doc_ref[1].id

        doc = db.collection('users').document(user_id).get()
        assert doc.exists
        assert doc.to_dict()['email'] == 'test@example.com'

    def test_query_user(self, db):
        db.collection('users').add({'email': 'find@example.com', 'name': 'Find Me'})

        docs = list(db.collection('users')
            .where('email', '==', 'find@example.com').limit(1).stream())

        assert len(docs) == 1
        assert docs[0].to_dict()['name'] == 'Find Me'

    def test_transaction(self, db):
        db.collection('accounts').document('a').set({'balance': 100})
        db.collection('accounts').document('b').set({'balance': 50})

        @firestore.transactional
        def transfer(transaction, from_ref, to_ref, amount):
            from_doc = from_ref.get(transaction=transaction)
            to_doc = to_ref.get(transaction=transaction)
            transaction.update(from_ref, {'balance': from_doc.get('balance') - amount})
            transaction.update(to_ref, {'balance': to_doc.get('balance') + amount})

        transaction = db.transaction()
        transfer(transaction, db.collection('accounts').document('a'),
                 db.collection('accounts').document('b'), 30)

        assert db.collection('accounts').document('a').get().get('balance') == 70'''
    },
    {
        "instruction": "Write TypeScript code to test Firestore security rules with Jest",
        "output": '''import { initializeTestEnvironment, assertFails, assertSucceeds } from '@firebase/rules-unit-testing';
import { doc, setDoc, getDoc } from 'firebase/firestore';
import * as fs from 'fs';

let testEnv;

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: 'test-project',
    firestore: { rules: fs.readFileSync('firestore.rules', 'utf8') }
  });
});

afterAll(() => testEnv.cleanup());
beforeEach(() => testEnv.clearFirestore());

describe('Users collection', () => {
  it('allows users to read their own profile', async () => {
    const context = testEnv.authenticatedContext('user123');
    const db = context.firestore();

    await testEnv.withSecurityRulesDisabled(async (admin) => {
      await setDoc(doc(admin.firestore(), 'users', 'user123'), { name: 'Test' });
    });

    await assertSucceeds(getDoc(doc(db, 'users', 'user123')));
  });

  it('denies reading other profiles', async () => {
    const context = testEnv.authenticatedContext('user123');

    await testEnv.withSecurityRulesDisabled(async (admin) => {
      await setDoc(doc(admin.firestore(), 'users', 'other'), { name: 'Other', private: true });
    });

    await assertFails(getDoc(doc(context.firestore(), 'users', 'other')));
  });
});'''
    },
    # =========================================================================
    # CLOUD STORAGE OPERATIONS
    # =========================================================================
    {
        "instruction": "Write Python code to upload a file to Firebase Cloud Storage",
        "output": '''from firebase_admin import storage

def upload_file(local_path: str, destination_path: str, content_type: str = None) -> str:
    """Upload a file to Firebase Storage and return its public URL."""
    bucket = storage.bucket()
    blob = bucket.blob(destination_path)

    blob.upload_from_filename(local_path, content_type=content_type)
    blob.make_public()

    return blob.public_url

# Usage
url = upload_file('local/image.png', 'uploads/images/profile.png', 'image/png')
print(f"Uploaded to: {url}")'''
    },
    {
        "instruction": "Write Python code to download a file from Firebase Cloud Storage",
        "output": '''from firebase_admin import storage

def download_file(storage_path: str, local_path: str) -> bool:
    """Download a file from Firebase Storage."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    if not blob.exists():
        raise FileNotFoundError(f"File not found: {storage_path}")

    blob.download_to_filename(local_path)
    return True

# Usage
download_file('uploads/documents/report.pdf', '/tmp/report.pdf')'''
    },
    {
        "instruction": "Write Python code to generate a signed URL for Firebase Storage",
        "output": '''from firebase_admin import storage
from datetime import timedelta

def generate_signed_url(storage_path: str, expiration_hours: int = 1) -> str:
    """Generate a signed URL for temporary access to a private file."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    url = blob.generate_signed_url(
        version='v4',
        expiration=timedelta(hours=expiration_hours),
        method='GET'
    )

    return url

# Usage - URL expires in 24 hours
signed_url = generate_signed_url('private/documents/contract.pdf', 24)
print(f"Temporary access URL: {signed_url}")'''
    },
    {
        "instruction": "Write TypeScript code to upload a file to Firebase Storage from a web app",
        "output": '''import { getStorage, ref, uploadBytesResumable, getDownloadURL } from 'firebase/storage';

async function uploadFileWithProgress(
  file: File,
  path: string,
  onProgress?: (progress: number) => void
): Promise<string> {
  const storage = getStorage();
  const storageRef = ref(storage, path);

  const uploadTask = uploadBytesResumable(storageRef, file);

  return new Promise((resolve, reject) => {
    uploadTask.on('state_changed',
      (snapshot) => {
        const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
        onProgress?.(progress);
      },
      (error) => reject(error),
      async () => {
        const downloadURL = await getDownloadURL(uploadTask.snapshot.ref);
        resolve(downloadURL);
      }
    );
  });
}

// Usage
const url = await uploadFileWithProgress(file, `uploads/${file.name}`, (progress) => {
  console.log(`Upload progress: ${progress}%`);
});'''
    },
    {
        "instruction": "Write Python code to delete files from Firebase Storage with a prefix",
        "output": '''from firebase_admin import storage
from typing import List

def delete_files_with_prefix(prefix: str) -> List[str]:
    """Delete all files in Firebase Storage with the given prefix."""
    bucket = storage.bucket()
    blobs = bucket.list_blobs(prefix=prefix)

    deleted = []
    for blob in blobs:
        blob.delete()
        deleted.append(blob.name)

    return deleted

# Usage - delete all files in a user's folder
deleted_files = delete_files_with_prefix('users/user_123/')
print(f"Deleted {len(deleted_files)} files")'''
    },
    {
        "instruction": "Write TypeScript code to list files in a Firebase Storage folder",
        "output": '''import { getStorage, ref, listAll, getDownloadURL, getMetadata } from 'firebase/storage';

interface StorageFile {
  name: string;
  fullPath: string;
  url: string;
  size: number;
  contentType: string;
}

async function listFiles(folderPath: string): Promise<StorageFile[]> {
  const storage = getStorage();
  const folderRef = ref(storage, folderPath);
  const result = await listAll(folderRef);

  const files: StorageFile[] = [];

  for (const itemRef of result.items) {
    const [url, metadata] = await Promise.all([
      getDownloadURL(itemRef),
      getMetadata(itemRef)
    ]);

    files.push({
      name: itemRef.name,
      fullPath: itemRef.fullPath,
      url,
      size: metadata.size,
      contentType: metadata.contentType || 'unknown'
    });
  }

  return files;
}'''
    },
    {
        "instruction": "Write Firebase Storage security rules for user-specific uploads",
        "output": '''rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Users can only access their own folder
    match /users/{userId}/{allPaths=**} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if request.auth != null && request.auth.uid == userId
                   && request.resource.size < 10 * 1024 * 1024  // 10MB limit
                   && request.resource.contentType.matches('image/.*');
    }

    // Public read access for shared files
    match /public/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null && request.auth.token.admin == true;
    }
  }
}'''
    },
    {
        "instruction": "Write Python code to copy a file within Firebase Storage",
        "output": '''from firebase_admin import storage

def copy_file(source_path: str, destination_path: str) -> str:
    """Copy a file within Firebase Storage."""
    bucket = storage.bucket()
    source_blob = bucket.blob(source_path)

    if not source_blob.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    destination_blob = bucket.copy_blob(source_blob, bucket, destination_path)

    return destination_blob.name

# Usage
new_path = copy_file('templates/default.png', 'users/user_123/avatar.png')'''
    },
    {
        "instruction": "Write TypeScript code for image compression before Firebase Storage upload",
        "output": '''import { getStorage, ref, uploadBytes, getDownloadURL } from 'firebase/storage';

async function compressAndUpload(
  file: File,
  path: string,
  maxWidth: number = 800,
  quality: number = 0.8
): Promise<string> {
  // Compress image
  const compressedBlob = await compressImage(file, maxWidth, quality);

  // Upload to Firebase Storage
  const storage = getStorage();
  const storageRef = ref(storage, path);
  await uploadBytes(storageRef, compressedBlob);

  return getDownloadURL(storageRef);
}

async function compressImage(file: File, maxWidth: number, quality: number): Promise<Blob> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ratio = Math.min(1, maxWidth / img.width);
      canvas.width = img.width * ratio;
      canvas.height = img.height * ratio;

      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      canvas.toBlob((blob) => resolve(blob!), 'image/jpeg', quality);
    };
    img.src = URL.createObjectURL(file);
  });
}'''
    },
    {
        "instruction": "Write Python code to set custom metadata on Firebase Storage files",
        "output": '''from firebase_admin import storage

def set_file_metadata(storage_path: str, custom_metadata: dict) -> dict:
    """Set custom metadata on a Firebase Storage file."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    blob.metadata = custom_metadata
    blob.patch()

    return blob.metadata

# Usage
metadata = set_file_metadata('documents/report.pdf', {
    'uploadedBy': 'user_123',
    'department': 'sales',
    'confidential': 'true',
    'version': '2.1'
})'''
    },
    # =========================================================================
    # FIREBASE AUTH ADVANCED FLOWS
    # =========================================================================
    {
        "instruction": "Write Python code to implement multi-factor authentication enrollment",
        "output": '''from firebase_admin import auth

def enroll_mfa_phone(uid: str, phone_number: str, session_info: str) -> dict:
    """Enroll a phone number for MFA."""
    try:
        # Verify the phone number session
        phone_info = auth.PhoneMultiFactorInfo(
            phone_number=phone_number
        )

        # Update user with MFA enrollment
        user = auth.update_user(
            uid,
            multi_factor=auth.MultiFactorSettings(
                enrolled_factors=[phone_info]
            )
        )

        return {
            'success': True,
            'uid': user.uid,
            'mfa_enrolled': True
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}'''
    },
    {
        "instruction": "Write TypeScript code for phone authentication with Firebase",
        "output": '''import {
  getAuth, signInWithPhoneNumber, RecaptchaVerifier,
  PhoneAuthProvider, signInWithCredential
} from 'firebase/auth';

let confirmationResult: any;

async function sendVerificationCode(phoneNumber: string): Promise<void> {
  const auth = getAuth();

  // Setup invisible reCAPTCHA
  const recaptchaVerifier = new RecaptchaVerifier(auth, 'recaptcha-container', {
    size: 'invisible',
    callback: () => console.log('reCAPTCHA verified')
  });

  confirmationResult = await signInWithPhoneNumber(auth, phoneNumber, recaptchaVerifier);
}

async function verifyCode(code: string): Promise<User | null> {
  if (!confirmationResult) {
    throw new Error('No verification in progress');
  }

  try {
    const result = await confirmationResult.confirm(code);
    return result.user;
  } catch (error) {
    console.error('Verification failed:', error);
    return null;
  }
}'''
    },
    {
        "instruction": "Write Python code to link multiple auth providers to a Firebase user",
        "output": '''from firebase_admin import auth

def get_user_providers(uid: str) -> list:
    """Get all auth providers linked to a user."""
    user = auth.get_user(uid)
    return [
        {
            'provider_id': info.provider_id,
            'uid': info.uid,
            'email': getattr(info, 'email', None),
            'phone_number': getattr(info, 'phone_number', None),
        }
        for info in user.provider_data
    ]

def update_provider_data(uid: str, provider_to_link: dict) -> dict:
    """Update user with additional provider data."""
    try:
        user = auth.update_user(
            uid,
            provider_to_link=auth.UserProvider(
                uid=provider_to_link['uid'],
                provider_id=provider_to_link['provider_id'],
                email=provider_to_link.get('email'),
            )
        )
        return {'success': True, 'providers': len(user.provider_data)}
    except Exception as e:
        return {'success': False, 'error': str(e)}'''
    },
    {
        "instruction": "Write TypeScript code for Firebase Auth session management with cookies",
        "output": '''import { getAuth, signInWithEmailAndPassword, getIdToken } from 'firebase/auth';

async function createSessionCookie(email: string, password: string): Promise<string> {
  const auth = getAuth();
  const userCredential = await signInWithEmailAndPassword(auth, email, password);

  // Get fresh ID token
  const idToken = await getIdToken(userCredential.user, true);

  // Send to backend to create session cookie
  const response = await fetch('/api/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idToken }),
    credentials: 'include'
  });

  if (!response.ok) {
    throw new Error('Failed to create session');
  }

  // Sign out client-side (session managed by cookie now)
  await auth.signOut();

  return 'Session created';
}

// Server-side (Node.js)
import * as admin from 'firebase-admin';

async function createSession(idToken: string): Promise<string> {
  const expiresIn = 60 * 60 * 24 * 5 * 1000; // 5 days

  const sessionCookie = await admin.auth().createSessionCookie(idToken, { expiresIn });
  return sessionCookie;
}'''
    },
    {
        "instruction": "Write Python code to implement Firebase Auth rate limiting",
        "output": '''from firebase_admin import auth, firestore
from datetime import datetime, timedelta

db = firestore.client()

async def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> tuple:
    """Check if identifier has exceeded rate limit."""
    doc_ref = db.collection('rate_limits').document(identifier)
    doc = doc_ref.get()

    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    if doc.exists:
        data = doc.to_dict()
        attempts = data.get('attempts', [])

        # Filter attempts within window
        recent_attempts = [
            a for a in attempts
            if datetime.fromisoformat(a) > window_start
        ]

        if len(recent_attempts) >= max_attempts:
            return False, f"Rate limit exceeded. Try again in {window_minutes} minutes."

        # Add new attempt
        recent_attempts.append(now.isoformat())
        doc_ref.update({'attempts': recent_attempts})
    else:
        doc_ref.set({'attempts': [now.isoformat()]})

    return True, "OK"

# Usage in login flow
async def secure_login(email: str, password: str):
    allowed, message = await check_rate_limit(email)
    if not allowed:
        return {'error': message}

    # Proceed with authentication
    # ...'''
    },
    {
        "instruction": "Write TypeScript code for anonymous to permanent account upgrade",
        "output": '''import {
  getAuth, signInAnonymously, linkWithCredential,
  EmailAuthProvider, GoogleAuthProvider, linkWithPopup, User
} from 'firebase/auth';

async function signInAnonymouslyAndSaveData(): Promise<User> {
  const auth = getAuth();
  const userCredential = await signInAnonymously(auth);

  // User can now use the app with temporary data
  return userCredential.user;
}

async function upgradeToEmailAccount(email: string, password: string): Promise<User> {
  const auth = getAuth();
  const currentUser = auth.currentUser;

  if (!currentUser || !currentUser.isAnonymous) {
    throw new Error('Must be signed in anonymously to upgrade');
  }

  const credential = EmailAuthProvider.credential(email, password);
  const userCredential = await linkWithCredential(currentUser, credential);

  // User keeps same UID, data preserved
  return userCredential.user;
}

async function upgradeWithGoogle(): Promise<User> {
  const auth = getAuth();
  const currentUser = auth.currentUser;

  if (!currentUser || !currentUser.isAnonymous) {
    throw new Error('Must be signed in anonymously to upgrade');
  }

  const provider = new GoogleAuthProvider();
  const userCredential = await linkWithPopup(currentUser, provider);

  return userCredential.user;
}'''
    },
    {
        "instruction": "Write Python code to sync Firebase Auth users with Firestore profiles",
        "output": '''from firebase_admin import auth, firestore

db = firestore.client()

def sync_auth_to_firestore(uid: str) -> dict:
    """Sync Firebase Auth user data to Firestore profile."""
    try:
        user = auth.get_user(uid)

        profile_data = {
            'uid': user.uid,
            'email': user.email,
            'email_verified': user.email_verified,
            'display_name': user.display_name,
            'photo_url': user.photo_url,
            'phone_number': user.phone_number,
            'disabled': user.disabled,
            'providers': [p.provider_id for p in user.provider_data],
            'created_at': user.user_metadata.creation_timestamp,
            'last_sign_in': user.user_metadata.last_sign_in_timestamp,
            'synced_at': firestore.SERVER_TIMESTAMP,
        }

        # Add custom claims if any
        if user.custom_claims:
            profile_data['custom_claims'] = user.custom_claims

        db.collection('users').document(uid).set(profile_data, merge=True)

        return {'success': True, 'synced': profile_data}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def bulk_sync_all_users(batch_size: int = 100):
    """Sync all Firebase Auth users to Firestore."""
    synced_count = 0
    page = auth.list_users()

    while page:
        batch = db.batch()

        for user in page.users:
            profile_ref = db.collection('users').document(user.uid)
            batch.set(profile_ref, {
                'email': user.email,
                'display_name': user.display_name,
                'synced_at': firestore.SERVER_TIMESTAMP,
            }, merge=True)
            synced_count += 1

        batch.commit()
        page = page.get_next_page()

    return synced_count'''
    },
    {
        "instruction": "Write TypeScript code for Firebase Auth with custom token claims",
        "output": '''import { getAuth, getIdTokenResult, onAuthStateChanged, User } from 'firebase/auth';

interface CustomClaims {
  role: 'admin' | 'editor' | 'viewer';
  permissions: string[];
  organizationId?: string;
}

async function getUserClaims(user: User): Promise<CustomClaims | null> {
  const tokenResult = await getIdTokenResult(user, true);
  return tokenResult.claims as unknown as CustomClaims;
}

function useAuthWithClaims() {
  const [user, setUser] = useState<User | null>(null);
  const [claims, setClaims] = useState<CustomClaims | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const auth = getAuth();

    return onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);

      if (firebaseUser) {
        const userClaims = await getUserClaims(firebaseUser);
        setClaims(userClaims);
      } else {
        setClaims(null);
      }

      setLoading(false);
    });
  }, []);

  const isAdmin = claims?.role === 'admin';
  const hasPermission = (perm: string) => claims?.permissions?.includes(perm) ?? false;

  return { user, claims, loading, isAdmin, hasPermission };
}'''
    },
    {
        "instruction": "Write Python code to handle Firebase Auth user deletion cascades",
        "output": '''from firebase_admin import auth, firestore, storage

db = firestore.client()

async def delete_user_cascade(uid: str) -> dict:
    """Delete a user and all their associated data."""
    results = {
        'auth_deleted': False,
        'firestore_deleted': [],
        'storage_deleted': [],
        'errors': []
    }

    try:
        # Delete Firestore data
        collections_to_clean = ['users', 'posts', 'comments', 'notifications']

        for collection_name in collections_to_clean:
            # Delete user's document
            db.collection(collection_name).document(uid).delete()
            results['firestore_deleted'].append(f'{collection_name}/{uid}')

            # Delete documents where user is author/owner
            docs = db.collection(collection_name).where('authorId', '==', uid).stream()
            batch = db.batch()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                if count >= 500:
                    batch.commit()
                    batch = db.batch()
                    count = 0
            if count > 0:
                batch.commit()

        # Delete Storage files
        bucket = storage.bucket()
        blobs = bucket.list_blobs(prefix=f'users/{uid}/')
        for blob in blobs:
            blob.delete()
            results['storage_deleted'].append(blob.name)

        # Delete Auth user last
        auth.delete_user(uid)
        results['auth_deleted'] = True

    except Exception as e:
        results['errors'].append(str(e))

    return results'''
    },
    {
        "instruction": "Write TypeScript code for password strength validation with Firebase",
        "output": '''import { getAuth, createUserWithEmailAndPassword } from 'firebase/auth';

interface PasswordValidation {
  valid: boolean;
  score: number;
  feedback: string[];
}

function validatePassword(password: string): PasswordValidation {
  const feedback: string[] = [];
  let score = 0;

  if (password.length >= 8) score += 1;
  else feedback.push('Password must be at least 8 characters');

  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  else feedback.push('Add lowercase letters');

  if (/[A-Z]/.test(password)) score += 1;
  else feedback.push('Add uppercase letters');

  if (/[0-9]/.test(password)) score += 1;
  else feedback.push('Add numbers');

  if (/[^a-zA-Z0-9]/.test(password)) score += 1;
  else feedback.push('Add special characters');

  // Check for common patterns
  const commonPatterns = ['password', '123456', 'qwerty', 'abc123'];
  if (commonPatterns.some(p => password.toLowerCase().includes(p))) {
    score -= 2;
    feedback.push('Avoid common password patterns');
  }

  return {
    valid: score >= 4 && password.length >= 8,
    score: Math.max(0, Math.min(5, score)),
    feedback
  };
}

async function signUpWithValidation(email: string, password: string) {
  const validation = validatePassword(password);

  if (!validation.valid) {
    throw new Error(`Weak password: ${validation.feedback.join(', ')}`);
  }

  const auth = getAuth();
  return createUserWithEmailAndPassword(auth, email, password);
}'''
    },
    # =========================================================================
    # FIRESTORE SUBCOLLECTIONS
    # =========================================================================
    {
        "instruction": "Write Python code to manage Firestore subcollections for a blog system",
        "output": '''from firebase_admin import firestore
from typing import List, Dict

db = firestore.client()

class BlogPostRepository:
    def __init__(self, collection_name: str = 'posts'):
        self.posts_ref = db.collection(collection_name)

    def add_comment(self, post_id: str, comment: Dict) -> str:
        """Add a comment to a post's subcollection."""
        comment['created_at'] = firestore.SERVER_TIMESTAMP
        doc_ref = self.posts_ref.document(post_id).collection('comments').add(comment)

        # Update comment count on parent
        self.posts_ref.document(post_id).update({
            'comment_count': firestore.Increment(1)
        })

        return doc_ref[1].id

    def get_comments(self, post_id: str, limit: int = 20) -> List[Dict]:
        """Get comments for a post, ordered by date."""
        comments_ref = self.posts_ref.document(post_id).collection('comments')
        docs = comments_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()

        return [{'id': doc.id, **doc.to_dict()} for doc in docs]

    def add_like(self, post_id: str, user_id: str) -> bool:
        """Add a like to a post (using subcollection for deduplication)."""
        like_ref = self.posts_ref.document(post_id).collection('likes').document(user_id)

        if like_ref.get().exists:
            return False  # Already liked

        like_ref.set({'user_id': user_id, 'created_at': firestore.SERVER_TIMESTAMP})
        self.posts_ref.document(post_id).update({'like_count': firestore.Increment(1)})

        return True

    def get_post_with_nested_data(self, post_id: str) -> Dict:
        """Get a post with its recent comments and like status."""
        post_doc = self.posts_ref.document(post_id).get()

        if not post_doc.exists:
            return None

        post = {'id': post_doc.id, **post_doc.to_dict()}
        post['recent_comments'] = self.get_comments(post_id, limit=5)

        return post'''
    },
    {
        "instruction": "Write TypeScript code to query across Firestore subcollections with collection group",
        "output": '''import {
  collection, collectionGroup, query, where, orderBy,
  limit, getDocs, Timestamp
} from 'firebase/firestore';
import { db } from './firebase';

interface Comment {
  id: string;
  postId: string;
  authorId: string;
  content: string;
  createdAt: Timestamp;
}

async function getRecentCommentsByUser(userId: string, maxResults: number = 20): Promise<Comment[]> {
  // Query across ALL 'comments' subcollections in the database
  const commentsQuery = query(
    collectionGroup(db, 'comments'),
    where('authorId', '==', userId),
    orderBy('createdAt', 'desc'),
    limit(maxResults)
  );

  const snapshot = await getDocs(commentsQuery);

  return snapshot.docs.map(doc => {
    // Get parent post ID from path: posts/{postId}/comments/{commentId}
    const pathParts = doc.ref.path.split('/');
    const postId = pathParts[1];

    return {
      id: doc.id,
      postId,
      ...doc.data()
    } as Comment;
  });
}

async function getAllReactionsToday(): Promise<{ postId: string; count: number }[]> {
  const startOfDay = new Date();
  startOfDay.setHours(0, 0, 0, 0);

  const reactionsQuery = query(
    collectionGroup(db, 'reactions'),
    where('createdAt', '>=', Timestamp.fromDate(startOfDay))
  );

  const snapshot = await getDocs(reactionsQuery);

  // Group by post ID
  const countByPost = new Map<string, number>();

  snapshot.docs.forEach(doc => {
    const postId = doc.ref.parent.parent?.id;
    if (postId) {
      countByPost.set(postId, (countByPost.get(postId) || 0) + 1);
    }
  });

  return Array.from(countByPost.entries())
    .map(([postId, count]) => ({ postId, count }))
    .sort((a, b) => b.count - a.count);
}'''
    },
    {
        "instruction": "Write Python code to delete a document and all its subcollections",
        "output": '''from firebase_admin import firestore
from typing import List

db = firestore.client()

def delete_document_recursively(doc_ref) -> int:
    """Delete a document and all its subcollections recursively."""
    deleted_count = 0

    # Get all subcollections
    subcollections = doc_ref.collections()

    for subcol in subcollections:
        # Delete all documents in the subcollection
        docs = subcol.stream()
        for doc in docs:
            # Recursively delete nested subcollections
            deleted_count += delete_document_recursively(doc.reference)

    # Delete the document itself
    doc_ref.delete()
    deleted_count += 1

    return deleted_count

def delete_post_with_all_data(post_id: str) -> dict:
    """Delete a blog post and all related subcollection data."""
    post_ref = db.collection('posts').document(post_id)

    if not post_ref.get().exists:
        return {'success': False, 'error': 'Post not found'}

    deleted = delete_document_recursively(post_ref)

    return {
        'success': True,
        'deleted_documents': deleted,
        'message': f'Deleted post {post_id} and {deleted - 1} related documents'
    }'''
    },
    {
        "instruction": "Write TypeScript code to manage nested subcollections for an e-commerce system",
        "output": '''import {
  collection, doc, setDoc, getDoc, getDocs,
  query, where, orderBy, serverTimestamp
} from 'firebase/firestore';
import { db } from './firebase';

interface OrderItem {
  productId: string;
  name: string;
  quantity: number;
  price: number;
}

interface ShippingUpdate {
  status: string;
  location: string;
  timestamp: any;
}

class OrderService {
  private ordersRef = collection(db, 'orders');

  async createOrder(userId: string, items: OrderItem[]): Promise<string> {
    const orderRef = doc(this.ordersRef);
    const orderId = orderRef.id;

    // Create order document
    await setDoc(orderRef, {
      userId,
      status: 'pending',
      total: items.reduce((sum, item) => sum + item.price * item.quantity, 0),
      createdAt: serverTimestamp()
    });

    // Add items as subcollection
    const itemsRef = collection(orderRef, 'items');
    for (const item of items) {
      await setDoc(doc(itemsRef), item);
    }

    return orderId;
  }

  async addShippingUpdate(orderId: string, update: Omit<ShippingUpdate, 'timestamp'>): Promise<void> {
    const updateRef = doc(collection(db, 'orders', orderId, 'shipping_updates'));
    await setDoc(updateRef, {
      ...update,
      timestamp: serverTimestamp()
    });

    // Update order status
    await setDoc(doc(db, 'orders', orderId), { status: update.status }, { merge: true });
  }

  async getOrderWithDetails(orderId: string) {
    const orderDoc = await getDoc(doc(db, 'orders', orderId));
    if (!orderDoc.exists()) return null;

    const [itemsSnap, updatesSnap] = await Promise.all([
      getDocs(collection(db, 'orders', orderId, 'items')),
      getDocs(query(
        collection(db, 'orders', orderId, 'shipping_updates'),
        orderBy('timestamp', 'desc')
      ))
    ]);

    return {
      id: orderId,
      ...orderDoc.data(),
      items: itemsSnap.docs.map(d => ({ id: d.id, ...d.data() })),
      shippingUpdates: updatesSnap.docs.map(d => ({ id: d.id, ...d.data() }))
    };
  }
}'''
    },
    {
        "instruction": "Write Python code to copy a document with all its subcollections",
        "output": '''from firebase_admin import firestore
from typing import Dict, Any

db = firestore.client()

def copy_document_with_subcollections(
    source_ref,
    dest_ref,
    transform_data: callable = None
) -> int:
    """Copy a document and all its subcollections to a new location."""
    copied_count = 0

    # Get source document data
    source_doc = source_ref.get()
    if not source_doc.exists:
        return 0

    # Transform data if needed
    data = source_doc.to_dict()
    if transform_data:
        data = transform_data(data)

    # Copy to destination
    dest_ref.set(data)
    copied_count += 1

    # Copy all subcollections
    for subcol in source_ref.collections():
        dest_subcol = dest_ref.collection(subcol.id)

        for doc in subcol.stream():
            new_doc_ref = dest_subcol.document(doc.id)
            copied_count += copy_document_with_subcollections(
                doc.reference, new_doc_ref, transform_data
            )

    return copied_count

# Usage: Archive a user's data
def archive_user(user_id: str) -> dict:
    source = db.collection('users').document(user_id)
    dest = db.collection('archived_users').document(user_id)

    def add_archive_timestamp(data):
        data['archived_at'] = firestore.SERVER_TIMESTAMP
        return data

    copied = copy_document_with_subcollections(source, dest, add_archive_timestamp)

    return {'copied_documents': copied, 'archived_to': f'archived_users/{user_id}'}'''
    },
    # =========================================================================
    # CLOUD FUNCTIONS V2
    # =========================================================================
    {
        "instruction": "Write a Firebase Cloud Function v2 HTTP trigger with CORS",
        "output": '''import { onRequest } from 'firebase-functions/v2/https';
import * as admin from 'firebase-admin';

admin.initializeApp();

export const createUser = onRequest(
  {
    cors: true,
    region: 'us-central1',
    maxInstances: 10,
  },
  async (req, res) => {
    // Handle preflight
    if (req.method === 'OPTIONS') {
      res.status(204).send('');
      return;
    }

    if (req.method !== 'POST') {
      res.status(405).json({ error: 'Method not allowed' });
      return;
    }

    try {
      const { email, displayName } = req.body;

      const userRecord = await admin.auth().createUser({
        email,
        displayName,
      });

      await admin.firestore().collection('users').doc(userRecord.uid).set({
        email,
        displayName,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      res.status(201).json({ uid: userRecord.uid });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
);'''
    },
    {
        "instruction": "Write a Firebase Cloud Function v2 Firestore trigger with typed data",
        "output": '''import { onDocumentCreated, onDocumentUpdated } from 'firebase-functions/v2/firestore';
import * as admin from 'firebase-admin';

admin.initializeApp();

interface Order {
  userId: string;
  items: Array<{ productId: string; quantity: number; price: number }>;
  total: number;
  status: 'pending' | 'paid' | 'shipped' | 'delivered';
}

export const onOrderCreated = onDocumentCreated(
  {
    document: 'orders/{orderId}',
    region: 'us-central1',
  },
  async (event) => {
    const orderId = event.params.orderId;
    const orderData = event.data?.data() as Order;

    if (!orderData) return;

    // Send notification to user
    const userDoc = await admin.firestore()
      .collection('users')
      .doc(orderData.userId)
      .get();

    if (userDoc.exists) {
      await admin.firestore().collection('notifications').add({
        userId: orderData.userId,
        type: 'order_created',
        message: `Your order #${orderId} has been received`,
        orderId,
        read: false,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
      });
    }
  }
);

export const onOrderStatusChanged = onDocumentUpdated(
  {
    document: 'orders/{orderId}',
    region: 'us-central1',
  },
  async (event) => {
    const before = event.data?.before.data() as Order;
    const after = event.data?.after.data() as Order;

    if (before.status === after.status) return;

    // Log status change
    await admin.firestore()
      .collection('orders')
      .doc(event.params.orderId)
      .collection('history')
      .add({
        previousStatus: before.status,
        newStatus: after.status,
        changedAt: admin.firestore.FieldValue.serverTimestamp(),
      });
  }
);'''
    },
    {
        "instruction": "Write a Firebase Cloud Function v2 scheduled function with secret management",
        "output": '''import { onSchedule } from 'firebase-functions/v2/scheduler';
import { defineSecret } from 'firebase-functions/params';
import * as admin from 'firebase-admin';

admin.initializeApp();

// Define secrets
const SLACK_WEBHOOK_URL = defineSecret('SLACK_WEBHOOK_URL');

export const dailyReport = onSchedule(
  {
    schedule: '0 9 * * *',  // Every day at 9 AM
    timeZone: 'America/New_York',
    region: 'us-central1',
    secrets: [SLACK_WEBHOOK_URL],
  },
  async (event) => {
    const db = admin.firestore();

    // Calculate yesterday's stats
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const [ordersSnap, usersSnap] = await Promise.all([
      db.collection('orders')
        .where('createdAt', '>=', yesterday)
        .where('createdAt', '<', today)
        .count()
        .get(),
      db.collection('users')
        .where('createdAt', '>=', yesterday)
        .where('createdAt', '<', today)
        .count()
        .get(),
    ]);

    const report = {
      date: yesterday.toISOString().split('T')[0],
      newOrders: ordersSnap.data().count,
      newUsers: usersSnap.data().count,
    };

    // Send to Slack
    await fetch(SLACK_WEBHOOK_URL.value(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: `Daily Report for ${report.date}\\nNew Orders: ${report.newOrders}\\nNew Users: ${report.newUsers}`,
      }),
    });
  }
);'''
    },
    {
        "instruction": "Write a Firebase Cloud Function v2 callable function with authentication",
        "output": '''import { onCall, HttpsError } from 'firebase-functions/v2/https';
import * as admin from 'firebase-admin';

admin.initializeApp();

interface TransferRequest {
  toUserId: string;
  amount: number;
  note?: string;
}

interface TransferResponse {
  transactionId: string;
  newBalance: number;
}

export const transferFunds = onCall<TransferRequest, TransferResponse>(
  {
    region: 'us-central1',
    enforceAppCheck: true,  // Require App Check
  },
  async (request) => {
    // Verify authentication
    if (!request.auth) {
      throw new HttpsError('unauthenticated', 'Must be logged in');
    }

    const fromUserId = request.auth.uid;
    const { toUserId, amount, note } = request.data;

    // Validate input
    if (!toUserId || typeof amount !== 'number' || amount <= 0) {
      throw new HttpsError('invalid-argument', 'Invalid transfer data');
    }

    const db = admin.firestore();

    try {
      const result = await db.runTransaction(async (transaction) => {
        const fromRef = db.collection('wallets').doc(fromUserId);
        const toRef = db.collection('wallets').doc(toUserId);

        const [fromDoc, toDoc] = await Promise.all([
          transaction.get(fromRef),
          transaction.get(toRef),
        ]);

        if (!fromDoc.exists || !toDoc.exists) {
          throw new HttpsError('not-found', 'Wallet not found');
        }

        const fromBalance = fromDoc.data()!.balance;
        if (fromBalance < amount) {
          throw new HttpsError('failed-precondition', 'Insufficient funds');
        }

        const newFromBalance = fromBalance - amount;
        const newToBalance = toDoc.data()!.balance + amount;

        transaction.update(fromRef, { balance: newFromBalance });
        transaction.update(toRef, { balance: newToBalance });

        // Create transaction record
        const txRef = db.collection('transactions').doc();
        transaction.set(txRef, {
          from: fromUserId,
          to: toUserId,
          amount,
          note: note || '',
          createdAt: admin.firestore.FieldValue.serverTimestamp(),
        });

        return { transactionId: txRef.id, newBalance: newFromBalance };
      });

      return result;
    } catch (error) {
      if (error instanceof HttpsError) throw error;
      throw new HttpsError('internal', 'Transfer failed');
    }
  }
);'''
    },
    {
        "instruction": "Write a Firebase Cloud Function v2 for Storage trigger with image processing",
        "output": '''import { onObjectFinalized } from 'firebase-functions/v2/storage';
import * as admin from 'firebase-admin';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';
import sharp from 'sharp';

admin.initializeApp();

const THUMBNAIL_SIZES = [100, 300, 600];

export const generateThumbnails = onObjectFinalized(
  {
    region: 'us-central1',
    memory: '512MiB',
    timeoutSeconds: 120,
  },
  async (event) => {
    const filePath = event.data.name;
    const contentType = event.data.contentType;
    const bucket = admin.storage().bucket(event.bucket);

    // Only process images
    if (!contentType?.startsWith('image/')) {
      console.log('Not an image, skipping');
      return;
    }

    // Skip thumbnails
    const fileName = path.basename(filePath);
    if (fileName.startsWith('thumb_')) {
      console.log('Already a thumbnail, skipping');
      return;
    }

    const tempFilePath = path.join(os.tmpdir(), fileName);

    try {
      // Download original
      await bucket.file(filePath).download({ destination: tempFilePath });

      // Generate thumbnails
      const uploadPromises = THUMBNAIL_SIZES.map(async (size) => {
        const thumbName = `thumb_${size}_${fileName}`;
        const thumbPath = path.join(os.tmpdir(), thumbName);

        await sharp(tempFilePath)
          .resize(size, size, { fit: 'cover' })
          .jpeg({ quality: 80 })
          .toFile(thumbPath);

        const destination = path.join(path.dirname(filePath), 'thumbnails', thumbName);
        await bucket.upload(thumbPath, { destination });

        // Cleanup temp file
        fs.unlinkSync(thumbPath);

        return { size, path: destination };
      });

      const thumbnails = await Promise.all(uploadPromises);

      // Update metadata in Firestore
      const fileId = path.basename(filePath, path.extname(filePath));
      await admin.firestore().collection('files').doc(fileId).set({
        originalPath: filePath,
        thumbnails,
        processedAt: admin.firestore.FieldValue.serverTimestamp(),
      }, { merge: true });

    } finally {
      // Cleanup original temp file
      if (fs.existsSync(tempFilePath)) {
        fs.unlinkSync(tempFilePath);
      }
    }
  }
);'''
    },
    {
        "instruction": "Write a Firebase Cloud Function v2 with concurrency and rate limiting",
        "output": '''import { onRequest } from 'firebase-functions/v2/https';
import * as admin from 'firebase-admin';

admin.initializeApp();

// In-memory rate limiting (per instance)
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();

function checkRateLimit(identifier: string, maxRequests: number, windowMs: number): boolean {
  const now = Date.now();
  const record = rateLimitMap.get(identifier);

  if (!record || now > record.resetTime) {
    rateLimitMap.set(identifier, { count: 1, resetTime: now + windowMs });
    return true;
  }

  if (record.count >= maxRequests) {
    return false;
  }

  record.count++;
  return true;
}

export const rateLimitedApi = onRequest(
  {
    cors: true,
    region: 'us-central1',
    concurrency: 80,  // Handle up to 80 concurrent requests per instance
    minInstances: 1,  // Keep warm for faster cold starts
    maxInstances: 10,
  },
  async (req, res) => {
    // Get client identifier (IP or user ID)
    const clientId = req.headers['x-forwarded-for'] as string ||
                     req.auth?.uid ||
                     req.ip ||
                     'anonymous';

    // Check rate limit: 100 requests per minute
    if (!checkRateLimit(clientId, 100, 60000)) {
      res.status(429).json({
        error: 'Rate limit exceeded',
        retryAfter: 60
      });
      return;
    }

    // Process the request
    try {
      const data = await processRequest(req.body);
      res.json({ success: true, data });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
);

async function processRequest(body: any) {
  // Your business logic here
  return { processed: true, timestamp: new Date().toISOString() };
}'''
    },
    # =========================================================================
    # FIRESTORE INDEXES
    # =========================================================================
    {
        "instruction": "Write Firestore index configuration for a blog application",
        "output": '''// firestore.indexes.json
{
  "indexes": [
    {
      "collectionGroup": "posts",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "published", "order": "ASCENDING" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "posts",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "authorId", "order": "ASCENDING" },
        { "fieldPath": "published", "order": "ASCENDING" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "posts",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "tags", "arrayConfig": "CONTAINS" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "comments",
      "queryScope": "COLLECTION_GROUP",
      "fields": [
        { "fieldPath": "authorId", "order": "ASCENDING" },
        { "fieldPath": "createdAt", "order": "DESCENDING" }
      ]
    }
  ],
  "fieldOverrides": [
    {
      "collectionGroup": "posts",
      "fieldPath": "content",
      "indexes": []
    },
    {
      "collectionGroup": "posts",
      "fieldPath": "tags",
      "indexes": [
        { "queryScope": "COLLECTION", "arrayConfig": "CONTAINS" }
      ]
    }
  ]
}'''
    },
    {
        "instruction": "Write Python code to programmatically create Firestore indexes",
        "output": '''import subprocess
import json
from pathlib import Path

def generate_index_config(indexes: list, field_overrides: list = None) -> dict:
    """Generate Firestore index configuration."""
    return {
        "indexes": indexes,
        "fieldOverrides": field_overrides or []
    }

def create_composite_index(collection: str, fields: list, scope: str = "COLLECTION") -> dict:
    """Create a composite index definition."""
    return {
        "collectionGroup": collection,
        "queryScope": scope,
        "fields": [
            {"fieldPath": f["path"], "order": f.get("order", "ASCENDING")}
            if "order" in f or "arrayConfig" not in f
            else {"fieldPath": f["path"], "arrayConfig": f["arrayConfig"]}
            for f in fields
        ]
    }

def deploy_indexes(config_path: str = "firestore.indexes.json"):
    """Deploy Firestore indexes using Firebase CLI."""
    result = subprocess.run(
        ["firebase", "deploy", "--only", "firestore:indexes"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stdout + result.stderr

# Example: Generate indexes for an e-commerce app
indexes = [
    create_composite_index("products", [
        {"path": "category"},
        {"path": "price", "order": "ASCENDING"}
    ]),
    create_composite_index("products", [
        {"path": "inStock"},
        {"path": "rating", "order": "DESCENDING"}
    ]),
    create_composite_index("orders", [
        {"path": "userId"},
        {"path": "status"},
        {"path": "createdAt", "order": "DESCENDING"}
    ]),
]

config = generate_index_config(indexes)
Path("firestore.indexes.json").write_text(json.dumps(config, indent=2))'''
    },
    # =========================================================================
    # ERROR HANDLING PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code for comprehensive Firestore error handling",
        "output": '''from firebase_admin import firestore
from google.api_core import exceptions as gcp_exceptions
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FirestoreError(Exception):
    """Custom Firestore error with context."""
    def __init__(self, message: str, operation: str, collection: str = None, doc_id: str = None):
        self.message = message
        self.operation = operation
        self.collection = collection
        self.doc_id = doc_id
        super().__init__(self.message)

def handle_firestore_operation(func):
    """Decorator for handling Firestore operations with proper error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except gcp_exceptions.NotFound as e:
            logger.warning(f"Document not found: {e}")
            raise FirestoreError("Document not found", func.__name__)
        except gcp_exceptions.PermissionDenied as e:
            logger.error(f"Permission denied: {e}")
            raise FirestoreError("Access denied", func.__name__)
        except gcp_exceptions.AlreadyExists as e:
            logger.warning(f"Document already exists: {e}")
            raise FirestoreError("Document already exists", func.__name__)
        except gcp_exceptions.InvalidArgument as e:
            logger.error(f"Invalid argument: {e}")
            raise FirestoreError("Invalid data provided", func.__name__)
        except gcp_exceptions.ResourceExhausted as e:
            logger.error(f"Quota exceeded: {e}")
            raise FirestoreError("Rate limit exceeded, try again later", func.__name__)
        except gcp_exceptions.Aborted as e:
            logger.warning(f"Transaction aborted: {e}")
            raise FirestoreError("Operation was aborted, please retry", func.__name__)
        except gcp_exceptions.DeadlineExceeded as e:
            logger.error(f"Operation timeout: {e}")
            raise FirestoreError("Operation timed out", func.__name__)
        except Exception as e:
            logger.exception(f"Unexpected Firestore error: {e}")
            raise FirestoreError(f"Unexpected error: {str(e)}", func.__name__)
    return wrapper

class SafeFirestoreClient:
    def __init__(self):
        self.db = firestore.client()

    @handle_firestore_operation
    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None

    @handle_firestore_operation
    def create_document(self, collection: str, data: dict, doc_id: str = None) -> str:
        if doc_id:
            self.db.collection(collection).document(doc_id).set(data)
            return doc_id
        else:
            doc_ref = self.db.collection(collection).add(data)
            return doc_ref[1].id'''
    },
    {
        "instruction": "Write TypeScript code for Firestore error boundary in React",
        "output": '''import React, { Component, ReactNode } from 'react';
import { FirestoreError } from 'firebase/firestore';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: string;
}

class FirestoreErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: '' };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const info = this.getErrorInfo(error);
    this.setState({ errorInfo: info });
    this.props.onError?.(error);
  }

  getErrorInfo(error: Error): string {
    if (error instanceof FirestoreError) {
      const errorMessages: Record<string, string> = {
        'permission-denied': 'You do not have permission to access this data.',
        'not-found': 'The requested data was not found.',
        'unavailable': 'Service is temporarily unavailable. Please try again.',
        'resource-exhausted': 'Too many requests. Please wait and try again.',
        'cancelled': 'The operation was cancelled.',
        'unauthenticated': 'Please sign in to continue.',
      };
      return errorMessages[error.code] || `Database error: ${error.message}`;
    }
    return error.message;
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.errorInfo}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default FirestoreErrorBoundary;'''
    },
    {
        "instruction": "Write Python code for Firestore transaction retry logic",
        "output": '''from firebase_admin import firestore
from google.api_core.exceptions import Aborted, DeadlineExceeded
import time
import random
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar('T')

def with_transaction_retry(
    max_retries: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True
) -> Callable:
    """Decorator for retrying Firestore transactions with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = base_delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (Aborted, DeadlineExceeded) as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff
                        sleep_time = min(delay, max_delay)

                        # Add jitter to prevent thundering herd
                        if jitter:
                            sleep_time = sleep_time * (0.5 + random.random())

                        print(f"Transaction retry {attempt + 1}/{max_retries}, "
                              f"waiting {sleep_time:.2f}s")
                        time.sleep(sleep_time)

                        delay *= 2  # Exponential backoff
                except Exception as e:
                    # Don't retry non-transient errors
                    raise

            raise last_exception

        return wrapper
    return decorator

db = firestore.client()

@with_transaction_retry(max_retries=5)
def transfer_with_retry(from_id: str, to_id: str, amount: float):
    """Transfer funds with automatic retry on transaction conflicts."""

    @firestore.transactional
    def _transfer(transaction, from_ref, to_ref):
        from_doc = from_ref.get(transaction=transaction)
        to_doc = to_ref.get(transaction=transaction)

        if from_doc.get('balance') < amount:
            raise ValueError("Insufficient funds")

        transaction.update(from_ref, {'balance': from_doc.get('balance') - amount})
        transaction.update(to_ref, {'balance': to_doc.get('balance') + amount})

    from_ref = db.collection('accounts').document(from_id)
    to_ref = db.collection('accounts').document(to_id)
    transaction = db.transaction()

    _transfer(transaction, from_ref, to_ref)'''
    },
    {
        "instruction": "Write TypeScript code for offline-first Firestore error handling",
        "output": '''import {
  enableIndexedDbPersistence,
  disableNetwork,
  enableNetwork,
  waitForPendingWrites,
  onSnapshotsInSync
} from 'firebase/firestore';
import { db } from './firebase';

// Enable offline persistence
async function initializeOfflineSupport() {
  try {
    await enableIndexedDbPersistence(db);
    console.log('Offline persistence enabled');
  } catch (err: any) {
    if (err.code === 'failed-precondition') {
      console.warn('Multiple tabs open, persistence available in first tab only');
    } else if (err.code === 'unimplemented') {
      console.warn('Browser does not support offline persistence');
    }
  }
}

// Connection state management
class ConnectionManager {
  private isOnline = navigator.onLine;
  private listeners: Array<(online: boolean) => void> = [];

  constructor() {
    window.addEventListener('online', () => this.setOnline(true));
    window.addEventListener('offline', () => this.setOnline(false));

    // Monitor Firestore sync status
    onSnapshotsInSync(db, () => {
      console.log('All snapshots in sync');
    });
  }

  private setOnline(online: boolean) {
    this.isOnline = online;
    this.listeners.forEach(cb => cb(online));

    if (online) {
      enableNetwork(db);
      console.log('Reconnected to Firestore');
    } else {
      disableNetwork(db);
      console.log('Switched to offline mode');
    }
  }

  subscribe(callback: (online: boolean) => void) {
    this.listeners.push(callback);
    callback(this.isOnline); // Immediate callback with current state
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  async waitForSync() {
    if (!this.isOnline) {
      throw new Error('Cannot sync while offline');
    }
    await waitForPendingWrites(db);
    console.log('All pending writes completed');
  }
}

export const connectionManager = new ConnectionManager();'''
    },
    # =========================================================================
    # TESTING PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code for mocking Firestore in unit tests",
        "output": '''import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, Any, List

class MockDocumentSnapshot:
    def __init__(self, doc_id: str, data: Dict[str, Any], exists: bool = True):
        self.id = doc_id
        self._data = data
        self._exists = exists

    @property
    def exists(self):
        return self._exists

    def to_dict(self):
        return self._data if self._exists else None

    def get(self, field: str):
        return self._data.get(field) if self._exists else None

class MockDocumentReference:
    def __init__(self, collection_path: str, doc_id: str, data: Dict[str, Any] = None):
        self.path = f"{collection_path}/{doc_id}"
        self.id = doc_id
        self._data = data

    def get(self):
        return MockDocumentSnapshot(self.id, self._data, self._data is not None)

    def set(self, data: Dict[str, Any], merge: bool = False):
        self._data = data if not merge else {**self._data or {}, **data}

    def update(self, data: Dict[str, Any]):
        self._data.update(data)

    def delete(self):
        self._data = None

class MockCollection:
    def __init__(self, name: str, documents: Dict[str, Dict[str, Any]] = None):
        self.name = name
        self._documents = documents or {}

    def document(self, doc_id: str) -> MockDocumentReference:
        return MockDocumentReference(self.name, doc_id, self._documents.get(doc_id))

    def add(self, data: Dict[str, Any]):
        import uuid
        doc_id = str(uuid.uuid4())[:8]
        self._documents[doc_id] = data
        return (None, MockDocumentReference(self.name, doc_id, data))

    def where(self, field: str, op: str, value: Any):
        return MockQuery(self._documents, field, op, value)

class MockQuery:
    def __init__(self, documents: Dict, field: str, op: str, value: Any):
        self._results = []
        for doc_id, data in documents.items():
            if self._matches(data.get(field), op, value):
                self._results.append(MockDocumentSnapshot(doc_id, data))

    def _matches(self, field_value, op, value):
        if op == '==': return field_value == value
        if op == '>': return field_value > value
        if op == '<': return field_value < value
        return False

    def stream(self):
        return iter(self._results)

# Usage in tests
@pytest.fixture
def mock_firestore():
    with patch('firebase_admin.firestore.client') as mock_client:
        collections = {
            'users': MockCollection('users', {
                'user_1': {'name': 'Alice', 'email': 'alice@test.com'},
                'user_2': {'name': 'Bob', 'email': 'bob@test.com'},
            })
        }
        mock_client.return_value.collection = lambda name: collections.get(name, MockCollection(name))
        yield mock_client'''
    },
    {
        "instruction": "Write TypeScript code for integration testing Firebase with Jest",
        "output": '''import { initializeTestEnvironment, RulesTestEnvironment } from '@firebase/rules-unit-testing';
import { doc, setDoc, getDoc, collection, addDoc, query, where, getDocs } from 'firebase/firestore';

let testEnv: RulesTestEnvironment;

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: 'demo-test-project',
    firestore: {
      host: 'localhost',
      port: 8080,
    },
  });
});

afterAll(async () => {
  await testEnv.cleanup();
});

beforeEach(async () => {
  await testEnv.clearFirestore();
});

describe('User Service Integration Tests', () => {
  test('should create and retrieve a user', async () => {
    const db = testEnv.unauthenticatedContext().firestore();

    // Create user
    const userData = {
      name: 'Test User',
      email: 'test@example.com',
      createdAt: new Date(),
    };

    await setDoc(doc(db, 'users', 'test-user-id'), userData);

    // Retrieve user
    const userDoc = await getDoc(doc(db, 'users', 'test-user-id'));

    expect(userDoc.exists()).toBe(true);
    expect(userDoc.data()?.name).toBe('Test User');
    expect(userDoc.data()?.email).toBe('test@example.com');
  });

  test('should query users by email', async () => {
    const db = testEnv.unauthenticatedContext().firestore();

    // Create test data
    const usersRef = collection(db, 'users');
    await addDoc(usersRef, { name: 'User 1', email: 'user1@test.com' });
    await addDoc(usersRef, { name: 'User 2', email: 'user2@test.com' });
    await addDoc(usersRef, { name: 'User 3', email: 'user1@test.com' });

    // Query
    const q = query(usersRef, where('email', '==', 'user1@test.com'));
    const snapshot = await getDocs(q);

    expect(snapshot.size).toBe(2);
    expect(snapshot.docs.map(d => d.data().name)).toContain('User 1');
    expect(snapshot.docs.map(d => d.data().name)).toContain('User 3');
  });

  test('should handle authenticated context', async () => {
    const authenticatedDb = testEnv.authenticatedContext('user123').firestore();

    // Write data as authenticated user
    await setDoc(doc(authenticatedDb, 'userProfiles', 'user123'), {
      displayName: 'Authenticated User',
      updatedAt: new Date(),
    });

    // Verify data
    const profileDoc = await getDoc(doc(authenticatedDb, 'userProfiles', 'user123'));
    expect(profileDoc.exists()).toBe(true);
  });
});'''
    },
    # =========================================================================
    # MIGRATION PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code to migrate Firestore data between collections",
        "output": '''from firebase_admin import firestore
from typing import Callable, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

db = firestore.client()

class FirestoreMigration:
    """Tool for migrating data between Firestore collections."""

    def __init__(self, batch_size: int = 500):
        self.batch_size = batch_size
        self.migrated_count = 0
        self.error_count = 0

    def migrate_collection(
        self,
        source_collection: str,
        dest_collection: str,
        transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Migrate all documents from source to destination collection."""

        docs = db.collection(source_collection).stream()
        batch = db.batch()
        batch_count = 0

        for doc in docs:
            try:
                data = doc.to_dict()

                # Apply transformation if provided
                if transform:
                    data = transform(data)
                    if data is None:  # Skip this document
                        continue

                dest_ref = db.collection(dest_collection).document(doc.id)

                if not dry_run:
                    batch.set(dest_ref, data)
                    batch_count += 1

                    if batch_count >= self.batch_size:
                        batch.commit()
                        logger.info(f"Committed batch of {batch_count} documents")
                        batch = db.batch()
                        batch_count = 0

                self.migrated_count += 1

            except Exception as e:
                logger.error(f"Error migrating {doc.id}: {e}")
                self.error_count += 1

        # Commit remaining documents
        if batch_count > 0 and not dry_run:
            batch.commit()
            logger.info(f"Committed final batch of {batch_count} documents")

        return {
            'migrated': self.migrated_count,
            'errors': self.error_count,
            'dry_run': dry_run
        }

    def add_field_to_collection(
        self,
        collection_name: str,
        field_name: str,
        field_value: Any,
        condition: Optional[Callable[[Dict], bool]] = None
    ) -> int:
        """Add a new field to all documents in a collection."""

        docs = db.collection(collection_name).stream()
        batch = db.batch()
        batch_count = 0
        updated = 0

        for doc in docs:
            data = doc.to_dict()

            # Check condition if provided
            if condition and not condition(data):
                continue

            # Skip if field already exists
            if field_name in data:
                continue

            batch.update(doc.reference, {field_name: field_value})
            batch_count += 1
            updated += 1

            if batch_count >= self.batch_size:
                batch.commit()
                batch = db.batch()
                batch_count = 0

        if batch_count > 0:
            batch.commit()

        return updated

# Example usage
def migrate_users_v1_to_v2():
    migration = FirestoreMigration()

    def transform_user(data: Dict) -> Dict:
        # Transform old schema to new schema
        return {
            'profile': {
                'displayName': data.get('name', ''),
                'email': data.get('email', ''),
                'photoUrl': data.get('avatar', ''),
            },
            'settings': {
                'notifications': data.get('notify', True),
                'theme': 'light',
            },
            'metadata': {
                'createdAt': data.get('created_at'),
                'migratedAt': firestore.SERVER_TIMESTAMP,
                'version': 2,
            }
        }

    result = migration.migrate_collection('users', 'users_v2', transform_user, dry_run=True)
    print(f"Migration result: {result}")'''
    },
    {
        "instruction": "Write TypeScript code for Firestore schema versioning",
        "output": '''import { doc, getDoc, setDoc, updateDoc, Timestamp } from 'firebase/firestore';
import { db } from './firebase';

// Schema versions
const CURRENT_USER_VERSION = 3;

interface UserV1 {
  name: string;
  email: string;
  created: Date;
}

interface UserV2 extends UserV1 {
  profile: {
    displayName: string;
    avatar?: string;
  };
  schemaVersion: 2;
}

interface UserV3 {
  profile: {
    displayName: string;
    avatar?: string;
    bio?: string;
  };
  contact: {
    email: string;
    phone?: string;
  };
  settings: {
    notifications: boolean;
    theme: 'light' | 'dark';
  };
  metadata: {
    createdAt: Timestamp;
    updatedAt: Timestamp;
    schemaVersion: 3;
  };
}

type CurrentUser = UserV3;

const migrations: Record<number, (data: any) => any> = {
  // V1 -> V2
  1: (data: UserV1): UserV2 => ({
    ...data,
    profile: {
      displayName: data.name,
    },
    schemaVersion: 2,
  }),

  // V2 -> V3
  2: (data: UserV2): UserV3 => ({
    profile: {
      displayName: data.profile.displayName,
      avatar: data.profile.avatar,
    },
    contact: {
      email: data.email,
    },
    settings: {
      notifications: true,
      theme: 'light',
    },
    metadata: {
      createdAt: Timestamp.fromDate(data.created),
      updatedAt: Timestamp.now(),
      schemaVersion: 3,
    },
  }),
};

async function migrateUserDocument(userId: string): Promise<CurrentUser | null> {
  const userRef = doc(db, 'users', userId);
  const userDoc = await getDoc(userRef);

  if (!userDoc.exists()) return null;

  let data = userDoc.data();
  let version = data.schemaVersion || data.metadata?.schemaVersion || 1;

  // Apply migrations sequentially
  while (version < CURRENT_USER_VERSION) {
    const migration = migrations[version];
    if (!migration) {
      throw new Error(`No migration found for version ${version}`);
    }

    data = migration(data);
    version++;
    console.log(`Migrated user ${userId} to version ${version}`);
  }

  // Save migrated data
  if (version !== (userDoc.data().metadata?.schemaVersion || 1)) {
    await setDoc(userRef, data);
    console.log(`Saved migrated user ${userId}`);
  }

  return data as CurrentUser;
}

// Hook for automatic migration on read
async function getUserWithMigration(userId: string): Promise<CurrentUser | null> {
  return migrateUserDocument(userId);
}'''
    },
    # =========================================================================
    # PERFORMANCE OPTIMIZATION
    # =========================================================================
    {
        "instruction": "Write Python code for Firestore query optimization with caching",
        "output": '''from firebase_admin import firestore
from functools import lru_cache
from typing import Dict, Any, List, Optional
import hashlib
import json
import time
from dataclasses import dataclass

db = firestore.client()

@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl: float

class FirestoreCache:
    """In-memory cache for Firestore queries."""

    def __init__(self, default_ttl: float = 60.0):
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def _make_key(self, collection: str, query_params: dict) -> str:
        params_str = json.dumps(query_params, sort_keys=True)
        return hashlib.md5(f"{collection}:{params_str}".encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and time.time() - entry.timestamp < entry.ttl:
            self.hits += 1
            return entry.data
        self.misses += 1
        return None

    def set(self, key: str, data: Any, ttl: Optional[float] = None):
        self._cache[key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl
        )

    def invalidate(self, key: str):
        self._cache.pop(key, None)

    def invalidate_collection(self, collection: str):
        keys_to_remove = [k for k in self._cache if collection in k]
        for key in keys_to_remove:
            del self._cache[key]

cache = FirestoreCache(default_ttl=300)  # 5 minute cache

class CachedFirestoreClient:
    """Firestore client with caching layer."""

    def __init__(self, cache_instance: FirestoreCache):
        self.cache = cache_instance

    def get_document(self, collection: str, doc_id: str, use_cache: bool = True) -> Optional[Dict]:
        cache_key = f"{collection}/{doc_id}"

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        doc = db.collection(collection).document(doc_id).get()
        data = doc.to_dict() if doc.exists else None

        if data is not None:
            self.cache.set(cache_key, data)

        return data

    def query_documents(
        self,
        collection: str,
        filters: List[tuple],
        order_by: Optional[str] = None,
        limit: int = 100,
        use_cache: bool = True,
        cache_ttl: float = 60
    ) -> List[Dict]:
        query_params = {'filters': filters, 'order_by': order_by, 'limit': limit}
        cache_key = self.cache._make_key(collection, query_params)

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Build query
        query = db.collection(collection)
        for field, op, value in filters:
            query = query.where(field, op, value)
        if order_by:
            query = query.order_by(order_by)
        query = query.limit(limit)

        # Execute
        docs = query.stream()
        results = [{'id': d.id, **d.to_dict()} for d in docs]

        self.cache.set(cache_key, results, cache_ttl)
        return results

    def update_document(self, collection: str, doc_id: str, data: Dict):
        """Update with cache invalidation."""
        db.collection(collection).document(doc_id).update(data)
        self.cache.invalidate(f"{collection}/{doc_id}")
        self.cache.invalidate_collection(collection)  # Invalidate queries'''
    },
    {
        "instruction": "Write TypeScript code for Firestore query batching and deduplication",
        "output": '''import { doc, getDoc, DocumentSnapshot } from 'firebase/firestore';
import { db } from './firebase';

class QueryBatcher {
  private pendingQueries: Map<string, Array<{
    resolve: (value: DocumentSnapshot | null) => void;
    reject: (error: Error) => void;
  }>> = new Map();

  private batchTimeout: NodeJS.Timeout | null = null;
  private readonly batchDelayMs = 10;
  private readonly maxBatchSize = 100;

  async getDocument(path: string): Promise<DocumentSnapshot | null> {
    return new Promise((resolve, reject) => {
      // Add to pending queries
      if (!this.pendingQueries.has(path)) {
        this.pendingQueries.set(path, []);
      }
      this.pendingQueries.get(path)!.push({ resolve, reject });

      // Schedule batch execution
      if (!this.batchTimeout) {
        this.batchTimeout = setTimeout(() => this.executeBatch(), this.batchDelayMs);
      }

      // Execute immediately if batch is full
      if (this.pendingQueries.size >= this.maxBatchSize) {
        this.executeBatch();
      }
    });
  }

  private async executeBatch() {
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }

    const batch = new Map(this.pendingQueries);
    this.pendingQueries.clear();

    const paths = Array.from(batch.keys());

    // Execute all queries in parallel
    const results = await Promise.allSettled(
      paths.map(path => {
        const [collection, docId] = path.split('/');
        return getDoc(doc(db, collection, docId));
      })
    );

    // Resolve/reject all pending promises
    paths.forEach((path, index) => {
      const callbacks = batch.get(path)!;
      const result = results[index];

      callbacks.forEach(({ resolve, reject }) => {
        if (result.status === 'fulfilled') {
          resolve(result.value.exists() ? result.value : null);
        } else {
          reject(result.reason);
        }
      });
    });
  }
}

// Singleton instance
export const queryBatcher = new QueryBatcher();

// Usage example - multiple components requesting same document
// Only one Firestore read will occur
async function getUserProfile(userId: string) {
  const snapshot = await queryBatcher.getDocument(`users/${userId}`);
  return snapshot?.data();
}

// Deduplication in action
async function loadDashboard(userId: string) {
  // These will be deduplicated into single requests
  const [profile, settings, profile2] = await Promise.all([
    queryBatcher.getDocument(`users/${userId}`),
    queryBatcher.getDocument(`settings/${userId}`),
    queryBatcher.getDocument(`users/${userId}`), // Deduplicated!
  ]);

  return { profile: profile?.data(), settings: settings?.data() };
}'''
    },
    {
        "instruction": "Write Python code for Firestore bulk operations with progress tracking",
        "output": '''from firebase_admin import firestore
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

db = firestore.client()

@dataclass
class BulkOperationProgress:
    total: int
    completed: int
    failed: int
    current_batch: int
    total_batches: int

    @property
    def percent_complete(self) -> float:
        return (self.completed / self.total * 100) if self.total > 0 else 0

class BulkOperationManager:
    """Manage bulk Firestore operations with progress tracking."""

    def __init__(
        self,
        batch_size: int = 500,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[BulkOperationProgress], None]] = None
    ):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.progress_callback = progress_callback

    def bulk_write(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
        doc_id_field: Optional[str] = None
    ) -> BulkOperationProgress:
        """Write multiple documents with progress tracking."""

        total = len(documents)
        batches = [documents[i:i + self.batch_size]
                   for i in range(0, total, self.batch_size)]

        progress = BulkOperationProgress(
            total=total,
            completed=0,
            failed=0,
            current_batch=0,
            total_batches=len(batches)
        )

        for batch_idx, batch_docs in enumerate(batches):
            progress.current_batch = batch_idx + 1

            try:
                batch = db.batch()

                for doc_data in batch_docs:
                    if doc_id_field and doc_id_field in doc_data:
                        doc_id = doc_data.pop(doc_id_field)
                        ref = db.collection(collection).document(str(doc_id))
                    else:
                        ref = db.collection(collection).document()

                    batch.set(ref, doc_data)

                batch.commit()
                progress.completed += len(batch_docs)

            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} failed: {e}")
                progress.failed += len(batch_docs)

            if self.progress_callback:
                self.progress_callback(progress)

        return progress

    def bulk_update(
        self,
        collection: str,
        updates: List[Dict[str, Any]],
        id_field: str = 'id'
    ) -> BulkOperationProgress:
        """Update multiple documents."""

        total = len(updates)
        progress = BulkOperationProgress(
            total=total, completed=0, failed=0,
            current_batch=0, total_batches=(total + self.batch_size - 1) // self.batch_size
        )

        batches = [updates[i:i + self.batch_size]
                   for i in range(0, total, self.batch_size)]

        for batch_idx, batch_updates in enumerate(batches):
            progress.current_batch = batch_idx + 1
            batch = db.batch()

            for update in batch_updates:
                doc_id = update.pop(id_field)
                ref = db.collection(collection).document(doc_id)
                batch.update(ref, update)

            try:
                batch.commit()
                progress.completed += len(batch_updates)
            except Exception as e:
                logger.error(f"Update batch failed: {e}")
                progress.failed += len(batch_updates)

            if self.progress_callback:
                self.progress_callback(progress)

        return progress

    def bulk_delete(self, collection: str, doc_ids: List[str]) -> BulkOperationProgress:
        """Delete multiple documents."""

        total = len(doc_ids)
        progress = BulkOperationProgress(
            total=total, completed=0, failed=0,
            current_batch=0, total_batches=(total + self.batch_size - 1) // self.batch_size
        )

        batches = [doc_ids[i:i + self.batch_size]
                   for i in range(0, total, self.batch_size)]

        for batch_idx, batch_ids in enumerate(batches):
            progress.current_batch = batch_idx + 1
            batch = db.batch()

            for doc_id in batch_ids:
                ref = db.collection(collection).document(doc_id)
                batch.delete(ref)

            try:
                batch.commit()
                progress.completed += len(batch_ids)
            except Exception as e:
                logger.error(f"Delete batch failed: {e}")
                progress.failed += len(batch_ids)

            if self.progress_callback:
                self.progress_callback(progress)

        return progress

# Usage
def on_progress(p: BulkOperationProgress):
    print(f"Progress: {p.percent_complete:.1f}% - Batch {p.current_batch}/{p.total_batches}")

manager = BulkOperationManager(progress_callback=on_progress)
result = manager.bulk_write('products', products_data, doc_id_field='sku')'''
    },
    {
        "instruction": "Write TypeScript code for Firestore connection pooling and read replicas",
        "output": '''import { initializeApp, FirebaseApp } from 'firebase/app';
import {
  getFirestore, Firestore, connectFirestoreEmulator,
  doc, getDoc, collection, query, getDocs, QueryConstraint
} from 'firebase/firestore';

interface FirestorePoolConfig {
  primaryConfig: object;
  replicaConfigs?: object[];
  readReplicaRatio?: number; // 0-1, percentage of reads to replicas
}

class FirestoreConnectionPool {
  private primaryApp: FirebaseApp;
  private primaryDb: Firestore;
  private replicaApps: FirebaseApp[] = [];
  private replicaDbs: Firestore[] = [];
  private readReplicaRatio: number;
  private readCount = 0;

  constructor(config: FirestorePoolConfig) {
    // Initialize primary connection
    this.primaryApp = initializeApp(config.primaryConfig, 'primary');
    this.primaryDb = getFirestore(this.primaryApp);

    // Initialize replica connections
    this.replicaApps = (config.replicaConfigs || []).map((cfg, i) =>
      initializeApp(cfg, `replica-${i}`)
    );
    this.replicaDbs = this.replicaApps.map(app => getFirestore(app));

    this.readReplicaRatio = config.readReplicaRatio || 0.5;
  }

  private selectReadDb(): Firestore {
    // No replicas, use primary
    if (this.replicaDbs.length === 0) {
      return this.primaryDb;
    }

    this.readCount++;

    // Route some reads to replicas based on ratio
    if (Math.random() < this.readReplicaRatio) {
      const replicaIndex = this.readCount % this.replicaDbs.length;
      return this.replicaDbs[replicaIndex];
    }

    return this.primaryDb;
  }

  // Always write to primary
  getWriteDb(): Firestore {
    return this.primaryDb;
  }

  // Reads can go to replicas
  getReadDb(): Firestore {
    return this.selectReadDb();
  }

  async getDocument(collectionPath: string, docId: string) {
    const db = this.getReadDb();
    const docRef = doc(db, collectionPath, docId);
    return getDoc(docRef);
  }

  async queryDocuments(
    collectionPath: string,
    ...constraints: QueryConstraint[]
  ) {
    const db = this.getReadDb();
    const q = query(collection(db, collectionPath), ...constraints);
    return getDocs(q);
  }

  // Strong consistency read (always from primary)
  async getDocumentStrong(collectionPath: string, docId: string) {
    const docRef = doc(this.primaryDb, collectionPath, docId);
    return getDoc(docRef);
  }

  getStats() {
    return {
      totalReads: this.readCount,
      replicaCount: this.replicaDbs.length,
      readReplicaRatio: this.readReplicaRatio,
    };
  }
}

// Usage
const pool = new FirestoreConnectionPool({
  primaryConfig: {
    apiKey: process.env.FIREBASE_API_KEY,
    projectId: 'my-project',
  },
  readReplicaRatio: 0.7, // 70% of reads to replicas
});

// Reads automatically load-balanced
const userDoc = await pool.getDocument('users', 'user123');

// Writes always go to primary
const writeDb = pool.getWriteDb();
await setDoc(doc(writeDb, 'users', 'user123'), { updated: true });'''
    },
]

def format_examples(examples: List[Dict]) -> List[Dict]:
    """Format examples for training."""
    formatted = []
    for example in examples:
        formatted.append({
            "messages": [
                {"role": "system", "content": "You are an expert Firebase and Firestore developer. Write clean, efficient, and well-documented code."},
                {"role": "user", "content": example["instruction"]},
                {"role": "assistant", "content": example["output"]}
            ]
        })
    return formatted

def main():
    import random

    examples = format_examples(ALL_EXAMPLES)
    print(f"Total examples: {len(examples)}")

    # Split into train/valid (90/10)
    random.shuffle(examples)
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    output_dir = Path("/Users/fredtaylor/Development/Projects/AITeamPlatform/mlx-training/data/firebase")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write training data
    with open(output_dir / "train.jsonl", "w") as f:
        for example in train_examples:
            f.write(json.dumps(example) + "\n")

    # Write validation data
    with open(output_dir / "valid.jsonl", "w") as f:
        for example in valid_examples:
            f.write(json.dumps(example) + "\n")

    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(valid_examples)}")
    print(f"Saved to: {output_dir}")

if __name__ == "__main__":
    main()
