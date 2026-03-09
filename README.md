<p align="center">
  <img src="assets/elgringo-logo.png" alt="El Gringo" width="200">
</p>

<h1 align="center">El Gringo</h1>

<p align="center">
  <a href="https://pypi.org/project/el-gringo/"><img src="https://img.shields.io/pypi/v/el-gringo.svg" alt="PyPI"></a>
  <a href="https://github.com/TheGringo-ai/ElGringo/actions/workflows/ci.yml"><img src="https://github.com/TheGringo-ai/ElGringo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
</p>

<p align="center"><strong>Autonomous AI development agent. Give it a task — it plans, builds, tests, and fixes.</strong></p>

---

## The Demo

```bash
$ elgringo build "a FastAPI REST API with JWT auth and user management"

============================================================
  EL GRINGO — AUTONOMOUS BUILD
============================================================

  a FastAPI REST API with JWT auth and user management

  Agents: chatgpt-coder, gemini-creative, grok-reasoner
  Planning...

  [1] Decomposing task into subtasks
  [2] Generating project structure
  [3] Creating database schema and models
  [4] Writing API routes and auth middleware
  [5] Generating test suite
  [6] Running tests
  [7] Fixing 2 failing tests
  [8] Re-running tests — all passing

────────────────────────────────────────────────────────────
  BUILD COMPLETE
────────────────────────────────────────────────────────────

  Time:       34.2s
  Confidence: 92%
  Subtasks:   8/8 completed
  Corrections: 1
```

One command. Multiple AI agents. Working code.

---

## Install

```bash
pip install el-gringo
```

Or from source:
```bash
git clone https://github.com/TheGringo-ai/ElGringo.git && cd ElGringo
pip install -e ".[all]"
```

## Configure

```bash
# Add at least one API key
export OPENAI_API_KEY=sk-...    # ChatGPT
export GEMINI_API_KEY=...       # Gemini
export XAI_API_KEY=xai-...      # Grok

# Or use local models (no API keys needed)
ollama pull llama3.2:3b
```

## Run

```bash
# Autonomous build
elgringo build "a CLI tool that converts CSV to JSON"

# Interactive mode (60+ commands)
elgringo

# Single task
elgringo "Review this code for security issues"

# MCP server (for Claude Code / Cursor)
python elgringo/server/mcp_server.py
```

---

## How It Works

```
Task: "Build a REST API with auth"
                |
        +-------+-------+
        |  Orchestrator  |  Routes to best agents, manages the loop
        +--+----+----+--+
           |    |    |
      +----+ +--+--+ +----+
      | GPT | |Gemini| |Grok |   3+ agents work in parallel
      +----+ +-----+ +----+
           |    |    |
        +--+----+----+--+
        |   Consensus    |  Weighted synthesis of responses
        +-------+-------+
                |
        +-------+-------+
        |  Self-Corrector |  Detects failures, retries with new strategy
        +-------+-------+
                |
        +-------+-------+
        |    Memory      |  Stores solutions, prevents repeat mistakes
        +---------------+
```

The orchestrator doesn't just call one model. It:

1. **Plans** — TaskPlanner decomposes goals into dependency-aware subtasks
2. **Routes** — TaskRouter picks the best agent for each subtask (based on past performance)
3. **Executes** — GraphExecutor runs subtasks in parallel batches
4. **Validates** — CodeExecutor sandboxes and tests generated code
5. **Corrects** — SelfCorrector retries failures with 7 adaptive strategies
6. **Learns** — SessionLearner records outcomes so the next build is smarter

---

## Key Features

### Autonomous Build Loop
Plan, generate, test, fix, improve — repeat until done. Not just code generation. Actual autonomous development with self-correction.

### Multi-Agent Collaboration
8 modes: parallel, sequential, consensus, debate, peer review, brainstorming, devil's advocate, expert panel. Responses are weighted by confidence, not concatenated.

### Smart Memory
Every interaction is captured, scored, and searchable. Tiered storage (hot/warm/cold). Mistake prevention injects past failures into prompts before they happen again. Memory consolidation auto-deduplicates and prunes.

### Code RAG
Hybrid TF-IDF + MLX vector embeddings. Indexes your codebase. Past solutions are automatically included in context. The agents understand your project, not just the current file.

### Sandboxed Execution
CodeExecutor with subprocess and Docker modes. Resource limits, security validation, AST-level blocking of dangerous operations. Agents can run code safely.

### Tool System
18 tools (filesystem, git, docker, deploy, database, browser, k8s, terraform, GCP). Full permission system with risk levels. JSON Schema for every tool, compatible with OpenAI and Anthropic function calling.

### Specialist Agents
SecurityAuditor (OWASP/CWE scanning), CodeReviewer (complexity analysis), SolutionArchitect (ADR generation, pattern detection).

### Apple Silicon Optimization
Smart routing between local MLX models and cloud APIs. GPU memory detection for optimal model selection.

### MCP Server (24 tools)
Works with Claude Code, Cursor, or any MCP client. Multi-agent collaboration, code review, security audit, memory search, PR review, personas, benchmarking, cost tracking — all as MCP tools.

