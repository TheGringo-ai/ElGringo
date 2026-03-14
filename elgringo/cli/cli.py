#!/usr/bin/env python3
"""
AI Team CLI Interface
=====================

Interactive command-line interface for the AI Team Platform.
Start with: ai-team

Commands:
  /help     - Show available commands
  /agents   - List available AI agents
  /status   - Show system status
  /index    - Index a project into RAG
  /search   - Search the knowledge base
  /clear    - Clear conversation history
  /exit     - Exit the CLI
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import warnings
import readline
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ── Suppress aiohttp/asyncio cleanup noise ──────────────────────────
warnings.filterwarnings("ignore", message=".*unclosed.*", category=ResourceWarning)
warnings.filterwarnings("ignore", message=".*Event loop is closed.*", category=RuntimeWarning)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def _quiet_event_loop_close():
    """Patch asyncio to suppress 'Event loop is closed' errors on exit."""
    _original_del = getattr(asyncio.selector_events._SelectorTransport, "__del__", None)
    if _original_del:
        def _patched_del(self, *args, **kwargs):
            try:
                _original_del(self, *args, **kwargs)
            except (OSError, RuntimeError):
                pass
        asyncio.selector_events._SelectorTransport.__del__ = _patched_del


try:
    _quiet_event_loop_close()
except Exception:
    pass  # Not critical — just noise suppression


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


# CLI Commands for tab completion
CLI_COMMANDS = [
    "/help", "/agents", "/status", "/index", "/search", "/history",
    "/clear", "/project", "/validate", "/mode", "/exit", "/quit",
    "/react", "/reason", "/plan", "/git", "/commit", "/run", "/exec",
    "/new", "/create", "/build", "/templates", "/analyze", "/screenshot",
    "/voice", "/listen",
]

CLI_MODES = ["auto", "quick", "team", "deep", "parallel", "sequential", "debate", "turbo"]
CLI_GIT_SUBCMDS = ["status", "log", "diff", "branch"]


def _cli_completer(text, state):
    """Readline completer for CLI commands and subcommands."""
    line = readline.get_line_buffer().lstrip()

    if line.startswith("/git "):
        sub = line[5:]
        options = [s for s in CLI_GIT_SUBCMDS if s.startswith(sub)]
    elif line.startswith("/mode "):
        sub = line[6:]
        options = [m for m in CLI_MODES if m.startswith(sub)]
    elif line.startswith("/"):
        options = [c for c in CLI_COMMANDS if c.startswith(text)]
    else:
        options = []

    if state < len(options):
        return options[state]
    return None


readline.set_completer(_cli_completer)
readline.set_completer_delims(" \t")
readline.parse_and_bind("tab: complete")


class AITeamCLI:
    """Interactive CLI for the AI Team Platform."""

    BANNER = f"""
{Colors.CYAN}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     █████╗ ██╗    ████████╗███████╗ █████╗ ███╗   ███╗       ║
    ║    ██╔══██╗██║    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║       ║
    ║    ███████║██║       ██║   █████╗  ███████║██╔████╔██║       ║
    ║    ██╔══██║██║       ██║   ██╔══╝  ██╔══██║██║╚██╔╝██║       ║
    ║    ██║  ██║██║       ██║   ███████╗██║  ██║██║ ╚═╝ ██║       ║
    ║    ╚═╝  ╚═╝╚═╝       ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝       ║
    ║                                                               ║
    ║              El Gringo — AI Orchestration Platform              ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
{Colors.RESET}
    {Colors.DIM}Type your request or /help for commands{Colors.RESET}
    """

    def __init__(self, project_name: str = "default"):
        self.orchestrator = None
        self.rag = None
        self.validator = None
        self.conversation_history: List[dict] = []
        self.current_project: Optional[str] = None
        self.project_name = project_name
        self.running = True

    async def initialize(self):
        """Initialize the AI Team components."""
        print(f"\n{Colors.YELLOW}Initializing AI Team...{Colors.RESET}")

        try:
            # Import orchestrator
            from elgringo.orchestrator import AIDevTeam
            self.orchestrator = AIDevTeam(project_name=self.project_name)
            agent_count = len(self.orchestrator.agents) if self.orchestrator.agents else 0
            print(f"  {Colors.GREEN}✓{Colors.RESET} Orchestrator ready ({agent_count} agents)")

            # Import RAG
            try:
                from elgringo.knowledge import get_rag
                self.rag = get_rag()
                doc_count = len(self.rag._documents) if hasattr(self.rag, '_documents') else 0
                print(f"  {Colors.GREEN}✓{Colors.RESET} RAG system ready ({doc_count} documents)")
            except Exception as e:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} RAG system: {e}")

            # Import validator
            try:
                from elgringo.validation import get_validator
                self.validator = get_validator()
                print(f"  {Colors.GREEN}✓{Colors.RESET} Code validator ready")
            except Exception as e:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} Validator: {e}")

            # Check available agents
            agents = self._get_available_agents()
            print(f"  {Colors.GREEN}✓{Colors.RESET} Available: {', '.join(agents)}")

            print(f"\n{Colors.GREEN}AI Team ready!{Colors.RESET}\n")

        except Exception as e:
            print(f"\n{Colors.RED}Error initializing: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            print(f"{Colors.YELLOW}Some features may be limited.{Colors.RESET}\n")

    def _get_available_agents(self) -> List[str]:
        """Get list of available AI agents based on API keys."""
        agents = []

        if os.getenv("ANTHROPIC_API_KEY"):
            agents.append("Claude")
        if os.getenv("OPENAI_API_KEY"):
            agents.append("ChatGPT")
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            agents.append("Gemini")
        if os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"):
            agents.append("Grok")

        # Check for local models
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                if "qwen" in result.stdout.lower():
                    agents.append("Qwen-Local")
                if "llama" in result.stdout.lower():
                    agents.append("Llama-Local")
        except Exception:
            pass

        return agents if agents else ["None configured"]

    def print_banner(self):
        """Print the welcome banner."""
        print(self.BANNER)

    def print_help(self):
        """Print help information."""
        help_text = f"""
{Colors.BOLD}Available Commands:{Colors.RESET}

  {Colors.CYAN}/help{Colors.RESET}              Show this help message
  {Colors.CYAN}/agents{Colors.RESET}            List available AI agents
  {Colors.CYAN}/status{Colors.RESET}            Show system status
  {Colors.CYAN}/index <path>{Colors.RESET}      Index a project into RAG
  {Colors.CYAN}/search <query>{Colors.RESET}    Search the knowledge base
  {Colors.CYAN}/history{Colors.RESET}           Show conversation history
  {Colors.CYAN}/clear{Colors.RESET}             Clear conversation history
  {Colors.CYAN}/project <path>{Colors.RESET}    Set current project context
  {Colors.CYAN}/validate <file>{Colors.RESET}   Validate a code file
  {Colors.CYAN}/mode <mode>{Colors.RESET}       Set collaboration mode (parallel/sequential/consensus)
  {Colors.CYAN}/exit{Colors.RESET}              Exit the CLI

{Colors.BOLD}Advanced Agent Framework:{Colors.RESET}

  {Colors.CYAN}/react <task>{Colors.RESET}      ReAct agent - reasoning + tool use
  {Colors.CYAN}/reason <problem>{Colors.RESET}  Chain-of-thought reasoning
  {Colors.CYAN}/plan <goal>{Colors.RESET}       Create and execute a multi-step plan

{Colors.BOLD}Git Automation:{Colors.RESET}

  {Colors.CYAN}/git{Colors.RESET}               Show git commands
  {Colors.CYAN}/git status{Colors.RESET}        Show repository status
  {Colors.CYAN}/git log{Colors.RESET}           Show recent commits
  {Colors.CYAN}/git diff{Colors.RESET}          Show changes
  {Colors.CYAN}/commit{Colors.RESET}            Smart commit (AI-generated message)
  {Colors.CYAN}/commit <msg>{Colors.RESET}      Commit with custom message

{Colors.BOLD}Code Execution:{Colors.RESET}

  {Colors.CYAN}/run python <code>{Colors.RESET}  Execute Python code
  {Colors.CYAN}/run js <code>{Colors.RESET}      Execute JavaScript code
  {Colors.CYAN}/run file <path>{Colors.RESET}    Execute a file

{Colors.BOLD}Autonomous Build:{Colors.RESET}

  {Colors.CYAN}/build <description>{Colors.RESET}    Plan, generate, test, fix — fully autonomous
  {Colors.CYAN}/new <template> <name>{Colors.RESET}  Create from template
  {Colors.CYAN}/new <description>{Colors.RESET}      AI generates project
  {Colors.CYAN}/templates{Colors.RESET}              List available templates

{Colors.BOLD}Screenshot Analysis:{Colors.RESET}

  {Colors.CYAN}/analyze <path>{Colors.RESET}         Analyze image with AI
  {Colors.CYAN}/analyze <path> code{Colors.RESET}    Convert UI to code
  {Colors.CYAN}/analyze <path> error{Colors.RESET}   Debug error screenshot

{Colors.BOLD}Voice Commands:{Colors.RESET}

  {Colors.CYAN}/voice{Colors.RESET}                  Speak a request
  {Colors.CYAN}/voice code{Colors.RESET}             Speak to generate code
  {Colors.CYAN}/voice file <path>{Colors.RESET}      Transcribe audio file

{Colors.BOLD}Usage:{Colors.RESET}

  Just type your request naturally:

  {Colors.DIM}> Create a FastAPI endpoint for user authentication
  > Fix the bug in my Firebase security rules
  > Review this code for performance issues
  > Help me write tests for the payment module{Colors.RESET}

{Colors.BOLD}Framework Examples:{Colors.RESET}

  {Colors.DIM}/react Find all Python files with TODO comments
  /reason What is the time complexity of quicksort?
  /plan Set up a new Flask project with tests{Colors.RESET}

{Colors.BOLD}Tips:{Colors.RESET}

  - Set a project with /project to give context
  - Use /index to add your codebase to the knowledge base
  - Use /react for tasks requiring tool use
  - The AI team will collaborate to solve complex tasks
