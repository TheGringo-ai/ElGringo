"""
El Gringo Command Center
=====================
Unified Streamlit dashboard for daily operations:
sprint board, content queue, AI chat, and automation status.

Run: streamlit run elgringo/command_center.py --server.port 7863
"""

import asyncio
import concurrent.futures
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import streamlit as st

# ---------------------------------------------------------------------------
# Async bridge (same pattern as chat_ui.py)
# ---------------------------------------------------------------------------

def run_async(coro):
    """Run async code in sync Streamlit context."""
    def _in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(_in_new_loop).result(timeout=120)
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Cached singletons
# ---------------------------------------------------------------------------

@st.cache_resource
def get_sprint_manager():
    from elgringo.workflow.sprint_manager import SprintManager
    return SprintManager()


@st.cache_resource
def get_content_generator():
    from elgringo.workflow.content_generator import ContentGenerator
    return ContentGenerator()


@st.cache_resource
def get_content_queue():
    from elgringo.workflow.content_generator import ContentQueue
    return ContentQueue()


@st.cache_resource
def get_scheduler():
    from elgringo.workflow.scheduler import TaskScheduler
    return TaskScheduler()


@st.cache_resource
def get_standup_generator():
    from elgringo.workflow.standup import StandupGenerator
    return StandupGenerator()


@st.cache_resource
def get_ai_team():
    from elgringo.orchestrator import AIDevTeam
    return AIDevTeam()


@st.cache_resource
def get_persona_library():
    from elgringo.workflow.personas import PersonaLibrary
    return PersonaLibrary()


CONTENT_DIR = Path.home() / ".ai-dev-team" / "workflow" / "content"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def priority_label(p) -> str:
    """Normalize priority (int or string) to display label."""
    mapping = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Low"}
    if isinstance(p, int):
        return mapping.get(p, f"P{p}")
    s = str(p).lower()
    if s in ("critical", "high", "medium", "low"):
        return s.capitalize()
    try:
        return mapping.get(int(s), s)
    except ValueError:
        return s.capitalize()


def load_content_files() -> List[Dict]:
    """Load all content JSON files from the content directory."""
    items = []
    if not CONTENT_DIR.exists():
        return items
    for fp in sorted(CONTENT_DIR.glob("*.json")):
        try:
            with fp.open() as f:
                data = json.load(f)
            data["_filepath"] = str(fp)
            if "id" not in data:
                data["id"] = fp.stem
            items.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return items


