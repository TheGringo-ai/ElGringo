"""
Export & Deliverable Tools
==========================

Package projects for client handoff with documentation.
"""

import os
import zipfile
from datetime import datetime
from typing import Dict, List, Any


class ProjectExporter:
    """Export projects for client delivery."""

    def __init__(self):
        self.export_dir = os.path.expanduser("~/.ai-dev-team/exports")
        os.makedirs(self.export_dir, exist_ok=True)

    def export_to_zip(self, project_path: str, include_docs: bool = True,
                     include_git: bool = False) -> Dict[str, Any]:
        """Export project to a ZIP file."""
        try:
            project_path = os.path.expanduser(project_path)
            if not os.path.isdir(project_path):
                return {"success": False, "error": "Project directory not found"}

            project_name = os.path.basename(project_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"{project_name}_{timestamp}.zip"
            zip_path = os.path.join(self.export_dir, zip_name)

            # Files/folders to exclude
            exclude = {'.git', '__pycache__', 'node_modules', '.env', '.venv',
                      'venv', '.DS_Store', '*.pyc', '.idea', '.vscode'}
            if not include_git:
                exclude.add('.git')

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(project_path):
                    # Filter directories
                    dirs[:] = [d for d in dirs if d not in exclude]

                    for file in files:
                        if file in exclude or file.endswith('.pyc'):
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, project_path)
                        zipf.write(file_path, arcname)

                # Add handoff documentation if requested
                if include_docs:
                    readme = self._generate_handoff_readme(project_path, project_name)
                    zipf.writestr("HANDOFF_README.md", readme)

            file_size = os.path.getsize(zip_path)
            return {
                "success": True,
                "zip_path": zip_path,
                "zip_name": zip_name,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_handoff_readme(self, project_path: str, project_name: str) -> str:
        """Generate handoff documentation."""
        # Detect project type
        has_package_json = os.path.exists(os.path.join(project_path, "package.json"))
        has_requirements = os.path.exists(os.path.join(project_path, "requirements.txt"))
        has_dockerfile = os.path.exists(os.path.join(project_path, "Dockerfile"))
        has_firebase = os.path.exists(os.path.join(project_path, "firebase.json"))

        readme = f"""# {project_name} - Project Handoff

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Project Overview

This package contains the complete source code for {project_name}.

## Quick Start

"""
        if has_package_json:
            readme += """### Node.js Project

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

"""

        if has_requirements:
            readme += """### Python Project

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

"""

        if has_dockerfile:
            readme += f"""### Docker

```bash
# Build image
docker build -t {project_name.lower()} .

# Run container
docker run -p 8080:8080 {project_name.lower()}
```

"""

        if has_firebase:
            readme += """### Firebase Deployment

```bash
# Login to Firebase
firebase login

# Deploy
firebase deploy
```

"""

        readme += """## Environment Variables

Create a `.env` file with the following variables:

```
# Add your environment variables here
```

## Support

For questions or issues, contact your development team.

---
*Created with AI Team Studio*
"""
        return readme

    def generate_invoice_package(self, project_path: str, client_name: str,
                                project_name: str, hours: float,
                                hourly_rate: float = 150.0) -> Dict[str, Any]:
        """Generate an invoice-ready package."""
        try:
            # Export project
            export_result = self.export_to_zip(project_path, include_docs=True)
            if not export_result["success"]:
                return export_result

            # Generate invoice
            total = hours * hourly_rate
            invoice = f"""# Invoice

**Client:** {client_name}
**Project:** {project_name}
**Date:** {datetime.now().strftime("%Y-%m-%d")}

## Services

| Description | Hours | Rate | Amount |
|-------------|-------|------|--------|
| Development | {hours} | ${hourly_rate}/hr | ${total:,.2f} |

**Total Due: ${total:,.2f}**

## Deliverables

- Complete source code ({export_result['zip_name']})
- Documentation
- Deployment instructions

## Payment Terms

Net 30 days

---
*Thank you for your business!*
"""
            # Save invoice
            invoice_path = os.path.join(self.export_dir, f"invoice_{project_name}_{datetime.now().strftime('%Y%m%d')}.md")
            with open(invoice_path, 'w') as f:
                f.write(invoice)

            return {
                "success": True,
                "zip_path": export_result["zip_path"],
                "invoice_path": invoice_path,
                "total": total
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class DeploymentGuideGenerator:
    """Generate deployment guides for different platforms."""

    GUIDES = {
        "firebase_hosting": """# Deploy to Firebase Hosting

## Prerequisites
- Firebase CLI installed: `npm install -g firebase-tools`
- Firebase project created at https://console.firebase.google.com

## Steps

1. Login to Firebase:
```bash
firebase login
```

2. Initialize hosting:
```bash
firebase init hosting
```

3. Select your project and set the public directory.

4. Deploy:
```bash
firebase deploy --only hosting
```

Your site will be live at: `https://your-project.web.app`
""",

        "cloud_run": """# Deploy to Google Cloud Run

## Prerequisites
- Google Cloud SDK installed
- Project created in GCP Console
- Billing enabled

## Steps

1. Login to GCP:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2. Enable Cloud Run:
```bash
gcloud services enable run.googleapis.com
```

3. Deploy from source:
```bash
gcloud run deploy SERVICE_NAME --source . --region us-central1 --allow-unauthenticated
```

Your service will be live at the provided URL.
""",

        "cloud_functions": """# Deploy to Google Cloud Functions

## Prerequisites
- Google Cloud SDK installed
- Functions Framework installed: `pip install functions-framework`

## Steps

1. Login to GCP:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2. Enable Cloud Functions:
```bash
gcloud services enable cloudfunctions.googleapis.com
```

3. Deploy:
```bash
gcloud functions deploy FUNCTION_NAME \\
    --gen2 \\
    --runtime=python311 \\
    --region=us-central1 \\
    --source=. \\
    --entry-point=FUNCTION_NAME \\
    --trigger-http \\
    --allow-unauthenticated
```
""",

        "vercel": """# Deploy to Vercel

## Prerequisites
- Vercel CLI installed: `npm install -g vercel`
- Vercel account created

## Steps

1. Login to Vercel:
```bash
vercel login
```

2. Deploy:
```bash
vercel
```

3. For production:
```bash
vercel --prod
```

Your site will be live at: `https://your-project.vercel.app`
""",

        "docker_vm": """# Deploy to VM with Docker

## Prerequisites
- VM with Docker installed
- SSH access to VM

## Steps

1. Build Docker image:
```bash
docker build -t myapp .
```

2. Save image:
```bash
docker save myapp > myapp.tar
```

3. Copy to VM:
```bash
scp myapp.tar user@vm-ip:/home/user/
```

4. On VM, load and run:
```bash
docker load < myapp.tar
docker run -d -p 80:8080 --restart always myapp
```
"""
    }

    def get_guide(self, platform: str) -> str:
        """Get deployment guide for a platform."""
        return self.GUIDES.get(platform, f"No guide available for {platform}")

    def list_platforms(self) -> List[str]:
        """List available deployment platforms."""
        return list(self.GUIDES.keys())


def export_project(project_path: str) -> Dict:
    """Quick function to export a project."""
    exporter = ProjectExporter()
    return exporter.export_to_zip(project_path)