"""
        print(help_text)

    async def handle_command(self, command: str) -> bool:
        """Handle a CLI command. Returns False if should exit."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ["/exit", "/quit", "/q"]:
            print(f"\n{Colors.CYAN}Goodbye! The AI Team will be here when you need us.{Colors.RESET}\n")
            return False

        elif cmd == "/help":
            self.print_help()

        elif cmd == "/agents":
            await self.show_agents()

        elif cmd == "/status":
            await self.show_status()

        elif cmd == "/index":
            await self.index_project(args)

        elif cmd == "/search":
            await self.search_knowledge(args)

        elif cmd == "/history":
            self.show_history()

        elif cmd == "/clear":
            self.clear_history()

        elif cmd == "/project":
            self.set_project(args)

        elif cmd == "/validate":
            await self.validate_file(args)

        elif cmd == "/mode":
            self.set_mode(args)

        elif cmd == "/react":
            await self.run_react(args)

        elif cmd == "/reason":
            await self.run_reason(args)

        elif cmd == "/plan":
            await self.run_plan(args)

        elif cmd == "/git":
            await self.run_git(args)

        elif cmd == "/commit":
            await self.run_smart_commit(args)

        elif cmd == "/status" and args.strip() == "git":
            await self.run_git("status")

        elif cmd == "/run":
            await self.run_code(args)

        elif cmd == "/exec":
            await self.run_code(args)

        elif cmd in ["/new", "/create"]:
            await self.create_project(args)

        elif cmd == "/build":
            await self.build_project(args)

        elif cmd == "/templates":
            await self.list_templates()

        elif cmd == "/analyze":
            await self.analyze_screenshot(args)

        elif cmd == "/screenshot":
            await self.analyze_screenshot(args)

        elif cmd == "/voice":
            await self.voice_input(args)

        elif cmd == "/listen":
            await self.voice_input(args)

        else:
            print(f"{Colors.RED}Unknown command: {cmd}{Colors.RESET}")
            print(f"Type {Colors.CYAN}/help{Colors.RESET} for available commands")

        return True

    async def show_agents(self):
        """Show available AI agents."""
        print(f"\n{Colors.BOLD}Available AI Agents:{Colors.RESET}\n")

        agents_info = [
            ("Claude", "ANTHROPIC_API_KEY", "Lead Architect - Analysis, planning, complex reasoning"),
            ("ChatGPT", "OPENAI_API_KEY", "Senior Developer - Coding, debugging, optimization"),
            ("Gemini", "GEMINI_API_KEY,GOOGLE_API_KEY", "Creative Innovator - UI/UX, creative solutions"),
            ("Grok", "XAI_API_KEY,GROK_API_KEY", "Strategic Reasoner - Analysis, strategy"),
            ("Local", None, "Fast Coder - Quick tasks, offline capability (Ollama)"),
        ]

        for name, env_vars, description in agents_info:
            if env_vars:
                available = any(os.getenv(v) for v in env_vars.split(","))
            else:
                available = any("Local" in a for a in self._get_available_agents())

            status = f"{Colors.GREEN}●{Colors.RESET}" if available else f"{Colors.RED}○{Colors.RESET}"
            print(f"  {status} {Colors.BOLD}{name:12}{Colors.RESET} - {description}")

        # Show actual agent instances if orchestrator is available
        if self.orchestrator and self.orchestrator.agents:
            print(f"\n{Colors.BOLD}Active Agent Instances:{Colors.RESET}")
            for name, agent in self.orchestrator.agents.items():
                model = getattr(agent, 'model_type', 'unknown')
                role = getattr(agent, 'role', 'agent')
                print(f"  {Colors.GREEN}●{Colors.RESET} {name} ({model}) - {role}")

        print()

    async def show_status(self):
        """Show system status."""
        print(f"\n{Colors.BOLD}System Status:{Colors.RESET}\n")

        # Orchestrator status
        if self.orchestrator:
            agent_count = len(self.orchestrator.agents) if self.orchestrator.agents else 0
            print(f"  {Colors.GREEN}●{Colors.RESET} Orchestrator ({agent_count} agents)")
        else:
            print(f"  {Colors.RED}○{Colors.RESET} Orchestrator")

        # RAG status
        if self.rag:
            doc_count = len(self.rag._documents) if hasattr(self.rag, '_documents') else 0
            print(f"  {Colors.GREEN}●{Colors.RESET} RAG System ({doc_count} documents)")
        else:
            print(f"  {Colors.RED}○{Colors.RESET} RAG System")

        # Validation status
        if self.validator:
            print(f"  {Colors.GREEN}●{Colors.RESET} Code Validator")
        else:
            print(f"  {Colors.RED}○{Colors.RESET} Code Validator")

        # Current project
        if self.current_project:
            print(f"\n  {Colors.CYAN}Current Project:{Colors.RESET} {self.current_project}")

        # Conversation history
        print(f"  {Colors.CYAN}Conversation History:{Colors.RESET} {len(self.conversation_history)} messages")

        # Available agents
        agents = self._get_available_agents()
        print(f"  {Colors.CYAN}Available Models:{Colors.RESET} {', '.join(agents)}")

        print()

    async def index_project(self, path: str):
        """Index a project into RAG."""
        if not path:
            path = os.getcwd()
            print(f"{Colors.YELLOW}No path specified, using current directory: {path}{Colors.RESET}")

        path = os.path.expanduser(path)
        if not os.path.exists(path):
            print(f"{Colors.RED}Path does not exist: {path}{Colors.RESET}")
            return

        if not self.rag:
            print(f"{Colors.RED}RAG system not available{Colors.RESET}")
            return

        print(f"\n{Colors.YELLOW}Indexing project: {path}{Colors.RESET}")
        print(f"{Colors.DIM}This may take a moment...{Colors.RESET}\n")

        try:
            count = await asyncio.to_thread(self.rag.index_project_files, path)
            print(f"{Colors.GREEN}✓ Indexed {count} documents from {path}{Colors.RESET}\n")
        except Exception as e:
            print(f"{Colors.RED}Error indexing: {e}{Colors.RESET}\n")

    async def search_knowledge(self, query: str):
        """Search the knowledge base."""
        if not query:
            print(f"{Colors.RED}Please provide a search query{Colors.RESET}")
            return

        if not self.rag:
            print(f"{Colors.RED}RAG system not available{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}Searching for: {query}{Colors.RESET}\n")

        try:
            results = self.rag.search(query, limit=5)
            if results:
                for i, result in enumerate(results, 1):
                    print(f"{Colors.BOLD}{i}. [{result.doc_type}]{Colors.RESET} {result.title}")
                    print(f"   {Colors.DIM}Score: {result.score:.3f}{Colors.RESET}")
                    preview = result.content[:150].replace('\n', ' ')
                    print(f"   {preview}...")
                    print()
            else:
                print(f"{Colors.YELLOW}No results found{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Error searching: {e}{Colors.RESET}")

    def show_history(self):
        """Show conversation history."""
        if not self.conversation_history:
            print(f"\n{Colors.YELLOW}No conversation history{Colors.RESET}\n")
            return

        print(f"\n{Colors.BOLD}Conversation History:{Colors.RESET}\n")
        for entry in self.conversation_history[-10:]:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")[:100]
            timestamp = entry.get("timestamp", "")

            if role == "user":
                print(f"  {Colors.GREEN}You:{Colors.RESET} {content}")
            else:
                print(f"  {Colors.CYAN}AI:{Colors.RESET} {content}...")
            if timestamp:
                print(f"      {Colors.DIM}{timestamp}{Colors.RESET}")
        print()

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print(f"\n{Colors.GREEN}Conversation history cleared{Colors.RESET}\n")

    def set_project(self, path: str):
        """Set the current project context."""
        if not path:
            if self.current_project:
                print(f"\n{Colors.CYAN}Current project:{Colors.RESET} {self.current_project}\n")
            else:
                print(f"\n{Colors.YELLOW}No project set. Use /project <path> to set one.{Colors.RESET}\n")
            return

        path = os.path.expanduser(path)
        if os.path.exists(path):
            self.current_project = os.path.abspath(path)
            print(f"\n{Colors.GREEN}Project set to: {self.current_project}{Colors.RESET}\n")
        else:
            print(f"\n{Colors.RED}Path does not exist: {path}{Colors.RESET}\n")

    def set_mode(self, mode: str):
        """Set collaboration mode."""
        valid_modes = ["parallel", "sequential", "consensus"]
        if mode.lower() in valid_modes:
            self.collaboration_mode = mode.lower()
            print(f"\n{Colors.GREEN}Collaboration mode set to: {mode}{Colors.RESET}\n")
        else:
            print(f"\n{Colors.RED}Invalid mode. Choose from: {', '.join(valid_modes)}{Colors.RESET}\n")

    async def validate_file(self, filepath: str):
        """Validate a code file."""
        if not filepath:
            print(f"{Colors.RED}Please provide a file path{Colors.RESET}")
            return

        filepath = os.path.expanduser(filepath)
        if not os.path.exists(filepath):
            print(f"{Colors.RED}File does not exist: {filepath}{Colors.RESET}")
            return

        if not self.validator:
            print(f"{Colors.RED}Validator not available{Colors.RESET}")
            return

        try:
            with open(filepath, 'r') as f:
                code = f.read()

            ext = Path(filepath).suffix.lower()
            lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.tsx': 'typescript',
                '.jsx': 'javascript',
            }
            language = lang_map.get(ext, 'python')

            print(f"\n{Colors.YELLOW}Validating {filepath}...{Colors.RESET}\n")

            result = self.validator.validate(code, language=language)

            if result.valid:
                print(f"{Colors.GREEN}✓ No errors found{Colors.RESET}")
            else:
                print(f"{Colors.RED}✗ Found {len(result.errors)} error(s){Colors.RESET}")

            if result.errors:
                print(f"\n{Colors.BOLD}Errors:{Colors.RESET}")
                for err in result.errors[:5]:
                    line_info = f" (line {err.line})" if err.line else ""
                    print(f"  {Colors.RED}•{Colors.RESET} {err.message}{line_info}")

            if result.warnings:
                print(f"\n{Colors.BOLD}Warnings:{Colors.RESET}")
                for warn in result.warnings[:5]:
                    line_info = f" (line {warn.line})" if warn.line else ""
                    print(f"  {Colors.YELLOW}•{Colors.RESET} {warn.message}{line_info}")

            if result.suggestions:
                print(f"\n{Colors.BOLD}Suggestions:{Colors.RESET}")
                for sug in result.suggestions[:3]:
                    print(f"  {Colors.CYAN}•{Colors.RESET} {sug}")

            print()

        except Exception as e:
            print(f"{Colors.RED}Error validating: {e}{Colors.RESET}\n")

    async def run_react(self, task: str):
        """Run a task using the ReAct agent pattern."""
        if not task:
            print(f"{Colors.RED}Please provide a task for the ReAct agent{Colors.RESET}")
            print(f"{Colors.DIM}Example: /react Find all Python files with TODO comments{Colors.RESET}\n")
            return

        if not self.orchestrator:
            print(f"{Colors.RED}Orchestrator not available{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}Starting ReAct Agent...{Colors.RESET}")
        print(f"{Colors.DIM}Task: {task}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}{'─' * 60}{Colors.RESET}")

        try:
            trace = await self.orchestrator.react(task, max_steps=10, verbose=False)

            # Display each step
            for step in trace.steps:
                print(f"\n{Colors.BOLD}Step {step.step_number}:{Colors.RESET}")
                print(f"  {Colors.CYAN}Thought:{Colors.RESET} {step.thought[:200]}{'...' if len(step.thought) > 200 else ''}")
                if step.action:
                    print(f"  {Colors.GREEN}Action:{Colors.RESET} {step.action}")
                    if step.action_input:
                        import json
                        params = json.dumps(step.action_input, indent=4)
                        # Indent the params
                        params = '\n'.join('    ' + line for line in params.split('\n'))
                        print(f"  {Colors.DIM}Input:{Colors.RESET}\n{params}")
                if step.observation:
                    obs = step.observation[:300] + '...' if len(step.observation) > 300 else step.observation
                    print(f"  {Colors.YELLOW}Observation:{Colors.RESET} {obs}")

            print(f"\n{Colors.YELLOW}{'─' * 60}{Colors.RESET}")
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}")
            status = f"{Colors.GREEN}✓ Completed{Colors.RESET}" if trace.success else f"{Colors.RED}✗ Failed{Colors.RESET}"
            print(f"{status} in {trace.execution_time:.2f}s | Steps: {len(trace.steps)} | Tools: {', '.join(trace.tools_used) or 'None'}")
            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
            print(f"\n{Colors.BOLD}Final Answer:{Colors.RESET}")
            print(trace.final_answer)
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}\n")

        except Exception as e:
            print(f"{Colors.RED}ReAct error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

    async def run_reason(self, problem: str):
        """Run chain-of-thought reasoning on a problem."""
        if not problem:
            print(f"{Colors.RED}Please provide a problem to reason about{Colors.RESET}")
            print(f"{Colors.DIM}Example: /reason What is the time complexity of merge sort?{Colors.RESET}\n")
            return

        if not self.orchestrator:
            print(f"{Colors.RED}Orchestrator not available{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}Starting Chain-of-Thought Reasoning...{Colors.RESET}")
        print(f"{Colors.DIM}Problem: {problem}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}{'─' * 60}{Colors.RESET}")

        try:
            chain = await self.orchestrator.reason(problem, method="zero_shot")

            # Display reasoning steps
            for step in chain.steps:
                print(f"\n{Colors.BOLD}Step {step.step_number}:{Colors.RESET}")
                print(f"  {step.content}")
                if step.evidence:
                    print(f"  {Colors.DIM}Evidence: {step.evidence}{Colors.RESET}")

            print(f"\n{Colors.YELLOW}{'─' * 60}{Colors.RESET}")
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}")
            print(f"Completed in {chain.execution_time:.2f}s | Confidence: {chain.confidence:.0%}")
            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
            print(f"\n{Colors.BOLD}Conclusion:{Colors.RESET}")
            print(chain.conclusion)
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}\n")

        except Exception as e:
            print(f"{Colors.RED}Reasoning error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

    async def run_plan(self, goal: str):
        """Create and execute a multi-step plan."""
        if not goal:
            print(f"{Colors.RED}Please provide a goal for the planner{Colors.RESET}")
            print(f"{Colors.DIM}Example: /plan Set up a new Flask project with tests{Colors.RESET}\n")
            return

        if not self.orchestrator:
            print(f"{Colors.RED}Orchestrator not available{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}Starting Task Planner...{Colors.RESET}")
        print(f"{Colors.DIM}Goal: {goal}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}{'─' * 60}{Colors.RESET}")

        try:
            plan = await self.orchestrator.plan_and_execute(goal)

            # Display plan steps
            print(f"\n{Colors.BOLD}Execution Plan:{Colors.RESET}")
            for step in plan.steps:
                status_emoji = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "skipped": "⏭️",
                    "blocked": "🚫",
                }.get(step.status.value, "❓")

                print(f"  {status_emoji} {step.description}")
                if step.error:
                    print(f"     {Colors.RED}Error: {step.error}{Colors.RESET}")

            # Show progress
            progress = plan.get_progress()
            print(f"\n{Colors.YELLOW}{'─' * 60}{Colors.RESET}")
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}")
            completed = progress['completed']
            total = progress['total']
            pct = progress['percent_complete']
            print(f"Plan Status: {plan.status.value} | Progress: {completed}/{total} ({pct:.0f}%)")
            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

            # Show markdown summary
            print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
            print(plan.to_markdown())
            print(f"\n{Colors.GREEN}{'═' * 60}{Colors.RESET}\n")

        except Exception as e:
            print(f"{Colors.RED}Planning error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

    async def run_git(self, args: str):
        """Run git commands."""
        if not args:
            print(f"\n{Colors.BOLD}Git Commands:{Colors.RESET}")
            print(f"  {Colors.CYAN}/git status{Colors.RESET}        - Show repository status")
            print(f"  {Colors.CYAN}/git log{Colors.RESET}           - Show recent commits")
            print(f"  {Colors.CYAN}/git diff{Colors.RESET}          - Show unstaged changes")
            print(f"  {Colors.CYAN}/git branch{Colors.RESET}        - List branches")
            print(f"  {Colors.CYAN}/git add <file>{Colors.RESET}    - Stage a file")
            print(f"  {Colors.CYAN}/git add .{Colors.RESET}         - Stage all changes")
            print(f"  {Colors.CYAN}/commit{Colors.RESET}            - Smart commit (AI message)")
            print(f"  {Colors.CYAN}/commit <msg>{Colors.RESET}      - Commit with message")
            print(f"  {Colors.CYAN}/git push{Colors.RESET}          - Push to remote")
            print(f"  {Colors.CYAN}/git pull{Colors.RESET}          - Pull from remote")
            print()
            return

        try:
            from elgringo.tools.git import create_smart_git_tools
            git = create_smart_git_tools(os.getcwd())

            parts = args.split(maxsplit=1)
            subcmd = parts[0].lower()
            subargs = parts[1] if len(parts) > 1 else ""

            if subcmd == "status":
                result = git._status()
            elif subcmd == "log":
                count = int(subargs) if subargs.isdigit() else 10
                result = git._log(count=count)
            elif subcmd == "diff":
                staged = "--staged" in subargs
                result = git._diff(staged=staged)
            elif subcmd == "branch":
                result = git._branch(all_branches="-a" in subargs)
            elif subcmd == "add":
                if subargs == "." or subargs == "-A":
                    result = git._add(all_files=True)
                else:
                    result = git._add(files=[subargs] if subargs else None)
            elif subcmd == "push":
                result = git._push()
            elif subcmd == "pull":
                result = git._pull()
            elif subcmd == "fetch":
                result = git._fetch()
            elif subcmd == "analyze":
                result = git._analyze_changes()
            else:
                print(f"{Colors.RED}Unknown git command: {subcmd}{Colors.RESET}")
                return

            if result.success:
                print(f"\n{Colors.GREEN}Git {subcmd}:{Colors.RESET}")
                print(result.output if result.output else "(no output)")
            else:
                print(f"{Colors.RED}Git error: {result.error}{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}Git error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

        print()

    async def run_smart_commit(self, message: str = ""):
        """Smart commit with AI-generated message."""
        try:
            from elgringo.tools.git import create_smart_git_tools
            git = create_smart_git_tools(os.getcwd())

            # Analyze changes first
            print(f"\n{Colors.CYAN}Analyzing changes...{Colors.RESET}")
            analysis = git._analyze_changes()

            if not analysis.success:
                print(f"{Colors.RED}Error analyzing changes: {analysis.error}{Colors.RESET}\n")
                return

            metadata = analysis.metadata
            total_files = metadata.get('total_files', 0)

            if total_files == 0:
                print(f"{Colors.YELLOW}No changes to commit{Colors.RESET}\n")
                return

            # Show what we're committing
            print(f"\n{Colors.BOLD}Changes to commit:{Colors.RESET}")
            print(f"  Added:    {metadata.get('added', 0)}")
            print(f"  Modified: {metadata.get('modified', 0)}")
            print(f"  Deleted:  {metadata.get('deleted', 0)}")

            files = metadata.get('files', {})
            if files.get('added'):
                print(f"\n  {Colors.GREEN}+ {', '.join(files['added'][:5])}{Colors.RESET}")
            if files.get('modified'):
                print(f"  {Colors.YELLOW}~ {', '.join(files['modified'][:5])}{Colors.RESET}")
            if files.get('deleted'):
                print(f"  {Colors.RED}- {', '.join(files['deleted'][:5])}{Colors.RESET}")

            # Perform commit
            print(f"\n{Colors.CYAN}Committing...{Colors.RESET}")
            result = git._smart_commit(
                message=message if message else None,
                add_all=True,
                push=False
            )

            if result.success:
                print(f"\n{Colors.GREEN}✓ Commit successful!{Colors.RESET}")
                print(f"{Colors.DIM}{result.output}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Commit failed: {result.error}{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}Commit error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

        print()

    async def run_code(self, args: str):
        """Execute code in the sandbox."""
        if not args:
            print(f"\n{Colors.BOLD}Code Execution:{Colors.RESET}")
            print(f"  {Colors.CYAN}/run python <code>{Colors.RESET}   - Run Python code")
            print(f"  {Colors.CYAN}/run js <code>{Colors.RESET}       - Run JavaScript code")
            print(f"  {Colors.CYAN}/run file <path>{Colors.RESET}     - Run a file")
            print(f"\n{Colors.BOLD}Examples:{Colors.RESET}")
            print(f"  {Colors.DIM}/run python print('Hello, World!')")
            print("  /run js console.log(2 + 2)")
            print(f"  /run python for i in range(5): print(i){Colors.RESET}")
            print()
            return

        try:
            from elgringo.sandbox import get_code_executor

            executor = get_code_executor()

            # Parse language and code
            parts = args.split(maxsplit=1)
            lang_or_cmd = parts[0].lower()
            code_or_path = parts[1] if len(parts) > 1 else ""

            if lang_or_cmd == "file":
                # Execute a file
                if not code_or_path:
                    print(f"{Colors.RED}Please provide a file path{Colors.RESET}\n")
                    return

                path = os.path.expanduser(code_or_path)
                if not os.path.exists(path):
                    print(f"{Colors.RED}File not found: {path}{Colors.RESET}\n")
                    return

                with open(path, 'r') as f:
                    code = f.read()

                # Detect language from extension
                if path.endswith('.py'):
                    language = 'python'
                elif path.endswith(('.js', '.mjs')):
                    language = 'javascript'
                else:
                    print(f"{Colors.RED}Unknown file type. Use .py or .js{Colors.RESET}\n")
                    return

                print(f"\n{Colors.CYAN}Executing {path}...{Colors.RESET}")

            elif lang_or_cmd in ('python', 'py'):
                language = 'python'
                code = code_or_path
            elif lang_or_cmd in ('javascript', 'js', 'node'):
                language = 'javascript'
                code = code_or_path
            else:
                # Assume python if no language specified
                language = 'python'
                code = args

            if not code:
                print(f"{Colors.RED}Please provide code to execute{Colors.RESET}\n")
                return

            print(f"\n{Colors.CYAN}Executing {language}...{Colors.RESET}")
            print(f"{Colors.DIM}{'─' * 40}{Colors.RESET}")

            # Validate and execute
            result = await executor.execute_with_validation(code, language)

            # Show results
            if result.success:
                print(f"{Colors.GREEN}Output:{Colors.RESET}")
                if result.stdout:
                    print(result.stdout)
                else:
                    print(f"{Colors.DIM}(no output){Colors.RESET}")
            else:
                print(f"{Colors.RED}Execution failed:{Colors.RESET}")
                if result.stderr:
                    print(result.stderr)
                if result.error:
                    print(f"{Colors.RED}{result.error}{Colors.RESET}")
                if result.timed_out:
                    print(f"{Colors.YELLOW}Execution timed out{Colors.RESET}")

            print(f"{Colors.DIM}{'─' * 40}{Colors.RESET}")
            print(f"{Colors.DIM}Exit code: {result.exit_code} | Time: {result.execution_time}s{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}Execution error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

        print()

    async def list_templates(self):
        """List available project templates."""
        from elgringo.workflows.app_generator import APP_TEMPLATES

        print(f"\n{Colors.BOLD}Available Project Templates:{Colors.RESET}\n")

        for key, template in APP_TEMPLATES.items():
            stack = ", ".join(template.get("stack", []))
            print(f"  {Colors.CYAN}{key:12}{Colors.RESET} - {template['name']}")
            print(f"               {Colors.DIM}Stack: {stack}{Colors.RESET}")

        print(f"\n{Colors.BOLD}Usage:{Colors.RESET}")
        print(f"  {Colors.CYAN}/new <template> <name>{Colors.RESET}  - Create from template")
        print(f"  {Colors.CYAN}/new <description>{Colors.RESET}      - AI generates project")
        print(f"\n{Colors.BOLD}Examples:{Colors.RESET}")
        print(f"  {Colors.DIM}/new fastapi my-api")
        print("  /new react my-dashboard")
        print(f"  /new Build a task manager with user auth{Colors.RESET}")
        print()

    async def create_project(self, args: str):
        """Create a new project from template or description."""
        if not args:
            await self.list_templates()
            return

        from elgringo.workflows.app_generator import APP_TEMPLATES, AppGenerator

        parts = args.split(maxsplit=1)
        first_arg = parts[0].lower()

        # Check if first arg is a template name
        if first_arg in APP_TEMPLATES:
            template = first_arg
            name = parts[1] if len(parts) > 1 else None

            if not name:
                print(f"{Colors.RED}Please provide a project name{Colors.RESET}")
                print(f"{Colors.DIM}Example: /new {template} my-project{Colors.RESET}\n")
                return

            print(f"\n{Colors.CYAN}Creating {template} project: {name}{Colors.RESET}")
            print(f"{Colors.DIM}This may take a moment...{Colors.RESET}\n")

            try:
                generator = AppGenerator(output_dir=os.getcwd())
                result = await generator.create_app(
                    description=f"Create a {APP_TEMPLATES[template]['name']} project",
                    name=name,
                    template=template
                )

                if result.get("success"):
                    print(f"{Colors.GREEN}✓ Project created successfully!{Colors.RESET}\n")
                    print(f"  {Colors.BOLD}Location:{Colors.RESET} {result['project_path']}")
                    print(f"  {Colors.BOLD}Template:{Colors.RESET} {result['template']}")
                    print(f"  {Colors.BOLD}Files:{Colors.RESET} {len(result.get('files_created', []))}")

                    if result.get("next_steps"):
                        print(f"\n{Colors.BOLD}Next Steps:{Colors.RESET}")
                        for step in result["next_steps"][:5]:
                            print(f"  • {step}")
                else:
                    print(f"{Colors.RED}Project creation failed{Colors.RESET}")

            except Exception as e:
                print(f"{Colors.RED}Error creating project: {e}{Colors.RESET}")
                import traceback
                traceback.print_exc()

        else:
            # Treat as natural language description
            description = args
            print(f"\n{Colors.CYAN}Generating project from description...{Colors.RESET}")
            print(f"{Colors.DIM}Description: {description[:100]}{'...' if len(description) > 100 else ''}{Colors.RESET}\n")

            try:
                generator = AppGenerator(output_dir=os.getcwd())
                result = await generator.create_app(description=description)

                if result.get("success"):
                    print(f"{Colors.GREEN}✓ Project created successfully!{Colors.RESET}\n")
                    print(f"  {Colors.BOLD}Name:{Colors.RESET} {result['project_name']}")
                    print(f"  {Colors.BOLD}Location:{Colors.RESET} {result['project_path']}")
                    print(f"  {Colors.BOLD}Template:{Colors.RESET} {result['template']}")
                    print(f"  {Colors.BOLD}Files:{Colors.RESET} {len(result.get('files_created', []))}")

                    if result.get("next_steps"):
                        print(f"\n{Colors.BOLD}Next Steps:{Colors.RESET}")
                        for step in result["next_steps"][:5]:
                            print(f"  • {step}")
                else:
                    print(f"{Colors.RED}Project creation failed{Colors.RESET}")

            except Exception as e:
                print(f"{Colors.RED}Error creating project: {e}{Colors.RESET}")
                import traceback
                traceback.print_exc()

        print()

    async def build_project(self, args: str):
        """Autonomous build — actually creates project files on disk."""
        if not args:
            print(f"\n{Colors.BOLD}Autonomous Build:{Colors.RESET}")
            print(f"  {Colors.CYAN}/build <description>{Colors.RESET}  - Build a project from a description\n")
            print(f"{Colors.BOLD}Examples:{Colors.RESET}")
            print(f"  {Colors.DIM}/build a FastAPI REST API with JWT auth and PostgreSQL")
            print("  /build a React dashboard with charts and dark mode")
            print(f"  /build a CLI tool that converts CSV to JSON{Colors.RESET}\n")
            return

        import time as _time
        from elgringo.workflows.app_generator import AppGenerator

        description = args
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.CYAN}  AUTONOMOUS BUILD{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"\n  {Colors.DIM}{description}{Colors.RESET}\n")
        print(f"  {Colors.GREEN}[1]{Colors.RESET} Analyzing requirements...")

        output_dir = self.current_project or os.getcwd()
        generator = AppGenerator(output_dir=output_dir)
        start = _time.time()

        try:
            result = await generator.create_app(description=description)
        except Exception as e:
            print(f"\n{Colors.RED}Build error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            print()
            return

        elapsed = _time.time() - start
        print(f"\n{Colors.BOLD}{'─' * 60}{Colors.RESET}")

        if result.get("success"):
            print(f"{Colors.GREEN}  BUILD COMPLETE{Colors.RESET}")
            print(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}\n")

            print(f"  {Colors.BOLD}Project:{Colors.RESET}    {result.get('project_name', 'unknown')}")
            print(f"  {Colors.BOLD}Location:{Colors.RESET}   {result.get('project_path', output_dir)}")
            print(f"  {Colors.BOLD}Template:{Colors.RESET}   {result.get('template', 'custom')}")
            print(f"  {Colors.BOLD}Files:{Colors.RESET}      {len(result.get('files_created', []))}")
            print(f"  {Colors.BOLD}Time:{Colors.RESET}       {elapsed:.1f}s")

            files = result.get("files_created", [])
            if files:
                print(f"\n  {Colors.BOLD}Created:{Colors.RESET}")
                for f in files[:15]:
                    print(f"    {Colors.DIM}{f}{Colors.RESET}")
                if len(files) > 15:
                    print(f"    {Colors.DIM}... and {len(files) - 15} more{Colors.RESET}")

            next_steps = result.get("next_steps", [])
            if next_steps:
                print(f"\n  {Colors.BOLD}Next steps:{Colors.RESET}")
                for step in next_steps[:5]:
                    print(f"    {step}")
        else:
            print(f"{Colors.RED}  BUILD FAILED{Colors.RESET}")
            print(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}")

        print()

    async def analyze_screenshot(self, args: str):
        """Analyze a screenshot or image."""
        if not args:
            print(f"\n{Colors.BOLD}Screenshot Analysis:{Colors.RESET}")
            print(f"  {Colors.CYAN}/analyze <path> [prompt]{Colors.RESET}  - Analyze an image")
            print(f"  {Colors.CYAN}/analyze <path> code{Colors.RESET}      - Convert UI to code")
            print(f"  {Colors.CYAN}/analyze <path> error{Colors.RESET}     - Analyze error screenshot")
            print(f"  {Colors.CYAN}/analyze <path> arch{Colors.RESET}      - Analyze architecture diagram")
            print(f"\n{Colors.BOLD}Examples:{Colors.RESET}")
            print(f"  {Colors.DIM}/analyze ~/Desktop/screenshot.png")
            print("  /analyze ./mockup.png Convert to React")
            print(f"  /analyze error.png error{Colors.RESET}")
            print()
            return

        parts = args.split(maxsplit=1)
        image_path = os.path.expanduser(parts[0])
        prompt_or_mode = parts[1] if len(parts) > 1 else ""

        if not os.path.exists(image_path):
            print(f"{Colors.RED}Image not found: {image_path}{Colors.RESET}\n")
            return

        try:
            from elgringo.advanced.vision import VisionEngine

            engine = VisionEngine()

            print(f"\n{Colors.CYAN}Analyzing image...{Colors.RESET}")
            print(f"{Colors.DIM}Path: {image_path}{Colors.RESET}")
            print(f"{Colors.YELLOW}{'─' * 50}{Colors.RESET}\n")

            # Determine analysis type
            mode = prompt_or_mode.lower().strip()

            if mode == "code" or mode.startswith("convert"):
                # Screenshot to code
                framework = "react"
                if "vue" in mode:
                    framework = "vue"
                elif "svelte" in mode:
                    framework = "svelte"
                elif "html" in mode:
                    framework = "html"

                print(f"{Colors.CYAN}Converting to {framework} code...{Colors.RESET}\n")
                result = await engine.screenshot_to_code(image_path, framework=framework)

            elif mode == "error":
                # Error analysis
                print(f"{Colors.CYAN}Analyzing error...{Colors.RESET}\n")
                result = await engine.analyze_error_screenshot(image_path)

            elif mode == "arch" or mode == "architecture":
                # Architecture diagram
                print(f"{Colors.CYAN}Analyzing architecture...{Colors.RESET}\n")
                result = await engine.analyze_architecture_diagram(image_path)

            else:
                # Custom prompt or general analysis
                prompt = prompt_or_mode if prompt_or_mode else """Analyze this image and provide:
1. Description of what you see
2. UI/UX feedback if it's a UI
3. Suggestions for improvement
4. Any issues or concerns"""

                result = await engine.analyze_image(image_path, prompt)

            # Display results
            print(f"{Colors.BOLD}Analysis Result:{Colors.RESET}")
            print(f"{Colors.DIM}Model: {result.model_used} | Time: {result.processing_time:.2f}s{Colors.RESET}\n")

            print(result.description)

            if result.code:
                print(f"\n{Colors.BOLD}Generated Code:{Colors.RESET}")
                print(f"{Colors.GREEN}{result.code}{Colors.RESET}")

            if result.suggestions:
                print(f"\n{Colors.BOLD}Suggestions:{Colors.RESET}")
                for s in result.suggestions:
                    print(f"  • {s}")

            print(f"\n{Colors.YELLOW}{'─' * 50}{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}Analysis error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

        print()

    async def voice_input(self, args: str):
        """Handle voice input commands."""
        if args == "help" or not args:
            print(f"\n{Colors.BOLD}Voice Commands:{Colors.RESET}")
            print(f"  {Colors.CYAN}/voice{Colors.RESET}              - Speak a command")
            print(f"  {Colors.CYAN}/voice code{Colors.RESET}         - Speak and generate code")
            print(f"  {Colors.CYAN}/voice file <path>{Colors.RESET}  - Transcribe audio file")
            print(f"\n{Colors.BOLD}Requirements:{Colors.RESET}")
            print(f"  {Colors.DIM}pip install SpeechRecognition pyaudio")
            print(f"  OPENAI_API_KEY for Whisper (best quality){Colors.RESET}")
            print(f"\n{Colors.BOLD}Examples:{Colors.RESET}")
            print(f"  {Colors.DIM}/voice              # Speak a request to AI Team")
            print(f"  /voice code        # Speak code requirements{Colors.RESET}")
            print()
            return

        try:
            from elgringo.advanced.voice import VoiceInput, VoiceToCodePipeline

            if args.startswith("file "):
                # Transcribe audio file
                file_path = os.path.expanduser(args[5:].strip())
                if not os.path.exists(file_path):
                    print(f"{Colors.RED}File not found: {file_path}{Colors.RESET}\n")
                    return

                print(f"\n{Colors.CYAN}Transcribing audio file...{Colors.RESET}")
                pipeline = VoiceToCodePipeline()
                result = await pipeline.transcribe(file_path)

                print(f"\n{Colors.BOLD}Transcription:{Colors.RESET}")
                print(result.text)
                print(f"\n{Colors.DIM}Confidence: {result.confidence:.0%} | Duration: {result.duration:.2f}s{Colors.RESET}")

            elif args == "code":
                # Voice to code
                print(f"\n{Colors.CYAN}Voice-to-Code Mode{Colors.RESET}")
                print(f"{Colors.DIM}Speak what you want to create...{Colors.RESET}\n")

                voice = VoiceInput()
                result = await voice.listen()

                if not result.text:
                    print(f"{Colors.YELLOW}No speech detected{Colors.RESET}\n")
                    return

                print(f"\n{Colors.BOLD}You said:{Colors.RESET} {result.text}")
                print(f"\n{Colors.CYAN}Generating code...{Colors.RESET}")

                pipeline = VoiceToCodePipeline()
                code_result = await pipeline.execute_voice_command(result.text)

                print(f"\n{Colors.BOLD}Generated Code:{Colors.RESET}")
                print(f"{Colors.GREEN}{code_result.code}{Colors.RESET}")

                if code_result.explanation:
                    print(f"\n{Colors.BOLD}Explanation:{Colors.RESET}")
                    print(code_result.explanation)

            else:
                # Voice command to AI Team
                print(f"\n{Colors.CYAN}Speak your request...{Colors.RESET}\n")

                voice = VoiceInput()
                result = await voice.listen()

                if not result.text:
                    print(f"{Colors.YELLOW}No speech detected{Colors.RESET}\n")
                    return

                print(f"\n{Colors.BOLD}You said:{Colors.RESET} {result.text}")
                print(f"{Colors.DIM}Confidence: {result.confidence:.0%}{Colors.RESET}")

                # Process through AI Team
                print(f"\n{Colors.CYAN}Processing with AI Team...{Colors.RESET}")
                await self.process_request(result.text)

        except ImportError as e:
            print(f"{Colors.RED}Voice input requires additional packages:{Colors.RESET}")
            print(f"{Colors.DIM}pip install SpeechRecognition pyaudio{Colors.RESET}")
            print(f"\n{Colors.DIM}Error: {e}{Colors.RESET}\n")
        except Exception as e:
            print(f"{Colors.RED}Voice error: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

        print()

    async def process_request(self, user_input: str):
        """Process a user request through the AI team."""
        if not self.orchestrator:
            print(f"{Colors.RED}Orchestrator not available. Cannot process request.{Colors.RESET}")
            return

        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })

        # Build context
        context = ""
        if self.current_project:
            context = f"Current project: {self.current_project}\n"

        print(f"\n{Colors.CYAN}AI Team is working on your request...{Colors.RESET}\n")

        try:
            # Use the orchestrator to process the request
            result = await self.orchestrator.collaborate(
                prompt=user_input,
                context=context if context else None,
            )

            # Extract the response content
            if hasattr(result, 'final_answer'):
                content = result.final_answer
                success = result.success if hasattr(result, 'success') else True
                time_taken = result.total_time if hasattr(result, 'total_time') else 0
                agents = result.participating_agents if hasattr(result, 'participating_agents') else []
                confidence = result.confidence_score if hasattr(result, 'confidence_score') else 0
            elif hasattr(result, 'content'):
                content = result.content
                success = True
                time_taken = 0
                agents = []
                confidence = 0
            elif isinstance(result, dict):
                content = result.get('content', result.get('response', result.get('final_answer', str(result))))
                success = result.get('success', True)
                time_taken = result.get('total_time', 0)
                agents = result.get('participating_agents', [])
                confidence = result.get('confidence_score', 0)
            else:
                content = str(result)
                success = True
                time_taken = 0
                agents = []
                confidence = 0

            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })

            # Print response header
            print(f"{Colors.GREEN}{'═' * 60}{Colors.RESET}")
            if success:
                status_line = f"{Colors.GREEN}✓ Completed{Colors.RESET}"
                if time_taken:
                    status_line += f" in {time_taken:.2f}s"
                if confidence:
                    status_line += f" | Confidence: {confidence:.0%}"
                if agents:
                    status_line += f" | Agents: {', '.join(agents)}"
                print(status_line)
            else:
                print(f"{Colors.RED}✗ Task had issues{Colors.RESET}")
            print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

            # Print content
            print(content)

            print(f"{Colors.GREEN}{'═' * 60}{Colors.RESET}")
            print()

        except Exception as e:
            print(f"{Colors.RED}Error processing request: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()

    async def run(self):
        """Main CLI loop."""
        self.print_banner()
        await self.initialize()

        # Setup readline for history
        histfile = os.path.expanduser("~/.ai_team_history")
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except (FileNotFoundError, PermissionError, OSError):
            pass

        self.collaboration_mode = "parallel"

        while self.running:
            try:
                # Get user input
                prompt_str = f"{Colors.BOLD}{Colors.GREEN}AI Team > {Colors.RESET}"
                user_input = input(prompt_str).strip()

                if not user_input:
                    continue

                # Check if it's a command
                if user_input.startswith("/"):
                    self.running = await self.handle_command(user_input)
                else:
                    # Process as AI request
                    await self.process_request(user_input)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.CYAN}Use /exit to quit{Colors.RESET}\n")
            except EOFError:
                print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")
                break

        # Save history
        try:
            readline.write_history_file(histfile)
        except (PermissionError, OSError):
            pass


# Legacy functions for backward compatibility with argparse mode
def print_banner():
    """Print the AI Dev Team banner"""
    cli = AITeamCLI()
    cli.print_banner()


def print_status(team):
    """Print team status"""
    status = team.get_team_status()
    print(f"\n📊 Team Status: {status['project']}")
    print(f"   Agents: {status['total_agents']}")
    print(f"   Memory: {'✓' if status['memory_enabled'] else '✗'}")
    print(f"   Learning: {'✓' if status['learning_enabled'] else '✗'}")
    print("\n   Available Agents:")
    for name, agent_stats in status['agents'].items():
        role = agent_stats.get('role', 'Unknown')
        model = agent_stats.get('model_type', 'Unknown')
        print(f"   - {name} ({model}): {role}")
    print()


async def interactive_mode(team):
    """Run interactive chat mode - now uses the new CLI"""
    cli = AITeamCLI()
    cli.orchestrator = team
    await cli.run()


async def run_single_task(team, prompt: str, mode: str = "auto", context: str = ""):
    """Run a single task with simplified mode aliases and optional context."""
    # Resolve simplified mode names
    _MODE_ALIASES = {"auto": None, "quick": "turbo", "team": "parallel", "deep": "debate"}
    resolved = _MODE_ALIASES.get(mode, mode)
    display_mode = mode if resolved else "auto (smart routing)"
    print(f"\n Running task with {len(team.agents)} agents ({display_mode})...\n")

    result = await team.collaborate(prompt, context=context, mode=resolved)

    if result.success:
        print(f"✅ Completed in {result.total_time:.2f}s")
        print(f"   Confidence: {result.confidence_score:.0%}")
        print(f"   Agents: {', '.join(result.participating_agents)}")
        print("\n" + "─" * 60)
        print(result.final_answer)
        print("─" * 60)
    else:
        print(f"❌ Failed: {result.final_answer}")

    return result


async def _run_build(description: str):
    """Run an autonomous build from the command line — actually creates project files."""
    import time as _time
    from elgringo.workflows.app_generator import AppGenerator

    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.CYAN}  EL GRINGO — AUTONOMOUS BUILD{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"\n  {Colors.DIM}{description}{Colors.RESET}\n")

    output_dir = os.getcwd()
    generator = AppGenerator(output_dir=output_dir)

    start = _time.time()

    print(f"  {Colors.GREEN}[1]{Colors.RESET} Analyzing requirements...")

    try:
        result = await generator.create_app(description=description)
    except Exception as e:
        print(f"\n{Colors.RED}  BUILD FAILED: {e}{Colors.RESET}\n")
        import traceback
        traceback.print_exc()
        return

    elapsed = _time.time() - start

    print(f"\n{Colors.BOLD}{'─' * 60}{Colors.RESET}")

    if result.get("success"):
        print(f"{Colors.GREEN}  BUILD COMPLETE{Colors.RESET}")
        print(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}\n")

        print(f"  {Colors.BOLD}Project:{Colors.RESET}    {result.get('project_name', 'unknown')}")
        print(f"  {Colors.BOLD}Location:{Colors.RESET}   {result.get('project_path', output_dir)}")
        print(f"  {Colors.BOLD}Template:{Colors.RESET}   {result.get('template', 'custom')}")
        print(f"  {Colors.BOLD}Files:{Colors.RESET}      {len(result.get('files_created', []))}")
        print(f"  {Colors.BOLD}Time:{Colors.RESET}       {elapsed:.1f}s")

        files = result.get("files_created", [])
        if files:
            print(f"\n  {Colors.BOLD}Created:{Colors.RESET}")
            for f in files[:20]:
                print(f"    {Colors.DIM}{f}{Colors.RESET}")
            if len(files) > 20:
                print(f"    {Colors.DIM}... and {len(files) - 20} more{Colors.RESET}")

        next_steps = result.get("next_steps", [])
        if next_steps:
            print(f"\n  {Colors.BOLD}Next steps:{Colors.RESET}")
            for step in next_steps[:5]:
                print(f"    {step}")

    else:
        print(f"{Colors.RED}  BUILD FAILED{Colors.RESET}")
        print(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}")

    print()


def _read_stdin_if_piped() -> str:
    """Read piped stdin if available (non-blocking)."""
    import select
    if not sys.stdin.isatty():
        # Data is being piped in
        try:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                return sys.stdin.read(50000)  # Cap at 50KB
        except Exception:
            pass
    return ""


def _gather_project_context(verbose: bool = False) -> str:
    """Auto-detect project context from the current directory."""
    import subprocess
    context_parts = []

    # Find git root
    try:
        git_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        git_root = ""

    cwd = git_root or os.getcwd()

    # Project name from directory
    project_name = os.path.basename(cwd)
    context_parts.append(f"Project: {project_name}")
    context_parts.append(f"Directory: {cwd}")

    # Detect language/framework from key files
    markers = {
        "pyproject.toml": "Python",
        "package.json": "Node.js/JavaScript",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java (Gradle)",
        "Gemfile": "Ruby",
        "requirements.txt": "Python",
    }
    for filename, lang in markers.items():
        if os.path.exists(os.path.join(cwd, filename)):
            context_parts.append(f"Language: {lang}")
            break

    # Git branch + recent changes
    if git_root:
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5, cwd=cwd,
            ).stdout.strip()
            if branch:
                context_parts.append(f"Branch: {branch}")

            # Recent git status (modified files)
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5, cwd=cwd,
            ).stdout.strip()
            if status:
                changed_files = [line[3:] for line in status.split("\n")[:10]]
                context_parts.append(f"Changed files: {', '.join(changed_files)}")

            # Last 3 commit messages
            log = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                capture_output=True, text=True, timeout=5, cwd=cwd,
            ).stdout.strip()
            if log:
                context_parts.append(f"Recent commits:\n{log}")
        except Exception:
            pass

    # Read key config files (first 20 lines) for project understanding
    for config_file in ["pyproject.toml", "package.json", "README.md"]:
        filepath = os.path.join(cwd, config_file)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    head = "".join(f.readlines()[:20])
                context_parts.append(f"\n--- {config_file} (first 20 lines) ---\n{head}")
                break  # Only read one config file
            except Exception:
                pass

    if verbose:
        print(f"{Colors.DIM}Auto-context: {'; '.join(context_parts[:5])}{Colors.RESET}")

    return "\n".join(context_parts)


