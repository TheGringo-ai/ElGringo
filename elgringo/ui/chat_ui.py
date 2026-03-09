#!/usr/bin/env python3
"""
AI Team Chat UI
===============

A Gradio-based chat interface for the AI Team Platform.
Supports natural language + commands: /react, /reason, /plan

Run with: python -m elgringo.chat_ui
Opens at: http://localhost:7860
"""

import asyncio
import gradio as gr
import logging
import os
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global team instance
team = None

# Chat history persistence
_CHAT_HISTORY_DIR = os.path.join(os.path.expanduser("~"), ".ai-dev-team", "chat_history")
_CHAT_HISTORY_FILE = os.path.join(_CHAT_HISTORY_DIR, "last_session.json")
_MAX_PERSISTED_MESSAGES = 20


def _save_chat_history(history: list):
    """Persist chat history to disk."""
    try:
        os.makedirs(_CHAT_HISTORY_DIR, exist_ok=True)
        # Keep only recent messages
        trimmed = history[-_MAX_PERSISTED_MESSAGES * 2:]  # Each exchange = 2 entries
        with open(_CHAT_HISTORY_FILE, "w") as f:
            import json
            json.dump(trimmed, f, indent=2)
    except Exception as e:
        logger.debug(f"Could not save chat history: {e}")


def _load_chat_history() -> list:
    """Load persisted chat history from disk."""
    try:
        if os.path.exists(_CHAT_HISTORY_FILE):
            with open(_CHAT_HISTORY_FILE, "r") as f:
                import json
                history = json.load(f)
                return history[-_MAX_PERSISTED_MESSAGES * 2:]
    except Exception as e:
        logger.debug(f"Could not load chat history: {e}")
    return []


def get_team():
    """Get or create the AI Team instance."""
    global team
    if team is None:
        from elgringo import AIDevTeam
        team = AIDevTeam(project_name="chat-ui", enable_memory=True)
        logger.info(f"AI Team initialized with {len(team.agents)} agents")
    return team


def format_react_trace(trace) -> str:
    """Format ReAct trace for display."""
    lines = []
    lines.append(f"**ReAct Agent** | {len(trace.steps)} steps | {trace.execution_time:.2f}s\n")

    for step in trace.steps:
        lines.append(f"\n**Step {step.step_number}:**")
        lines.append(f"- Thought: {step.thought[:300]}{'...' if len(step.thought) > 300 else ''}")
        if step.action:
            lines.append(f"- Action: `{step.action}`")
        if step.observation:
            obs = step.observation[:200] + '...' if len(step.observation) > 200 else step.observation
            lines.append(f"- Observation: {obs}")

    lines.append(f"\n---\n**Final Answer:**\n{trace.final_answer}")
    return "\n".join(lines)


def format_reasoning_chain(chain) -> str:
    """Format reasoning chain for display."""
    lines = []
    lines.append(f"**Chain-of-Thought** | {len(chain.steps)} steps | Confidence: {chain.confidence:.0%}\n")

    for step in chain.steps:
        lines.append(f"\n**Step {step.step_number}:**")
        lines.append(f"{step.content}")

    lines.append(f"\n---\n**Conclusion:**\n{chain.conclusion}")
    return "\n".join(lines)


def format_plan(plan) -> str:
    """Format execution plan for display."""
    lines = []
    progress = plan.get_progress()
    lines.append(f"**Task Planner** | {progress['completed']}/{progress['total']} steps | {plan.status.value}\n")

    status_icons = {
        "pending": "[PENDING]",
        "in_progress": "[IN PROGRESS]",
        "completed": "[DONE]",
        "failed": "[FAILED]",
        "skipped": "[SKIPPED]",
        "blocked": "[BLOCKED]",
    }

    for step in plan.steps:
        icon = status_icons.get(step.status.value, "[?]")
        lines.append(f"{icon} **{step.description}**")
        if step.error:
            lines.append(f"   - Error: {step.error}")

    return "\n".join(lines)


def run_async(coro):
    """Run async code in sync context, handling nested event loops."""
    import concurrent.futures

    def run_in_new_loop():
        """Run coroutine in a fresh event loop."""
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
        # Event loop is running (e.g., inside Gradio), use thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_new_loop)
            return future.result(timeout=120)
    else:
        # No running loop, just run directly
        return asyncio.run(coro)


