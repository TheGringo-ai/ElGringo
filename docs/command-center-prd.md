# FredAI Command Center v2 -- Product Requirements Document

**Author:** FredAI Team
**Date:** 2026-02-22
**Status:** Ready for implementation

---

## Deliverable 1: PRD

### Problem

The existing Streamlit command center (`ai_dev_team/command_center.py`) works but has these concrete problems:

1. **No task creation inline** -- you can move tasks between columns but cannot create new ones without editing JSON
2. **Content generation blocks the entire UI** -- Streamlit reruns on every action; generating a LinkedIn post freezes the page for 30+ seconds
3. **No sprint CRUD** -- cannot create/close sprints from the UI
4. **Scheduler is display-only** -- cannot add/remove/toggle scheduled jobs
5. **No standup history navigation** -- sidebar shows last 5 days but no detail view
6. **No velocity/trend visualization** -- data exists in `get_velocity_trend()` but is never rendered
7. **Chat context is lost on page refresh** -- `st.session_state` is ephemeral

### Architecture Decision

Replace Streamlit with **FastAPI backend + React (Vite + Tailwind) frontend**. Same pattern as the Managers Dashboard. Single `docker compose up` or `make dev` to run locally.

**Why not keep Streamlit:** Streamlit cannot do background jobs, websocket chat streaming, or component-level loading states. Every button click triggers a full page rerun.

### Features (MVP)

| # | Feature | Backend module | Notes |
|---|---------|---------------|-------|
| F1 | Sprint board with drag-drop columns | `SprintManager` | Backlog / In Progress / Review / Done |
| F2 | Task CRUD (create, edit, delete, move) | `SprintManager.create_task`, `update_task_status` | Inline form, not a modal |
| F3 | Sprint CRUD (create, close, view history) | `SprintManager.create_sprint`, sprints list | |
| F4 | Content queue with approve/reject | `ContentQueue`, content JSON files | |
| F5 | Content generation (async, non-blocking) | `ContentGenerator.generate_*` | Background job, poll for result |
| F6 | AI chat with streaming | `AIDevTeam.ask()` via SSE | Persona selector from `PersonaLibrary` |
| F7 | Scheduler dashboard (list, add, remove, toggle) | `TaskScheduler` CRUD | |
| F8 | Daily standup viewer | `StandupGenerator.get_standup_history` | |
| F9 | Metrics strip (sprint completion, velocity, counts) | `SprintManager.get_summary_stats`, `get_velocity_trend` | |
| F10 | Generate standup on demand | `StandupGenerator.generate_standup` | |

### Non-goals (NOT in MVP)

- Multi-user / auth (single founder use)
- Real-time collaboration / websockets for board sync
- Drag-and-drop (use click-to-move; drag-drop is a v2 polish item)
- Email/Slack notifications
- Deployment pipeline integration
- Mobile-specific layout
- Content publishing to LinkedIn/blog (generate only, copy-paste to publish)
- Goal tracking (`progress_api.py` Goal CRUD -- defer to v2)

### User Stories

**US-1: Morning check-in**
As a founder, I want to open the Command Center and immediately see sprint completion percentage, active task count, content drafts pending review, and scheduled job count so that I know the state of everything in under 5 seconds.
**Acceptance criteria:**
- Page loads in < 2s with cached data
- Metrics strip shows: sprint completion %, tasks active/total, content drafts count, scheduler jobs count, days remaining in sprint
- Data refreshes on page load and on manual refresh button

**US-2: Plan my day**
As a founder, I want to ask the AI "What should I work on today?" and get an answer that references my actual backlog and in-progress tasks so that I get actionable priorities.
**Acceptance criteria:**
- Chat panel has quick-prompt buttons ("What should I work on today?", "Summarize this week", "Generate content idea")
- Response includes actual task titles from SprintManager
- Chat history persists across page navigations (stored in localStorage)
- Response streams token-by-token via SSE

**US-3: Manage sprint tasks**
As a founder, I want to create a task, assign it to the current sprint, move it through columns, and mark it done -- all from one screen.
**Acceptance criteria:**
- "Add task" form at top of Backlog column: title (required), description, priority (1-5), estimate_hours, project, assignee
- Each task card shows: title, priority badge, estimate, assignee
- Each card has a "Move to" dropdown with status options
- Clicking a card expands inline detail (description, timestamps, ID)

**US-4: Create and manage sprints**
As a founder, I want to create a new sprint with a name and goals, view the current sprint, and close completed sprints.
**Acceptance criteria:**
- Sprint header shows current sprint name, goals, date range, completion %
- "New Sprint" button opens inline form: name, goals (comma-separated), start_date, end_date
- "Close Sprint" button sets sprint status to "completed"

