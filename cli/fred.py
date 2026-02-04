#!/usr/bin/env python3
"""
FRED - The Ultimate AI Development Platform
=============================================

Fred is your AI development team running locally on your Mac.
All AI models (Claude, ChatGPT, Gemini, Grok, Ollama) work together
to build, test, and deploy enterprise applications from natural language.

Usage:
    fred                          # Interactive mode
    fred "Build a todo app"       # Create app from description
    fred review [path]            # Code review
    fred security [path]          # Security audit
    fred fix [path]               # Fix issues
    fred create <description>     # Create new project
    fred status                   # Check team status

    fred start                    # Start API server (background)
    fred stop                     # Stop API server
    fred server                   # Server status

Agent Tasks:
    fred commit                   # Generate commit message from staged changes
    fred explain <file>           # Explain code in a file
    fred test <file>              # Generate tests for a file
    fred todo [path]              # Find TODOs/FIXMEs in project
    fred scan [path]              # Full project health scan

Examples:
    fred "Create a task management app with Firebase auth"
    fred review ~/Projects/MyApp
    fred commit  # Generate commit message for staged changes
    fred explain src/main.py  # Get AI explanation of code
    fred start  # Then other apps can call http://localhost:8080
"""

import argparse
import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv
load_dotenv()


# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


# Server management paths
PLATFORM_DIR = SCRIPT_DIR.parent
PID_FILE = PLATFORM_DIR / ".fred-server.pid"
LOG_FILE = PLATFORM_DIR / "logs" / "server.log"
SERVER_PORT = 8080