async def _process_message_async(message: str) -> str:
    """Process a user message and return the response."""
    t = get_team()
    message = message.strip()

    if not message:
        return "Please enter a message."

    try:
        # Check for commands
        if message.lower().startswith("/react "):
            task = message[7:].strip()
            trace = await t.react(task, max_steps=10, verbose=False)
            return format_react_trace(trace)

        elif message.lower().startswith("/reason "):
            problem = message[8:].strip()
            chain = await t.reason(problem, method="zero_shot")
            return format_reasoning_chain(chain)

        elif message.lower().startswith("/plan "):
            goal = message[6:].strip()
            plan = await t.plan_and_execute(goal)
            return format_plan(plan)

        elif message.lower() == "/help":
            return """**AI Team Commands:**

- `/react <task>` - ReAct agent (reasoning + tool use)
- `/reason <problem>` - Chain-of-thought reasoning
- `/plan <goal>` - Multi-step task planning
- `/agents` - List available agents
- `/help` - Show this help

**Git Automation:**

- `/git status` - Show repository status
- `/git log` - Show recent commits
- `/commit` - Smart commit (AI-generated message)

**Code Execution:**

- `/run python <code>` - Run Python code
- `/run js <code>` - Run JavaScript code

**Project Generator:**

- `/templates` - List available templates
- `/new <template> <name>` - Create from template

**Screenshot Analysis:**

- `/analyze <path>` - Analyze image with AI
- `/analyze <path> code` - Convert UI to code

**File System (writes real files!):**

- `/build <file> <description>` - Generate code and save to file
- `/write <file> <content>` - Write content to file
- `/read <file>` - Read a file

**Voice Commands:**

- `/voice file <path>` - Transcribe audio file

**Web Search:**

- `/search <query>` - Search the web and get AI-synthesized answer

**Or just type naturally** and the AI Team will collaborate!

**Examples:**
- `/new fastapi my-api`
- `/run python print('Hello!')`
- `/search latest Python 3.13 features`
- `/analyze ~/screenshot.png code`
"""

        elif message.lower() == "/agents":
            agents = list(t.agents.keys())
            local = [a for a in agents if "local" in a.lower()]
            cloud = [a for a in agents if "local" not in a.lower()]

            response = f"**Available Agents ({len(agents)} total):**\n\n"
            if cloud:
                response += f"Cloud: {', '.join(cloud)}\n"
            if local:
                response += f"Local: {', '.join(local)}\n"
            return response

        elif message.lower().startswith("/git"):
            return await _handle_git_command(message)

        elif message.lower().startswith("/commit"):
            msg = message[7:].strip() if len(message) > 7 else ""
            return await _handle_smart_commit(msg)

        elif message.lower().startswith("/run"):
            return await _handle_code_execution(message[4:].strip())

        elif message.lower().startswith("/new") or message.lower().startswith("/create"):
            cmd_len = 4 if message.lower().startswith("/new") else 7
            return await _handle_project_creation(message[cmd_len:].strip())

        elif message.lower() == "/templates":
            return await _handle_list_templates()

        elif message.lower().startswith("/analyze") or message.lower().startswith("/screenshot"):
            cmd_len = 8 if message.lower().startswith("/analyze") else 11
            return await _handle_screenshot_analysis(message[cmd_len:].strip())

        elif message.lower().startswith("/voice"):
            return await _handle_voice_command(message[6:].strip())

        elif message.lower().startswith("/search "):
            return await _handle_web_search(message[8:].strip())

        elif message.lower().startswith("/write "):
            return await _handle_write_file(message[7:].strip())

        elif message.lower().startswith("/read "):
            return await _handle_read_file(message[6:].strip())

        elif message.lower().startswith("/build "):
            return await _handle_build_code(message[7:].strip())

        else:
            # Regular collaboration
            result = await t.collaborate(prompt=message, mode="parallel")

            agents_used = ', '.join(result.participating_agents) if result.participating_agents else "AI Team"

            response = f"**{agents_used}** | {result.total_time:.2f}s | Confidence: {result.confidence_score:.0%}\n\n"
            response += result.final_answer
            return response

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"


async def _handle_git_command(message: str) -> str:
    """Handle git commands using subprocess directly."""
    import os
    import subprocess

    args = message[4:].strip()  # Remove "/git"

    if not args:
        return """**Git Commands:**

- `/git status` - Show repository status
- `/git log` - Show recent commits
- `/git diff` - Show unstaged changes
- `/git branch` - List branches
- `/commit` - Smart commit with AI message
"""

    parts = args.split(maxsplit=1)
    subcmd = parts[0].lower()
    subargs = parts[1] if len(parts) > 1 else ""

    try:
        # Build git command
        if subcmd == "status":
            cmd = ["git", "status", "--short", "--branch"]
        elif subcmd == "log":
            count = int(subargs) if subargs.isdigit() else 10
            cmd = ["git", "log", f"-{count}", "--oneline"]
        elif subcmd == "diff":
            cmd = ["git", "diff", "--staged"] if "--staged" in subargs else ["git", "diff"]
        elif subcmd == "branch":
            cmd = ["git", "branch", "-a"] if "-a" in subargs else ["git", "branch"]
        else:
            return f"Unknown git command: {subcmd}"

        # Run command
        result = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout.strip() or result.stderr.strip() or "(no output)"

        if result.returncode == 0:
            return f"**Git {subcmd}:**\n```\n{output}\n```"
        else:
            return f"**Git {subcmd} error:**\n```\n{output}\n```"

    except subprocess.TimeoutExpired:
        return "Git command timed out"
    except Exception as e:
        return f"Git error: {str(e)}"