**US-5: Generate and review content**
As a founder, I want to generate a LinkedIn post by entering a topic and tone, review the generated content, and approve or reject it.
**Acceptance criteria:**
- Content panel has type selector (linkedin_post, blog_post, newsletter, release_notes)
- Generation runs in background; panel shows spinner with "Generating..." then renders result
- Each content item shows: title/subject, body preview (first 300 chars), hashtags, CTA, status badge
- Approve/Reject buttons update both the content JSON file and the ContentQueue

**US-6: View and manage scheduled automations**
As a founder, I want to see all scheduled tasks, their cron expressions, next/last run times, and toggle them on/off.
**Acceptance criteria:**
- Scheduler panel lists all tasks from `TaskScheduler.list_tasks()`
- Each row: name, cron expression (human-readable label), type, enabled toggle, next_run, last_run
- "Add Schedule" form: name, cron_expression, task_type (dropdown of TASK_TYPES), config JSON
- Delete button per task

**US-7: View standup history**
As a founder, I want to see today's standup and browse previous days so that I can track daily progress over time.
**Acceptance criteria:**
- Standup panel shows today's standup formatted via `StandupGenerator.format_standup()`
- Date picker or prev/next arrows to navigate history
- "Generate Now" button triggers `generate_standup()` and saves

**US-8: See velocity trends**
As a founder, I want to see a chart of sprint velocity over the last 4 sprints so that I know if I'm speeding up or slowing down.
**Acceptance criteria:**
- Bar chart showing velocity (hours completed) per sprint
- Line overlay showing completion % per sprint
- Data from `SprintManager.get_velocity_trend(weeks=4)`

---

## Deliverable 2: Screen-by-Screen Wireframe Descriptions

### Layout: Single-page app with sidebar + main area

```
+------------------+----------------------------------------------+
|                  |  METRICS STRIP (full width)                  |
|   SIDEBAR        +----------------------------------------------+
|                  |                                              |
|   - Nav links    |  MAIN CONTENT AREA                           |
|   - Scheduler    |  (changes based on active tab)               |
|   - Standup      |                                              |
|                  |                                              |
+------------------+----------------------------------------------+
```

### Screen 1: Dashboard (default view, path: `/`)

**Metrics Strip** (top, 100% width, 80px height, flex row, 5 equal cards):

| Position | Label | Value source | Format |
|----------|-------|-------------|--------|
| Card 1 | Sprint Completion | `calculate_sprint_completion(current_sprint.id)` | `73%` with progress bar |
| Card 2 | Tasks Active | `stats.tasks_in_progress / stats.tasks_total` | `4 / 12` |
| Card 3 | Content Queue | count of items with status=draft | `3 drafts` |
| Card 4 | Scheduled Jobs | count of enabled scheduler tasks | `5 active` |
| Card 5 | Sprint Days Left | `(sprint.end_date - now).days` | `6 days` |

**Main area** (below metrics strip, two columns: 65% / 35%):

**Left column (65%): Sprint Board**
- Header: sprint name, goals as tags, date range
- 4 columns: Backlog, In Progress, Review, Done
- Each column has a header with count badge
- Backlog column has an "Add Task" button at top that expands an inline form
- Each task card (vertically stacked in column):
  - Priority badge (color-coded: red=1, orange=2, blue=3, gray=4-5)
  - Title (bold, truncated at 60 chars)
  - Estimate hours (small, right-aligned)
  - Assignee (small, left-aligned, or "Unassigned")
  - Click to expand: full description, ID, created_at, updated_at
  - "Move to" dropdown: shows only valid transitions
- Empty state per column: "No tasks" in muted text

**Right column (35%): AI Chat**
- 3 quick-prompt buttons in a row at top
- Scrollable message list (chat bubbles, user right, assistant left)
- Persona selector dropdown above input: dev_lead, content_creator, scheduler, standup_reporter, safety_reviewer
- Text input at bottom with send button
- Loading state: animated dots while waiting for response
- Empty state: "Ask FredAI anything about your projects, tasks, or content."

### Screen 2: Content (`/content`)

**Metrics Strip** (same as dashboard, always visible)

**Main area** (two columns: 60% / 40%):

**Left column (60%): Content Queue**
- Filter bar: status dropdown (all, draft, pending_review, approved, rejected)
- Content card list (vertical stack):
  - Status badge (color: draft=yellow, pending_review=blue, approved=green, rejected=red)
  - Type badge (linkedin_post, blog_post, newsletter, release_notes)
  - Title (from data.title or data.subject)
  - Body preview (first 300 chars, muted text)
  - Hashtags row (if present)
  - CTA line (if present)
  - Action row: Approve (green button), Reject (red button), Delete (icon)
  - Created date (small, muted)
