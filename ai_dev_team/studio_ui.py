#!/usr/bin/env python3
"""
AI Team Studio - Full Development Environment
==============================================

A comprehensive IDE with:
- File Explorer (tree view)
- Directory Browser & Navigator
- File/Folder Creator
- Code Editor with syntax highlighting
- AI Code Generator
- Code Reviewer
- Live Preview

Run with: python -m ai_dev_team.studio_ui
Opens at: http://localhost:7861
"""

import asyncio
import concurrent.futures
import gradio as gr
import logging
import os
import subprocess
import re
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
team = None

# Supported languages for editor
SUPPORTED_LANGUAGES = [
    "python", "javascript", "typescript", "jsx", "tsx",
    "html", "css", "json", "yaml", "markdown", "sql",
    "shell", "dockerfile", "c", "cpp", "go", "rust"
]

# File templates
FILE_TEMPLATES = {
    "Empty": "",
    "Python Script": '''#!/usr/bin/env python3
"""
Module description.
"""

def main():
    """Main entry point."""
    pass

if __name__ == "__main__":
    main()
''',
    "Python Class": '''#!/usr/bin/env python3
"""
Module description.
"""
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class MyClass:
    """Class description."""
    name: str
    value: int = 0

    def process(self) -> str:
        """Process the data."""
        return f"{self.name}: {self.value}"
''',
    "FastAPI Endpoint": '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="My API")

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

items: List[Item] = []

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

@app.get("/items", response_model=List[Item])
async def get_items():
    return items

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    items.append(item)
    return item

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")
''',
    "React Component": '''import React, { useState } from 'react';

interface Props {
    title?: string;
}

export function Component({ title = "Hello" }: Props) {
    const [count, setCount] = useState(0);

    return (
        <div className="component">
            <h1>{title}</h1>
            <p>Count: {count}</p>
            <button onClick={() => setCount(count + 1)}>
                Increment
            </button>
        </div>
    );
}

export default Component;
''',
    "HTML Page": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Title</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
    </style>
</head>
<body>
    <h1>Hello World</h1>
    <p>Edit this template to get started.</p>
</body>
</html>
''',
    "CSS Stylesheet": '''/* Main Styles */
:root {
    --primary: #3b82f6;
    --secondary: #64748b;
    --background: #ffffff;
    --text: #1e293b;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: system-ui, -apple-system, sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}
''',
    "Firebase Functions": '''import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';

admin.initializeApp();
const db = admin.firestore();

export const onUserCreate = functions.auth.user().onCreate(async (user) => {
    await db.collection('users').doc(user.uid).set({
        email: user.email,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
    });
});

export const api = functions.https.onRequest(async (req, res) => {
    if (req.method !== 'GET') {
        res.status(405).send('Method Not Allowed');
        return;
    }

    const snapshot = await db.collection('items').get();
    const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    res.json(items);
});
''',
    "Test File (pytest)": '''"""
Tests for module.
"""
import pytest

class TestExample:
    """Test cases for Example."""

    def test_basic(self):
        """Test basic functionality."""
        assert 1 + 1 == 2

    def test_with_fixture(self, sample_data):
        """Test with fixture data."""
        assert sample_data is not None

@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {"key": "value", "items": [1, 2, 3]}
''',
}


def get_team(local_only: bool = None):
    """Get or create the AI Team instance."""
    global team, _local_only_mode

    # Check if we need to recreate team with different mode
    if local_only is not None and team is not None:
        current_mode = getattr(team, 'local_only', False)
        if current_mode != local_only:
            team = None  # Force recreation

    if team is None:
        from ai_dev_team import AIDevTeam
        use_local = local_only if local_only is not None else _local_only_mode
        team = AIDevTeam(project_name="studio", enable_memory=True, local_only=use_local)
        mode_str = "LOCAL ONLY (Ollama)" if use_local else "CLOUD + LOCAL"
        logger.info(f"AI Team initialized: {mode_str} - {len(team.agents)} agents")
    return team

# Global setting for local-only mode
_local_only_mode = False

def set_local_only_mode(enabled: bool):
    """Switch between local-only and cloud+local modes."""
    global _local_only_mode, team
    _local_only_mode = enabled
    team = None  # Force recreation on next get_team()
    mode_str = "LOCAL ONLY" if enabled else "CLOUD + LOCAL"
    logger.info(f"AI Team mode switched to: {mode_str}")
    return f"Mode: {mode_str}"

def get_team_status():
    """Get current AI Team status."""
    t = get_team()
    agents = list(t.agents.keys())
    mode = "Local Only (Ollama)" if t.local_only else "Cloud + Local"
    return f"**Mode:** {mode}\n**Agents ({len(agents)}):** {', '.join(agents)}"


def run_async(coro):
    """Run async code safely."""
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            return future.result(timeout=120)
    else:
        return asyncio.run(coro)


def detect_language(filepath):
    """Detect language from file extension."""
    ext_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'jsx', '.tsx': 'tsx', '.html': 'html', '.htm': 'html',
        '.css': 'css', '.json': 'json', '.md': 'markdown',
        '.yaml': 'yaml', '.yml': 'yaml', '.sql': 'sql',
        '.sh': 'shell', '.bash': 'shell', '.go': 'go', '.rs': 'rust',
        '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.hpp': 'cpp',
    }
    ext = os.path.splitext(filepath)[1].lower() if filepath else ''
    return ext_map.get(ext, 'python')


def read_file(filepath):
    """Read file contents."""
    try:
        filepath = os.path.expanduser(filepath)

        # Check if it's a binary file by extension
        binary_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp',
                            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                            '.zip', '.tar', '.gz', '.rar', '.7z',
                            '.exe', '.dll', '.so', '.dylib', '.bin',
                            '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
                            '.pyc', '.pyo', '.class', '.o', '.obj',
                            '.woff', '.woff2', '.ttf', '.otf', '.eot'}
        ext = os.path.splitext(filepath)[1].lower()
        if ext in binary_extensions:
            size = os.path.getsize(filepath)
            return f"# Binary file: {os.path.basename(filepath)}\n# Size: {size:,} bytes\n# Cannot display binary content in editor"

        # Try UTF-8 first
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            pass

        # Try latin-1 (covers all byte values)
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                return f.read()
        except UnicodeDecodeError:
            pass

        # If all else fails, it's likely binary
        size = os.path.getsize(filepath)
        return f"# Binary file: {os.path.basename(filepath)}\n# Size: {size:,} bytes\n# Cannot display binary content in editor"

    except Exception as e:
        return f"# Error reading file: {e}"


def save_file(filepath, content):
    """Save file contents."""
    try:
        filepath = os.path.expanduser(filepath)
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)
        return f"Saved: {filepath}"
    except Exception as e:
        return f"Error: {e}"


def create_directory(dirpath):
    """Create a directory."""
    try:
        dirpath = os.path.expanduser(dirpath)
        os.makedirs(dirpath, exist_ok=True)
        return f"Created folder: {dirpath}"
    except Exception as e:
        return f"Error: {e}"


def delete_path(filepath):
    """Delete a file or empty directory."""
    try:
        filepath = os.path.expanduser(filepath)
        if os.path.isfile(filepath):
            os.remove(filepath)
            return f"Deleted: {filepath}"
        elif os.path.isdir(filepath):
            os.rmdir(filepath)
            return f"Deleted folder: {filepath}"
        else:
            return f"Path not found: {filepath}"
    except Exception as e:
        return f"Error: {e}"


def list_directory(directory="."):
    """List directory contents as formatted text."""
    try:
        path = Path(directory).resolve()
        items = []
        for item in sorted(path.iterdir()):
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                items.append(f"[DIR]  {item.name}/")
            else:
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size // (1024 * 1024)}MB"
                items.append(f"[FILE] {item.name} ({size_str})")
        return "\n".join(items) if items else "(empty directory)"
    except Exception as e:
        return f"Error: {e}"


def get_directory_tree(root_dir=".", max_depth=3):
    """Get directory tree as formatted text."""
    try:
        # Expand user home directory
        root_dir = os.path.expanduser(str(root_dir))
        root = Path(root_dir).resolve()

        if not root.exists():
            return f"Directory not found: {root_dir}"

        if not root.is_dir():
            return f"Not a directory: {root_dir}"

        lines = [f"📁 {root.name}/ ({root})"]

        def add_items(path, prefix="", depth=0):
            if depth >= max_depth:
                return
            try:
                items = list(path.iterdir())
                # Filter hidden files and sort
                items = [i for i in items if not i.name.startswith('.')]
                items = sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))

                # Limit items to prevent huge trees
                if len(items) > 50:
                    items = items[:50]
                    lines.append(f"{prefix}... ({len(items) - 50} more items)")

                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    connector = "└── " if is_last else "├── "

                    if item.is_dir():
                        lines.append(f"{prefix}{connector}📁 {item.name}/")
                        new_prefix = prefix + ("    " if is_last else "│   ")
                        add_items(item, new_prefix, depth + 1)
                    else:
                        icon = get_file_icon(item.suffix)
                        lines.append(f"{prefix}{connector}{icon} {item.name}")
            except PermissionError:
                lines.append(f"{prefix}└── ⛔ (permission denied)")
            except Exception as e:
                lines.append(f"{prefix}└── ❌ Error: {str(e)[:30]}")

        add_items(root)
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading directory: {e}"


def get_file_icon(ext):
    """Get icon for file type."""
    icons = {
        '.py': '🐍', '.js': '📜', '.ts': '📘', '.jsx': '⚛️', '.tsx': '⚛️',
        '.html': '🌐', '.css': '🎨', '.json': '📋', '.md': '📝',
        '.yaml': '⚙️', '.yml': '⚙️', '.sql': '🗃️',
        '.png': '🖼️', '.jpg': '🖼️', '.gif': '🖼️', '.svg': '🖼️',
        '.pdf': '📕', '.txt': '📄', '.sh': '⚡', '.env': '🔐',
    }
    return icons.get(ext.lower(), '📄')


def get_file_list(directory):
    """Get files in directory as a list for display."""
    try:
        directory = os.path.expanduser(str(directory))
        path = Path(directory).resolve()
        if not path.exists() or not path.is_dir():
            return []

        items = []
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                items.append(["📁", item.name, "folder", ""])
            else:
                ext = item.suffix
                icon = get_file_icon(ext)
                size = item.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size // (1024 * 1024)}MB"
                items.append([icon, item.name, ext[1:] if ext else "", size_str])
        return items
    except Exception:
        return []


def generate_preview(code, language):
    """Generate live preview HTML."""
    # Handle None values
    if not code or not language:
        return "<div style='padding:2rem;color:#666;text-align:center;'>No code to preview</div>"
    if language in ['html', 'htm']:
        return code
    elif language == 'css':
        return f"<style>{code}</style><div class='preview'>CSS Applied - Add HTML to see styles</div>"
    elif language in ['js', 'javascript']:
        return f"""
        <div id="output" style="font-family: monospace; padding: 1rem;"></div>
        <script>
        try {{
            const output = document.getElementById('output');
            const log = console.log;
            console.log = (...args) => {{
                output.innerHTML += args.map(a =>
                    typeof a === 'object' ? JSON.stringify(a, null, 2) : a
                ).join(' ') + '<br>';
                log.apply(console, args);
            }};
            {code}
        }} catch(e) {{
            document.getElementById('output').innerHTML = '<span style="color:red">Error: ' + e.message + '</span>';
        }}
        </script>
        """
    elif language in ['jsx', 'tsx', 'react']:
        return f"""
        <div id="root"></div>
        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script type="text/babel">
        {code}
        </script>
        """
    elif language == 'python':
        try:
            from ai_dev_team.sandbox import get_code_executor
            import asyncio

            executor = get_code_executor()

            def _run():
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(executor.execute(code, "python", timeout=10))
                finally:
                    loop.close()

            result = _run()
            output = result.stdout or result.stderr or "(no output)"
            if not result.success:
                return f"<pre style='background:#1e1e1e;color:#ff6b6b;padding:1rem;border-radius:8px;overflow-x:auto;'>{output}</pre>"
            return f"<pre style='background:#1e1e1e;color:#d4d4d4;padding:1rem;border-radius:8px;overflow-x:auto;'>{output}</pre>"
        except Exception as e:
            return f"<pre style='color:red'>Error: {e}</pre>"
    else:
        return f"<pre style='background:#f5f5f5;padding:1rem;border-radius:8px;overflow-x:auto;'>{code[:2000]}</pre>"


