"""
App Generator
=============

Generates complete applications from AppProject definitions.
- Frontend HTML/CSS/JS
- Backend FastAPI
- Database schema (SQLite/Firestore)
"""

import os
import re
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .models import AppProject, Page, Component, DataModel, DataField


class IntentDetector:
    """Analyzes frontend components to detect backend requirements"""

    def analyze_project(self, project: AppProject) -> Dict[str, Any]:
        """Analyze project to determine what backend is needed"""

        # Detect data models from components
        detected_models = self._detect_models(project)

        # Check if auth is needed
        auth_needed = self._needs_auth(project)

        # Generate endpoints
        endpoints = self._generate_endpoints(detected_models)

        return {
            "data_models": detected_models,
            "auth_required": auth_needed,
            "endpoints": endpoints,
            "database_type": project.database_type
        }

    def _detect_models(self, project: AppProject) -> List[DataModel]:
        """Scan components for data fields and infer models"""
        models = {}

        for page in project.pages:
            for component in page.components:
                self._scan_component_for_models(component, page.name, models)

        # Also include explicitly defined models
        for model in project.data_models:
            if model.name not in models:
                models[model.name] = model

        return list(models.values())

    def _scan_component_for_models(self, component: Component, page_name: str, models: Dict):
        """Recursively scan component for data bindings"""

        # Forms create models
        if component.component_type == "form":
            model_name = component.properties.get("model", page_name.lower())
            if model_name not in models:
                models[model_name] = DataModel(name=model_name, display_name=model_name.title())

            # Extract fields from form children
            for child in component.children:
                if child.data_binding:
                    field = self._component_to_field(child)
                    models[model_name].fields.append(field)

        # Data tables reference models
        elif component.component_type == "data_table":
            model_name = component.properties.get("model", "")
            if model_name and model_name not in models:
                # Infer fields from columns
                columns = component.properties.get("columns", [])
                fields = [DataField(name=col, field_type="string") for col in columns]
                models[model_name] = DataModel(name=model_name, display_name=model_name.title(), fields=fields)

        # Auth forms create users model
        elif component.component_type in ["login_form", "signup_form"]:
            if "users" not in models:
                models["users"] = DataModel(
                    name="users",
                    display_name="Users",
                    fields=[
                        DataField(name="email", field_type="email", required=True, unique=True),
                        DataField(name="password", field_type="password", required=True),
                        DataField(name="name", field_type="string"),
                    ]
                )

        # Recurse into children
        for child in component.children:
            self._scan_component_for_models(child, page_name, models)

    def _component_to_field(self, component: Component) -> DataField:
        """Convert a form component to a data field"""
        field_name = component.data_binding or component.name or component.component_type

        type_map = {
            "text_field": "string",
            "email_field": "email",
            "password_field": "password",
            "number_field": "number",
            "date_field": "date",
            "datetime_field": "datetime",
            "checkbox": "boolean",
            "textarea": "text",
            "dropdown": "string",
            "file_upload": "file",
        }

        field_type = type_map.get(component.component_type, "string")
        required = component.properties.get("required", False)

        return DataField(name=field_name, field_type=field_type, required=required)

    def _needs_auth(self, project: AppProject) -> bool:
        """Check if project needs authentication"""
        if project.auth_enabled:
            return True

        for page in project.pages:
            if page.requires_auth:
                return True
            for component in page.components:
                if self._has_auth_component(component):
                    return True

        return False

    def _has_auth_component(self, component: Component) -> bool:
        """Check if component is auth-related"""
        auth_types = ["login_form", "signup_form", "logout_button", "profile_card", "auth_guard"]
        if component.component_type in auth_types:
            return True
        return any(self._has_auth_component(c) for c in component.children)

    def _generate_endpoints(self, models: List[DataModel]) -> List[Dict]:
        """Generate CRUD endpoints for each model"""
        endpoints = []

        for model in models:
            base_path = f"/api/{model.name}"
            endpoints.extend([
                {"path": base_path, "method": "GET", "model": model.name, "operation": "list"},
                {"path": f"{base_path}/{{id}}", "method": "GET", "model": model.name, "operation": "get"},
                {"path": base_path, "method": "POST", "model": model.name, "operation": "create"},
                {"path": f"{base_path}/{{id}}", "method": "PUT", "model": model.name, "operation": "update"},
                {"path": f"{base_path}/{{id}}", "method": "DELETE", "model": model.name, "operation": "delete"},
            ])

        return endpoints


