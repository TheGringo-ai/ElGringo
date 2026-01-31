#!/usr/bin/env python3
"""
AI Team Chat UI
===============

A Gradio-based chat interface for the AI Team Platform.
Supports natural language + commands: /react, /reason, /plan

Run with: python chat_ui.py
Opens at: http://localhost:7860
"""

import asyncio
import gradio as gr
import logging
import os
from datetime import datetime
from typing import List, Tuple

# Load environment
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global team instance
team = None


def get_team():
    """Get or create the AI Team instance."""
    global team
    if team is None:
        from ai_dev_team import AIDevTeam
        team = AIDevTeam(project_name="chat-ui", enable_memory=True)
        logger.info(f"AI Team initialized with {len(team.agents)} agents")
    return team


def format_react_trace(trace) -> str:
    """Format ReAct trace for display."""
    lines = []
    lines.append(f"**ReAct Agent** | {len(trace.steps)} steps | {trace.execution_time:.2f}s\n")

    for step in trace.steps:
        lines.append(f"\n**Step {step.step_number}:**")
        lines.append(f"- 💭 *Thought:* {step.thought[:300]}{'...' if len(step.thought) > 300 else ''}")
        if step.action:
            lines.append(f"- 🔧 *Action:* `{step.action}`")
        if step.observation:
            obs = step.observation[:200] + '...' if len(step.observation) > 200 else step.observation
            lines.append(f"- 👁️ *Observation:* {obs}")

    lines.append(f"\n---\n**Final Answer:**\n{trace.final_answer}")
    return "\n".join(lines)


def format_reasoning_chain(chain) -> str:
    """Format reasoning chain for display."""
    lines = []
    lines.append(f"**Chain-of-Thought** | {len(chain.steps)} steps | Confidence: {chain.confidence:.0%}\n")

    for step in chain.steps:
        lines.append(f"\n**Step {step.step_number}:**")
        lines.append(f"{step.content}")

    lines.append(f"\n---\n**Conclusion:**\n{chain.conclusion}")
    return "\n".join(lines)


def format_plan(plan) -> str:
    """Format execution plan for display."""
    lines = []
    progress = plan.get_progress()
    lines.append(f"**Task Planner** | {progress['completed']}/{progress['total']} steps | {plan.status.value}\n")

    status_emoji = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
        "failed": "❌",
        "skipped": "⏭️",
        "blocked": "🚫",
    }

    for step in plan.steps:
        emoji = status_emoji.get(step.status.value, "❓")
        lines.append(f"{emoji} **{step.description}**")
        if step.error:
            lines.append(f"   - ❌ Error: {step.error}")

    return "\n".join(lines)


async def process_message(message: str, history: List[Tuple[str, str]]) -> str:
    """Process a user message and return the response."""
    t = get_team()
    message = message.strip()

    if not message:
        return "Please enter a message."

    try:
        # Check for commands
        if message.lower().startswith("/react "):
            task = message[7:].strip()
            trace = await t.react(task, max_steps=10, verbose=False)
            return format_react_trace(trace)

        elif message.lower().startswith("/reason "):
            problem = message[8:].strip()
            chain = await t.reason(problem, method="zero_shot")
            return format_reasoning_chain(chain)

        elif message.lower().startswith("/plan "):
            goal = message[6:].strip()
            plan = await t.plan_and_execute(goal)
            return format_plan(plan)

        elif message.lower() == "/help":
            return """**AI Team Commands:**

- `/react <task>` - ReAct agent (reasoning + tool use)
- `/reason <problem>` - Chain-of-thought reasoning
- `/plan <goal>` - Multi-step task planning
- `/agents` - List available agents
- `/help` - Show this help

**Or just type naturally** and the AI Team will collaborate!

**Examples:**
- `/react Find all Python files with TODO comments`
- `/reason What are the trade-offs of microservices?`
- `/plan Set up a new Flask API project`
- `Write a function to validate email addresses`
"""

        elif message.lower() == "/agents":
            agents = list(t.agents.keys())
            local = [a for a in agents if "local" in a.lower()]
            cloud = [a for a in agents if "local" not in a.lower()]

            response = f"**Available Agents ({len(agents)} total):**\n\n"
            if cloud:
                response += f"☁️ **Cloud:** {', '.join(cloud)}\n"
            if local:
                response += f"🏠 **Local:** {', '.join(local)}\n"
            return response

        else:
            # Regular collaboration
            result = await t.collaborate(prompt=message, mode="parallel")

            agents_used = ', '.join(result.participating_agents) if result.participating_agents else "AI Team"

            response = f"**{agents_used}** | {result.total_time:.2f}s | Confidence: {result.confidence_score:.0%}\n\n"
            response += result.final_answer
            return response

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}"