async def _handle_smart_commit(message: str) -> str:
    """Handle smart commit command using subprocess."""
    import os
    import subprocess

    try:
        cwd = os.getcwd()

        # Check status first
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, timeout=30
        )

        if not status.stdout.strip():
            return "No changes to commit"

        # Count changes
        lines = status.stdout.strip().split('\n')
        added = sum(1 for ln in lines if ln.startswith('A') or ln.startswith('?'))
        modified = sum(1 for ln in lines if ln.startswith('M'))
        deleted = sum(1 for ln in lines if ln.startswith('D'))

        # Stage changes selectively (exclude secrets)
        SECRET_PATTERNS = [".env", ".env.*", "*.pem", "*.key", "*.p12",
                           "credentials.*", "*secret*", "*.pfx", "*.crt",
                           "firebase-admin*.json", "service-account*.json"]
        # Add all, then unstage anything matching secret patterns
        subprocess.run(["git", "add", "-A"], cwd=cwd, timeout=30)
        for pattern in SECRET_PATTERNS:
            subprocess.run(
                ["git", "reset", "HEAD", "--", pattern],
                cwd=cwd, capture_output=True, timeout=10
            )

        # Generate commit message if not provided
        if not message:
            if added > modified:
                message = f"feat: Add {added} new file(s)"
            elif deleted > 0:
                message = f"chore: Remove {deleted} file(s)"
            else:
                message = f"fix: Update {modified} file(s)"

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=cwd, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            return f"""**Commit Successful!**

- Added: {added}
- Modified: {modified}
- Deleted: {deleted}

```
{result.stdout.strip()}
```
"""
        else:
            return f"Commit failed:\n```\n{result.stderr.strip()}\n```"

    except subprocess.TimeoutExpired:
        return "Commit timed out"
    except Exception as e:
        return f"Commit error: {str(e)}"


def _validate_write_path(filepath: str) -> str | None:
    """Validate a file path for safety. Returns error message or None if safe."""
    import os

    abs_path = os.path.abspath(filepath)

    # Block path traversal
    if ".." in filepath:
        return "Path traversal (`..`) is not allowed."

    # Block dotfiles/directories (e.g. .env, .ssh, .git)
    parts = abs_path.split(os.sep)
    sensitive_dotfiles = {".env", ".ssh", ".aws", ".git", ".gnupg", ".config"}
    for part in parts:
        if part in sensitive_dotfiles:
            return f"Writing to `{part}` is not allowed for security reasons."

    # Block system directories
    blocked_prefixes = ["/etc", "/usr", "/bin", "/sbin", "/var", "/tmp", "/dev", "/proc", "/sys"]
    for prefix in blocked_prefixes:
        if abs_path.startswith(prefix):
            return f"Writing to `{prefix}` is not allowed."

    # Block sensitive file extensions
    _, ext = os.path.splitext(abs_path)
    if ext.lower() in {".pem", ".key", ".crt", ".p12", ".pfx"}:
        return f"Writing `{ext}` files is not allowed for security reasons."

    return None


