# El Gringo — AI Development Platform

## What This Is
Multi-agent AI orchestration platform. 6 AI agents (ChatGPT, Gemini, Grok x2, Qwen, Llama) working as a team.
Renamed from FredAI on 2026-03-06. Repo: `TheGringo-ai/ElGringo`.

## Architecture
- **Orchestrator**: `elgringo/orchestrator.py` — AIDevTeam class coordinates agents
  - `orchestrator_agents.py` — Agent setup/registration (cloud, Ollama, MLX)
  - `orchestrator_context.py` — Pre-collaboration context enrichment (memory, RAG, domain knowledge)
  - `orchestrator_intelligence.py` — Post-collaboration processing (costs, quality, learning, caching)
- **Agents**: `elgringo/agents/` — ChatGPT, Gemini, Grok, Qwen (MLX), Ollama, LlamaCloud
- **Tools**: `elgringo/tools/` — filesystem, shell, git, browser, docker, deploy
- **API**: `products/fred_api/server.py` — FastAPI at port 8090, `/v1/*` endpoints
- **Coding Agent**: `products/fred_api/coding_endpoints.py` — `/v1/code/*` endpoints
- **MCP Server**: `mcp_server.py` — Claude Code integration (73 tools, FastMCP + HTTP/local hybrid)
- **Tool Factory**: `elgringo/core/tool_factory.py` — Dynamic tool creation at runtime

## Key Endpoints (36 total)
| Endpoint | What |
|----------|------|
| `POST /v1/collaborate` | Multi-agent collaboration (modes: auto, quick, team, deep) |
| `POST /v1/ask` | Single-agent Q&A |
| `POST /v1/stream` | SSE streaming from single agent |
| `POST /v1/collaborate/stream` | SSE streaming multi-agent collaboration |
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
| `GET /dashboard` | Web UI dashboard |

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

## Coding Agent Safety Features
- **Post-write syntax validation**: Python files are `py_compile`-checked immediately after writing. Syntax errors trigger a self-correction retry.
- **Execution context detection**: Reads systemd/Dockerfile/Makefile to detect the working directory. Warns about import path mismatches (e.g., app runs from `backend/` but imports say `from backend.module`).
- **Silent exception detection**: Scans written code for `except Exception: pass` and similar patterns. Also runs during `/v1/code/review`.
- **Defensive coding prompt**: AI agents are instructed to check fields/columns exist before use and use fallback imports for subdirectory execution.

## Simplified Collaboration Modes (user-facing)
| Mode | What It Does |
|------|-------------|
| `auto` | Smart routing — picks the best mode based on task complexity |
| `quick` | Single best agent, zero overhead (maps to turbo) |
| `team` | Full team collaboration with critique round (maps to parallel) |
| `deep` | Structured 4-phase debate for complex decisions (maps to debate) |

Advanced modes (auto-selected by router or manually specified):
- `turbo` — single agent | `parallel` — agents + critique | `sequential` — chain of findings
- `brainstorming` — creative ideation | `debate` — structured positions | `devils_advocate` — adversarial
- `peer_review` — formal review | `consensus` — agreement-seeking | `expert_panel` — domain experts

## Smart Router (replaces teams)
The router automatically handles what manual "teams" used to do:
- **Dynamic persona injection**: Generates task-specific system prompts (security audit → "Think like a pen tester", architecture → "Challenge assumptions, consider failure modes")
- **Cost-aware routing**: Low complexity → free agents (Qwen) first. Medium+ → cloud agents. Tracked via `cost_tier` field.
- **Feedback-informed weights**: Uses `expertise_adjustments` from the feedback loop to bias agent selection based on proven outcomes
- **Confidence-based escalation**: If turbo response confidence < 60%, auto-escalates to parallel with more agents

## Dynamic Tool Factory
Create new MCP tools at runtime via `ai_tool_create()`. Tools are sandboxed prompt templates that call the collaborate API. Persisted to `~/.ai-dev-team/custom_tools/`.

## Dashboard
Open `http://localhost:8090/dashboard` for a live web UI showing agents, costs, quality scores, ROI, and feedback history. Auto-refreshes every 10 seconds. Single HTML file at `products/fred_api/dashboard.html`.

## Testing
- **513 tests** across 16 test files, 0 failures
- Run: `python3 -m pytest tests/ -q`
- Key test files: `test_intelligence.py` (51 tests), `test_core_systems.py` (36 tests), `test_orchestrator.py` (43 tests)
- Stress test: `python3 tests/stress_test.py --url http://127.0.0.1:8090`

## DO NOT
- Break the `/v1/collaborate` or `/v1/code/*` endpoints — Claude Code depends on them via MCP
- Change the MCP tool function signatures without updating `mcp_server.py`
- Remove any agent from the orchestrator without testing all collaboration modes
