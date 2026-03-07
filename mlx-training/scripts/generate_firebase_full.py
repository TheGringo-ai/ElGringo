#!/usr/bin/env python3
"""
Complete Firebase/Firestore training data generator.
Generates 500+ diverse examples with variations.
"""

import json
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
    # =========================================================================
    # CLOUD STORAGE OPERATIONS
    # =========================================================================
    {
        "instruction": "Write Python code to upload a file to Firebase Cloud Storage",
        "output": '''from firebase_admin import storage
from pathlib import Path

def upload_file(local_path: str, storage_path: str, content_type: str = None) -> str:
    """Upload a file to Firebase Cloud Storage."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    # Set content type if provided
    if content_type:
        blob.content_type = content_type

    # Upload from local file
    blob.upload_from_filename(local_path)

    # Make publicly accessible (optional)
    blob.make_public()

    return blob.public_url

# Usage
url = upload_file("./photo.jpg", "uploads/users/user123/profile.jpg", "image/jpeg")
print(f"File uploaded: {url}")'''
    },
    {
        "instruction": "Write Python code to download a file from Firebase Cloud Storage",
        "output": '''from firebase_admin import storage

def download_file(storage_path: str, local_path: str) -> bool:
    """Download a file from Firebase Cloud Storage."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    if not blob.exists():
        raise FileNotFoundError(f"File not found: {storage_path}")

    blob.download_to_filename(local_path)
    return True

# Usage
download_file("uploads/users/user123/profile.jpg", "./downloaded_profile.jpg")
print("File downloaded successfully")'''
    },
    {
        "instruction": "Write Python code to generate a signed URL for Firebase Storage file",
        "output": '''from firebase_admin import storage
from datetime import timedelta

def generate_signed_url(storage_path: str, expiration_minutes: int = 60) -> str:
    """Generate a signed URL for temporary file access."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET"
    )

    return url

# Usage
url = generate_signed_url("private/documents/report.pdf", expiration_minutes=30)
print(f"Signed URL (expires in 30 min): {url}")'''
    },
    {
        "instruction": "Write Python code to list files in a Firebase Storage folder",
        "output": '''from firebase_admin import storage
from typing import List, Dict

def list_files(folder_path: str) -> List[Dict]:
    """List all files in a Storage folder."""
    bucket = storage.bucket()
    blobs = bucket.list_blobs(prefix=folder_path)

    files = []
    for blob in blobs:
        files.append({
            'name': blob.name,
            'size': blob.size,
            'content_type': blob.content_type,
            'updated': blob.updated,
            'public_url': blob.public_url if blob.public_url else None
        })

    return files

# Usage
files = list_files("uploads/users/user123/")
for f in files:
    print(f"{f['name']} - {f['size']} bytes")'''
    },
    {
        "instruction": "Write Python code to delete a file from Firebase Storage",
        "output": '''from firebase_admin import storage

def delete_file(storage_path: str) -> bool:
    """Delete a file from Firebase Cloud Storage."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    if blob.exists():
        blob.delete()
        return True
    return False

def delete_folder(folder_path: str) -> int:
    """Delete all files in a folder."""
    bucket = storage.bucket()
    blobs = bucket.list_blobs(prefix=folder_path)

    count = 0
    for blob in blobs:
        blob.delete()
        count += 1

    return count

# Usage
delete_file("uploads/temp/file.txt")
deleted_count = delete_folder("uploads/users/deleted_user/")
print(f"Deleted {deleted_count} files")'''
    },
    {
        "instruction": "Write Python code to copy a file in Firebase Storage",
        "output": '''from firebase_admin import storage

def copy_file(source_path: str, dest_path: str) -> str:
    """Copy a file within Firebase Cloud Storage."""
    bucket = storage.bucket()
    source_blob = bucket.blob(source_path)

    if not source_blob.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Copy to new location
    new_blob = bucket.copy_blob(source_blob, bucket, dest_path)

    return new_blob.public_url

# Usage
new_url = copy_file(
    "uploads/templates/default_avatar.png",
    "uploads/users/user123/avatar.png"
)
print(f"File copied to: {new_url}")'''
    },
    {
        "instruction": "Write Python code to set metadata on a Firebase Storage file",
        "output": '''from firebase_admin import storage

def set_file_metadata(storage_path: str, metadata: dict) -> dict:
    """Set custom metadata on a Storage file."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    # Reload to get current state
    blob.reload()

    # Update metadata
    blob.metadata = metadata
    blob.patch()

    return blob.metadata

# Usage
metadata = set_file_metadata(
    "uploads/documents/report.pdf",
    {
        "uploaded_by": "user123",
        "document_type": "monthly_report",
        "department": "sales",
        "version": "1.2"
    }
)
print(f"Metadata set: {metadata}")'''
    },
    {
        "instruction": "Write TypeScript code to upload a file from browser to Firebase Storage",
        "output": '''import { getStorage, ref, uploadBytesResumable, getDownloadURL } from 'firebase/storage';

interface UploadProgress {
  progress: number;
  state: string;
}

async function uploadFileWithProgress(
  file: File,
  path: string,
  onProgress?: (progress: UploadProgress) => void
): Promise<string> {
  const storage = getStorage();
  const storageRef = ref(storage, path);

  const uploadTask = uploadBytesResumable(storageRef, file, {
    contentType: file.type,
    customMetadata: {
      originalName: file.name,
      uploadedAt: new Date().toISOString()
    }
  });

  return new Promise((resolve, reject) => {
    uploadTask.on(
      'state_changed',
      (snapshot) => {
        const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
        onProgress?.({ progress, state: snapshot.state });
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
const fileInput = document.getElementById('fileInput') as HTMLInputElement;
const file = fileInput.files?.[0];

if (file) {
  const url = await uploadFileWithProgress(
    file,
    `uploads/users/${userId}/${file.name}`,
    (progress) => console.log(`Upload: ${progress.progress}%`)
  );
  console.log('Download URL:', url);
}'''
    },
    {
        "instruction": "Write Python code to upload file content directly to Firebase Storage",
        "output": '''from firebase_admin import storage
import io

def upload_content(content: bytes, storage_path: str, content_type: str) -> str:
    """Upload content directly to Storage without a local file."""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)
    blob.content_type = content_type

    # Upload from bytes
    blob.upload_from_string(content, content_type=content_type)

    # Make public and return URL
    blob.make_public()
    return blob.public_url

def upload_json(data: dict, storage_path: str) -> str:
    """Upload JSON data to Storage."""
    import json
    content = json.dumps(data, indent=2).encode('utf-8')
    return upload_content(content, storage_path, 'application/json')

# Usage
report_data = {"sales": 10000, "month": "January"}
url = upload_json(report_data, "reports/2024/january.json")
print(f"Report uploaded: {url}")'''
    },
    {
        "instruction": "Write Python code to resize image before uploading to Firebase Storage",
        "output": '''from firebase_admin import storage
from PIL import Image
import io

def upload_resized_image(
    image_path: str,
    storage_path: str,
    max_size: tuple = (800, 800),
    quality: int = 85
) -> str:
    """Resize image and upload to Firebase Storage."""
    # Open and resize image
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Resize maintaining aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)

    # Upload to Storage
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)
    blob.content_type = 'image/jpeg'
    blob.upload_from_file(buffer)
    blob.make_public()

    return blob.public_url

# Usage
url = upload_resized_image(
    "./large_photo.png",
    "thumbnails/user123/profile_thumb.jpg",
    max_size=(200, 200)
)
print(f"Thumbnail uploaded: {url}")'''
    },
    # =========================================================================
    # FIREBASE AUTH ADVANCED FLOWS
    # =========================================================================
    {
        "instruction": "Write Python code to implement email verification flow",
        "output": '''from firebase_admin import auth

def send_verification_email(uid: str) -> str:
    """Generate email verification link."""
    user = auth.get_user(uid)

    if user.email_verified:
        return None  # Already verified

    # Generate verification link
    link = auth.generate_email_verification_link(
        user.email,
        action_code_settings=auth.ActionCodeSettings(
            url='https://yourapp.com/verify-complete',
            handle_code_in_app=True
        )
    )

    return link

def verify_email_action(action_code: str) -> dict:
    """Process email verification action code."""
    try:
        # Verify the action code
        info = auth.check_action_code(action_code)

        # Apply the verification
        auth.apply_action_code(action_code)

        return {
            'success': True,
            'email': info.email,
            'operation': info.action
        }
    except auth.InvalidIdTokenError:
        return {'success': False, 'error': 'Invalid or expired code'}'''
    },
    {
        "instruction": "Write Python code to implement password reset flow",
        "output": '''from firebase_admin import auth

def send_password_reset(email: str) -> str:
    """Generate password reset link for a user."""
    try:
        # Verify user exists
        user = auth.get_user_by_email(email)

        # Generate reset link
        link = auth.generate_password_reset_link(
            email,
            action_code_settings=auth.ActionCodeSettings(
                url='https://yourapp.com/reset-complete',
                handle_code_in_app=True
            )
        )

        return link
    except auth.UserNotFoundError:
        # Don't reveal if user exists
        return None

def reset_password(action_code: str, new_password: str) -> dict:
    """Reset password using action code."""
    try:
        # Verify action code
        info = auth.check_action_code(action_code)
        email = info.email

        # Get user and update password
        user = auth.get_user_by_email(email)
        auth.update_user(user.uid, password=new_password)

        # Apply the action code
        auth.apply_action_code(action_code)

        return {'success': True, 'email': email}
    except Exception as e:
        return {'success': False, 'error': str(e)}'''
    },
    {
        "instruction": "Write Python code to implement multi-factor authentication setup",
        "output": '''from firebase_admin import auth

def enroll_mfa_phone(uid: str, phone_number: str) -> dict:
    """Enroll a phone number for MFA."""
    try:
        # Update user with MFA enrollment
        auth.update_user(
            uid,
            mfa_info=[
                auth.PhoneMultiFactorInfo(
                    phone_number=phone_number,
                    display_name='Primary Phone'
                )
            ]
        )

        return {'success': True, 'message': 'MFA enrolled'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def list_mfa_factors(uid: str) -> list:
    """List all MFA factors for a user."""
    user = auth.get_user(uid)

    factors = []
    if user.mfa_info:
        for factor in user.mfa_info:
            factors.append({
                'uid': factor.uid,
                'display_name': factor.display_name,
                'factor_type': factor.factor_id,
                'enrolled_at': factor.enrollment_time
            })

    return factors

def unenroll_mfa(uid: str, mfa_uid: str) -> bool:
    """Remove an MFA factor."""
    user = auth.get_user(uid)

    # Filter out the factor to remove
    remaining = [f for f in user.mfa_info if f.uid != mfa_uid]

    auth.update_user(uid, mfa_info=remaining)
    return True'''
    },
    {
        "instruction": "Write Python code to implement user session management",
        "output": '''from firebase_admin import auth
from datetime import datetime, timezone

def revoke_user_sessions(uid: str) -> dict:
    """Revoke all refresh tokens for a user."""
    auth.revoke_refresh_tokens(uid)

    user = auth.get_user(uid)
    revocation_time = user.tokens_valid_after_timestamp

    return {
        'success': True,
        'uid': uid,
        'tokens_revoked_at': revocation_time
    }

def verify_session_token(id_token: str, check_revoked: bool = True) -> dict:
    """Verify ID token and check if session is still valid."""
    try:
        decoded = auth.verify_id_token(id_token, check_revoked=check_revoked)

        return {
            'valid': True,
            'uid': decoded['uid'],
            'auth_time': datetime.fromtimestamp(decoded['auth_time'], tz=timezone.utc),
            'exp': datetime.fromtimestamp(decoded['exp'], tz=timezone.utc)
        }
    except auth.RevokedIdTokenError:
        return {'valid': False, 'error': 'Token has been revoked'}
    except auth.ExpiredIdTokenError:
        return {'valid': False, 'error': 'Token has expired'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def get_active_sessions(uid: str) -> dict:
    """Get session info for a user."""
    user = auth.get_user(uid)

    return {
        'uid': uid,
        'last_sign_in': user.user_metadata.last_sign_in_timestamp,
        'creation_time': user.user_metadata.creation_timestamp,
        'tokens_valid_after': user.tokens_valid_after_timestamp
    }'''
    },
    {
        "instruction": "Write Python code to bulk import users to Firebase Auth",
        "output": '''from firebase_admin import auth
from typing import List, Dict
import hashlib

def import_users_from_list(users_data: List[Dict]) -> Dict:
    """Bulk import users to Firebase Auth."""
    users_to_import = []

    for user_data in users_data:
        user = auth.ImportUserRecord(
            uid=user_data.get('uid'),
            email=user_data.get('email'),
            display_name=user_data.get('display_name'),
            email_verified=user_data.get('email_verified', False),
            disabled=user_data.get('disabled', False),
            custom_claims=user_data.get('custom_claims', {}),
        )

        # Set password hash if migrating from another system
        if 'password_hash' in user_data:
            user = auth.ImportUserRecord(
                uid=user_data.get('uid'),
                email=user_data.get('email'),
                password_hash=user_data['password_hash'].encode(),
                password_salt=user_data.get('password_salt', '').encode(),
            )

        users_to_import.append(user)

    # Import in batches of 1000
    results = {'success': 0, 'failed': 0, 'errors': []}
    batch_size = 1000

    for i in range(0, len(users_to_import), batch_size):
        batch = users_to_import[i:i + batch_size]

        try:
            result = auth.import_users(
                batch,
                hash_alg=auth.UserImportHash.scrypt(
                    key=b'your-signing-key',
                    salt_separator=b'',
                    rounds=8,
                    memory_cost=14
                )
            )

            results['success'] += result.success_count
            results['failed'] += result.failure_count
            results['errors'].extend([e.reason for e in result.errors])
        except Exception as e:
            results['errors'].append(str(e))

    return results

# Usage
users = [
    {'uid': 'user1', 'email': 'user1@example.com', 'display_name': 'User One'},
    {'uid': 'user2', 'email': 'user2@example.com', 'display_name': 'User Two'},
]
result = import_users_from_list(users)
print(f"Imported {result['success']} users, {result['failed']} failed")'''
    },
    {
        "instruction": "Write Python code to implement account linking between providers",
        "output": '''from firebase_admin import auth

def get_user_providers(uid: str) -> List[Dict]:
    """Get all linked providers for a user."""
    user = auth.get_user(uid)

    providers = []
    for provider in user.provider_data:
        providers.append({
            'provider_id': provider.provider_id,
            'uid': provider.uid,
            'email': provider.email,
            'display_name': provider.display_name,
            'photo_url': provider.photo_url
        })

    return providers

def link_email_password(uid: str, email: str, password: str) -> Dict:
    """Link email/password to existing account."""
    try:
        user = auth.update_user(
            uid,
            email=email,
            password=password
        )

        return {
            'success': True,
            'providers': [p.provider_id for p in user.provider_data]
        }
    except auth.EmailAlreadyExistsError:
        return {'success': False, 'error': 'Email already in use'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def unlink_provider(uid: str, provider_id: str) -> Dict:
    """Unlink a provider from user account."""
    user = auth.get_user(uid)

    # Ensure user has more than one provider
    if len(user.provider_data) <= 1:
        return {'success': False, 'error': 'Cannot unlink last provider'}

    # Firebase Admin SDK doesn't directly support unlinking
    # This would need to be done client-side
    return {'success': False, 'error': 'Unlink must be done client-side'}'''
    },
    {
        "instruction": "Write Python code to implement user impersonation for admin",
        "output": '''from firebase_admin import auth
import time

def create_impersonation_token(
    admin_uid: str,
    target_uid: str,
    duration_minutes: int = 60
) -> str:
    """Create a custom token for admin to impersonate a user."""
    # Verify admin has permission
    admin_user = auth.get_user(admin_uid)
    admin_claims = admin_user.custom_claims or {}

    if not admin_claims.get('super_admin'):
        raise PermissionError("Only super admins can impersonate")

    # Create custom token with impersonation claims
    additional_claims = {
        'impersonated_by': admin_uid,
        'impersonation_expires': int(time.time()) + (duration_minutes * 60),
        'is_impersonation': True
    }

    custom_token = auth.create_custom_token(target_uid, additional_claims)

    # Log impersonation for audit
    log_impersonation(admin_uid, target_uid, duration_minutes)

    return custom_token.decode('utf-8')

def log_impersonation(admin_uid: str, target_uid: str, duration: int):
    """Log impersonation event for audit trail."""
    from firebase_admin import firestore
    db = firestore.client()

    db.collection('audit_logs').add({
        'event': 'user_impersonation',
        'admin_uid': admin_uid,
        'target_uid': target_uid,
        'duration_minutes': duration,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

def verify_impersonation_token(id_token: str) -> Dict:
    """Verify if token is an impersonation session."""
    decoded = auth.verify_id_token(id_token)

    is_impersonation = decoded.get('is_impersonation', False)

    if is_impersonation:
        expires = decoded.get('impersonation_expires', 0)
        if time.time() > expires:
            raise auth.InvalidIdTokenError("Impersonation session expired")

    return {
        'uid': decoded['uid'],
        'is_impersonation': is_impersonation,
        'impersonated_by': decoded.get('impersonated_by')
    }'''
    },
    # =========================================================================
    # FIRESTORE SUBCOLLECTIONS
    # =========================================================================
    {
        "instruction": "Write Python code to work with Firestore subcollections",
        "output": '''from firebase_admin import firestore
from typing import List, Dict

db = firestore.client()

def add_comment_to_post(post_id: str, comment_data: Dict) -> str:
    """Add a comment to a post's subcollection."""
    comment_ref = db.collection('posts').document(post_id).collection('comments').add({
        'text': comment_data['text'],
        'author_id': comment_data['author_id'],
        'author_name': comment_data['author_name'],
        'created_at': firestore.SERVER_TIMESTAMP,
        'likes': 0
    })

    # Update comment count on parent
    db.collection('posts').document(post_id).update({
        'comment_count': firestore.Increment(1)
    })

    return comment_ref[1].id

def get_post_comments(post_id: str, limit: int = 20) -> List[Dict]:
    """Get comments for a post with pagination."""
    comments_ref = (db.collection('posts').document(post_id)
                   .collection('comments')
                   .order_by('created_at', direction=firestore.Query.DESCENDING)
                   .limit(limit))

    comments = []
    for doc in comments_ref.stream():
        comment = doc.to_dict()
        comment['id'] = doc.id
        comments.append(comment)

    return comments

def delete_comment(post_id: str, comment_id: str) -> bool:
    """Delete a comment and update count."""
    db.collection('posts').document(post_id).collection('comments').document(comment_id).delete()

    db.collection('posts').document(post_id).update({
        'comment_count': firestore.Increment(-1)
    })

    return True'''
    },
    {
        "instruction": "Write Python code to manage nested subcollections in Firestore",
        "output": '''from firebase_admin import firestore
from typing import List, Dict

db = firestore.client()

def create_thread_reply(
    forum_id: str,
    thread_id: str,
    reply_data: Dict
) -> str:
    """Add a reply to a forum thread (nested subcollection)."""
    reply_ref = (db.collection('forums')
                .document(forum_id)
                .collection('threads')
                .document(thread_id)
                .collection('replies')
                .add({
                    'content': reply_data['content'],
                    'author_id': reply_data['author_id'],
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'edited': False
                }))

    # Update reply count on thread
    (db.collection('forums')
     .document(forum_id)
     .collection('threads')
     .document(thread_id)
     .update({
         'reply_count': firestore.Increment(1),
         'last_activity': firestore.SERVER_TIMESTAMP
     }))

    return reply_ref[1].id

def get_thread_with_replies(forum_id: str, thread_id: str) -> Dict:
    """Get a thread with its replies."""
    thread_ref = (db.collection('forums')
                 .document(forum_id)
                 .collection('threads')
                 .document(thread_id))

    thread_doc = thread_ref.get()
    if not thread_doc.exists:
        return None

    thread = thread_doc.to_dict()
    thread['id'] = thread_id

    # Get replies
    replies_ref = thread_ref.collection('replies').order_by('created_at').stream()
    thread['replies'] = [{'id': r.id, **r.to_dict()} for r in replies_ref]

    return thread

def delete_thread_cascade(forum_id: str, thread_id: str) -> int:
    """Delete thread and all its replies."""
    thread_ref = (db.collection('forums')
                 .document(forum_id)
                 .collection('threads')
                 .document(thread_id))

    # Delete all replies first
    replies = thread_ref.collection('replies').stream()
    deleted = 0
    for reply in replies:
        reply.reference.delete()
        deleted += 1

    # Delete the thread
    thread_ref.delete()

    return deleted'''
    },
    {
        "instruction": "Write Python code to copy subcollection data in Firestore",
        "output": '''from firebase_admin import firestore
from typing import Dict

db = firestore.client()

def copy_subcollection(
    source_path: str,
    dest_path: str,
    subcollection_name: str
) -> int:
    """Copy a subcollection from one document to another."""
    source_ref = db.document(source_path).collection(subcollection_name)
    dest_ref = db.document(dest_path).collection(subcollection_name)

    batch = db.batch()
    count = 0

    for doc in source_ref.stream():
        new_ref = dest_ref.document(doc.id)
        batch.set(new_ref, doc.to_dict())
        count += 1

        # Commit in batches of 500
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()

    if count % 500 != 0:
        batch.commit()

    return count

def clone_document_with_subcollections(
    source_doc_path: str,
    dest_doc_path: str,
    subcollections: list
) -> Dict:
    """Clone a document and specified subcollections."""
    # Copy main document
    source_doc = db.document(source_doc_path).get()
    if not source_doc.exists:
        raise ValueError("Source document not found")

    data = source_doc.to_dict()
    data['cloned_from'] = source_doc_path
    data['cloned_at'] = firestore.SERVER_TIMESTAMP

    db.document(dest_doc_path).set(data)

    # Copy each subcollection
    results = {'document': True, 'subcollections': {}}
    for subcol in subcollections:
        count = copy_subcollection(source_doc_path, dest_doc_path, subcol)
        results['subcollections'][subcol] = count

    return results

# Usage
result = clone_document_with_subcollections(
    "templates/project_template",
    "projects/new_project",
    ["tasks", "members", "settings"]
)
print(f"Cloned: {result}")'''
    },
    # =========================================================================
    # CLOUD FUNCTIONS V2
    # =========================================================================
    {
        "instruction": "Write Python Cloud Function v2 triggered by Firestore document creation",
        "output": '''from firebase_functions import firestore_fn, https_fn
from firebase_admin import initialize_app, firestore
import google.cloud.firestore

initialize_app()

@firestore_fn.on_document_created(document="users/{userId}")
def on_user_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot]) -> None:
    """Triggered when a new user document is created."""
    user_id = event.params["userId"]
    user_data = event.data.to_dict()

    db = firestore.client()

    # Create user profile
    db.collection("profiles").document(user_id).set({
        "display_name": user_data.get("name", "Anonymous"),
        "bio": "",
        "avatar_url": None,
        "created_at": firestore.SERVER_TIMESTAMP,
        "settings": {
            "notifications": True,
            "theme": "light"
        }
    })

    # Send welcome notification
    db.collection("notifications").add({
        "user_id": user_id,
        "type": "welcome",
        "title": "Welcome to the platform!",
        "read": False,
        "created_at": firestore.SERVER_TIMESTAMP
    })

    print(f"Created profile for user: {user_id}")'''
    },
    {
        "instruction": "Write Python Cloud Function v2 with HTTP trigger and CORS",
        "output": '''from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore
import json

initialize_app()

@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=["https://yourapp.com", "http://localhost:3000"],
        cors_methods=["GET", "POST", "OPTIONS"]
    ),
    memory=options.MemoryOption.MB_256,
    timeout_sec=60
)
def api_endpoint(req: https_fn.Request) -> https_fn.Response:
    """HTTP API endpoint with CORS support."""
    # Handle preflight
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204)

    # Verify authentication
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return https_fn.Response(
            json.dumps({"error": "Unauthorized"}),
            status=401,
            mimetype="application/json"
        )

    # Handle GET request
    if req.method == "GET":
        db = firestore.client()
        items = []
        for doc in db.collection("items").limit(100).stream():
            items.append({"id": doc.id, **doc.to_dict()})

        return https_fn.Response(
            json.dumps({"items": items}),
            status=200,
            mimetype="application/json"
        )

    # Handle POST request
    if req.method == "POST":
        data = req.get_json()
        if not data:
            return https_fn.Response(
                json.dumps({"error": "Invalid JSON"}),
                status=400,
                mimetype="application/json"
            )

        db = firestore.client()
        doc_ref = db.collection("items").add(data)

        return https_fn.Response(
            json.dumps({"id": doc_ref[1].id}),
            status=201,
            mimetype="application/json"
        )

    return https_fn.Response(
        json.dumps({"error": "Method not allowed"}),
        status=405,
        mimetype="application/json"
    )'''
    },
    {
        "instruction": "Write Python Cloud Function v2 for scheduled background job",
        "output": '''from firebase_functions import scheduler_fn, options
from firebase_admin import initialize_app, firestore
from datetime import datetime, timedelta, timezone

initialize_app()

@scheduler_fn.on_schedule(
    schedule="0 2 * * *",  # Run at 2 AM daily
    timezone=scheduler_fn.Timezone("America/New_York"),
    memory=options.MemoryOption.GB_1,
    timeout_sec=540
)
def daily_cleanup(event: scheduler_fn.ScheduledEvent) -> None:
    """Daily cleanup job for expired data."""
    db = firestore.client()
    now = datetime.now(timezone.utc)

    # Clean up expired sessions
    expired_sessions = (db.collection("sessions")
                       .where("expires_at", "<", now)
                       .stream())

    session_count = 0
    batch = db.batch()
    for doc in expired_sessions:
        batch.delete(doc.reference)
        session_count += 1
        if session_count % 500 == 0:
            batch.commit()
            batch = db.batch()

    if session_count % 500 != 0:
        batch.commit()

    # Archive old notifications (older than 30 days)
    cutoff = now - timedelta(days=30)
    old_notifications = (db.collection("notifications")
                        .where("created_at", "<", cutoff)
                        .where("read", "==", True)
                        .stream())

    notification_count = 0
    batch = db.batch()
    for doc in old_notifications:
        # Move to archive
        archive_ref = db.collection("notifications_archive").document(doc.id)
        batch.set(archive_ref, doc.to_dict())
        batch.delete(doc.reference)
        notification_count += 1
        if notification_count % 250 == 0:
            batch.commit()
            batch = db.batch()

    batch.commit()

    # Log results
    db.collection("job_logs").add({
        "job": "daily_cleanup",
        "sessions_deleted": session_count,
        "notifications_archived": notification_count,
        "completed_at": firestore.SERVER_TIMESTAMP
    })

    print(f"Cleanup complete: {session_count} sessions, {notification_count} notifications")'''
    },
    {
        "instruction": "Write Python Cloud Function v2 for Pub/Sub message processing",
        "output": '''from firebase_functions import pubsub_fn, options
from firebase_admin import initialize_app, firestore
import json
import base64

initialize_app()

@pubsub_fn.on_message_published(
    topic="order-events",
    memory=options.MemoryOption.MB_512,
    timeout_sec=120
)
def process_order_event(event: pubsub_fn.CloudEvent[pubsub_fn.MessagePublishedData]) -> None:
    """Process order events from Pub/Sub."""
    # Decode message
    message_data = base64.b64decode(event.data.message.data).decode("utf-8")
    order_event = json.loads(message_data)

    db = firestore.client()
    order_id = order_event.get("order_id")
    event_type = order_event.get("type")

    if event_type == "order_created":
        # Update inventory
        for item in order_event.get("items", []):
            db.collection("inventory").document(item["product_id"]).update({
                "reserved": firestore.Increment(item["quantity"])
            })

        # Notify warehouse
        db.collection("warehouse_tasks").add({
            "order_id": order_id,
            "type": "pick_and_pack",
            "status": "pending",
            "items": order_event["items"],
            "created_at": firestore.SERVER_TIMESTAMP
        })

    elif event_type == "order_shipped":
        # Update order status
        db.collection("orders").document(order_id).update({
            "status": "shipped",
            "shipped_at": firestore.SERVER_TIMESTAMP,
            "tracking_number": order_event.get("tracking_number")
        })

        # Notify customer
        db.collection("notifications").add({
            "user_id": order_event["customer_id"],
            "type": "order_shipped",
            "order_id": order_id,
            "message": f"Your order {order_id} has shipped!",
            "created_at": firestore.SERVER_TIMESTAMP
        })

    elif event_type == "order_cancelled":
        # Release inventory
        for item in order_event.get("items", []):
            db.collection("inventory").document(item["product_id"]).update({
                "reserved": firestore.Increment(-item["quantity"])
            })

        # Process refund
        db.collection("refund_queue").add({
            "order_id": order_id,
            "amount": order_event.get("total"),
            "reason": order_event.get("cancellation_reason"),
            "created_at": firestore.SERVER_TIMESTAMP
        })

    print(f"Processed {event_type} for order {order_id}")'''
    },
    {
        "instruction": "Write Python Cloud Function v2 for image processing on Storage upload",
        "output": '''from firebase_functions import storage_fn, options
from firebase_admin import initialize_app, storage, firestore
from PIL import Image
import io

initialize_app()

@storage_fn.on_object_finalized(
    bucket="your-bucket.appspot.com",
    memory=options.MemoryOption.GB_1,
    timeout_sec=300
)
def process_uploaded_image(event: storage_fn.CloudEvent[storage_fn.StorageObjectData]) -> None:
    """Process uploaded images: resize and create thumbnails."""
    file_path = event.data.name
    content_type = event.data.content_type

    # Only process images in uploads folder
    if not file_path.startswith("uploads/") or not content_type.startswith("image/"):
        return

    bucket = storage.bucket()
    blob = bucket.blob(file_path)

    # Download image
    image_data = blob.download_as_bytes()
    image = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Create thumbnails
    sizes = {
        "thumb": (150, 150),
        "medium": (400, 400),
        "large": (800, 800)
    }

    db = firestore.client()
    urls = {}

    for size_name, dimensions in sizes.items():
        # Resize
        resized = image.copy()
        resized.thumbnail(dimensions, Image.Resampling.LANCZOS)

        # Save to buffer
        buffer = io.BytesIO()
        resized.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        # Upload
        thumb_path = file_path.replace("uploads/", f"thumbnails/{size_name}/")
        thumb_blob = bucket.blob(thumb_path)
        thumb_blob.upload_from_file(buffer, content_type="image/jpeg")
        thumb_blob.make_public()

        urls[size_name] = thumb_blob.public_url

    # Store metadata in Firestore
    db.collection("image_metadata").add({
        "original_path": file_path,
        "thumbnails": urls,
        "original_size": {"width": image.width, "height": image.height},
        "processed_at": firestore.SERVER_TIMESTAMP
    })

    print(f"Processed image: {file_path}, created {len(sizes)} thumbnails")'''
    },
    # =========================================================================
    # REAL-TIME LISTENERS
    # =========================================================================
    {
        "instruction": "Write TypeScript code to listen for real-time Firestore document changes",
        "output": '''import {
  doc,
  onSnapshot,
  Unsubscribe,
  DocumentSnapshot,
  FirestoreError
} from 'firebase/firestore';
import { db } from './firebase-config';

interface User {
  id: string;
  name: string;
  email: string;
  status: 'online' | 'offline';
  lastSeen: Date;
}

function subscribeToUser(
  userId: string,
  onUpdate: (user: User | null) => void,
  onError?: (error: FirestoreError) => void
): Unsubscribe {
  const userRef = doc(db, 'users', userId);

  return onSnapshot(
    userRef,
    (snapshot: DocumentSnapshot) => {
      if (snapshot.exists()) {
        const data = snapshot.data();
        onUpdate({
          id: snapshot.id,
          name: data.name,
          email: data.email,
          status: data.status,
          lastSeen: data.lastSeen?.toDate()
        });
      } else {
        onUpdate(null);
      }
    },
    (error: FirestoreError) => {
      console.error('Snapshot error:', error);
      onError?.(error);
    }
  );
}

// React hook example
function useUser(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);

    const unsubscribe = subscribeToUser(
      userId,
      (userData) => {
        setUser(userData);
        setLoading(false);
      },
      (err) => {
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, [userId]);

  return { user, loading, error };
}'''
    },
    {
        "instruction": "Write TypeScript code to listen for real-time Firestore collection changes",
        "output": '''import {
  collection,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  QuerySnapshot,
  DocumentChange
} from 'firebase/firestore';
import { db } from './firebase-config';

interface Message {
  id: string;
  text: string;
  senderId: string;
  createdAt: Date;
}

interface ChatSubscription {
  unsubscribe: () => void;
}

function subscribeToChat(
  chatId: string,
  callbacks: {
    onAdded?: (message: Message) => void;
    onModified?: (message: Message) => void;
    onRemoved?: (messageId: string) => void;
    onError?: (error: Error) => void;
  }
): ChatSubscription {
  const messagesRef = collection(db, 'chats', chatId, 'messages');
  const q = query(
    messagesRef,
    orderBy('createdAt', 'desc'),
    limit(50)
  );

  const unsubscribe = onSnapshot(
    q,
    (snapshot: QuerySnapshot) => {
      snapshot.docChanges().forEach((change: DocumentChange) => {
        const data = change.doc.data();
        const message: Message = {
          id: change.doc.id,
          text: data.text,
          senderId: data.senderId,
          createdAt: data.createdAt?.toDate()
        };

        switch (change.type) {
          case 'added':
            callbacks.onAdded?.(message);
            break;
          case 'modified':
            callbacks.onModified?.(message);
            break;
          case 'removed':
            callbacks.onRemoved?.(change.doc.id);
            break;
        }
      });
    },
    (error) => {
      console.error('Chat subscription error:', error);
      callbacks.onError?.(error);
    }
  );

  return { unsubscribe };
}

// Usage
const chatSub = subscribeToChat('chat123', {
  onAdded: (msg) => console.log('New message:', msg.text),
  onModified: (msg) => console.log('Message edited:', msg.text),
  onRemoved: (id) => console.log('Message deleted:', id)
});

// Cleanup when done
chatSub.unsubscribe();'''
    },
    {
        "instruction": "Write Python code to listen for Firestore changes with exponential backoff",
        "output": '''from firebase_admin import firestore
import time
import threading
from typing import Callable, Dict, Any, Optional

class FirestoreListener:
    """Resilient Firestore listener with exponential backoff."""

    def __init__(
        self,
        collection_path: str,
        callback: Callable[[list], None],
        query_filters: Optional[list] = None,
        max_retries: int = 5,
        base_delay: float = 1.0
    ):
        self.collection_path = collection_path
        self.callback = callback
        self.query_filters = query_filters or []
        self.max_retries = max_retries
        self.base_delay = base_delay

        self._unsubscribe = None
        self._retry_count = 0
        self._running = False
        self._db = firestore.client()

    def start(self):
        """Start listening for changes."""
        self._running = True
        self._subscribe()

    def stop(self):
        """Stop listening."""
        self._running = False
        if self._unsubscribe:
            self._unsubscribe.unsubscribe()
            self._unsubscribe = None

    def _subscribe(self):
        """Create subscription with error handling."""
        if not self._running:
            return

        try:
            query = self._db.collection(self.collection_path)
            for filter_args in self.query_filters:
                query = query.where(*filter_args)

            self._unsubscribe = query.on_snapshot(self._on_snapshot)
            self._retry_count = 0  # Reset on successful connection

        except Exception as e:
            print(f"Subscription error: {e}")
            self._handle_error()

    def _on_snapshot(self, docs, changes, read_time):
        """Handle snapshot updates."""
        try:
            results = []
            for change in changes:
                results.append({
                    'type': change.type.name,
                    'id': change.document.id,
                    'data': change.document.to_dict()
                })

            self.callback(results)

        except Exception as e:
            print(f"Callback error: {e}")

    def _handle_error(self):
        """Handle errors with exponential backoff."""
        if not self._running or self._retry_count >= self.max_retries:
            print("Max retries reached, stopping listener")
            self._running = False
            return

        delay = self.base_delay * (2 ** self._retry_count)
        self._retry_count += 1

        print(f"Retrying in {delay}s (attempt {self._retry_count})")

        def retry():
            time.sleep(delay)
            if self._running:
                self._subscribe()

        thread = threading.Thread(target=retry, daemon=True)
        thread.start()

# Usage
def handle_changes(changes):
    for change in changes:
        print(f"{change['type']}: {change['id']}")

listener = FirestoreListener(
    'orders',
    handle_changes,
    query_filters=[('status', '==', 'pending')]
)
listener.start()

# Later: listener.stop()'''
    },
    # =========================================================================
    # TESTING PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code to test Firestore with the emulator",
        "output": '''import os
import pytest
from firebase_admin import credentials, firestore, initialize_app, delete_app, get_app
import requests

# Configure emulator
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

@pytest.fixture(scope="session")
def firebase_app():
    """Initialize Firebase app for testing."""
    try:
        app = get_app()
    except ValueError:
        # Use a dummy credential for emulator
        app = initialize_app(options={
            "projectId": "test-project"
        })
    yield app
    # Cleanup after all tests
    delete_app(app)

@pytest.fixture
def db(firebase_app):
    """Get Firestore client."""
    return firestore.client()

@pytest.fixture(autouse=True)
def clear_firestore():
    """Clear Firestore data before each test."""
    # Clear all data using emulator REST API
    requests.delete(
        "http://localhost:8080/emulator/v1/projects/test-project/databases/(default)/documents"
    )
    yield

class TestUserOperations:
    """Test user CRUD operations."""

    def test_create_user(self, db):
        """Test creating a new user."""
        user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "age": 25
        }

        doc_ref = db.collection("users").add(user_data)
        user_id = doc_ref[1].id

        # Verify user was created
        user_doc = db.collection("users").document(user_id).get()
        assert user_doc.exists
        assert user_doc.to_dict()["name"] == "Test User"

    def test_update_user(self, db):
        """Test updating a user."""
        # Create user first
        user_ref = db.collection("users").document("test_user")
        user_ref.set({"name": "Original", "age": 25})

        # Update user
        user_ref.update({"name": "Updated"})

        # Verify update
        user_doc = user_ref.get()
        assert user_doc.to_dict()["name"] == "Updated"
        assert user_doc.to_dict()["age"] == 25  # Unchanged

    def test_query_users(self, db):
        """Test querying users."""
        # Create test data
        db.collection("users").add({"name": "Alice", "age": 30})
        db.collection("users").add({"name": "Bob", "age": 25})
        db.collection("users").add({"name": "Charlie", "age": 35})

        # Query users over 28
        query = db.collection("users").where("age", ">", 28)
        results = list(query.stream())

        assert len(results) == 2
        names = [doc.to_dict()["name"] for doc in results]
        assert "Alice" in names
        assert "Charlie" in names'''
    },
    {
        "instruction": "Write Python code for mocking Firestore in unit tests",
        "output": '''import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, List

# Mock classes for Firestore
@dataclass
class MockDocumentSnapshot:
    """Mock Firestore document snapshot."""
    id: str
    _data: Dict[str, Any]
    _exists: bool = True

    @property
    def exists(self):
        return self._exists

    def to_dict(self):
        return self._data.copy()

    def get(self, field):
        return self._data.get(field)

class MockCollectionReference:
    """Mock Firestore collection reference."""

    def __init__(self, data: Dict[str, Dict] = None):
        self._data = data or {}

    def document(self, doc_id: str):
        return MockDocumentReference(doc_id, self._data.get(doc_id, {}))

    def add(self, data: Dict):
        import uuid
        doc_id = str(uuid.uuid4())[:8]
        self._data[doc_id] = data
        return (None, MockDocumentReference(doc_id, data))

    def where(self, field, op, value):
        # Simple filter implementation
        filtered = {}
        for doc_id, data in self._data.items():
            if op == "==" and data.get(field) == value:
                filtered[doc_id] = data
            elif op == ">" and data.get(field, 0) > value:
                filtered[doc_id] = data
        return MockQuery(filtered)

    def stream(self):
        for doc_id, data in self._data.items():
            yield MockDocumentSnapshot(doc_id, data)

class MockDocumentReference:
    """Mock Firestore document reference."""

    def __init__(self, doc_id: str, data: Dict = None):
        self.id = doc_id
        self._data = data or {}

    def get(self):
        return MockDocumentSnapshot(self.id, self._data, bool(self._data))

    def set(self, data: Dict):
        self._data = data

    def update(self, data: Dict):
        self._data.update(data)

    def delete(self):
        self._data = {}

class MockQuery:
    """Mock Firestore query."""

    def __init__(self, data: Dict[str, Dict]):
        self._data = data

    def stream(self):
        for doc_id, data in self._data.items():
            yield MockDocumentSnapshot(doc_id, data)

# Test using mocks
class TestUserService:
    """Test user service with mocked Firestore."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database with test data."""
        users = {
            "user1": {"name": "Alice", "age": 30},
            "user2": {"name": "Bob", "age": 25}
        }

        mock = Mock()
        mock.collection.return_value = MockCollectionReference(users)
        return mock

    def test_get_user(self, mock_db):
        """Test getting a user."""
        # Import your service (mocked import)
        with patch("your_module.firestore.client", return_value=mock_db):
            from your_module import get_user

            user = get_user("user1")
            assert user["name"] == "Alice"

    def test_user_not_found(self, mock_db):
        """Test handling missing user."""
        mock_db.collection.return_value = MockCollectionReference({})

        with patch("your_module.firestore.client", return_value=mock_db):
            from your_module import get_user

            user = get_user("nonexistent")
            assert user is None'''
    },
    {
        "instruction": "Write Python code for integration testing Firebase Security Rules",
        "output": '''import pytest
import requests
import json
from typing import Dict, Any

class SecurityRulesTestClient:
    """Client for testing Firebase Security Rules."""

    def __init__(self, project_id: str, emulator_host: str = "localhost:8080"):
        self.project_id = project_id
        self.base_url = f"http://{emulator_host}/v1/projects/{project_id}/databases/(default)/documents"

    def as_user(self, uid: str, claims: Dict[str, Any] = None):
        """Create a request context as a specific user."""
        return AuthenticatedClient(self, uid, claims or {})

    def as_anonymous(self):
        """Create an anonymous request context."""
        return AuthenticatedClient(self, None, {})

class AuthenticatedClient:
    """Client with authentication context."""

    def __init__(self, parent: SecurityRulesTestClient, uid: str, claims: Dict):
        self.parent = parent
        self.uid = uid
        self.claims = claims

    def _get_headers(self):
        if self.uid:
            auth = {"uid": self.uid, **self.claims}
            return {
                "Authorization": f"Bearer {json.dumps(auth)}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}

    def read(self, path: str) -> Dict:
        """Attempt to read a document."""
        url = f"{self.parent.base_url}/{path}"
        response = requests.get(url, headers=self._get_headers())
        return {"allowed": response.status_code == 200, "status": response.status_code}

    def write(self, path: str, data: Dict) -> Dict:
        """Attempt to write a document."""
        url = f"{self.parent.base_url}/{path}"
        response = requests.patch(url, json={"fields": data}, headers=self._get_headers())
        return {"allowed": response.status_code in [200, 201], "status": response.status_code}

    def delete(self, path: str) -> Dict:
        """Attempt to delete a document."""
        url = f"{self.parent.base_url}/{path}"
        response = requests.delete(url, headers=self._get_headers())
        return {"allowed": response.status_code == 200, "status": response.status_code}


class TestSecurityRules:
    """Test Firebase Security Rules."""

    @pytest.fixture
    def client(self):
        return SecurityRulesTestClient("test-project")

    def test_user_can_read_own_profile(self, client):
        """Users should be able to read their own profile."""
        result = client.as_user("user123").read("users/user123")
        assert result["allowed"], "User should read own profile"

    def test_user_cannot_read_other_profile(self, client):
        """Users should not read other user profiles."""
        result = client.as_user("user123").read("users/other_user")
        assert not result["allowed"], "User should not read other profiles"

    def test_admin_can_read_any_profile(self, client):
        """Admins should read any profile."""
        result = client.as_user("admin1", {"admin": True}).read("users/any_user")
        assert result["allowed"], "Admin should read any profile"

    def test_anonymous_cannot_write(self, client):
        """Anonymous users should not write."""
        result = client.as_anonymous().write("users/test", {"name": "Test"})
        assert not result["allowed"], "Anonymous should not write"

    def test_user_can_write_own_data(self, client):
        """Users can write their own data."""
        result = client.as_user("user123").write(
            "users/user123",
            {"name": "Updated Name"}
        )
        assert result["allowed"], "User should write own data"'''
    },
    # =========================================================================
    # MIGRATION PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code to migrate data between Firestore collections",
        "output": '''from firebase_admin import firestore
from typing import Callable, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirestoreMigration:
    """Migrate data between Firestore collections."""

    def __init__(self):
        self.db = firestore.client()
        self.batch_size = 500

    def migrate_collection(
        self,
        source_collection: str,
        dest_collection: str,
        transform: Optional[Callable[[Dict], Dict]] = None,
        filter_fn: Optional[Callable[[Dict], bool]] = None
    ) -> Dict[str, int]:
        """
        Migrate documents from one collection to another.

        Args:
            source_collection: Source collection path
            dest_collection: Destination collection path
            transform: Optional function to transform documents
            filter_fn: Optional function to filter which docs to migrate
        """
        source_ref = self.db.collection(source_collection)
        dest_ref = self.db.collection(dest_collection)

        stats = {"migrated": 0, "skipped": 0, "errors": 0}
        batch = self.db.batch()
        batch_count = 0

        for doc in source_ref.stream():
            try:
                data = doc.to_dict()

                # Apply filter
                if filter_fn and not filter_fn(data):
                    stats["skipped"] += 1
                    continue

                # Apply transform
                if transform:
                    data = transform(data)

                # Add to batch
                new_ref = dest_ref.document(doc.id)
                batch.set(new_ref, data)
                batch_count += 1

                # Commit batch when full
                if batch_count >= self.batch_size:
                    batch.commit()
                    stats["migrated"] += batch_count
                    logger.info(f"Migrated {stats['migrated']} documents")
                    batch = self.db.batch()
                    batch_count = 0

            except Exception as e:
                logger.error(f"Error migrating {doc.id}: {e}")
                stats["errors"] += 1

        # Commit remaining
        if batch_count > 0:
            batch.commit()
            stats["migrated"] += batch_count

        return stats

# Usage example
migration = FirestoreMigration()

# Transform function to update schema
def transform_user_v2(data: Dict) -> Dict:
    """Transform user document to v2 schema."""
    return {
        "profile": {
            "displayName": data.get("name", ""),
            "email": data.get("email", ""),
            "avatar": data.get("avatar_url")
        },
        "settings": {
            "notifications": data.get("notifications_enabled", True),
            "theme": "light"
        },
        "metadata": {
            "createdAt": data.get("created_at"),
            "schemaVersion": 2
        }
    }

# Run migration
stats = migration.migrate_collection(
    "users",
    "users_v2",
    transform=transform_user_v2,
    filter_fn=lambda d: d.get("status") != "deleted"
)
print(f"Migration complete: {stats}")'''
    },
    {
        "instruction": "Write Python code for zero-downtime Firestore schema migration",
        "output": '''from firebase_admin import firestore
from typing import Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MigrationPhase(Enum):
    DUAL_WRITE = "dual_write"      # Write to both old and new
    BACKFILL = "backfill"          # Copy old data to new
    DUAL_READ = "dual_read"        # Read from new, fallback to old
    NEW_ONLY = "new_only"          # Only use new schema

@dataclass
class SchemaVersion:
    version: int
    transformer: Callable[[Dict], Dict]

class ZeroDowntimeMigration:
    """
    Zero-downtime schema migration for Firestore.

    Strategy:
    1. DUAL_WRITE: All writes go to both schemas
    2. BACKFILL: Migrate existing data
    3. DUAL_READ: Read from new, fallback to old
    4. NEW_ONLY: Remove old schema support
    """

    def __init__(self, collection: str, current_version: int):
        self.db = firestore.client()
        self.collection = collection
        self.current_version = current_version
        self.phase = MigrationPhase.DUAL_WRITE
        self.versions: Dict[int, SchemaVersion] = {}

    def register_version(self, version: int, transformer: Callable[[Dict], Dict]):
        """Register a schema version with its transformer."""
        self.versions[version] = SchemaVersion(version, transformer)

    def write(self, doc_id: str, data: Dict) -> None:
        """Write document respecting current migration phase."""
        doc_ref = self.db.collection(self.collection).document(doc_id)

        if self.phase == MigrationPhase.DUAL_WRITE:
            # Write current version
            current_data = data.copy()
            current_data["_schemaVersion"] = self.current_version

            # Also write next version if transformer exists
            next_version = self.current_version + 1
            if next_version in self.versions:
                next_data = self.versions[next_version].transformer(data)
                next_data["_schemaVersion"] = next_version
                current_data["_nextSchema"] = next_data

            doc_ref.set(current_data)

        elif self.phase in [MigrationPhase.DUAL_READ, MigrationPhase.NEW_ONLY]:
            # Write only new version
            data["_schemaVersion"] = self.current_version + 1
            doc_ref.set(data)

    def read(self, doc_id: str) -> Dict:
        """Read document respecting current migration phase."""
        doc_ref = self.db.collection(self.collection).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        schema_version = data.get("_schemaVersion", 1)

        # If new schema available, use it
        if "_nextSchema" in data and self.phase in [MigrationPhase.DUAL_READ, MigrationPhase.NEW_ONLY]:
            return data["_nextSchema"]

        # Transform to latest if needed
        while schema_version < self.current_version:
            next_v = schema_version + 1
            if next_v in self.versions:
                data = self.versions[next_v].transformer(data)
                schema_version = next_v

        return data

    def backfill(self, batch_size: int = 500) -> Dict[str, int]:
        """Backfill all documents to new schema."""
        stats = {"updated": 0, "skipped": 0}

        collection_ref = self.db.collection(self.collection)
        batch = self.db.batch()
        count = 0

        for doc in collection_ref.stream():
            data = doc.to_dict()

            if "_nextSchema" in data:
                stats["skipped"] += 1
                continue

            # Transform to new schema
            next_version = self.current_version + 1
            if next_version in self.versions:
                new_data = self.versions[next_version].transformer(data)
                new_data["_schemaVersion"] = next_version
                data["_nextSchema"] = new_data

                batch.set(doc.reference, data)
                count += 1

                if count >= batch_size:
                    batch.commit()
                    stats["updated"] += count
                    batch = self.db.batch()
                    count = 0

        if count > 0:
            batch.commit()
            stats["updated"] += count

        return stats

# Usage
migration = ZeroDowntimeMigration("users", current_version=1)

# Register transformer for v2
migration.register_version(2, lambda data: {
    "profile": {"name": data.get("name"), "email": data.get("email")},
    "createdAt": data.get("created_at")
})

# Start dual-write phase
migration.phase = MigrationPhase.DUAL_WRITE

# Backfill existing data
stats = migration.backfill()
print(f"Backfill: {stats}")

# Switch to dual-read
migration.phase = MigrationPhase.DUAL_READ'''
    },
    # =========================================================================
    # PERFORMANCE OPTIMIZATION
    # =========================================================================
    {
        "instruction": "Write Python code to implement Firestore query caching",
        "output": '''from firebase_admin import firestore
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import threading

@dataclass
class CacheEntry:
    data: Any
    expires_at: datetime
    query_hash: str

class FirestoreCache:
    """In-memory cache for Firestore queries."""

    def __init__(self, default_ttl_seconds: int = 300):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.lock = threading.RLock()
        self.db = firestore.client()

    def _hash_query(self, collection: str, filters: List[Tuple], order: str = None) -> str:
        """Create a hash for the query parameters."""
        query_str = json.dumps({
            "collection": collection,
            "filters": filters,
            "order": order
        }, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()

    def get_cached(self, query_hash: str) -> Optional[Any]:
        """Get cached result if not expired."""
        with self.lock:
            entry = self.cache.get(query_hash)
            if entry and entry.expires_at > datetime.now():
                return entry.data
            elif entry:
                del self.cache[query_hash]
            return None

    def set_cached(self, query_hash: str, data: Any, ttl: timedelta = None):
        """Cache query result."""
        with self.lock:
            self.cache[query_hash] = CacheEntry(
                data=data,
                expires_at=datetime.now() + (ttl or self.default_ttl),
                query_hash=query_hash
            )

    def query(
        self,
        collection: str,
        filters: List[Tuple] = None,
        order_by: str = None,
        limit: int = None,
        ttl_seconds: int = None
    ) -> List[Dict]:
        """Execute query with caching."""
        filters = filters or []
        query_hash = self._hash_query(collection, filters, order_by)

        # Check cache first
        cached = self.get_cached(query_hash)
        if cached is not None:
            return cached

        # Execute query
        query = self.db.collection(collection)
        for field, op, value in filters:
            query = query.where(field, op, value)

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        results = [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

        # Cache results
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None
        self.set_cached(query_hash, results, ttl)

        return results

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries."""
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                to_delete = [k for k in self.cache if pattern in k]
                for key in to_delete:
                    del self.cache[key]

    def get_document(self, collection: str, doc_id: str, ttl_seconds: int = None) -> Optional[Dict]:
        """Get single document with caching."""
        cache_key = f"{collection}/{doc_id}"

        cached = self.get_cached(cache_key)
        if cached is not None:
            return cached

        doc = self.db.collection(collection).document(doc_id).get()
        if not doc.exists:
            return None

        data = {"id": doc.id, **doc.to_dict()}
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None
        self.set_cached(cache_key, data, ttl)

        return data

# Usage
cache = FirestoreCache(default_ttl_seconds=300)

# Cached query
users = cache.query(
    "users",
    filters=[("status", "==", "active")],
    order_by="created_at",
    limit=100
)

# Cached document
user = cache.get_document("users", "user123")

# Invalidate when data changes
cache.invalidate("users")'''
    },
    {
        "instruction": "Write Python code for optimized Firestore batch reading",
        "output": '''from firebase_admin import firestore
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OptimizedReader:
    """Optimized batch reading for Firestore."""

    def __init__(self, max_workers: int = 10):
        self.db = firestore.client()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def get_multiple_documents(
        self,
        collection: str,
        doc_ids: List[str]
    ) -> Dict[str, Dict]:
        """
        Get multiple documents efficiently using get_all().

        Much faster than individual get() calls.
        """
        if not doc_ids:
            return {}

        # Create document references
        refs = [self.db.collection(collection).document(doc_id) for doc_id in doc_ids]

        # Get all documents in one call
        docs = self.db.get_all(refs)

        results = {}
        for doc in docs:
            if doc.exists:
                results[doc.id] = doc.to_dict()

        return results

    def get_documents_from_multiple_collections(
        self,
        requests: List[Dict[str, str]]
    ) -> Dict[str, Dict]:
        """
        Get documents from multiple collections in parallel.

        Args:
            requests: List of {"collection": "...", "doc_id": "..."}
        """
        refs = [
            self.db.collection(req["collection"]).document(req["doc_id"])
            for req in requests
        ]

        docs = self.db.get_all(refs)

        results = {}
        for doc in docs:
            if doc.exists:
                key = f"{doc.reference.parent.id}/{doc.id}"
                results[key] = doc.to_dict()

        return results

    def parallel_queries(
        self,
        queries: List[Dict[str, Any]]
    ) -> List[List[Dict]]:
        """
        Execute multiple queries in parallel.

        Args:
            queries: List of query configs:
                {
                    "collection": "users",
                    "filters": [("status", "==", "active")],
                    "limit": 100
                }
        """
        def execute_query(query_config: Dict) -> List[Dict]:
            query = self.db.collection(query_config["collection"])

            for field, op, value in query_config.get("filters", []):
                query = query.where(field, op, value)

            if "order_by" in query_config:
                query = query.order_by(query_config["order_by"])

            if "limit" in query_config:
                query = query.limit(query_config["limit"])

            return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

        # Execute all queries in parallel
        futures = [
            self.executor.submit(execute_query, q)
            for q in queries
        ]

        return [f.result() for f in futures]

    def stream_large_collection(
        self,
        collection: str,
        batch_size: int = 1000,
        order_field: str = "__name__"
    ):
        """
        Stream a large collection efficiently using pagination.

        Yields documents in batches to avoid memory issues.
        """
        query = (self.db.collection(collection)
                .order_by(order_field)
                .limit(batch_size))

        last_doc = None

        while True:
            if last_doc:
                query = (self.db.collection(collection)
                        .order_by(order_field)
                        .start_after(last_doc)
                        .limit(batch_size))

            docs = list(query.stream())

            if not docs:
                break

            yield [{"id": doc.id, **doc.to_dict()} for doc in docs]
            last_doc = docs[-1]

# Usage
reader = OptimizedReader()

# Get multiple documents efficiently
users = reader.get_multiple_documents(
    "users",
    ["user1", "user2", "user3", "user4", "user5"]
)

# Parallel queries
results = reader.parallel_queries([
    {"collection": "users", "filters": [("role", "==", "admin")], "limit": 50},
    {"collection": "posts", "filters": [("published", "==", True)], "limit": 100},
    {"collection": "orders", "filters": [("status", "==", "pending")], "limit": 50},
])

# Stream large collection
for batch in reader.stream_large_collection("events"):
    process_batch(batch)'''
    },
    {
        "instruction": "Write Python code for Firestore connection pooling",
        "output": '''from firebase_admin import firestore, credentials, initialize_app
from typing import Optional
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class PooledClient:
    client: firestore.Client
    created_at: datetime
    last_used: datetime
    in_use: bool = False

class FirestoreConnectionPool:
    """
    Connection pool for Firestore clients.

    Useful for high-throughput applications where creating
    new clients is expensive.
    """

    def __init__(
        self,
        min_connections: int = 2,
        max_connections: int = 10,
        max_idle_time_seconds: int = 300
    ):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = timedelta(seconds=max_idle_time_seconds)

        self.pool: list[PooledClient] = []
        self.lock = threading.RLock()

        # Initialize minimum connections
        for _ in range(min_connections):
            self._create_client()

    def _create_client(self) -> PooledClient:
        """Create a new Firestore client."""
        client = firestore.client()
        pooled = PooledClient(
            client=client,
            created_at=datetime.now(),
            last_used=datetime.now()
        )
        self.pool.append(pooled)
        return pooled

    def acquire(self) -> firestore.Client:
        """Acquire a client from the pool."""
        with self.lock:
            # Find an available client
            for pooled in self.pool:
                if not pooled.in_use:
                    pooled.in_use = True
                    pooled.last_used = datetime.now()
                    return pooled.client

            # Create new client if under max
            if len(self.pool) < self.max_connections:
                pooled = self._create_client()
                pooled.in_use = True
                return pooled.client

            # Wait and retry (simple blocking)
            raise RuntimeError("Connection pool exhausted")

    def release(self, client: firestore.Client):
        """Release a client back to the pool."""
        with self.lock:
            for pooled in self.pool:
                if pooled.client is client:
                    pooled.in_use = False
                    pooled.last_used = datetime.now()
                    return

    def cleanup_idle(self):
        """Remove idle connections above minimum."""
        with self.lock:
            now = datetime.now()
            to_remove = []

            for pooled in self.pool:
                if (not pooled.in_use and
                    len(self.pool) > self.min_connections and
                    now - pooled.last_used > self.max_idle_time):
                    to_remove.append(pooled)

            for pooled in to_remove:
                self.pool.remove(pooled)

class PooledFirestoreContext:
    """Context manager for pooled Firestore client."""

    def __init__(self, pool: FirestoreConnectionPool):
        self.pool = pool
        self.client = None

    def __enter__(self) -> firestore.Client:
        self.client = self.pool.acquire()
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.pool.release(self.client)

# Global pool instance
_pool: Optional[FirestoreConnectionPool] = None

def get_pool() -> FirestoreConnectionPool:
    global _pool
    if _pool is None:
        _pool = FirestoreConnectionPool()
    return _pool

def with_firestore():
    """Get a pooled Firestore context."""
    return PooledFirestoreContext(get_pool())

# Usage
def high_throughput_operation():
    with with_firestore() as db:
        # Use db for operations
        docs = db.collection("users").limit(100).stream()
        for doc in docs:
            process(doc)
    # Client automatically returned to pool'''
    },
    # =========================================================================
    # DATA MODELING PATTERNS
    # =========================================================================
    {
        "instruction": "Write Python code for denormalized data pattern in Firestore",
        "output": '''from firebase_admin import firestore
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class DenormalizedData:
    """Manage denormalized data across Firestore documents."""

    db = firestore.client()

    @classmethod
    def update_user_profile(cls, user_id: str, updates: Dict) -> None:
        """
        Update user profile and propagate to denormalized locations.

        When user data changes, update:
        - users/{userId}
        - posts/{postId}.author (embedded author info)
        - comments/{commentId}.author
        - team_members/{teamId}/members/{userId}
        """
        batch = cls.db.batch()

        # Update main user document
        user_ref = cls.db.collection("users").document(user_id)
        batch.update(user_ref, updates)

        # Prepare denormalized updates
        denorm_updates = {}
        if "display_name" in updates:
            denorm_updates["author.display_name"] = updates["display_name"]
        if "avatar_url" in updates:
            denorm_updates["author.avatar_url"] = updates["avatar_url"]

        if denorm_updates:
            # Update posts by this user
            posts = cls.db.collection("posts").where("author.uid", "==", user_id).stream()
            for post in posts:
                batch.update(post.reference, denorm_updates)

            # Update comments by this user
            comments = cls.db.collection_group("comments").where("author.uid", "==", user_id).stream()
            for comment in comments:
                batch.update(comment.reference, denorm_updates)

        batch.commit()

    @classmethod
    def create_post(cls, user_id: str, post_data: Dict) -> str:
        """
        Create a post with denormalized author data.
        """
        # Get author data
        user_doc = cls.db.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()

        # Embed author info in post
        post = {
            **post_data,
            "author": {
                "uid": user_id,
                "display_name": user_data.get("display_name"),
                "avatar_url": user_data.get("avatar_url"),
            },
            "created_at": firestore.SERVER_TIMESTAMP,
            "comment_count": 0,
            "like_count": 0,
        }

        doc_ref = cls.db.collection("posts").add(post)
        return doc_ref[1].id

    @classmethod
    def add_comment(cls, post_id: str, user_id: str, comment_text: str) -> str:
        """
        Add a comment with denormalized data and update counters.
        """
        # Get author data
        user_doc = cls.db.collection("users").document(user_id).get()
        user_data = user_doc.to_dict()

        batch = cls.db.batch()

        # Create comment with embedded author
        comment_ref = cls.db.collection("posts").document(post_id).collection("comments").document()
        batch.set(comment_ref, {
            "text": comment_text,
            "author": {
                "uid": user_id,
                "display_name": user_data.get("display_name"),
                "avatar_url": user_data.get("avatar_url"),
            },
            "created_at": firestore.SERVER_TIMESTAMP,
            "like_count": 0,
        })

        # Update post comment count
        post_ref = cls.db.collection("posts").document(post_id)
        batch.update(post_ref, {
            "comment_count": firestore.Increment(1),
            "last_comment_at": firestore.SERVER_TIMESTAMP,
        })

        batch.commit()
        return comment_ref.id

# Usage
DenormalizedData.update_user_profile("user123", {
    "display_name": "New Name",
    "avatar_url": "https://example.com/new-avatar.jpg"
})

post_id = DenormalizedData.create_post("user123", {
    "title": "My Post",
    "content": "Hello world!"
})'''
    },
    {
        "instruction": "Write Python code for aggregation pattern in Firestore",
        "output": '''from firebase_admin import firestore
from typing import Dict, Optional
from datetime import datetime, timezone

class AggregationManager:
    """
    Manage aggregations in Firestore using counters and summaries.

    Patterns:
    - Distributed counters for high-write scenarios
    - Pre-computed aggregations for read performance
    - Time-based aggregations for analytics
    """

    def __init__(self):
        self.db = firestore.client()
        self.num_shards = 10

    # Distributed Counter Pattern
    def increment_counter(self, counter_path: str, amount: int = 1) -> None:
        """Increment a distributed counter."""
        import random

        shard_id = random.randint(0, self.num_shards - 1)
        shard_ref = self.db.collection(f"{counter_path}_shards").document(str(shard_id))

        shard_ref.set({
            "count": firestore.Increment(amount)
        }, merge=True)

    def get_counter_value(self, counter_path: str) -> int:
        """Get total value of distributed counter."""
        shards = self.db.collection(f"{counter_path}_shards").stream()

        total = 0
        for shard in shards:
            total += shard.to_dict().get("count", 0)

        return total

    # Pre-computed Aggregation Pattern
    def update_user_stats(self, user_id: str, event_type: str) -> None:
        """Update pre-computed user statistics."""
        stats_ref = self.db.collection("user_stats").document(user_id)

        updates = {
            f"counts.{event_type}": firestore.Increment(1),
            f"last_{event_type}": firestore.SERVER_TIMESTAMP,
        }

        stats_ref.set(updates, merge=True)

    def get_user_stats(self, user_id: str) -> Dict:
        """Get pre-computed user statistics."""
        stats = self.db.collection("user_stats").document(user_id).get()
        return stats.to_dict() if stats.exists else {}

    # Time-based Aggregation Pattern
    def record_daily_metric(self, metric_name: str, value: float, date: datetime = None) -> None:
        """Record a metric for daily aggregation."""
        date = date or datetime.now(timezone.utc)
        date_str = date.strftime("%Y-%m-%d")

        metric_ref = self.db.collection("daily_metrics").document(f"{metric_name}_{date_str}")

        metric_ref.set({
            "metric": metric_name,
            "date": date_str,
            "sum": firestore.Increment(value),
            "count": firestore.Increment(1),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    def get_daily_metrics(self, metric_name: str, days: int = 30) -> list:
        """Get daily metrics for a time range."""
        from datetime import timedelta

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        metrics = (self.db.collection("daily_metrics")
                  .where("metric", "==", metric_name)
                  .where("date", ">=", start_date.strftime("%Y-%m-%d"))
                  .order_by("date")
                  .stream())

        results = []
        for doc in metrics:
            data = doc.to_dict()
            data["average"] = data["sum"] / data["count"] if data["count"] > 0 else 0
            results.append(data)

        return results

    # Leaderboard Pattern
    def update_leaderboard(self, user_id: str, score: int) -> None:
        """Update user score on leaderboard."""
        # Update user's score
        score_ref = self.db.collection("leaderboard").document(user_id)
        score_ref.set({
            "user_id": user_id,
            "score": score,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

    def get_top_users(self, limit: int = 10) -> list:
        """Get top users from leaderboard."""
        top = (self.db.collection("leaderboard")
              .order_by("score", direction=firestore.Query.DESCENDING)
              .limit(limit)
              .stream())

        return [{"rank": i + 1, **doc.to_dict()} for i, doc in enumerate(top)]

    def get_user_rank(self, user_id: str) -> Optional[int]:
        """Get a user's rank on leaderboard."""
        user_doc = self.db.collection("leaderboard").document(user_id).get()
        if not user_doc.exists:
            return None

        user_score = user_doc.to_dict()["score"]

        # Count users with higher scores
        higher = (self.db.collection("leaderboard")
                 .where("score", ">", user_score)
                 .count().get())

        return higher[0][0].value + 1

# Usage
agg = AggregationManager()

# Distributed counter
agg.increment_counter("page_views/homepage")
views = agg.get_counter_value("page_views/homepage")

# User stats
agg.update_user_stats("user123", "login")
agg.update_user_stats("user123", "post_created")
stats = agg.get_user_stats("user123")

# Daily metrics
agg.record_daily_metric("revenue", 99.99)
metrics = agg.get_daily_metrics("revenue", days=7)

# Leaderboard
agg.update_leaderboard("user123", 1500)
top_10 = agg.get_top_users(10)'''
    },
    # =========================================================================
    # SECURITY RULES EXAMPLES
    # =========================================================================
    {
        "instruction": "Write Firestore security rules for a social media application",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Helper functions
    function isSignedIn() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return request.auth.uid == userId;
    }

    function isAdmin() {
      return request.auth.token.admin == true;
    }

    function hasVerifiedEmail() {
      return request.auth.token.email_verified == true;
    }

    function isValidUserData(data) {
      return data.keys().hasAll(['displayName', 'email'])
        && data.displayName is string
        && data.displayName.size() >= 2
        && data.displayName.size() <= 50
        && data.email == request.auth.token.email;
    }

    // User profiles
    match /users/{userId} {
      // Anyone can read public profiles
      allow read: if true;

      // Users can only write their own profile
      allow create: if isOwner(userId) && isValidUserData(request.resource.data);
      allow update: if isOwner(userId)
        && request.resource.data.email == resource.data.email  // Can't change email
        && request.resource.data.createdAt == resource.data.createdAt;  // Can't change creation date
      allow delete: if isOwner(userId) || isAdmin();

      // User's private settings
      match /settings/{document=**} {
        allow read, write: if isOwner(userId);
      }
    }

    // Posts
    match /posts/{postId} {
      function isPostOwner() {
        return resource.data.authorId == request.auth.uid;
      }

      function isValidPost(data) {
        return data.keys().hasAll(['title', 'content', 'authorId'])
          && data.title is string
          && data.title.size() >= 1
          && data.title.size() <= 200
          && data.content is string
          && data.content.size() <= 10000
          && data.authorId == request.auth.uid;
      }

      // Anyone can read published posts
      allow read: if resource.data.published == true || isPostOwner() || isAdmin();

      // Verified users can create posts
      allow create: if isSignedIn() && hasVerifiedEmail() && isValidPost(request.resource.data);

      // Only author can update their posts
      allow update: if isPostOwner()
        && request.resource.data.authorId == resource.data.authorId;  // Can't change author

      // Author or admin can delete
      allow delete: if isPostOwner() || isAdmin();

      // Comments subcollection
      match /comments/{commentId} {
        function isCommentOwner() {
          return resource.data.authorId == request.auth.uid;
        }

        // Anyone can read comments on published posts
        allow read: if get(/databases/$(database)/documents/posts/$(postId)).data.published == true;

        // Verified users can comment
        allow create: if isSignedIn()
          && hasVerifiedEmail()
          && request.resource.data.authorId == request.auth.uid;

        // Only comment author can update/delete
        allow update, delete: if isCommentOwner();
      }
    }

    // Follow relationships
    match /follows/{followId} {
      // followId format: "{followerId}_{followedId}"
      function getFollowerId() {
        return followId.split('_')[0];
      }

      allow read: if true;
      allow create: if isOwner(getFollowerId());
      allow delete: if isOwner(getFollowerId());
    }

    // Notifications (read-only for users)
    match /notifications/{userId}/{notificationId} {
      allow read: if isOwner(userId);
      allow update: if isOwner(userId)
        && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['read']);
    }
  }
}'''
    },
    {
        "instruction": "Write Firestore security rules for a multi-tenant SaaS application",
        "output": '''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Helper functions
    function isSignedIn() {
      return request.auth != null;
    }

    function getUserData() {
      return get(/databases/$(database)/documents/users/$(request.auth.uid)).data;
    }

    function getTenantMembership(tenantId) {
      return get(/databases/$(database)/documents/tenants/$(tenantId)/members/$(request.auth.uid)).data;
    }

    function isTenantMember(tenantId) {
      return exists(/databases/$(database)/documents/tenants/$(tenantId)/members/$(request.auth.uid));
    }

    function hasTenantRole(tenantId, roles) {
      return isTenantMember(tenantId)
        && getTenantMembership(tenantId).role in roles;
    }

    function isTenantAdmin(tenantId) {
      return hasTenantRole(tenantId, ['admin', 'owner']);
    }

    function isTenantOwner(tenantId) {
      return hasTenantRole(tenantId, ['owner']);
    }

    function isSuperAdmin() {
      return request.auth.token.superAdmin == true;
    }

    // Rate limiting helper
    function isRateLimited() {
      let recentWrites = getAfter(/databases/$(database)/documents/rate_limits/$(request.auth.uid)).data;
      return recentWrites.count > 100;
    }

    // Global users collection
    match /users/{userId} {
      allow read: if isSignedIn();
      allow create: if request.auth.uid == userId;
      allow update: if request.auth.uid == userId
        && !request.resource.data.diff(resource.data).affectedKeys().hasAny(['tenants']);
    }

    // Tenants (organizations)
    match /tenants/{tenantId} {
      // Only members can read tenant info
      allow read: if isTenantMember(tenantId) || isSuperAdmin();

      // Only owner can update tenant settings
      allow update: if isTenantOwner(tenantId)
        && !request.resource.data.diff(resource.data).affectedKeys().hasAny(['createdAt', 'ownerId']);

      // Super admin can delete tenants
      allow delete: if isSuperAdmin();

      // Members subcollection
      match /members/{memberId} {
        // Members can see other members
        allow read: if isTenantMember(tenantId);

        // Admins can add members
        allow create: if isTenantAdmin(tenantId)
          && request.resource.data.role in ['member', 'editor', 'admin']
          && request.resource.data.role != 'owner';  // Can't create another owner

        // Admins can update member roles (but not owners)
        allow update: if isTenantAdmin(tenantId)
          && resource.data.role != 'owner'  // Can't modify owner
          && request.resource.data.role != 'owner';  // Can't promote to owner

        // Members can remove themselves, admins can remove others
        allow delete: if memberId == request.auth.uid
          || (isTenantAdmin(tenantId) && resource.data.role != 'owner');
      }

      // Projects within tenant
      match /projects/{projectId} {
        function isProjectMember() {
          return request.auth.uid in resource.data.memberIds;
        }

        // Tenant members can read projects they're assigned to
        allow read: if isTenantMember(tenantId)
          && (isProjectMember() || isTenantAdmin(tenantId));

        // Editors and above can create projects
        allow create: if hasTenantRole(tenantId, ['editor', 'admin', 'owner'])
          && request.resource.data.tenantId == tenantId;

        // Project members with editor role can update
        allow update: if isProjectMember()
          && hasTenantRole(tenantId, ['editor', 'admin', 'owner'])
          && request.resource.data.tenantId == resource.data.tenantId;  // Can't move to another tenant

        // Only admins can delete projects
        allow delete: if isTenantAdmin(tenantId);

        // Documents within projects
        match /documents/{docId} {
          allow read: if isTenantMember(tenantId)
            && (request.auth.uid in get(/databases/$(database)/documents/tenants/$(tenantId)/projects/$(projectId)).data.memberIds
                || isTenantAdmin(tenantId));

          allow write: if hasTenantRole(tenantId, ['editor', 'admin', 'owner'])
            && request.auth.uid in get(/databases/$(database)/documents/tenants/$(tenantId)/projects/$(projectId)).data.memberIds;
        }
      }

      // Billing (owner only)
      match /billing/{document=**} {
        allow read: if isTenantOwner(tenantId);
        allow write: if false;  // Only via backend
      }
    }

    // Audit logs (read-only)
    match /audit_logs/{tenantId}/{logId} {
      allow read: if isTenantAdmin(tenantId);
      allow write: if false;  // Only via backend
    }
  }
}'''
    },
    # =========================================================================
    # ADDITIONAL CRUD VARIATIONS - PYTHON
    # =========================================================================
    {
        "instruction": "Create a Python function to add a user with validation to Firestore",
        "output": '''from firebase_admin import firestore