# ── Per-Project Config (.elgringo.yml) ──────────────────────────────

_ELGRINGO_DIR = ".elgringo"
_BACKUP_FILE = os.path.join(_ELGRINGO_DIR, "last_change.json")
_CONFIG_FILE = ".elgringo.yml"


def _load_project_config() -> dict:
    """Load .elgringo.yml from current directory if it exists."""
    if not os.path.isfile(_CONFIG_FILE):
        return {}
    try:
        import yaml
        with open(_CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback: parse simple key: value lines
        config = {}
        try:
            with open(_CONFIG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        k, v = line.split(":", 1)
                        config[k.strip()] = v.strip()
        except Exception:
            pass
        return config
    except Exception:
        return {}


# ── Backup Persistence (for undo/diff) ──────────────────────────────

def _save_backup(project_path: str, backups: Dict[str, str], files_changed: list):
    """Save backup state to .elgringo/last_change.json for undo/diff."""
    elgringo_dir = os.path.join(project_path, _ELGRINGO_DIR)
    os.makedirs(elgringo_dir, exist_ok=True)
    backup_file = os.path.join(project_path, _BACKUP_FILE)

    data = {
        "project_path": project_path,
        "timestamp": datetime.now().isoformat(),
        "backups": backups,  # filepath -> original content
        "files_changed": [
            {"path": fc.path, "action": fc.action, "lines_changed": fc.lines_changed}
            for fc in files_changed
        ],
    }
    with open(backup_file, "w") as f:
        json.dump(data, f, indent=2)

    # Add .elgringo/ to .gitignore if not already there
    gitignore = os.path.join(project_path, ".gitignore")
    if os.path.isfile(gitignore):
        content = open(gitignore).read()
        if ".elgringo/" not in content:
            with open(gitignore, "a") as f:
                f.write("\n.elgringo/\n")
    elif os.path.isdir(os.path.join(project_path, ".git")):
        with open(gitignore, "w") as f:
            f.write(".elgringo/\n")


def _load_backup(project_path: str = None) -> dict:
    """Load the last backup state."""
    project_path = project_path or os.getcwd()
    backup_file = os.path.join(project_path, _BACKUP_FILE)
    if not os.path.isfile(backup_file):
        return {}
    try:
        with open(backup_file, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _run_undo():
    """Restore files from the last coding change."""
    import difflib

    backup = _load_backup()
    if not backup or not backup.get("backups"):
        print(f"{Colors.YELLOW}No backup found. Nothing to undo.{Colors.RESET}")
        return

    backups = backup["backups"]
    project = backup.get("project_path", os.getcwd())
    ts = backup.get("timestamp", "unknown")

    print(f"\n{Colors.BOLD}Undo last change{Colors.RESET} ({ts})")
    print(f"  Project: {project}")
    print(f"  Files to restore: {len(backups)}\n")

    for filepath in backups:
        abs_path = os.path.join(project, filepath) if not os.path.isabs(filepath) else filepath
        current = ""
        if os.path.isfile(abs_path):
            current = open(abs_path, "r", errors="replace").read()
        original = backups[filepath]
        if current == original:
            print(f"  {Colors.DIM}= {filepath} (unchanged){Colors.RESET}")
        else:
            print(f"  {Colors.YELLOW}↩ {filepath}{Colors.RESET}")

    confirm = input(f"\n  Restore these files? [y/N] ").strip().lower()
    if confirm != "y":
        print(f"  {Colors.DIM}Cancelled.{Colors.RESET}")
        return

    restored = 0
    for filepath, content in backups.items():
        abs_path = os.path.join(project, filepath) if not os.path.isabs(filepath) else filepath
        try:
            Path(abs_path).write_text(content)
            restored += 1
        except Exception as e:
            print(f"  {Colors.RED}Failed: {filepath}: {e}{Colors.RESET}")

    print(f"\n  {Colors.GREEN}Restored {restored}/{len(backups)} files.{Colors.RESET}\n")

    # Remove the backup file
    backup_file = os.path.join(project, _BACKUP_FILE)
    if os.path.isfile(backup_file):
        os.remove(backup_file)


def _run_diff():
    """Show diff of the last coding change."""
    import difflib

    backup = _load_backup()
    if not backup or not backup.get("backups"):
        print(f"{Colors.YELLOW}No recent changes to show.{Colors.RESET}")
        return

    backups = backup["backups"]
    project = backup.get("project_path", os.getcwd())
    ts = backup.get("timestamp", "unknown")

    print(f"\n{Colors.BOLD}Last change{Colors.RESET} ({ts})")
    print(f"  Project: {project}\n")

    has_diff = False
    for filepath, original in backups.items():
        abs_path = os.path.join(project, filepath) if not os.path.isabs(filepath) else filepath
        if os.path.isfile(abs_path):
            current = open(abs_path, "r", errors="replace").read()
        else:
            current = ""

        if current == original:
            continue

        has_diff = True
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
        )
        print(f"{Colors.BOLD}--- {filepath} ---{Colors.RESET}")
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                print(f"{Colors.GREEN}{line}{Colors.RESET}", end="")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"{Colors.RED}{line}{Colors.RESET}", end="")
            else:
                print(line, end="")
        print()

    if not has_diff:
        print(f"  {Colors.DIM}No differences found (files may have been restored).{Colors.RESET}\n")


# Smart subcommand definitions: name → (prompt_prefix, default_mode, needs_input)
_SMART_SUBCOMMANDS = {
    # Code-focused
    "review": ("Review this code for bugs, security issues, and improvements:\n\n", "team", True),
    "debug": ("Debug this error. Find the root cause and suggest a fix:\n\n", "quick", True),
    "explain": ("Explain this code clearly and concisely:\n\n", "quick", True),
    "test": ("Write comprehensive tests for this code:\n\n", "team", True),
    "refactor": ("Refactor this code for clarity and maintainability:\n\n", "team", True),
    "secure": ("Security audit — find vulnerabilities in this code:\n\n", "deep", True),
    "optimize": ("Optimize this code for performance:\n\n", "quick", True),
    # General-purpose
    "ask": ("", "quick", False),
    "write": ("Write the following content. Be clear, well-structured, and professional:\n\n", "quick", False),
    "analyze": ("Analyze the following thoroughly. Identify key insights, issues, and recommendations:\n\n", "team", True),
    "research": ("Research this topic. Provide a thorough, well-sourced summary with key findings and recommendations:\n\n", "deep", False),
    "plan": ("Create a detailed, actionable plan for the following. Include steps, dependencies, and risks:\n\n", "team", False),
    "summarize": ("Summarize the following concisely. Highlight the key points:\n\n", "quick", True),
    "convert": ("Convert the following to the requested format. Preserve all data accurately:\n\n", "quick", True),
    "deploy": ("Help with this deployment/DevOps task. Give specific commands and configs:\n\n", "quick", False),
}

# Coding subcommands that write files (use CodingAgentEngine)
_CODING_SUBCOMMANDS = {"fix", "code", "implement"}


async def _run_coding_task(
    task: str,
    files: list = None,
    dry_run: bool = False,
    auto_commit: bool = False,
    test_cmd: str = "",
    no_tests: bool = False,
    yes: bool = False,
):
    """Run a coding task that reads, edits, and writes files.

    Flow: plan (dry-run) → show plan → confirm → execute → save backup.
    """
    import time as _time

    project_path = os.getcwd()

    # Load per-project config
    config = _load_project_config()
    if not test_cmd and config.get("test_command"):
        test_cmd = config["test_command"]
    if config.get("preferred_agents"):
        # Will be passed as allowed_agents
        pass

    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.CYAN}  EL GRINGO — CODING AGENT{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"\n  {Colors.DIM}Project: {project_path}{Colors.RESET}")
    if config:
        print(f"  {Colors.DIM}Config: .elgringo.yml loaded{Colors.RESET}")
    if dry_run:
        print(f"  {Colors.YELLOW}DRY RUN — planning only, no changes{Colors.RESET}")
    print(f"\n  {Colors.GREEN}Task:{Colors.RESET} {task[:120]}\n")

    from elgringo.orchestrator import AIDevTeam
    from products.fred_api.coding_endpoints import (
        CodingAgentEngine,
        CodingTaskRequest,
        ProjectTools,
    )

    team = AIDevTeam(enable_memory=True)
    if not team.agents:
        print(f"{Colors.RED}No agents available. Set API keys.{Colors.RESET}")
        return

    tools = ProjectTools(project_path)
    engine = CodingAgentEngine(team=team, tools=tools)

    allowed_agents = config.get("preferred_agents") if config.get("preferred_agents") else None

    # ── Step 1: Plan first (dry-run) unless --yes or already --dry-run ──
    if not dry_run and not yes:
        print(f"  {Colors.DIM}Planning...{Colors.RESET}\n")
        plan_request = CodingTaskRequest(
            task=task,
            project_path=project_path,
            files_to_read=files or [],
            run_tests=False,
            test_command=test_cmd,
            auto_commit=False,
            dry_run=True,
            allowed_agents=allowed_agents,
        )

        try:
            plan_result = await engine.execute_task(plan_request)
        except Exception as e:
            print(f"\n{Colors.RED}  Planning failed: {e}{Colors.RESET}\n")
            return

        # Show the plan
        if plan_result.plan:
            print(f"  {Colors.BOLD}Plan:{Colors.RESET}")
            for step in plan_result.plan[:15]:  # Cap display at 15 steps
                print(f"    {Colors.DIM}{step}{Colors.RESET}")
            print()

        print(f"  {Colors.DIM}Agents: {', '.join(plan_result.agents_used)}{Colors.RESET}")
        print()

        # Ask for confirmation (use /dev/tty if stdin is piped)
        try:
            if sys.stdin.isatty():
                confirm = input(f"  {Colors.BOLD}Apply these changes? [y/N]{Colors.RESET} ").strip().lower()
            else:
                tty = open("/dev/tty", "r")
                print(f"  {Colors.BOLD}Apply these changes? [y/N]{Colors.RESET} ", end="", flush=True)
                confirm = tty.readline().strip().lower()
                tty.close()
        except (EOFError, OSError):
            # Non-interactive (CI, piped) — skip confirmation
            confirm = "y"

        if confirm != "y":
            print(f"\n  {Colors.DIM}Cancelled.{Colors.RESET}\n")
            return
        print()

    # ── Step 2: Execute for real ─────────────────────────────────────
    # Create a fresh engine so it gets clean state
    engine = CodingAgentEngine(team=team, tools=tools)

    request = CodingTaskRequest(
        task=task,
        project_path=project_path,
        files_to_read=files or [],
        run_tests=not no_tests,
        test_command=test_cmd,
        auto_commit=auto_commit,
        dry_run=dry_run,
        allowed_agents=allowed_agents,
    )

    start = _time.time()
    if not dry_run:
        print(f"  {Colors.DIM}Applying changes...{Colors.RESET}\n")
    else:
        print(f"  {Colors.DIM}Planning...{Colors.RESET}\n")

    try:
        result = await engine.execute_task(request)
    except Exception as e:
        print(f"\n{Colors.RED}  FAILED: {e}{Colors.RESET}\n")
        import traceback
        traceback.print_exc()
        return

    elapsed = _time.time() - start

    # ── Step 3: Save backup for undo/diff ────────────────────────────
    if not dry_run and engine._backups and result.files_changed:
        _save_backup(project_path, engine._backups, result.files_changed)

    # ── Display results ──────────────────────────────────────────────
    print(f"\n{Colors.BOLD}{'─' * 60}{Colors.RESET}")

    status_color = Colors.GREEN if result.status == "success" else (
        Colors.YELLOW if result.status in ("partial", "dry_run") else Colors.RED
    )
    print(f"{status_color}  {result.status.upper()}{Colors.RESET} in {elapsed:.1f}s ({result.iterations} iteration{'s' if result.iterations != 1 else ''})")
    print(f"  Agents: {', '.join(result.agents_used)}")
    print(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}\n")

    if result.plan:
        print(f"  {Colors.BOLD}Plan:{Colors.RESET}")
        for step in result.plan:
            print(f"    • {step}")
        print()

    if result.files_changed:
        print(f"  {Colors.BOLD}Files changed ({len(result.files_changed)}):{Colors.RESET}")
        for fc in result.files_changed:
            icon = {"created": "+", "modified": "~", "deleted": "-"}.get(fc.action, "?")
            color = {"created": Colors.GREEN, "modified": Colors.YELLOW, "deleted": Colors.RED}.get(fc.action, Colors.RESET)
            print(f"    {color}{icon} {fc.path}{Colors.RESET} ({fc.lines_changed} lines)")
        print()

    if result.test_results:
        tr = result.test_results
        test_icon = "✅" if tr.passed else "❌"
        print(f"  {Colors.BOLD}Tests:{Colors.RESET} {test_icon} {tr.command} ({tr.duration_seconds:.1f}s)")
        if not tr.passed:
            lines = tr.output.strip().split("\n")
            for line in lines[-10:]:
                print(f"    {Colors.DIM}{line}{Colors.RESET}")
        print()

    if result.git_commit:
        print(f"  {Colors.GREEN}Committed: {result.git_commit}{Colors.RESET}\n")

    if result.errors:
        print(f"  {Colors.RED}Errors:{Colors.RESET}")
        for err in result.errors:
            print(f"    • {err}")
        print()

    print(f"  {Colors.BOLD}Summary:{Colors.RESET} {result.summary}\n")

    if not dry_run and result.files_changed:
        print(f"  {Colors.DIM}Tip: 'elgringo undo' to revert, 'elgringo diff' to review changes{Colors.RESET}\n")

    return result