- Empty state: "No content items. Generate your first piece of content."
- Loading state: skeleton cards

**Right column (40%): Content Generator**
- Type selector: linkedin_post, blog_post, newsletter, release_notes
- Conditional fields based on type:
  - linkedin_post: topic (text), tone (dropdown: professional, casual, technical, storytelling), context (textarea)
  - blog_post: topic (text), audience (text), key_points (textarea, one per line)
  - newsletter: topic (text), highlights (textarea, one per line), metrics (key=value textarea)
  - release_notes: commits (textarea, one per line), sprint_data (auto-populated from current sprint)
- "Generate" button (disabled while generating)
- Generation status: idle / "Generating... (this takes 15-30s)" / "Done -- see queue"
- Most recent generation result preview (rendered inline below form)

### Screen 3: Scheduler (`/scheduler`)

**Metrics Strip** (same)

**Main area** (single column, max-width 900px, centered):

**Scheduled Tasks Table:**

| Column | Width | Content |
|--------|-------|---------|
| Name | 25% | Task name |
| Type | 15% | Badge (standup, social_post, sprint_report, etc.) |
| Schedule | 20% | Cron expression + human label ("Daily at 9 AM") |
| Next Run | 15% | Relative time ("in 3 hours") + absolute |
| Last Run | 15% | Relative time ("2 hours ago") + absolute |
| Actions | 10% | Toggle switch (enabled/disabled), Delete button |

**Add Schedule Form** (below table, collapsible):
- Name (text input)
- Cron Expression (text input with helper: "0 9 * * *" = "Daily at 9 AM")
- Task Type (dropdown from TASK_TYPES)
- Config (JSON textarea, optional)
- "Add" button

Empty state: "No scheduled tasks. Add your first automation."

### Screen 4: Standups (`/standups`)

**Metrics Strip** (same)

**Main area** (single column, max-width 800px, centered):

**Header row:**
- "Generate Now" button (right-aligned)
- Date navigation: left arrow, date display, right arrow

**Standup Display:**
- Formatted standup text (monospace, pre-formatted from `format_standup()`)
- Sections clearly delineated: Yesterday, Today, Blockers
- Each section uses the standup data structure:
  - Yesterday: repo commits + completed tasks
  - Today: in_progress tasks
  - Blockers: review tasks

**History List** (below current standup):
- Cards for each previous day (last 7 days)
- Each card: date, summary line ("3 commits, 2 tasks completed"), expand to see full

Empty state: "No standups yet. Click 'Generate Now' to create today's standup."

### Sidebar (always visible, 250px width)

**Top:** FredAI logo/text + current date

**Navigation:**
- Dashboard (icon + label)
- Content (icon + label)
- Scheduler (icon + label)
- Standups (icon + label)

**Sprint Info (below nav):**
- Current sprint name
- Mini progress bar
- Completion %
- Days remaining

**Quick Actions:**
- "New Task" (opens task form on dashboard)
- "Generate Standup" (triggers standup generation)
- "New Content" (navigates to content page)

---

## Deliverable 3: Data Model for UI State

### Frontend State (React context / zustand store)

```typescript
// --- Sprint & Tasks ---
interface Task {
  id: string;             // 8-char UUID from SprintManager
  title: string;
  description: string;
  status: "backlog" | "sprint" | "in_progress" | "review" | "done";
  priority: number;       // 1-5
  estimate_hours: number;
  sprint_id: string | null;
  project: string;
  assignee: string;
  created_at: string;     // ISO datetime
  updated_at: string;     // ISO datetime
}

interface Sprint {
  id: string;
  name: string;
  start_date: string;     // ISO datetime
  end_date: string;       // ISO datetime
  goals: string[];
  status: "active" | "completed";
}

interface SprintState {
  currentSprint: Sprint | null;
  sprints: Sprint[];
  tasks: Task[];
  stats: SummaryStats;
  velocityTrend: VelocityPoint[];
  loading: boolean;
  error: string | null;
}

interface SummaryStats {
  tasks_total: number;
  tasks_done: number;
  tasks_in_progress: number;
  tasks_in_review: number;
  tasks_backlog: number;
  active_sprint: Sprint | null;
  velocity: number;
}

interface VelocityPoint {
  sprint: string;         // sprint name
  velocity: number;       // hours completed
  completion: number;     // percentage
}

// --- Content ---
interface ContentItem {
  id: string;
  type: "linkedin_post" | "blog_post" | "newsletter" | "release_notes";
  data: Record<string, any>;  // varies by type
  status: "draft" | "pending_review" | "approved" | "rejected";
  created_at: string;
}

interface ContentState {
  items: ContentItem[];
  filterStatus: string;
  generating: boolean;     // true while generation job is running
  generationJobId: string | null;
  loading: boolean;
  error: string | null;
}

// --- Scheduler ---
interface ScheduledTask {
  id: string;
  name: string;
  cron: string;            // matches cron_expression field
  type: string;            // task_type
  enabled: boolean;
  next_run: string | null;
  last_run: string | null;
}

interface SchedulerState {
  tasks: ScheduledTask[];
  loading: boolean;
  error: string | null;
}

// --- Standup ---
interface StandupData {
  date: string;            // YYYY-MM-DD
  generated_at: string;
  repos: Record<string, string[]>;  // repo_name -> commit list
  tasks: {
    completed: string[];
    in_progress: string[];
    blocked: string[];
  };
}

interface StandupState {
  current: StandupData | null;
  formatted: string;       // pre-formatted text from backend
  history: StandupData[];
  selectedDate: string;
  loading: boolean;
  error: string | null;
}

// --- Chat ---
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  persona?: string;        // which persona was used
  agent_name?: string;     // which AI model responded
}

interface ChatState {
  messages: ChatMessage[];        // persisted to localStorage
  selectedPersona: string;        // key from PersonaLibrary
  streaming: boolean;
  error: string | null;
}
```

