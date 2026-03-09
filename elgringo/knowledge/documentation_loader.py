"""
Documentation Loader for RAG System
====================================

Loads and parses documentation from various sources:
- Local markdown/text files
- Cached documentation bundles
- Code docstrings and comments

Usage:
    loader = DocumentationLoader()

    # Load local documentation
    docs = loader.load_markdown_file("/path/to/README.md")

    # Load from a documentation bundle
    docs = loader.load_documentation_bundle("firebase")

    # Extract docstrings from Python files
    docs = loader.extract_docstrings("/path/to/module.py")
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of documentation content."""
    content: str
    title: str
    source: str
    chunk_type: str  # section, function, class, example, etc.
    language: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MarkdownParser:
    """Parse markdown documents into chunks."""

    def __init__(self, chunk_size: int = 1500):
        self.chunk_size = chunk_size

    def parse(self, content: str, source: str) -> List[DocumentChunk]:
        """Parse markdown content into document chunks."""
        chunks = []

        # Split by headers
        sections = self._split_by_headers(content)

        for title, section_content in sections:
            # Extract code blocks
            code_blocks = self._extract_code_blocks(section_content)

            # Create chunk for the section text
            text_content = self._remove_code_blocks(section_content)
            if text_content.strip():
                chunks.append(DocumentChunk(
                    content=text_content.strip(),
                    title=title,
                    source=source,
                    chunk_type="section",
                ))

            # Create chunks for code examples
            for lang, code in code_blocks:
                chunks.append(DocumentChunk(
                    content=code,
                    title=f"{title} - Code Example",
                    source=source,
                    chunk_type="example",
                    language=lang,
                    tags=["code", "example"],
                ))

        return chunks

    def _split_by_headers(self, content: str) -> List[Tuple[str, str]]:
        """Split markdown by headers."""
        # Match headers (# ## ### etc.)
        pattern = r'^(#{1,6})\s+(.+)$'
        lines = content.split('\n')

        sections = []
        current_title = "Introduction"
        current_content = []

        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Save previous section
                if current_content:
                    sections.append((current_title, '\n'.join(current_content)))
                current_title = match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections.append((current_title, '\n'.join(current_content)))

        return sections

    def _extract_code_blocks(self, content: str) -> List[Tuple[str, str]]:
        """Extract code blocks from markdown."""
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        return [(lang or 'text', code.strip()) for lang, code in matches]

    def _remove_code_blocks(self, content: str) -> str:
        """Remove code blocks from content."""
        pattern = r'```\w*\n.*?```'
        return re.sub(pattern, '[code example]', content, flags=re.DOTALL)


class PythonDocstringExtractor:
    """Extract docstrings from Python source files."""

    def extract(self, file_path: str) -> List[DocumentChunk]:
        """Extract docstrings from a Python file."""
        chunks = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            file_name = Path(file_path).name

            # Module docstring
            module_doc = ast.get_docstring(tree)
            if module_doc:
                chunks.append(DocumentChunk(
                    content=module_doc,
                    title=f"Module: {file_name}",
                    source=file_path,
                    chunk_type="module",
                    language="python",
                ))

            # Walk through classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_doc = ast.get_docstring(node)
                    if class_doc:
                        chunks.append(DocumentChunk(
                            content=class_doc,
                            title=f"Class: {node.name}",
                            source=file_path,
                            chunk_type="class",
                            language="python",
                            tags=["class", node.name.lower()],
                        ))

                    # Extract method docstrings
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_doc = ast.get_docstring(item)
                            if method_doc:
                                chunks.append(DocumentChunk(
                                    content=method_doc,
                                    title=f"Method: {node.name}.{item.name}",
                                    source=file_path,
                                    chunk_type="method",
                                    language="python",
                                    tags=["method", item.name.lower()],
                                ))

                elif isinstance(node, ast.FunctionDef):
                    # Top-level function
                    if node.col_offset == 0:  # Only top-level
                        func_doc = ast.get_docstring(node)
                        if func_doc:
                            chunks.append(DocumentChunk(
                                content=func_doc,
                                title=f"Function: {node.name}",
                                source=file_path,
                                chunk_type="function",
                                language="python",
                                tags=["function", node.name.lower()],
                            ))

        except Exception as e:
            logger.warning(f"Error extracting docstrings from {file_path}: {e}")

        return chunks


