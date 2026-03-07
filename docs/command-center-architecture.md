# El Gringo Command Center -- Architecture Decision

**Date:** 2026-02-22
**Author:** Claude (Lead Architect, El Gringo Team)
**Status:** Approved

---

## 1. Recommended Architecture: Option A -- Streamlit Frontend + FastAPI Backend

### The Decision

Option A. Keep the Streamlit frontend and add a thin FastAPI backend behind it.

### Why This Wins

1. **You already have a working Streamlit prototype with real features.** The command_center.py
   at 387 lines has a sprint board, content queue, AI chat, automation sidebar, and standup
   viewer. That is not throwaway code -- it is the product. Rewriting it in React means
   rebuilding every widget, every state interaction, and every async bridge from scratch.
   Weeks of work for zero new functionality.

2. **Every other El Gringo UI is already Streamlit/Gradio.** Chat UI and Studio are Gradio.
   The command center is Streamlit. There is no React anywhere in this repo. Adding React
   means adding node, npm, Vite, a build pipeline, a node_modules directory, CORS debugging,
   and a second language to maintain. For a solo founder, that is not "modern" -- it is
   overhead.

3. **The real gap is not the frontend -- it is the API boundary.** The current prototype
   imports Python classes directly and wraps async calls in thread pools. That works locally
   but breaks when you need the command center on the VM to talk to the same data as the
   CLI, the Chat UI, or external tools. The fix is a FastAPI backend that the Streamlit
   frontend calls via HTTP. That backend also serves the CLI, webhooks, and future mobile
   clients.

4. **Streamlit ships fast for dashboards.** Kanban boards, metrics strips, chat interfaces,
   sidebar navigation -- all of this is 5-10 lines in Streamlit versus 50-100 in React.
   For an internal command center (not a customer-facing SaaS UI), Streamlit is the right
   tool.

5. **The existing deploy pipeline already handles it.** ci-deploy-elgringo.sh already has a
   `elgringo-command-center` systemd service. deploy-vm.sh already packages everything as a
   tar. Adding React would mean adding a build step, a static file serve config, and
   probably a separate Docker stage.

### What I Reject

**Option B (React + Vite + FastAPI):** React is the right choice for customer-facing products
like the Managers Dashboard. It is the wrong choice for an internal dev command center built
by one person. The cognitive switching cost between Python-everywhere and Python+JS+JSX is
real. You would spend more time fighting Vite proxy configs and CORS than building features.

**Option C (Next.js + FastAPI):** Everything from Option B plus SSR complexity, Vercel
assumptions, and two separate server processes (Next.js + FastAPI) where one suffices. Next.js
is for SEO-driven marketing sites and large team apps. This is neither.

### Trade-offs I Accept

- Streamlit's component model limits custom interactions (no drag-and-drop Kanban, no
  real-time WebSocket push). This is acceptable because the current selectbox-based task
  movement works and the command center is used by one person.
- Streamlit re-renders the full page on interaction. For a dashboard with <100 items, this
  is imperceptible. If it ever matters, the FastAPI backend enables swapping the frontend
  later without touching any backend code.
- No offline/PWA support. Not needed for a dev command center.

---

## 2. Repo Structure

The command center lives inside `products/` alongside el_gringo_api, code_audit, etc. The existing
`ai_dev_team/command_center.py` prototype stays as-is during migration (delete it after the
new one is verified). The backend is a FastAPI app. The frontend is the Streamlit app that
calls the backend over HTTP.

```
El Gringo/
  products/
    command_center/
      __init__.py              # Product registration
      config.py                # ProductConfig instance (port 7863)
      server.py                # FastAPI backend (port 7862)
      ui.py                    # Streamlit frontend (port 7863)
      routers/
        __init__.py
        sprints.py             # Sprint CRUD + Kanban endpoints
        content.py             # Content queue + generation endpoints
        chat.py                # AI chat endpoint (SSE streaming)
        automation.py          # Scheduler status + standup endpoints
        health.py              # Health check
      models.py                # Pydantic request/response models
      services.py              # Thin wrappers around ai_dev_team modules
```

### What Each File Does

| File | Purpose | Lines (est.) |
|------|---------|-------------|
| `config.py` | `PRODUCT_CONFIG = ProductConfig(name="command_center", port=7863, ...)` | 15 |
| `server.py` | FastAPI app, mounts routers, CORS, auth middleware | 60 |
| `ui.py` | Streamlit frontend, calls backend via `requests`/`httpx` | 400 |
| `routers/sprints.py` | `GET/POST/PATCH` for tasks, sprints, board state | 120 |
| `routers/content.py` | `GET/POST` for content items, generation trigger | 100 |
| `routers/chat.py` | `POST /chat` with SSE streaming via AIDevTeam.ask() | 80 |
| `routers/automation.py` | `GET` scheduler tasks, standup history | 60 |
| `routers/health.py` | `GET /health` | 15 |
| `models.py` | All Pydantic models for request/response | 100 |
| `services.py` | Singletons for SprintManager, ContentGenerator, etc. | 80 |

