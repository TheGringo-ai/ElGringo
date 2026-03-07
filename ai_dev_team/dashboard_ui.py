#!/usr/bin/env python3
"""
El Gringo Dashboard - Costs, Patterns, Agent Performance
======================================================

Visualizes:
- Today's costs by model
- Memory quality report and top patterns
- Agent performance rankings
- Benchmark routing table

Run with: python -m ai_dev_team.dashboard_ui
Opens at: http://localhost:7862
"""

import logging

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
team = None
memory = None
cost_tracker = None


def get_team():
    """Lazy-init the AI team."""
    global team
    if team is None:
        from .orchestrator import AIDevTeam
        team = AIDevTeam(project_name="dashboard")
    return team


def get_memory():
    """Lazy-init the memory system."""
    global memory
    if memory is None:
        from .memory import MemorySystem
        memory = MemorySystem()
    return memory


def get_cost_tracker():
    """Lazy-init the cost tracker."""
    global cost_tracker
    if cost_tracker is None:
        from .routing.cost_tracker import get_cost_tracker as _get
        cost_tracker = _get()
    return cost_tracker


# ---- Data fetchers ----

def fetch_cost_summary():
    """Get cost summary for the dashboard."""
    tracker = get_cost_tracker()
    stats = tracker.get_statistics()

    today = stats.get("today", {})
    budget = stats.get("budget", {})
    by_model = stats.get("by_model", {})

    # Format model table
    rows = []
    for model, data in by_model.items():
        rows.append([
            model,
            data.get("total_requests", 0),
            data.get("total_tokens", 0),
            f"${data.get('total_cost', 0):.4f}",
        ])

    # Sort by cost descending
    rows.sort(key=lambda r: float(r[3].replace("$", "")), reverse=True)

    summary = (
        f"## Today ({today.get('date', 'N/A')})\n"
        f"- **Requests:** {today.get('total_requests', 0)}\n"
        f"- **Tokens:** {today.get('total_tokens', 0):,}\n"
        f"- **Cost:** ${today.get('total_cost', 0):.4f}\n\n"
        f"## Budget\n"
        f"- Daily: ${budget.get('daily_spent', 0):.4f} / ${budget.get('daily_limit', 10):.2f} "
        f"({budget.get('daily_percentage', 0):.1f}%)\n"
        f"- Monthly: ${budget.get('monthly_spent', 0):.4f} / ${budget.get('monthly_limit', 100):.2f} "
        f"({budget.get('monthly_percentage', 0):.1f}%)\n"
    )

    return summary, rows


def fetch_quality_report():
    """Get memory quality report."""
    mem = get_memory()
    report = mem.get_quality_report()

    summary = (
        f"## Memory Quality\n"
        f"- **Total patterns:** {report.get('total', 0)}\n"
        f"- **Avg quality:** {report.get('avg_quality', 0):.3f}\n"
        f"- **High quality (>0.7):** {report.get('high_quality', 0)}\n"
        f"- **Medium (0.4-0.7):** {report.get('medium_quality', 0)}\n"
        f"- **Low (<0.4):** {report.get('low_quality', 0)}\n"
        f"- **User-rated:** {report.get('user_rated', 0)}\n"
        f"- **Curated (with best practices):** {report.get('curated_with_practices', 0)}\n"
    )

    # Top patterns table
    rows = []
    for p in report.get("top_5", []):
        rows.append([
            p.get("pattern", "")[:50],
            f"{p.get('quality', 0):.3f}",
            p.get("ratings", "+0/-0"),
            p.get("injections", 0),
        ])

    return summary, rows