def create_ui():
    """Create the Gradio UI."""

    # Custom CSS for better styling
    css = """
    .container { max-width: 900px; margin: auto; }
    .chatbot { height: 500px !important; }
    footer { display: none !important; }
    """

    with gr.Blocks(title="AI Team Chat") as demo:
        gr.Markdown("""
        # 🤖 AI Team Chat

        Chat with Fred's AI Development Team. Use natural language or commands:

        | Command | Description |
        |---------|-------------|
        | `/react <task>` | ReAct agent with tool use |
        | `/reason <problem>` | Step-by-step reasoning |
        | `/plan <goal>` | Multi-step planning |
        | `/help` | Show all commands |
        """)

        chatbot = gr.Chatbot(
            label="Conversation",
            height=450,
        )

        with gr.Row():
            msg = gr.Textbox(
                label="Message",
                placeholder="Type your message or /command here...",
                scale=9,
                show_label=False,
            )
            submit = gr.Button("Send", variant="primary", scale=1)

        with gr.Row():
            clear = gr.Button("🗑️ Clear Chat")
            examples_btn = gr.Button("📚 Examples")

        # Status bar
        status = gr.Markdown("*Ready - Type a message to start*")

        async def respond(message, chat_history):
            if not message.strip():
                yield "", chat_history
                return

            # Add user message to history
            chat_history = chat_history + [(message, None)]
            yield "", chat_history

            # Get response
            response = await process_message(message, chat_history)

            # Update with response
            chat_history[-1] = (message, response)
            yield "", chat_history

        def clear_chat():
            return [], "*Chat cleared - Ready*"

        def show_examples():
            examples = """**Try these examples:**

**ReAct (tool use):**
- `/react List Python files in the current directory`
- `/react Read the README.md and summarize it`

**Reasoning:**
- `/reason Why is Python popular for AI?`
- `/reason What are the pros and cons of NoSQL databases?`

**Planning:**
- `/plan Create a REST API for user management`

**Natural language:**
- `Write a Python function to merge two sorted lists`
- `Explain how async/await works in Python`
"""
            return examples

        # Event handlers
        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        submit.click(respond, [msg, chatbot], [msg, chatbot])
        clear.click(clear_chat, outputs=[chatbot, status])
        examples_btn.click(show_examples, outputs=[status])

        gr.Markdown("""
        ---
        *Powered by Fred's AI Team Platform - Claude, ChatGPT, Gemini, Grok, and Local Models*
        """)

    return demo


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("🤖 AI Team Chat UI")
    print("="*60)

    # Pre-initialize team
    print("\nInitializing AI Team...")
    t = get_team()
    print(f"✓ {len(t.agents)} agents ready")

    agents = list(t.agents.keys())
    local = [a for a in agents if "local" in a.lower()]
    cloud = [a for a in agents if "local" not in a.lower()]

    if cloud:
        print(f"  ☁️  Cloud: {', '.join(cloud)}")
    if local:
        print(f"  🏠 Local: {', '.join(local)}")

    print("\n" + "="*60)
    print("Starting web interface...")
    print("Open: http://localhost:7860")
    print("="*60 + "\n")

    # Create and launch UI
    ui = create_ui()
    ui.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