class SchemaGenerator:
    """Generates database schemas"""

    def generate_sqlite(self, models: List[DataModel]) -> str:
        """Generate SQLite CREATE TABLE statements"""
        statements = []

        for model in models:
            columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

            for field in model.fields:
                col = self._sqlite_column(field)
                columns.append(col)

            if model.timestamps:
                columns.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                columns.append("updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            sql = f"CREATE TABLE IF NOT EXISTS {model.name} (\n    " + ",\n    ".join(columns) + "\n);"
            statements.append(sql)

        return "\n\n".join(statements)

    def _sqlite_column(self, field: DataField) -> str:
        """Generate SQLite column definition"""
        type_map = {
            "string": "TEXT",
            "text": "TEXT",
            "email": "TEXT",
            "password": "TEXT",
            "number": "REAL",
            "integer": "INTEGER",
            "boolean": "INTEGER",
            "date": "DATE",
            "datetime": "TIMESTAMP",
            "file": "TEXT",
            "json": "TEXT",
        }

        col_type = type_map.get(field.field_type, "TEXT")
        nullable = "" if field.required else " NULL"
        unique = " UNIQUE" if field.unique else ""
        default = f" DEFAULT {repr(field.default_value)}" if field.default_value is not None else ""

        return f"{field.name} {col_type}{nullable}{unique}{default}"

    def generate_firestore_rules(self, models: List[DataModel], auth_required: bool) -> str:
        """Generate Firestore security rules"""
        lines = [
            "rules_version = '2';",
            "service cloud.firestore {",
            "  match /databases/{database}/documents {"
        ]

        for model in models:
            lines.append(f"    match /{model.name}/{{docId}} {{")
            if auth_required:
                lines.append("      allow read: if request.auth != null;")
                lines.append("      allow create: if request.auth != null;")
                lines.append("      allow update: if request.auth != null;")
                lines.append("      allow delete: if request.auth != null;")
            else:
                lines.append("      allow read, write: if true;")
            lines.append("    }")

        lines.append("  }")
        lines.append("}")

        return "\n".join(lines)


class BackendGenerator:
    """Generates FastAPI backend code"""

    def generate(self, project: AppProject, intent: Dict) -> Dict[str, str]:
        """Generate all backend files"""
        files = {}

        # main.py
        files["backend/main.py"] = self._generate_main(project, intent)

        # models.py
        files["backend/models.py"] = self._generate_models(intent["data_models"])

        # database.py
        files["backend/database.py"] = self._generate_database(project.database_type)

        # routers
        for model in intent["data_models"]:
            files[f"backend/routers/{model.name}.py"] = self._generate_router(model)

        # auth
        if intent["auth_required"]:
            files["backend/routers/auth.py"] = self._generate_auth_router()

        # requirements.txt
        files["backend/requirements.txt"] = self._generate_requirements(project, intent)

        return files

    def _generate_main(self, project: AppProject, intent: Dict) -> str:
        """Generate main FastAPI app"""
        model_imports = ", ".join([f"{m.name}_router" for m in intent["data_models"]])
        router_includes = "\n".join([
            f'app.include_router({m.name}_router, prefix="/api/{m.name}", tags=["{m.display_name}"])'
            for m in intent["data_models"]
        ])

        auth_import = "from routers.auth import router as auth_router" if intent["auth_required"] else ""
        auth_include = 'app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])' if intent["auth_required"] else ""

        return f'''"""
{project.display_name} - Backend API
Generated by AI Team Studio
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_db
{"from routers." + ", ".join([m.name for m in intent["data_models"]]) + " import router as " + model_imports if intent["data_models"] else ""}
{auth_import}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title="{project.display_name}",
    description="{project.description}",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{router_includes}
{auth_include}


@app.get("/")
async def root():
    return {{"message": "Welcome to {project.display_name} API", "docs": "/docs"}}


@app.get("/health")
async def health():
    return {{"status": "healthy"}}
'''

    def _generate_models(self, models: List[DataModel]) -> str:
        """Generate Pydantic models"""
        code = '''"""
Pydantic Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


'''
        for model in models:
            # Base model
            fields = []
            for field in model.fields:
                py_type = self._python_type(field.field_type)
                optional = "" if field.required else " = None"
                fields.append(f"    {field.name}: {py_type}{optional}")

            field_str = "\n".join(fields) if fields else "    pass"

            # Create optional version for Update model
            update_fields = []
            for field in model.fields:
                py_type = self._python_type(field.field_type)
                update_fields.append(f"    {field.name}: Optional[{py_type}] = None")
            update_field_str = "\n".join(update_fields) if update_fields else "    pass"

            code += f'''
class {model.display_name}Base(BaseModel):
{field_str}


class {model.display_name}Create({model.display_name}Base):
    pass


class {model.display_name}Update(BaseModel):
{update_field_str}


class {model.display_name}({model.display_name}Base):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


'''
        return code

    def _python_type(self, field_type: str) -> str:
        """Convert field type to Python type"""
        type_map = {
            "string": "str",
            "text": "str",
            "email": "str",
            "password": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "date": "datetime",
            "datetime": "datetime",
            "file": "str",
            "json": "dict",
        }
        return type_map.get(field_type, "str")

    def _generate_database(self, db_type: str) -> str:
        """Generate database connection code"""
        if db_type == "sqlite":
            return '''"""
Database Configuration - SQLite
"""

import aiosqlite
from pathlib import Path

DATABASE_PATH = Path("database/app.db")


async def init_db():
    """Initialize database"""
    DATABASE_PATH.parent.mkdir(exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Read and execute schema
        schema_path = Path("database/schema.sql")
        if schema_path.exists():
            schema = schema_path.read_text()
            await db.executescript(schema)
            await db.commit()


async def get_db():
    """Get database connection"""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
'''
        else:
            return '''"""
Database Configuration - Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore


def init_db():
    """Initialize Firestore"""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firestore.client()


db = None

def get_db():
    """Get Firestore client"""
    global db
    if db is None:
        db = init_db()
    return db
'''

    def _generate_router(self, model: DataModel) -> str:
        """Generate CRUD router for a model"""
        name = model.name
        display = model.display_name

        return f'''"""
{display} API Router
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import {display}, {display}Create, {display}Update
from database import get_db

router = APIRouter()


@router.get("/", response_model=List[{display}])
async def list_{name}(skip: int = 0, limit: int = 100, db=Depends(get_db)):
    """List all {name}"""
    cursor = await db.execute("SELECT * FROM {name} LIMIT ? OFFSET ?", (limit, skip))
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{{id}}", response_model={display})
async def get_{name}(id: int, db=Depends(get_db)):
    """Get {name} by ID"""
    cursor = await db.execute("SELECT * FROM {name} WHERE id = ?", (id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="{display} not found")
    return dict(row)


@router.post("/", response_model={display})
async def create_{name}(item: {display}Create, db=Depends(get_db)):
    """Create new {name}"""
    data = item.model_dump()
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])

    cursor = await db.execute(
        f"INSERT INTO {name} ({{columns}}) VALUES ({{placeholders}})",
        tuple(data.values())
    )
    await db.commit()

    return await get_{name}(cursor.lastrowid, db)


@router.put("/{{id}}", response_model={display})
async def update_{name}(id: int, item: {display}Update, db=Depends(get_db)):
    """Update {name}"""
    data = {{k: v for k, v in item.model_dump().items() if v is not None}}
    if not data:
        return await get_{name}(id, db)

    set_clause = ", ".join([f"{{k}} = ?" for k in data.keys()])

    await db.execute(
        f"UPDATE {name} SET {{set_clause}}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*data.values(), id)
    )
    await db.commit()

    return await get_{name}(id, db)


@router.delete("/{{id}}")
async def delete_{name}(id: int, db=Depends(get_db)):
    """Delete {name}"""
    await db.execute("DELETE FROM {name} WHERE id = ?", (id,))
    await db.commit()
    return {{"message": "{display} deleted"}}
'''

    def _generate_auth_router(self) -> str:
        """Generate authentication router"""
        return '''"""
Authentication Router
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import hashlib
import os

router = APIRouter()
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user"""
    # In production, validate against database
    # This is a placeholder
    token = create_token(1, request.email)
    return TokenResponse(access_token=token)


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """Register new user"""
    # In production, save to database
    # This is a placeholder
    token = create_token(1, request.email)
    return TokenResponse(access_token=token)


@router.get("/me")
async def get_current_user(payload: dict = Depends(verify_token)):
    """Get current user"""
    return {"user_id": payload["sub"], "email": payload["email"]}
'''

    def _generate_requirements(self, project: AppProject, intent: Dict) -> str:
        """Generate requirements.txt"""
        reqs = [
            "fastapi>=0.109.0",
            "uvicorn>=0.27.0",
            "pydantic>=2.0.0",
        ]

        if project.database_type == "sqlite":
            reqs.append("aiosqlite>=0.19.0")
        elif project.database_type == "firestore":
            reqs.append("firebase-admin>=6.0.0")

        if intent["auth_required"]:
            reqs.append("pyjwt>=2.8.0")

        return "\n".join(reqs)


class FrontendGenerator:
    """Generates frontend HTML/CSS/JS"""

    def generate(self, project: AppProject) -> Dict[str, str]:
        """Generate all frontend files"""
        files = {}

        # index.html
        files["frontend/index.html"] = self._generate_index(project)

        # CSS
        files["frontend/css/styles.css"] = self._generate_styles()

        # JavaScript
        files["frontend/js/app.js"] = self._generate_app_js(project)
        files["frontend/js/api.js"] = self._generate_api_js()

        # Page files
        for page in project.pages:
            files[f"frontend/pages/{page.name.lower().replace(' ', '-')}.html"] = self._generate_page(page, project)

        return files

    def _generate_index(self, project: AppProject) -> str:
        """Generate main index.html"""
        nav_links = "\n            ".join([
            f'<a href="pages/{p.name.lower().replace(" ", "-")}.html">{p.name}</a>'
            for p in project.pages
        ])

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project.display_name}</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <nav class="navbar">
        <div class="navbar-brand">{project.display_name}</div>
        <div class="navbar-links">
            {nav_links}
        </div>
    </nav>

    <main class="container">
        <h1>Welcome to {project.display_name}</h1>
        <p>{project.description}</p>
    </main>

    <script src="js/api.js"></script>
    <script src="js/app.js"></script>