### What comes from API calls vs local state

| Data | Source | Cache strategy |
|------|--------|---------------|
| `SprintState.tasks` | `GET /api/tasks` | Fetch on mount + after any mutation. No polling. |
| `SprintState.currentSprint` | `GET /api/sprints/current` | Fetch on mount. |
| `SprintState.stats` | `GET /api/stats` | Fetch on mount + after task mutations. |
| `SprintState.velocityTrend` | `GET /api/velocity` | Fetch on mount. Stale OK (changes weekly). |
| `ContentState.items` | `GET /api/content` | Fetch on mount + after generate/approve/reject. |
| `ContentState.generating` | `GET /api/content/jobs/{id}` | Poll every 3s while `generating=true`. |
| `SchedulerState.tasks` | `GET /api/scheduler` | Fetch on mount + after add/remove/toggle. |
| `StandupState.current` | `GET /api/standups/today` | Fetch on mount. |
| `StandupState.history` | `GET /api/standups?days=7` | Fetch on mount. Stale OK. |
| `ChatState.messages` | localStorage | Never fetched from API. Persisted client-side. |
| `ChatState.streaming` | SSE `/api/chat/stream` | Real-time SSE connection per message. |
| Sidebar sprint info | Derived from `SprintState` | No separate fetch. |

### Polling intervals

| Endpoint | Strategy | Interval |
|----------|----------|----------|
| Content generation job | Poll while `generating=true` | 3 seconds |
| Everything else | Fetch on mount + after mutations | No polling |

---

## Deliverable 4: API Contract Definitions

**Base URL:** `http://localhost:8100/api`
**Content-Type:** `application/json` (all requests and responses)
**Error format (all endpoints):**

```json
{
  "error": "Human-readable error message",
  "detail": "Optional technical detail"
}
```

Error HTTP codes: 400 (bad request), 404 (not found), 500 (server error).

---

### 4.1 Sprint & Task Endpoints

#### `GET /api/stats`

Returns summary statistics from `SprintManager.get_summary_stats()`.

**Response 200:**
```json
{
  "tasks_total": 12,
  "tasks_done": 5,
  "tasks_in_progress": 3,
  "tasks_in_review": 1,
  "tasks_backlog": 3,
  "active_sprint": {
    "id": "a1b2c3d4",
    "name": "Sprint 3",
    "start_date": "2026-02-17T00:00:00",
    "end_date": "2026-03-02T00:00:00",
    "goals": ["Ship content generator", "Fix scheduler"],
    "status": "active"
  },
  "velocity": 24.5
}
```

#### `GET /api/tasks`

Returns all tasks. Optional query params: `?status=in_progress&sprint_id=abc`.

**Response 200:**
```json
{
  "tasks": [
    {
      "id": "f7e8d9c0",
      "title": "Build content review UI",
      "description": "React component for reviewing generated content",
      "status": "in_progress",
      "priority": 2,
      "estimate_hours": 4.0,
      "sprint_id": "a1b2c3d4",
      "project": "command-center",
      "assignee": "fred",
      "created_at": "2026-02-20T10:00:00",
      "updated_at": "2026-02-21T14:30:00"
    }
  ]
}
```

#### `POST /api/tasks`

Creates a new task via `SprintManager.create_task()`.

**Request body:**
```json
{
  "title": "Implement scheduler toggle",
  "description": "Add enable/disable toggle to scheduler UI",
  "priority": 2,
  "estimate_hours": 2.0,
  "project": "command-center",
  "assignee": "fred"
}
```
Required: `title`. All others optional (defaults from Task dataclass).