def get_server_pid() -> Optional[int]:
    """Get the running server PID if it exists."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process is actually running
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            # Process not running, clean up stale PID file
            PID_FILE.unlink(missing_ok=True)
    return None


def is_server_running() -> bool:
    """Check if the API server is running."""
    return get_server_pid() is not None


def start_server():
    """Start the API server in the background."""
    if is_server_running():
        pid = get_server_pid()
        print(f"{Colors.YELLOW}Server already running (PID: {pid}){Colors.END}")
        print(f"  URL: http://localhost:{SERVER_PORT}")
        return

    # Ensure logs directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Start the server
    server_script = PLATFORM_DIR / "servers" / "main.py"
    if not server_script.exists():
        print(f"{Colors.RED}Server script not found: {server_script}{Colors.END}")
        return

    print(f"{Colors.CYAN}Starting API server...{Colors.END}")

    with open(LOG_FILE, 'w') as log:
        process = subprocess.Popen(
            [sys.executable, str(server_script)],
            cwd=str(PLATFORM_DIR),
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    # Save PID
    PID_FILE.write_text(str(process.pid))

    # Wait a moment and check if it started
    import time
    time.sleep(2)

    if is_server_running():
        print(f"{Colors.GREEN}✓ Server started (PID: {process.pid}){Colors.END}")
        print(f"  URL: http://localhost:{SERVER_PORT}")
        print(f"  Logs: {LOG_FILE}")
        print(f"\n  Stop with: {Colors.CYAN}fred stop{Colors.END}")
    else:
        print(f"{Colors.RED}✗ Server failed to start. Check logs: {LOG_FILE}{Colors.END}")


def stop_server():
    """Stop the API server."""
    pid = get_server_pid()
    if not pid:
        print(f"{Colors.YELLOW}Server is not running{Colors.END}")
        return

    print(f"{Colors.CYAN}Stopping server (PID: {pid})...{Colors.END}")

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for graceful shutdown
        import time
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # Force kill if still running
            os.kill(pid, signal.SIGKILL)

        PID_FILE.unlink(missing_ok=True)
        print(f"{Colors.GREEN}✓ Server stopped{Colors.END}")
    except OSError as e:
        print(f"{Colors.RED}Error stopping server: {e}{Colors.END}")
        PID_FILE.unlink(missing_ok=True)


def server_status():
    """Show server status."""
    pid = get_server_pid()
    if pid:
        print(f"{Colors.GREEN}● Server running{Colors.END}")
        print(f"  PID: {pid}")
        print(f"  URL: http://localhost:{SERVER_PORT}")
        print(f"  Logs: {LOG_FILE}")

        # Try to get health status
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://localhost:{SERVER_PORT}/health", timeout=2) as r:
                print(f"  Health: {Colors.GREEN}OK{Colors.END}")
        except Exception:
            print(f"  Health: {Colors.YELLOW}checking...{Colors.END}")
    else:
        print(f"{Colors.RED}● Server not running{Colors.END}")
        print(f"\n  Start with: {Colors.CYAN}fred start{Colors.END}")


BANNER = f"""
{Colors.CYAN}{Colors.BOLD}
   ███████╗██████╗ ███████╗██████╗
   ██╔════╝██╔══██╗██╔════╝██╔══██╗
   █████╗  ██████╔╝█████╗  ██║  ██║
   ██╔══╝  ██╔══██╗██╔══╝  ██║  ██║
   ██║     ██║  ██║███████╗██████╔╝
   ╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝
{Colors.END}
{Colors.YELLOW}   The Ultimate AI Development Platform{Colors.END}
{Colors.GREEN}   Claude + ChatGPT + Gemini + Grok + Ollama{Colors.END}
"""


def check_api_keys() -> dict:
    """Check which API keys are configured and return status."""
    keys = {
        "Claude (Architect)": "ANTHROPIC_API_KEY",
        "ChatGPT (Developer)": "OPENAI_API_KEY",
        "Gemini (Creative)": "GEMINI_API_KEY",
        "Grok (Analyst)": "XAI_API_KEY",
    }

    status = {}
    for name, env_key in keys.items():
        status[name] = "available" if os.getenv(env_key) else "no API key"

    return status


async def get_team_status() -> dict:
    """Get comprehensive status of all AI team members."""
    from ai_dev_team.agents.ollama import get_available_local_models

    agents = check_api_keys()

    # Check Ollama
    try:
        ollama_models = await get_available_local_models()
        agents["Ollama (Local)"] = "available" if ollama_models else "not running"
    except Exception:
        ollama_models = []
        agents["Ollama (Local)"] = "not running"

    tools = ["filesystem", "shell", "browser", "git", "docker", "database", "package", "deploy"]

    return {
        "agents": agents,
        "tools": tools,
        "ollama_models": ollama_models
    }


def print_status(team_status: dict):
    """Print AI team status."""
    print(f"\n{Colors.BOLD}AI Team Status:{Colors.END}")
    print("-" * 50)

    for name, status in team_status["agents"].items():
        color = Colors.GREEN if status == "available" else Colors.RED
        print(f"  {color}●{Colors.END} {name}: {status}")

    print(f"\n{Colors.BOLD}Available Tools:{Colors.END}")
    print(f"  {', '.join(team_status['tools'])}")

    ollama = team_status.get("ollama_models", [])
    if ollama:
        print(f"\n{Colors.BOLD}Local Models (Ollama):{Colors.END}")
        for model in ollama:
            print(f"  • {model}")


def print_help():
    """Print help message."""
    print(f"""
{Colors.BOLD}Fred Commands:{Colors.END}

  {Colors.CYAN}Natural Language:{Colors.END}
    Just type what you want to build or do.
    Example: "Build a REST API with user authentication"

  {Colors.CYAN}create <description>{Colors.END}
    Create a new application from description.
    Example: create a todo app with React and Firebase

  {Colors.CYAN}review [path]{Colors.END}
    Code review of current directory or specified path.

  {Colors.CYAN}security [path]{Colors.END}
    Security audit of current directory or specified path.

  {Colors.CYAN}fix [path]{Colors.END}
    Analyze and fix issues in the code.

  {Colors.CYAN}deploy <target>{Colors.END}
    Deploy to: firebase, vercel, gcp, aws

  {Colors.BOLD}Agent Tasks:{Colors.END}

  {Colors.CYAN}commit{Colors.END}
    Generate a commit message from staged git changes.

  {Colors.CYAN}explain <file>{Colors.END}
    Get AI explanation of code in a file.

  {Colors.CYAN}test <file>{Colors.END}
    Generate tests for a file.

  {Colors.CYAN}todo [path]{Colors.END}
    Find all TODOs, FIXMEs, HACKs in the project.

  {Colors.CYAN}scan [path]{Colors.END}
    Full project health scan (review + security + todos).

  {Colors.BOLD}Other:{Colors.END}

  {Colors.CYAN}status{Colors.END}
    Show AI team status and available tools.

  {Colors.CYAN}cd <path>{Colors.END}
    Change working directory.

  {Colors.CYAN}help{Colors.END}
    Show this help message.

  {Colors.CYAN}quit / exit / q{Colors.END}
    Exit Fred.