# ==========================================
# CODE EXECUTION MANAGER
# ==========================================
class ProcessManager:
    """Manages running code processes."""

    def __init__(self):
        self.process = None
        self.output_lines = []
        self.is_running = False
        self.server_url = None

    def run_code(self, code, language, file_path, current_dir, port=8000, server_type="Auto"):
        """Run code and return output."""
        self.stop()  # Stop any existing process
        self.output_lines = []

        # Detect what type of code we're running
        is_server = any(kw in code.lower() for kw in ['fastapi', 'flask', 'uvicorn', 'app.run', 'express', 'http.createserver'])

        if server_type == "Static HTML" or (language in ['html', 'htm'] and server_type == "Auto"):
            return self._serve_static(code, current_dir, port)
        elif language == 'python':
            if is_server or server_type == "Python":
                return self._run_python_server(code, file_path, current_dir, port)
            else:
                return self._run_python_script(code, file_path, current_dir)
        elif language in ['javascript', 'js', 'typescript', 'ts']:
            if is_server or server_type == "Node.js":
                return self._run_node_server(code, file_path, current_dir, port)
            else:
                return self._run_node_script(code, file_path, current_dir)
        else:
            return f"Cannot run {language} files directly", "*Not supported*", ""

    def _run_python_script(self, code, file_path, current_dir):
        """Run a Python script using the sandboxed executor."""
        try:
            from ai_dev_team.sandbox import get_code_executor
            import asyncio

            executor = get_code_executor()

            def _run():
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(executor.execute(code, "python", timeout=30))
                finally:
                    loop.close()

            result = _run()
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.timed_out:
                return "Execution timed out (30s limit)", "*Timed out*", ""
            return output or "(no output)", "*Completed*", ""
        except Exception as e:
            return f"Error: {e}", "*Error*", ""

    def _run_python_server(self, code, file_path, current_dir, port):
        """Run a Python server (FastAPI, Flask, etc.)."""
        try:
            # Save code to file
            if not file_path or not os.path.exists(file_path):
                temp_file = os.path.join(current_dir, "_temp_server.py")
                with open(temp_file, 'w') as f:
                    f.write(code)
                file_path = temp_file

            # Detect framework and build command
            if 'fastapi' in code.lower() or 'uvicorn' in code.lower():
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                cmd = ['uvicorn', f'{module_name}:app', '--reload', '--port', str(port)]
            elif 'flask' in code.lower():
                cmd = ['python', file_path]
                os.environ['FLASK_RUN_PORT'] = str(port)
            else:
                cmd = ['python', file_path]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=current_dir,
                bufsize=1
            )
            self.is_running = True
            self.server_url = f"http://localhost:{port}"

            # Read initial output
            import time
            time.sleep(1)
            initial_output = self._read_output()

            return initial_output or f"Server starting on port {port}...", f"*🟢 Running on port {port}*", self.server_url
        except Exception as e:
            return f"Error starting server: {e}", "*Error*", ""

    def _run_node_script(self, code, file_path, current_dir):
        """Run a Node.js script."""
        try:
            if not file_path or not os.path.exists(file_path):
                temp_file = os.path.join(current_dir, "_temp_run.js")
                with open(temp_file, 'w') as f:
                    f.write(code)
                file_path = temp_file

            result = subprocess.run(
                ['node', file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=current_dir
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            return output or "(no output)", "*Completed*", ""
        except subprocess.TimeoutExpired:
            return "Execution timed out (30s limit)", "*Timed out*", ""
        except FileNotFoundError:
            return "Node.js not found. Please install Node.js.", "*Error*", ""
        except Exception as e:
            return f"Error: {e}", "*Error*", ""

    def _run_node_server(self, code, file_path, current_dir, port):
        """Run a Node.js server."""
        try:
            if not file_path or not os.path.exists(file_path):
                temp_file = os.path.join(current_dir, "_temp_server.js")
                with open(temp_file, 'w') as f:
                    f.write(code)
                file_path = temp_file

            self.process = subprocess.Popen(
                ['node', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=current_dir,
                bufsize=1,
                env={**os.environ, 'PORT': str(port)}
            )
            self.is_running = True
            self.server_url = f"http://localhost:{port}"

            import time
            time.sleep(1)
            initial_output = self._read_output()

            return initial_output or f"Server starting on port {port}...", f"*🟢 Running on port {port}*", self.server_url
        except FileNotFoundError:
            return "Node.js not found. Please install Node.js.", "*Error*", ""
        except Exception as e:
            return f"Error starting server: {e}", "*Error*", ""

    def _serve_static(self, code, current_dir, port):
        """Serve static HTML file."""
        try:
            # Save HTML to temp file
            temp_file = os.path.join(current_dir, "_preview.html")
            with open(temp_file, 'w') as f:
                f.write(code)

            # Start simple HTTP server
            self.process = subprocess.Popen(
                ['python', '-m', 'http.server', str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=current_dir
            )
            self.is_running = True
            self.server_url = f"http://localhost:{port}/_preview.html"

            return f"Serving static files on port {port}", f"*🟢 Serving on port {port}*", self.server_url
        except Exception as e:
            return f"Error: {e}", "*Error*", ""

    def _read_output(self):
        """Read available output from process."""
        if not self.process:
            return ""

        import select
        output = []
        try:
            # Non-blocking read
            while True:
                if self.process.stdout and select.select([self.process.stdout], [], [], 0.1)[0]:
                    line = self.process.stdout.readline()
                    if line:
                        output.append(line)
                        self.output_lines.append(line)
                    else:
                        break
                else:
                    break
        except Exception:
            pass

        return "".join(output[-50:])  # Return last 50 lines

    def get_output(self):
        """Get all output so far."""
        if self.process:
            self._read_output()
        return "".join(self.output_lines[-100:])  # Return last 100 lines

    def stop(self):
        """Stop the running process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self.is_running = False
        self.server_url = None
        return "Process stopped", "*Not running*"


# Global process manager
_process_manager = ProcessManager()


def run_code_handler(code, language, file_path, current_dir, port, server_type):
    """Handler for running code."""
    output, status, url = _process_manager.run_code(code, language, file_path, current_dir, int(port), server_type)

    # Automatically open browser for server URLs
    if url:
        try:
            webbrowser.open(url)
            preview_html = f"""
            <div style='padding:1rem;text-align:center;background:#e8f5e9;border-radius:8px;'>
                <p style='margin:0;color:#2e7d32;'>✅ <strong>Preview opened in new browser window</strong></p>
                <p style='margin:8px 0 0;'><a href="{url}" target="_blank" style='color:#1976d2;'>{url} ↗</a></p>
            </div>
            """
        except Exception:
            preview_html = f"<div style='text-align:center;'><a href='{url}' target='_blank'>{url} ↗</a></div>"
    else:
        preview_html = ""

    return output, status, preview_html, url


def stop_code_handler():
    """Handler for stopping code."""
    output, status = _process_manager.stop()
    return output, status


def refresh_output_handler():
    """Handler for refreshing output."""
    return _process_manager.get_output()


def generate_preview_iframe(url):
    """Generate iframe for preview URL."""
    if not url or not url.startswith("http"):
        return "<div style='padding:2rem;color:#666;text-align:center;'>Enter a valid URL to preview</div>"

    return f"""
    <iframe src="{url}" style="width:100%;height:300px;border:1px solid #ddd;border-radius:8px;" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>
    <div style="text-align:center;padding:8px;"><a href="{url}" target="_blank">Open in new tab ↗</a></div>
    """


async def ai_generate_code(prompt, language, current_code="", mode="new"):
    """Generate code using AI Team."""
    t = get_team()

    mode_prompts = {
        "new": f"Generate {language} code for: {prompt}",
        "extend": f"Extend this {language} code with: {prompt}\n\nCurrent code:\n```\n{current_code}\n```",
        "refactor": f"Refactor this {language} code to: {prompt}\n\nCurrent code:\n```\n{current_code}\n```",
        "fix": f"Fix bugs and issues in this {language} code:\n```\n{current_code}\n```",
        "explain": f"Explain this {language} code in detail:\n```\n{current_code}\n```",
    }

    full_prompt = mode_prompts.get(mode, mode_prompts["new"])

    if mode != "explain":
        full_prompt += "\n\nRequirements:\n1. Write clean, production-ready code\n2. Include necessary imports\n3. Add brief comments\n4. Follow best practices\n\nReturn ONLY the code, no markdown."

    result = await t.collaborate(prompt=full_prompt, mode="auto")
    response = result.final_answer

    # Clean up markdown code blocks
    if "```" in response:
        matches = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        if matches:
            response = matches[0]

    return response.strip()


async def ai_review_code(code, language, review_types):
    """Review code using AI Team."""
    t = get_team()

    review_prompt = f"""Review this {language} code for the following aspects:
{', '.join(review_types)}

Code to review:
```{language}
{code}
```

Provide:
1. Issues found (if any)
2. Suggestions for improvement
3. Security concerns (if any)
4. Best practice recommendations

Format as markdown with clear sections."""

    result = await t.collaborate(prompt=review_prompt, mode="auto")
    return result.final_answer


def format_code_python(code):
    """Format Python code using ruff or black."""
    try:
        result = subprocess.run(
            ['ruff', 'format', '-'],
            input=code, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout, "Formatted with ruff"
        else:
            return code, f"Format error: {result.stderr}"
    except FileNotFoundError:
        try:
            result = subprocess.run(
                ['black', '-'],
                input=code, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout, "Formatted with black"
            else:
                return code, f"Format error: {result.stderr}"
        except FileNotFoundError:
            return code, "No formatter available (install ruff or black)"
    except Exception as e:
        return code, f"Format error: {e}"


def lint_code_python(code):
    """Lint Python code using ruff."""
    try:
        result = subprocess.run(
            ['ruff', 'check', '-'],
            input=code, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return "No issues found"
        else:
            return result.stdout or result.stderr
    except FileNotFoundError:
        return "Linter not available (install ruff)"
    except Exception as e:
        return f"Lint error: {e}"


def create_app_builder_ui(app_project_state, current_page_idx, home_dir):
    """Create the No-Code App Builder UI."""

    from ai_dev_team.app_builder import (
        AppProject, Page, Component, DataModel, DataField,
        create_default_project, COMPONENT_PALETTE, APP_TYPE_TEMPLATES,
        VisualAppBuilder
    )
    from ai_dev_team.app_builder.components import FULL_APP_TEMPLATES, COMPONENT_TEMPLATES, count_components

    # Custom CSS for better styling
    gr.HTML("""
    <style>
        .template-card {
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 16px;
            margin: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        }
        .template-card:hover {
            border-color: #3b82f6;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
            transform: translateY(-2px);
        }
        .template-card h4 {
            margin: 0 0 8px 0;
            color: #1e293b;
        }
        .template-card p {
            margin: 0;
            font-size: 12px;
            color: #64748b;
        }
        .component-btn {
            margin: 4px;
            font-size: 12px;
        }
        .stat-box {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-box h3 { margin: 0; font-size: 24px; }
        .stat-box p { margin: 4px 0 0 0; font-size: 12px; opacity: 0.9; }
    </style>
    """)

    gr.Markdown("## No-Code App Builder")
    gr.Markdown(f"*{count_components()} components • 6 full app templates • AI-powered generation*")

    with gr.Tabs():
        # ==========================================
        # TAB 1: QUICK START WITH TEMPLATES
        # ==========================================
        with gr.Tab("🚀 Quick Start"):
            gr.Markdown("### Start with a Full App Template")
            gr.Markdown("*One-click to generate a complete, production-ready application*")

            with gr.Row():
                template_choice = gr.Radio(
                    choices=list(FULL_APP_TEMPLATES.keys()),
                    value="saas_dashboard",
                    label="Choose Template",
                    interactive=True
                )

            with gr.Row():
                with gr.Column(scale=2):
                    template_name_input = gr.Textbox(
                        label="Project Name",
                        placeholder="my-awesome-app",
                        value="my-app"
                    )
                with gr.Column(scale=1):
                    template_db = gr.Radio(
                        choices=["SQLite", "Firestore"],
                        value="SQLite",
                        label="Database"
                    )

            template_info = gr.Markdown("""
**SaaS Dashboard**
- Dashboard with analytics
- User management
- Settings page
- Login/Auth system
- **Pages:** Dashboard, Users, Settings, Login
- **Data Models:** users
            """)

            generate_template_btn = gr.Button(
                "🚀 Generate Complete App",
                variant="primary",
                size="lg"
            )

            template_output = gr.Textbox(
                label="Generation Output",
                lines=8,
                interactive=False
            )

        # ==========================================
        # TAB 2: CUSTOM BUILD
        # ==========================================
        with gr.Tab("🎨 Custom Build"):
            gr.Markdown("### Build Your Own App")

            with gr.Row():
                # === LEFT: Project Setup & Components ===
                with gr.Column(scale=1, min_width=300):

                    with gr.Accordion("📱 New Project", open=True):
                        project_name = gr.Textbox(
                            label="Project Name",
                            placeholder="my-awesome-app",
                            value="my-app"
                        )
                        app_type = gr.Dropdown(
                            choices=list(APP_TYPE_TEMPLATES.keys()),
                            value="web_app",
                            label="App Type"
                        )
                        app_description = gr.Textbox(
                            label="Describe Your App",
                            placeholder="A task manager with user login, task lists, due dates...",
                            lines=3
                        )
                        create_project_btn = gr.Button("Create Project", variant="primary")

                    with gr.Accordion("📄 Pages", open=True):
                        pages_display = gr.Dataframe(
                            headers=["Page", "Route", "Auth"],
                            datatype=["str", "str", "bool"],
                            value=[["Home", "/", False]],
                            interactive=False,
                            row_count=5
                        )
                        with gr.Row():
                            new_page_name = gr.Textbox(placeholder="Page name", scale=3, show_label=False)
                            add_page_btn = gr.Button("+ Add", size="sm", scale=1)

                    with gr.Accordion("🧩 Components (80+)", open=True):
                        gr.Markdown("*Click to add to current page*")
                        component_category = gr.Dropdown(
                            choices=[(v["display_name"], k) for k, v in COMPONENT_PALETTE.items()],
                            value="layout",
                            label="Category"
                        )
                        component_list = gr.Dataframe(
                            headers=["Component", "Description"],
                            value=[[c["name"], c.get("description", "")] for c in COMPONENT_PALETTE["layout"]["components"]],
                            interactive=False,
                            row_count=8
                        )
                        gr.Button("+ Add Selected", variant="secondary", size="sm")

                    with gr.Accordion("💬 Natural Language", open=True):
                        nl_input = gr.Textbox(
                            placeholder="Add a contact form with name, email, and message fields",
                            label="Describe what to add",
                            lines=2
                        )
                        nl_add_btn = gr.Button("Add with AI", variant="primary")

                # === CENTER: Page Designer ===
                with gr.Column(scale=2):
                    with gr.Row():
                        current_page = gr.Dropdown(
                            choices=["Home"],
                            value="Home",
                            label="Current Page",
                            scale=3
                        )
                        gr.Checkbox(label="Requires Login", value=False, scale=1)

                    page_components = gr.Textbox(
                        label="Page Components",
                        value="(empty page - add components from the palette or use natural language)",
                        lines=12,
                        interactive=False
                    )

                    with gr.Row():
                        gr.Button("👁️ Preview Page", size="sm")
                        gr.Button("🗑️ Clear Page", size="sm")

                # === RIGHT: Preview & Database ===
                with gr.Column(scale=2):
                    with gr.Tabs():
                        with gr.Tab("👁️ Preview"):
                            gr.Radio(["Desktop", "Mobile"], value="Desktop", label="Device")
                            gr.HTML(
                                value="<div style='padding:2rem;text-align:center;color:#666;border:1px dashed #ccc;border-radius:8px;min-height:300px;'><h3>App Preview</h3><p>Create a project to see preview</p></div>"
                            )

                        with gr.Tab("📊 Data Models"):
                            gr.Dataframe(
                                headers=["Model", "Fields"],
                                datatype=["str", "str"],
                                value=[],
                                interactive=False
                            )
                            with gr.Row():
                                gr.Textbox(placeholder="Model name (e.g., tasks)", scale=3, show_label=False)
                                gr.Button("+ Add", size="sm", scale=1)

                        with gr.Tab("🗄️ Database"):
                            db_type = gr.Radio(["SQLite", "Firestore"], value="SQLite", label="Database Type")
                            schema_preview = gr.Code(
                                label="Schema Preview",
                                language="sql",
                                value="-- Schema will appear here after generation",
                                lines=10
                            )

            # Bottom Action Bar for Custom Build
            gr.Markdown("---")
            with gr.Row():
                generate_btn = gr.Button("🚀 Generate Full App", variant="primary", size="lg")
                gr.Button("📦 Export ZIP", size="lg")
                gr.Button("▶️ Run Locally", size="lg")

            generation_log = gr.Textbox(label="Generation Log", lines=5, visible=True)

        # ==========================================
        # TAB 3: COMPONENT TEMPLATES
        # ==========================================
        with gr.Tab("📦 Component Templates"):
            gr.Markdown("### Pre-built Component Combinations")
            gr.Markdown("*Ready-to-use component templates for common patterns*")

            with gr.Row():
                with gr.Column(scale=1):
                    template_type = gr.Radio(
                        choices=list(COMPONENT_TEMPLATES.keys()),
                        value="contact_form",
                        label="Select Template"
                    )

                with gr.Column(scale=2):
                    comp_template_preview = gr.Code(
                        label="Template Preview",
                        language="json",
                        value="{}",
                        lines=15
                    )

            gr.Button("+ Add to Current Page", variant="primary")

        # ==========================================
        # TAB 4: DEPLOY
        # ==========================================
        with gr.Tab("🌐 Deploy"):
            gr.Markdown("### Deploy Your Application")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("""
#### Local Development
Run your app locally for testing:
- **Backend:** FastAPI on port 8000
- **Frontend:** Static HTML served
- **Database:** SQLite file or Firestore
                    """)
                    gr.Button("▶️ Run Locally", variant="primary", size="lg")
                    gr.Textbox(label="Server Output", lines=4, interactive=False)

                with gr.Column():
                    gr.Markdown("""
#### Export Options
Export your complete application:
- Full source code (Python + HTML/CSS/JS)
- Docker configuration
- README with setup instructions
                    """)
                    gr.Button("📦 Export as ZIP", size="lg")
                    gr.Button("🐳 Export with Docker", size="lg")
                    gr.Textbox(label="Export Status", lines=2, interactive=False)

    # === Event Handlers ===

    def update_template_info(template_key):
        """Update template info display when selection changes"""
        template = FULL_APP_TEMPLATES.get(template_key, {})
        name = template.get("name", "Unknown")
        desc = template.get("description", "")
        pages = template.get("pages", [])
        models = template.get("data_models", [])
        auth = "Yes" if template.get("auth_enabled") else "No"

        page_names = [p["name"] for p in pages]
        model_names = [m["name"] for m in models]

        info = f"""
**{name}**
{desc}

- **Pages ({len(pages)}):** {', '.join(page_names)}
- **Data Models ({len(models)}):** {', '.join(model_names) if model_names else 'None'}
- **Authentication:** {auth}
        """
        return info

    def generate_from_template(template_key, project_name, db_type_val):
        """Generate a complete app from a full template"""
        try:
            template = FULL_APP_TEMPLATES.get(template_key)
            if not template:
                return f"Template '{template_key}' not found"

            # Create project from template
            project = AppProject(
                name=project_name.lower().replace(" ", "-"),
                display_name=project_name.title(),
                description=template.get("description", ""),
                app_type=template_key,
                database_type="sqlite" if db_type_val == "SQLite" else "firestore",
                auth_enabled=template.get("auth_enabled", False)
            )

            # Add pages from template
            for page_data in template.get("pages", []):
                page = Page(
                    name=page_data["name"],
                    route=page_data["route"],
                    requires_auth=page_data.get("requires_auth", False)
                )
                # Add components to page
                for comp_data in page_data.get("components", []):
                    comp = Component(
                        component_type=comp_data["type"],
                        name=comp_data["type"].replace("_", " ").title(),
                        properties=comp_data.get("properties", {})
                    )
                    page.components.append(comp)
                project.pages.append(page)

            # Add data models from template
            for model_data in template.get("data_models", []):
                model = DataModel(
                    name=model_data["name"],
                    display_name=model_data["name"].replace("_", " ").title()
                )
                for field_data in model_data.get("fields", []):
                    field = DataField(
                        name=field_data["name"],
                        field_type=field_data.get("type", "string"),
                        required=field_data.get("required", False),
                        unique=field_data.get("unique", False),
                        default_value=field_data.get("default")
                    )
                    model.fields.append(field)
                project.data_models.append(model)

            # Generate the app
            generator = VisualAppBuilder()
            result = generator.generate(project)

            if result["success"]:
                # Save to disk
                output_dir = os.path.join(home_dir, "Development", project.name)
                saved_path = generator.save_to_disk(result, output_dir)

                output = f"""
✅ Successfully generated: {template.get('name')}

📁 Output Directory: {saved_path}

📄 Files Generated ({len(result['files'])}):
"""
                for filename in sorted(result['files'].keys()):
                    output += f"   - {filename}\n"

                output += f"""
🚀 To run your app:
   cd {saved_path}
   pip install -r requirements.txt
   python -m uvicorn backend.main:app --reload

🌐 Then open: http://localhost:8000
                """
                return output
            else:
                return f"❌ Generation failed: {result.get('error', 'Unknown error')}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def update_component_list(category_key):
        """Update component list when category changes"""
        components = COMPONENT_PALETTE.get(category_key, {}).get("components", [])
        data = [[c["name"], c.get("description", "")] for c in components]
        return data

    def update_comp_template_preview(template_key):
        """Update component template preview"""
        import json
        template = COMPONENT_TEMPLATES.get(template_key, {})
        return json.dumps(template, indent=2)

    def create_project(name, app_t, description):
        """Create a new app project"""
        project = create_default_project(name, app_t)
        project.description = description

        pages_data = [[p.name, p.route, p.requires_auth] for p in project.pages]
        page_names = [p.name for p in project.pages]

        return (
            project.to_dict(),
            pages_data,
            page_names[0] if page_names else "Home",
            gr.Dropdown(choices=page_names, value=page_names[0] if page_names else None),
            f"Project '{name}' created with {len(project.pages)} pages"
        )

    def add_page_to_project(project_dict, page_name, pages_data):
        """Add a new page"""
        if not page_name:
            return project_dict, pages_data, gr.update()

        new_route = "/" + page_name.lower().replace(" ", "-")
        new_row = [page_name, new_route, False]
        pages_data = list(pages_data) if pages_data else []
        pages_data.append(new_row)

        page_names = [p[0] for p in pages_data]
        return project_dict, pages_data, gr.Dropdown(choices=page_names, value=page_name)

    def generate_full_app(project_dict, db_type_val, pages_data):
        """Generate the complete application"""
        if not project_dict:
            return "Please create a project first", ""

        try:
            # Reconstruct project
            project = AppProject(
                name=project_dict.get("name", "my-app"),
                display_name=project_dict.get("display_name", "My App"),
                description=project_dict.get("description", ""),
                app_type=project_dict.get("app_type", "web_app"),
                database_type="sqlite" if db_type_val == "SQLite" else "firestore"
            )

            # Add pages
            if pages_data:
                for page_row in pages_data:
                    if len(page_row) >= 3:
                        project.add_page(page_row[0], page_row[1], page_row[2])

            # Generate
            generator = VisualAppBuilder()
            result = generator.generate(project)

            if result["success"]:
                # Save to disk
                output_dir = os.path.join(home_dir, "Development", project.name)
                saved_path = generator.save_to_disk(result, output_dir)

                log = "\n".join(result["log"])
                log += f"\n\nSaved to: {saved_path}"
                log += f"\nFiles generated: {len(result['files'])}"

                # Get schema for preview
                schema = result["files"].get("database/schema.sql", "-- No schema")

                return log, schema
            else:
                return "Generation failed: " + str(result.get("error", "Unknown error")), ""

        except Exception as e:
            return f"Error: {str(e)}", ""

    def add_component_nl(nl_text, current_pg, page_comps):
        """Add components using natural language"""
        if not nl_text:
            return page_comps

        # Parse common patterns
        components_added = []

        nl_lower = nl_text.lower()

        if "form" in nl_lower:
            components_added.append("Form")
            if "contact" in nl_lower:
                components_added.extend(["Text Field (Name)", "Email Field", "Text Area (Message)", "Submit Button"])
            elif "login" in nl_lower:
                components_added.extend(["Email Field", "Password Field", "Submit Button"])

        if "button" in nl_lower:
            components_added.append("Button")

        if "table" in nl_lower or "list" in nl_lower:
            components_added.append("Data Table")

        if "heading" in nl_lower or "title" in nl_lower:
            components_added.append("Heading")

        if "image" in nl_lower:
            components_added.append("Image")

        if "card" in nl_lower:
            components_added.append("Card")

        if components_added:
            result = f"Page: {current_pg}\n\nComponents:\n"
            result += "\n".join([f"  - {c}" for c in components_added])
            return result
        else:
            return page_comps + f"\n\n(Trying to add: {nl_text})"

    # Wire up events

    # Quick Start Tab - Template selection
    template_choice.change(
        update_template_info,
        inputs=[template_choice],
        outputs=[template_info]
    )

    generate_template_btn.click(
        generate_from_template,
        inputs=[template_choice, template_name_input, template_db],
        outputs=[template_output]
    )

    # Custom Build Tab - Component category change
    component_category.change(
        update_component_list,
        inputs=[component_category],
        outputs=[component_list]
    )

    # Component Templates Tab
    template_type.change(
        update_comp_template_preview,
        inputs=[template_type],
        outputs=[comp_template_preview]
    )

    # Custom Build - Project creation
    create_project_btn.click(
        create_project,
        inputs=[project_name, app_type, app_description],
        outputs=[app_project_state, pages_display, current_page, current_page, generation_log]
    )

    add_page_btn.click(
        add_page_to_project,
        inputs=[app_project_state, new_page_name, pages_display],
        outputs=[app_project_state, pages_display, current_page]
    )

    generate_btn.click(
        generate_full_app,
        inputs=[app_project_state, db_type, pages_display],
        outputs=[generation_log, schema_preview]
    )

    nl_add_btn.click(
        add_component_nl,
        inputs=[nl_input, current_page, page_components],
        outputs=[page_components]
    )


def create_studio_ui():
    """Create the full development environment interface."""

    # Custom CSS for dark mode and styling
    custom_css = """
    .dark-mode {
        --body-background-fill: #0f172a !important;
        --block-background-fill: #1e293b !important;
        --body-text-color: #e2e8f0 !important;
        --block-title-text-color: #f1f5f9 !important;
        --input-background-fill: #334155 !important;
        --button-primary-background-fill: #3b82f6 !important;
        --button-primary-text-color: white !important;
    }
    .studio-header {
        background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%);
        padding: 16px 24px;
        border-radius: 12px;
        margin-bottom: 16px;
        color: white;
    }
    .studio-header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }
    .studio-header p {
        margin: 4px 0 0 0;
        opacity: 0.9;
        font-size: 14px;
    }
    .feature-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        margin: 2px;
    }
    .panel-header {
        font-weight: 600;
        color: #3b82f6;
        margin-bottom: 8px;
    }

    /* ============================================
       AI CHAT STYLES
       ============================================ */

    :root {
        --ai-primary: #6366f1;
        --ai-primary-light: rgba(99, 102, 241, 0.1);
        --ai-bg: #ffffff;
        --ai-bg-secondary: #f8fafc;
        --ai-bg-tertiary: #f1f5f9;
        --ai-border: #e2e8f0;
        --ai-text: #1e293b;
        --ai-text-secondary: #64748b;
    }

    /* Integrated AI Chat in Right Panel */
    .integrated-chatbot {
        border: 1px solid var(--ai-border) !important;
        border-radius: 12px !important;
        background: var(--ai-bg) !important;
    }

    .integrated-chatbot .message {
        padding: 12px 16px !important;
        margin: 8px !important;
        border-radius: 12px !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }

    .integrated-chatbot .user {
        background: linear-gradient(135deg, var(--ai-primary) 0%, #8b5cf6 100%) !important;
        color: white !important;
        margin-left: 15% !important;
    }

    .integrated-chatbot .bot {
        background: var(--ai-bg-tertiary) !important;
        color: var(--ai-text) !important;
        margin-right: 15% !important;
    }
    """

    with gr.Blocks(title="AI Team Studio") as demo:
        # Inject custom CSS
        gr.HTML(f"<style>{custom_css}</style>")

        # State management - start in user's Development/Projects directory
        home_dir = os.path.expanduser("~")
        # Default to Projects folder if it exists
        projects_dir = os.path.expanduser("~/Development/Projects")
        start_dir = projects_dir if os.path.isdir(projects_dir) else home_dir
        current_dir = gr.State(value=start_dir)
        current_file_path = gr.State(value=None)
        gr.State(value={})

        # App Builder State
        app_project_state = gr.State(value=None)
        current_page_idx = gr.State(value=0)

        # Header with mode switch
        gr.HTML("""
        <div class="studio-header">
            <h1>AI Team Studio</h1>
            <p>No-Code Development Platform • Powered by AI Team</p>
            <div style="margin-top: 8px;">
                <span class="feature-badge">📝 Code Editor</span>
                <span class="feature-badge">🚀 App Builder</span>
                <span class="feature-badge">🤖 AI Assistant</span>
                <span class="feature-badge">👁️ Live Preview</span>
            </div>
        </div>
        """)

        with gr.Row():
            studio_mode = gr.Radio(
                choices=["📝 Code Editor", "🚀 App Builder", "💼 Business Suite", "🛠️ Dev Tools"],
                value="📝 Code Editor",
                label="Studio Mode",
                interactive=True,
                scale=3
            )
            gr.Radio(
                choices=["☀️ Light", "🌙 Dark"],
                value="☀️ Light",
                label="Theme",
                interactive=True,
                scale=1
            )

        # ==========================================
        # DEV TOOLS MODE
        # ==========================================
        with gr.Column(visible=False) as dev_tools_panel:
            try:
                from ai_dev_team.tools.dev_tools_ui import create_dev_tools_ui
                create_dev_tools_ui()
            except ImportError as e:
                gr.Markdown(f"### Dev Tools\n\nError loading: {e}")

        # ==========================================
        # BUSINESS SUITE MODE
        # ==========================================
        with gr.Column(visible=False) as business_suite_panel:
            try:
                from ai_dev_team.business_suite.suite_ui import create_business_suite_ui
                create_business_suite_ui()
            except ImportError as e:
                gr.Markdown(f"### Business Suite\n\nError loading: {e}")

        # ==========================================
        # APP BUILDER MODE
        # ==========================================
        with gr.Column(visible=False) as app_builder_panel:
            create_app_builder_ui(app_project_state, current_page_idx, home_dir)

        # ==========================================
        # CODE EDITOR MODE
        # ==========================================
        with gr.Column(visible=True) as code_editor_panel:

            # ==========================================
            # HIDDEN COMPONENTS (for event handler compatibility)
            # ==========================================
            with gr.Row(visible=False):
                new_project_name = gr.Textbox(placeholder="my-app", label="Name")
                project_type = gr.Dropdown(choices=["Python API", "Web App", "CLI Tool", "Script"], value="Python API", label="Type")
                create_project_btn = gr.Button("📁 Create", variant="primary")
                start_status = gr.Markdown("")
                quick_prompt = gr.Textbox()
                start_building_btn = gr.Button("")
                tpl_api = gr.Button("")
                tpl_web = gr.Button("")
                tpl_cli = gr.Button("")
                tpl_scraper = gr.Button("")
                tpl_bot = gr.Button("")
                tpl_data = gr.Button("")
                main_chatbot = gr.Chatbot()
                main_chat_input = gr.Textbox()
                main_chat_send = gr.Button("")
                main_chat_clear = gr.Button("")
                ai_mode_toggle = gr.Radio(choices=["a", "b"])
                ai_team_status = gr.Markdown("")
                btn_fix = gr.Button("")
                btn_improve = gr.Button("")
                btn_explain = gr.Button("")
                btn_generate = gr.Button("")
                btn_test = gr.Button("")
                btn_doc = gr.Button("")
                gen_prompt = gr.Textbox()
                gen_mode = gr.Dropdown(choices=["a"])
                gen_btn = gr.Button("")
                layout_mode = gr.Radio(choices=["Full"])

            # ==========================================
            # MAIN LAYOUT: 3-Panel IDE Style
            # ==========================================
            with gr.Row():

                # === LEFT SIDEBAR: Files & Projects ===
                with gr.Column(scale=1, min_width=240) as left_panel:

                    # Project selector (compact, always visible)
                    with gr.Row():
                        project_dropdown = gr.Dropdown(
                            choices=[],
                            label="📁 Project",
                            interactive=True,
                            scale=3
                        )
                        open_project_btn = gr.Button("Open", size="sm", variant="primary", scale=1)
                        refresh_project_list_btn = gr.Button("🔄", size="sm", scale=1)
                    project_info_display = gr.Markdown("", elem_classes=["small-text"])

                    # Directory path (compact)
                    with gr.Row():
                        dir_input = gr.Textbox(value=start_dir, label="", show_label=False, scale=4)
                        go_btn = gr.Button("→", size="sm", scale=1)

                    # Navigation buttons (single row)
                    with gr.Row():
                        up_btn = gr.Button("⬆️", size="sm")
                        home_btn = gr.Button("🏠", size="sm")
                        refresh_btn = gr.Button("🔄", size="sm")
                        dev_btn = gr.Button("📂", size="sm")

                    # File Explorer (primary - always visible, taller)
                    file_tree = gr.FileExplorer(
                        glob="**/*",
                        root_dir=start_dir,
                        ignore_glob="**/.git/**",
                        file_count="single",
                        label="",
                        height=400
                    )

                    # Quick file actions
                    with gr.Row():
                        btn_new_py = gr.Button("+ .py", size="sm")
                        btn_new_js = gr.Button("+ .js", size="sm")
                        btn_new_html = gr.Button("+ .html", size="sm")
                        delete_btn = gr.Button("🗑️", size="sm", variant="stop")

                    # Create new (collapsed)
                    with gr.Accordion("➕ New File/Folder", open=False):
                        new_file_name = gr.Textbox(placeholder="filename.py", label="Name", scale=3)
                        new_file_template = gr.Dropdown(choices=list(FILE_TEMPLATES.keys()), value="Empty", label="Template")
                        with gr.Row():
                            create_file_btn = gr.Button("📄 Create File", size="sm", variant="primary")
                            create_folder_btn = gr.Button("📁 Folder", size="sm")
                        new_folder_name = gr.Textbox(placeholder="folder_name", label="", visible=False)

                    # Hidden quick action buttons for compatibility
                    with gr.Row(visible=False):
                        btn_new_css = gr.Button("")
                        btn_new_react = gr.Button("")
                        btn_new_api = gr.Button("")

                # === CENTER PANEL: Code Editor (Primary Focus ~65%) ===
                with gr.Column(scale=4):

                    # Compact toolbar: File info + actions
                    with gr.Row():
                        file_selector = gr.Dropdown(
                            choices=["Untitled"],
                            value="Untitled",
                            label="",
                            allow_custom_value=True,
                            scale=4
                        )
                        language_select = gr.Dropdown(
                            choices=SUPPORTED_LANGUAGES,
                            value="python",
                            label="",
                            scale=1
                        )
                        save_btn = gr.Button("💾", variant="primary", size="sm", scale=1)
                        run_btn = gr.Button("▶️", variant="secondary", size="sm", scale=1)
                        stop_btn = gr.Button("⏹️", variant="stop", size="sm", scale=1)
                    file_name_display = gr.Textbox(value="Untitled", visible=False)

                    # Main code editor (large, primary focus)
                    code_editor = gr.Code(
                        language="python",
                        label="",
                        lines=24,
                        interactive=True
                    )

                    # Status bar (compact)
                    with gr.Row():
                        status_bar = gr.Textbox(value="Ready", label="", interactive=False, scale=3)
                        gr.Textbox(value="Ln 1, Col 1 | UTF-8", label="", interactive=False, scale=2)

                    # Terminal Output (always visible, collapsible)
                    with gr.Accordion("🖥️ Output", open=True) as run_preview_panel:
                        run_output = gr.Textbox(
                            value="",
                            label="",
                            lines=6,
                            max_lines=12,
                            interactive=False,
                            elem_classes=["terminal-output"]
                        )
                        with gr.Row():
                            clear_output_btn = gr.Button("Clear", size="sm")
                            run_status = gr.Markdown("*Ready*")
                            server_port = gr.Number(value=8000, label="Port", minimum=3000, maximum=65535, scale=1)

                    # Hidden components for compatibility
                    with gr.Row(visible=False):
                        save_as_btn = gr.Button("")
                        format_btn = gr.Button("")
                        lint_btn = gr.Button("")
                        toggle_preview_btn = gr.Button("")
                        preview_url = gr.Textbox(value="http://localhost:8000")
                        refresh_preview_btn = gr.Button("")
                        web_preview = gr.HTML(value="")
                        server_type = gr.Radio(choices=["Auto", "Python", "Node.js", "Static HTML"], value="Auto")
                        gr.Checkbox(value=True)

                # === RIGHT PANEL: AI Assistant + Tools (~20%) ===
                with gr.Column(scale=2, min_width=280) as right_panel:

                    # AI ASSISTANT (Primary - Always Visible)
                    gr.Markdown("### 🤖 AI Assistant")
                    top_chatbot = gr.Chatbot(label="", height=200, elem_classes=["ai-chat"])
                    with gr.Row():
                        top_chat_input = gr.Textbox(placeholder="Ask AI...", label="", lines=1, scale=4)
                        top_chat_send = gr.Button("Send", variant="primary", size="sm", scale=1)
                    with gr.Row():
                        top_btn_fix = gr.Button("🔧 Fix", size="sm")
                        top_btn_improve = gr.Button("✨ Improve", size="sm")
                        top_btn_explain = gr.Button("💡 Explain", size="sm")
                        top_btn_test = gr.Button("🧪 Test", size="sm")
                    with gr.Row():
                        top_ai_mode = gr.Radio(choices=["☁️ Cloud", "💻 Local"], value="☁️ Cloud", label="", scale=2)
                        top_ai_status = gr.Markdown("*7 agents*", elem_classes=["small-text"])

                    # TOOLS TABS (simplified)
                    with gr.Tabs() as right_tabs:

                        # 🔀 GIT - Most used tool, first tab
                        with gr.Tab("🔀 Git", id="git-tab"):
                            with gr.Row():
                                git_status_btn = gr.Button("Status", size="sm")
                                git_pull_btn = gr.Button("Pull", size="sm")
                                git_push_btn = gr.Button("Push", size="sm")
                            git_output = gr.Code(label="", language="shell", lines=5)
                            with gr.Row():
                                git_files_to_add = gr.Textbox(placeholder=".", label="", scale=2)
                                git_commit_msg = gr.Textbox(placeholder="Commit message", label="", scale=3)
                            with gr.Row():
                                git_add_btn = gr.Button("Stage", size="sm")
                                git_commit_btn = gr.Button("Commit", size="sm", variant="primary")
                            # Hidden git components
                            with gr.Row(visible=False):
                                git_fetch_btn = gr.Button("")
                                git_list_branches_btn = gr.Button("")
                                git_log_btn = gr.Button("")
                                git_branch_list = gr.Textbox()
                                git_log_output = gr.Code(language="shell")
                                git_branch_name = gr.Textbox()
                                git_create_branch_btn = gr.Button("")
                                git_checkout_btn = gr.Button("")
                                git_smart_commit_btn = gr.Button("")
                            gr.Row(visible=False)

                        # 🧪 TEST - Quick test runner
                        with gr.Tab("🧪 Test", id="test-tab"):
                            with gr.Row():
                                test_framework = gr.Dropdown(choices=["pytest", "unittest", "jest"], value="pytest", label="", scale=2)
                                run_tests_btn = gr.Button("▶️ Run", variant="primary", scale=1)
                            test_output = gr.Code(label="", language="shell", lines=8)
                            # Hidden test components
                            with gr.Row(visible=False):
                                test_path = gr.Textbox(value="tests/")
                                run_coverage_btn = gr.Button("")
                                test_verbose = gr.Checkbox(value=True)
                                test_pattern = gr.Textbox()
                                run_pattern_btn = gr.Button("")

                        # 👁️ PREVIEW
                        with gr.Tab("👁️ Preview", id="preview-tab"):
                            gr.Markdown("**Live Preview** - Opens in new browser window")
                            with gr.Row():
                                preview_port = gr.Number(value=8000, label="Port", minimum=3000, maximum=65535, scale=1)
                                open_preview_btn = gr.Button("🌐 Open in Browser", variant="primary", scale=2)
                            preview_frame = gr.HTML(value="<div style='padding:1rem;color:#666;text-align:center;min-height:80px;border:1px dashed #ccc;border-radius:8px;'>Click 'Open in Browser' to preview your app</div>")
                            with gr.Row():
                                preview_btn = gr.Button("🔄 Refresh Code Preview", size="sm")
                                auto_preview = gr.Checkbox(label="Auto-refresh", value=False)

                        # 🔍 REVIEW
                        with gr.Tab("🔍 Review", id="review-tab"):
                            review_types = gr.CheckboxGroup(choices=["Quality", "Security", "Performance"], value=["Quality"], label="")
                            review_btn = gr.Button("🔍 Review Code", variant="primary")
                            review_output = gr.Markdown("*Click Review to analyze*")

                        # 📋 MORE (Templates, Docker, etc)
                        with gr.Tab("📋 More", id="more-tab"):
                            with gr.Accordion("📋 Templates", open=True):
                                template_select = gr.Dropdown(choices=list(FILE_TEMPLATES.keys()), value="Empty", label="")
                                template_preview = gr.Code(value="", language="python", label="", lines=4, interactive=False)
                                use_template_btn = gr.Button("Insert", size="sm", variant="primary")

                            with gr.Accordion("🐳 Docker", open=False):
                                with gr.Row():
                                    docker_ps_btn = gr.Button("Containers", size="sm")
                                    docker_compose_up_btn = gr.Button("Up", size="sm", variant="primary")
                                    docker_compose_down_btn = gr.Button("Down", size="sm", variant="stop")
                                docker_output = gr.Code(label="", language="shell", lines=4)
                                # Hidden docker components
                                with gr.Row(visible=False):
                                    docker_images_btn = gr.Button("")
                                    docker_container_id = gr.Textbox()
                                    docker_logs_btn = gr.Button("")
                                    docker_stop_btn = gr.Button("")
                                    docker_image_name = gr.Textbox()
                                    docker_build_btn = gr.Button("")
                                    docker_start_btn = gr.Button("")
                                    docker_restart_btn = gr.Button("")

                            with gr.Accordion("⚙️ Environment", open=False):
                                gr.Radio(choices=["dev", "staging", "prod"], value="dev", label="")
                                env_content = gr.Code(label="", language="shell", lines=4, value="# KEY=value")
                                with gr.Row():
                                    load_env_btn = gr.Button("Load", size="sm")
                                    save_env_btn = gr.Button("Save", size="sm", variant="primary")
                                # Hidden env components
                                with gr.Row(visible=False):
                                    validate_env_btn = gr.Button("")
                                    env_status = gr.Markdown("")

                            # Hidden project memory components
                            with gr.Row(visible=False):
                                project_path_input = gr.Textbox()
                                project_name_input = gr.Textbox()
                                project_desc_input = gr.Textbox()
                                add_current_dir_btn = gr.Button("")
                                add_project_btn = gr.Button("")
                                add_project_status = gr.Markdown("")
                                project_list = gr.Dataframe()
                                refresh_projects_btn = gr.Button("")
                                selected_project_id = gr.Textbox()
                                reindex_project_btn = gr.Button("")
                                delete_project_btn = gr.Button("")
                                project_action_status = gr.Markdown("")
                                project_search_input = gr.Textbox()
                                project_search_btn = gr.Button("")
                                project_search_results = gr.Markdown("")
                                project_stats = gr.Markdown("")
                                refresh_stats_btn = gr.Button("")

                            with gr.Accordion("🚀 CI/CD", open=False):
                                cicd_platform = gr.Radio(
                                    choices=["GitHub Actions", "GitLab CI", "Jenkins"],
                                    value="GitHub Actions", label="Platform"
                                )
                                with gr.Row():
                                    cicd_test = gr.Checkbox(label="Test", value=True)
                                    cicd_lint = gr.Checkbox(label="Lint", value=True)
                                    cicd_deploy = gr.Checkbox(label="Deploy", value=False)
                                generate_cicd_btn = gr.Button("🔧 Generate", variant="primary")
                                cicd_output = gr.Code(label="Workflow", language="yaml", lines=10)
                                cicd_security = gr.Checkbox(label="Security", value=True, visible=False)
                                workflow_template = gr.Dropdown(choices=["Python", "Node.js", "Docker"], value="Python", label="Template", visible=False)
                                load_template_btn = gr.Button("📂 Template", size="sm", visible=False)

        # Mode switching
        def switch_mode(mode):
            # Returns: [dev_tools, business_suite, app_builder, code_editor]
            if mode == "🚀 App Builder":
                return gr.Column(visible=False), gr.Column(visible=False), gr.Column(visible=True), gr.Column(visible=False)
            elif mode == "💼 Business Suite":
                return gr.Column(visible=False), gr.Column(visible=True), gr.Column(visible=False), gr.Column(visible=False)
            elif mode == "🛠️ Dev Tools":
                return gr.Column(visible=True), gr.Column(visible=False), gr.Column(visible=False), gr.Column(visible=False)
            else:  # Code Editor
                return gr.Column(visible=False), gr.Column(visible=False), gr.Column(visible=False), gr.Column(visible=True)

        studio_mode.change(
            switch_mode,
            inputs=[studio_mode],
            outputs=[dev_tools_panel, business_suite_panel, app_builder_panel, code_editor_panel]
        )

        # === EVENT HANDLERS ===

        def change_layout(mode):
            if mode == "Full":
                return gr.Column(visible=True), gr.Column(visible=True)
            elif mode == "Editor Focus":
                return gr.Column(visible=False), gr.Column(visible=False)
            elif mode == "Preview Focus":
                return gr.Column(visible=False), gr.Column(visible=True)
            return gr.Column(visible=True), gr.Column(visible=True)

        def navigate_directory(path, current):
            path = os.path.expanduser(path) if path else current
            if os.path.isdir(path):
                abs_path = os.path.abspath(path)
                return abs_path, gr.FileExplorer(root_dir=abs_path), abs_path
            return current, gr.FileExplorer(root_dir=current), current

        def go_up(current):
            parent = os.path.dirname(current)
            return navigate_directory(parent, current)

        def go_home():
            home = os.path.expanduser("~")
            return navigate_directory(home, home)

        def go_dev():
            # Try Projects first, then Development, then Documents
            projects = os.path.expanduser("~/Development/Projects")
            dev = os.path.expanduser("~/Development")
            docs = os.path.expanduser("~/Documents")
            home = os.path.expanduser("~")

            if os.path.isdir(projects):
                return navigate_directory(projects, projects)
            elif os.path.isdir(dev):
                return navigate_directory(dev, dev)
            elif os.path.isdir(docs):
                return navigate_directory(docs, docs)
            else:
                return navigate_directory(home, home)

        def refresh_tree(current):
            return gr.FileExplorer(root_dir=current)

        def open_file(filepath, current_dir):
            if not filepath:
                return "", "python", "Untitled", "No file specified", None

            full_path = filepath if os.path.isabs(filepath) else os.path.join(current_dir, filepath)
            full_path = os.path.expanduser(full_path)

            if not os.path.isfile(full_path):
                return "", "python", "Untitled", f"File not found: {full_path}", None

            content = read_file(full_path)
            lang = detect_language(full_path)
            name = os.path.basename(full_path)
            return content, lang, name, f"Opened: {full_path}", full_path

        def save_current_file(content, filepath, filename, current_dir):
            if filepath:
                result = save_file(filepath, content)
            elif filename and filename != "Untitled":
                full_path = os.path.join(current_dir, filename)
                result = save_file(full_path, content)
            else:
                return "Please specify a file name (use Save As)"
            return result

        def save_as_file(content, new_name, current_dir):
            if not new_name:
                return "Please enter a file name", None, "Untitled"
            full_path = os.path.join(current_dir, new_name)
            result = save_file(full_path, content)
            return result, full_path, new_name

        def delete_file(filepath, current_dir):
            if not filepath:
                return "No file selected", gr.FileExplorer(root_dir=current_dir)
            full_path = filepath if os.path.isabs(filepath) else os.path.join(current_dir, filepath)
            result = delete_path(full_path)
            return result, gr.FileExplorer(root_dir=current_dir)

        def create_new_file(name, template, current_dir):
            if not name:
                return "Enter a file name", gr.FileExplorer(root_dir=current_dir), "", "", ""
            full_path = os.path.join(current_dir, name)
            content = FILE_TEMPLATES.get(template, "")
            result = save_file(full_path, content)
            lang = detect_language(name)
            return result, gr.FileExplorer(root_dir=current_dir), content, lang, name

        def create_new_folder(name, current_dir):
            if not name:
                return "Enter a folder name", gr.FileExplorer(root_dir=current_dir)
            full_path = os.path.join(current_dir, name)
            result = create_directory(full_path)
            return result, gr.FileExplorer(root_dir=current_dir)

        def quick_create_file(ext, template_name, current_dir):
            from datetime import datetime
            timestamp = datetime.now().strftime("%H%M%S")
            name = f"new_file_{timestamp}.{ext}"
            full_path = os.path.join(current_dir, name)
            content = FILE_TEMPLATES.get(template_name, "")
            save_file(full_path, content)
            lang = detect_language(name)
            return content, lang, name, f"Created: {name}", full_path, gr.FileExplorer(root_dir=current_dir)

        def update_preview(code, language, auto):
            if auto:
                return generate_preview(code, language)
            return gr.update()

        def format_code(code, language):
            if language == "python":
                formatted, msg = format_code_python(code)
                return formatted, msg
            return code, f"Formatting not available for {language}"

        def lint_code(code, language):
            if language == "python":
                return lint_code_python(code)
            return f"Linting not available for {language}"

        def update_template_preview(template_name):
            content = FILE_TEMPLATES.get(template_name, "")
            # Detect language from template name
            if "python" in template_name.lower() or template_name.startswith("Python") or template_name.startswith("FastAPI") or template_name.startswith("Test"):
                lang = "python"
            elif "react" in template_name.lower() or "jsx" in template_name.lower():
                lang = "jsx"
            elif "html" in template_name.lower():
                lang = "html"
            elif "css" in template_name.lower():
                lang = "css"
            elif "firebase" in template_name.lower():
                lang = "typescript"
            else:
                lang = "python"
            return gr.update(value=content, language=lang)

        def insert_template(template_name):
            content = FILE_TEMPLATES.get(template_name, "")
            # Detect language
            if "python" in template_name.lower() or template_name.startswith("Python") or template_name.startswith("FastAPI") or template_name.startswith("Test"):
                lang = "python"
            elif "react" in template_name.lower():
                lang = "jsx"
            elif "html" in template_name.lower():
                lang = "html"
            elif "css" in template_name.lower():
                lang = "css"
            elif "firebase" in template_name.lower():
                lang = "typescript"
            else:
                lang = "python"
            # Return content for editor and language for dropdown
            return gr.update(value=content, language=lang), lang

        # Chat with AI
        def chat_with_ai(message, history, code, language):
            if not message.strip():
                return "", history, code

            if message.lower().startswith("/generate "):
                desc = message[10:].strip()
                new_code = run_async(ai_generate_code(desc, language, code, "new"))
                history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": f"Generated {language} code. Check the editor!"}
                ]
                return "", history, new_code

            elif message.lower() == "/fix":
                new_code = run_async(ai_generate_code("", language, code, "fix"))
                history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": "Fixed the code. Check the editor!"}
                ]
                return "", history, new_code

            elif message.lower() == "/improve":
                new_code = run_async(ai_generate_code("improve and optimize", language, code, "refactor"))
                history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": "Improved the code. Check the editor!"}
                ]
                return "", history, new_code

            elif message.lower() == "/explain":
                explanation = run_async(ai_generate_code("", language, code, "explain"))
                history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": explanation}
                ]
                return "", history, code

            else:
                new_code = run_async(ai_generate_code(message, language, "", "new"))
                history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": f"Generated {language} code. Check the editor!"}
                ]
                return "", history, new_code

        def ai_generate(prompt, mode, code, language):
            if not prompt.strip() and mode == "new":
                return code, "Please enter a description"
            new_code = run_async(ai_generate_code(prompt, language, code, mode))
            return new_code, f"Generated ({mode})"

        def ai_review(code, language, types):
            if not code.strip():
                return "No code to review"
            result = run_async(ai_review_code(code, language, types))
            return result

        def quick_fix(code, language, history):
            return chat_with_ai("/fix", history, code, language)

        def quick_improve(code, language, history):
            return chat_with_ai("/improve", history, code, language)

        def quick_explain(code, language, history):
            return chat_with_ai("/explain", history, code, language)

        def quick_generate(history, code, language):
            return chat_with_ai("/generate Create something useful", history, code, language)

        def quick_test(code, language, history):
            return chat_with_ai("/test Write comprehensive unit tests for this code", history, code, language)

        def quick_doc(code, language, history):
            return chat_with_ai("/doc Add detailed docstrings and comments to this code", history, code, language)

        def clear_chat():
            return []

        # === PROJECT MEMORY FUNCTIONS ===

        def get_project_manager():
            """Get or create project manager instance."""
            try:
                from ai_dev_team.knowledge.project_memory import get_project_manager as gpm
                return gpm()
            except Exception as e:
                logger.error(f"Failed to load project manager: {e}")
                return None

        def get_project_choices():
            """Get list of projects for dropdown."""
            pm = get_project_manager()
            if not pm:
                return []
            projects = pm.list_projects()
            return [(f"{p.name} ({p.file_count} files)", p.id) for p in projects]

        def get_project_info(project_id):
            """Get info about a selected project."""
            if not project_id:
                return "*Select a project to open*"
            pm = get_project_manager()
            if not pm:
                return "*Project manager not available*"
            project = pm.get_project(project_id)
            if not project:
                return "*Project not found*"
            techs = ", ".join(project.technologies[:4]) if project.technologies else "Unknown"
            return f"""**{project.name}**
📁 {project.file_count} files | {project.total_size // 1024} KB
🛠️ {techs}
📍 `{project.path}`"""

        def open_project(project_id, current):
            """Open a project in the file explorer and load a main file."""
            # Default return: dir, tree, dir_input, info, code, lang, filename, filepath, file_selector
            default_dropdown = gr.Dropdown(choices=["Untitled"], value="Untitled")
            default = (current, gr.FileExplorer(root_dir=current), current, "*Please select a project*", "", "python", "Untitled", None, default_dropdown)

            if not project_id:
                return default
            pm = get_project_manager()
            if not pm:
                return (current, gr.FileExplorer(root_dir=current), current, "*Project manager not available*", "", "python", "Untitled", None, default_dropdown)
            project = pm.get_project(project_id)
            if not project:
                return (current, gr.FileExplorer(root_dir=current), current, "*Project not found*", "", "python", "Untitled", None, default_dropdown)

            # Navigate to project directory
            path = project.path
            if not os.path.isdir(path):
                return (current, gr.FileExplorer(root_dir=current), current, f"*Directory not found: {path}*", "", "python", "Untitled", None, default_dropdown)

            tree = gr.FileExplorer(root_dir=path)

            # Populate file selector with all project files
            file_choices = populate_file_selector(path)
            file_count = len(project_files["order"])

            # Find a main file to open
            main_files = [
                "README.md", "readme.md", "README.txt",
                "main.py", "app.py", "__init__.py", "index.py",
                "index.js", "index.ts", "index.tsx", "App.js", "App.tsx",
                "main.go", "main.rs", "Main.java",
                "package.json", "pyproject.toml", "Cargo.toml"
            ]

            main_file_path = None
            for mf in main_files:
                candidate = os.path.join(path, mf)
                if os.path.isfile(candidate):
                    main_file_path = candidate
                    break

            # If no main file, try to find any code file
            if not main_file_path:
                for f in os.listdir(path):
                    fp = os.path.join(path, f)
                    if os.path.isfile(fp) and any(f.endswith(ext) for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.md']):
                        main_file_path = fp
                        break

            # Load the file content
            if main_file_path and os.path.isfile(main_file_path):
                content = read_file(main_file_path)
                lang = detect_language(main_file_path)
                filename = os.path.basename(main_file_path)
                # Move main file to top of list
                add_to_recent(main_file_path, filename)
                file_choices = get_file_choices()
                selected_display = project_files["files"].get(main_file_path, filename)
                info = f"✅ Opened **{project.name}** ({file_count} files) - {filename}"
                file_dropdown = gr.Dropdown(choices=file_choices, value=selected_display)
                return (path, tree, path, info, content, lang, filename, main_file_path, file_dropdown)

            # No file to load, just navigate
            info = f"✅ Opened **{project.name}** ({file_count} files)"
            file_dropdown = gr.Dropdown(choices=file_choices, value=file_choices[0] if file_choices else "Untitled")
            return (path, tree, path, info, "", "python", "Untitled", None, file_dropdown)

        def load_project_list():
            """Load and format project list for display."""
            pm = get_project_manager()
            if not pm:
                return []

            projects = pm.list_projects()
            rows = []
            for p in projects:
                techs = ", ".join(p.technologies[:3]) if p.technologies else "-"
                added = p.created_at[:10] if p.created_at else "-"
                rows.append([p.id, p.name, p.file_count, techs, added])
            return rows

        def add_project(path, name, description):
            """Add a project to memory."""
            pm = get_project_manager()
            if not pm:
                return "❌ Project manager not available", load_project_list()

            if not path or not path.strip():
                return "❌ Please enter a project path", load_project_list()

            try:
                project = pm.add_project(
                    path=path.strip(),
                    name=name.strip() if name else None,
                    description=description.strip() if description else ""
                )
                return f"✅ Added **{project.name}** ({project.file_count} files indexed)", load_project_list()
            except Exception as e:
                return f"❌ Error: {str(e)}", load_project_list()

        def use_current_directory(current):
            """Fill in the current directory path."""
            return current

        def delete_project(project_id):
            """Delete a project from memory."""
            pm = get_project_manager()
            if not pm:
                return "❌ Project manager not available", load_project_list()

            if not project_id or not project_id.strip():
                return "❌ Please enter a project ID", load_project_list()

            try:
                success = pm.delete_project(project_id.strip())
                if success:
                    return "✅ Project deleted and archived", load_project_list()
                else:
                    return "❌ Project not found", load_project_list()
            except Exception as e:
                return f"❌ Error: {str(e)}", load_project_list()

        def reindex_project(project_id):
            """Re-index a project."""
            pm = get_project_manager()
            if not pm:
                return "❌ Project manager not available", load_project_list()

            if not project_id or not project_id.strip():
                return "❌ Please enter a project ID", load_project_list()

            try:
                project = pm.reindex_project(project_id.strip())
                if project:
                    return f"✅ Re-indexed **{project.name}** ({project.file_count} files)", load_project_list()
                else:
                    return "❌ Project not found", load_project_list()
            except Exception as e:
                return f"❌ Error: {str(e)}", load_project_list()

        def search_projects(query):
            """Search across all projects."""
            pm = get_project_manager()
            if not pm:
                return "❌ Project manager not available"

            if not query or not query.strip():
                return "Please enter a search query"

            try:
                results = pm.search_projects(query.strip(), limit=10)
                if not results:
                    return "No results found"

                output = f"### Found {len(results)} results\n\n"
                for r in results:
                    output += f"**{r['project_name']}** - `{r['file_path']}`\n"
                    output += f"```{r['language']}\n{r['content'][:200]}...\n```\n\n"
                return output
            except Exception as e:
                return f"❌ Error: {str(e)}"

        def get_project_stats():
            """Get project memory statistics."""
            pm = get_project_manager()
            if not pm:
                return "❌ Project manager not available"

            try:
                stats = pm.get_stats()
                return f"""
### 📊 Project Memory Stats

| Metric | Value |
|--------|-------|
| Total Projects | {stats['total_projects']} |
| Active Projects | {stats['active_projects']} |
| Total Files Indexed | {stats['total_files']} |
| Total Size | {stats['total_size_mb']:.2f} MB |
| Total Memories | {stats['total_memories']} |
                """
            except Exception as e:
                return f"❌ Error: {str(e)}"

        # === WIRE UP EVENTS ===

        # Layout
        layout_mode.change(change_layout, inputs=[layout_mode], outputs=[left_panel, right_panel])

        # Navigation
        go_btn.click(navigate_directory, inputs=[dir_input, current_dir], outputs=[current_dir, file_tree, dir_input])
        dir_input.submit(navigate_directory, inputs=[dir_input, current_dir], outputs=[current_dir, file_tree, dir_input])
        up_btn.click(go_up, inputs=[current_dir], outputs=[current_dir, file_tree, dir_input])
        home_btn.click(go_home, outputs=[current_dir, file_tree, dir_input])
        dev_btn.click(go_dev, outputs=[current_dir, file_tree, dir_input])
        refresh_btn.click(refresh_tree, inputs=[current_dir], outputs=[file_tree])

        # File operations - Project files tracking
        project_files = {"files": {}, "order": [], "project_dir": None}  # {filepath: display_name}

        CODE_EXTENSIONS = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.cpp', '.c', '.h',
            '.html', '.css', '.scss', '.json', '.yaml', '.yml', '.toml', '.md', '.txt',
            '.sh', '.bash', '.zsh', '.sql', '.graphql', '.proto', '.xml', '.env', '.gitignore'
        }

        SKIP_DIRS = {
            'node_modules', '__pycache__', '.git', '.venv', 'venv', 'env',
            'dist', 'build', '.next', '.nuxt', 'target', '.idea', '.vscode',
            'coverage', '.pytest_cache', '.mypy_cache', 'eggs', '*.egg-info'
        }

        def scan_project_files(project_dir, max_files=100):
            """Scan project directory for code files."""
            files = []
            if not project_dir or not os.path.isdir(project_dir):
                return files

            try:
                for root, dirs, filenames in os.walk(project_dir):
                    # Skip hidden and build directories
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

                    for fname in filenames:
                        if len(files) >= max_files:
                            break
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in CODE_EXTENSIONS or fname in ['.gitignore', '.env.example', 'Makefile', 'Dockerfile']:
                            full_path = os.path.join(root, fname)
                            # Create relative path for display
                            rel_path = os.path.relpath(full_path, project_dir)
                            files.append((full_path, rel_path))

                    if len(files) >= max_files:
                        break
            except Exception:
                pass

            # Sort by path for easier navigation
            files.sort(key=lambda x: x[1].lower())
            return files

        def populate_file_selector(project_dir):
            """Populate file selector with project files."""
            project_files["files"].clear()
            project_files["order"].clear()
            project_files["project_dir"] = project_dir

            files = scan_project_files(project_dir)
            for full_path, rel_path in files:
                project_files["files"][full_path] = rel_path
                project_files["order"].append(full_path)

            return get_file_choices()

        def add_to_recent(filepath, filename):
            """Add file to project files list (move to top)."""
            if filepath and os.path.isfile(filepath):
                # Get relative path if within project
                if project_files["project_dir"] and filepath.startswith(project_files["project_dir"]):
                    display = os.path.relpath(filepath, project_files["project_dir"])
                else:
                    display = f"{filename} ({os.path.dirname(filepath)[-30:]})"

                project_files["files"][filepath] = display
                # Move to front of order
                if filepath in project_files["order"]:
                    project_files["order"].remove(filepath)
                project_files["order"].insert(0, filepath)

        def get_file_choices():
            """Get dropdown choices for file selector."""
            choices = []
            for fp in project_files["order"]:
                if fp in project_files["files"]:
                    choices.append(project_files["files"][fp])
            return choices if choices else ["Untitled"]

        # Alias for compatibility
        def get_recent_choices():
            return get_file_choices()

        def on_file_select(filepath):
            """Handle file selection from FileExplorer."""
            if not filepath:
                return gr.update(), gr.update(), gr.update(), gr.update(), None, gr.update()

            # FileExplorer returns full path
            if os.path.isfile(filepath):
                content = read_file(filepath)
                lang = detect_language(filepath)
                filename = os.path.basename(filepath)
                add_to_recent(filepath, filename)
                display = project_files["files"].get(filepath, filename)
                return content, lang, filename, f"Opened: {filename}", filepath, gr.Dropdown(choices=get_file_choices(), value=display)

            return gr.update(), gr.update(), gr.update(), gr.update(), None, gr.update()

        def on_file_dropdown_select(selected, current_dir):
            """Handle file selection from dropdown."""
            if not selected or selected == "Untitled":
                return gr.update(), gr.update(), gr.update(), gr.update(), None

            # Find filepath from display name
            for fp, display in project_files["files"].items():
                if display == selected:
                    if os.path.isfile(fp):
                        content = read_file(fp)
                        lang = detect_language(fp)
                        filename = os.path.basename(fp)
                        # Move selected file to top
                        add_to_recent(fp, filename)
                        return content, lang, filename, f"Opened: {filename}", fp
                    else:
                        # File was deleted, remove from list
                        project_files["files"].pop(fp, None)
                        if fp in project_files["order"]:
                            project_files["order"].remove(fp)
                        return gr.update(), gr.update(), gr.update(), "File not found", None

            return gr.update(), gr.update(), gr.update(), gr.update(), None

        file_tree.change(
            on_file_select,
            inputs=[file_tree],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_selector]
        )

        file_selector.change(
            on_file_dropdown_select,
            inputs=[file_selector, current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path]
        )

        # Delete currently open file
        def delete_current_file(filepath, current_dir):
            if not filepath:
                return "No file open to delete", gr.FileExplorer(root_dir=current_dir), "", "python", "Untitled", None
            result = delete_path(filepath)
            return result, gr.FileExplorer(root_dir=current_dir), "", "python", "Untitled", None

        delete_btn.click(
            delete_current_file,
            inputs=[current_file_path, current_dir],
            outputs=[status_bar, file_tree, code_editor, language_select, file_name_display, current_file_path]
        )

        save_btn.click(
            save_current_file,
            inputs=[code_editor, current_file_path, file_name_display, current_dir],
            outputs=[status_bar]
        )
        save_as_btn.click(
            save_as_file,
            inputs=[code_editor, file_name_display, current_dir],
            outputs=[status_bar, current_file_path, file_name_display]
        )

        # Create new
        create_file_btn.click(
            create_new_file,
            inputs=[new_file_name, new_file_template, current_dir],
            outputs=[status_bar, file_tree, code_editor, language_select, file_name_display]
        )
        create_folder_btn.click(
            create_new_folder,
            inputs=[new_folder_name, current_dir],
            outputs=[status_bar, file_tree]
        )

        # Quick create buttons
        btn_new_py.click(
            lambda d: quick_create_file("py", "Python Script", d),
            inputs=[current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_tree]
        )
        btn_new_js.click(
            lambda d: quick_create_file("js", "Empty", d),
            inputs=[current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_tree]
        )
        btn_new_html.click(
            lambda d: quick_create_file("html", "HTML Page", d),
            inputs=[current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_tree]
        )
        btn_new_css.click(
            lambda d: quick_create_file("css", "CSS Stylesheet", d),
            inputs=[current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_tree]
        )
        btn_new_react.click(
            lambda d: quick_create_file("jsx", "React Component", d),
            inputs=[current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_tree]
        )
        btn_new_api.click(
            lambda d: quick_create_file("py", "FastAPI Endpoint", d),
            inputs=[current_dir],
            outputs=[code_editor, language_select, file_name_display, status_bar, current_file_path, file_tree]
        )

        # Editor operations
        format_btn.click(format_code, inputs=[code_editor, language_select], outputs=[code_editor, status_bar])
        lint_btn.click(lint_code, inputs=[code_editor, language_select], outputs=[status_bar])
        language_select.change(lambda lang: gr.Code(language=lang), inputs=[language_select], outputs=[code_editor])

        # Run & Preview Panel
        run_btn.click(
            run_code_handler,
            inputs=[code_editor, language_select, current_file_path, current_dir, server_port, server_type],
            outputs=[run_output, run_status, web_preview, preview_url]
        )
        stop_btn.click(
            stop_code_handler,
            outputs=[run_output, run_status]
        )
        clear_output_btn.click(
            lambda: ("", "*Ready*"),
            outputs=[run_output, run_status]
        )
        refresh_preview_btn.click(
            generate_preview_iframe,
            inputs=[preview_url],
            outputs=[web_preview]
        )
        toggle_preview_btn.click(
            lambda: gr.Accordion(open=True),
            outputs=[run_preview_panel]
        )

        # Preview (existing - for in-tab preview)
        preview_btn.click(generate_preview, inputs=[code_editor, language_select], outputs=[preview_frame])
        code_editor.change(update_preview, inputs=[code_editor, language_select, auto_preview], outputs=[preview_frame])

        # Open preview in browser
        def open_browser_preview(port):
            url = f"http://localhost:{int(port)}"
            try:
                webbrowser.open(url)
                return f"<div style='padding:1rem;text-align:center;background:#e8f5e9;border-radius:8px;'><p style='color:#2e7d32;margin:0;'>✅ Opened <a href='{url}' target='_blank'>{url}</a> in browser</p></div>"
            except Exception as e:
                return f"<div style='padding:1rem;color:#c62828;'>Failed to open browser: {e}</div>"

        open_preview_btn.click(open_browser_preview, inputs=[preview_port], outputs=[preview_frame])

        # Templates
        template_select.change(update_template_preview, inputs=[template_select], outputs=[template_preview])
        use_template_btn.click(insert_template, inputs=[template_select], outputs=[code_editor, language_select])

        # === GETTING STARTED WIZARD ===
        def create_new_project(name, proj_type, current):
            """Create a new project folder and setup."""
            if not name:
                return "❌ Please enter a project name", current

            # Sanitize name
            safe_name = name.lower().replace(" ", "-").replace("_", "-")

            # Create in Development/Projects
            base_dir = os.path.expanduser("~/Development/Projects")
            os.makedirs(base_dir, exist_ok=True)
            project_dir = os.path.join(base_dir, safe_name)

            if os.path.exists(project_dir):
                return f"⚠️ Project '{safe_name}' already exists. Opening it...", project_dir

            os.makedirs(project_dir)

            # Create basic structure based on type
            if proj_type == "Python API":
                os.makedirs(os.path.join(project_dir, "app"), exist_ok=True)
                with open(os.path.join(project_dir, "app", "__init__.py"), "w") as f:
                    f.write('"""App package."""\n')
                with open(os.path.join(project_dir, "main.py"), "w") as f:
                    f.write('"""Main entry point."""\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef root():\n    return {"message": "Hello World"}\n')
                with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
                    f.write("fastapi\nuvicorn\n")
            elif proj_type == "Web App":
                with open(os.path.join(project_dir, "index.html"), "w") as f:
                    f.write('<!DOCTYPE html>\n<html>\n<head>\n    <title>My App</title>\n</head>\n<body>\n    <h1>Hello World</h1>\n</body>\n</html>\n')
            elif proj_type == "CLI Tool":
                with open(os.path.join(project_dir, "cli.py"), "w") as f:
                    f.write('"""CLI Tool."""\nimport argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    args = parser.parse_args()\n    print("Hello from CLI!")\n\nif __name__ == "__main__":\n    main()\n')
            else:
                with open(os.path.join(project_dir, "main.py"), "w") as f:
                    f.write('"""Main script."""\n\ndef main():\n    print("Hello World")\n\nif __name__ == "__main__":\n    main()\n')

            # Add to project memory
            try:
                pm = get_project_manager()
                pm.add_project(project_dir, safe_name, f"New {proj_type} project")
            except Exception:
                logger.debug("Failed to add project to project memory: %s", safe_name)

            return f"✅ Created project: **{safe_name}**\n\nLocation: `{project_dir}`\n\n→ Now go to **Step 2** and tell the AI what to build!", project_dir

        def start_building_from_wizard(prompt, proj_name, current_dir):
            """Start building from the wizard prompt."""
            if not prompt:
                return "", [], "", "❌ Please describe what you want to build"

            # If project name given but no project created yet, create it
            if proj_name and not os.path.exists(os.path.join(os.path.expanduser("~/Development/Projects"), proj_name)):
                create_new_project(proj_name, "Other", current_dir)

            return prompt, [], "", f"🤖 AI Team is working on: {prompt[:50]}..."

        def use_template(template_name, current_dir):
            """Apply a quick template."""
            templates = {
                "🔌 REST API": "Build a REST API with FastAPI that has:\n- User registration and login endpoints\n- JWT authentication\n- CRUD operations for a 'items' resource\n- Input validation with Pydantic",
                "🌐 Web App": "Create a responsive web application with:\n- Modern HTML5 structure\n- CSS styling with flexbox/grid\n- Interactive JavaScript features\n- Mobile-friendly design",
                "💻 CLI Tool": "Build a command-line tool that:\n- Accepts arguments and options\n- Has a help menu\n- Provides colored output\n- Handles errors gracefully",
                "🕷️ Scraper": "Create a web scraper that:\n- Fetches data from a URL\n- Parses HTML with BeautifulSoup\n- Extracts specific information\n- Saves results to JSON/CSV",
                "🤖 Discord Bot": "Build a Discord bot that:\n- Responds to commands\n- Has a help command\n- Can moderate messages\n- Stores data persistently",
                "📊 Data Script": "Create a data processing script that:\n- Reads CSV/JSON files\n- Cleans and transforms data\n- Generates summary statistics\n- Creates visualizations",
            }
            prompt = templates.get(template_name, "Build something cool")
            return prompt, f"Template loaded: {template_name}"

        create_project_btn.click(
            create_new_project,
            inputs=[new_project_name, project_type, current_dir],
            outputs=[start_status, current_dir]
        )

        start_building_btn.click(
            start_building_from_wizard,
            inputs=[quick_prompt, new_project_name, current_dir],
            outputs=[main_chat_input, main_chatbot, quick_prompt, start_status]
        ).then(
            lambda: gr.Tabs(selected="ai-team-main"),
            outputs=[right_tabs]
        )

        # Template buttons
        tpl_api.click(lambda d: use_template("🔌 REST API", d), inputs=[current_dir], outputs=[quick_prompt, start_status])
        tpl_web.click(lambda d: use_template("🌐 Web App", d), inputs=[current_dir], outputs=[quick_prompt, start_status])
        tpl_cli.click(lambda d: use_template("💻 CLI Tool", d), inputs=[current_dir], outputs=[quick_prompt, start_status])
        tpl_scraper.click(lambda d: use_template("🕷️ Scraper", d), inputs=[current_dir], outputs=[quick_prompt, start_status])
        tpl_bot.click(lambda d: use_template("🤖 Discord Bot", d), inputs=[current_dir], outputs=[quick_prompt, start_status])
        tpl_data.click(lambda d: use_template("📊 Data Script", d), inputs=[current_dir], outputs=[quick_prompt, start_status])

        # AI Team Chat (primary interface in right panel)
        main_chat_send.click(
            chat_with_ai,
            inputs=[main_chat_input, main_chatbot, code_editor, language_select],
            outputs=[main_chat_input, main_chatbot, code_editor]
        )
        main_chat_input.submit(
            chat_with_ai,
            inputs=[main_chat_input, main_chatbot, code_editor, language_select],
            outputs=[main_chat_input, main_chatbot, code_editor]
        )
        main_chat_clear.click(clear_chat, outputs=[main_chatbot])

        # TOP AI Team Chat (at top of screen)
        top_chat_send.click(
            chat_with_ai,
            inputs=[top_chat_input, top_chatbot, code_editor, language_select],
            outputs=[top_chat_input, top_chatbot, code_editor]
        )
        top_chat_input.submit(
            chat_with_ai,
            inputs=[top_chat_input, top_chatbot, code_editor, language_select],
            outputs=[top_chat_input, top_chatbot, code_editor]
        )

        # Top AI quick buttons
        top_btn_fix.click(quick_fix, inputs=[code_editor, language_select, top_chatbot], outputs=[top_chat_input, top_chatbot, code_editor])
        top_btn_improve.click(quick_improve, inputs=[code_editor, language_select, top_chatbot], outputs=[top_chat_input, top_chatbot, code_editor])
        top_btn_explain.click(quick_explain, inputs=[code_editor, language_select, top_chatbot], outputs=[top_chat_input, top_chatbot, code_editor])
        top_btn_test.click(quick_test, inputs=[code_editor, language_select, top_chatbot], outputs=[top_chat_input, top_chatbot, code_editor])

        # Top AI mode toggle
        def switch_top_ai_mode(mode_choice):
            local_only = "Local" in mode_choice
            set_local_only_mode(local_only)
            return get_team_status()
        top_ai_mode.change(switch_top_ai_mode, inputs=[top_ai_mode], outputs=[top_ai_status])

        # AI Team mode toggle (Cloud vs Local)
        def switch_ai_mode(mode_choice):
            local_only = "Local" in mode_choice
            set_local_only_mode(local_only)
            return get_team_status()

        ai_mode_toggle.change(switch_ai_mode, inputs=[ai_mode_toggle], outputs=[ai_team_status])

        # Initialize AI Team status on load
        demo.load(lambda: get_team_status(), outputs=[ai_team_status])

        # AI Quick buttons (all use main chatbot)
        btn_generate.click(quick_generate, inputs=[main_chatbot, code_editor, language_select], outputs=[main_chat_input, main_chatbot, code_editor])
        btn_fix.click(quick_fix, inputs=[code_editor, language_select, main_chatbot], outputs=[main_chat_input, main_chatbot, code_editor])
        btn_improve.click(quick_improve, inputs=[code_editor, language_select, main_chatbot], outputs=[main_chat_input, main_chatbot, code_editor])
        btn_explain.click(quick_explain, inputs=[code_editor, language_select, main_chatbot], outputs=[main_chat_input, main_chatbot, code_editor])
        btn_test.click(quick_test, inputs=[code_editor, language_select, main_chatbot], outputs=[main_chat_input, main_chatbot, code_editor])
        btn_doc.click(quick_doc, inputs=[code_editor, language_select, main_chatbot], outputs=[main_chat_input, main_chatbot, code_editor])

        # AI Generator
        gen_btn.click(ai_generate, inputs=[gen_prompt, gen_mode, code_editor, language_select], outputs=[code_editor, status_bar])

        # Code Review
        review_btn.click(ai_review, inputs=[code_editor, language_select, review_types], outputs=[review_output])

        # Project Memory Management
        add_current_dir_btn.click(use_current_directory, inputs=[current_dir], outputs=[project_path_input])
        add_project_btn.click(add_project, inputs=[project_path_input, project_name_input, project_desc_input], outputs=[add_project_status, project_list])
        refresh_projects_btn.click(lambda: load_project_list(), outputs=[project_list])
        delete_project_btn.click(delete_project, inputs=[selected_project_id], outputs=[project_action_status, project_list])
        reindex_project_btn.click(reindex_project, inputs=[selected_project_id], outputs=[project_action_status, project_list])
        project_search_btn.click(search_projects, inputs=[project_search_input], outputs=[project_search_results])
        refresh_stats_btn.click(get_project_stats, outputs=[project_stats])

        # Load initial project list
        demo.load(lambda: load_project_list(), outputs=[project_list])

        # My Projects panel (left sidebar)
        demo.load(lambda: gr.Dropdown(choices=get_project_choices()), outputs=[project_dropdown])
        refresh_project_list_btn.click(lambda: gr.Dropdown(choices=get_project_choices()), outputs=[project_dropdown])
        project_dropdown.change(get_project_info, inputs=[project_dropdown], outputs=[project_info_display])
        open_project_btn.click(
            open_project,
            inputs=[project_dropdown, current_dir],
            outputs=[current_dir, file_tree, dir_input, project_info_display, code_editor, language_select, file_name_display, current_file_path, file_selector]
        )

        # === GIT EVENT HANDLERS ===
        def run_git_command(cmd, cwd=None):
            """Run git command and return output."""
            import subprocess
            try:
                cwd = cwd or os.getcwd()
                result = subprocess.run(
                    cmd, shell=True, cwd=cwd,
                    capture_output=True, text=True, timeout=30
                )
                output = result.stdout + result.stderr
                return output if output.strip() else "Command completed successfully"
            except Exception as e:
                return f"Error: {e}"

        def git_status(current_dir):
            return run_git_command("git status", current_dir)

        def git_pull(current_dir):
            return run_git_command("git pull", current_dir)

        def git_push(current_dir):
            return run_git_command("git push", current_dir)

        def git_fetch(current_dir):
            return run_git_command("git fetch --all", current_dir)

        def git_add(files, current_dir):
            return run_git_command(f"git add {files}", current_dir)

        def git_commit(msg, current_dir):
            if not msg:
                return "Please enter a commit message"
            return run_git_command(f'git commit -m "{msg}"', current_dir)

        def git_smart_commit(current_dir):
            diff = run_git_command("git diff --staged", current_dir)
            if not diff or "Error" in diff:
                return "No staged changes. Stage files first with 'git add'"
            # Use AI to generate commit message (simplified for now)
            return f"# Suggested commit message based on diff:\n# (Review and modify as needed)\n\nUpdate: Code changes\n\n{diff[:500]}"

        def git_list_branches(current_dir):
            return run_git_command("git branch -a", current_dir)

        def git_create_branch(name, current_dir):
            if not name:
                return "Please enter a branch name"
            return run_git_command(f"git checkout -b {name}", current_dir)

        def git_checkout(name, current_dir):
            if not name:
                return "Please enter a branch name"
            return run_git_command(f"git checkout {name}", current_dir)

        def git_log(current_dir):
            return run_git_command("git log --oneline -20", current_dir)

        git_status_btn.click(git_status, inputs=[current_dir], outputs=[git_output])
        git_pull_btn.click(git_pull, inputs=[current_dir], outputs=[git_output])
        git_push_btn.click(git_push, inputs=[current_dir], outputs=[git_output])
        git_fetch_btn.click(git_fetch, inputs=[current_dir], outputs=[git_output])
        git_add_btn.click(git_add, inputs=[git_files_to_add, current_dir], outputs=[git_output])
        git_commit_btn.click(git_commit, inputs=[git_commit_msg, current_dir], outputs=[git_output])
        git_smart_commit_btn.click(git_smart_commit, inputs=[current_dir], outputs=[git_commit_msg])
        git_list_branches_btn.click(git_list_branches, inputs=[current_dir], outputs=[git_branch_list])
        git_create_branch_btn.click(git_create_branch, inputs=[git_branch_name, current_dir], outputs=[git_output])
        git_checkout_btn.click(git_checkout, inputs=[git_branch_name, current_dir], outputs=[git_output])
        git_log_btn.click(git_log, inputs=[current_dir], outputs=[git_log_output])

        # === DOCKER EVENT HANDLERS ===
        def run_docker_command(cmd):
            """Run docker command and return output."""
            import subprocess
            try:
                result = subprocess.run(
                    cmd, shell=True,
                    capture_output=True, text=True, timeout=60
                )
                output = result.stdout + result.stderr
                return output if output.strip() else "Command completed successfully"
            except Exception as e:
                return f"Error: {e}"

        def docker_ps():
            return run_docker_command("docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}'")

        def docker_images():
            return run_docker_command("docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'")

        def docker_compose_up(current_dir):
            return run_docker_command(f"cd {current_dir} && docker-compose up -d")

        def docker_compose_down(current_dir):
            return run_docker_command(f"cd {current_dir} && docker-compose down")

        def docker_logs(container_id):
            if not container_id:
                return "Please enter a container ID or name"
            return run_docker_command(f"docker logs --tail 50 {container_id}")

        def docker_stop(container_id):
            if not container_id:
                return "Please enter a container ID or name"
            return run_docker_command(f"docker stop {container_id}")

        def docker_start(container_id):
            if not container_id:
                return "Please enter a container ID or name"
            return run_docker_command(f"docker start {container_id}")

        def docker_restart(container_id):
            if not container_id:
                return "Please enter a container ID or name"
            return run_docker_command(f"docker restart {container_id}")

        def docker_build(image_name, current_dir):
            if not image_name:
                return "Please enter an image name"
            return run_docker_command(f"cd {current_dir} && docker build -t {image_name} .")

        docker_ps_btn.click(docker_ps, outputs=[docker_output])
        docker_images_btn.click(docker_images, outputs=[docker_output])
        docker_compose_up_btn.click(docker_compose_up, inputs=[current_dir], outputs=[docker_output])
        docker_compose_down_btn.click(docker_compose_down, inputs=[current_dir], outputs=[docker_output])
        docker_logs_btn.click(docker_logs, inputs=[docker_container_id], outputs=[docker_output])
        docker_stop_btn.click(docker_stop, inputs=[docker_container_id], outputs=[docker_output])
        docker_start_btn.click(docker_start, inputs=[docker_container_id], outputs=[docker_output])
        docker_restart_btn.click(docker_restart, inputs=[docker_container_id], outputs=[docker_output])
        docker_build_btn.click(docker_build, inputs=[docker_image_name, current_dir], outputs=[docker_output])

        # === TESTING EVENT HANDLERS ===
        def run_tests(framework, path, verbose, current_dir):
            """Run tests with specified framework."""
            import subprocess
            try:
                if framework == "pytest":
                    cmd = f"cd {current_dir} && pytest {path}" + (" -v" if verbose else "")
                elif framework == "unittest":
                    cmd = f"cd {current_dir} && python -m unittest discover {path}" + (" -v" if verbose else "")
                elif framework == "vitest":
                    cmd = f"cd {current_dir} && npx vitest run {path}"
                elif framework == "jest":
                    cmd = f"cd {current_dir} && npx jest {path}" + (" --verbose" if verbose else "")
                elif framework == "playwright":
                    cmd = f"cd {current_dir} && npx playwright test {path}"
                else:
                    return f"Unknown framework: {framework}"

                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                return result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                return "Test execution timed out (120s limit)"
            except Exception as e:
                return f"Error: {e}"

        def run_coverage(framework, path, current_dir):
            """Run tests with coverage."""
            import subprocess
            try:
                if framework == "pytest":
                    cmd = f"cd {current_dir} && pytest {path} --cov --cov-report=term-missing"
                elif framework == "vitest":
                    cmd = f"cd {current_dir} && npx vitest run --coverage"
                elif framework == "jest":
                    cmd = f"cd {current_dir} && npx jest --coverage"
                else:
                    return f"Coverage not configured for {framework}"

                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
                return result.stdout + result.stderr
            except Exception as e:
                return f"Error: {e}"

        def run_pattern_tests(framework, pattern, current_dir):
            """Run tests matching pattern."""
            import subprocess
            try:
                if framework == "pytest":
                    cmd = f"cd {current_dir} && pytest -k '{pattern}' -v"
                elif framework == "jest":
                    cmd = f"cd {current_dir} && npx jest --testNamePattern='{pattern}'"
                else:
                    return f"Pattern matching not configured for {framework}"

                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                return result.stdout + result.stderr
            except Exception as e:
                return f"Error: {e}"

        run_tests_btn.click(run_tests, inputs=[test_framework, test_path, test_verbose, current_dir], outputs=[test_output])
        run_coverage_btn.click(run_coverage, inputs=[test_framework, test_path, current_dir], outputs=[test_output])
        run_pattern_btn.click(run_pattern_tests, inputs=[test_framework, test_pattern, current_dir], outputs=[test_output])

        # === ENVIRONMENT EVENT HANDLERS ===
        def load_env_file(current_dir):
            """Load .env file from current directory."""
            env_path = os.path.join(current_dir, ".env")
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    return f.read(), "✅ Loaded .env file"
            return "# No .env file found\n# Add your environment variables here\nDEBUG=true\n", "⚠️ No .env file found, created template"

        def save_env_file(content, current_dir):
            """Save .env file to current directory."""
            env_path = os.path.join(current_dir, ".env")
            try:
                with open(env_path, 'w') as f:
                    f.write(content)
                return "✅ Saved .env file"
            except Exception as e:
                return f"❌ Error saving: {e}"

        def validate_env(content):
            """Validate environment variables."""
            issues = []
            lines = content.strip().split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    issues.append(f"Line {i}: Missing '=' in variable definition")
                elif line.startswith('='):
                    issues.append(f"Line {i}: Variable name is empty")

            if issues:
                return "⚠️ Issues found:\n" + "\n".join(issues)
            return "✅ Environment file is valid"

        load_env_btn.click(load_env_file, inputs=[current_dir], outputs=[env_content, env_status])
        save_env_btn.click(save_env_file, inputs=[env_content, current_dir], outputs=[env_status])
        validate_env_btn.click(validate_env, inputs=[env_content], outputs=[env_status])

        # === CI/CD EVENT HANDLERS ===
        def generate_cicd_workflow(platform, test, lint, security, deploy, template):
            """Generate CI/CD workflow file."""
            if platform == "GitHub Actions":
                workflow = generate_github_actions(test, lint, security, deploy, template)
            elif platform == "GitLab CI":
                workflow = generate_gitlab_ci(test, lint, security, deploy, template)
            else:
                workflow = "# Jenkins pipeline coming soon"
            return workflow

        def generate_github_actions(test, lint, security, deploy, template):
            """Generate GitHub Actions workflow."""
            is_python = template in ["Python App", "Full Stack"]
            is_node = template in ["Node.js App", "Full Stack"]
            is_docker = template in ["Docker Build", "Full Stack"]

            yaml = """name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
"""
            if test:
                if is_python:
                    yaml += """  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v4

"""
                if is_node:
                    yaml += """  test-node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test

"""
            if lint:
                if is_python:
                    yaml += """  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff black mypy
      - run: ruff check .
      - run: black --check .

"""
                if is_node:
                    yaml += """  lint-node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run lint

"""
            if security:
                yaml += """  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run security scan
        uses: github/codeql-action/analyze@v3

"""
            if deploy and is_docker:
                yaml += """  deploy:
    needs: [test, lint]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker image
        run: |
          docker build -t ${{ secrets.REGISTRY }}/${{ github.repository }}:${{ github.sha }} .
          docker push ${{ secrets.REGISTRY }}/${{ github.repository }}:${{ github.sha }}

"""
            return yaml

        def generate_gitlab_ci(test, lint, security, deploy, template):
            """Generate GitLab CI configuration."""
            yaml = """stages:
  - test
  - lint
  - security
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

"""
            if test:
                yaml += """test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pytest --cov

"""
            if lint:
                yaml += """lint:
  stage: lint
  image: python:3.11
  script:
    - pip install ruff black
    - ruff check .
    - black --check .

"""
            if security:
                yaml += """security:
  stage: security
  image: python:3.11
  script:
    - pip install safety
    - safety check

"""
            if deploy:
                yaml += """deploy:
  stage: deploy
  only:
    - main
  script:
    - echo "Deploying..."

"""
            return yaml

        def load_workflow_template(template):
            """Load a predefined workflow template."""
            return generate_github_actions(True, True, True, False, template)

        generate_cicd_btn.click(
            generate_cicd_workflow,
            inputs=[cicd_platform, cicd_test, cicd_lint, cicd_security, cicd_deploy, workflow_template],
            outputs=[cicd_output]
        )
        load_template_btn.click(load_workflow_template, inputs=[workflow_template], outputs=[cicd_output])

    return demo


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("AI Team Studio - No-Code Development Platform")
    print("=" * 60)

    print("\nInitializing AI Team...")
    t = get_team()
    print(f"✓ {len(t.agents)} agents ready")

    print("\n" + "=" * 60)
    print("Features:")
    print("  🛠️ Dev Tools - One-click project scaffolding & deploy")
    print("  💼 Business Suite - Client management & AI chatbots")
    print("  🚀 App Builder - Visual no-code app creation")
    print("  📝 Code Editor - AI-powered coding assistant")
    print("")
    print("Deployment Targets:")
    print("  ☁️ Cloud Run | ⚡ Cloud Functions | 🔥 Firebase")
    print("  ▲ Vercel | 🐳 Docker | 💻 Local Server")
    print("")
    print("Project Templates:")
    print("  🌐 Landing Page | ⚛️ React App | ▲ Next.js")
    print("  🚀 FastAPI | ⚡ Cloud Function | 🤖 Chatbot")
    print("=" * 60)
    print("\nOpen: http://localhost:7861")
    print("=" * 60 + "\n")

    ui = create_studio_ui()
    # Gradio auth — set GRADIO_USERNAME and GRADIO_PASSWORD env vars to enable
    auth_user = os.environ.get("GRADIO_USERNAME")
    auth_pass = os.environ.get("GRADIO_PASSWORD")
    auth_config = [(auth_user, auth_pass)] if auth_user and auth_pass else None

    ui.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7861)),
        share=False,
        show_error=True,
        favicon_path=None,
        auth=auth_config,
        root_path=os.environ.get("GRADIO_ROOT_PATH", ""),
    )


if __name__ == "__main__":
    main()