import re

db = firestore.client()

def add_user(name: str, email: str, age: int) -> dict:
    """Add a user with validation."""
    # Validate email
    if not re.match(r'^[\\w.-]+@[\\w.-]+\\.\\w+$', email):
        raise ValueError("Invalid email format")

    # Validate age
    if not 0 < age < 150:
        raise ValueError("Age must be between 1 and 149")

    user_data = {
        "name": name.strip(),
        "email": email.lower(),
        "age": age,
        "created_at": firestore.SERVER_TIMESTAMP
    }

    doc_ref = db.collection("users").add(user_data)
    return {"id": doc_ref[1].id, **user_data}'''
    },
    {
        "instruction": "Write Python code to update user email in Firestore with validation",
        "output": '''from firebase_admin import firestore
import re

db = firestore.client()

def update_user_email(user_id: str, new_email: str) -> bool:
    """Update user email with validation."""
    # Validate email format
    if not re.match(r'^[\\w.-]+@[\\w.-]+\\.\\w+$', new_email):
        raise ValueError("Invalid email format")

    # Check if email already exists
    existing = db.collection("users").where("email", "==", new_email.lower()).limit(1).get()
    if list(existing):
        raise ValueError("Email already in use")

    # Update email
    db.collection("users").document(user_id).update({
        "email": new_email.lower(),
        "email_updated_at": firestore.SERVER_TIMESTAMP
    })
    return True'''
    },
    {
        "instruction": "Write Python code to soft delete a document in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def soft_delete(collection: str, doc_id: str) -> bool:
    """Soft delete a document by marking it as deleted."""
    doc_ref = db.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return False

    doc_ref.update({
        "deleted": True,
        "deleted_at": firestore.SERVER_TIMESTAMP
    })
    return True

def restore_deleted(collection: str, doc_id: str) -> bool:
    """Restore a soft-deleted document."""
    doc_ref = db.collection(collection).document(doc_id)
    doc_ref.update({
        "deleted": firestore.DELETE_FIELD,
        "deleted_at": firestore.DELETE_FIELD,
        "restored_at": firestore.SERVER_TIMESTAMP
    })
    return True'''
    },
    {
        "instruction": "Write Python code to get documents with field projection in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def get_users_with_projection(fields: list) -> list:
    """Get users with only specific fields (projection)."""
    # Note: Firestore doesn't support true field projection
    # We fetch all and filter in application
    docs = db.collection("users").stream()

    users = []
    for doc in docs:
        data = doc.to_dict()
        projected = {k: data[k] for k in fields if k in data}
        projected["id"] = doc.id
        users.append(projected)

    return users

# Usage - only get name and email
users = get_users_with_projection(["name", "email"])'''
    },
    {
        "instruction": "Write Python code to upsert a document in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def upsert_document(collection: str, doc_id: str, data: dict) -> dict:
    """Upsert (insert or update) a document."""
    doc_ref = db.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if doc.exists:
        # Update existing
        data["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.update(data)
        return {"action": "updated", "id": doc_id}
    else:
        # Create new
        data["created_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(data)
        return {"action": "created", "id": doc_id}

# Usage
result = upsert_document("products", "prod_123", {"name": "Widget", "price": 9.99})'''
    },
    {
        "instruction": "Write Python code to get a document or create default in Firestore",
        "output": '''from firebase_admin import firestore
from typing import Callable, Dict

db = firestore.client()

def get_or_create(
    collection: str,
    doc_id: str,
    default_factory: Callable[[], Dict]
) -> dict:
    """Get a document or create it with default values."""
    doc_ref = db.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if doc.exists:
        return {"exists": True, "data": doc.to_dict()}

    # Create with defaults
    default_data = default_factory()
    default_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.set(default_data)

    return {"exists": False, "data": default_data}

# Usage
result = get_or_create(
    "user_preferences",
    "user_123",
    lambda: {"theme": "light", "notifications": True, "language": "en"}
)'''
    },
    # =========================================================================
    # ADDITIONAL QUERY VARIATIONS
    # =========================================================================
    {
        "instruction": "Write Python code to query Firestore with text search prefix matching",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def search_by_prefix(collection: str, field: str, prefix: str, limit: int = 20) -> list:
    """Search documents where field starts with prefix."""
    # Firestore prefix search technique
    end = prefix[:-1] + chr(ord(prefix[-1]) + 1)

    query = (db.collection(collection)
             .where(field, ">=", prefix)
             .where(field, "<", end)
             .limit(limit))

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

# Usage - search users whose name starts with "Joh"
results = search_by_prefix("users", "name", "Joh")'''
    },
    {
        "instruction": "Write Python code to query Firestore with NOT equal condition",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def get_active_users() -> list:
    """Get users where status is NOT 'inactive'."""
    # Use 'not-in' for not-equal queries
    query = db.collection("users").where("status", "not-in", ["inactive", "banned", "deleted"])

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

def get_users_without_role() -> list:
    """Get users who don't have admin role."""
    query = db.collection("users").where("role", "!=", "admin")

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]'''
    },
    {
        "instruction": "Write Python code to query Firestore with OR conditions",
        "output": '''from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import Or, FieldFilter

db = firestore.client()

def get_featured_or_popular_posts() -> list:
    """Get posts that are either featured OR have many likes."""
    posts_ref = db.collection("posts")

    # OR query using filters
    or_filter = Or(filters=[
        FieldFilter("featured", "==", True),
        FieldFilter("likes", ">=", 100)
    ])

    query = posts_ref.where(filter=or_filter)

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

def get_users_by_role() -> list:
    """Get users with admin OR moderator role."""
    users_ref = db.collection("users")

    # Alternative: use 'in' for simple OR on same field
    query = users_ref.where("role", "in", ["admin", "moderator"])

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]'''
    },
    {
        "instruction": "Write Python code to query Firestore by document ID range",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def get_documents_in_id_range(
    collection: str,
    start_id: str,
    end_id: str,
    limit: int = 100
) -> list:
    """Get documents with IDs in a specific range."""
    query = (db.collection(collection)
             .order_by("__name__")
             .start_at([start_id])
             .end_at([end_id])
             .limit(limit))

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

def get_documents_after_id(collection: str, last_id: str, limit: int = 100) -> list:
    """Get documents after a specific ID (for pagination)."""
    query = (db.collection(collection)
             .order_by("__name__")
             .start_after([last_id])
             .limit(limit))

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]'''
    },
    {
        "instruction": "Write Python code to query Firestore with composite index",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def get_user_orders(user_id: str, status: str = None, limit: int = 20) -> list:
    """
    Get user orders with composite query.
    Requires composite index: user_id (ASC), created_at (DESC)
    """
    query = db.collection("orders").where("user_id", "==", user_id)

    if status:
        # Requires composite index: user_id (ASC), status (ASC), created_at (DESC)
        query = query.where("status", "==", status)

    query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]

def get_products_by_category_and_price(category: str, min_price: float, max_price: float) -> list:
    """
    Get products filtered by category and price range.
    Requires composite index: category (ASC), price (ASC)
    """
    query = (db.collection("products")
             .where("category", "==", category)
             .where("price", ">=", min_price)
             .where("price", "<=", max_price)
             .order_by("price"))

    return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]'''
    },
    # =========================================================================
    # TYPESCRIPT/JAVASCRIPT VARIATIONS
    # =========================================================================
    {
        "instruction": "Write TypeScript code to add a document to Firestore with validation",
        "output": '''import { collection, addDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase-config';

interface UserData {
  name: string;
  email: string;
  age: number;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
}

function validateUser(data: UserData): ValidationResult {
  const errors: string[] = [];

  if (!data.name || data.name.trim().length < 2) {
    errors.push('Name must be at least 2 characters');
  }

  if (!data.email || !/^[\\w.-]+@[\\w.-]+\\.\\w+$/.test(data.email)) {
    errors.push('Invalid email format');
  }

  if (!data.age || data.age < 1 || data.age > 150) {
    errors.push('Age must be between 1 and 150');
  }

  return { valid: errors.length === 0, errors };
}

async function addUser(userData: UserData): Promise<string> {
  const validation = validateUser(userData);
  if (!validation.valid) {
    throw new Error(validation.errors.join(', '));
  }

  const docRef = await addDoc(collection(db, 'users'), {
    ...userData,
    name: userData.name.trim(),
    email: userData.email.toLowerCase(),
    createdAt: serverTimestamp()
  });

  return docRef.id;
}'''
    },
    {
        "instruction": "Write TypeScript code to update a Firestore document with optimistic locking",
        "output": '''import { doc, getDoc, updateDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase-config';

interface UpdateOptions {
  version: number;
  updates: Record<string, any>;
}

class OptimisticLockError extends Error {
  constructor() {
    super('Document was modified by another process');
    this.name = 'OptimisticLockError';
  }
}

async function updateWithVersion(
  collectionName: string,
  docId: string,
  options: UpdateOptions
): Promise<void> {
  const docRef = doc(db, collectionName, docId);
  const docSnap = await getDoc(docRef);

  if (!docSnap.exists()) {
    throw new Error('Document not found');
  }

  const currentVersion = docSnap.data().version || 0;

  if (currentVersion !== options.version) {
    throw new OptimisticLockError();
  }

  await updateDoc(docRef, {
    ...options.updates,
    version: currentVersion + 1,
    updatedAt: serverTimestamp()
  });
}

// Usage with retry
async function safeUpdate(
  collection: string,
  docId: string,
  updates: Record<string, any>,
  maxRetries: number = 3
): Promise<void> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const docSnap = await getDoc(doc(db, collection, docId));
      const version = docSnap.data()?.version || 0;

      await updateWithVersion(collection, docId, { version, updates });
      return;
    } catch (error) {
      if (error instanceof OptimisticLockError && attempt < maxRetries - 1) {
        await new Promise(r => setTimeout(r, 100 * (attempt + 1)));
        continue;
      }
      throw error;
    }
  }
}'''
    },
    {
        "instruction": "Write TypeScript code to batch write documents to Firestore",
        "output": '''import { writeBatch, doc, collection, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase-config';

interface BatchItem {
  operation: 'set' | 'update' | 'delete';
  collection: string;
  id?: string;
  data?: Record<string, any>;
}

async function executeBatch(items: BatchItem[]): Promise<void> {
  // Firestore batch limit is 500
  const batchSize = 500;

  for (let i = 0; i < items.length; i += batchSize) {
    const batch = writeBatch(db);
    const chunk = items.slice(i, i + batchSize);

    for (const item of chunk) {
      const docRef = item.id
        ? doc(db, item.collection, item.id)
        : doc(collection(db, item.collection));

      switch (item.operation) {
        case 'set':
          batch.set(docRef, {
            ...item.data,
            createdAt: serverTimestamp()
          });
          break;
        case 'update':
          batch.update(docRef, {
            ...item.data,
            updatedAt: serverTimestamp()
          });
          break;
        case 'delete':
          batch.delete(docRef);
          break;
      }
    }

    await batch.commit();
    console.log(`Committed batch ${Math.floor(i / batchSize) + 1}`);
  }
}

// Usage
await executeBatch([
  { operation: 'set', collection: 'users', data: { name: 'Alice' } },
  { operation: 'update', collection: 'users', id: 'user123', data: { status: 'active' } },
  { operation: 'delete', collection: 'users', id: 'oldUser' }
]);'''
    },
    {
        "instruction": "Write TypeScript code to query Firestore with cursor pagination",
        "output": '''import {
  collection,
  query,
  orderBy,
  limit,
  startAfter,
  getDocs,
  DocumentSnapshot,
  QueryDocumentSnapshot
} from 'firebase/firestore';
import { db } from './firebase-config';

interface PaginatedResult<T> {
  items: T[];
  lastDoc: QueryDocumentSnapshot | null;
  hasMore: boolean;
}

async function getPaginatedDocs<T>(
  collectionName: string,
  orderField: string,
  pageSize: number,
  lastDoc?: DocumentSnapshot
): Promise<PaginatedResult<T>> {
  let q = query(
    collection(db, collectionName),
    orderBy(orderField),
    limit(pageSize + 1) // Fetch one extra to check hasMore
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
  })) as T[];

  const newLastDoc = docs.length > 0 ? docs[Math.min(docs.length - 1, pageSize - 1)] : null;

  return { items, lastDoc: newLastDoc, hasMore };
}

// React hook for pagination
function usePaginatedCollection<T>(collectionName: string, orderField: string, pageSize: number) {
  const [items, setItems] = useState<T[]>([]);
  const [lastDoc, setLastDoc] = useState<DocumentSnapshot | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadMore = async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    const result = await getPaginatedDocs<T>(collectionName, orderField, pageSize, lastDoc);

    setItems(prev => [...prev, ...result.items]);
    setLastDoc(result.lastDoc);
    setHasMore(result.hasMore);
    setLoading(false);
  };

  return { items, loadMore, hasMore, loading };
}'''
    },
    {
        "instruction": "Write TypeScript code for Firestore real-time chat room",
        "output": '''import {
  collection,
  addDoc,
  query,
  orderBy,
  limit,
  onSnapshot,
  serverTimestamp,
  Timestamp
} from 'firebase/firestore';
import { db } from './firebase-config';

interface Message {
  id: string;
  text: string;
  userId: string;
  userName: string;
  createdAt: Date;
}

interface ChatRoom {
  roomId: string;
  messages: Message[];
  unsubscribe: () => void;
}

function createChatRoom(
  roomId: string,
  onMessage: (messages: Message[]) => void,
  messageLimit: number = 100
): ChatRoom {
  const messagesRef = collection(db, 'chatRooms', roomId, 'messages');
  const q = query(
    messagesRef,
    orderBy('createdAt', 'desc'),
    limit(messageLimit)
  );

  const messages: Message[] = [];

  const unsubscribe = onSnapshot(q, (snapshot) => {
    snapshot.docChanges().forEach((change) => {
      const data = change.doc.data();
      const message: Message = {
        id: change.doc.id,
        text: data.text,
        userId: data.userId,
        userName: data.userName,
        createdAt: (data.createdAt as Timestamp)?.toDate() || new Date()
      };

      if (change.type === 'added') {
        messages.unshift(message);
      } else if (change.type === 'modified') {
        const index = messages.findIndex(m => m.id === message.id);
        if (index !== -1) messages[index] = message;
      } else if (change.type === 'removed') {
        const index = messages.findIndex(m => m.id === message.id);
        if (index !== -1) messages.splice(index, 1);
      }
    });

    onMessage([...messages]);
  });

  return { roomId, messages, unsubscribe };
}

async function sendMessage(
  roomId: string,
  userId: string,
  userName: string,
  text: string
): Promise<string> {
  const messagesRef = collection(db, 'chatRooms', roomId, 'messages');

  const docRef = await addDoc(messagesRef, {
    text,
    userId,
    userName,
    createdAt: serverTimestamp()
  });

  return docRef.id;
}

// Usage
const room = createChatRoom('room123', (messages) => {
  console.log('Messages updated:', messages);
});

await sendMessage('room123', 'user1', 'Alice', 'Hello!');

// Cleanup
room.unsubscribe();'''
    },
    # =========================================================================
    # CLOUD FUNCTIONS ADDITIONAL EXAMPLES
    # =========================================================================
    {
        "instruction": "Write Python Cloud Function for webhook handling",
        "output": '''from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore
import hashlib
import hmac
import json

initialize_app()

@https_fn.on_request(
    memory=options.MemoryOption.MB_256,
    timeout_sec=30
)
def stripe_webhook(req: https_fn.Request) -> https_fn.Response:
    """Handle Stripe webhook events."""
    # Verify webhook signature
    payload = req.data
    sig_header = req.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        # Verify signature
        timestamp, signature = parse_stripe_signature(sig_header)
        expected_sig = compute_signature(timestamp, payload, webhook_secret)

        if not hmac.compare_digest(expected_sig, signature):
            return https_fn.Response("Invalid signature", status=401)

        # Parse event
        event = json.loads(payload)
        event_type = event["type"]

        db = firestore.client()

        # Handle different event types
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            handle_checkout_completed(db, session)

        elif event_type == "invoice.paid":
            invoice = event["data"]["object"]
            handle_invoice_paid(db, invoice)

        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            handle_subscription_cancelled(db, subscription)

        return https_fn.Response(json.dumps({"received": True}), status=200)

    except Exception as e:
        print(f"Webhook error: {e}")
        return https_fn.Response(str(e), status=400)

def parse_stripe_signature(sig_header: str):
    """Parse Stripe signature header."""
    parts = dict(item.split("=") for item in sig_header.split(","))
    return parts["t"], parts["v1"]

def compute_signature(timestamp: str, payload: bytes, secret: str) -> str:
    """Compute expected Stripe signature."""
    signed_payload = f"{timestamp}.{payload.decode()}"
    return hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()

def handle_checkout_completed(db, session):
    """Handle successful checkout."""
    customer_id = session["customer"]
    subscription_id = session.get("subscription")

    db.collection("customers").document(customer_id).update({
        "subscription_status": "active",
        "subscription_id": subscription_id,
        "updated_at": firestore.SERVER_TIMESTAMP
    })'''
    },
    {
        "instruction": "Write Python Cloud Function for data aggregation on schedule",
        "output": '''from firebase_functions import scheduler_fn, options
from firebase_admin import initialize_app, firestore
from datetime import datetime, timedelta, timezone
from collections import defaultdict

initialize_app()

@scheduler_fn.on_schedule(
    schedule="0 0 * * *",  # Midnight daily
    timezone=scheduler_fn.Timezone("UTC"),
    memory=options.MemoryOption.GB_1,
    timeout_sec=540
)
def daily_analytics_aggregation(event: scheduler_fn.ScheduledEvent) -> None:
    """Aggregate daily analytics data."""
    db = firestore.client()
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    # Get all events from yesterday
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    events = (db.collection("events")
              .where("timestamp", ">=", start)
              .where("timestamp", "<", end)
              .stream())

    # Aggregate by event type and user
    stats = defaultdict(lambda: {"count": 0, "users": set()})
    user_stats = defaultdict(lambda: {"events": 0, "types": set()})

    for event_doc in events:
        data = event_doc.to_dict()
        event_type = data.get("type", "unknown")
        user_id = data.get("user_id")

        stats[event_type]["count"] += 1
        if user_id:
            stats[event_type]["users"].add(user_id)
            user_stats[user_id]["events"] += 1
            user_stats[user_id]["types"].add(event_type)

    # Store aggregated stats
    batch = db.batch()

    # Event type aggregations
    for event_type, data in stats.items():
        ref = db.collection("daily_stats").document(f"{date_str}_{event_type}")
        batch.set(ref, {
            "date": date_str,
            "event_type": event_type,
            "count": data["count"],
            "unique_users": len(data["users"]),
            "created_at": firestore.SERVER_TIMESTAMP
        })

    # Daily summary
    summary_ref = db.collection("daily_summaries").document(date_str)
    batch.set(summary_ref, {
        "date": date_str,
        "total_events": sum(d["count"] for d in stats.values()),
        "unique_users": len(user_stats),
        "event_types": dict((k, v["count"]) for k, v in stats.items()),
        "created_at": firestore.SERVER_TIMESTAMP
    })

    batch.commit()
    print(f"Aggregated {sum(d['count'] for d in stats.values())} events for {date_str}")'''
    },
    {
        "instruction": "Write Python Cloud Function for email notification on Firestore trigger",
        "output": '''from firebase_functions import firestore_fn
from firebase_admin import initialize_app, firestore
import requests

initialize_app()

# Email service configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = "noreply@yourapp.com"

@firestore_fn.on_document_created(document="orders/{orderId}")
def send_order_confirmation(event: firestore_fn.Event[firestore_fn.DocumentSnapshot]) -> None:
    """Send order confirmation email when order is created."""
    order_id = event.params["orderId"]
    order_data = event.data.to_dict()

    db = firestore.client()

    # Get user email
    user_id = order_data.get("user_id")
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        print(f"User not found: {user_id}")
        return

    user_email = user_doc.to_dict().get("email")
    user_name = user_doc.to_dict().get("name", "Customer")

    # Build email content
    items = order_data.get("items", [])
    total = order_data.get("total", 0)

    items_html = "".join([
        "<li>" + item['name'] + " x " + str(item['quantity']) + " - $" + f"{item['price']:.2f}" + "</li>"
        for item in items
    ])

    email_html = """
    <h2>Order Confirmation</h2>
    <p>Hi """ + user_name + """,</p>
    <p>Thank you for your order #""" + order_id + """!</p>
    <h3>Order Details:</h3>
    <ul>""" + items_html + """</ul>
    <p><strong>Total: $""" + f"{total:.2f}" + """</strong></p>
    <p>We'll notify you when your order ships.</p>
    """

    # Send via SendGrid
    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "personalizations": [{"to": [{"email": user_email}]}],
            "from": {"email": FROM_EMAIL},
            "subject": f"Order Confirmation #{order_id}",
            "content": [{"type": "text/html", "value": email_html}]
        }
    )

    if response.status_code == 202:
        # Log success
        db.collection("email_logs").add({
            "type": "order_confirmation",
            "order_id": order_id,
            "user_id": user_id,
            "email": user_email,
            "status": "sent",
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        print(f"Order confirmation sent to {user_email}")
    else:
        print(f"Failed to send email: {response.text}")'''
    },
    # =========================================================================
    # ERROR HANDLING VARIATIONS
    # =========================================================================
    {
        "instruction": "Write Python code for retry logic with Firestore operations",
        "output": '''from firebase_admin import firestore
import time
from functools import wraps
from typing import TypeVar, Callable
import random

T = TypeVar('T')

class FirestoreRetryError(Exception):
    """Raised when all retries are exhausted."""
    pass

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """Decorator for retrying Firestore operations with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_type = type(e).__name__

                    # Check if error is retryable
                    retryable = any(err in str(e).lower() for err in [
                        "deadline exceeded",
                        "unavailable",
                        "resource exhausted",
                        "internal",
                        "aborted"
                    ])

                    if not retryable or attempt == max_retries:
                        raise

                    # Calculate delay with jitter
                    current_delay = min(delay, max_delay)
                    if jitter:
                        current_delay *= (0.5 + random.random())

                    print(f"Retry {attempt + 1}/{max_retries} after {error_type}, waiting {current_delay:.2f}s")
                    time.sleep(current_delay)
                    delay *= exponential_base

            raise FirestoreRetryError(f"Failed after {max_retries} retries") from last_exception
        return wrapper
    return decorator

db = firestore.client()

@with_retry(max_retries=3)
def get_user_with_retry(user_id: str) -> dict:
    """Get user with automatic retry on transient errors."""
    doc = db.collection("users").document(user_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()

@with_retry(max_retries=5, initial_delay=1.0)
def batch_write_with_retry(documents: list) -> int:
    """Batch write with retry logic."""
    batch = db.batch()
    for doc_data in documents:
        ref = db.collection("items").document()
        batch.set(ref, doc_data)
    batch.commit()
    return len(documents)'''
    },
    {
        "instruction": "Write Python code for circuit breaker pattern with Firestore",
        "output": '''from firebase_admin import firestore
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, TypeVar, Optional
import threading

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=30)
    half_open_requests: int = 3

class CircuitBreaker:
    """Circuit breaker for Firestore operations."""

    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.lock = threading.Lock()

    def _should_allow_request(self) -> bool:
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                if datetime.now() - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
                return False

            # HALF_OPEN - allow limited requests
            return self.success_count < self.config.half_open_requests

    def _record_success(self):
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.half_open_requests:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            else:
                self.failure_count = 0

    def _record_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if not self._should_allow_request():
            raise Exception(f"Circuit breaker is {self.state.value}")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

# Usage
db = firestore.client()
circuit_breaker = CircuitBreaker()

def get_user(user_id: str) -> dict:
    return circuit_breaker.execute(
        lambda: db.collection("users").document(user_id).get().to_dict()
    )'''
    },
    # =========================================================================
    # OFFLINE AND PERSISTENCE
    # =========================================================================
    {
        "instruction": "Write TypeScript code to enable Firestore offline persistence",
        "output": '''import {
  initializeFirestore,
  persistentLocalCache,
  persistentMultipleTabManager,
  enableIndexedDbPersistence,
  CACHE_SIZE_UNLIMITED
} from 'firebase/firestore';
import { app } from './firebase-config';

// Modern approach (Firebase v9.8+)
const db = initializeFirestore(app, {
  localCache: persistentLocalCache({
    tabManager: persistentMultipleTabManager(),
    cacheSizeBytes: CACHE_SIZE_UNLIMITED
  })
});

// Check connection status
import { onSnapshot, doc } from 'firebase/firestore';

function setupConnectionListener() {
  const connectedRef = doc(db, '.info/connected');

  return onSnapshot(connectedRef, (snapshot) => {
    const isConnected = snapshot.data()?.connected ?? false;
    console.log(isConnected ? 'Online' : 'Offline');

    // Update UI or handle offline state
    if (!isConnected) {
      showOfflineBanner();
    } else {
      hideOfflineBanner();
    }
  });
}

// Pending writes indicator
import { getDocsFromCache, getDocsFromServer, collection, onSnapshotsInSync } from 'firebase/firestore';

async function getPendingWriteCount(): Promise<number> {
  // This is a simplified approach - actual pending write count
  // requires tracking locally
  return 0;
}

// Force server sync when online
async function syncWithServer(collectionName: string) {
  const colRef = collection(db, collectionName);

  try {
    // Try to get from server
    const serverDocs = await getDocsFromServer(colRef);
    console.log(`Synced ${serverDocs.size} documents from server`);
    return serverDocs;
  } catch (error) {
    // Fall back to cache
    console.log('Failed to sync, using cache');
    return getDocsFromCache(colRef);
  }
}'''
    },
    {
        "instruction": "Write TypeScript code to handle Firestore offline queue",
        "output": '''import {
  collection,
  addDoc,
  serverTimestamp,
  onSnapshot,
  DocumentReference
} from 'firebase/firestore';
import { db } from './firebase-config';

interface QueuedOperation {
  id: string;
  type: 'create' | 'update' | 'delete';
  collection: string;
  docId?: string;
  data?: Record<string, any>;
  timestamp: number;
  status: 'pending' | 'syncing' | 'synced' | 'failed';
  retryCount: number;
}

class OfflineQueue {
  private queue: QueuedOperation[] = [];
  private readonly STORAGE_KEY = 'firestore_offline_queue';
  private isOnline: boolean = navigator.onLine;

  constructor() {
    this.loadFromStorage();
    this.setupNetworkListeners();
  }

  private loadFromStorage(): void {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored) {
      this.queue = JSON.parse(stored);
    }
  }

  private saveToStorage(): void {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.queue));
  }

  private setupNetworkListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processQueue();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  async addOperation(operation: Omit<QueuedOperation, 'id' | 'timestamp' | 'status' | 'retryCount'>): Promise<string> {
    const id = crypto.randomUUID();
    const queuedOp: QueuedOperation = {
      ...operation,
      id,
      timestamp: Date.now(),
      status: 'pending',
      retryCount: 0
    };

    this.queue.push(queuedOp);
    this.saveToStorage();

    if (this.isOnline) {
      await this.processOperation(queuedOp);
    }

    return id;
  }

  private async processQueue(): Promise<void> {
    const pending = this.queue.filter(op => op.status === 'pending' || op.status === 'failed');

    for (const operation of pending) {
      await this.processOperation(operation);
    }

    // Clean up synced operations
    this.queue = this.queue.filter(op => op.status !== 'synced');
    this.saveToStorage();
  }

  private async processOperation(operation: QueuedOperation): Promise<void> {
    operation.status = 'syncing';
    this.saveToStorage();

    try {
      switch (operation.type) {
        case 'create':
          await addDoc(collection(db, operation.collection), {
            ...operation.data,
            createdAt: serverTimestamp(),
            _offlineId: operation.id
          });
          break;
        // Add update and delete handlers
      }

      operation.status = 'synced';
    } catch (error) {
      operation.status = 'failed';
      operation.retryCount++;
      console.error('Failed to sync operation:', error);
    }

    this.saveToStorage();
  }

  getPendingCount(): number {
    return this.queue.filter(op => op.status !== 'synced').length;
  }
}

export const offlineQueue = new OfflineQueue();'''
    },
    # =========================================================================
    # ADMIN SDK OPERATIONS
    # =========================================================================
    {
        "instruction": "Write Python code to list all Firebase users with pagination",
        "output": '''from firebase_admin import auth
from typing import List, Dict, Optional

def list_all_users(page_size: int = 1000) -> List[Dict]:
    """List all Firebase Auth users with pagination."""
    all_users = []
    page_token = None

    while True:
        # Fetch a page of users
        page = auth.list_users(max_results=page_size, page_token=page_token)

        for user in page.users:
            all_users.append({
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "disabled": user.disabled,
                "creation_time": user.user_metadata.creation_timestamp,
                "last_sign_in": user.user_metadata.last_sign_in_timestamp,
                "providers": [p.provider_id for p in user.provider_data],
                "custom_claims": user.custom_claims
            })

        # Check for more pages
        page_token = page.next_page_token
        if not page_token:
            break

    return all_users

def search_users_by_email(email_pattern: str) -> List[Dict]:
    """Search users by email pattern."""
    all_users = list_all_users()
    return [u for u in all_users if email_pattern.lower() in u.get("email", "").lower()]

def get_users_by_custom_claim(claim_name: str, claim_value) -> List[Dict]:
    """Get users with specific custom claim."""
    all_users = list_all_users()
    return [
        u for u in all_users
        if u.get("custom_claims", {}).get(claim_name) == claim_value
    ]

# Usage
all_users = list_all_users()
print(f"Total users: {len(all_users)}")

admins = get_users_by_custom_claim("role", "admin")
print(f"Admin users: {len(admins)}")'''
    },
    {
        "instruction": "Write Python code to export Firestore collection to JSON",
        "output": '''from firebase_admin import firestore
import json
from datetime import datetime
from pathlib import Path
from typing import Any

db = firestore.client()

class FirestoreEncoder(json.JSONEncoder):
    """Custom JSON encoder for Firestore types."""
    def default(self, obj):
        if hasattr(obj, 'timestamp'):  # Firestore Timestamp
            return {"_type": "timestamp", "value": obj.timestamp()}
        if isinstance(obj, datetime):
            return {"_type": "datetime", "value": obj.isoformat()}
        if hasattr(obj, 'path'):  # DocumentReference
            return {"_type": "reference", "path": obj.path}
        return super().default(obj)

def export_collection(
    collection_path: str,
    output_file: str,
    include_subcollections: bool = False
) -> int:
    """Export Firestore collection to JSON file."""
    documents = []
    collection_ref = db.collection(collection_path)

    for doc in collection_ref.stream():
        doc_data = {
            "_id": doc.id,
            "_path": doc.reference.path,
            **doc.to_dict()
        }

        if include_subcollections:
            doc_data["_subcollections"] = export_subcollections(doc.reference)

        documents.append(doc_data)

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "collection": collection_path,
            "exported_at": datetime.now().isoformat(),
            "count": len(documents),
            "documents": documents
        }, f, cls=FirestoreEncoder, indent=2)

    return len(documents)

def export_subcollections(doc_ref) -> dict:
    """Export all subcollections of a document."""
    subcollections = {}

    for subcol in doc_ref.collections():
        subcollections[subcol.id] = []
        for subdoc in subcol.stream():
            subcollections[subcol.id].append({
                "_id": subdoc.id,
                **subdoc.to_dict()
            })

    return subcollections

# Usage
count = export_collection("users", "./exports/users.json", include_subcollections=True)
print(f"Exported {count} documents")'''
    },
    {
        "instruction": "Write Python code to import JSON data to Firestore",
        "output": '''from firebase_admin import firestore
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

db = firestore.client()

def restore_firestore_types(obj: Any) -> Any:
    """Restore Firestore types from JSON."""
    if isinstance(obj, dict):
        if obj.get("_type") == "timestamp":
            return datetime.fromtimestamp(obj["value"])
        if obj.get("_type") == "datetime":
            return datetime.fromisoformat(obj["value"])
        if obj.get("_type") == "reference":
            return db.document(obj["path"])
        return {k: restore_firestore_types(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [restore_firestore_types(item) for item in obj]
    return obj

def import_collection(
    input_file: str,
    collection_path: str = None,
    merge: bool = False,
    dry_run: bool = False
) -> Dict[str, int]:
    """Import JSON data to Firestore collection."""
    with open(input_file) as f:
        data = json.load(f)

    collection_path = collection_path or data.get("collection")
    if not collection_path:
        raise ValueError("Collection path not specified")

    documents = data.get("documents", [])
    stats = {"created": 0, "updated": 0, "skipped": 0}

    batch = db.batch()
    batch_count = 0

    for doc_data in documents:
        doc_id = doc_data.get("_id")
        if not doc_id:
            stats["skipped"] += 1
            continue

        # Remove internal fields and restore types
        clean_data = restore_firestore_types(doc_data)
        clean_data["imported_at"] = firestore.SERVER_TIMESTAMP

        doc_ref = db.collection(collection_path).document(doc_id)

        if dry_run:
            print(f"Would {'merge' if merge else 'set'}: {doc_ref.path}")
            stats["created"] += 1
            continue

        if merge:
            batch.set(doc_ref, clean_data, merge=True)
        else:
            batch.set(doc_ref, clean_data)

        batch_count += 1
        stats["created"] += 1

        # Commit in batches of 500
        if batch_count >= 500:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0 and not dry_run:
        batch.commit()

    return stats

# Usage
stats = import_collection("./exports/users.json", merge=True)
print(f"Import complete: {stats}")'''
    },
    # =========================================================================
    # ADDITIONAL VARIATIONS FOR DIVERSITY
    # =========================================================================
    {
        "instruction": "Write Python code to create a Firestore document with nested data",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def create_order(user_id: str, items: list, shipping_address: dict) -> str:
    """Create an order with nested data structure."""
    order_data = {
        "user_id": user_id,
        "status": "pending",
        "items": [
            {
                "product_id": item["product_id"],
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "subtotal": item["quantity"] * item["price"]
            }
            for item in items
        ],
        "shipping": {
            "address": {
                "street": shipping_address["street"],
                "city": shipping_address["city"],
                "state": shipping_address["state"],
                "zip": shipping_address["zip"],
                "country": shipping_address.get("country", "US")
            },
            "method": shipping_address.get("method", "standard"),
            "tracking": None
        },
        "totals": {
            "subtotal": sum(item["quantity"] * item["price"] for item in items),
            "shipping": 5.99,
            "tax": 0,  # Calculate based on location
            "total": 0  # Will be calculated
        },
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }

    # Calculate total
    order_data["totals"]["total"] = (
        order_data["totals"]["subtotal"] +
        order_data["totals"]["shipping"] +
        order_data["totals"]["tax"]
    )

    doc_ref = db.collection("orders").add(order_data)
    return doc_ref[1].id'''
    },
    {
        "instruction": "Write Python code to update nested fields in Firestore",
        "output": '''from firebase_admin import firestore

db = firestore.client()

def update_shipping_status(order_id: str, tracking_number: str, carrier: str) -> bool:
    """Update nested shipping information."""
    order_ref = db.collection("orders").document(order_id)

    # Use dot notation for nested field updates
    order_ref.update({
        "shipping.tracking": tracking_number,
        "shipping.carrier": carrier,
        "shipping.shipped_at": firestore.SERVER_TIMESTAMP,
        "status": "shipped",
        "updated_at": firestore.SERVER_TIMESTAMP
    })

    return True

def update_item_quantity(order_id: str, item_index: int, new_quantity: int) -> bool:
    """Update quantity of a specific item in order."""
    order_ref = db.collection("orders").document(order_id)
    order_doc = order_ref.get()

    if not order_doc.exists:
        return False

    order_data = order_doc.to_dict()
    items = order_data.get("items", [])

    if item_index >= len(items):
        return False

    # Update specific item
    items[item_index]["quantity"] = new_quantity
    items[item_index]["subtotal"] = new_quantity * items[item_index]["price"]

    # Recalculate totals
    new_subtotal = sum(item["subtotal"] for item in items)

    order_ref.update({
        "items": items,
        "totals.subtotal": new_subtotal,
        "totals.total": new_subtotal + order_data["totals"]["shipping"] + order_data["totals"]["tax"],
        "updated_at": firestore.SERVER_TIMESTAMP
    })

    return True'''
    },
    {
        "instruction": "Write Python code to query Firestore with geolocation",
        "output": '''from firebase_admin import firestore
from typing import List, Dict
import math

db = firestore.client()

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers."""
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def find_nearby_stores(
    lat: float,
    lon: float,
    radius_km: float,
    limit: int = 20
) -> List[Dict]:
    """Find stores within a radius of a location."""
    # Approximate bounding box for initial query
    lat_delta = radius_km / 111.0  # ~111km per degree of latitude
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

    # Query within bounding box
    stores_ref = db.collection("stores")
    query = (stores_ref
             .where("location.lat", ">=", lat - lat_delta)
             .where("location.lat", "<=", lat + lat_delta))

    stores = []
    for doc in query.stream():
        store = doc.to_dict()
        store["id"] = doc.id

        # Calculate exact distance
        store_lat = store["location"]["lat"]
        store_lon = store["location"]["lon"]
        distance = haversine_distance(lat, lon, store_lat, store_lon)

        # Filter by exact distance
        if distance <= radius_km:
            store["distance_km"] = round(distance, 2)
            stores.append(store)

    # Sort by distance and limit
    stores.sort(key=lambda x: x["distance_km"])
    return stores[:limit]

# Store location data
def save_store_location(store_id: str, lat: float, lon: float) -> None:
    """Save store with geolocation."""
    db.collection("stores").document(store_id).set({
        "location": {
            "lat": lat,
            "lon": lon,
            "geohash": compute_geohash(lat, lon)  # Optional for better queries
        }
    }, merge=True)'''
    },
    {
        "instruction": "Write Python code to implement full-text search with Firestore",
        "output": '''from firebase_admin import firestore
from typing import List, Dict
import re

db = firestore.client()

def create_search_index(text: str) -> List[str]:
    """Create search index tokens from text."""
    # Normalize text
    text = text.lower()
    text = re.sub(r'[^a-z0-9\\s]', '', text)

    # Split into words
    words = text.split()

    # Create prefix tokens for autocomplete
    tokens = set()
    for word in words:
        tokens.add(word)
        # Add prefixes for autocomplete (min 2 chars)
        for i in range(2, len(word) + 1):
            tokens.add(word[:i])

    return list(tokens)

def save_searchable_document(collection: str, doc_id: str, data: dict, search_fields: List[str]) -> None:
    """Save document with search index."""
    # Build search text from specified fields
    search_text = " ".join(str(data.get(field, "")) for field in search_fields)

    # Create search index
    data["_search_tokens"] = create_search_index(search_text)

    db.collection(collection).document(doc_id).set(data)

def search_documents(
    collection: str,
    query: str,
    limit: int = 20
) -> List[Dict]:
    """Search documents by query."""
    # Normalize query
    query_tokens = query.lower().split()

    if not query_tokens:
        return []

    # Search using first token (Firestore limitation)
    primary_token = query_tokens[0]

    results_ref = (db.collection(collection)
                   .where("_search_tokens", "array_contains", primary_token)
                   .limit(limit * 2))  # Fetch extra for client-side filtering

    results = []
    for doc in results_ref.stream():
        data = doc.to_dict()
        tokens = set(data.get("_search_tokens", []))

        # Check if all query tokens match
        if all(any(t.startswith(qt) for t in tokens) for qt in query_tokens):
            data["id"] = doc.id
            del data["_search_tokens"]  # Remove internal field
            results.append(data)

    return results[:limit]

# Usage
save_searchable_document("products", "prod_1", {
    "name": "Apple iPhone 15 Pro",
    "description": "Latest smartphone with advanced features",
    "price": 999
}, search_fields=["name", "description"])

results = search_documents("products", "iphone pro")'''
    },
    {
        "instruction": "Write Python code for Firestore document versioning",
        "output": '''from firebase_admin import firestore
from typing import Dict, Optional, List
from datetime import datetime

db = firestore.client()

class VersionedDocument:
    """Manage document versions in Firestore."""

    def __init__(self, collection: str):
        self.collection = collection
        self.versions_subcollection = "versions"

    def save(self, doc_id: str, data: Dict, user_id: str = None) -> int:
        """Save document and create version."""
        doc_ref = db.collection(self.collection).document(doc_id)
        doc = doc_ref.get()

        # Get current version number
        current_version = 0
        if doc.exists:
            current_version = doc.to_dict().get("_version", 0)

        new_version = current_version + 1

        # Create version entry
        version_data = {
            "version": new_version,
            "data": data,
            "created_at": firestore.SERVER_TIMESTAMP,
            "created_by": user_id
        }

        # Save current state to versions subcollection
        if doc.exists:
            old_data = doc.to_dict()
            del old_data["_version"]
            del old_data["_updated_at"]
            doc_ref.collection(self.versions_subcollection).document(str(current_version)).set({
                "version": current_version,
                "data": old_data,
                "created_at": firestore.SERVER_TIMESTAMP
            })

        # Update main document
        data["_version"] = new_version
        data["_updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(data)

        return new_version

    def get_version(self, doc_id: str, version: int) -> Optional[Dict]:
        """Get a specific version of a document."""
        if version == 0:
            return None

        # Check if it's the current version
        doc_ref = db.collection(self.collection).document(doc_id)
        doc = doc_ref.get()

        if doc.exists and doc.to_dict().get("_version") == version:
            data = doc.to_dict()
            del data["_version"]
            del data["_updated_at"]
            return data

        # Get from versions subcollection
        version_doc = doc_ref.collection(self.versions_subcollection).document(str(version)).get()
        if version_doc.exists:
            return version_doc.to_dict().get("data")

        return None

    def list_versions(self, doc_id: str) -> List[Dict]:
        """List all versions of a document."""
        doc_ref = db.collection(self.collection).document(doc_id)
        versions = []

        # Get versions from subcollection
        for version_doc in doc_ref.collection(self.versions_subcollection).order_by("version").stream():
            v = version_doc.to_dict()
            versions.append({
                "version": v["version"],
                "created_at": v.get("created_at"),
                "created_by": v.get("created_by")
            })

        # Add current version
        doc = doc_ref.get()
        if doc.exists:
            versions.append({
                "version": doc.to_dict().get("_version"),
                "created_at": doc.to_dict().get("_updated_at"),
                "current": True
            })

        return versions

    def restore_version(self, doc_id: str, version: int, user_id: str = None) -> int:
        """Restore a document to a specific version."""
        old_data = self.get_version(doc_id, version)
        if old_data is None:
            raise ValueError(f"Version {version} not found")

        return self.save(doc_id, old_data, user_id)

# Usage
versioned = VersionedDocument("documents")
version = versioned.save("doc_1", {"title": "Hello", "content": "World"}, "user_123")
versions = versioned.list_versions("doc_1")'''
    },
    {
        "instruction": "Write Python code for Firestore rate limiting",
        "output": '''from firebase_admin import firestore
from datetime import datetime, timedelta
from typing import Tuple

db = firestore.client()

class RateLimiter:
    """Token bucket rate limiter using Firestore."""

    def __init__(
        self,
        collection: str = "rate_limits",
        max_tokens: int = 100,
        refill_rate: float = 10.0,  # tokens per second
        refill_interval: float = 1.0  # seconds
    ):
        self.collection = collection
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval

    def check_rate_limit(self, key: str, tokens_needed: int = 1) -> Tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.

        Returns (allowed, info) tuple.
        """
        doc_ref = db.collection(self.collection).document(key)

        @firestore.transactional
        def update_in_transaction(transaction):
            doc = doc_ref.get(transaction=transaction)
            now = datetime.now()

            if doc.exists:
                data = doc.to_dict()
                tokens = data.get("tokens", self.max_tokens)
                last_update = data.get("last_update").replace(tzinfo=None)

                # Calculate refilled tokens
                elapsed = (now - last_update).total_seconds()
                refilled = elapsed * self.refill_rate
                tokens = min(self.max_tokens, tokens + refilled)
            else:
                tokens = self.max_tokens
                last_update = now

            # Check if enough tokens
            if tokens >= tokens_needed:
                new_tokens = tokens - tokens_needed
                allowed = True
            else:
                new_tokens = tokens
                allowed = False

            # Update rate limit document
            transaction.set(doc_ref, {
                "tokens": new_tokens,
                "last_update": now,
                "key": key
            })

            return allowed, {
                "allowed": allowed,
                "remaining": int(new_tokens),
                "reset_at": now + timedelta(seconds=(self.max_tokens - new_tokens) / self.refill_rate)
            }

        transaction = db.transaction()
        return update_in_transaction(transaction)

    def get_limit_info(self, key: str) -> dict:
        """Get current rate limit info without consuming tokens."""
        doc = db.collection(self.collection).document(key).get()

        if not doc.exists:
            return {"remaining": self.max_tokens, "max": self.max_tokens}

        data = doc.to_dict()
        now = datetime.now()
        last_update = data.get("last_update").replace(tzinfo=None)

        elapsed = (now - last_update).total_seconds()
        refilled = elapsed * self.refill_rate
        tokens = min(self.max_tokens, data.get("tokens", 0) + refilled)

        return {
            "remaining": int(tokens),
            "max": self.max_tokens,
            "reset_at": now + timedelta(seconds=(self.max_tokens - tokens) / self.refill_rate)
        }

# Usage
limiter = RateLimiter(max_tokens=100, refill_rate=10)

# Check rate limit for user
allowed, info = limiter.check_rate_limit(f"user:{user_id}")
if not allowed:
    raise Exception(f"Rate limited. Try again at {info['reset_at']}")'''
    },
]

def generate_variations(base_examples: List[Dict]) -> List[Dict]:
    """Generate variations of base examples to expand training data."""
    variations = []

    # Instruction variations
    instruction_prefixes_py = [
        ("Write Python code to ", "Create Python code that "),
        ("Write Python code to ", "Implement Python code for "),
        ("Write Python code to ", "Show me how to "),
        ("Write Python code to ", "Write a Python function to "),
        ("Write Python code for ", "Create Python code for "),
        ("Write Python code for ", "Implement Python code for "),
    ]

    instruction_prefixes_ts = [
        ("Write TypeScript code to ", "Create TypeScript code that "),
        ("Write TypeScript code to ", "Implement TypeScript code for "),
        ("Write TypeScript code for ", "Create TypeScript code for "),
    ]

    # Collection name variations
    collection_variations = [
        ("users", "customers"),
        ("users", "members"),
        ("users", "accounts"),
        ("products", "items"),
        ("products", "goods"),
        ("orders", "purchases"),
        ("orders", "transactions"),
        ("posts", "articles"),
        ("posts", "entries"),
        ("comments", "replies"),
        ("comments", "feedback"),
    ]

    # Field name variations
    field_variations = [
        ("name", "title"),
        ("email", "username"),
        ("status", "state"),
        ("created_at", "createdAt"),
        ("user_id", "userId"),
    ]

    for example in base_examples:
        instruction = example["instruction"]
        output = example["output"]

        # Create variations with different instruction phrasings
        for old_prefix, new_prefix in instruction_prefixes_py:
            if instruction.startswith(old_prefix):
                new_instruction = new_prefix + instruction[len(old_prefix):]
                if new_instruction != instruction:
                    variations.append({"instruction": new_instruction, "output": output})

        for old_prefix, new_prefix in instruction_prefixes_ts:
            if instruction.startswith(old_prefix):
                new_instruction = new_prefix + instruction[len(old_prefix):]
                if new_instruction != instruction:
                    variations.append({"instruction": new_instruction, "output": output})

        # Create variations with different collection names
        for old_col, new_col in collection_variations:
            if old_col in instruction:
                new_instruction = instruction.replace(old_col, new_col)
                new_output = output.replace(f"'{old_col}'", f"'{new_col}'").replace(f'"{old_col}"', f'"{new_col}"')
                if new_instruction != instruction:
                    variations.append({"instruction": new_instruction, "output": new_output})

        # Create variations with different field names
        for old_field, new_field in field_variations[:3]:
            if old_field in instruction and old_field in output:
                new_instruction = instruction.replace(old_field, new_field)
                new_output = output.replace(old_field, new_field)
                if new_instruction != instruction:
                    variations.append({"instruction": new_instruction, "output": new_output})

    return variations

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

    # Generate variations to expand training data
    variations = generate_variations(ALL_EXAMPLES)
    all_examples = ALL_EXAMPLES + variations

    # Remove duplicates based on instruction
    seen = set()
    unique_examples = []
    for ex in all_examples:
        if ex["instruction"] not in seen:
            seen.add(ex["instruction"])
            unique_examples.append(ex)

    examples = format_examples(unique_examples)
    print(f"Total examples: {len(examples)}")

    # Split into train/valid (90/10)
    random.shuffle(examples)
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    output_dir = Path(__file__).resolve().parent.parent / "data" / "firebase"
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