""")


async def quick_review(project_path: str):
    """Quick code review of a project."""
    from ai_dev_team import AIDevTeam, ParallelCodingEngine

    print(f"\n{Colors.CYAN}🔍 Reviewing: {project_path}{Colors.END}")
    print("-" * 50)

    team = AIDevTeam(project_name="code-review")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Working...\n")

    result = await engine.review_project(project_path)

    print("=" * 50)
    print(f"{Colors.GREEN}✅ Review Complete ({result.total_time:.1f}s){Colors.END}")
    print(result.summary)

    # Show agent insights
    for agent_name, agent_results in result.agent_results.items():
        if isinstance(agent_results, list):
            for r in agent_results:
                if r.get('success') and r.get('content'):
                    print(f"\n{Colors.YELLOW}📝 {agent_name}:{Colors.END}")
                    content = r.get('content', '')
                    print(content[:500] + "..." if len(content) > 500 else content)


async def security_audit(project_path: str):
    """Security audit of a project."""
    from ai_dev_team import AIDevTeam, ParallelCodingEngine

    print(f"\n{Colors.CYAN}🔒 Security Audit: {project_path}{Colors.END}")
    print("-" * 50)

    team = AIDevTeam(project_name="security-audit")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Scanning...\n")

    result = await engine.security_audit(project_path)

    print("=" * 50)
    print(f"{Colors.GREEN}✅ Audit Complete{Colors.END}")
    print(result.summary)


async def quick_fix(project_path: str):
    """Quick fix issues in a project."""
    from ai_dev_team import AIDevTeam, ParallelCodingEngine

    print(f"\n{Colors.CYAN}🔧 Fix Mode: {project_path}{Colors.END}")
    print("-" * 50)

    team = AIDevTeam(project_name="quick-fix")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Analyzing and fixing...\n")

    # First do a quick review to identify issues
    review_result = await engine.review_project(project_path)

    # Extract issues
    issues = []
    for agent_name, agent_results in review_result.agent_results.items():
        if isinstance(agent_results, list):
            for r in agent_results:
                if r.get('success'):
                    issues.append({
                        "type": "review_finding",
                        "description": f"Issue found by {agent_name}",
                        "file_path": project_path,
                        "content": r.get('content', '')[:1000]
                    })

    if issues:
        fix_result = await engine.fix_issues(issues[:5], project_path)
        print("=" * 50)
        print(f"{Colors.GREEN}✅ Fix Session Complete ({fix_result.total_time:.1f}s){Colors.END}")
        print(f"Proposed fixes: {len(fix_result.proposed_fixes)}")
    else:
        print(f"{Colors.GREEN}No significant issues found to fix.{Colors.END}")


async def generate_commit_message():
    """Generate a commit message from staged changes."""
    from ai_dev_team import AIDevTeam

    # Get staged diff
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True, text=True
    )

    if not result.stdout.strip():
        print(f"{Colors.YELLOW}No staged changes found.{Colors.END}")
        print(f"Stage files first: git add <files>")
        return

    diff = result.stdout[:4000]  # Limit diff size

    print(f"{Colors.CYAN}📝 Generating commit message...{Colors.END}")

    team = AIDevTeam(project_name="commit-msg")
    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    prompt = f"""Analyze this git diff and generate a concise, conventional commit message.

Use format: type(scope): description

Types: feat, fix, docs, style, refactor, test, chore

DIFF:
```
{diff}
```

