# El Gringo — AI Development Platform

## What This Is
Multi-agent AI orchestration platform. 5 AI agents (ChatGPT, Gemini, Grok x2, Llama) working as a team.
Renamed from FredAI on 2026-03-06. Repo: `TheGringo-ai/ElGringo`.

## Architecture
- **Orchestrator**: `ai_dev_team/orchestrator.py` — AIDevTeam class coordinates agents
- **Agents**: `ai_dev_team/agents/` — ChatGPT, Gemini, Grok, Ollama, LlamaCloud
- **Tools**: `ai_dev_team/tools/` — filesystem, shell, git, browser, docker, deploy
- **API**: `products/fred_api/server.py` — FastAPI at port 8080, `/v1/*` endpoints
- **Coding Agent**: `products/fred_api/coding_endpoints.py` — `/v1/code/*` endpoints
- **MCP Server**: `mcp_server.py` — Claude Code integration (15 tools, FastMCP + HTTP client)

## Key Endpoints
| Endpoint | What |
|----------|------|
| `POST /v1/collaborate` | Multi-agent collaboration |
| `POST /v1/ask` | Single-agent Q&A |
| `POST /v1/code/task` | Autonomous coding (read → edit → test → commit) |
| `POST /v1/code/review` | Multi-agent code review |
| `POST /v1/code/plan` | Dry-run planning |
| `GET /v1/code/project-info` | Project structure |

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