**Total new code: ~1,030 lines.** Most of ui.py is migrated from the existing 387-line
prototype with `st.cache_resource` calls replaced by HTTP calls to the backend.

---

## 3. Local Dev Workflow

### Port Assignments

| Service | Port | Role |
|---------|------|------|
| Command Center API (FastAPI) | 7862 | Backend |
| Command Center UI (Streamlit) | 7863 | Frontend (unchanged) |
| Chat UI (Gradio) | 7860 | Existing |
| Studio (Gradio) | 7861 | Existing |
| Fred API | 8080 | Existing |
| Code Audit | 8081 | Existing |
| Test Gen | 8082 | Existing |
| Doc Gen | 8083 | Existing |

Port 7862 is new. Every other port stays the same.

### Start Everything with 1 Command

The existing `local-start.sh` already starts the command center. Add the backend service
to it. Updated line additions for `local-start.sh`:

```bash
# Add BEFORE the existing command center line:
start_service "command-api" 7862 "uvicorn products.command_center.server:app --host 127.0.0.1 --port 7862 --reload --log-level info"

# The existing command center line stays:
start_service "command"     7863 "python -m streamlit run products/command_center/ui.py --server.port 7863 --server.headless true"
```

Single command:
```bash
./local-start.sh
```

### Dev Mode (single service, hot reload)

For iterating on just the command center:

```bash
# Terminal 1: Backend with auto-reload
cd /Users/fredtaylor/Development/Projects/El Gringo
PYTHONPATH=. uvicorn products.command_center.server:app --host 127.0.0.1 --port 7862 --reload

# Terminal 2: Frontend with auto-reload (Streamlit does this by default)
cd /Users/fredtaylor/Development/Projects/El Gringo
PYTHONPATH=. COMMAND_CENTER_API=http://127.0.0.1:7862 streamlit run products/command_center/ui.py --server.port 7863
```

Streamlit auto-reloads on file save. Uvicorn `--reload` watches for Python file changes.
No build step. No npm. No node_modules.

---

## 4. Deployment Plan

### Systemd (not Docker)

Docker adds nothing here. Every other El Gringo service runs as a systemd unit on the VM.
The command center does the same. Consistency over novelty.

### Two New Systemd Units

The existing `elgringo-command-center` unit gets replaced with two units:

**elgringo-command-api.service** (the backend):
```ini
[Unit]
Description=El Gringo Command Center API (FastAPI)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=7862
EnvironmentFile=/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/uvicorn products.command_center.server:app --host 127.0.0.1 --port 7862 --log-level info
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/command-api.log
StandardError=append:/opt/elgringo/logs/command-api-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**elgringo-command-center.service** (the frontend -- update existing):
```ini
[Unit]
Description=El Gringo Command Center UI (Streamlit)
After=network.target elgringo-command-api.service
Wants=network-online.target elgringo-command-api.service

[Service]
Type=simple
User=elgringo
Group=elgringo
WorkingDirectory=/opt/elgringo
Environment=PATH=/opt/elgringo/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/elgringo
Environment=PORT=7863
Environment=COMMAND_CENTER_API=http://127.0.0.1:7862
EnvironmentFile=/opt/elgringo/.env
ExecStart=/opt/elgringo/venv/bin/python -m streamlit run products/command_center/ui.py --server.port 7863 --server.headless true --server.baseUrlPath /command
Restart=always
RestartSec=5
StandardOutput=append:/opt/elgringo/logs/command-center.log
StandardError=append:/opt/elgringo/logs/command-center-error.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### ci-deploy-elgringo.sh Changes

Add the `elgringo-command-api` service definition and update the existing command center
definition. Add it to the `systemctl enable` and `systemctl restart` lines. Add a health
check line at the end. Specific diff:

```diff
  # In the systemctl enable line, add elgringo-command-api:
- systemctl enable elgringo-api elgringo-pr-bot ... elgringo-command-center
+ systemctl enable elgringo-api elgringo-pr-bot ... elgringo-command-api elgringo-command-center

  # In the restart block, add:
+ systemctl restart elgringo-command-api

  # In the verify block, add:
+ systemctl is-active elgringo-command-api && echo "  elgringo-cmd-api:   RUNNING (port 7862)" || echo "  elgringo-cmd-api:   FAILED"
```

### Nginx Config for /command/ Route

Add to the existing nginx server block on the VM:

