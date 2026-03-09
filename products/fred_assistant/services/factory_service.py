"""
App Factory Service — Build, Launch & Monetize Apps from El Gringo.

Orchestrates: code generation (AppBuilder), quality gates (test_gen, code_audit),
Docker builds, and VM deploys into a single pipeline.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from products.fred_assistant.database import get_conn, log_activity

logger = logging.getLogger(__name__)

FACTORY_DIR = os.path.expanduser("~/.fred-assistant/factory")
PORT_RANGE_START = 9000
PORT_RANGE_END = 9100


# ── Helpers ──────────────────────────────────────────────────────────


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _row_to_app(row) -> dict:
    """Convert a sqlite3.Row to an app dict, parsing JSON fields."""
    d = dict(row)
    for key in ("tech_stack", "spec"):
        if isinstance(d.get(key), str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = {}
    return d


def _row_to_build(row) -> dict:
    return dict(row)


def _row_to_customer(row) -> dict:
    return dict(row)


def _next_port() -> int:
    """Find next available port in the 9000-9100 range."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT port FROM apps WHERE port > 0 ORDER BY port"
        ).fetchall()
    used = {r["port"] for r in rows}
    for p in range(PORT_RANGE_START, PORT_RANGE_END):
        if p not in used:
            return p
    return PORT_RANGE_START  # fallback


# ── CRUD ─────────────────────────────────────────────────────────────


def create_app(data: dict) -> dict:
    """Create a new app record and its project directory."""
    app_id = str(uuid.uuid4())[:12]
    name = data["name"].lower().replace(" ", "-")
    display_name = data.get("display_name") or name.replace("-", " ").title()
    description = data.get("description", "")
    app_type = data.get("app_type", "fullstack")
    tech_stack = data.get("tech_stack", {})
    template = data.get("template")

    project_dir = os.path.join(FACTORY_DIR, name)
    os.makedirs(project_dir, exist_ok=True)

    port = _next_port()

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO apps
               (id, name, display_name, description, app_type, tech_stack, spec,
                status, port, project_dir, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, '{}', 'draft', ?, ?, ?, ?)""",
            (app_id, name, display_name, description, app_type,
             json.dumps(tech_stack), port, project_dir, _now(), _now()),
        )

    # Optionally scaffold from a template
    if template:
        try:
            from elgringo.tools.scaffolding import ProjectScaffolder
            scaffolder = ProjectScaffolder()
            scaffolder.create_project(template, display_name, output_dir=project_dir)
            logger.info("Scaffolded %s from template %s", name, template)
        except Exception as e:
            logger.warning("Template scaffolding failed: %s", e)

    log_activity("factory:create_app", "app", app_id, {"name": name})
    return get_app(app_id)


def list_apps() -> list:
    """List all apps with status."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM apps ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_app(r) for r in rows]


def get_app(app_id: str) -> Optional[dict]:
    """Get app detail including builds and revenue summary."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
        if not row:
            return None
        app = _row_to_app(row)

        # Attach builds
        builds = conn.execute(
            "SELECT * FROM app_builds WHERE app_id = ? ORDER BY version, step",
            (app_id,),
        ).fetchall()
        app["builds"] = [_row_to_build(b) for b in builds]

        # Attach revenue summary
        rev = conn.execute(
            """SELECT COUNT(*) as customer_count, COALESCE(SUM(mrr), 0) as total_mrr
               FROM app_customers WHERE app_id = ? AND status != 'churned'""",
            (app_id,),
        ).fetchone()
        app["customer_count"] = rev["customer_count"] if rev else 0
        app["total_mrr"] = rev["total_mrr"] if rev else 0

    return app


def update_app(app_id: str, data: dict) -> Optional[dict]:
    """Update app metadata."""
    sets, vals = [], []
    for field in ("display_name", "description", "app_type", "repo_url"):
        if field in data and data[field] is not None:
            sets.append(f"{field} = ?")
            vals.append(data[field])
    if "tech_stack" in data and data["tech_stack"] is not None:
        sets.append("tech_stack = ?")
        vals.append(json.dumps(data["tech_stack"]))
    if not sets:
        return get_app(app_id)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(app_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE apps SET {', '.join(sets)} WHERE id = ?", vals)
    return get_app(app_id)


def archive_app(app_id: str) -> bool:
    """Soft-delete an app."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE apps SET status = 'archived', updated_at = ? WHERE id = ?",
            (_now(), app_id),
        )
    log_activity("factory:archive_app", "app", app_id)
    return True


