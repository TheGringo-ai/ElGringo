# El Gringo — AI Development Platform

## What This Is
Multi-agent AI orchestration platform. 6 AI agents (ChatGPT, Gemini, Grok x2, Qwen, Llama) working as a team.
Renamed from FredAI on 2026-03-06. Repo: `TheGringo-ai/ElGringo`.

## Architecture
- **Orchestrator**: `elgringo/orchestrator.py` — AIDevTeam class coordinates agents
- **Agents**: `elgringo/agents/` — ChatGPT, Gemini, Grok, Qwen (MLX), Ollama, LlamaCloud
- **Tools**: `elgringo/tools/` — filesystem, shell, git, browser, docker, deploy
- **API**: `products/fred_api/server.py` — FastAPI at port 8090, `/v1/*` endpoints
- **Coding Agent**: `products/fred_api/coding_endpoints.py` — `/v1/code/*` endpoints
- **MCP Server**: `mcp_server.py` — Claude Code integration (65 tools, FastMCP + HTTP/local hybrid)

## Key Endpoints (35 total)
| Endpoint | What |
|----------|------|
| `POST /v1/collaborate` | Multi-agent collaboration |
| `POST /v1/ask` | Single-agent Q&A |
| `POST /v1/stream` | SSE streaming from single agent |
| `POST /v1/code/task` | Autonomous coding (read → edit → test → commit) |
| `POST /v1/code/review` | Multi-agent code review |
| `POST /v1/code/plan` | Dry-run planning |
| `GET /v1/code/project-info` | Project structure |
| `POST /v1/memory/search` | Search past solutions/mistakes |
| `POST /v1/memory/store` | Store solution or mistake |
| `GET /v1/memory/stats` | Memory system statistics |
| `GET /v1/costs` | Cost tracking report |
| `POST /v1/verify` | Code validation (syntax + security) |
| `POST /v1/teach` | Teach AI team new knowledge |
| `GET /v1/agents` | List available agents |
| `GET /v1/health` | Health check |
| `GET /v1/arbitrage` | Cost savings report + provider comparison |
| `POST /v1/scan` | Scan AI output for failures/hallucinations |
| `POST /v1/transparency` | Reasoning transparency report |
| `GET /v1/agent-insights` | Deep agent profiles from feedback |
| `GET /v1/nexus` | Cross-project intelligence stats |
| `POST /v1/nexus/search` | Search solutions across all projects |
| `POST /v1/code/restore` | Restore files to pre-task state |

## Qwen (Local Specialist)
- **qwen-coder**: Qwen 2.5 Coder 7B via MLX — coding tasks, zero cost
- **qwen-general**: Qwen 2.5 3B via MLX — general tasks, zero cost
- Both models run on Apple Silicon Metal, ~6GB total, stay loaded in memory

## Deploy
```bash
VM_NAME=managers-dashboard VM_ZONE=us-central1-a ./deploy-vm.sh
```

## Important
- Python import paths still use `fred_*` directory names (not renamed on disk inside the package)
- VM path is `/opt/elgringo/` (after deploy) but old deploys may still have `/opt/fredai/`
- Env vars: `ELGRINGO_API_TOKEN`, `FRED_API_KEYS` (Fred API keys not renamed yet on VM)
- Domain: `ai.chatterfix.com` (unchanged)

## DO NOT
- Break the `/v1/collaborate` or `/v1/code/*` endpoints — Claude Code depends on them via MCP
- Change the MCP tool function signatures without updating `mcp_server.py`
- Remove any agent from the orchestrator without testing all collaboration modes