Return ONLY the commit message, nothing else."""

    response = await team.ask(prompt)

    print(f"\n{Colors.GREEN}Suggested commit message:{Colors.END}")
    print("-" * 50)
    print(response.content.strip())
    print("-" * 50)
    print(f"\n{Colors.CYAN}To use: git commit -m \"{response.content.strip().split(chr(10))[0]}\"{Colors.END}")


async def explain_code(file_path: str):
    """Explain code in a file."""
    from ai_dev_team import AIDevTeam

    path = Path(file_path)
    if not path.exists():
        print(f"{Colors.RED}File not found: {file_path}{Colors.END}")
        return

    content = path.read_text()[:8000]  # Limit size

    print(f"{Colors.CYAN}🔍 Explaining: {file_path}{Colors.END}")
    print("-" * 50)

    team = AIDevTeam(project_name="explain")
    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    prompt = f"""Explain this code clearly and concisely:

1. What does this code do? (1-2 sentences)
2. Key components/functions
3. How it works (brief)
4. Any notable patterns or issues

FILE: {path.name}
```
{content}
```"""

    response = await team.ask(prompt)
    print(response.content)


async def generate_tests(file_path: str):
    """Generate tests for a file."""
    from ai_dev_team import AIDevTeam

    path = Path(file_path)
    if not path.exists():
        print(f"{Colors.RED}File not found: {file_path}{Colors.END}")
        return

    content = path.read_text()[:6000]

    print(f"{Colors.CYAN}🧪 Generating tests for: {file_path}{Colors.END}")
    print("-" * 50)

    team = AIDevTeam(project_name="test-gen")
    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    # Detect language
    ext = path.suffix
    lang = {"py": "pytest", ".js": "jest", ".ts": "jest", ".go": "go test"}.get(ext, "appropriate framework")

    prompt = f"""Generate comprehensive tests for this code using {lang}.

Include:
- Unit tests for each function/method
- Edge cases
- Error handling tests

FILE: {path.name}
```
{content}
```

