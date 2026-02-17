"""
Business Suite UI Components
============================

Gradio UI components for the business development suite.
"""

import gradio as gr
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from .models import (
    Client, Project, ChatBot, KnowledgeBase, Deployment,
    BusinessDataStore, create_client, create_project, create_chatbot
)
from .chat_builder import (
    ChatBotBuilder, PERSONA_TEMPLATES, FLOW_TEMPLATES, INDUSTRY_PRESETS
)
from .integrations import (
    APIKeyManager, WebhookManager, EmbedCodeGenerator, get_available_integrations
)


# Initialize global instances
data_store = BusinessDataStore()
chat_builder = ChatBotBuilder()
api_manager = APIKeyManager()
webhook_manager = WebhookManager()
embed_generator = EmbedCodeGenerator()


def create_business_suite_ui():
    """Create the complete Business Suite UI."""

    # Custom CSS
    gr.HTML("""
    <style>
        .client-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #3b82f6;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-active { background: #dcfce7; color: #166534; }
        .status-prospect { background: #fef3c7; color: #92400e; }
        .status-inactive { background: #f3f4f6; color: #6b7280; }
        .metric-card {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 24px;
            border-radius: 12px;
            text-align: center;
        }
        .metric-card h3 { font-size: 32px; margin: 0; }
        .metric-card p { margin: 4px 0 0 0; opacity: 0.9; }
    </style>
    """)

    gr.Markdown("## AI Business Development Suite")
    gr.Markdown("*Build, deploy, and manage AI chat solutions for your clients*")

    with gr.Tabs() as main_tabs:

        # ==========================================
        # TAB 1: DASHBOARD
        # ==========================================
        with gr.Tab("📊 Dashboard"):
            with gr.Row():
                with gr.Column():
                    gr.HTML("""
                    <div class="metric-card">
                        <h3>0</h3>
                        <p>Active Clients</p>
                    </div>
                    """)
                with gr.Column():
                    gr.HTML("""
                    <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                        <h3>0</h3>
                        <p>Live Chatbots</p>
                    </div>
                    """)
                with gr.Column():
                    gr.HTML("""
                    <div class="metric-card" style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);">
                        <h3>0</h3>
                        <p>Conversations Today</p>
                    </div>
                    """)
                with gr.Column():
                    gr.HTML("""
                    <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                        <h3>$0</h3>
                        <p>Monthly Revenue</p>
                    </div>
                    """)

            gr.Markdown("### Recent Activity")
            activity_log = gr.Dataframe(
                headers=["Time", "Activity", "Client", "Details"],
                value=[
                    [datetime.now().strftime("%H:%M"), "System Started", "-", "Business Suite initialized"],
                ],
                interactive=False
            )

        # ==========================================
        # TAB 2: CLIENTS
        # ==========================================
        with gr.Tab("👥 Clients"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Client List")
                    client_list = gr.Dataframe(
                        headers=["ID", "Company", "Industry", "Status", "Tier"],
                        value=[],
                        interactive=False
                    )
                    refresh_clients_btn = gr.Button("🔄 Refresh", size="sm")

                with gr.Column(scale=2):
                    with gr.Tabs():
                        with gr.Tab("➕ Add Client"):
                            company_name = gr.Textbox(label="Company Name", placeholder="Acme Corp")
                            industry = gr.Dropdown(
                                choices=["SaaS", "E-commerce", "Healthcare", "Finance", "Real Estate", "Education", "Other"],
                                label="Industry"
                            )
                            website = gr.Textbox(label="Website", placeholder="https://example.com")
                            with gr.Row():
                                contact_name = gr.Textbox(label="Primary Contact", placeholder="John Doe")
                                contact_email = gr.Textbox(label="Email", placeholder="john@example.com")
                            pricing_tier = gr.Radio(
                                choices=["starter", "professional", "business", "enterprise"],
                                value="starter",
                                label="Pricing Tier"
                            )
                            notes = gr.Textbox(label="Notes", lines=3)
                            add_client_btn = gr.Button("Add Client", variant="primary")
                            add_client_status = gr.Textbox(label="Status", interactive=False)

                        with gr.Tab("📋 Client Details"):
                            client_id_input = gr.Textbox(label="Client ID")
                            load_client_btn = gr.Button("Load Client")
                            client_details = gr.JSON(label="Client Data")

        # ==========================================
        # TAB 3: PROJECTS
        # ==========================================
        with gr.Tab("📁 Projects"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Projects")
                    project_list = gr.Dataframe(
                        headers=["ID", "Name", "Client", "Status", "Budget"],
                        value=[],
                        interactive=False
                    )

                with gr.Column(scale=2):
                    with gr.Tab("➕ New Project"):
                        proj_client_id = gr.Textbox(label="Client ID")
                        proj_name = gr.Textbox(label="Project Name", placeholder="AI Chatbot for Support")
                        proj_description = gr.Textbox(label="Description", lines=3)
                        proj_budget = gr.Number(label="Budget ($)", value=0)
                        with gr.Row():
                            proj_start = gr.Textbox(label="Start Date", placeholder="2024-01-15")
                            proj_target = gr.Textbox(label="Target Date", placeholder="2024-03-15")
                        create_project_btn = gr.Button("Create Project", variant="primary")
                        project_status = gr.Textbox(label="Status", interactive=False)

        # ==========================================
        # TAB 4: CHAT BUILDER
        # ==========================================
        with gr.Tab("🤖 Chat Builder"):
            with gr.Row():
                # Left: Configuration
                with gr.Column(scale=1):
                    gr.Markdown("### Build Your Chatbot")

                    with gr.Accordion("🏢 Client Info", open=True):
                        cb_project_id = gr.Textbox(label="Project ID")
                        cb_company_name = gr.Textbox(label="Company Name", placeholder="Acme Corp")
                        cb_industry = gr.Dropdown(
                            choices=list(INDUSTRY_PRESETS.keys()),
                            label="Industry",
                            value="saas"
                        )

                    with gr.Accordion("🎭 Persona", open=True):
                        persona_select = gr.Dropdown(
                            choices=[(v["name"], k) for k, v in PERSONA_TEMPLATES.items()],
                            label="Persona Template",
                            value="professional_assistant"
                        )
                        persona_preview = gr.Markdown("*Select a persona to see details*")

                    with gr.Accordion("⚙️ Model Settings", open=False):
                        model_select = gr.Dropdown(
                            choices=["claude-sonnet", "claude-opus", "gpt-4o", "gemini-pro", "grok"],
                            value="claude-sonnet",
                            label="AI Model"
                        )
                        temperature = gr.Slider(0, 1, value=0.7, label="Temperature")
                        max_tokens = gr.Slider(256, 4096, value=1024, step=256, label="Max Tokens")

                    with gr.Accordion("🎨 Widget Style", open=False):
                        primary_color = gr.ColorPicker(label="Primary Color", value="#3b82f6")
                        position = gr.Radio(
                            choices=["bottom-right", "bottom-left"],
                            value="bottom-right",
                            label="Position"
                        )
                        header_text = gr.Textbox(label="Header Text", value="Chat with us")

                # Center: Preview & Test
                with gr.Column(scale=2):
                    gr.Markdown("### Preview & Test")

                    # System prompt preview
                    with gr.Accordion("📝 System Prompt", open=True):
                        system_prompt_preview = gr.Textbox(
                            label="Generated System Prompt",
                            lines=10,
                            interactive=True
                        )
                        regenerate_prompt_btn = gr.Button("🔄 Regenerate", size="sm")

                    # Chat preview
                    gr.Markdown("### Test Chat")
                    chat_preview = gr.Chatbot(height=300, label="Test Conversation")
                    with gr.Row():
                        test_message = gr.Textbox(
                            placeholder="Type a test message...",
                            show_label=False,
                            scale=4
                        )
                        send_test_btn = gr.Button("Send", scale=1)

                    with gr.Row():
                        save_chatbot_btn = gr.Button("💾 Save Chatbot", variant="primary")
                        deploy_chatbot_btn = gr.Button("🚀 Deploy", variant="secondary")

                    chatbot_status = gr.Textbox(label="Status", interactive=False)

        # ==========================================
        # TAB 5: KNOWLEDGE BASE
        # ==========================================
        with gr.Tab("📚 Knowledge Base"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Knowledge Bases")
                    kb_list = gr.Dataframe(
                        headers=["ID", "Name", "Sources", "Chunks", "Status"],
                        value=[],
                        interactive=False
                    )

                with gr.Column(scale=2):
                    with gr.Tabs():
                        with gr.Tab("➕ Create"):
                            kb_name = gr.Textbox(label="Name", placeholder="Company FAQ")
                            kb_description = gr.Textbox(label="Description", lines=2)
                            create_kb_btn = gr.Button("Create Knowledge Base", variant="primary")

                        with gr.Tab("📄 Add Documents"):
                            kb_id_select = gr.Textbox(label="Knowledge Base ID")
                            doc_upload = gr.File(label="Upload Documents", file_count="multiple")
                            url_input = gr.Textbox(label="Or enter URLs (one per line)", lines=3)
                            process_docs_btn = gr.Button("Process Documents", variant="primary")

                        with gr.Tab("❓ FAQ Builder"):
                            faq_kb_id = gr.Textbox(label="Knowledge Base ID")
                            faq_question = gr.Textbox(label="Question")
                            faq_answer = gr.Textbox(label="Answer", lines=3)
                            add_faq_btn = gr.Button("Add FAQ", variant="primary")

                    kb_status = gr.Textbox(label="Status", interactive=False)

        # ==========================================
        # TAB 6: DEPLOYMENTS
        # ==========================================
        with gr.Tab("🚀 Deployments"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Active Deployments")
                    deployment_list = gr.Dataframe(
                        headers=["ID", "Chatbot", "Environment", "Status", "URL"],
                        value=[],
                        interactive=False
                    )

                with gr.Column(scale=2):
                    with gr.Tabs():
                        with gr.Tab("🔑 API Keys"):
                            api_deployment_id = gr.Textbox(label="Deployment ID")
                            api_key_name = gr.Textbox(label="Key Name", placeholder="Production API Key")
                            api_permissions = gr.CheckboxGroup(
                                choices=["chat", "history", "analytics", "settings"],
                                value=["chat"],
                                label="Permissions"
                            )
                            create_api_key_btn = gr.Button("Create API Key", variant="primary")
                            api_key_display = gr.Code(label="API Key (save this!)", language=None)

                        with gr.Tab("🔗 Embed Code"):
                            embed_deployment_id = gr.Textbox(label="Deployment ID")
                            embed_api_key = gr.Textbox(label="API Key")
                            embed_type = gr.Radio(
                                choices=["JavaScript", "React", "iframe", "Full Page"],
                                value="JavaScript",
                                label="Embed Type"
                            )
                            generate_embed_btn = gr.Button("Generate Code", variant="primary")
                            embed_code_output = gr.Code(label="Embed Code", language="html", lines=15)

                        with gr.Tab("🔔 Webhooks"):
                            wh_deployment_id = gr.Textbox(label="Deployment ID")
                            wh_name = gr.Textbox(label="Webhook Name")
                            wh_url = gr.Textbox(label="URL", placeholder="https://your-server.com/webhook")
                            wh_events = gr.CheckboxGroup(
                                choices=WebhookManager.EVENTS,
                                value=["conversation.started", "conversation.ended"],
                                label="Events"
                            )
                            create_webhook_btn = gr.Button("Create Webhook", variant="primary")
                            webhook_status = gr.Textbox(label="Status", interactive=False)

        # ==========================================
        # TAB 7: ANALYTICS
        # ==========================================
        with gr.Tab("📈 Analytics"):
            gr.Markdown("### Conversation Analytics")
            with gr.Row():
                analytics_deployment = gr.Dropdown(
                    choices=[],
                    label="Select Deployment"
                )
                analytics_range = gr.Radio(
                    choices=["Today", "7 Days", "30 Days", "All Time"],
                    value="7 Days",
                    label="Date Range"
                )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Total Conversations**")
                    total_convos = gr.Number(value=0, interactive=False)
                with gr.Column():
                    gr.Markdown("**Avg. Messages/Conversation**")
                    avg_messages = gr.Number(value=0, interactive=False)
                with gr.Column():
                    gr.Markdown("**Resolution Rate**")
                    resolution_rate = gr.Textbox(value="0%", interactive=False)
                with gr.Column():
                    gr.Markdown("**Satisfaction Score**")
                    satisfaction = gr.Textbox(value="N/A", interactive=False)

            gr.Markdown("### Recent Conversations")
            recent_convos = gr.Dataframe(
                headers=["ID", "Started", "Messages", "Resolved", "Rating"],
                value=[],
                interactive=False
            )

        # ==========================================
        # TAB 8: INTEGRATIONS
        # ==========================================
        with gr.Tab("🔌 Integrations"):
            gr.Markdown("### Available Integrations")

            integrations = get_available_integrations()
            with gr.Row():
                for integration in integrations[:3]:
                    with gr.Column():
                        gr.Markdown(f"**{integration['name']}**")
                        gr.Markdown(f"_{integration['description']}_")
                        gr.Button(f"Connect {integration['name']}", size="sm")

            with gr.Row():
                for integration in integrations[3:6]:
                    with gr.Column():
                        gr.Markdown(f"**{integration['name']}**")
                        gr.Markdown(f"_{integration['description']}_")
                        gr.Button(f"Connect {integration['name']}", size="sm")

        # ==========================================
        # TAB 9: BILLING
        # ==========================================
        with gr.Tab("💰 Billing"):
            gr.Markdown("### Revenue Overview")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Monthly Recurring Revenue**")
                    mrr_display = gr.Number(value=0, interactive=False, label="MRR ($)")
                with gr.Column():
                    gr.Markdown("**Active Subscriptions**")
                    active_subs = gr.Number(value=0, interactive=False, label="Subscriptions")

            gr.Markdown("### Client Billing")
            billing_table = gr.Dataframe(
                headers=["Client", "Plan", "Monthly ($)", "Usage", "Status"],
                value=[],
                interactive=False
            )

    # ==========================================
    # EVENT HANDLERS
    # ==========================================

    def add_new_client(company, ind, web, contact, email, tier, note):
        """Add a new client."""
        if not company:
            return "Please enter a company name"

        client = create_client(
            company_name=company,
            industry=ind or "",
            contact_name=contact,
            contact_email=email,
            pricing_tier=tier
        )
        client.website = web or ""
        client.notes = note or ""

        data_store.save_client(client)
        return f"Client '{company}' created with ID: {client.id}"

    def refresh_client_list():
        """Refresh the client list."""
        clients = data_store.get_clients()
        data = [[c["id"], c["company_name"], c["industry"], c["status"], c["pricing_tier"]]
                for c in clients]
        return data

    def load_client_details(client_id):
        """Load client details."""
        client = data_store.get_client(client_id)
        return client if client else {"error": "Client not found"}

    def update_persona_preview(persona_id):
        """Update persona preview."""
        persona = PERSONA_TEMPLATES.get(persona_id, {})
        if persona:
            preview = f"""
**{persona.get('name', 'Unknown')}**

*Tone:* {persona.get('tone', 'N/A')}

*Greeting:* {persona.get('greeting', '')}

*Traits:* {', '.join(persona.get('personality_traits', []))}
            """
            return preview
        return "*Select a persona*"

    def generate_system_prompt(company_name, persona_id, industry):
        """Generate system prompt from settings."""
        industry_info = INDUSTRY_PRESETS.get(industry, {})
        context = f"{company_name} is a company in the {industry_info.get('name', industry)} industry."
        return chat_builder.build_system_prompt(persona_id, company_name, context)

    def generate_embed_code(deployment_id, api_key, embed_type):
        """Generate embed code."""
        if not deployment_id or not api_key:
            return "Please provide deployment ID and API key"

        config = {"primary_color": "#3b82f6", "header_text": "Chat with us"}

        if embed_type == "JavaScript":
            return embed_generator.generate_embed_code(deployment_id, api_key, config)
        elif embed_type == "React":
            return embed_generator.generate_react_component(deployment_id, api_key, config)
        elif embed_type == "iframe":
            return embed_generator.generate_iframe_embed(deployment_id)
        elif embed_type == "Full Page":
            return embed_generator.generate_full_page_chat(deployment_id, api_key, config)
        return ""

    def create_new_api_key(deployment_id, name, permissions):
        """Create a new API key."""
        if not deployment_id or not name:
            return "Please provide deployment ID and key name"

        key = api_manager.create_key(
            name=name,
            deployment_id=deployment_id,
            permissions=permissions
        )
        return f"API Key created!\n\n{key.key}\n\n⚠️ Save this key - it won't be shown again!"

    def create_new_webhook(deployment_id, name, url, events):
        """Create a new webhook."""
        if not deployment_id or not name or not url:
            return "Please provide all required fields"

        webhook = webhook_manager.create_webhook(
            name=name,
            url=url,
            deployment_id=deployment_id,
            events=events
        )
        return f"Webhook created! ID: {webhook.id}\nSecret: {webhook.secret}"

    # Wire up events
    add_client_btn.click(
        add_new_client,
        inputs=[company_name, industry, website, contact_name, contact_email, pricing_tier, notes],
        outputs=[add_client_status]
    )

    refresh_clients_btn.click(refresh_client_list, outputs=[client_list])
    load_client_btn.click(load_client_details, inputs=[client_id_input], outputs=[client_details])

    persona_select.change(update_persona_preview, inputs=[persona_select], outputs=[persona_preview])

    regenerate_prompt_btn.click(
        generate_system_prompt,
        inputs=[cb_company_name, persona_select, cb_industry],
        outputs=[system_prompt_preview]
    )

    generate_embed_btn.click(
        generate_embed_code,
        inputs=[embed_deployment_id, embed_api_key, embed_type],
        outputs=[embed_code_output]
    )

    create_api_key_btn.click(
        create_new_api_key,
        inputs=[api_deployment_id, api_key_name, api_permissions],
        outputs=[api_key_display]
    )

    create_webhook_btn.click(
        create_new_webhook,
        inputs=[wh_deployment_id, wh_name, wh_url, wh_events],
        outputs=[webhook_status]
    )