**Response 201:**
```json
{
  "id": "b2c3d4e5",
  "title": "Implement scheduler toggle",
  "description": "Add enable/disable toggle to scheduler UI",
  "status": "backlog",
  "priority": 2,
  "estimate_hours": 2.0,
  "sprint_id": null,
  "project": "command-center",
  "assignee": "fred",
  "created_at": "2026-02-22T09:00:00",
  "updated_at": "2026-02-22T09:00:00"
}
```

#### `PATCH /api/tasks/{task_id}/status`

Updates task status via `SprintManager.update_task_status()`.

**Request body:**
```json
{
  "status": "in_progress"
}
```
Valid statuses: `backlog`, `sprint`, `in_progress`, `review`, `done`.

**Response 200:**
```json
{
  "success": true,
  "task_id": "f7e8d9c0",
  "new_status": "in_progress"
}
```

**Response 400** (invalid status):
```json
{
  "error": "Invalid status: 'invalid'. Must be one of: backlog, sprint, in_progress, review, done"
}
```

#### `POST /api/tasks/{task_id}/assign-sprint`

Assigns a task to a sprint via `SprintManager.add_to_sprint()`.

**Request body:**
```json
{
  "sprint_id": "a1b2c3d4"
}
```

**Response 200:**
```json
{
  "success": true,
  "task_id": "f7e8d9c0",
  "sprint_id": "a1b2c3d4"
}
```

---

### 4.2 Sprint Endpoints

#### `GET /api/sprints`

Returns all sprints.

**Response 200:**
```json
{
  "sprints": [
    {
      "id": "a1b2c3d4",
      "name": "Sprint 3",
      "start_date": "2026-02-17T00:00:00",
      "end_date": "2026-03-02T00:00:00",
      "goals": ["Ship content generator"],
      "status": "active"
    }
  ]
}
```

#### `GET /api/sprints/current`

Returns the current active sprint with its tasks and completion.

**Response 200:**
```json
{
  "sprint": {
    "id": "a1b2c3d4",
    "name": "Sprint 3",
    "start_date": "2026-02-17T00:00:00",
    "end_date": "2026-03-02T00:00:00",
    "goals": ["Ship content generator"],
    "status": "active"
  },
  "tasks": [ /* Task objects */ ],
  "completion_percentage": 41.7,
  "days_remaining": 8
}
```

**Response 404** (no active sprint):
```json
{
  "error": "No active sprint"
}
```

#### `POST /api/sprints`

Creates a new sprint via `SprintManager.create_sprint()`.

**Request body:**
```json
{
  "name": "Sprint 4",
  "goals": ["Launch command center", "Write docs"],
  "start_date": "2026-03-03T00:00:00",
  "end_date": "2026-03-16T00:00:00"
}
```
Required: `name`. Others optional.

**Response 201:**
```json
{
  "id": "e5f6a7b8",
  "name": "Sprint 4",
  "start_date": "2026-03-03T00:00:00",
  "end_date": "2026-03-16T00:00:00",
  "goals": ["Launch command center", "Write docs"],
  "status": "active"
}
```

#### `GET /api/velocity`

Returns velocity trend from `SprintManager.get_velocity_trend()`.

**Query params:** `?weeks=4` (optional, default 4)

**Response 200:**
```json
{
  "trend": [
    { "sprint": "Sprint 1", "velocity": 18.0, "completion": 75.0 },
    { "sprint": "Sprint 2", "velocity": 22.5, "completion": 80.0 },
    { "sprint": "Sprint 3", "velocity": 24.5, "completion": 41.7 }
  ]
}
```

---

### 4.3 Content Endpoints

#### `GET /api/content`

Returns all content items from `~/.ai-dev-team/workflow/content/*.json`.

**Query params:** `?status=draft` (optional filter)

**Response 200:**
```json
{
  "items": [
    {
      "id": "c1d2e3f4",
      "type": "linkedin_post",
      "status": "draft",
      "created_at": "2026-02-21T15:00:00",
      "data": {
        "title": "Why CMMS matters",
        "hook": "Most maintenance teams waste 30% of their time...",
        "body": "Full post body here...",
        "cta": "Try ChatterFix free for 14 days",
        "hashtags": ["#CMMS", "#Maintenance"],
        "suggested_publish_time": "Tuesday 9am"
      }
    }
  ]
}
```

#### `POST /api/content/generate`

Starts an async content generation job. Returns immediately with a job ID.

**Request body:**
```json
{
  "type": "linkedin_post",
  "params": {
    "topic": "Why preventive maintenance saves money",
    "tone": "professional",
    "context": "For maintenance managers at mid-size facilities"
  }
}
```