def _set_status(app_id: str, status: str, error: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE apps SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
            (status, error, _now(), app_id),
        )


# ── Build Pipeline Helpers ───────────────────────────────────────────


def _create_build_step(app_id: str, step: str, version: int = 1) -> str:
    build_id = str(uuid.uuid4())[:12]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO app_builds (id, app_id, version, step, status, started_at)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (build_id, app_id, version, step, _now()),
        )
    return build_id


def _finish_build_step(build_id: str, status: str, log_text: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE app_builds SET status = ?, log = ?, completed_at = ? WHERE id = ?",
            (status, log_text[:10000], _now(), build_id),
        )


def _get_latest_version(app_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(version) as v FROM app_builds WHERE app_id = ?", (app_id,)
        ).fetchone()
    return (row["v"] or 0) + 1


# ── Generate ─────────────────────────────────────────────────────────


async def generate_app(app_id: str, enrich: bool = True, template: Optional[str] = None) -> dict:
    """AI-generate a complete codebase for the app."""
    app = get_app(app_id)
    if not app:
        return {"error": "App not found"}

    _set_status(app_id, "generating")
    version = _get_latest_version(app_id)
    build_id = _create_build_step(app_id, "generate", version)

    try:
        project_dir = app["project_dir"]
        os.makedirs(project_dir, exist_ok=True)

        # Build an AppProject spec from the app metadata
        from elgringo.app_builder.models import create_default_project

        app_type_map = {
            "api": "crud",
            "web": "web_app",
            "fullstack": "dashboard",
        }
        mapped_type = app_type_map.get(app["app_type"], "web_app")
        project = create_default_project(app["name"], mapped_type)
        project.description = app["description"]
        project.display_name = app["display_name"]

        # Use BackendGenerator for backend files
        from elgringo.app_builder.generator import IntentDetector, BackendGenerator

        intent = IntentDetector().analyze_project(project)
        backend_files = BackendGenerator().generate(project, intent)

        # Write all generated files
        files_written = []
        for relpath, content in backend_files.items():
            filepath = os.path.join(project_dir, relpath)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(content)
            files_written.append(relpath)

        # Optionally enrich files with LLM
        if enrich:
            try:
                from products.fred_assistant.services.llm_shared import llm_response

                system = (
                    f"You are building a {app['app_type']} app called '{app['display_name']}'. "
                    f"Description: {app['description']}. "
                    "Improve the generated code: add input validation, error handling, "
                    "and clean docstrings. Return ONLY the improved code, no markdown fences."
                )

                for relpath in files_written:
                    filepath = os.path.join(project_dir, relpath)
                    with open(filepath) as f:
                        original = f.read()
                    if len(original) < 50:
                        continue
                    improved = await llm_response(
                        f"Improve this file ({relpath}):\n\n{original[:3000]}",
                        system,
                        feature="factory_generate",
                    )
                    if improved and len(improved) > 50:
                        with open(filepath, "w") as f:
                            f.write(improved)
            except Exception as e:
                logger.warning("LLM enrichment failed (non-fatal): %s", e)

        # Generate a Dockerfile
        dockerfile_content = _generate_dockerfile(app)
        dockerfile_path = os.path.join(project_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
        files_written.append("Dockerfile")

        # Update app spec
        with get_conn() as conn:
            conn.execute(
                "UPDATE apps SET spec = ?, status = 'draft', updated_at = ? WHERE id = ?",
                (json.dumps(project.to_dict()), _now(), app_id),
            )

        _finish_build_step(build_id, "passed", f"Generated {len(files_written)} files")
        log_activity("factory:generate", "app", app_id, {"files": len(files_written)})

        return {"status": "ok", "files": files_written}

    except Exception as e:
        _finish_build_step(build_id, "failed", str(e))
        _set_status(app_id, "failed", str(e))
        logger.error("generate_app failed: %s", e, exc_info=True)
        return {"error": str(e)}


def _generate_dockerfile(app: dict) -> str:
    """Generate a simple Dockerfile based on app type."""
    port = app.get("port", 8000)
    app.get("name", "app")
    if app.get("app_type") == "api" or app.get("app_type") == "fullstack":
        return f"""FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE {port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""
    return f"""FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true
EXPOSE {port}
CMD ["python", "main.py"]
"""


# ── Build (Test + Audit + Docker) ───────────────────────────────────


async def build_app(app_id: str) -> dict:
    """Run the full build pipeline: test -> audit -> docker."""
    app = get_app(app_id)
    if not app:
        return {"error": "App not found"}

    _set_status(app_id, "building")
    version = _get_latest_version(app_id)
    results = {}

    # Step 1: Test generation
    test_build_id = _create_build_step(app_id, "test", version)
    try:
        from products.fred_assistant.services.platform_services import call_service
        test_result = await call_service(
            "test_gen", "POST", "/tests/generate",
            data={"project_path": app["project_dir"], "language": "python"},
            timeout=120,
        )
        if "error" in test_result:
            _finish_build_step(test_build_id, "failed", test_result["error"])
            results["test"] = "failed"
        else:
            _finish_build_step(test_build_id, "passed", json.dumps(test_result)[:5000])
            results["test"] = "passed"
    except Exception as e:
        _finish_build_step(test_build_id, "skipped", f"Test gen unavailable: {e}")
        results["test"] = "skipped"

    # Step 2: Code audit
    audit_build_id = _create_build_step(app_id, "audit", version)
    try:
        from products.fred_assistant.services.platform_services import call_service
        audit_result = await call_service(
            "code_audit", "POST", "/audit/scan",
            data={"project_path": app["project_dir"], "language": "python"},
            timeout=120,
        )
        if "error" in audit_result:
            _finish_build_step(audit_build_id, "failed", audit_result["error"])
            results["audit"] = "failed"
        else:
            _finish_build_step(audit_build_id, "passed", json.dumps(audit_result)[:5000])
            results["audit"] = "passed"
    except Exception as e:
        _finish_build_step(audit_build_id, "skipped", f"Code audit unavailable: {e}")
        results["audit"] = "skipped"

    # Step 3: Docker build
    docker_build_id = _create_build_step(app_id, "docker", version)
    try:
        from elgringo.tools.docker import DockerTools
        docker = DockerTools(default_cwd=app["project_dir"])
        tag = f"elgringo-factory/{app['name']}:v{version}"
        build_result = docker._build(tag=tag, context=".", cwd=app["project_dir"])
        if build_result.success:
            _finish_build_step(docker_build_id, "passed", build_result.output[:5000])
            results["docker"] = "passed"
        else:
            _finish_build_step(docker_build_id, "failed", build_result.error or "Docker build failed")
            results["docker"] = "failed"
    except Exception as e:
        _finish_build_step(docker_build_id, "skipped", f"Docker unavailable: {e}")
        results["docker"] = "skipped"

    # Determine overall status
    if any(v == "failed" for v in results.values()):
        _set_status(app_id, "failed", "Build pipeline had failures")
    else:
        _set_status(app_id, "draft")  # Ready for deploy

    log_activity("factory:build", "app", app_id, results)
    return {"status": "ok", "steps": results}


# ── Deploy ───────────────────────────────────────────────────────────


async def deploy_app(app_id: str) -> dict:
    """Deploy an app to the VM using systemd + nginx pattern."""
    app = get_app(app_id)
    if not app:
        return {"error": "App not found"}

    _set_status(app_id, "deploying")
    version = _get_latest_version(app_id)
    deploy_build_id = _create_build_step(app_id, "deploy", version)

    try:
        port = app["port"]
        name = app["name"]
        project_dir = app["project_dir"]

        # Generate systemd unit file
        service_content = f"""[Unit]
Description=El Gringo Factory App: {name}
After=network.target

[Service]
Type=simple
User=elgringo
WorkingDirectory={project_dir}/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port {port}
Restart=always
RestartSec=5
Environment=PORT={port}

[Install]
WantedBy=multi-user.target
"""
        service_path = os.path.join(project_dir, f"elgringo-app-{name}.service")
        with open(service_path, "w") as f:
            f.write(service_content)

        # Generate nginx snippet
        nginx_content = f"""# Factory app: {name}
location /apps/{name}/ {{
    proxy_pass http://127.0.0.1:{port}/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}}
"""
        nginx_path = os.path.join(project_dir, f"nginx-{name}.conf")
        with open(nginx_path, "w") as f:
            f.write(nginx_content)

        deploy_url = f"https://ai.chatterfix.com/apps/{name}/"

        with get_conn() as conn:
            conn.execute(
                "UPDATE apps SET status = 'live', deploy_url = ?, updated_at = ? WHERE id = ?",
                (deploy_url, _now(), app_id),
            )

        _finish_build_step(deploy_build_id, "passed", f"Deploy configs generated. URL: {deploy_url}")
        log_activity("factory:deploy", "app", app_id, {"url": deploy_url, "port": port})

        return {
            "status": "ok",
            "deploy_url": deploy_url,
            "port": port,
            "service_file": service_path,
            "nginx_file": nginx_path,
            "note": "Service + nginx configs generated. Run deploy-vm.sh to activate on VM.",
        }

    except Exception as e:
        _finish_build_step(deploy_build_id, "failed", str(e))
        _set_status(app_id, "failed", str(e))
        logger.error("deploy_app failed: %s", e, exc_info=True)
        return {"error": str(e)}


# ── Builds ───────────────────────────────────────────────────────────


def list_builds(app_id: str) -> list:
    """Get build history for an app."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM app_builds WHERE app_id = ? ORDER BY version DESC, started_at DESC",
            (app_id,),
        ).fetchall()
    return [_row_to_build(r) for r in rows]


# ── Templates ────────────────────────────────────────────────────────


def list_templates() -> list:
    """Merge templates from scaffolding + registry."""
    templates = []

    # From scaffolding PROJECT_TEMPLATES
    try:
        from elgringo.tools.scaffolding import PROJECT_TEMPLATES
        for key, tmpl in PROJECT_TEMPLATES.items():
            templates.append({
                "id": key,
                "source": "scaffolding",
                "name": tmpl.get("name", key),
                "description": tmpl.get("description", ""),
                "icon": tmpl.get("icon", ""),
                "tech": tmpl.get("tech", []),
                "deploy_to": tmpl.get("deploy_to", []),
            })
    except Exception as e:
        logger.debug("Scaffolding templates unavailable: %s", e)

    # From TemplateRegistry
    try:
        from templates.registry import TemplateRegistry
        registry = TemplateRegistry()
        for t in registry.list_all():
            templates.append({
                "id": t.id,
                "source": "registry",
                "name": t.name,
                "description": t.description,
                "icon": "",
                "tech": [t.language],
                "deploy_to": [],
            })
    except Exception as e:
        logger.debug("Template registry unavailable: %s", e)

    return templates


# ── Portfolio ────────────────────────────────────────────────────────


def get_portfolio_summary() -> dict:
    """Total MRR, app count, per-app breakdown."""
    with get_conn() as conn:
        apps = conn.execute(
            "SELECT id, name, display_name, status, deploy_url FROM apps WHERE status != 'archived'"
        ).fetchall()

        total_mrr = 0
        total_customers = 0
        per_app = []

        for app in apps:
            rev = conn.execute(
                """SELECT COUNT(*) as customers, COALESCE(SUM(mrr), 0) as mrr
                   FROM app_customers WHERE app_id = ? AND status != 'churned'""",
                (app["id"],),
            ).fetchone()
            customers = rev["customers"] if rev else 0
            mrr = rev["mrr"] if rev else 0
            total_mrr += mrr
            total_customers += customers
            per_app.append({
                "id": app["id"],
                "name": app["name"],
                "display_name": app["display_name"],
                "status": app["status"],
                "deploy_url": app["deploy_url"],
                "customers": customers,
                "mrr": mrr,
            })

    live_count = sum(1 for a in per_app if a["status"] == "live")

    return {
        "total_apps": len(per_app),
        "live_apps": live_count,
        "total_mrr": total_mrr,
        "total_customers": total_customers,
        "apps": per_app,
    }


# ── Customers ────────────────────────────────────────────────────────


def add_customer(data: dict) -> dict:
    """Add a customer to an app."""
    cust_id = str(uuid.uuid4())[:12]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO app_customers (id, app_id, name, email, plan, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'trial', ?, ?)""",
            (cust_id, data["app_id"], data["name"], data.get("email", ""),
             data.get("plan", "free"), _now(), _now()),
        )
    log_activity("factory:add_customer", "app_customer", cust_id, data)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM app_customers WHERE id = ?", (cust_id,)).fetchone()
    return _row_to_customer(row)


def list_customers(app_id: str) -> list:
    """List customers for an app."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM app_customers WHERE app_id = ? ORDER BY created_at DESC",
            (app_id,),
        ).fetchall()
    return [_row_to_customer(r) for r in rows]


# ── File Browser ─────────────────────────────────────────────────────

# Text-like extensions we allow viewing/editing
_TEXT_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".yaml",
    ".yml", ".md", ".txt", ".toml", ".cfg", ".ini", ".env", ".sh", ".bash",
    ".sql", ".xml", ".csv", ".dockerfile", ".service", ".conf", ".gitignore",
    ".lock", ".log",
}