```nginx
# Command Center UI (Streamlit on port 7863)
location /command/ {
    proxy_pass http://127.0.0.1:7863/command/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}

# Command Center API (FastAPI on port 7862)
location /command/api/ {
    proxy_pass http://127.0.0.1:7862/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Streamlit WebSocket (required for Streamlit's live updates)
location /command/_stcore/stream {
    proxy_pass http://127.0.0.1:7863/command/_stcore/stream;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
```

**Public URL:** `https://ai.chatterfix.com/command/`

---

## 5. Auth Approach

### Now: Single-User, Local-Only

The command center backend binds to `127.0.0.1` (not `0.0.0.0`). Nginx handles external
access. Streamlit has built-in password protection for single-user:

```python
# In ui.py, at the top:
import os
if os.getenv("COMMAND_CENTER_PASSWORD"):
    # Streamlit's native auth
    if "authenticated" not in st.session_state:
        password = st.text_input("Password", type="password")
        if password == os.getenv("COMMAND_CENTER_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.stop()
```

For the FastAPI backend, reuse the same Bearer token pattern from el_gringo_api:

```python
# In server.py:
COMMAND_API_KEYS = set()
_raw = os.getenv("COMMAND_CENTER_API_KEYS", os.getenv("ELGRINGO_API_TOKEN", ""))
if _raw:
    COMMAND_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}
```

On the VM, the Streamlit UI calls the backend on localhost. No auth needed for that
localhost path. The nginx reverse proxy protects external access. The existing Gradio
username/password pattern (set in .env) works here too.

### Later: Multi-User

Design the FastAPI backend with a `current_user` dependency from the start, but hardcode
it to a single user initially:

```python
# In server.py:
async def get_current_user(request: Request) -> dict:
    """Returns current user. Hardcoded now, swap to JWT/Firebase later."""
    return {"uid": "fred", "name": "Fred Taylor", "role": "admin"}
```

When multi-user is needed:
1. Swap `get_current_user` to validate a JWT (Firebase Auth, same as Managers Dashboard).
2. Add a `user_id` field to SprintManager tasks and ContentGenerator items.
3. Filter queries by user. The FastAPI routers already receive `current_user` as a
   dependency -- no endpoint changes needed.

Do not build this until there is a second user.

---

## 6. How It Connects to Existing El Gringo Modules

### Direct Python Imports (Backend Only)

The FastAPI backend imports El Gringo modules directly. It runs in the same Python process
with the same `PYTHONPATH=/opt/elgringo`. This is exactly how el_gringo_api/server.py and
code_audit/server.py work today.

```python
# products/command_center/services.py

from ai_dev_team.orchestrator import AIDevTeam
from ai_dev_team.workflow.sprint_manager import SprintManager
from ai_dev_team.workflow.content_generator import ContentGenerator, ContentQueue
from ai_dev_team.workflow.scheduler import TaskScheduler
from ai_dev_team.workflow.standup import StandupGenerator
from ai_dev_team.workflow.personas import PersonaLibrary

# Singletons (same pattern as el_gringo_api/server.py lines 111-120)
_sprint_manager = None
_content_generator = None
_content_queue = None
_scheduler = None
_standup_generator = None
_ai_team = None
_persona_library = None

def get_sprint_manager() -> SprintManager:
    global _sprint_manager
    if _sprint_manager is None:
        _sprint_manager = SprintManager()
    return _sprint_manager

def get_ai_team() -> AIDevTeam:
    global _ai_team
    if _ai_team is None:
        _ai_team = AIDevTeam(project_name="command-center", enable_memory=True)
    return _ai_team

# ... same pattern for all others
```

### Handling Async (AIDevTeam.ask() is async)

FastAPI natively supports `async def` endpoints. No thread pool hacks needed (unlike the
current Streamlit prototype which uses `concurrent.futures.ThreadPoolExecutor`).

```python
# routers/chat.py
@router.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    team = get_ai_team()
    persona = get_persona_library().get_system_prompt("dev_lead") or ""
    response = await team.ask(req.message, context=persona)  # Native async
    return {"role": "assistant", "content": response.content}
```

For SSE streaming (real-time chat responses):

