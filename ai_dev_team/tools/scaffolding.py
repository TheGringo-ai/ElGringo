"""
Project Scaffolding
===================

One-click project generation with best practices baked in.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


# ============================================================
# PROJECT TEMPLATES
# ============================================================

PROJECT_TEMPLATES = {
    "landing_page": {
        "name": "Landing Page",
        "description": "Single page marketing site with contact form",
        "icon": "🌐",
        "tech": ["HTML", "Tailwind CSS", "JavaScript"],
        "deploy_to": ["Firebase Hosting", "Vercel", "Netlify"],
        "estimated_time": "1-2 hours",
        "price_range": "$500-$1500",
        "files": {
            "index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <!-- Hero Section -->
    <section class="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-20">
        <div class="container mx-auto px-6 text-center">
            <h1 class="text-5xl font-bold mb-4">{project_name}</h1>
            <p class="text-xl mb-8">Your compelling tagline goes here</p>
            <a href="#contact" class="bg-white text-blue-600 px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition">
                Get Started
            </a>
        </div>
    </section>

    <!-- Features Section -->
    <section class="py-20">
        <div class="container mx-auto px-6">
            <h2 class="text-3xl font-bold text-center mb-12">Features</h2>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="text-4xl mb-4">⚡</div>
                    <h3 class="text-xl font-semibold mb-2">Fast</h3>
                    <p class="text-gray-600">Lightning fast performance</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="text-4xl mb-4">🔒</div>
                    <h3 class="text-xl font-semibold mb-2">Secure</h3>
                    <p class="text-gray-600">Enterprise-grade security</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="text-4xl mb-4">📈</div>
                    <h3 class="text-xl font-semibold mb-2">Scalable</h3>
                    <p class="text-gray-600">Grows with your business</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact Section -->
    <section id="contact" class="bg-gray-100 py-20">
        <div class="container mx-auto px-6 max-w-md">
            <h2 class="text-3xl font-bold text-center mb-8">Contact Us</h2>
            <form class="space-y-4">
                <input type="text" placeholder="Name" class="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none">
                <input type="email" placeholder="Email" class="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none">
                <textarea placeholder="Message" rows="4" class="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none"></textarea>
                <button type="submit" class="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition">
                    Send Message
                </button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-8">
        <div class="container mx-auto px-6 text-center">
            <p>&copy; {year} {project_name}. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>''',
            "firebase.json": '''{
  "hosting": {
    "public": ".",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {"source": "**", "destination": "/index.html"}
    ]
  }
}''',
            "README.md": '''# {project_name}

Landing page created with AI Team Studio.

## Deploy to Firebase

```bash
firebase login
firebase init hosting
firebase deploy
```

## Deploy to Vercel

```bash
vercel
```
'''
        }
    },

    "react_app": {
        "name": "React Web App",
        "description": "React + Vite + Tailwind + Firebase Auth",
        "icon": "⚛️",
        "tech": ["React", "Vite", "Tailwind CSS", "Firebase"],
        "deploy_to": ["Firebase Hosting", "Vercel", "Netlify"],
        "estimated_time": "4-8 hours",
        "price_range": "$2000-$5000",
        "command": "npm create vite@latest {name} -- --template react-ts && cd {name} && npm install && npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p",
        "post_commands": [
            "npm install firebase",
            "npm install react-router-dom"
        ],
        "files": {
            "src/App.tsx": '''import { BrowserRouter, Routes, Route } from 'react-router-dom';

function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">{project_name}</h1>
        <p className="text-gray-600">Welcome to your new React app!</p>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
''',
            "src/index.css": '''@tailwind base;
@tailwind components;
@tailwind utilities;
''',
            "tailwind.config.js": '''/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
''',
            "firebase.json": '''{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{"source": "**", "destination": "/index.html"}]
  }
}'''
        }
    },

    "nextjs_app": {
        "name": "Next.js Full Stack",
        "description": "Next.js 14 + App Router + Tailwind + Firebase",
        "icon": "▲",
        "tech": ["Next.js", "TypeScript", "Tailwind CSS", "Firebase"],
        "deploy_to": ["Vercel", "Cloud Run"],
        "estimated_time": "8-16 hours",
        "price_range": "$3000-$10000",
        "command": "npx create-next-app@latest {name} --typescript --tailwind --app --src-dir --import-alias '@/*'",
        "post_commands": [
            "npm install firebase firebase-admin"
        ],
        "files": {
            "src/app/page.tsx": '''export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 text-white">
      <div className="container mx-auto px-6 py-20">
        <h1 className="text-5xl font-bold mb-6">{project_name}</h1>
        <p className="text-xl text-gray-300">Built with Next.js and Firebase</p>
      </div>
    </main>
  );
}
''',
            "src/lib/firebase.ts": '''import { initializeApp, getApps } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
};

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const db = getFirestore(app);
export const auth = getAuth(app);
''',
            ".env.local.example": '''NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
'''
        }
    },

    "fastapi_backend": {
        "name": "FastAPI Backend",
        "description": "FastAPI + SQLite/Postgres + Auth + Docker",
        "icon": "🚀",
        "tech": ["Python", "FastAPI", "SQLModel", "Docker"],
        "deploy_to": ["Cloud Run", "App Engine", "VM"],
        "estimated_time": "4-8 hours",
        "price_range": "$1500-$4000",
        "files": {
            "main.py": '''from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="{project_name} API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

# In-memory storage (replace with database)
items: List[Item] = []

@app.get("/")
async def root():
    return {"message": "Welcome to {project_name} API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/items", response_model=List[Item])
async def get_items():
    return items

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    item.id = len(items) + 1
    items.append(item)
    return item

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
            "requirements.txt": '''fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
python-multipart
''',
            "Dockerfile": '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
            ".dockerignore": '''__pycache__
*.pyc
.env
.git
''',
            "README.md": '''# {project_name} API

FastAPI backend service.

## Run Locally

```bash
pip install -r requirements.txt
python main.py
```

## Run with Docker

```bash
docker build -t {project_name_lower} .
docker run -p 8000:8000 {project_name_lower}
```

## Deploy to Cloud Run

```bash
gcloud run deploy {project_name_lower} --source . --region us-central1
```
'''
        }
    },

    "cloud_function": {
        "name": "Cloud Function",
        "description": "GCP Cloud Function with HTTP trigger",
        "icon": "⚡",
        "tech": ["Python", "Functions Framework"],
        "deploy_to": ["Cloud Functions"],
        "estimated_time": "1-2 hours",
        "price_range": "$300-$800",
        "files": {
            "main.py": '''import functions_framework
from flask import jsonify
import json

@functions_framework.http
def {function_name}(request):
    """HTTP Cloud Function.

    Args:
        request (flask.Request): The request object.
    Returns:
        Response object with JSON data.
    """
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        # Get request data
        request_json = request.get_json(silent=True)
        request_args = request.args

        # Your logic here
        result = {
            "status": "success",
            "message": "Hello from {project_name}!",
            "data": request_json or dict(request_args)
        }

        return (jsonify(result), 200, headers)

    except Exception as e:
        return (jsonify({"error": str(e)}), 500, headers)
''',
            "requirements.txt": '''functions-framework==3.*
flask>=2.0.0
''',
            "deploy.sh": '''#!/bin/bash
gcloud functions deploy {function_name} \\
    --gen2 \\
    --runtime=python311 \\
    --region=us-central1 \\
    --source=. \\
    --entry-point={function_name} \\
    --trigger-http \\
    --allow-unauthenticated
''',
            "README.md": '''# {project_name}

Google Cloud Function with HTTP trigger.

## Test Locally

```bash
pip install functions-framework
functions-framework --target={function_name} --debug
```

## Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```
'''
        }
    },

    "chatbot_widget": {
        "name": "AI Chatbot Widget",
        "description": "Embeddable AI chat widget for websites",
        "icon": "🤖",
        "tech": ["TypeScript", "Firebase", "OpenAI/Claude"],
        "deploy_to": ["Firebase Hosting", "Vercel"],
        "estimated_time": "4-8 hours",
        "price_range": "$1500-$3000",
        "files": {
            "index.html": '''<!DOCTYPE html>
<html>
<head>
    <title>{project_name} Chat Widget</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }

        .chat-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 380px;
            height: 500px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 5px 40px rgba(0,0,0,0.16);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 20px;
        }

        .chat-header h3 { font-size: 16px; font-weight: 600; }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .message {
            margin-bottom: 12px;
            max-width: 80%;
        }

        .message.user {
            margin-left: auto;
            background: #667eea;
            color: white;
            padding: 10px 14px;
            border-radius: 18px 18px 4px 18px;
        }

        .message.assistant {
            background: #f1f3f4;
            padding: 10px 14px;
            border-radius: 18px 18px 18px 4px;
        }

        .chat-input {
            padding: 12px 16px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 8px;
        }

        .chat-input input {
            flex: 1;
            border: 1px solid #ddd;
            border-radius: 24px;
            padding: 10px 16px;
            outline: none;
        }

        .chat-input button {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="chat-widget">
        <div class="chat-header">
            <h3>{project_name}</h3>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message assistant">Hi! How can I help you today?</div>
        </div>
        <div class="chat-input">
            <input type="text" id="input" placeholder="Type a message..." />
            <button onclick="sendMessage()">→</button>
        </div>
    </div>

    <script>
        async function sendMessage() {
            const input = document.getElementById('input');
            const messages = document.getElementById('messages');
            const text = input.value.trim();
            if (!text) return;

            // Add user message
            messages.innerHTML += `<div class="message user">${text}</div>`;
            input.value = '';
            messages.scrollTop = messages.scrollHeight;

            // TODO: Call your AI API here
            // const response = await fetch('/api/chat', { ... });

            // Mock response
            setTimeout(() => {
                messages.innerHTML += `<div class="message assistant">Thanks for your message! This is a demo response.</div>`;
                messages.scrollTop = messages.scrollHeight;
            }, 1000);
        }

        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>''',
            "api/chat.py": '''# Cloud Function for chat API
import functions_framework
from flask import jsonify
import os

# TODO: Add your AI provider (OpenAI, Anthropic, etc.)
# import openai
# openai.api_key = os.environ.get("OPENAI_API_KEY")

@functions_framework.http
def chat(request):
    """Process chat messages."""
    if request.method == 'OPTIONS':
        return ('', 204, {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST'})

    data = request.get_json()
    message = data.get('message', '')

    # TODO: Call your AI API
    # response = openai.ChatCompletion.create(...)

    # Mock response
    reply = f"You said: {message}. This is a demo response."

    return (jsonify({"reply": reply}), 200, {'Access-Control-Allow-Origin': '*'})
''',
            "firebase.json": '''{
  "hosting": {
    "public": ".",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**", "api/**"]
  },
  "functions": {
    "source": "api"
  }
}'''
        }
    },

    "api_microservice": {
        "name": "API Microservice",
        "description": "REST API microservice ready for Cloud Run",
        "icon": "🔌",
        "tech": ["Python", "FastAPI", "Docker", "Cloud Run"],
        "deploy_to": ["Cloud Run"],
        "estimated_time": "2-4 hours",
        "price_range": "$800-$2000",
        "files": {
            "main.py": '''from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(
    title="{project_name} API",
    description="Microservice API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "{project_name}"}

# API routes
@app.get("/api/v1/")
async def api_root():
    return {"message": "Welcome to {project_name} API v1"}

# TODO: Add your endpoints here

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
''',
            "requirements.txt": '''fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
''',
            "Dockerfile": '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
''',
            "cloudbuild.yaml": '''steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/{project_name_lower}', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/{project_name_lower}']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '{project_name_lower}'
      - '--image'
      - 'gcr.io/$PROJECT_ID/{project_name_lower}'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
'''
        }
    }
}


class ProjectScaffolder:
    """Scaffolds new projects from templates."""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.expanduser("~/Development/Projects")
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def list_templates(self) -> List[Dict]:
        """List available project templates."""
        return [
            {
                "id": key,
                "name": template["name"],
                "description": template["description"],
                "icon": template["icon"],
                "tech": template["tech"],
                "deploy_to": template["deploy_to"],
                "estimated_time": template.get("estimated_time", "Unknown"),
                "price_range": template.get("price_range", "Custom"),
            }
            for key, template in PROJECT_TEMPLATES.items()
        ]

    def create_project(self, template_id: str, project_name: str,
                      output_dir: str = None) -> Dict[str, Any]:
        """Create a new project from template."""
        if template_id not in PROJECT_TEMPLATES:
            return {"success": False, "error": f"Template '{template_id}' not found"}

        template = PROJECT_TEMPLATES[template_id]

        # Prepare project directory
        project_name_lower = project_name.lower().replace(" ", "-").replace("_", "-")
        if output_dir is None:
            output_dir = os.path.join(self.base_dir, project_name_lower)

        try:
            os.makedirs(output_dir, exist_ok=True)

            # Substitution variables
            year = datetime.now().year
            function_name = project_name_lower.replace("-", "_")
            substitutions = {
                "{project_name}": project_name,
                "{project_name_lower}": project_name_lower,
                "{function_name}": function_name,
                "{year}": str(year),
            }

            # Create files from template
            files_created = []
            for filename, content in template.get("files", {}).items():
                # Apply substitutions
                for key, value in substitutions.items():
                    content = content.replace(key, value)
                    filename = filename.replace(key, value)

                filepath = os.path.join(output_dir, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None

                with open(filepath, 'w') as f:
                    f.write(content)
                files_created.append(filename)

            # Run setup command if specified
            command = template.get("command")
            if command:
                command = command.format(name=project_name_lower)

            result = {
                "success": True,
                "project_name": project_name,
                "output_dir": output_dir,
                "template": template["name"],
                "files_created": files_created,
                "setup_command": command,
                "post_commands": template.get("post_commands", []),
                "deploy_to": template["deploy_to"],
                "next_steps": self._get_next_steps(template_id, project_name_lower, output_dir)
            }

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_next_steps(self, template_id: str, project_name: str, output_dir: str) -> List[str]:
        """Get next steps for the created project."""
        steps = [f"cd {output_dir}"]

        if template_id == "landing_page":
            steps.extend([
                "# Preview locally:",
                "python -m http.server 8000",
                "# Deploy to Firebase:",
                "firebase login && firebase init hosting && firebase deploy"
            ])
        elif template_id in ["react_app", "nextjs_app"]:
            steps.extend([
                "npm install",
                "npm run dev",
                "# Deploy to Vercel:",
                "vercel"
            ])
        elif template_id == "fastapi_backend":
            steps.extend([
                "pip install -r requirements.txt",
                "python main.py",
                "# Deploy to Cloud Run:",
                f"gcloud run deploy {project_name} --source . --region us-central1"
            ])
        elif template_id == "cloud_function":
            steps.extend([
                "pip install -r requirements.txt",
                "# Test locally:",
                f"functions-framework --target={project_name.replace('-', '_')} --debug",
                "# Deploy:",
                "chmod +x deploy.sh && ./deploy.sh"
            ])
        elif template_id == "api_microservice":
            steps.extend([
                "pip install -r requirements.txt",
                "python main.py",
                "# Deploy with Cloud Build:",
                "gcloud builds submit"
            ])

        return steps


# Helper function for quick access
def scaffold_project(template_id: str, project_name: str, output_dir: str = None) -> Dict:
    """Quick function to scaffold a project."""
    scaffolder = ProjectScaffolder()
    return scaffolder.create_project(template_id, project_name, output_dir)