async def _handle_web_search(query: str) -> str:
    """Search the web and synthesize results with AI."""
    if not query:
        return """**Web Search:**

Usage: `/search <query>`

Examples:
- `/search latest Python 3.13 features`
- `/search FastAPI best practices 2026`
- `/search how to optimize SQLite queries`
"""

    try:
        # Perform web search
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            results = []
            for r in DDGS().text(query, max_results=5):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        except ImportError:
            return "**Error:** `ddgs` not installed. Run: `pip install ddgs`"

        if not results:
            return f"No results found for: {query}"

        # Format results as context for the AI
        context_parts = [f"Web search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            context_parts.append(f"{i}. **{r['title']}**")
            context_parts.append(f"   {r['url']}")
            context_parts.append(f"   {r['snippet']}\n")

        search_context = "\n".join(context_parts)

        # Feed to AI for synthesis
        t = get_team()
        prompt = (
            f"Based on these web search results, provide a concise, helpful answer "
            f"to the query: \"{query}\"\n\n"
            f"Include citations [1], [2], etc. referencing the source URLs.\n\n"
            f"{search_context}"
        )

        result = await t.ask(prompt=prompt)

        # Build response with sources
        response = f"**Web Search:** {query}\n\n"
        response += result.content if result.success else "Could not synthesize results."
        response += "\n\n---\n**Sources:**\n"
        for i, r in enumerate(results, 1):
            response += f"[{i}] [{r['title']}]({r['url']})\n"

        return response

    except Exception as e:
        return f"Search error: {str(e)}"


async def _handle_write_file(args: str) -> str:
    """Write content to a file with path validation."""
    import os

    if not args:
        return """**Write File:**

Usage: `/write <filepath> <content>`

Examples:
- `/write hello.py print("Hello World")`
- `/write src/utils.py def add(a, b): return a + b`
"""

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return "Please provide both filepath and content.\n\nExample: `/write hello.py print('Hello')`"

    filepath = os.path.expanduser(parts[0])
    content = parts[1]

    # Validate path before writing
    path_error = _validate_write_path(filepath)
    if path_error:
        return f"**Write Blocked:** {path_error}"

    try:
        # Create directory if needed
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Write file
        with open(filepath, 'w') as f:
            f.write(content)

        abs_path = os.path.abspath(filepath)
        return f"""**File Written Successfully!**

- **Path:** `{abs_path}`
- **Size:** {len(content)} bytes

```
{content[:500]}{'...' if len(content) > 500 else ''}
```
"""
    except Exception as e:
        return f"Error writing file: {str(e)}"


async def _handle_read_file(args: str) -> str:
    """Read a file and display contents."""
    import os

    if not args:
        return "Usage: `/read <filepath>`"

    filepath = os.path.expanduser(args.strip())

    if not os.path.exists(filepath):
        return f"File not found: {filepath}"

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Detect language for syntax highlighting
        ext = os.path.splitext(filepath)[1]
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'jsx', '.tsx': 'tsx', '.json': 'json',
            '.html': 'html', '.css': 'css', '.md': 'markdown',
            '.yaml': 'yaml', '.yml': 'yaml', '.sh': 'bash',
        }
        lang = lang_map.get(ext, '')

        return f"""**{filepath}**

```{lang}
{content[:3000]}{'...' if len(content) > 3000 else ''}
```
"""
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def _handle_build_code(args: str) -> str:
    """Generate code with AI and save to file."""
    import os

    if not args:
        return """**Build Code:**

Generate code with AI and save directly to a file.

Usage: `/build <filepath> <description>`

Examples:
- `/build utils/email.py A function to validate email addresses`
- `/build api/routes.py FastAPI routes for user CRUD operations`
- `/build tests/test_calc.py Unit tests for a calculator class`
"""

    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return "Please provide filepath and description.\n\nExample: `/build utils.py A function to validate emails`"

    filepath = os.path.expanduser(parts[0])
    description = parts[1]

    # Detect language from extension
    ext = os.path.splitext(filepath)[1]
    lang_map = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
        '.jsx': 'React JSX', '.tsx': 'React TSX',
        '.html': 'HTML', '.css': 'CSS', '.sh': 'Bash',
    }
    language = lang_map.get(ext, 'code')

    # Generate code using AI Team
    t = get_team()

    prompt = f"""Generate {language} code for: {description}

Requirements:
1. Write clean, production-ready code
2. Include necessary imports
3. Add brief comments for complex logic
4. Follow best practices for {language}

Return ONLY the code, no explanations or markdown."""

    try:
        result = await t.collaborate(prompt=prompt, mode="parallel")
        code = result.final_answer

        # Clean up code (remove markdown if present)
        if "```" in code:
            import re
            matches = re.findall(r'```(?:\w+)?\n(.*?)```', code, re.DOTALL)
            if matches:
                code = matches[0]

        # Create directory if needed
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # Write file
        with open(filepath, 'w') as f:
            f.write(code.strip())

        abs_path = os.path.abspath(filepath)

        return f"""**Code Built Successfully!**

- **File:** `{abs_path}`
- **Language:** {language}
- **Description:** {description}

```{ext[1:] if ext else ''}
{code.strip()[:1500]}{'...' if len(code) > 1500 else ''}
```

The file has been created on your file system. Open it in VS Code:
```
code {filepath}
```
"""
    except Exception as e:
        return f"Error building code: {str(e)}"


