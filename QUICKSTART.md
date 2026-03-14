# El Gringo Quick-Start Guide

## What is El Gringo?

El Gringo is a multi-agent AI orchestration platform that coordinates 6 AI agents (ChatGPT, Gemini, Grok x2, Qwen, Llama) as a unified team. A smart router automatically picks the best collaboration mode for each task -- single agent for simple questions, full team debate for architecture decisions, sequential handoff for debugging -- so you just describe what you need and the platform handles the rest.

---

## Quick Start (30 seconds)

**1. Set API keys** in a `.env` file at the project root:
```bash
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
XAI_API_KEY=xai-...
```

**2. Start the server:**
```bash
python3 -m uvicorn products.fred_api.server:app --port 8090
```

**3. Open the dashboard:** [http://localhost:8090/dashboard](http://localhost:8090/dashboard)

**4. Try your first request:**
```bash
curl -s http://localhost:8090/v1/health | python3 -m json.tool
```

---

## API Keys Needed

| Provider | Env Var | Get it at |
|----------|---------|-----------|
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| Google | `GOOGLE_API_KEY` | [ai.google.dev](https://ai.google.dev) |
| xAI (Grok) | `XAI_API_KEY` | [console.x.ai](https://console.x.ai) |
| Qwen (local) | _No key needed_ | Runs on Apple Silicon via MLX, zero cost |

You only need the keys for providers you want to use. The platform works with any subset of agents.

---

## Your First Request

```bash
curl -X POST http://localhost:8090/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Python function that checks if a number is prime"}'
```

The router picks the best available agent automatically. Response includes the agent used, the answer, and token/cost info.

---

## Collaboration Modes

| Mode | When to Use | Example |
|------|-------------|---------|
| `auto` (default) | Let El Gringo pick the best mode | Any request without a mode specified |
| `turbo` | Simple tasks, single best agent, zero overhead | Quick questions, one-liners |
| `parallel` | Medium tasks, agents answer then critique each other | Code generation with review |
| `sequential` | Debugging/security, each agent builds on previous | Root cause analysis |
| `brainstorming` | Creative tasks, diverse ideas with cross-pollination | Feature ideation |
| `debate` | Architecture decisions, 4-phase structured debate | System design |
| `devils_advocate` | Security review, adversarial challenge of proposals | Threat modeling |
| `peer_review` | Quality assurance, agents formally review each other | Code review |

---

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/ask` | Single-agent Q&A (smart-routed) |
| `POST` | `/v1/collaborate` | Full team collaboration |
| `POST` | `/v1/code/task` | Autonomous coding (read, edit, test, commit) |
| `POST` | `/v1/code/review` | Multi-agent code review |
| `POST` | `/v1/code/plan` | Dry-run planning (no changes made) |
| `GET` | `/v1/costs` | Cost tracking report |
| `GET` | `/v1/agents` | List available agents |
| `GET` | `/v1/health` | Health check |
| `GET` | `/v1/teams` | List teams and templates |
| `GET` | `/dashboard` | Web UI |

### Curl Examples

**Ask a single agent:**
```bash
curl -X POST http://localhost:8090/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain Python decorators in 3 sentences"}'
```

**Team collaboration:**
```bash
curl -X POST http://localhost:8090/v1/collaborate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Design a rate limiter for a REST API", "mode": "debate"}'
```

**Autonomous coding task:**
```bash
curl -X POST http://localhost:8090/v1/code/task \
  -H "Content-Type: application/json" \
  -d '{"task": "Add input validation to the user signup endpoint", "project_path": "/path/to/project"}'
```

**Code review:**
```bash
curl -X POST http://localhost:8090/v1/code/review \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project", "files": ["src/auth.py"]}'
```

**Check costs:**
```bash
curl -s http://localhost:8090/v1/costs | python3 -m json.tool
```

---

## MCP Integration (Claude Code)

Add this to `~/.claude/mcp.json` so Claude Code can call El Gringo's tools directly:

```json
{
  "mcpServers": {
    "ai-team": {
      "command": "/path/to/ElGringo/start_mcp.sh",
      "args": []
    }
  }
}
```

Once configured, Claude Code gains access to El Gringo's full toolset (73 tools) -- collaborate with the AI team, run code tasks, search memory, and more, all from within Claude Code conversations.

---

## Example Workflows

### 1. Review My Code

```bash
curl -X POST http://localhost:8090/v1/code/review \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/Users/you/myproject",
    "files": ["src/api/handlers.py", "src/models/user.py"]
  }'
```
Multiple agents review the files in parallel, checking for bugs, security issues, and performance problems.

### 2. Debug This Error

```bash
curl -X POST http://localhost:8090/v1/collaborate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Getting ConnectionResetError on Redis after 30min idle. Using redis-py 5.0 with connection pooling. Stack trace: ...",
    "mode": "sequential"
  }'
```
Sequential mode passes the problem through each agent in order -- each one builds on the previous findings for deeper root cause analysis.

### 3. Design System Architecture

```bash
curl -X POST http://localhost:8090/v1/collaborate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Design a notification system that handles email, SMS, and push notifications with retry logic and user preferences. Expected scale: 10M notifications/day.",
    "mode": "debate"
  }'
```
Debate mode runs a 4-phase structured discussion: agents take assigned positions, challenge each other, and converge on a well-tested architecture.

---

## Dashboard

Open [http://localhost:8090/dashboard](http://localhost:8090/dashboard) for a live view of agents, costs, quality scores, and collaboration history.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No agents available" | Check that at least one API key is set in `.env` |
| "Connection refused" | Start the server: `python3 -m uvicorn products.fred_api.server:app --port 8090` |
| Qwen not loading | Requires an Apple Silicon Mac (M1/M2/M3/M4) with MLX installed |
| Slow first request | Models are loading on first call. Subsequent requests are faster |
| API docs | Visit [http://localhost:8090/v1/docs](http://localhost:8090/v1/docs) for interactive Swagger UI |