class TypeScriptDocExtractor:
    """Extract JSDoc comments from TypeScript/JavaScript files."""

    def extract(self, file_path: str) -> List[DocumentChunk]:
        """Extract JSDoc comments from a TypeScript/JavaScript file."""
        chunks = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            Path(file_path).name

            # Match JSDoc comments
            jsdoc_pattern = r'/\*\*\s*(.*?)\s*\*/\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var|interface|type)\s+(\w+)'
            matches = re.findall(jsdoc_pattern, content, re.DOTALL)

            for doc, name in matches:
                # Clean up the doc comment
                doc = re.sub(r'\n\s*\*\s*', '\n', doc)
                doc = doc.strip()

                if doc:
                    # Determine type from doc content
                    chunk_type = "function"
                    if "@class" in doc or "class " in content[content.find(name):content.find(name)+50]:
                        chunk_type = "class"
                    elif "@interface" in doc:
                        chunk_type = "interface"

                    chunks.append(DocumentChunk(
                        content=doc,
                        title=f"{chunk_type.title()}: {name}",
                        source=file_path,
                        chunk_type=chunk_type,
                        language="typescript",
                        tags=[chunk_type, name.lower()],
                    ))

        except Exception as e:
            logger.warning(f"Error extracting docs from {file_path}: {e}")

        return chunks