async def _handle_voice_command(args: str) -> str:
    """Handle voice commands."""
    if args.startswith("file "):
        # Transcribe audio file
        import os
        file_path = os.path.expanduser(args[5:].strip())

        if not os.path.exists(file_path):
            return f"File not found: {file_path}"

        try:
            from elgringo.advanced.voice import VoiceToCodePipeline

            pipeline = VoiceToCodePipeline()
            result = await pipeline.transcribe(file_path)

            return f"""**Transcription:**

{result.text}

*Confidence: {result.confidence:.0%} | Duration: {result.duration:.2f}s*
"""
        except Exception as e:
            return f"Transcription error: {str(e)}"

    elif args == "code":
        return """**Voice-to-Code Mode:**

To use voice-to-code, run from the CLI:
```
ai-team
/voice code
```

The CLI supports real-time microphone input.
Speak what you want to create, and the AI will generate code.

**Requirements:**
- `pip install SpeechRecognition pyaudio`
- OPENAI_API_KEY for Whisper (best quality)
"""

    else:
        return """**Voice Commands:**

- `/voice file <path>` - Transcribe an audio file
- `/voice code` - Generate code from speech (CLI only)

**For real-time voice input, use the CLI:**
```
ai-team
/voice
```

The CLI supports microphone input for hands-free operation.

**Requirements:**
- `pip install SpeechRecognition pyaudio`
- OPENAI_API_KEY for Whisper (best quality)
"""


async def _handle_screenshot_analysis(args: str) -> str:
    """Handle screenshot analysis command."""
    if not args:
        return """**Screenshot Analysis:**

- `/analyze <path>` - Analyze an image
- `/analyze <path> code` - Convert UI to code
- `/analyze <path> error` - Analyze error screenshot
- `/analyze <path> arch` - Analyze architecture diagram

**Examples:**
- `/analyze ~/Desktop/mockup.png`
- `/analyze ./screenshot.png Convert to React`
- `/analyze error.png error`
"""

    import os
    parts = args.split(maxsplit=1)
    image_path = os.path.expanduser(parts[0])
    prompt_or_mode = parts[1] if len(parts) > 1 else ""

    if not os.path.exists(image_path):
        return f"Image not found: {image_path}"

    try:
        from elgringo.advanced.vision import VisionEngine

        engine = VisionEngine()
        mode = prompt_or_mode.lower().strip()

        if mode == "code" or mode.startswith("convert"):
            framework = "react"
            if "vue" in mode:
                framework = "vue"
            elif "svelte" in mode:
                framework = "svelte"
            result = await engine.screenshot_to_code(image_path, framework=framework)

        elif mode == "error":
            result = await engine.analyze_error_screenshot(image_path)

        elif mode == "arch" or mode == "architecture":
            result = await engine.analyze_architecture_diagram(image_path)

        else:
            prompt = prompt_or_mode if prompt_or_mode else """Analyze this image and provide:
1. Description of what you see
2. UI/UX feedback if applicable
3. Suggestions for improvement"""
            result = await engine.analyze_image(image_path, prompt)

        # Format result
        output = f"""**Image Analysis**
*Model: {result.model_used} | Time: {result.processing_time:.2f}s*

{result.description}
"""

        if result.code:
            output += f"\n**Generated Code:**\n```\n{result.code}\n```"

        return output

    except Exception as e:
        return f"Analysis error: {str(e)}"


async def _handle_list_templates() -> str:
    """List available project templates."""
    from elgringo.workflows.app_generator import APP_TEMPLATES

    lines = ["**Available Project Templates:**\n"]

    for key, template in APP_TEMPLATES.items():
        stack = ", ".join(template.get("stack", []))
        lines.append(f"- **{key}** - {template['name']}")
        lines.append(f"  Stack: {stack}")

    lines.append("\n**Usage:**")
    lines.append("- `/new <template> <name>` - Create from template")
    lines.append("- `/new <description>` - AI generates project")
    lines.append("\n**Examples:**")
    lines.append("- `/new fastapi my-api`")
    lines.append("- `/new react my-dashboard`")

    return "\n".join(lines)


async def _handle_project_creation(args: str) -> str:
    """Handle project creation command."""
    if not args:
        return await _handle_list_templates()

    import os
    from elgringo.workflows.app_generator import APP_TEMPLATES, AppGenerator

    parts = args.split(maxsplit=1)
    first_arg = parts[0].lower()

    try:
        # Check if first arg is a template name
        if first_arg in APP_TEMPLATES:
            template = first_arg
            name = parts[1] if len(parts) > 1 else None

            if not name:
                return f"Please provide a project name.\n\nExample: `/new {template} my-project`"

            generator = AppGenerator(output_dir=os.getcwd())
            result = await generator.create_app(
                description=f"Create a {APP_TEMPLATES[template]['name']} project",
                name=name,
                template=template
            )

            if result.get("success"):
                next_steps = result.get("next_steps", [])[:3]
                steps_text = "\n".join(f"- {s}" for s in next_steps) if next_steps else ""

                return f"""**Project Created Successfully!**

- **Name:** {result['project_name']}
- **Location:** {result['project_path']}
- **Template:** {result['template']}
- **Files:** {len(result.get('files_created', []))}

**Next Steps:**
{steps_text}
"""
            else:
                return "Project creation failed"
        else:
            # Natural language description
            generator = AppGenerator(output_dir=os.getcwd())
            result = await generator.create_app(description=args)

            if result.get("success"):
                next_steps = result.get("next_steps", [])[:3]
                steps_text = "\n".join(f"- {s}" for s in next_steps) if next_steps else ""

                return f"""**Project Created Successfully!**

- **Name:** {result['project_name']}
- **Location:** {result['project_path']}
- **Template:** {result['template']}
- **Files:** {len(result.get('files_created', []))}

**Next Steps:**
{steps_text}
"""
            else:
                return "Project creation failed"

    except Exception as e:
        return f"Error creating project: {str(e)}"


