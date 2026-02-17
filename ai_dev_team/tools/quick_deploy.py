"""
Quick Deploy Panel
==================

One-stop deployment for all project types.
"""

import os
import subprocess
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime


class QuickDeployer:
    """Handle quick deployments to various platforms."""

    def __init__(self):
        self.gcloud_path = shutil.which("gcloud")
        self.firebase_path = shutil.which("firebase")
        self.vercel_path = shutil.which("vercel")
        self.docker_path = shutil.which("docker")

    def check_tools(self) -> Dict[str, bool]:
        """Check which deployment tools are available."""
        return {
            "gcloud": self.gcloud_path is not None,
            "firebase": self.firebase_path is not None,
            "vercel": self.vercel_path is not None,
            "docker": self.docker_path is not None,
        }

    def get_available_targets(self, project_path: str) -> List[Dict]:
        """Determine available deployment targets for a project."""
        targets = []
        tools = self.check_tools()

        has_dockerfile = os.path.exists(os.path.join(project_path, "Dockerfile"))
        has_firebase_json = os.path.exists(os.path.join(project_path, "firebase.json"))
        has_vercel_json = os.path.exists(os.path.join(project_path, "vercel.json"))
        has_package_json = os.path.exists(os.path.join(project_path, "package.json"))
        has_requirements = os.path.exists(os.path.join(project_path, "requirements.txt"))
        has_main_py = os.path.exists(os.path.join(project_path, "main.py"))

        # Firebase Hosting
        if tools["firebase"] and (has_firebase_json or has_package_json or os.path.exists(os.path.join(project_path, "index.html"))):
            targets.append({
                "id": "firebase_hosting",
                "name": "Firebase Hosting",
                "icon": "🔥",
                "description": "Static sites and SPAs",
                "ready": has_firebase_json,
                "setup_needed": not has_firebase_json
            })

        # Vercel
        if tools["vercel"] and (has_package_json or has_vercel_json):
            targets.append({
                "id": "vercel",
                "name": "Vercel",
                "icon": "▲",
                "description": "Next.js, React, static sites",
                "ready": True,
                "setup_needed": False
            })

        # Cloud Run
        if tools["gcloud"] and (has_dockerfile or has_requirements):
            targets.append({
                "id": "cloud_run",
                "name": "Cloud Run",
                "icon": "☁️",
                "description": "Containerized apps",
                "ready": has_dockerfile,
                "setup_needed": not has_dockerfile
            })

        # Cloud Functions
        if tools["gcloud"] and has_main_py:
            targets.append({
                "id": "cloud_functions",
                "name": "Cloud Functions",
                "icon": "⚡",
                "description": "Serverless functions",
                "ready": True,
                "setup_needed": False
            })

        # Local Docker
        if tools["docker"] and has_dockerfile:
            targets.append({
                "id": "docker_local",
                "name": "Docker (Local)",
                "icon": "🐳",
                "description": "Run locally in container",
                "ready": True,
                "setup_needed": False
            })

        return targets

    def deploy(self, project_path: str, target: str, options: Dict = None) -> Dict[str, Any]:
        """Deploy project to specified target."""
        options = options or {}

        try:
            if target == "firebase_hosting":
                return self._deploy_firebase(project_path, options)
            elif target == "vercel":
                return self._deploy_vercel(project_path, options)
            elif target == "cloud_run":
                return self._deploy_cloud_run(project_path, options)
            elif target == "cloud_functions":
                return self._deploy_cloud_functions(project_path, options)
            elif target == "docker_local":
                return self._deploy_docker_local(project_path, options)
            else:
                return {"success": False, "error": f"Unknown target: {target}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_command(self, cmd: List[str], cwd: str = None) -> Dict:
        """Run a shell command and return result."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _deploy_firebase(self, project_path: str, options: Dict) -> Dict:
        """Deploy to Firebase Hosting."""
        # Check if firebase.json exists
        if not os.path.exists(os.path.join(project_path, "firebase.json")):
            return {
                "success": False,
                "error": "firebase.json not found. Run 'firebase init hosting' first.",
                "setup_command": "firebase init hosting"
            }

        result = self._run_command(["firebase", "deploy", "--only", "hosting"], cwd=project_path)

        if result["success"]:
            # Extract URL from output
            url = "Check Firebase Console for URL"
            if "Hosting URL:" in result.get("stdout", ""):
                lines = result["stdout"].split("\n")
                for line in lines:
                    if "Hosting URL:" in line:
                        url = line.split("Hosting URL:")[-1].strip()
                        break

            return {
                "success": True,
                "url": url,
                "output": result["stdout"],
                "platform": "Firebase Hosting"
            }
        else:
            return {
                "success": False,
                "error": result.get("stderr") or result.get("error"),
                "output": result.get("stdout", "")
            }

    def _deploy_vercel(self, project_path: str, options: Dict) -> Dict:
        """Deploy to Vercel."""
        prod = options.get("production", True)
        cmd = ["vercel", "--yes"]
        if prod:
            cmd.append("--prod")

        result = self._run_command(cmd, cwd=project_path)

        if result["success"]:
            # Extract URL from output
            url = result.get("stdout", "").strip().split("\n")[-1]
            return {
                "success": True,
                "url": url,
                "output": result["stdout"],
                "platform": "Vercel"
            }
        else:
            return {
                "success": False,
                "error": result.get("stderr") or result.get("error")
            }

    def _deploy_cloud_run(self, project_path: str, options: Dict) -> Dict:
        """Deploy to Google Cloud Run."""
        service_name = options.get("service_name", os.path.basename(project_path).lower().replace("_", "-"))
        region = options.get("region", "us-central1")
        project_id = options.get("project_id")

        cmd = [
            "gcloud", "run", "deploy", service_name,
            "--source", ".",
            "--region", region,
            "--allow-unauthenticated"
        ]

        if project_id:
            cmd.extend(["--project", project_id])

        result = self._run_command(cmd, cwd=project_path)

        if result["success"]:
            # Extract URL
            url = "Check Cloud Console for URL"
            output = result.get("stdout", "") + result.get("stderr", "")
            if "Service URL:" in output:
                for line in output.split("\n"):
                    if "Service URL:" in line:
                        url = line.split("Service URL:")[-1].strip()
                        break

            return {
                "success": True,
                "url": url,
                "service_name": service_name,
                "region": region,
                "output": output,
                "platform": "Cloud Run"
            }
        else:
            return {
                "success": False,
                "error": result.get("stderr") or result.get("error")
            }

    def _deploy_cloud_functions(self, project_path: str, options: Dict) -> Dict:
        """Deploy to Google Cloud Functions."""
        function_name = options.get("function_name", "main")
        region = options.get("region", "us-central1")
        runtime = options.get("runtime", "python311")

        cmd = [
            "gcloud", "functions", "deploy", function_name,
            "--gen2",
            "--runtime", runtime,
            "--region", region,
            "--source", ".",
            "--entry-point", function_name,
            "--trigger-http",
            "--allow-unauthenticated"
        ]

        result = self._run_command(cmd, cwd=project_path)

        if result["success"]:
            return {
                "success": True,
                "function_name": function_name,
                "output": result["stdout"],
                "platform": "Cloud Functions"
            }
        else:
            return {
                "success": False,
                "error": result.get("stderr") or result.get("error")
            }

    def _deploy_docker_local(self, project_path: str, options: Dict) -> Dict:
        """Build and run Docker container locally."""
        image_name = options.get("image_name", os.path.basename(project_path).lower())
        port = options.get("port", 8080)

        # Build
        build_result = self._run_command(
            ["docker", "build", "-t", image_name, "."],
            cwd=project_path
        )

        if not build_result["success"]:
            return {
                "success": False,
                "error": f"Build failed: {build_result.get('stderr')}"
            }

        # Stop existing container if running
        self._run_command(["docker", "stop", image_name])
        self._run_command(["docker", "rm", image_name])

        # Run
        run_result = self._run_command([
            "docker", "run", "-d",
            "--name", image_name,
            "-p", f"{port}:8080",
            image_name
        ])

        if run_result["success"]:
            return {
                "success": True,
                "url": f"http://localhost:{port}",
                "container_name": image_name,
                "platform": "Docker (Local)"
            }
        else:
            return {
                "success": False,
                "error": f"Run failed: {run_result.get('stderr')}"
            }


class LocalServer:
    """Run local development servers."""

    def __init__(self):
        self.running_servers = {}

    def start_python_server(self, project_path: str, port: int = 8000) -> Dict:
        """Start a Python HTTP server."""
        try:
            import threading
            import http.server
            import socketserver

            os.chdir(project_path)
            handler = http.server.SimpleHTTPRequestHandler

            with socketserver.TCPServer(("", port), handler) as httpd:
                thread = threading.Thread(target=httpd.serve_forever)
                thread.daemon = True
                thread.start()

                self.running_servers[port] = httpd
                return {
                    "success": True,
                    "url": f"http://localhost:{port}",
                    "port": port
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_server(self, port: int) -> Dict:
        """Stop a running server."""
        if port in self.running_servers:
            self.running_servers[port].shutdown()
            del self.running_servers[port]
            return {"success": True}
        return {"success": False, "error": "Server not found"}


# Quick access functions
def deploy_to_firebase(project_path: str) -> Dict:
    """Quick deploy to Firebase."""
    deployer = QuickDeployer()
    return deployer.deploy(project_path, "firebase_hosting")


def deploy_to_vercel(project_path: str) -> Dict:
    """Quick deploy to Vercel."""
    deployer = QuickDeployer()
    return deployer.deploy(project_path, "vercel")


def deploy_to_cloud_run(project_path: str, service_name: str = None) -> Dict:
    """Quick deploy to Cloud Run."""
    deployer = QuickDeployer()
    return deployer.deploy(project_path, "cloud_run", {"service_name": service_name})