<details>
<summary>Full MCP tools list</summary>

| Tool | What it does |
|------|-------------|
| `ai_team_collaborate` | Full multi-agent collaboration |
| `ai_team_ask` | Quick single-agent question |
| `ai_team_review` | Multi-agent code review |
| `ai_team_security_audit` | Security vulnerability scan |
| `ai_team_architect` | Architecture design |
| `ai_team_brainstorm` | Creative ideation |
| `ai_team_debug` | Multi-perspective debugging |
| `fredfix_scan` | Scan project for issues |
| `fredfix_auto_fix` | Auto-fix detected issues |
| `memory_search` | Search past interactions |
| `memory_store_mistake` | Record a mistake pattern |
| `memory_store_solution` | Record a solution pattern |
| `memory_curate` | Deduplicate and clean memory |
| `ai_team_teach` | Teach the team new knowledge |
| `ai_team_insights` | Get learning analytics |
| `ai_team_prompts` | Browse prompt templates |
| `ai_team_status` | Team health and stats |
| `ai_team_costs` | Cost reports (daily/weekly/monthly) |
| `ai_team_benchmark` | Compare agents, build routing table |
| `ai_team_routing_table` | Best agent per task type |
| `ai_team_rate` | Rate outcomes, triggers quality decay |
| `ai_team_quality_report` | Memory quality scores and stats |
| `ai_team_sessions` | Manage multi-turn sessions |
| `ai_team_review_pr` | Multi-agent GitHub PR review |
| `ai_team_create_persona` | Create custom agent personas |
| `load_project_context` | Load project files for context |
| `verify_code` | Syntax checks and build verification |

</details>

---

## Python API

```python
from elgringo.orchestrator import AIDevTeam

team = AIDevTeam(project_name="my-app", enable_memory=True)

# Multi-agent collaboration
result = await team.collaborate("Design a database schema for a blog")
print(result.final_answer)
print(result.confidence_score)  # 0.0-1.0
print(result.participating_agents)  # ['chatgpt-coder', 'grok-reasoner']

# Autonomous build (plan → execute → test → fix → learn)
result = await team.build("Create a FastAPI app with user auth")

# Different collaboration modes
result = await team.collaborate("Is this code secure?", mode="consensus")
result = await team.collaborate("How should we architect this?", mode="debate")
```

## REST API

```bash
# Start the API server
uvicorn products.fred_api.server:app --port 8080

# Collaborate
curl -X POST http://localhost:8080/v1/collaborate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Review this auth system", "mode": "parallel"}'

# Stream responses
curl -X POST http://localhost:8080/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain this code"}'
```

## MCP Integration

Add to your `.mcp.json`:
```json
{
  "mcpServers": {
    "el-gringo": {
      "command": "python3",
      "args": ["path/to/ElGringo/elgringo/server/mcp_server.py"],
      "env": {
        "PYTHONPATH": "path/to/ElGringo",
        "OPENAI_API_KEY": "sk-...",
        "XAI_API_KEY": "xai-..."
      }
    }
  }
}
```

---

## Project Structure

```
ElGringo/
  elgringo/
    agents/          # ChatGPT, Gemini, Grok, Claude, Ollama, LlamaCloud, Specialists
    autonomous/      # Self-correction, task decomposition, session learning
    cli/             # Interactive CLI (60+ commands)
    collaboration/   # Multi-agent engine, weighted consensus
    core/            # Shared config, security, sessions, personas
    framework/       # ReAct agents, task planner, chain-of-thought, tool registry
    knowledge/       # RAG system, auto-learner, teaching, domain knowledge
    memory/          # Tiered memory, learning engine, mistake prevention
    routing/         # Task classification, cost optimization, performance tracking
    sandbox/         # Isolated code execution (subprocess + Docker)
    server/          # MCP server (24 tools), REST API analytics
    tools/           # 18 tools — file, git, docker, deploy, database, browser, k8s
    ui/              # Gradio web UI, studio, chat, command center
    workflows/       # FredFix scanner, parallel coding, app generator
    orchestrator.py  # Core orchestration engine
  products/          # Standalone microservices (PR bot, code audit, test gen, docs)
  examples/          # Demo scripts and usage examples
  tests/             # 440+ tests
  main.py            # Single entry point
```

## Stats

- **69,000+** lines of Python across **149** modules
- **6** AI providers (ChatGPT, Gemini, Grok, Claude, Ollama, LlamaCloud)
- **8** collaboration modes
- **24** MCP tools
- **18** development tools
- **7** self-correction strategies
- **440+** tests passing

## What This Is NOT

- **Not a wrapper around one model** — orchestrates multiple models with routing, consensus, and memory
- **Not a chatbot** — agents execute tools, write code, run tests, deploy. Not just text generation
- **Not autonomous without consent** — tool calls require approval through the MCP client
- **Not a hosted service** — runs on your machine. Your code and API keys stay local

## Security

See [SECURITY.md](SECURITY.md) for the security model, tool permissions, and vulnerability reporting.

## License

Apache 2.0 - see [LICENSE](LICENSE)

Copyright 2024-2026 TheGringo AI