async def _handle_code_execution(args: str) -> str:
    """Handle code execution command."""
    if not args:
        return """**Code Execution:**

- `/run python <code>` - Run Python code
- `/run js <code>` - Run JavaScript code

**Examples:**
- `/run python print('Hello!')`
- `/run js console.log(2 + 2)`
- `/run python [x**2 for x in range(10)]`
"""

    from elgringo.sandbox import get_code_executor

    try:
        executor = get_code_executor()

        # Parse language and code
        parts = args.split(maxsplit=1)
        lang = parts[0].lower()
        code = parts[1] if len(parts) > 1 else ""

        if lang in ('python', 'py'):
            language = 'python'
        elif lang in ('javascript', 'js', 'node'):
            language = 'javascript'
        else:
            # Assume python if no language specified
            language = 'python'
            code = args

        if not code:
            return "Please provide code to execute"

        # Validate and execute
        result = await executor.execute_with_validation(code, language)

        # Format result
        if result.success:
            output = result.stdout if result.stdout else "(no output)"
            return f"""**Execution Result ({language}):**

```
{output}
```

Exit code: {result.exit_code} | Time: {result.execution_time}s
"""
        else:
            error_msg = result.stderr or result.error or "Unknown error"
            timeout_msg = " (timed out)" if result.timed_out else ""
            return f"""**Execution Failed{timeout_msg}:**

```
{error_msg}
```

Exit code: {result.exit_code}
"""

    except Exception as e:
        return f"Execution error: {str(e)}"


def process_message_sync(message: str) -> str:
    """Synchronous wrapper for message processing."""
    return run_async(_process_message_async(message))


def _is_command(message: str) -> bool:
    """Check if message is a slash command (non-streaming)."""
    return message.strip().startswith("/")


def respond(message: str, history: list) -> str:
    """Chat response function for gr.ChatInterface."""
    if not message.strip():
        return "Please enter a message."
    return process_message_sync(message)


def respond_stream(message: str, history: list):
    """Streaming chat response generator for Gradio.

    Yields partial responses for natural language queries.
    Falls back to blocking for slash commands.
    """
    if not message.strip():
        yield "Please enter a message."
        return

    # Slash commands are non-streaming (they do subprocess/tool work)
    if _is_command(message):
        yield process_message_sync(message)
        return

    # Stream from the best agent for natural language input
    t = get_team()
    try:
        import threading
        import queue as queue_mod

        token_queue = queue_mod.Queue()

        async def _stream_worker():
            try:
                # Classify and pick the best agent
                classification = t._task_router.classify(message)
                agents_list = list(t.agents.values())
                if not agents_list:
                    token_queue.put(("ERROR", "No agents available."))
                    return

                best_agent = agents_list[0]
                # Try to find the router-recommended agent
                recommended = classification.recommended_agents
                for rec_name in recommended:
                    if rec_name in t.agents:
                        best_agent = t.agents[rec_name]
                        break

                header = f"**{best_agent.name}** | Streaming...\n\n"
                token_queue.put(("TOKEN", header))

                async for token in best_agent.generate_stream(message):
                    token_queue.put(("TOKEN", token))

                token_queue.put(("DONE", None))
            except Exception as e:
                token_queue.put(("ERROR", str(e)))

        def _run_stream():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_stream_worker())
            finally:
                loop.close()

        thread = threading.Thread(target=_run_stream, daemon=True)
        thread.start()

        accumulated = ""
        while True:
            try:
                msg_type, data = token_queue.get(timeout=120)
                if msg_type == "DONE":
                    break
                elif msg_type == "ERROR":
                    accumulated += f"\n\nError: {data}"
                    yield accumulated
                    break
                elif msg_type == "TOKEN":
                    accumulated += data
                    yield accumulated
            except queue_mod.Empty:
                accumulated += "\n\n(Timed out waiting for response)"
                yield accumulated
                break

        thread.join(timeout=5)

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"Error: {str(e)}"


