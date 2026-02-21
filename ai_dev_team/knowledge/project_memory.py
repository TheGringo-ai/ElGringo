"""
Project Memory System
=====================

Manages project indexing, memory, and RAG integration.
Allows users to:
- Add projects to memory
- Search across project files
- Store project-specific learnings
- Delete projects and their data
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)

# File extensions to index
INDEXABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.scss',
    '.json', '.yaml', '.yml', '.md', '.txt', '.sql', '.sh',
    '.go', '.rs', '.java', '.kt', '.swift', '.c', '.cpp', '.h',
    '.vue', '.svelte', '.php', '.rb', '.ex', '.exs'
}

# Directories to skip
SKIP_DIRS = {
    'node_modules', 'venv', '.venv', '__pycache__', '.git', '.svn',
    'dist', 'build', '.next', '.nuxt', 'coverage', '.pytest_cache',
    '.mypy_cache', '.tox', 'eggs', '*.egg-info', '.eggs'
}

# Storage paths
STORAGE_DIR = Path.home() / '.ai-dev-team' / 'projects'
PROJECTS_INDEX = STORAGE_DIR / 'projects.json'
ARCHIVE_DIR = STORAGE_DIR / 'archive'


@dataclass
class ProjectFile:
    """Represents an indexed file in a project."""
    path: str  # Relative path within project
    language: str
    size: int
    last_modified: str
    content_hash: str
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProjectMemory:
    """Stores learnings and patterns specific to a project."""
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    error_fixes: List[Dict[str, Any]] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    architecture_notes: List[str] = field(default_factory=list)
    conversations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Project:
    """Represents a tracked project."""
    id: str
    name: str
    path: str
    description: str = ""
    technologies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    file_count: int = 0
    total_size: int = 0
    is_active: bool = True
    files: List[ProjectFile] = field(default_factory=list)
    memory: ProjectMemory = field(default_factory=ProjectMemory)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage."""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'description': self.description,
            'technologies': self.technologies,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'file_count': self.file_count,
            'total_size': self.total_size,
            'is_active': self.is_active,
            'files': [asdict(f) for f in self.files],
            'memory': asdict(self.memory)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        """Create from dictionary."""
        files = [ProjectFile(**f) for f in data.get('files', [])]
        memory_data = data.get('memory', {})
        memory = ProjectMemory(
            patterns=memory_data.get('patterns', []),
            error_fixes=memory_data.get('error_fixes', []),
            lessons=memory_data.get('lessons', []),
            architecture_notes=memory_data.get('architecture_notes', []),
            conversations=memory_data.get('conversations', [])
        )
        return cls(
            id=data['id'],
            name=data['name'],
            path=data['path'],
            description=data.get('description', ''),
            technologies=data.get('technologies', []),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            file_count=data.get('file_count', 0),
            total_size=data.get('total_size', 0),
            is_active=data.get('is_active', True),
            files=files,
            memory=memory
        )