```python
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    team = get_ai_team()

    async def event_generator():
        # If agent supports streaming:
        agent = next(iter(team.agents.values()))
        async for token in agent.generate_stream(req.message):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Where the API Boundary Lives

```
+------------------+          HTTP           +-------------------+
|                  |  localhost:7862/api/*    |                   |
|  Streamlit UI    | ----------------------> |  FastAPI Backend   |
|  (port 7863)     |                         |  (port 7862)      |
|                  |  JSON responses         |                   |
|  NO direct       | <---------------------- |  Direct Python    |
|  Python imports  |                         |  imports of:      |
|  of ai_dev_team  |                         |  - SprintManager  |
+------------------+                         |  - ContentGen     |
                                             |  - AIDevTeam      |
                                             |  - TaskScheduler  |
                                             |  - StandupGen     |
                                             |  - PersonaLibrary |
                                             +-------------------+
```

**Rule:** The Streamlit UI NEVER imports from `ai_dev_team`. It only calls the FastAPI
backend. The FastAPI backend is the sole consumer of `ai_dev_team` modules for the
command center.

This means:
- The Streamlit UI can be replaced with React later without touching the backend.
- The backend API can be called by the CLI, webhooks, or mobile apps.
- The `ai_dev_team` module surface area is encapsulated behind HTTP.

### API Endpoints (Complete List)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health |
| `GET` | `/sprints` | List all sprints |
| `GET` | `/sprints/current` | Get active sprint |
| `POST` | `/sprints` | Create sprint |
| `GET` | `/sprints/{id}/tasks` | Tasks for sprint |
| `GET` | `/tasks` | All tasks (filterable by status) |
| `POST` | `/tasks` | Create task |
| `PATCH` | `/tasks/{id}` | Update task (status, assignee, etc.) |
| `GET` | `/tasks/stats` | Summary stats |
| `GET` | `/tasks/velocity` | Velocity trend |
| `GET` | `/content` | List content items (filterable by status) |
| `POST` | `/content/generate` | Generate content (type + topic) |
| `PATCH` | `/content/{id}` | Update content status (approve/reject) |
| `POST` | `/chat` | AI chat (returns full response) |
| `POST` | `/chat/stream` | AI chat (SSE streaming) |
| `GET` | `/automation/jobs` | Scheduler task list |
| `GET` | `/automation/standups` | Recent standups |

---

## 7. Migration Plan (Execution Order)

### Step 1: Create the FastAPI backend (Day 1)

Build `products/command_center/` with all routers. Test every endpoint with `curl`
or the auto-generated `/docs` page. The existing `ai_dev_team/command_center.py`
continues running untouched.

### Step 2: Rewrite the Streamlit UI to call the backend (Day 2)

Copy `ai_dev_team/command_center.py` to `products/command_center/ui.py`. Replace every
`get_sprint_manager()` call with `requests.get("http://localhost:7862/sprints")`. Remove
all `@st.cache_resource` singletons and the `run_async()` bridge. The UI becomes a pure
HTTP client.

### Step 3: Update local-start.sh and ci-deploy-elgringo.sh (Day 2)

Add the `command-api` service. Update the `command` service path from
`ai_dev_team/command_center.py` to `products/command_center/ui.py`.

### Step 4: Update nginx on the VM (Day 3)

Add the `/command/` location block. Deploy with `./deploy-vm.sh`. Verify at
`https://ai.chatterfix.com/command/`.

### Step 5: Delete the old prototype (Day 3)

Remove `ai_dev_team/command_center.py` after confirming the new one works.

---

## 8. What NOT to Build

- **No database.** SprintManager and ContentGenerator already persist to JSON files in
  `~/.ai-dev-team/workflow/`. The FastAPI backend reads/writes through those same classes.
  Add a database when the JSON files become a bottleneck (they will not for a solo user
  with <200 tasks).

- **No WebSocket real-time updates.** Streamlit handles its own reactivity. The
  `st.rerun()` pattern works. Add WebSockets only if a second client (mobile, CLI)
  needs push notifications.

- **No Docker.** Systemd is simpler, already works, and has zero overhead. Docker
  adds image builds, registry pushes, and container orchestration that solve problems
  you do not have.

- **No separate auth service.** A `get_current_user` dependency with a hardcoded return
  value is correct for one user. JWT validation is a 20-line change when needed.

- **No GraphQL.** REST with 18 endpoints is simple and debuggable. GraphQL adds schema
  management, resolver complexity, and tooling overhead for zero benefit at this scale.

---

## 9. Summary

| Decision | Choice |
|----------|--------|
| Frontend | Streamlit (existing, extended) |
| Backend | FastAPI (new, 7 routers) |
| State | JSON files via existing managers |
| Auth | Bearer token (backend), password (UI) |
| Deploy | Systemd (2 units: API + UI) |
| Proxy | Nginx `/command/` and `/command/api/` |
| Port | 7862 (API), 7863 (UI) |
| Module access | Direct Python imports in backend only |
| Async | Native FastAPI async (no thread hacks) |

The fastest path from prototype to product is not rewriting in React. It is extracting
the backend into a proper API and letting the Streamlit frontend be a thin HTTP client.
This gives you a clean API boundary, native async, and the ability to swap frontends
later -- all without leaving Python.