def create_ui():
    """Create the Gradio UI with organized, clickable examples."""

    with gr.Blocks(title="AI Team Chat") as demo:
        gr.Markdown("""
# AI Team Chat

**7 AI agents ready to help:** ChatGPT, Gemini, Grok, Llama, Qwen, and more!

Click any example below or type your own request.
        """)

        chatbot = gr.Chatbot(label="Conversation", height=400)

        with gr.Row():
            msg = gr.Textbox(
                label="Message",
                placeholder="Type a message or click an example below...",
                scale=9,
                show_label=False,
            )
            submit = gr.Button("Send", variant="primary", scale=1)

        # Chat functions - using Gradio 6 message format with streaming
        def send_message(message, history):
            """Process a message with streaming for natural language."""
            if not message.strip():
                yield "", history
                return

            # Add user message immediately
            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": ""}
            ]

            # Stream the response
            for partial in respond_stream(message, history):
                history[-1]["content"] = partial
                yield "", history

            # Persist after streaming completes
            _save_chat_history(history)

        def set_and_send(cmd, history):
            """Set command and send it (non-streaming for commands)."""
            if not cmd.strip():
                return "", history
            response = process_message_sync(cmd)
            history = history + [
                {"role": "user", "content": cmd},
                {"role": "assistant", "content": response}
            ]
            _save_chat_history(history)
            return "", history

        # Quick action buttons
        gr.Markdown("### Quick Actions")

        with gr.Row():
            btn_help = gr.Button("/help", size="sm")
            btn_agents = gr.Button("/agents", size="sm")
            btn_templates = gr.Button("/templates", size="sm")
            btn_status = gr.Button("/git status", size="sm")
            btn_commit = gr.Button("/commit", size="sm")
            btn_search = gr.Button("/search", size="sm")

        with gr.Accordion("Code Execution", open=False):
            with gr.Row():
                btn_py1 = gr.Button("Hello World", size="sm")
                btn_py2 = gr.Button("List Squares", size="sm")
                btn_py3 = gr.Button("Sum Range", size="sm")
                btn_js1 = gr.Button("JS Math.PI", size="sm")

        with gr.Accordion("Git Automation", open=False):
            with gr.Row():
                btn_git1 = gr.Button("Status", size="sm")
                btn_git2 = gr.Button("Log", size="sm")
                btn_git3 = gr.Button("Diff", size="sm")
                btn_git4 = gr.Button("Analyze", size="sm")

        with gr.Accordion("Project Generator", open=False):
            with gr.Row():
                btn_new1 = gr.Button("FastAPI", size="sm")
                btn_new2 = gr.Button("React", size="sm")
                btn_new3 = gr.Button("Flask", size="sm")
                btn_new4 = gr.Button("Next.js", size="sm")

        with gr.Accordion("AI Agents", open=False):
            with gr.Row():
                btn_react = gr.Button("ReAct: Find TODOs", size="sm")
                btn_reason = gr.Button("Reason: Pros/Cons", size="sm")
                btn_plan = gr.Button("Plan: New Project", size="sm")

        with gr.Accordion("Build & Write Files", open=False):
            with gr.Row():
                btn_build1 = gr.Button("Build: Email Validator", size="sm")
                btn_build2 = gr.Button("Build: REST API", size="sm")
                btn_build3 = gr.Button("Build: Unit Tests", size="sm")
                btn_build4 = gr.Button("Build: Dockerfile", size="sm")

        with gr.Accordion("Common Tasks", open=False):
            with gr.Row():
                btn_task1 = gr.Button("Validate Email", size="sm")
                btn_task2 = gr.Button("REST API", size="sm")
                btn_task3 = gr.Button("Unit Tests", size="sm")
                btn_task4 = gr.Button("Dockerfile", size="sm")

        with gr.Row():
            clear = gr.Button("Clear Chat")

        # Wire up all buttons
        btn_help.click(fn=lambda h: set_and_send("/help", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_agents.click(fn=lambda h: set_and_send("/agents", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_templates.click(fn=lambda h: set_and_send("/templates", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_status.click(fn=lambda h: set_and_send("/git status", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_commit.click(fn=lambda h: set_and_send("/commit", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_search.click(fn=lambda h: set_and_send("/search latest Python AI frameworks", h), inputs=[chatbot], outputs=[msg, chatbot])

        # Code execution
        btn_py1.click(fn=lambda h: set_and_send("/run python print('Hello, World!')", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_py2.click(fn=lambda h: set_and_send("/run python [x**2 for x in range(10)]", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_py3.click(fn=lambda h: set_and_send("/run python sum(range(100))", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_js1.click(fn=lambda h: set_and_send("/run js console.log(Math.PI * 2)", h), inputs=[chatbot], outputs=[msg, chatbot])

        # Git
        btn_git1.click(fn=lambda h: set_and_send("/git status", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_git2.click(fn=lambda h: set_and_send("/git log", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_git3.click(fn=lambda h: set_and_send("/git diff", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_git4.click(fn=lambda h: set_and_send("/git analyze", h), inputs=[chatbot], outputs=[msg, chatbot])

        # Project generator
        btn_new1.click(fn=lambda h: set_and_send("/new fastapi my-api", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_new2.click(fn=lambda h: set_and_send("/new react my-app", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_new3.click(fn=lambda h: set_and_send("/new flask my-webapp", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_new4.click(fn=lambda h: set_and_send("/new next my-site", h), inputs=[chatbot], outputs=[msg, chatbot])

        # AI agents
        btn_react.click(fn=lambda h: set_and_send("/react Find all Python files with TODO comments", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_reason.click(fn=lambda h: set_and_send("/reason What are the pros and cons of microservices?", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_plan.click(fn=lambda h: set_and_send("/plan Set up a new Flask project with tests", h), inputs=[chatbot], outputs=[msg, chatbot])

        # Build commands (writes to file system)
        btn_build1.click(fn=lambda h: set_and_send("/build utils/email_validator.py A function to validate email addresses with regex", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_build2.click(fn=lambda h: set_and_send("/build api/routes.py FastAPI routes for user CRUD operations", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_build3.click(fn=lambda h: set_and_send("/build tests/test_calculator.py Unit tests for a Calculator class with add, subtract, multiply, divide", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_build4.click(fn=lambda h: set_and_send("/build Dockerfile Dockerfile for a Python Flask app with gunicorn", h), inputs=[chatbot], outputs=[msg, chatbot])

        # Common tasks (display only)
        btn_task1.click(fn=lambda h: set_and_send("Write a Python function to validate email addresses", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_task2.click(fn=lambda h: set_and_send("Create a REST API endpoint for user authentication", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_task3.click(fn=lambda h: set_and_send("Generate unit tests for a calculator class", h), inputs=[chatbot], outputs=[msg, chatbot])
        btn_task4.click(fn=lambda h: set_and_send("Create a Dockerfile for a Python Flask app", h), inputs=[chatbot], outputs=[msg, chatbot])

        # Main input handlers
        msg.submit(send_message, [msg, chatbot], [msg, chatbot])
        submit.click(send_message, [msg, chatbot], [msg, chatbot])
        clear.click(fn=lambda: [], outputs=[chatbot])

        # Feedback thumbs up/down via Gradio's built-in like button
        def handle_like(evt: gr.LikeData):
            """Handle thumbs up/down feedback from chat messages."""
            try:
                from elgringo.feedback.feedback_collector import FeedbackCollector
                collector = FeedbackCollector()
                task_id = f"chat-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                model_name = "ai-team"  # Generic since we may not know which agent
                if evt.liked:
                    collector.submit_thumbs_up(task_id, model_name)
                else:
                    collector.submit_thumbs_down(task_id, model_name)
                logger.info(f"Feedback recorded: {'positive' if evt.liked else 'negative'}")
            except Exception as e:
                logger.warning(f"Could not record feedback: {e}")

        chatbot.like(handle_like, None, None)

        # Load persisted history on page open
        demo.load(fn=_load_chat_history, outputs=[chatbot])

        gr.Markdown("""
---
*Powered by Fred's AI Team Platform - Claude, ChatGPT, Gemini, Grok, and Local Models*
        """)

    return demo


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("AI Team Chat UI")
    print("="*60)

    # Pre-initialize team
    print("\nInitializing AI Team...")
    t = get_team()
    print(f"Done - {len(t.agents)} agents ready")

    agents = list(t.agents.keys())
    local = [a for a in agents if "local" in a.lower()]
    cloud = [a for a in agents if "local" not in a.lower()]

    if cloud:
        print(f"  Cloud: {', '.join(cloud)}")
    if local:
        print(f"  Local: {', '.join(local)}")

    print("\n" + "="*60)
    print("Starting web interface...")
    print("Open: http://localhost:7860")
    print("="*60 + "\n")

    # Create and launch UI
    ui = create_ui()
    # Gradio auth — set GRADIO_USERNAME and GRADIO_PASSWORD env vars to enable
    auth_user = os.environ.get("GRADIO_USERNAME")
    auth_pass = os.environ.get("GRADIO_PASSWORD")
    auth_config = [(auth_user, auth_pass)] if auth_user and auth_pass else None

    ui.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False,
        show_error=True,
        auth=auth_config,
        root_path=os.environ.get("GRADIO_ROOT_PATH", ""),
    )


if __name__ == "__main__":
    main()