# Max file size for read/edit (500 KB)
_MAX_READ_SIZE = 512_000


def _safe_project_path(app_id: str, rel_path: str) -> tuple:
    """Resolve a relative path inside an app's project dir. Returns (abs_path, app) or raises."""
    app = get_app(app_id)
    if not app:
        raise FileNotFoundError("App not found")
    project_dir = app["project_dir"]
    if not project_dir or not os.path.isdir(project_dir):
        raise FileNotFoundError("Project directory does not exist")
    # Prevent path traversal
    resolved = os.path.normpath(os.path.join(project_dir, rel_path))
    if not resolved.startswith(os.path.normpath(project_dir)):
        raise PermissionError("Path traversal not allowed")
    return resolved, app


def list_files(app_id: str, rel_path: str = "") -> dict:
    """List files and directories in an app's project folder."""
    abs_path, app = _safe_project_path(app_id, rel_path)
    if not os.path.isdir(abs_path):
        return {"error": "Not a directory"}

    project_root = app["project_dir"]
    entries = []
    try:
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            rel = os.path.relpath(full, project_root)
            is_dir = os.path.isdir(full)
            entry = {
                "name": name,
                "path": rel,
                "is_dir": is_dir,
            }
            if not is_dir:
                try:
                    entry["size"] = os.path.getsize(full)
                except OSError:
                    entry["size"] = 0
                entry["ext"] = os.path.splitext(name)[1].lower()
            entries.append(entry)
    except OSError as e:
        return {"error": str(e)}

    # Sort: dirs first, then files
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))

    return {
        "path": rel_path or ".",
        "project_dir": project_root,
        "entries": entries,
    }