def fetch_agent_status():
    """Get agent performance stats."""
    t = get_team()
    status = t.get_team_status()

    agents = status.get("agents", {})
    rows = []
    for name, stats in agents.items():
        rows.append([
            name,
            stats.get("role", ""),
            stats.get("total_requests", 0),
            f"{stats.get('success_rate', 0):.0%}",
            f"{stats.get('avg_response_time', 0):.2f}s",
            "Yes" if stats.get("enabled", False) else "No",
        ])

    rows.sort(key=lambda r: r[2], reverse=True)

    summary = (
        f"## Team Status\n"
        f"- **Total agents:** {status.get('total_agents', 0)}\n"
        f"- **Memory:** {'Enabled' if status.get('memory_enabled') else 'Disabled'}\n"
        f"- **Learning:** {'Enabled' if status.get('learning_enabled') else 'Disabled'}\n"
        f"- **Project:** {status.get('project', 'default')}\n"
    )

    return summary, rows


def fetch_routing_table():
    """Get benchmark routing table."""
    try:
        from .routing.benchmark import BenchmarkRunner
        t = get_team()
        runner = BenchmarkRunner(t)
        table = runner.get_routing_table()

        if not table:
            return "No benchmark data yet. Run `ai_team_benchmark` to build the routing table.", []

        rows = []
        for task_type, data in table.items():
            rankings = data.get("rankings", {})
            best = data.get("best_agent", "unknown")
            updated = data.get("updated", "")[:10]

            for agent, score in sorted(rankings.items(), key=lambda x: x[1], reverse=True):
                rows.append([
                    task_type,
                    agent,
                    f"{score:.3f}",
                    "BEST" if agent == best else "",
                    updated,
                ])

        summary = f"## Routing Table\nBased on standardized benchmarks across {len(table)} task types.\n"
        return summary, rows

    except Exception as e:
        return f"Error loading routing table: {e}", []


def create_dashboard():
    """Create the Gradio dashboard."""
    import gradio as gr

    with gr.Blocks(
        title="El Gringo Dashboard",
        theme=gr.themes.Soft(primary_hue="blue"),
    ) as app:

        gr.Markdown("# El Gringo Dashboard\nReal-time costs, memory quality, and agent performance")

        with gr.Tabs():
            # ---- Costs Tab ----
            with gr.TabItem("Costs"):
                cost_summary = gr.Markdown("Loading...")
                cost_table = gr.Dataframe(
                    headers=["Model", "Requests", "Tokens", "Cost"],
                    interactive=False,
                )
                cost_btn = gr.Button("Refresh Costs")
                cost_btn.click(fn=fetch_cost_summary, outputs=[cost_summary, cost_table])

            # ---- Memory Quality Tab ----
            with gr.TabItem("Memory Quality"):
                quality_summary = gr.Markdown("Loading...")
                quality_table = gr.Dataframe(
                    headers=["Pattern", "Quality", "Ratings", "Injections"],
                    interactive=False,
                )
                quality_btn = gr.Button("Refresh Quality")
                quality_btn.click(fn=fetch_quality_report, outputs=[quality_summary, quality_table])

            # ---- Agents Tab ----
            with gr.TabItem("Agents"):
                agent_summary = gr.Markdown("Loading...")
                agent_table = gr.Dataframe(
                    headers=["Agent", "Role", "Requests", "Success Rate", "Avg Time", "Enabled"],
                    interactive=False,
                )
                agent_btn = gr.Button("Refresh Agents")
                agent_btn.click(fn=fetch_agent_status, outputs=[agent_summary, agent_table])

            # ---- Routing Table Tab ----
            with gr.TabItem("Routing Table"):
                routing_summary = gr.Markdown("Loading...")
                routing_table = gr.Dataframe(
                    headers=["Task Type", "Agent", "Score", "Best?", "Updated"],
                    interactive=False,
                )
                routing_btn = gr.Button("Refresh Routing")
                routing_btn.click(fn=fetch_routing_table, outputs=[routing_summary, routing_table])

        # Auto-load on open
        app.load(fn=fetch_cost_summary, outputs=[cost_summary, cost_table])

        # Auto-refresh every 30 seconds
        timer = gr.Timer(value=30)
        timer.tick(fn=fetch_cost_summary, outputs=[cost_summary, cost_table])
        timer.tick(fn=fetch_agent_status, outputs=[agent_summary, agent_table])

    return app


def main():
    """Launch the dashboard."""
    app = create_dashboard()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