Return ONLY the test code, ready to save to a file."""

    response = await team.ask(prompt)

    print(f"\n{Colors.GREEN}Generated tests:{Colors.END}")
    print("=" * 50)
    print(response.content)

    # Suggest save location
    test_file = path.parent / f"test_{path.name}"
    print("=" * 50)
    print(f"\n{Colors.CYAN}Save to: {test_file}{Colors.END}")


async def find_todos(project_path: str):
    """Find all TODOs, FIXMEs, and HACKs in project."""
    print(f"{Colors.CYAN}📋 Finding TODOs in: {project_path}{Colors.END}")
    print("-" * 50)

    # Use grep to find TODOs
    patterns = ["TODO", "FIXME", "HACK", "XXX", "BUG"]

    todos = []
    for pattern in patterns:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.ts",
             "--include=*.go", "--include=*.java", "--include=*.swift", pattern, project_path],
            capture_output=True, text=True
        )
        if result.stdout:
            todos.extend(result.stdout.strip().split('\n'))

    if not todos:
        print(f"{Colors.GREEN}No TODOs found - nice clean code!{Colors.END}")
        return

    # Group by type
    print(f"\n{Colors.YELLOW}Found {len(todos)} items:{Colors.END}\n")

    for todo in todos[:30]:  # Limit output
        if "TODO" in todo:
            print(f"  {Colors.BLUE}TODO{Colors.END}: {todo.split('TODO')[1][:80] if 'TODO' in todo else todo[:80]}")
        elif "FIXME" in todo:
            print(f"  {Colors.RED}FIXME{Colors.END}: {todo.split('FIXME')[1][:80] if 'FIXME' in todo else todo[:80]}")
        elif "HACK" in todo:
            print(f"  {Colors.YELLOW}HACK{Colors.END}: {todo.split('HACK')[1][:80] if 'HACK' in todo else todo[:80]}")
        else:
            print(f"  {todo[:80]}")

    if len(todos) > 30:
        print(f"\n  ... and {len(todos) - 30} more")


async def full_scan(project_path: str):
    """Comprehensive project health scan."""
    from ai_dev_team import AIDevTeam, ParallelCodingEngine

    print(f"\n{Colors.CYAN}🔬 Full Project Scan: {project_path}{Colors.END}")
    print("=" * 50)

    team = AIDevTeam(project_name="full-scan")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")

    # 1. Code Review
    print(f"\n{Colors.BLUE}[1/3] Code Review...{Colors.END}")
    review_result = await engine.review_project(project_path)

    # 2. Security Audit
    print(f"{Colors.BLUE}[2/3] Security Audit...{Colors.END}")
    security_result = await engine.security_audit(project_path)

    # 3. TODOs
    print(f"{Colors.BLUE}[3/3] Finding TODOs...{Colors.END}")
    await find_todos(project_path)

    # Summary
    print("\n" + "=" * 50)
    print(f"{Colors.GREEN}✅ Scan Complete{Colors.END}")
    print("=" * 50)

    print(f"\n{Colors.BOLD}Code Review:{Colors.END}")
    print(review_result.summary[:500] if review_result.summary else "No issues found")

    print(f"\n{Colors.BOLD}Security:{Colors.END}")
    print(security_result.summary[:500] if security_result.summary else "No vulnerabilities found")


async def create_app(
    description: str,
    name: Optional[str] = None,
    template: Optional[str] = None,
    deploy_target: Optional[str] = None
):
    """Create an application from description."""
    from ai_dev_team.app_generator import AppGenerator

    print(f"\n{Colors.CYAN}Creating application...{Colors.END}")
    print(f"Description: {description}")
    if template:
        print(f"Template: {template}")
    if deploy_target:
        print(f"Deploy to: {deploy_target}")
    print()

    generator = AppGenerator()
    result = await generator.create_app(
        description=description,
        name=name,
        template=template,
        deploy_target=deploy_target
    )

    print(f"\n{Colors.GREEN}✓ Project created successfully!{Colors.END}")
    print(f"\n{Colors.BOLD}Project Details:{Colors.END}")
    print(f"  Name: {result['project_name']}")
    print(f"  Path: {result['project_path']}")
    print(f"  Template: {result['template']}")
    print(f"  Files: {len(result['files_created'])} created")

    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    for step in result["next_steps"]:
        print(f"  {step}")

    return result


async def deploy_project(target: str, path: Optional[str] = None):
    """Deploy project to target platform."""
    from ai_dev_team.tools.deploy import create_deploy_tools

    print(f"\n{Colors.CYAN}Deploying to {target}...{Colors.END}")

    deploy_path = path or os.getcwd()
    deploy_tools = create_deploy_tools(cwd=deploy_path)

    if target == "firebase":
        result = deploy_tools._firebase_deploy(cwd=deploy_path)
    elif target == "vercel":
        result = deploy_tools._vercel_deploy(prod=True, cwd=deploy_path)
    elif target in ["gcp", "cloudrun"]:
        project_name = Path(deploy_path).name
        result = deploy_tools._gcp_run_deploy(
            service=project_name,
            source=".",
            cwd=deploy_path
        )
    elif target == "aws":
        result = deploy_tools._aws_deploy(cwd=deploy_path)
    else:
        print(f"{Colors.RED}Unknown deployment target: {target}{Colors.END}")
        print("Available: firebase, vercel, gcp, cloudrun, aws")
        return

    if result.success:
        print(f"{Colors.GREEN}✓ Deployment successful!{Colors.END}")
        print(result.output)
    else:
        print(f"{Colors.RED}✗ Deployment failed: {result.error}{Colors.END}")


async def natural_language_task(task: str, project_path: str):
    """Handle natural language task description."""
    from ai_dev_team import AIDevTeam

    print(f"\n{Colors.CYAN}🚀 Task: {task}{Colors.END}")
    print(f"Project: {project_path}")
    print("-" * 50)

    team = AIDevTeam(project_name="task")

    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured.{Colors.END}")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Team is working...\n")

    full_prompt = f"""
PROJECT CONTEXT:
Working directory: {project_path}

TASK:
{task}