def update_content_file_status(filepath: str, new_status: str):
    """Update status field in a content JSON file."""
    fp = Path(filepath)
    if not fp.exists():
        return
    with fp.open() as f:
        data = json.load(f)
    data["status"] = new_status
    with fp.open("w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="El Gringo Command Center",
    page_icon="@",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("El Gringo Command Center")
st.caption(datetime.now().strftime("%B %d, %Y"))

# ---------------------------------------------------------------------------
# Metrics strip
# ---------------------------------------------------------------------------

sm = get_sprint_manager()
scheduler = get_scheduler()

sprint = sm.get_current_sprint()
sprint_id = sprint.id if sprint else None
sprint_name = sprint.name if sprint else "No active sprint"

if sprint_id:
    completion = sm.calculate_sprint_completion(sprint_id)
    sprint_tasks = sm.get_tasks_for_sprint(sprint_id)
else:
    completion = 0.0
    sprint_tasks = []

stats = sm.get_summary_stats()
all_tasks = sm.tasks

content_items = load_content_files()
draft_count = sum(1 for c in content_items if c.get("status") == "draft")

sched_tasks = scheduler.list_tasks()
enabled_count = sum(1 for t in sched_tasks if t.get("enabled"))

if sprint and sprint.end_date:
    try:
        end = datetime.fromisoformat(sprint.end_date)
        days_left = max(0, (end - datetime.now()).days)
    except ValueError:
        days_left = "?"
else:
    days_left = "?"

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Sprint Completion", f"{completion}%")
m2.metric("Tasks Active", f"{stats['tasks_in_progress']}/{stats['tasks_total']}")
m3.metric("Content Queue", str(draft_count))
m4.metric("Scheduler", f"{enabled_count} jobs")
m5.metric("Days Left", str(days_left))

st.divider()

# ---------------------------------------------------------------------------
# Sprint Board + Content Queue (side by side)
# ---------------------------------------------------------------------------

col_sprint, col_content = st.columns([3, 2])

# --- Sprint Board ---
with col_sprint:
    st.subheader(f"Sprint Board — {sprint_name}")
    if sprint and sprint.goals:
        st.caption("Goals: " + " | ".join(sprint.goals))

    # Use all tasks (not just sprint-scoped) so backlog shows too
    kanban = {"Backlog": [], "In Progress": [], "Review": [], "Done": []}
    for t in all_tasks:
        if t.status in ("backlog", "sprint"):
            kanban["Backlog"].append(t)
        elif t.status == "in_progress":
            kanban["In Progress"].append(t)
        elif t.status == "review":
            kanban["Review"].append(t)
        elif t.status == "done":
            kanban["Done"].append(t)

    k1, k2, k3, k4 = st.columns(4)
    status_map = {
        "Backlog": ("backlog", k1),
        "In Progress": ("in_progress", k2),
        "Review": ("review", k3),
        "Done": ("done", k4),
    }

    for label, (_, col) in status_map.items():
        tasks_in_col = kanban[label]
        col.markdown(f"**{label}** ({len(tasks_in_col)})")
        for task in tasks_in_col:
            with col.expander(f"{priority_label(task.priority)} — {task.title}", expanded=False):
                st.text(f"ID: {task.id}")
                if task.assignee:
                    st.text(f"Assignee: {task.assignee}")
                if task.estimate_hours:
                    st.text(f"Est: {task.estimate_hours}h")
                if task.description:
                    st.caption(task.description[:200])
                new_status = st.selectbox(
                    "Move to",
                    ["backlog", "in_progress", "review", "done"],
                    key=f"status_{task.id}",
                    index=["backlog", "in_progress", "review", "done"].index(
                        task.status if task.status != "sprint" else "backlog"
                    ),
                )
                if st.button("Update", key=f"btn_{task.id}"):
                    sm.update_task_status(task.id, new_status)
                    st.rerun()

# --- Content Queue ---
with col_content:
    st.subheader("Content Queue")

    filter_status = st.selectbox(
        "Filter",
        ["all", "draft", "pending_review", "approved", "rejected"],
        key="content_filter",
    )

    filtered = content_items
    if filter_status != "all":
        filtered = [c for c in content_items if c.get("status") == filter_status]

    for item in filtered:
        item_id = item.get("id", "?")
        item_type = item.get("type", "content")
        item_status = item.get("status", "unknown")
        data = item.get("data", item)

        title = data.get("title", data.get("subject", item_type))
        with st.expander(f"[{item_status}] {title}", expanded=False):
            body = data.get("body", data.get("preview_text", ""))
            if body:
                st.write(body[:500])
            hashtags = data.get("hashtags", [])
            if hashtags:
                st.caption(" ".join(hashtags))
            cta = data.get("cta", "")
            if cta:
                st.caption(f"CTA: {cta}")

            filepath = item.get("_filepath", "")
            bc1, bc2 = st.columns(2)
            if bc1.button("Approve", key=f"approve_{item_id}"):
                update_content_file_status(filepath, "approved")
                get_content_queue().approve(item_id)
                st.rerun()
            if bc2.button("Reject", key=f"reject_{item_id}"):
                update_content_file_status(filepath, "rejected")
                get_content_queue().reject(item_id)
                st.rerun()

    st.markdown("---")
    st.markdown("**Generate New Content**")
    gen_type = st.selectbox("Type", ["linkedin_post", "blog_post", "newsletter", "release_notes"], key="gen_type")
    gen_topic = st.text_input("Topic", key="gen_topic")
    if st.button("Generate", key="gen_btn") and gen_topic:
        with st.spinner("Generating..."):
            cg = get_content_generator()
            if gen_type == "linkedin_post":
                cg.generate_linkedin_post(gen_topic)
            elif gen_type == "blog_post":
                cg.generate_blog_post(gen_topic, audience="developers")
            elif gen_type == "newsletter":
                cg.generate_newsletter(gen_topic)
            else:
                cg.generate_release_notes()
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# AI Dev Lead Chat
# ---------------------------------------------------------------------------

st.subheader("AI Dev Lead Chat")

if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[Dict[str, str]] = []

quick_cols = st.columns(3)
quick_prompts = [
    "What should I work on today?",
    "Summarize this week's progress",
    "Generate a content idea for LinkedIn",
]
for i, col in enumerate(quick_cols):
    if col.button(quick_prompts[i], key=f"quick_{i}"):
        st.session_state.chat_history.append({"role": "user", "content": quick_prompts[i]})
        with st.spinner("Thinking..."):
            persona = get_persona_library().get_system_prompt("dev_lead") or ""
            team = get_ai_team()
            response = run_async(team.ask(quick_prompts[i], context=persona))
            answer = response.content if hasattr(response, "content") else str(response)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask El Gringo anything...")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            persona = get_persona_library().get_system_prompt("dev_lead") or ""
            team = get_ai_team()
            response = run_async(team.ask(user_input, context=persona))
            answer = response.content if hasattr(response, "content") else str(response)
        st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ---------------------------------------------------------------------------
# Sidebar — Automation & Standups
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Automation Status")
    for task in sched_tasks:
        icon = "ON" if task.get("enabled") else "OFF"
        st.markdown(f"**{icon}** {task['name']}")
        st.caption(f"Cron: `{task['cron']}`")
        if task.get("next_run"):
            st.caption(f"Next: {task['next_run'][:16]}")
        if task.get("last_run"):
            st.caption(f"Last: {task['last_run'][:16]}")
        st.markdown("---")

    st.header("Recent Standups")
    sg = get_standup_generator()
    history = sg.get_standup_history(days=5)
    if history:
        for su in history:
            with st.expander(su.get("date", "?")):
                st.text(sg.format_standup(su))
    else:
        st.caption("No standups yet. Run the scheduler or generate one manually.")