def main():
    """Main CLI entry point"""
    # Intercept smart subcommands: elgringo review, elgringo debug, etc.
    if len(sys.argv) > 1 and sys.argv[1] in _SMART_SUBCOMMANDS:
        subcmd = sys.argv[1]
        prefix, default_mode, needs_input = _SMART_SUBCOMMANDS[subcmd]
        extra_args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

        # Read piped input
        piped = _read_stdin_if_piped()

        if needs_input and not piped and not extra_args:
            # Try to read a file if one exists as arg
            print(f"{Colors.BOLD}Usage:{Colors.RESET} elgringo {subcmd} <file_or_text>")
            print(f"       cat file.py | elgringo {subcmd}")
            print(f"       git diff | elgringo {subcmd}")
            sys.exit(0)

        prompt = prefix
        if extra_args:
            # Check if it's a file path
            if os.path.isfile(extra_args):
                try:
                    with open(extra_args, "r") as f:
                        file_content = f.read(50000)
                    prompt += f"File: {extra_args}\n```\n{file_content}\n```"
                except Exception:
                    prompt += extra_args
            else:
                prompt += extra_args
        if piped:
            prompt += f"\n```\n{piped}\n```"

        # Gather auto-context and run
        context = _gather_project_context()

        from elgringo.orchestrator import AIDevTeam
        team = AIDevTeam(enable_memory=True)
        if not team.agents:
            print("No agents available. Set API keys (OPENAI_API_KEY, GOOGLE_API_KEY, XAI_API_KEY)")
            sys.exit(1)

        result = asyncio.run(run_single_task(team, prompt, default_mode, context=context))
        sys.exit(0 if result.success else 1)

    # Intercept undo/diff commands
    if len(sys.argv) > 1 and sys.argv[1] == "undo":
        _run_undo()
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "diff":
        _run_diff()
        sys.exit(0)

    # Intercept coding subcommands: elgringo fix, elgringo code, elgringo implement
    if len(sys.argv) > 1 and sys.argv[1] in _CODING_SUBCOMMANDS:
        subcmd = sys.argv[1]
        # Parse coding-specific flags
        remaining = sys.argv[2:]
        dry_run = "--dry-run" in remaining or "--plan" in remaining
        auto_commit = "--commit" in remaining
        no_tests = "--no-tests" in remaining
        yes = "--yes" in remaining or "-y" in remaining
        test_cmd = ""
        files = []

        # Filter out flags, collect files and task text
        task_parts = []
        i = 0
        while i < len(remaining):
            arg = remaining[i]
            if arg in ("--dry-run", "--plan", "--commit", "--no-tests", "--yes", "-y"):
                pass
            elif arg == "--test-cmd" and i + 1 < len(remaining):
                test_cmd = remaining[i + 1]
                i += 1
            elif os.path.isfile(arg):
                files.append(arg)
            else:
                task_parts.append(arg)
            i += 1

        # Read piped input as additional context
        piped = _read_stdin_if_piped()

        task = " ".join(task_parts)
        if piped:
            task = f"{task}\n\nContext:\n```\n{piped}\n```" if task else piped

        if not task:
            print(f"\n{Colors.BOLD}Usage:{Colors.RESET} elgringo {subcmd} \"description of changes\"")
            print(f"\n{Colors.BOLD}Examples:{Colors.RESET}")
            print(f"  elgringo fix \"add error handling to the login endpoint\"")
            print(f"  elgringo code \"add a /health endpoint that returns uptime\" server.py")
            print(f"  elgringo implement \"add JWT auth middleware\" --commit")
            print(f"  elgringo fix \"fix the TypeError in utils.py\" utils.py --no-tests")
            print(f"  elgringo code \"refactor to async\" api.py --dry-run")
            print(f"\n{Colors.BOLD}Flags:{Colors.RESET}")
            print(f"  --dry-run, --plan   Plan only, don't write files")
            print(f"  --commit            Auto-commit if tests pass")
            print(f"  --no-tests          Skip running tests")
            print(f"  --yes, -y           Skip confirmation prompt")
            print(f"  --test-cmd \"cmd\"    Custom test command\n")
            sys.exit(0)

        asyncio.run(_run_coding_task(
            task=task,
            files=files,
            dry_run=dry_run,
            auto_commit=auto_commit,
            test_cmd=test_cmd,
            no_tests=no_tests,
            yes=yes,
        ))
        sys.exit(0)

    # Intercept "build" subcommand before argparse
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not description:
            print(f"\n{Colors.BOLD}Usage:{Colors.RESET} elgringo build <description>\n")
            print(f"{Colors.BOLD}Examples:{Colors.RESET}")
            print("  elgringo build \"a FastAPI REST API with JWT auth\"")
            print("  elgringo build \"a React dashboard with charts\"")
            print("  elgringo build \"a CLI tool that converts CSV to JSON\"\n")
            sys.exit(0)
        asyncio.run(_run_build(description))
        sys.exit(0)

    # Intercept "products" subcommand before argparse (avoids conflict with positional prompt)
    if len(sys.argv) > 1 and sys.argv[1] == "products":
        from products.cli import handle_products_command

        class _Args:
            pass

        args = _Args()
        args.products_action = sys.argv[2] if len(sys.argv) > 2 else "list"
        args.product_name = sys.argv[3] if len(sys.argv) > 3 else ""
        handle_products_command(args)
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="El Gringo - Multi-Agent AI Orchestration Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  elgringo                                    # Interactive mode
  elgringo "Write a REST API"                 # Smart routing (auto)
  elgringo -m quick "Fix this bug"            # Single best agent
  elgringo -m deep "Design auth system"       # Full team debate
  elgringo build "a FastAPI app with auth"    # Autonomous build
  elgringo --status                           # Show team status