INSTRUCTIONS:
1. Analyze what needs to be done
2. Provide production-ready code or solutions
3. Include all necessary imports and error handling
4. Be specific and actionable
"""

    result = await team.collaborate(full_prompt, mode="parallel")

    print("=" * 50)
    print(f"{Colors.BOLD}TEAM OUTPUT{Colors.END}")
    print("=" * 50)
    print(result.final_answer)
    print()
    print(f"Agents: {', '.join(result.participating_agents)}")
    print(f"Time: {result.total_time:.2f}s")
    print(f"Confidence: {result.confidence_score:.0%}")


async def interactive_mode():
    """Interactive AI team session."""
    from ai_dev_team import AIDevTeam, ParallelCodingEngine
    from ai_dev_team.app_generator import AppGenerator

    print(BANNER)

    # Show status
    status = await get_team_status()
    available = [k for k, v in status["agents"].items() if v == "available"]
    missing = [k for k, v in status["agents"].items() if v != "available"]

    print(f"{Colors.GREEN}✅ Available: {', '.join(available) if available else 'None'}{Colors.END}")
    if missing:
        print(f"{Colors.YELLOW}⚠️  Unavailable: {', '.join(missing)}{Colors.END}")
    print()

    team = AIDevTeam(project_name="interactive")

    if not team.agents:
        print(f"{Colors.RED}❌ No API keys configured. Set at least one of:{Colors.END}")
        print("   ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY")
        return

    print(f"Active Agents: {', '.join(team.agents.keys())}")
    print(f"\nType {Colors.CYAN}'help'{Colors.END} for commands, {Colors.CYAN}'quit'{Colors.END} to exit.")
    print("-" * 50)

    cwd = os.getcwd()
    generator = AppGenerator()
    engine = ParallelCodingEngine(team)

    while True:
        try:
            user_input = input(f"\n{Colors.GREEN}[{Path(cwd).name}] fred>{Colors.END} ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print(f"{Colors.YELLOW}Goodbye! Happy coding!{Colors.END}")
                break

            if user_input.lower() == 'help':
                print_help()
                continue

            if user_input.lower() == 'status':
                status = await get_team_status()
                print_status(status)
                continue

            # Parse command
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else cwd

            if cmd == 'review':
                target = arg if arg != cwd or len(parts) > 1 else cwd
                await quick_review(target)
            elif cmd == 'security':
                target = arg if arg != cwd or len(parts) > 1 else cwd
                await security_audit(target)
            elif cmd == 'fix':
                target = arg if arg != cwd or len(parts) > 1 else cwd
                await quick_fix(target)
            elif cmd == 'commit':
                await generate_commit_message()
            elif cmd == 'explain':
                if len(parts) > 1:
                    await explain_code(parts[1])
                else:
                    print(f"{Colors.YELLOW}Usage: explain <file>{Colors.END}")
            elif cmd == 'test':
                if len(parts) > 1:
                    await generate_tests(parts[1])
                else:
                    print(f"{Colors.YELLOW}Usage: test <file>{Colors.END}")
            elif cmd == 'todo':
                target = arg if arg != cwd or len(parts) > 1 else cwd
                await find_todos(target)
            elif cmd == 'scan':
                target = arg if arg != cwd or len(parts) > 1 else cwd
                await full_scan(target)
            elif cmd == 'cd':
                if os.path.isdir(arg):
                    cwd = os.path.abspath(arg)
                    print(f"Changed to: {cwd}")
                else:
                    print(f"{Colors.RED}Not a directory: {arg}{Colors.END}")
            elif cmd == 'create':
                if len(parts) > 1:
                    result = await generator.create_app(parts[1])
                    print(f"\n{Colors.GREEN}✓ Project created: {result['project_path']}{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}Usage: create <description>{Colors.END}")
            elif cmd == 'deploy':
                if len(parts) > 1:
                    await deploy_project(parts[1], cwd)
                else:
                    print(f"{Colors.YELLOW}Usage: deploy <target> (firebase, vercel, gcp, aws){Colors.END}")
            else:
                # Treat as natural language task
                await natural_language_task(user_input, cwd)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted. Type 'quit' to exit.{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")


async def async_main():
    """Async main entry point."""
    parser = argparse.ArgumentParser(
        description="Fred - The Ultimate AI Development Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fred                                  # Interactive mode
  fred "Build a task management app"    # Natural language task
  fred review                           # Review current directory
  fred review ~/Projects/MyApp          # Review specific project
  fred security                         # Security audit
  fred fix                              # Fix issues
  fred --create my-app --template react # Create project
  fred --deploy --target firebase       # Deploy project

Agent Tasks:
  fred commit                           # Generate commit message
  fred explain <file>                   # Explain code
  fred test <file>                      # Generate tests
  fred todo                             # Find TODOs
  fred scan                             # Full project scan

Server Management:
  fred start                            # Start API server (background)
  fred stop                             # Stop API server
  fred server                           # Server status
        """
    )

    parser.add_argument('command', nargs='?', help='Command or natural language task')
    parser.add_argument('path', nargs='?', default=os.getcwd(), help='Project path')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--chat', '-c', action='store_true', help='Interactive chat mode (alias for -i)')
    parser.add_argument('--status', '-s', action='store_true', help='Show AI team status')
    parser.add_argument('--create', metavar='NAME', help='Create project with specific name')
    parser.add_argument('--template', '-t',
                        choices=['react', 'next', 'fastapi', 'flask', 'fullstack', 'mobile', 'cli', 'automation'],
                        help='Project template to use')
    parser.add_argument('--deploy', '-d', action='store_true', help='Deploy the project')
    parser.add_argument('--target', choices=['firebase', 'vercel', 'gcp', 'cloudrun', 'aws'],
                        help='Deployment target')
    parser.add_argument('--review', '-r', action='store_true', help='Review code')
    parser.add_argument('--security', action='store_true', help='Security audit')
    parser.add_argument('--fix', '-f', action='store_true', help='Fix issues')

    args = parser.parse_args()

    # Handle server commands first (no banner, no async needed)
    if args.command == 'start':
        start_server()
        return
    elif args.command == 'stop':
        stop_server()
        return
    elif args.command == 'server':
        server_status()
        return

    # Print banner for most operations
    if not args.status:
        print(BANNER)

    # Determine action
    if args.status:
        print(BANNER)
        status = await get_team_status()
        print_status(status)
    elif args.deploy:
        if not args.target:
            print(f"{Colors.RED}Error: --target required for deployment{Colors.END}")
            sys.exit(1)
        await deploy_project(args.target, args.path)
    elif args.review:
        await quick_review(args.path)
    elif args.security:
        await security_audit(args.path)
    elif args.fix:
        await quick_fix(args.path)
    elif args.create:
        description = args.command or f"Create a {args.template or 'web'} application"
        await create_app(description=description, name=args.create, template=args.template, deploy_target=args.target)
    elif args.interactive or args.chat or not args.command:
        await interactive_mode()
    elif args.command in ['review', 'security', 'fix', 'commit', 'explain', 'test', 'todo', 'scan']:
        # Handle subcommand-style usage
        if args.command == 'review':
            await quick_review(args.path)
        elif args.command == 'security':
            await security_audit(args.path)
        elif args.command == 'fix':
            await quick_fix(args.path)
        elif args.command == 'commit':
            await generate_commit_message()
        elif args.command == 'explain':
            if args.path and args.path != os.getcwd():
                await explain_code(args.path)
            else:
                print(f"{Colors.YELLOW}Usage: fred explain <file>{Colors.END}")
        elif args.command == 'test':
            if args.path and args.path != os.getcwd():
                await generate_tests(args.path)
            else:
                print(f"{Colors.YELLOW}Usage: fred test <file>{Colors.END}")
        elif args.command == 'todo':
            await find_todos(args.path)
        elif args.command == 'scan':
            await full_scan(args.path)
    else:
        # Treat as natural language task
        task = args.command + (" " + args.path if args.path != os.getcwd() else "")
        await natural_language_task(task, os.getcwd())


def main():
    """Main entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