class DocumentationLoader:
    """
    Main documentation loader that coordinates various parsers.
    """

    # Built-in documentation bundles
    DOCUMENTATION_BUNDLES = {
        "firebase": {
            "title": "Firebase Documentation",
            "topics": [
                ("Firebase Admin SDK", """
The Firebase Admin SDK lets you interact with Firebase from privileged environments.

## Initialization
```python
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
```

## Key Features
- Firestore database operations (CRUD, queries, transactions)
- Firebase Authentication management
- Cloud Storage file operations
- Cloud Messaging for notifications
- Realtime Database access
"""),
                ("Firestore Operations", """
## Adding Documents
```python
# Auto-generated ID
doc_ref = db.collection('users').add({'name': 'Alice'})

# Specific ID
db.collection('users').document('user_id').set({'name': 'Alice'})
```

## Reading Documents
```python
doc = db.collection('users').document('user_id').get()
if doc.exists:
    data = doc.to_dict()
```

## Querying
```python
query = db.collection('users').where('age', '>=', 18).limit(10)
docs = query.stream()
```

## Transactions
```python
@firestore.transactional
def update_in_transaction(transaction, doc_ref):
    doc = doc_ref.get(transaction=transaction)
    transaction.update(doc_ref, {'count': doc.get('count') + 1})
```
"""),
                ("Security Rules", """
## Firestore Security Rules

Rules control access to your database.

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth.uid == userId;
    }
  }
}
```

### Common Patterns
- `request.auth` - The authenticated user
- `resource.data` - The document being accessed
- `request.resource.data` - The incoming data (for writes)
"""),
            ],
        },
        "react": {
            "title": "React Documentation",
            "topics": [
                ("React Hooks", """
## useState
```jsx
const [count, setCount] = useState(0);
```

## useEffect
```jsx
useEffect(() => {
  // Side effect code
  return () => {
    // Cleanup
  };
}, [dependencies]);
```

## useCallback
```jsx
const memoizedCallback = useCallback(() => {
  doSomething(a, b);
}, [a, b]);
```

## useMemo
```jsx
const memoizedValue = useMemo(() => computeExpensive(a, b), [a, b]);
```
"""),
                ("React Patterns", """
## Component Composition
Prefer composition over inheritance.

## Render Props
```jsx
<DataProvider render={data => <Component data={data} />} />
```

## Higher-Order Components
```jsx
const EnhancedComponent = withFeature(BaseComponent);
```

## Custom Hooks
Extract reusable logic into custom hooks:
```jsx
function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}
```
"""),
            ],
        },
        "python": {
            "title": "Python Best Practices",
            "topics": [
                ("Python Async", """
## Async/Await Basics
```python
import asyncio

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Run async function
result = asyncio.run(fetch_data('https://api.example.com'))
```

## Concurrent Execution
```python
async def main():
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

## Error Handling
```python
async def safe_fetch(url):
    try:
        return await fetch_data(url)
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None
```
"""),
                ("Python Type Hints", """
## Basic Types
```python
def greet(name: str) -> str:
    return f"Hello, {name}"

def process(items: list[int]) -> dict[str, int]:
    return {"sum": sum(items), "count": len(items)}
```

## Optional and Union
```python
from typing import Optional, Union

def find_user(id: int) -> Optional[User]:
    ...

def parse(value: Union[str, int]) -> str:
    ...
```

## Generics
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def get(self, id: str) -> T: ...
    def save(self, item: T) -> None: ...
```
"""),
            ],
        },
    }

    def __init__(self, cache_dir: str = "~/.ai-dev-team/docs_cache"):
        self.cache_dir = Path(os.path.expanduser(cache_dir))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._markdown_parser = MarkdownParser()
        self._python_extractor = PythonDocstringExtractor()
        self._typescript_extractor = TypeScriptDocExtractor()

    def load_markdown_file(self, file_path: str) -> List[DocumentChunk]:
        """Load and parse a markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._markdown_parser.parse(content, file_path)
        except Exception as e:
            logger.error(f"Error loading markdown {file_path}: {e}")
            return []

    def load_documentation_bundle(self, bundle_name: str) -> List[DocumentChunk]:
        """Load a built-in documentation bundle."""
        bundle = self.DOCUMENTATION_BUNDLES.get(bundle_name.lower())
        if not bundle:
            logger.warning(f"Unknown documentation bundle: {bundle_name}")
            return []

        chunks = []
        for title, content in bundle["topics"]:
            topic_chunks = self._markdown_parser.parse(content, f"bundle:{bundle_name}")
            for chunk in topic_chunks:
                chunk.title = f"{bundle['title']} - {title}: {chunk.title}"
                chunk.tags.append(bundle_name.lower())
            chunks.extend(topic_chunks)

        logger.info(f"Loaded {len(chunks)} chunks from {bundle_name} bundle")
        return chunks

    def extract_from_source_file(self, file_path: str) -> List[DocumentChunk]:
        """Extract documentation from a source file based on its type."""
        ext = Path(file_path).suffix.lower()

        if ext == '.py':
            return self._python_extractor.extract(file_path)
        elif ext in ['.ts', '.tsx', '.js', '.jsx']:
            return self._typescript_extractor.extract(file_path)
        elif ext in ['.md', '.markdown']:
            return self.load_markdown_file(file_path)
        else:
            logger.debug(f"No extractor for {ext} files")
            return []

    def load_project_documentation(
        self,
        project_path: str,
        include_source_docs: bool = True,
    ) -> List[DocumentChunk]:
        """Load all documentation from a project."""
        project_path = Path(project_path)
        chunks = []

        # Load README files
        for readme in project_path.glob("**/README*"):
            if "node_modules" in str(readme) or ".git" in str(readme):
                continue
            chunks.extend(self.load_markdown_file(str(readme)))

        # Load docs folder
        docs_dir = project_path / "docs"
        if docs_dir.exists():
            for md_file in docs_dir.rglob("*.md"):
                chunks.extend(self.load_markdown_file(str(md_file)))

        # Extract source documentation
        if include_source_docs:
            for py_file in project_path.rglob("*.py"):
                if "node_modules" in str(py_file) or ".git" in str(py_file):
                    continue
                if "__pycache__" in str(py_file) or "venv" in str(py_file):
                    continue
                chunks.extend(self._python_extractor.extract(str(py_file)))

            for ts_file in project_path.rglob("*.ts"):
                if "node_modules" in str(ts_file) or ".git" in str(ts_file):
                    continue
                chunks.extend(self._typescript_extractor.extract(str(ts_file)))

        logger.info(f"Loaded {len(chunks)} documentation chunks from {project_path}")
        return chunks

    def get_available_bundles(self) -> List[str]:
        """Get list of available documentation bundles."""
        return list(self.DOCUMENTATION_BUNDLES.keys())


def get_documentation_loader() -> DocumentationLoader:
    """Get documentation loader instance."""
    return DocumentationLoader()