class ProjectMemoryManager:
    """Manages project indexing, memory, and retrieval."""

    def __init__(self):
        """Initialize the project memory manager."""
        self.storage_dir = STORAGE_DIR
        self.projects_index = PROJECTS_INDEX
        self.archive_dir = ARCHIVE_DIR

        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Load projects
        self.projects: Dict[str, Project] = {}
        self._load_projects()

        # Try to connect to RAG system
        self.rag = None
        try:
            from .rag_system import get_rag
            self.rag = get_rag()
        except ImportError:
            logger.warning("RAG system not available")

    def _load_projects(self):
        """Load projects from disk."""
        if self.projects_index.exists():
            try:
                with open(self.projects_index, 'r') as f:
                    data = json.load(f)
                for project_data in data.get('projects', []):
                    project = Project.from_dict(project_data)
                    self.projects[project.id] = project
                logger.info(f"Loaded {len(self.projects)} projects")
            except Exception as e:
                logger.error(f"Failed to load projects: {e}")
                self.projects = {}

    def _save_projects(self):
        """Save projects to disk."""
        try:
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'projects': [p.to_dict() for p in self.projects.values()]
            }
            with open(self.projects_index, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save projects: {e}")

    def _generate_id(self, name: str, path: str) -> str:
        """Generate a unique project ID."""
        unique = f"{name}_{path}_{datetime.now().isoformat()}"
        return hashlib.md5(unique.encode()).hexdigest()[:12]

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.tsx': 'typescript', '.jsx': 'javascript', '.html': 'html',
            '.css': 'css', '.scss': 'scss', '.json': 'json',
            '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown',
            '.sql': 'sql', '.sh': 'shell', '.go': 'go', '.rs': 'rust',
            '.java': 'java', '.kt': 'kotlin', '.swift': 'swift',
            '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.vue': 'vue',
            '.svelte': 'svelte', '.php': 'php', '.rb': 'ruby',
            '.ex': 'elixir', '.exs': 'elixir'
        }
        return lang_map.get(ext, 'text')

    def _detect_technologies(self, project_path: str) -> List[str]:
        """Detect technologies used in a project."""
        techs = []
        path = Path(project_path)

        # Check for package files
        if (path / 'package.json').exists():
            techs.append('Node.js')
            try:
                with open(path / 'package.json') as f:
                    pkg = json.load(f)
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    if 'react' in deps:
                        techs.append('React')
                    if 'next' in deps:
                        techs.append('Next.js')
                    if 'vue' in deps:
                        techs.append('Vue')
                    if 'express' in deps:
                        techs.append('Express')
                    if 'typescript' in deps:
                        techs.append('TypeScript')
            except Exception:
                logger.debug("Failed to parse package.json at %s", path)

        if (path / 'requirements.txt').exists() or (path / 'pyproject.toml').exists():
            techs.append('Python')
            # Check for frameworks
            req_file = path / 'requirements.txt'
            if req_file.exists():
                try:
                    content = req_file.read_text().lower()
                    if 'fastapi' in content:
                        techs.append('FastAPI')
                    if 'flask' in content:
                        techs.append('Flask')
                    if 'django' in content:
                        techs.append('Django')
                    if 'firebase' in content:
                        techs.append('Firebase')
                except Exception:
                    logger.debug("Failed to parse requirements.txt at %s", path)

        if (path / 'firebase.json').exists():
            techs.append('Firebase')
        if (path / 'Dockerfile').exists():
            techs.append('Docker')
        if (path / 'docker-compose.yml').exists() or (path / 'docker-compose.yaml').exists():
            techs.append('Docker Compose')

        return list(set(techs))

    def _hash_content(self, content: str) -> str:
        """Generate hash of file content."""
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def add_project(self, path: str, name: str = None, description: str = "") -> Project:
        """
        Add a new project to the memory system.

        Args:
            path: Path to the project directory
            name: Optional project name (defaults to directory name)
            description: Optional project description

        Returns:
            The created Project object
        """
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.isdir(path):
            raise ValueError(f"Project path does not exist: {path}")

        # Check if project already exists
        for project in self.projects.values():
            if project.path == path and project.is_active:
                logger.info(f"Project already exists: {project.name}")
                return project

        # Create project
        name = name or os.path.basename(path)
        project_id = self._generate_id(name, path)
        technologies = self._detect_technologies(path)

        project = Project(
            id=project_id,
            name=name,
            path=path,
            description=description,
            technologies=technologies
        )

        # Index files
        self._index_project_files(project)

        # Save
        self.projects[project_id] = project
        self._save_projects()

        # Index in RAG if available
        if self.rag:
            self._index_in_rag(project)

        logger.info(f"Added project: {name} ({project.file_count} files)")
        return project

    def _index_project_files(self, project: Project):
        """Index all files in a project."""
        project.files = []
        project.file_count = 0
        project.total_size = 0

        for root, dirs, files in os.walk(project.path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext not in INDEXABLE_EXTENSIONS:
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, project.path)

                try:
                    stat = os.stat(file_path)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    project_file = ProjectFile(
                        path=rel_path,
                        language=self._detect_language(filename),
                        size=stat.st_size,
                        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        content_hash=self._hash_content(content)
                    )
                    project.files.append(project_file)
                    project.file_count += 1
                    project.total_size += stat.st_size
                except Exception as e:
                    logger.debug(f"Failed to index {file_path}: {e}")

        project.updated_at = datetime.now().isoformat()

    def _index_in_rag(self, project: Project):
        """Index project files in the RAG system."""
        if not self.rag:
            return

        indexed_count = 0
        for pf in project.files:
            try:
                file_path = os.path.join(project.path, pf.path)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Only index files with meaningful content
                if len(content.strip()) < 50:
                    continue

                # Use the RAG's index_text method with correct parameters
                self.rag.index_text(
                    content=content,
                    source_type='file',
                    title=f"{project.name}/{pf.path}",
                    language=pf.language,
                    tags=[project.name] + project.technologies,
                    metadata={
                        'project_id': project.id,
                        'project_name': project.name,
                        'file_path': pf.path,
                        'technologies': project.technologies
                    },
                    source_path=file_path
                )
                indexed_count += 1
            except Exception as e:
                logger.debug(f"Failed to index in RAG: {pf.path}: {e}")

        logger.info(f"Indexed {indexed_count} files from {project.name} in RAG")

    def reindex_project(self, project_id: str) -> Optional[Project]:
        """Re-index all files in a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        # Remove old RAG entries
        if self.rag:
            self._remove_from_rag(project)

        # Re-index
        self._index_project_files(project)
        self._save_projects()

        if self.rag:
            self._index_in_rag(project)

        logger.info(f"Re-indexed project: {project.name}")
        return project

    def _remove_from_rag(self, project: Project):
        """Remove project files from RAG index."""
        if not self.rag:
            return

        # The RAG system should have a method to remove by prefix
        # For now, we'll note this needs implementation in rag_system.py
        try:
            if hasattr(self.rag, 'remove_by_prefix'):
                self.rag.remove_by_prefix(f"project_{project.id}_")
        except Exception as e:
            logger.debug(f"Could not remove from RAG: {e}")

    def delete_project(self, project_id: str, archive: bool = True) -> bool:
        """
        Delete a project from the memory system.

        Args:
            project_id: ID of the project to delete
            archive: If True, archive the project data before deletion

        Returns:
            True if successful
        """
        project = self.projects.get(project_id)
        if not project:
            return False

        # Archive if requested
        if archive:
            archive_path = self.archive_dir / f"{project.id}_{datetime.now().strftime('%Y%m%d')}.json"
            try:
                with open(archive_path, 'w') as f:
                    json.dump(project.to_dict(), f, indent=2)
                logger.info(f"Archived project: {project.name}")
            except Exception as e:
                logger.error(f"Failed to archive project: {e}")

        # Remove from RAG
        if self.rag:
            self._remove_from_rag(project)

        # Remove from memory
        del self.projects[project_id]
        self._save_projects()

        logger.info(f"Deleted project: {project.name}")
        return True

    def list_projects(self, active_only: bool = True) -> List[Project]:
        """List all projects."""
        projects = list(self.projects.values())
        if active_only:
            projects = [p for p in projects if p.is_active]
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self.projects.get(project_id)

    def get_project_by_path(self, path: str) -> Optional[Project]:
        """Get a project by its path."""
        path = os.path.abspath(os.path.expanduser(path))
        for project in self.projects.values():
            if project.path == path and project.is_active:
                return project
        return None

    def search_projects(self, query: str, project_id: str = None, limit: int = 10) -> List[Dict]:
        """
        Search across project files.

        Args:
            query: Search query
            project_id: Optional - limit to specific project
            limit: Maximum results

        Returns:
            List of search results with file info
        """
        if not self.rag:
            return []

        try:
            # Use the RAG system's search method with correct parameters
            results = self.rag.search(
                query=query,
                limit=limit * 2,  # Get extra to filter
                source_types=['file'],
                min_score=0.1
            )

            # Filter by project_id if specified and extract data from SearchResult
            filtered = []
            for r in results:
                # SearchResult has .document (Document) and .score
                doc = r.document if hasattr(r, 'document') else r
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}

                # Filter by project if specified
                if project_id and metadata.get('project_id') != project_id:
                    continue

                filtered.append({
                    'content': doc.content[:500] if hasattr(doc, 'content') else str(doc)[:500],
                    'score': r.score if hasattr(r, 'score') else 0.5,
                    'file_path': metadata.get('file_path', doc.title if hasattr(doc, 'title') else ''),
                    'project_name': metadata.get('project_name', ''),
                    'project_id': metadata.get('project_id', ''),
                    'language': doc.language if hasattr(doc, 'language') else 'unknown',
                    'snippet': r.snippet if hasattr(r, 'snippet') else ''
                })

                if len(filtered) >= limit:
                    break

            return filtered
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def add_memory(self, project_id: str, memory_type: str, content: Dict) -> bool:
        """
        Add a memory/learning to a project.

        Args:
            project_id: Project ID
            memory_type: One of 'pattern', 'error_fix', 'lesson', 'architecture', 'conversation'
            content: The memory content

        Returns:
            True if successful
        """
        project = self.projects.get(project_id)
        if not project:
            return False

        content['added_at'] = datetime.now().isoformat()

        if memory_type == 'pattern':
            project.memory.patterns.append(content)
        elif memory_type == 'error_fix':
            project.memory.error_fixes.append(content)
        elif memory_type == 'lesson':
            project.memory.lessons.append(content.get('lesson', str(content)))
        elif memory_type == 'architecture':
            project.memory.architecture_notes.append(content.get('note', str(content)))
        elif memory_type == 'conversation':
            project.memory.conversations.append(content)
        else:
            return False

        project.updated_at = datetime.now().isoformat()
        self._save_projects()
        return True

    def get_project_context(self, project_id: str, task: str = "") -> str:
        """
        Generate context about a project for AI prompts.

        Args:
            project_id: Project ID
            task: Optional task description for focused context

        Returns:
            Context string for AI prompts
        """
        project = self.projects.get(project_id)
        if not project:
            return ""

        context_parts = [
            f"## Project: {project.name}",
            f"**Path:** {project.path}",
            f"**Technologies:** {', '.join(project.technologies) if project.technologies else 'Unknown'}",
            f"**Files:** {project.file_count} ({project.total_size // 1024} KB)",
        ]

        if project.description:
            context_parts.append(f"**Description:** {project.description}")

        # Add key files (top-level important files)
        important_files = [f.path for f in project.files if '/' not in f.path][:10]
        if important_files:
            context_parts.append(f"**Key Files:** {', '.join(important_files)}")

        # Add recent lessons
        if project.memory.lessons:
            context_parts.append(f"\n**Recent Lessons:**")
            for lesson in project.memory.lessons[-3:]:
                context_parts.append(f"- {lesson}")

        # Add architecture notes
        if project.memory.architecture_notes:
            context_parts.append(f"\n**Architecture Notes:**")
            for note in project.memory.architecture_notes[-2:]:
                context_parts.append(f"- {note}")

        # If task provided, search for relevant code
        if task and self.rag:
            results = self.search_projects(task, project_id=project_id, limit=3)
            if results:
                context_parts.append(f"\n**Relevant Code:**")
                for r in results:
                    context_parts.append(f"\n`{r['file_path']}` ({r['language']}):")
                    context_parts.append(f"```\n{r['content'][:300]}...\n```")

        return "\n".join(context_parts)

    def get_stats(self) -> Dict:
        """Get statistics about the project memory system."""
        active = [p for p in self.projects.values() if p.is_active]
        return {
            'total_projects': len(self.projects),
            'active_projects': len(active),
            'total_files': sum(p.file_count for p in active),
            'total_size_mb': sum(p.total_size for p in active) / (1024 * 1024),
            'total_memories': sum(
                len(p.memory.patterns) + len(p.memory.error_fixes) +
                len(p.memory.lessons) + len(p.memory.architecture_notes)
                for p in active
            )
        }


# Singleton instance
_manager: Optional[ProjectMemoryManager] = None


def get_project_manager() -> ProjectMemoryManager:
    """Get the global project memory manager instance."""
    global _manager
    if _manager is None:
        _manager = ProjectMemoryManager()
    return _manager
