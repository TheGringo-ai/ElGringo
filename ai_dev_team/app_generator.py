"""
Enterprise App Generator - Natural Language to Full Applications
================================================================

Transform natural language intentions into complete, deployable applications
using the full AI team (Claude, ChatGPT, Gemini, Grok, Ollama).

The AI team collaborates with specialized roles:
- Claude: Architecture and planning
- ChatGPT: Implementation and coding
- Gemini: UI/UX and creative solutions
- Grok: Analysis and optimization
- Ollama: Local processing and privacy-sensitive tasks

Usage:
    from ai_dev_team.app_generator import AppGenerator

    generator = AppGenerator()
    result = await generator.create_app(
        "Build a task management app with user auth,
        real-time updates, and mobile-friendly UI"
    )
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .orchestrator import AIDevTeam
from .tools import create_all_tools
from .tools.filesystem import FileSystemTools
from .tools.git import GitTools
from .tools.package import PackageTools

logger = logging.getLogger(__name__)


# Application templates
APP_TEMPLATES = {
    "react": {
        "name": "React Web App",
        "stack": ["react", "typescript", "tailwind"],
        "structure": {
            "src/": ["App.tsx", "index.tsx", "index.css"],
            "src/components/": [],
            "src/hooks/": [],
            "src/services/": [],
            "src/types/": [],
            "public/": ["index.html"],
        }
    },
    "next": {
        "name": "Next.js Full Stack",
        "stack": ["nextjs", "typescript", "tailwind", "prisma"],
        "structure": {
            "app/": ["layout.tsx", "page.tsx"],
            "app/api/": [],
            "components/": [],
            "lib/": [],
            "prisma/": ["schema.prisma"],
        }
    },
    "fastapi": {
        "name": "FastAPI Backend",
        "stack": ["python", "fastapi", "sqlalchemy"],
        "structure": {
            "app/": ["main.py", "__init__.py"],
            "app/api/": ["__init__.py"],
            "app/models/": ["__init__.py"],
            "app/services/": ["__init__.py"],
            "tests/": ["__init__.py"],
        }
    },
    "flask": {
        "name": "Flask Web App",
        "stack": ["python", "flask", "sqlalchemy"],
        "structure": {
            "app/": ["__init__.py", "routes.py", "models.py"],
            "app/templates/": [],
            "app/static/": [],
            "tests/": ["__init__.py"],
        }
    },
    "fullstack": {
        "name": "Full Stack (React + FastAPI)",
        "stack": ["react", "typescript", "fastapi", "postgresql"],
        "structure": {
            "frontend/src/": [],
            "frontend/public/": [],
            "backend/app/": [],
            "backend/tests/": [],
            "docker/": [],
        }
    },
    "mobile": {
        "name": "React Native Mobile",
        "stack": ["react-native", "typescript", "expo"],
        "structure": {
            "src/": [],
            "src/screens/": [],
            "src/components/": [],
            "src/navigation/": [],
            "src/services/": [],
        }
    },
    "cli": {
        "name": "CLI Tool",
        "stack": ["python", "click", "rich"],
        "structure": {
            "src/": ["__init__.py", "cli.py", "commands/"],
            "tests/": ["__init__.py"],
        }
    },
    "automation": {
        "name": "Automation Platform",
        "stack": ["python", "fastapi", "celery", "redis"],
        "structure": {
            "app/": ["main.py", "tasks.py"],
            "app/workflows/": [],
            "app/integrations/": [],
            "workers/": [],
        }
    }
}


class AppGenerator:
    """
    Enterprise Application Generator.

    Uses the full AI team to transform natural language
    into complete, deployable applications.
    """

    def __init__(
        self,
        output_dir: str = None,
        gcp_project: str = None,
        use_local_models: bool = True
    ):
        self.output_dir = Path(output_dir or os.getcwd())
        self.gcp_project = gcp_project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.use_local_models = use_local_models

        # Initialize AI team
        self.team = AIDevTeam()

        # Initialize tools
        self.tools = create_all_tools(
            cwd=str(self.output_dir),
            gcp_project=self.gcp_project
        )

        # Track generated projects
        self.generated_projects: List[Dict] = []

    async def create_app(
        self,
        description: str,
        name: Optional[str] = None,
        template: Optional[str] = None,
        features: Optional[List[str]] = None,
        deploy_target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a complete application from natural language description.

        Args:
            description: Natural language description of the app
            name: Optional project name (auto-generated if not provided)
            template: Optional template to use (react, next, fastapi, etc.)
            features: Optional list of specific features to include
            deploy_target: Optional deployment target (firebase, vercel, gcp, aws)

        Returns:
            Dictionary with project details, files created, and next steps
        """
        logger.info(f"Creating app from description: {description[:100]}...")

        # Step 1: Analyze requirements with AI team
        requirements = await self._analyze_requirements(description, features)

        # Step 2: Select or confirm template
        if not template:
            template = await self._select_template(requirements)

        # Step 3: Generate project name if not provided
        if not name:
            name = await self._generate_project_name(description)

        # Step 4: Create project structure
        project_path = self.output_dir / name
        structure = await self._create_project_structure(
            project_path, template, requirements
        )

        # Step 5: Generate code with AI team collaboration
        files_created = await self._generate_code(
            project_path, template, requirements, structure
        )

        # Step 6: Setup dependencies
        await self._setup_dependencies(project_path, template)

        # Step 7: Initialize git repository
        await self._init_git(project_path, description)

        # Step 8: Generate documentation
        docs = await self._generate_documentation(
            project_path, name, description, requirements
        )

        # Step 9: Setup deployment if requested
        deploy_info = None
        if deploy_target:
            deploy_info = await self._setup_deployment(
                project_path, deploy_target, template
            )

        result = {
            "success": True,
            "project_name": name,
            "project_path": str(project_path),
            "template": template,
            "files_created": files_created,
            "requirements": requirements,
            "documentation": docs,
            "deployment": deploy_info,
            "next_steps": self._get_next_steps(project_path, template, deploy_target),
            "created_at": datetime.now().isoformat()
        }

        self.generated_projects.append(result)
        logger.info(f"Successfully created project: {name}")

        return result

    async def _analyze_requirements(
        self,
        description: str,
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Use AI team to analyze and structure requirements."""

        prompt = f"""Analyze this application description and extract structured requirements.

Description: {description}

Additional features requested: {features or 'None specified'}

Provide a JSON response with:
{{
    "app_type": "web|mobile|api|cli|fullstack",
    "primary_language": "typescript|python|rust",
    "framework": "react|next|fastapi|flask|express",
    "features": ["list", "of", "features"],
    "database": "firestore|postgresql|sqlite|mongodb|none",
    "auth": "firebase|jwt|oauth|none",
    "ui_framework": "tailwind|material|bootstrap|none",
    "real_time": true|false,
    "file_upload": true|false,
    "api_integrations": ["list", "of", "apis"],
    "estimated_complexity": "simple|medium|complex",
    "key_entities": ["User", "Task", "etc"],
    "main_flows": ["user registers", "creates item", "etc"]
}}

Be specific and thorough in identifying all required components."""

        result = await self.team.collaborate(
            prompt,
            mode="parallel",
            context="You are analyzing requirements for a new application."
        )

        # Parse the response
        try:
            # Try to extract JSON from the response
            response_text = result.final_answer
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text

            requirements = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            # Fallback to basic requirements
            logger.warning("Could not parse AI requirements, using defaults")
            requirements = {
                "app_type": "web",
                "primary_language": "typescript",
                "framework": "react",
                "features": features or [],
                "database": "firestore",
                "auth": "firebase",
                "ui_framework": "tailwind",
                "estimated_complexity": "medium"
            }

        return requirements

    async def _select_template(self, requirements: Dict[str, Any]) -> str:
        """Select the best template based on requirements."""

        app_type = requirements.get("app_type", "web")
        framework = requirements.get("framework", "react")
        primary_lang = requirements.get("primary_language", "typescript")

        # Map requirements to templates
        if app_type == "fullstack":
            return "fullstack"
        elif app_type == "mobile":
            return "mobile"
        elif app_type == "cli":
            return "cli"
        elif app_type == "api":
            if primary_lang == "python":
                return "fastapi" if framework == "fastapi" else "flask"
            return "next"  # Next.js API routes
        elif framework == "next":
            return "next"
        elif framework == "fastapi":
            return "fastapi"
        elif framework == "flask":
            return "flask"
        else:
            return "react"

    async def _generate_project_name(self, description: str) -> str:
        """Generate a project name from description."""

        prompt = f"""Generate a short, lowercase, hyphenated project name for this app:

{description}

Requirements:
- Maximum 20 characters
- Only lowercase letters and hyphens
- Descriptive but concise
- No numbers

Respond with just the name, nothing else."""

        result = await self.team.collaborate(
            prompt,
            mode="parallel"
        )

        name = result.final_answer.strip().lower()
        # Clean up the name
        name = "".join(c if c.isalpha() or c == "-" else "-" for c in name)
        name = "-".join(filter(None, name.split("-")))[:20]

        if not name:
            name = f"app-{datetime.now().strftime('%Y%m%d')}"

        return name

    async def _create_project_structure(
        self,
        project_path: Path,
        template: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Create the project directory structure."""

        template_info = APP_TEMPLATES.get(template, APP_TEMPLATES["react"])
        structure = template_info["structure"]

        project_path.mkdir(parents=True, exist_ok=True)

        # Create directories
        for dir_path in structure.keys():
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)

        # Add common files
        common_dirs = [".github/workflows/", "docs/"]
        for dir_path in common_dirs:
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)

        return structure

    async def _generate_code(
        self,
        project_path: Path,
        template: str,
        requirements: Dict[str, Any],
        structure: Dict[str, List[str]]
    ) -> List[str]:
        """Generate code files using AI team collaboration."""

        files_created = []
        template_info = APP_TEMPLATES.get(template, APP_TEMPLATES["react"])

        # Determine which files to generate based on template
        files_to_generate = self._get_files_to_generate(template, requirements)

        for file_info in files_to_generate:
            file_path = project_path / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate file content with AI team
            content = await self._generate_file_content(
                file_info, requirements, template
            )

            # Write the file
            file_path.write_text(content)
            files_created.append(str(file_info["path"]))
            logger.info(f"Created: {file_info['path']}")

        return files_created

    def _get_files_to_generate(
        self,
        template: str,
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Determine which files need to be generated."""

        files = []

        if template in ["react", "next"]:
            files.extend([
                {"path": "src/App.tsx", "type": "component", "description": "Main App component"},
                {"path": "src/index.tsx", "type": "entry", "description": "Entry point"},
                {"path": "src/index.css", "type": "styles", "description": "Global styles"},
                {"path": "package.json", "type": "config", "description": "Package configuration"},
                {"path": "tsconfig.json", "type": "config", "description": "TypeScript config"},
                {"path": "tailwind.config.js", "type": "config", "description": "Tailwind config"},
            ])

            # Add feature-specific files
            if requirements.get("auth"):
                files.append({"path": "src/contexts/AuthContext.tsx", "type": "context", "description": "Auth context"})
                files.append({"path": "src/components/auth/LoginForm.tsx", "type": "component", "description": "Login form"})

            if requirements.get("database"):
                files.append({"path": "src/services/database.ts", "type": "service", "description": "Database service"})

        elif template in ["fastapi", "flask"]:
            files.extend([
                {"path": "app/main.py", "type": "entry", "description": "Main application"},
                {"path": "app/__init__.py", "type": "module", "description": "Package init"},
                {"path": "app/api/__init__.py", "type": "module", "description": "API package"},
                {"path": "app/models/__init__.py", "type": "module", "description": "Models package"},
                {"path": "requirements.txt", "type": "config", "description": "Python dependencies"},
                {"path": "Dockerfile", "type": "config", "description": "Docker configuration"},
            ])

            # Add database models if needed
            if requirements.get("database"):
                files.append({"path": "app/models/database.py", "type": "model", "description": "Database models"})

        elif template == "fullstack":
            # Frontend files
            files.extend([
                {"path": "frontend/src/App.tsx", "type": "component", "description": "Frontend App"},
                {"path": "frontend/package.json", "type": "config", "description": "Frontend packages"},
            ])
            # Backend files
            files.extend([
                {"path": "backend/app/main.py", "type": "entry", "description": "Backend API"},
                {"path": "backend/requirements.txt", "type": "config", "description": "Backend dependencies"},
            ])
            # Docker
            files.append({"path": "docker-compose.yml", "type": "config", "description": "Docker Compose"})

        # Always add these
        files.extend([
            {"path": "README.md", "type": "docs", "description": "Project documentation"},
            {"path": ".gitignore", "type": "config", "description": "Git ignore rules"},
            {"path": ".env.example", "type": "config", "description": "Environment template"},
        ])

        return files

    async def _generate_file_content(
        self,
        file_info: Dict[str, Any],
        requirements: Dict[str, Any],
        template: str
    ) -> str:
        """Generate content for a specific file using AI team."""

        file_type = file_info["type"]
        file_path = file_info["path"]
        description = file_info["description"]

        prompt = f"""Generate the complete code for this file:

File: {file_path}
Type: {file_type}
Purpose: {description}

Application Requirements:
{json.dumps(requirements, indent=2)}

Template: {template}

Generate production-ready code that:
1. Follows best practices for {template}
2. Includes proper error handling
3. Has clear comments where needed
4. Uses TypeScript types (if applicable)
5. Is well-structured and maintainable

Return ONLY the file content, no markdown formatting or explanation."""

        result = await self.team.collaborate(
            prompt,
            mode="consensus" if file_type in ["component", "entry"] else "parallel"
        )

        content = result.final_answer

        # Clean up markdown code blocks if present
        if "```" in content:
            lines = content.split("\n")
            clean_lines = []
            in_code = False
            for line in lines:
                if line.startswith("```"):
                    in_code = not in_code
                    continue
                if in_code or not line.startswith("```"):
                    clean_lines.append(line)
            content = "\n".join(clean_lines)

        return content.strip()

    async def _setup_dependencies(self, project_path: Path, template: str) -> None:
        """Install project dependencies."""

        pkg_tools = self.tools["package"]

        try:
            if template in ["react", "next", "mobile"]:
                # Check if package.json exists
                if (project_path / "package.json").exists():
                    pkg_tools._npm_install(cwd=str(project_path))
                    logger.info("Installed npm dependencies")

            elif template in ["fastapi", "flask", "cli", "automation"]:
                # Check if requirements.txt exists
                if (project_path / "requirements.txt").exists():
                    pkg_tools._pip_install(
                        packages=[],
                        requirements="requirements.txt",
                        cwd=str(project_path)
                    )
                    logger.info("Installed pip dependencies")

            elif template == "fullstack":
                # Install both
                frontend_path = project_path / "frontend"
                backend_path = project_path / "backend"

                if (frontend_path / "package.json").exists():
                    pkg_tools._npm_install(cwd=str(frontend_path))

                if (backend_path / "requirements.txt").exists():
                    pkg_tools._pip_install(
                        packages=[],
                        requirements="requirements.txt",
                        cwd=str(backend_path)
                    )

        except Exception as e:
            logger.warning(f"Could not install dependencies: {e}")

    async def _init_git(self, project_path: Path, description: str) -> None:
        """Initialize git repository."""

        git_tools = self.tools["git"]

        try:
            git_tools._init(cwd=str(project_path))
            git_tools._add(all_files=True, cwd=str(project_path))
            git_tools._commit(
                message=f"Initial commit: {description[:50]}",
                cwd=str(project_path)
            )
            logger.info("Initialized git repository")
        except Exception as e:
            logger.warning(f"Could not initialize git: {e}")

    async def _generate_documentation(
        self,
        project_path: Path,
        name: str,
        description: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate project documentation."""

        docs = {}

        # Generate README content
        readme_prompt = f"""Generate a comprehensive README.md for this project:

Project: {name}
Description: {description}
Requirements: {json.dumps(requirements, indent=2)}

Include:
1. Project title and description
2. Features list
3. Tech stack
4. Getting started (installation, setup)
5. Usage examples
6. API documentation (if applicable)
7. Contributing guidelines
8. License

Use proper Markdown formatting."""

        result = await self.team.collaborate(readme_prompt, mode="parallel")
        readme_content = result.final_answer

        readme_path = project_path / "README.md"
        readme_path.write_text(readme_content)
        docs["README.md"] = str(readme_path)

        return docs

    async def _setup_deployment(
        self,
        project_path: Path,
        target: str,
        template: str
    ) -> Dict[str, Any]:
        """Setup deployment configuration."""

        deploy_tools = self.tools["deploy"]
        deploy_info = {"target": target, "configured": False}

        try:
            if target == "firebase":
                # Create firebase.json
                firebase_config = {
                    "hosting": {
                        "public": "build" if template in ["react"] else "out",
                        "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
                    }
                }
                (project_path / "firebase.json").write_text(
                    json.dumps(firebase_config, indent=2)
                )
                deploy_info["configured"] = True
                deploy_info["command"] = "firebase deploy"

            elif target == "vercel":
                # Create vercel.json
                vercel_config = {"version": 2}
                (project_path / "vercel.json").write_text(
                    json.dumps(vercel_config, indent=2)
                )
                deploy_info["configured"] = True
                deploy_info["command"] = "vercel --prod"

            elif target == "gcp" or target == "cloudrun":
                # Create app.yaml for App Engine or use existing Dockerfile
                if template in ["fastapi", "flask"]:
                    deploy_info["configured"] = True
                    deploy_info["command"] = f"gcloud run deploy {project_path.name} --source ."

            elif target == "aws":
                deploy_info["note"] = "Configure AWS deployment manually"

        except Exception as e:
            logger.warning(f"Could not setup deployment: {e}")
            deploy_info["error"] = str(e)

        return deploy_info

    def _get_next_steps(
        self,
        project_path: Path,
        template: str,
        deploy_target: Optional[str]
    ) -> List[str]:
        """Get recommended next steps."""

        steps = [
            f"cd {project_path}",
        ]

        if template in ["react", "next", "mobile"]:
            steps.extend([
                "npm install  # Install dependencies",
                "npm run dev  # Start development server",
            ])
        elif template in ["fastapi"]:
            steps.extend([
                "pip install -r requirements.txt  # Install dependencies",
                "uvicorn app.main:app --reload  # Start development server",
            ])
        elif template in ["flask"]:
            steps.extend([
                "pip install -r requirements.txt",
                "flask run  # Start development server",
            ])
        elif template == "fullstack":
            steps.extend([
                "cd frontend && npm install && npm run dev",
                "cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload",
            ])

        if deploy_target:
            steps.append(f"# Deploy: configured for {deploy_target}")

        steps.append("# Happy coding!")

        return steps

    async def enhance_app(
        self,
        project_path: str,
        enhancement: str
    ) -> Dict[str, Any]:
        """
        Enhance an existing application with new features.

        Args:
            project_path: Path to the existing project
            enhancement: Description of the enhancement to make

        Returns:
            Dictionary with changes made
        """
        prompt = f"""Analyze this enhancement request and determine what changes are needed:

Enhancement: {enhancement}
Project: {project_path}

Provide a detailed plan of:
1. Files to modify
2. New files to create
3. Dependencies to add
4. Configuration changes

Return as JSON."""

        result = await self.team.collaborate(
            prompt,
            mode="consensus"
        )

        # TODO: Implement enhancement logic
        return {
            "enhancement": enhancement,
            "plan": result.final_answer,
            "status": "planned"
        }


# Convenience function
def create_app_generator(
    output_dir: str = None,
    gcp_project: str = None
) -> AppGenerator:
    """Create an AppGenerator instance."""
    return AppGenerator(output_dir=output_dir, gcp_project=gcp_project)


async def generate_app(
    description: str,
    **kwargs
) -> Dict[str, Any]:
    """Quick function to generate an app from description."""
    generator = AppGenerator()
    return await generator.create_app(description, **kwargs)