def read_file(app_id: str, rel_path: str) -> dict:
    """Read a file's content from the app project."""
    abs_path, app = _safe_project_path(app_id, rel_path)
    if not os.path.isfile(abs_path):
        return {"error": "File not found"}

    size = os.path.getsize(abs_path)
    ext = os.path.splitext(abs_path)[1].lower()
    is_text = ext in _TEXT_EXTS or ext == "" or size == 0

    if not is_text:
        return {
            "path": rel_path,
            "size": size,
            "ext": ext,
            "binary": True,
            "content": None,
        }
    if size > _MAX_READ_SIZE:
        return {"error": f"File too large ({size} bytes, max {_MAX_READ_SIZE})"}

    try:
        with open(abs_path, "r", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}

    return {
        "path": rel_path,
        "size": size,
        "ext": ext,
        "binary": False,
        "content": content,
    }


def write_file(app_id: str, rel_path: str, content: str) -> dict:
    """Write/update a file in the app project."""
    abs_path, app = _safe_project_path(app_id, rel_path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as f:
            f.write(content)
        log_activity("factory:write_file", "app", app_id, {"path": rel_path})
        return {"status": "ok", "path": rel_path, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def create_file(app_id: str, rel_path: str, content: str = "") -> dict:
    """Create a new file (or directory if rel_path ends with /)."""
    abs_path, app = _safe_project_path(app_id, rel_path)
    if os.path.exists(abs_path):
        return {"error": "Path already exists"}
    try:
        if rel_path.endswith("/"):
            os.makedirs(abs_path, exist_ok=True)
            return {"status": "ok", "path": rel_path, "is_dir": True}
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as f:
            f.write(content)
        log_activity("factory:create_file", "app", app_id, {"path": rel_path})
        return {"status": "ok", "path": rel_path, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def delete_file(app_id: str, rel_path: str) -> dict:
    """Delete a file or empty directory from the app project."""
    abs_path, app = _safe_project_path(app_id, rel_path)
    if not os.path.exists(abs_path):
        return {"error": "Path not found"}
    try:
        if os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        log_activity("factory:delete_file", "app", app_id, {"path": rel_path})
        return {"status": "ok", "path": rel_path}
    except Exception as e:
        return {"error": str(e)}


def rename_file(app_id: str, old_path: str, new_path: str) -> dict:
    """Rename/move a file within the app project."""
    abs_old, app = _safe_project_path(app_id, old_path)
    abs_new, _ = _safe_project_path(app_id, new_path)
    if not os.path.exists(abs_old):
        return {"error": "Source not found"}
    if os.path.exists(abs_new):
        return {"error": "Destination already exists"}
    try:
        os.makedirs(os.path.dirname(abs_new), exist_ok=True)
        os.rename(abs_old, abs_new)
        log_activity("factory:rename_file", "app", app_id, {"old": old_path, "new": new_path})
        return {"status": "ok", "old_path": old_path, "new_path": new_path}
    except Exception as e:
        return {"error": str(e)}


def export_app(app_id: str) -> dict:
    """Create a tar.gz export of the app project. Returns path to archive."""
    app = get_app(app_id)
    if not app:
        return {"error": "App not found"}
    project_dir = app["project_dir"]
    if not os.path.isdir(project_dir):
        return {"error": "Project directory does not exist"}

    import tarfile
    export_dir = os.path.join(FACTORY_DIR, "_exports")
    os.makedirs(export_dir, exist_ok=True)
    archive_name = f"{app['name']}-export.tar.gz"
    archive_path = os.path.join(export_dir, archive_name)

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(project_dir, arcname=app["name"])
        log_activity("factory:export", "app", app_id, {"archive": archive_path})
        return {
            "status": "ok",
            "archive_path": archive_path,
            "archive_name": archive_name,
            "size": os.path.getsize(archive_path),
        }
    except Exception as e:
        return {"error": str(e)}