Pipe support:
  cat error.log | elgringo debug              # Debug from piped input
  git diff | elgringo review                  # Review staged changes
  cat data.csv | elgringo analyze             # Analyze data
  cat README.md | elgringo summarize          # Summarize a doc

Code subcommands:
  elgringo review <file>    Code review (team)
  elgringo debug <error>    Debug an error (quick)
  elgringo explain <file>   Explain code (quick)
  elgringo test <file>      Generate tests (team)
  elgringo refactor <file>  Refactor code (team)
  elgringo secure <file>    Security audit (deep)
  elgringo optimize <file>  Optimize perf (quick)

General subcommands:
  elgringo ask "question"           Ask anything (quick)
  elgringo write "blog post about"  Write content (quick)
  elgringo analyze <file>           Analyze data/logs (team)
  elgringo research "topic"         Deep research (deep)
  elgringo plan "project idea"      Create action plan (team)
  elgringo summarize <file>         Summarize content (quick)
  elgringo convert <file> "to yaml" Convert formats (quick)
  elgringo deploy "setup nginx"     DevOps guidance (quick)

Coding (writes files — asks before applying):
  elgringo fix "add error handling"           Edit existing code
  elgringo code "add /health endpoint" app.py Write new code
  elgringo implement "add JWT auth" --commit  Implement + auto-commit
  elgringo fix "fix bug" --dry-run            Plan only, no changes
  elgringo fix "add logging" --yes            Skip confirmation
  elgringo undo                               Revert last change
  elgringo diff                               Show last change diff
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Task prompt (optional, interactive mode if not provided)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["auto", "quick", "team", "deep", "parallel", "sequential", "debate", "turbo"],
        default="auto",
        help="Collaboration mode: auto (smart routing), quick (single agent), team (full collab), deep (debate)",
    )
    parser.add_argument(
        "-p", "--project",
        default="default",
        help="Project name for memory/learning",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show team status and exit",
    )
    parser.add_argument(
        "--check-keys",
        action="store_true",
        help="Check API key configuration",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memory system",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Disable auto project context detection",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Check API keys
    if args.check_keys:
        print("\n API Key Status:\n")
        keys = {
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "grok": bool(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")),
        }
        for name, configured in keys.items():
            status = "Configured" if configured else "Not set"
            print(f"   {name.upper()}: {status}")
        print()
        sys.exit(0)

    # Import here to avoid circular imports
    from elgringo.orchestrator import AIDevTeam

    # Show status only
    if args.status:
        team = AIDevTeam(project_name=args.project, enable_memory=not args.no_memory)
        if not args.json:
            print_banner()
        print_status(team)
        sys.exit(0)

    # Read piped input for non-interactive use
    piped_input = _read_stdin_if_piped()

    # Single task mode (prompt given or input piped)
    if args.prompt or piped_input:
        if not args.json:
            print_banner()

        team = AIDevTeam(project_name=args.project, enable_memory=not args.no_memory)

        if not team.agents:
            print("No AI agents available. Please set API keys:")
            print("   export OPENAI_API_KEY=your_key")
            print("   export GOOGLE_API_KEY=your_key")
            print("   export XAI_API_KEY=your_key")
            sys.exit(1)

        # Build prompt with piped input
        prompt = args.prompt or ""
        if piped_input:
            if prompt:
                prompt = f"{prompt}\n\n```\n{piped_input}\n```"
            else:
                prompt = f"Analyze this:\n\n```\n{piped_input}\n```"

        # Auto-context: gather project info unless disabled
        context = "" if args.no_context else _gather_project_context(verbose=args.verbose)

        result = asyncio.run(run_single_task(team, prompt, args.mode, context=context))

        if args.json:
            output = {
                "success": result.success,
                "answer": result.final_answer,
                "confidence": result.confidence_score,
                "time": result.total_time,
                "agents": result.participating_agents,
            }
            print(json.dumps(output, indent=2))

        sys.exit(0 if result.success else 1)

    # Interactive mode (default)
    cli = AITeamCLI(project_name=args.project)
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