Type-specific `params`:
- `linkedin_post`: `topic` (required), `tone` (optional), `context` (optional)
- `blog_post`: `topic` (required), `audience` (required), `key_points` (optional, array)
- `newsletter`: `topic` (required), `highlights` (optional, array), `metrics` (optional, object)
- `release_notes`: `commits` (optional, array), `sprint_data` (optional, object -- auto-filled from current sprint if omitted)

**Response 202:**
```json
{
  "job_id": "gen_a1b2c3",
  "status": "running",
  "type": "linkedin_post"
}
```

#### `GET /api/content/jobs/{job_id}`

Poll for content generation job status.

**Response 200 (running):**
```json
{
  "job_id": "gen_a1b2c3",
  "status": "running",
  "started_at": "2026-02-22T09:00:00"
}
```

**Response 200 (completed):**
```json
{
  "job_id": "gen_a1b2c3",
  "status": "completed",
  "item_id": "c1d2e3f4",
  "result": { /* full content data object */ }
}
```

**Response 200 (failed):**
```json
{
  "job_id": "gen_a1b2c3",
  "status": "failed",
  "error": "Content generation returned empty result"
}
```

#### `POST /api/content/{item_id}/approve`

Approves a content item. Updates both the JSON file and ContentQueue.

**Response 200:**
```json
{
  "success": true,
  "item_id": "c1d2e3f4",
  "new_status": "approved"
}
```

#### `POST /api/content/{item_id}/reject`

Rejects a content item.

**Response 200:**
```json
{
  "success": true,
  "item_id": "c1d2e3f4",
  "new_status": "rejected"
}
```

---

### 4.4 Scheduler Endpoints

#### `GET /api/scheduler`

Returns all scheduled tasks from `TaskScheduler.list_tasks()`.

**Response 200:**
```json
{
  "tasks": [
    {
      "id": "s1t2u3v4",
      "name": "Daily Standup",
      "cron": "0 9 * * *",
      "type": "standup",
      "enabled": true,
      "next_run": "2026-02-23T09:00:00",
      "last_run": "2026-02-22T09:00:00"
    }
  ]
}
```

#### `POST /api/scheduler`

Adds a new scheduled task via `TaskScheduler.add_task()`.

**Request body:**
```json
{
  "name": "Weekly Blog Draft",
  "cron_expression": "0 8 * * 1",
  "task_type": "social_post",
  "config": {}
}
```
Required: `name`, `cron_expression`, `task_type`.

Valid task types: `standup`, `social_post`, `sprint_report`, `newsletter`, `code_review`, `custom`.

**Response 201:**
```json
{
  "id": "w5x6y7z8",
  "name": "Weekly Blog Draft",
  "cron": "0 8 * * 1",
  "type": "social_post",
  "enabled": true,
  "next_run": "2026-02-24T08:00:00",
  "last_run": null
}
```

#### `DELETE /api/scheduler/{task_id}`

Removes a scheduled task via `TaskScheduler.remove_task()`.

**Response 200:**
```json
{
  "success": true,
  "task_id": "w5x6y7z8"
}
```

**Response 404:**
```json
{
  "error": "Scheduled task not found: w5x6y7z8"
}
```

#### `PATCH /api/scheduler/{task_id}/toggle`

Toggles enabled/disabled state. (Note: `TaskScheduler` does not have a toggle method; implementation adds one or mutates `_tasks` directly and calls `_save()`.)

**Response 200:**
```json
{
  "success": true,
  "task_id": "s1t2u3v4",
  "enabled": false
}
```

---

### 4.5 Standup Endpoints

#### `GET /api/standups/today`

Returns today's standup (generates if not yet saved today).

**Response 200:**
```json
{
  "date": "2026-02-22",
  "formatted": "Daily Standup -- 2026-02-22\n===...",
  "raw": {
    "date": "2026-02-22",
    "generated_at": "2026-02-22T09:00:00",
    "repos": {
      "FredAI": ["abc1234 Fix scheduler deadlock (Fred Taylor)"],
      "managers-dashboard": []
    },
    "tasks": {
      "completed": ["Build content queue UI"],
      "in_progress": ["Implement scheduler toggle"],
      "blocked": []
    }
  }
}
```

#### `GET /api/standups`

Returns standup history.

**Query params:** `?days=7` (optional, default 7)

**Response 200:**
```json
{
  "standups": [
    {
      "date": "2026-02-22",
      "generated_at": "2026-02-22T09:00:00",
      "repos": { /* ... */ },
      "tasks": { /* ... */ }
    }
  ]
}
```

#### `POST /api/standups/generate`

Generates and saves today's standup on demand.

**Response 201:**
```json
{
  "date": "2026-02-22",
  "formatted": "Daily Standup -- 2026-02-22\n===...",
  "saved_to": "/Users/fred/.ai-dev-team/workflow/standups/2026-02-22.json"
}
```