</body>
</html>
'''

    def _generate_page(self, page: Page, project: AppProject) -> str:
        """Generate a page HTML file"""
        components_html = "\n        ".join([
            self._render_component(c) for c in page.components
        ])

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.name} - {project.display_name}</title>
    <link rel="stylesheet" href="../css/styles.css">
</head>
<body>
    <nav class="navbar">
        <a href="../index.html" class="navbar-brand">{project.display_name}</a>
    </nav>

    <main class="container">
        <h1>{page.name}</h1>
        {components_html if components_html else "<p>Page content goes here.</p>"}
    </main>

    <script src="../js/api.js"></script>
    <script src="../js/app.js"></script>
</body>
</html>
'''

    def _render_component(self, component: Component) -> str:
        """Render component to HTML"""
        renderers = {
            "heading": lambda c: f'<h{c.properties.get("level", 1)}>{c.properties.get("text", "")}</h{c.properties.get("level", 1)}>',
            "paragraph": lambda c: f'<p>{c.properties.get("text", "")}</p>',
            "text_field": lambda c: f'''
<div class="form-group">
    <label>{c.properties.get("label", "Text")}</label>
    <input type="text" name="{c.data_binding or c.name}" placeholder="{c.properties.get("placeholder", "")}" {"required" if c.properties.get("required") else ""}>
</div>''',
            "email_field": lambda c: f'''
<div class="form-group">
    <label>{c.properties.get("label", "Email")}</label>
    <input type="email" name="{c.data_binding or c.name}" {"required" if c.properties.get("required") else ""}>
</div>''',
            "button": lambda c: f'<button class="btn btn-{c.properties.get("variant", "primary")}">{c.properties.get("label", "Button")}</button>',
            "submit_button": lambda c: f'<button type="submit" class="btn btn-primary">{c.properties.get("label", "Submit")}</button>',
            "card": lambda c: f'''
<div class="card">
    {"<h3>" + c.properties.get("title") + "</h3>" if c.properties.get("title") else ""}
    {"".join([self._render_component(child) for child in c.children])}
</div>''',
            "form": lambda c: f'''
<form class="form" data-model="{c.properties.get("model", "")}">
    {"".join([self._render_component(child) for child in c.children])}
</form>''',
        }

        renderer = renderers.get(component.component_type, lambda c: f'<!-- {c.component_type} -->')
        return renderer(component)

    def _generate_styles(self) -> str:
        """Generate CSS styles"""
        return '''/* Generated Styles */
:root {
    --primary: #3b82f6;
    --primary-dark: #2563eb;
    --secondary: #64748b;
    --success: #22c55e;
    --danger: #ef4444;
    --background: #f8fafc;
    --surface: #ffffff;
    --text: #1e293b;
    --text-light: #64748b;
    --border: #e2e8f0;
    --radius: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.1);
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: system-ui, -apple-system, sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

.navbar {
    background: var(--surface);
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow);
    position: sticky;
    top: 0;
    z-index: 100;
}

.navbar-brand {
    font-weight: 600;
    font-size: 1.25rem;
    color: var(--text);
    text-decoration: none;
}

.navbar-links {
    display: flex;
    gap: 1.5rem;
}

.navbar-links a {
    color: var(--text-light);
    text-decoration: none;
}

.navbar-links a:hover {
    color: var(--primary);
}

.btn {
    padding: 0.625rem 1.25rem;
    border: none;
    border-radius: var(--radius);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-dark);
}

.btn-secondary {
    background: var(--secondary);
    color: white;
}

.card {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: var(--text);
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;
    padding: 0.625rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 0.875rem;
}

.form-group input:focus,
.form-group textarea:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

table {
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
}

th, td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
}

th {
    background: var(--background);
    font-weight: 600;
}

.stat-card {
    background: var(--surface);
    padding: 1.5rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
}

.stat-card .value {
    font-size: 2rem;
    font-weight: 600;
    color: var(--primary);
}

.stat-card .label {
    color: var(--text-light);
}
'''

    def _generate_app_js(self, project: AppProject) -> str:
        """Generate main JavaScript"""
        return f'''// {project.display_name} - Frontend JavaScript

document.addEventListener('DOMContentLoaded', () => {{
    console.log('{project.display_name} loaded');

    // Handle forms
    document.querySelectorAll('form[data-model]').forEach(form => {{
        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            const model = form.dataset.model;
            const formData = new FormData(form);
            const data = Object.fromEntries(formData);

            try {{
                const result = await api.create(model, data);
                alert('Saved successfully!');
                form.reset();
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }});
    }});
}});
'''

    def _generate_api_js(self) -> str:
        """Generate API client JavaScript"""
        return '''// API Client
const API_BASE = 'http://localhost:8000/api';

const api = {
    async request(endpoint, method = 'GET', data = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };

        if (data) options.body = JSON.stringify(data);

        const token = localStorage.getItem('token');
        if (token) options.headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            throw new Error(await response.text());
        }
        return response.json();
    },

    list(model) { return this.request(`/${model}`); },
    get(model, id) { return this.request(`/${model}/${id}`); },
    create(model, data) { return this.request(`/${model}`, 'POST', data); },
    update(model, id, data) { return this.request(`/${model}/${id}`, 'PUT', data); },
    delete(model, id) { return this.request(`/${model}/${id}`, 'DELETE'); },
};

// Auth helpers
const auth = {
    async login(email, password) {
        const result = await api.request('/auth/login', 'POST', { email, password });
        localStorage.setItem('token', result.access_token);
        return result;
    },

    async signup(name, email, password) {
        const result = await api.request('/auth/signup', 'POST', { name, email, password });
        localStorage.setItem('token', result.access_token);
        return result;
    },

    logout() {
        localStorage.removeItem('token');
        window.location.href = '/login';
    },

    isLoggedIn() {
        return !!localStorage.getItem('token');
    }
};
'''


