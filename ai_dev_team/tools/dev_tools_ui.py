"""
Developer Tools UI
==================

Gradio UI for project scaffolding, deployment, and export.
"""

import gradio as gr
import os
import subprocess
from typing import Dict, List, Any

from .scaffolding import ProjectScaffolder, PROJECT_TEMPLATES
from .quick_deploy import QuickDeployer
from .export import ProjectExporter, DeploymentGuideGenerator


def create_dev_tools_ui():
    """Create the Developer Tools panel UI."""

    scaffolder = ProjectScaffolder()
    deployer = QuickDeployer()
    exporter = ProjectExporter()
    guide_gen = DeploymentGuideGenerator()

    gr.HTML("""
    <style>
        .template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
        .template-card {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .template-card:hover {
            border-color: #3b82f6;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }
        .deploy-status {
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0;
        }
        .deploy-success { background: #dcfce7; color: #166534; }
        .deploy-error { background: #fee2e2; color: #991b1b; }
    </style>
    """)

    gr.Markdown("## Developer Tools")
    gr.Markdown("*Create, Deploy, and Export projects with one click*")

    # Check available tools
    tools = deployer.check_tools()
    tool_status = " • ".join([f"{'✅' if v else '❌'} {k}" for k, v in tools.items()])
    gr.Markdown(f"**Available Tools:** {tool_status}")

    with gr.Tabs():
        # ==========================================
        # TAB 1: NEW PROJECT
        # ==========================================
        with gr.Tab("🚀 New Project"):
            gr.Markdown("### Create a New Project")

            with gr.Row():
                with gr.Column(scale=1):
                    template_select = gr.Radio(
                        choices=[(f"{t['icon']} {t['name']}", k) for k, t in PROJECT_TEMPLATES.items()],
                        label="Project Template",
                        value="landing_page"
                    )

                with gr.Column(scale=2):
                    template_info = gr.Markdown("""
**Landing Page**
- Single page marketing site with contact form
- Tech: HTML, Tailwind CSS, JavaScript
- Deploy to: Firebase Hosting, Vercel, Netlify
- Estimated time: 1-2 hours
- Price range: $500-$1500
                    """)

            with gr.Row():
                project_name_input = gr.Textbox(
                    label="Project Name",
                    placeholder="my-awesome-project",
                    value=""
                )
                project_dir = gr.Textbox(
                    label="Output Directory (optional)",
                    placeholder="Leave blank for ~/Development/Projects/",
                    value=""
                )

            create_btn = gr.Button("🚀 Create Project", variant="primary", size="lg")

            create_output = gr.Markdown("")
            next_steps_output = gr.Code(label="Next Steps", language="shell", lines=10)

        # ==========================================
        # TAB 2: DEPLOY
        # ==========================================
        with gr.Tab("☁️ Deploy"):
            gr.Markdown("### Deploy Your Project")

            with gr.Row():
                deploy_path = gr.Textbox(
                    label="Project Path",
                    placeholder="/Users/you/Development/Projects/my-project",
                    value=""
                )
                scan_btn = gr.Button("🔍 Scan", size="sm")

            deploy_targets = gr.Radio(
                choices=[],
                label="Available Deployment Targets",
                visible=False
            )

            with gr.Row():
                with gr.Column():
                    service_name = gr.Textbox(label="Service Name (for Cloud Run)", visible=False)
                    region = gr.Dropdown(
                        choices=["us-central1", "us-east1", "us-west1", "europe-west1", "asia-east1"],
                        value="us-central1",
                        label="Region",
                        visible=False
                    )

            deploy_btn = gr.Button("🚀 Deploy Now", variant="primary", size="lg")

            deploy_output = gr.Markdown("")
            deploy_url = gr.Textbox(label="Deployment URL", interactive=False, visible=False)

        # ==========================================
        # TAB 3: EXPORT
        # ==========================================
        with gr.Tab("📦 Export"):
            gr.Markdown("### Export for Client Delivery")

            export_path = gr.Textbox(
                label="Project Path",
                placeholder="/Users/you/Development/Projects/my-project"
            )

            with gr.Row():
                include_docs = gr.Checkbox(label="Include Handoff Documentation", value=True)
                include_git = gr.Checkbox(label="Include .git folder", value=False)

            export_btn = gr.Button("📦 Create ZIP", variant="primary")

            export_output = gr.Markdown("")
            export_download = gr.File(label="Download", visible=False)

            gr.Markdown("---")
            gr.Markdown("### Invoice Package")

            with gr.Row():
                client_name = gr.Textbox(label="Client Name", placeholder="Acme Corp")
                hours_worked = gr.Number(label="Hours Worked", value=10)
                hourly_rate = gr.Number(label="Hourly Rate ($)", value=150)

            invoice_btn = gr.Button("📄 Generate Invoice Package")
            invoice_output = gr.Markdown("")

        # ==========================================
        # TAB 4: DEPLOYMENT GUIDES
        # ==========================================
        with gr.Tab("📚 Guides"):
            gr.Markdown("### Deployment Guides")

            guide_select = gr.Dropdown(
                choices=guide_gen.list_platforms(),
                label="Select Platform",
                value="firebase_hosting"
            )

            guide_content = gr.Markdown(guide_gen.get_guide("firebase_hosting"))

        # ==========================================
        # TAB 5: QUICK COMMANDS
        # ==========================================
        with gr.Tab("⚡ Quick Commands"):
            gr.Markdown("### Useful Commands")

            cmd_category = gr.Radio(
                choices=["Firebase", "Google Cloud", "Docker", "npm/Node", "Python"],
                value="Firebase",
                label="Category"
            )

            commands_display = gr.Code(
                value="""# Firebase Commands

# Login
firebase login

# Initialize project
firebase init

# Deploy hosting
firebase deploy --only hosting

# Deploy functions
firebase deploy --only functions

# View logs
firebase functions:log
""",
                language="shell",
                label="Commands",
                lines=15
            )

            with gr.Row():
                cmd_input = gr.Textbox(label="Run Command", placeholder="Enter command to run...")
                run_cmd_btn = gr.Button("▶️ Run", variant="primary")

            cmd_output = gr.Code(label="Output", language="shell", lines=10)

    # ==========================================
    # EVENT HANDLERS
    # ==========================================

    def update_template_info(template_id):
        """Update template info display."""
        t = PROJECT_TEMPLATES.get(template_id, {})
        info = f"""
**{t.get('name', 'Unknown')}**
- {t.get('description', '')}
- **Tech:** {', '.join(t.get('tech', []))}
- **Deploy to:** {', '.join(t.get('deploy_to', []))}
- **Estimated time:** {t.get('estimated_time', 'Unknown')}
- **Price range:** {t.get('price_range', 'Custom')}
        """
        return info

    def create_project(template_id, name, output_dir):
        """Create a new project."""
        if not name:
            return "❌ Please enter a project name", ""

        result = scaffolder.create_project(
            template_id,
            name,
            output_dir if output_dir else None
        )

        if result["success"]:
            msg = f"""
✅ **Project Created Successfully!**

- **Name:** {result['project_name']}
- **Template:** {result['template']}
- **Location:** `{result['output_dir']}`
- **Files:** {', '.join(result['files_created'])}
            """

            steps = "\n".join(result.get("next_steps", []))
            return msg, steps
        else:
            return f"❌ Error: {result['error']}", ""

    def scan_deploy_targets(project_path):
        """Scan project for deployment targets."""
        if not project_path or not os.path.isdir(project_path):
            return gr.Radio(choices=[], visible=False), gr.update(visible=False), gr.update(visible=False)

        targets = deployer.get_available_targets(project_path)

        if not targets:
            return gr.Radio(choices=[], visible=False), gr.update(visible=False), gr.update(visible=False)

        choices = [(f"{t['icon']} {t['name']} {'✅' if t['ready'] else '⚠️ Setup needed'}", t['id']) for t in targets]

        show_cloud_options = any(t['id'] in ['cloud_run', 'cloud_functions'] for t in targets)

        return (
            gr.Radio(choices=choices, visible=True, value=choices[0][1] if choices else None),
            gr.update(visible=show_cloud_options),
            gr.update(visible=show_cloud_options)
        )

    def run_deploy(project_path, target, svc_name, reg):
        """Run deployment."""
        if not project_path or not target:
            return "❌ Please select a project and target", gr.update(visible=False)

        options = {}
        if svc_name:
            options["service_name"] = svc_name
        if reg:
            options["region"] = reg

        result = deployer.deploy(project_path, target, options)

        if result["success"]:
            url = result.get("url", "")
            msg = f"""
✅ **Deployment Successful!**

- **Platform:** {result.get('platform', target)}
- **URL:** {url}

{result.get('output', '')[:500]}
            """
            return msg, gr.Textbox(value=url, visible=bool(url))
        else:
            return f"❌ **Deployment Failed**\n\n{result.get('error', 'Unknown error')}", gr.update(visible=False)

    def run_export(project_path, include_d, include_g):
        """Export project to ZIP."""
        if not project_path:
            return "❌ Please enter a project path", gr.update(visible=False)

        result = exporter.export_to_zip(project_path, include_d, include_g)

        if result["success"]:
            msg = f"""
✅ **Export Successful!**

- **File:** {result['zip_name']}
- **Size:** {result['size_mb']} MB
- **Location:** {result['zip_path']}
            """
            return msg, gr.File(value=result['zip_path'], visible=True)
        else:
            return f"❌ Error: {result['error']}", gr.update(visible=False)

    def generate_invoice(project_path, client, hours, rate):
        """Generate invoice package."""
        if not project_path or not client:
            return "❌ Please enter project path and client name"

        result = exporter.generate_invoice_package(project_path, client, os.path.basename(project_path), hours, rate)

        if result["success"]:
            return f"""
✅ **Invoice Package Created!**

- **ZIP:** {result['zip_path']}
- **Invoice:** {result['invoice_path']}
- **Total:** ${result['total']:,.2f}
            """
        else:
            return f"❌ Error: {result['error']}"

    def update_guide(platform):
        """Update deployment guide."""
        return guide_gen.get_guide(platform)

    def update_commands(category):
        """Update quick commands display."""
        commands = {
            "Firebase": """# Firebase Commands

# Login
firebase login

# Initialize project
firebase init

# Deploy hosting
firebase deploy --only hosting

# Deploy functions
firebase deploy --only functions

# View logs
firebase functions:log

# Emulators
firebase emulators:start
""",
            "Google Cloud": """# Google Cloud Commands

# Login
gcloud auth login

# Set project
gcloud config set project PROJECT_ID

# Deploy to Cloud Run
gcloud run deploy SERVICE --source . --region us-central1

# Deploy Cloud Function
gcloud functions deploy FUNCTION --gen2 --runtime python311 --trigger-http

# View logs
gcloud logging read "resource.type=cloud_run_revision"

# List services
gcloud run services list
""",
            "Docker": """# Docker Commands

# Build image
docker build -t myapp .

# Run container
docker run -p 8080:8080 myapp

# Run detached
docker run -d -p 8080:8080 --name myapp myapp

# View running containers
docker ps

# Stop container
docker stop myapp

# View logs
docker logs myapp

# Remove container
docker rm myapp
""",
            "npm/Node": """# npm/Node Commands

# Create React app
npm create vite@latest my-app -- --template react-ts

# Create Next.js app
npx create-next-app@latest my-app

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Deploy to Vercel
vercel --prod
""",
            "Python": """# Python Commands

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI
uvicorn main:app --reload

# Run Flask
flask run

# Format code
ruff format .

# Lint code
ruff check .

# Run tests
pytest
"""
        }
        return commands.get(category, "")

    def run_command(cmd):
        """Run a shell command."""
        if not cmd:
            return ""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\n\nSTDERR:\n{result.stderr}"
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error: {e}"

    # Wire up events
    template_select.change(update_template_info, inputs=[template_select], outputs=[template_info])
    create_btn.click(create_project, inputs=[template_select, project_name_input, project_dir], outputs=[create_output, next_steps_output])

    scan_btn.click(scan_deploy_targets, inputs=[deploy_path], outputs=[deploy_targets, service_name, region])
    deploy_btn.click(run_deploy, inputs=[deploy_path, deploy_targets, service_name, region], outputs=[deploy_output, deploy_url])

    export_btn.click(run_export, inputs=[export_path, include_docs, include_git], outputs=[export_output, export_download])
    invoice_btn.click(generate_invoice, inputs=[export_path, client_name, hours_worked, hourly_rate], outputs=[invoice_output])

    guide_select.change(update_guide, inputs=[guide_select], outputs=[guide_content])
    cmd_category.change(update_commands, inputs=[cmd_category], outputs=[commands_display])
    run_cmd_btn.click(run_command, inputs=[cmd_input], outputs=[cmd_output])