---

### 4.6 Chat Endpoint

#### `POST /api/chat/stream`

Streams AI response via Server-Sent Events (SSE).

**Request body:**
```json
{
  "message": "What should I work on today?",
  "persona": "dev_lead",
  "context": ""
}
```

`persona` is optional (default: `dev_lead`). Must be a key from `PersonaLibrary.list_personas()`.

**Response:** SSE stream (`text/event-stream`)

```
data: {"token": "Based", "done": false}
data: {"token": " on", "done": false}
data: {"token": " your", "done": false}
...
data: {"token": "", "done": true, "agent_name": "chatgpt", "full_content": "Based on your current sprint..."}
```

The final SSE event has `done: true` and includes the full response content plus metadata.

**Fallback (non-streaming):** If SSE is problematic, fall back to `POST /api/chat` returning:

```json
{
  "content": "Based on your current sprint...",
  "agent_name": "chatgpt",
  "confidence": 0.85,
  "response_time": 2.3
}
```

---

### 4.7 Personas Endpoint

#### `GET /api/personas`

Returns available personas from `PersonaLibrary`.

**Response 200:**
```json
{
  "personas": [
    {
      "name": "dev_lead",
      "role": "Lead Developer",
      "capabilities": ["code_generation", "task_planning", "architecture", "testing"],
      "output_format": "json",
      "temperature": 0.6
    },
    {
      "name": "content_creator",
      "role": "Content Creator",
      "capabilities": ["linkedin", "blog", "newsletter", "copywriting"],
      "output_format": "json",
      "temperature": 0.8
    }
  ]
}
```

---

## Deliverable 5: MVP Scope -- 72-Hour Build Plan

### Day 1: Backend API + Skeleton Frontend (hours 0-24)

**Backend (must be real):**

1. Create `command_center_api/` directory at project root with:
   - `server.py` -- FastAPI app, CORS, mounts all routers
   - `routers/tasks.py` -- `GET /api/tasks`, `POST /api/tasks`, `PATCH /api/tasks/{id}/status`, `POST /api/tasks/{id}/assign-sprint`
   - `routers/sprints.py` -- `GET /api/sprints`, `GET /api/sprints/current`, `POST /api/sprints`, `GET /api/velocity`
   - `routers/stats.py` -- `GET /api/stats`
   - `routers/scheduler.py` -- full CRUD
   - `routers/standups.py` -- `GET /api/standups/today`, `GET /api/standups`, `POST /api/standups/generate`
   - `routers/personas.py` -- `GET /api/personas`

2. All routers instantiate the existing workflow module classes (`SprintManager`, `TaskScheduler`, `StandupGenerator`, `PersonaLibrary`) as singletons and call their methods directly. No new data layer.

3. Add `toggle_task()` method to `TaskScheduler` (3 lines: flip `enabled`, call `_save()`).

**Frontend (skeleton):**

4. `npx create-vite command-center-ui --template react` at project root
5. Install: `tailwindcss`, `react-router-dom`, `lucide-react` (icons)
6. Create layout shell: sidebar nav + metrics strip + main content area
7. Dashboard page: metrics strip (fetching from `/api/stats`) + task list (fetching from `/api/tasks`) displayed as 4-column board
8. Task cards: static display with status badge and priority color

**Runnable at end of Day 1:**
- `cd command_center_api && uvicorn server:app --reload --port 8100`
- `cd command-center-ui && npm run dev` (port 5173, proxy to 8100)
- Dashboard shows real task data from `~/.ai-dev-team/workflow/tasks.json`
- Can create tasks via API (curl or from UI form)

**Can be stubbed on Day 1:**
- Chat (hardcoded responses)
- Content generation (show form, return mock data)
- Velocity chart (show data in a table, chart comes Day 2)

---

### Day 2: Content + Chat + Scheduler UI (hours 24-48)

**Backend:**

1. `routers/content.py` -- `GET /api/content`, `POST /api/content/generate`, `GET /api/content/jobs/{id}`, `POST /api/content/{id}/approve`, `POST /api/content/{id}/reject`
2. Background content generation: use `asyncio.to_thread()` wrapping `ContentGenerator.generate_*()`. Store job status in an in-memory dict `{job_id: {status, result, error}}`.
3. `routers/chat.py` -- `POST /api/chat` (non-streaming first). Calls `AIDevTeam.ask(message, context=persona_system_prompt)` via `asyncio`. Returns `AgentResponse.content`.

**Frontend:**