class AppGenerator:
    """Main generator that orchestrates all generators"""

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.schema_generator = SchemaGenerator()
        self.backend_generator = BackendGenerator()
        self.frontend_generator = FrontendGenerator()

    def generate(self, project: AppProject, output_dir: str = None) -> Dict[str, Any]:
        """Generate complete application"""
        result = {
            "success": False,
            "files": {},
            "log": [],
            "output_dir": output_dir or f"./{project.name}"
        }

        try:
            # Step 1: Analyze intent
            result["log"].append("Analyzing application requirements...")
            intent = self.intent_detector.analyze_project(project)
            result["log"].append(f"Detected {len(intent['data_models'])} data models")
            result["log"].append(f"Auth required: {intent['auth_required']}")

            # Step 2: Generate database schema
            result["log"].append("Generating database schema...")
            if project.database_type == "sqlite":
                schema = self.schema_generator.generate_sqlite(intent["data_models"])
                result["files"]["database/schema.sql"] = schema
            else:
                rules = self.schema_generator.generate_firestore_rules(
                    intent["data_models"], intent["auth_required"]
                )
                result["files"]["database/firestore.rules"] = rules

            # Step 3: Generate backend
            result["log"].append("Generating backend API...")
            backend_files = self.backend_generator.generate(project, intent)
            result["files"].update(backend_files)

            # Step 4: Generate frontend
            result["log"].append("Generating frontend...")
            frontend_files = self.frontend_generator.generate(project)
            result["files"].update(frontend_files)

            # Step 5: Generate run script
            result["log"].append("Creating run scripts...")
            result["files"]["run.sh"] = self._generate_run_script(project)
            result["files"]["README.md"] = self._generate_readme(project)

            result["success"] = True
            result["log"].append("Generation complete!")

        except Exception as e:
            result["log"].append(f"Error: {str(e)}")
            result["error"] = str(e)

        return result

    def _generate_run_script(self, project: AppProject) -> str:
        """Generate run script"""
        return f'''#!/bin/bash
# Run {project.display_name}

echo "Starting {project.display_name}..."

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Start backend
echo "Starting API server on http://localhost:8000"
uvicorn main:app --reload --port 8000 &

# Start frontend (simple HTTP server)
cd ../frontend
echo "Starting frontend on http://localhost:5500"
python -m http.server 5500 &

echo ""
echo "App is running!"
echo "  Frontend: http://localhost:5500"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""

wait
'''

    def _generate_readme(self, project: AppProject) -> str:
        """Generate README"""
        return f'''# {project.display_name}

{project.description}

## Generated by AI Team Studio

### Quick Start

```bash
chmod +x run.sh
./run.sh
```

### Project Structure

```
{project.name}/
├── frontend/
│   ├── index.html
│   ├── pages/
│   ├── css/
│   └── js/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   └── routers/
├── database/
│   └── schema.sql
├── run.sh
└── README.md
```

### API Endpoints

Visit http://localhost:8000/docs for interactive API documentation.

### Database

- Type: {project.database_type.upper()}
- Schema: database/schema.sql

---
Generated with AI Team Studio
'''

    def save_to_disk(self, result: Dict, output_dir: str = None):
        """Save generated files to disk"""
        output_dir = output_dir or result.get("output_dir", "./output")
        output_path = Path(output_dir)

        for file_path, content in result["files"].items():
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        return str(output_path.absolute())