4. Content page: queue list with filter, approve/reject buttons, generation form
5. Scheduler page: table of scheduled tasks, add form, delete button, toggle switch
6. Chat panel on Dashboard: quick-prompt buttons, message list, text input, send button
7. Loading states: skeleton loaders on all data-fetching components
8. Error states: red banner with error message on API failures
9. localStorage persistence for chat messages

**Runnable at end of Day 2:**
- All 4 pages functional with real data
- Can generate content (background job, poll for result)
- Can chat with AI (non-streaming, full response)
- Can add/remove/toggle scheduled tasks

**Can be stubbed on Day 2:**
- SSE streaming for chat (use full response for now)
- Velocity chart (still table)

---

### Day 3: Polish + Streaming + Charts + Docker (hours 48-72)

**Backend:**

1. `POST /api/chat/stream` -- SSE endpoint using `StreamingResponse`. If the orchestrator's `ask()` does not support streaming natively, fake it by splitting the full response into word-sized chunks and yielding them with small delays (feels real, ships fast).
2. Add sprint context injection to chat: before calling `ask()`, prepend current sprint stats and in-progress task titles to the context string so the AI gives task-aware answers.

**Frontend:**

3. SSE consumption in chat: `EventSource` or `fetch()` with `ReadableStream` to render tokens as they arrive
4. Velocity chart: use `recharts` (lightweight, React-native). Bar chart for velocity, line for completion %.
5. Sprint progress bar in metrics strip (animated)
6. Empty states for all panels (illustrated or text-only)
7. Responsive tweaks: sidebar collapse on narrow screens
8. Keyboard shortcuts: `Cmd+K` to focus chat input, `Cmd+N` for new task

**DevOps:**

9. `Makefile` at project root:
   ```makefile
   dev:
       (cd command_center_api && uvicorn server:app --reload --port 8100) & \
       (cd command-center-ui && npm run dev)

   build:
       cd command-center-ui && npm run build

   docker:
       docker compose up --build
   ```

10. `docker-compose.yml`:
    - `api` service: Python 3.11, installs `ai_dev_team` package, runs uvicorn on 8100
    - `ui` service: Node 20, builds Vite, serves with nginx on 80, proxies `/api` to `api:8100`
    - Mounts `~/.ai-dev-team/workflow/` as volume so data persists

**Runnable at end of Day 3:**
- `make dev` starts everything
- `docker compose up` for containerized run
- Full MVP: board, content, scheduler, standups, chat with streaming, velocity chart
- All loading/empty/error states handled

---

### Stub vs Real Decision Matrix

| Component | Day 1 | Day 2 | Day 3 |
|-----------|-------|-------|-------|
| Task CRUD API | Real | Real | Real |
| Sprint CRUD API | Real | Real | Real |
| Stats API | Real | Real | Real |
| Sprint Board UI | Real (no drag) | Real | Real + polish |
| Content API | Stub | Real | Real |
| Content UI | Stub form | Real | Real |
| Content generation | Stub (mock) | Real (background) | Real |
| Scheduler API | Real | Real | Real |
| Scheduler UI | -- | Real | Real |
| Standup API | Real | Real | Real |
| Standup UI | -- | Real | Real + date nav |
| Chat API | Stub | Real (non-stream) | Real (SSE stream) |
| Chat UI | Stub | Real | Real + streaming |
| Velocity chart | -- | Table | Recharts |
| Docker | -- | -- | Real |
| Metrics strip | Real | Real | Real + animations |
| Error/loading states | Minimal | Functional | Polished |

---

### File Structure (final)

```
FredAI/
  ai_dev_team/
    workflow/
      sprint_manager.py      # existing, no changes
      content_generator.py   # existing, no changes
      scheduler.py           # existing + add toggle_task() method
      standup.py             # existing, no changes
      personas.py            # existing, no changes
      progress_api.py        # existing Flask blueprint (unused by new UI)
  command_center_api/
    server.py                # FastAPI app
    routers/
      __init__.py
      tasks.py
      sprints.py
      stats.py
      content.py
      scheduler.py
      standups.py
      chat.py
      personas.py
  command-center-ui/
    src/
      App.jsx
      main.jsx
      api/
        client.js            # axios instance, base URL config
      components/
        MetricsStrip.jsx
        Sidebar.jsx
        TaskCard.jsx
        ContentCard.jsx
        ChatPanel.jsx
        SchedulerTable.jsx
        StandupViewer.jsx
        VelocityChart.jsx
      pages/
        Dashboard.jsx
        Content.jsx
        Scheduler.jsx
        Standups.jsx
      store/
        useSprint.js         # zustand store for sprint/task state
        useContent.js
        useScheduler.js
        useStandup.js
        useChat.js
    tailwind.config.js
    vite.config.js           # proxy /api to localhost:8100
    package.json
  docker-compose.yml
  Makefile
  docs/
    command-center-prd.md    # this file
```
