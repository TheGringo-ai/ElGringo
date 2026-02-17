"""
App Builder Data Models
=======================

Core data structures for the no-code app builder.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid
from datetime import datetime


class ComponentCategory(Enum):
    LAYOUT = "layout"
    INPUT = "input"
    DISPLAY = "display"
    ACTION = "action"
    DATA = "data"
    AUTH = "auth"


class FieldType(Enum):
    STRING = "string"
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    PASSWORD = "password"
    FILE = "file"
    ARRAY = "array"
    REFERENCE = "reference"
    JSON = "json"


class DatabaseType(Enum):
    SQLITE = "sqlite"
    FIRESTORE = "firestore"
    POSTGRESQL = "postgresql"


@dataclass
class Component:
    """A UI component in the app"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    component_type: str = ""  # "text_field", "button", "table", etc.
    name: str = ""
    category: str = "input"
    properties: Dict[str, Any] = field(default_factory=dict)
    data_binding: Optional[str] = None  # Field it binds to
    validation: Dict[str, Any] = field(default_factory=dict)
    children: List['Component'] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.component_type,
            "name": self.name,
            "category": self.category,
            "properties": self.properties,
            "data_binding": self.data_binding,
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class Page:
    """A page in the application"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Home"
    route: str = "/"
    components: List[Component] = field(default_factory=list)
    requires_auth: bool = False
    layout: str = "single"  # single, sidebar, split

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "route": self.route,
            "components": [c.to_dict() for c in self.components],
            "requires_auth": self.requires_auth,
            "layout": self.layout
        }


@dataclass
class DataField:
    """A field in a data model"""
    name: str
    field_type: str = "string"  # string, number, boolean, date, etc.
    required: bool = False
    unique: bool = False
    default_value: Any = None
    reference_to: Optional[str] = None  # For foreign keys

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.field_type,
            "required": self.required,
            "unique": self.unique,
            "default": self.default_value,
            "reference": self.reference_to
        }


@dataclass
class DataModel:
    """A data model (table/collection)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""  # lowercase, e.g., "users"
    display_name: str = ""  # e.g., "Users"
    fields: List[DataField] = field(default_factory=list)
    timestamps: bool = True  # created_at, updated_at
    soft_delete: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "fields": [f.to_dict() for f in self.fields],
            "timestamps": self.timestamps,
            "soft_delete": self.soft_delete
        }


@dataclass
class APIEndpoint:
    """An API endpoint"""
    path: str
    method: str = "GET"  # GET, POST, PUT, DELETE
    model: str = ""
    operation: str = "list"  # list, get, create, update, delete, custom
    requires_auth: bool = True

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "method": self.method,
            "model": self.model,
            "operation": self.operation,
            "requires_auth": self.requires_auth
        }


@dataclass
class AppProject:
    """Complete application project"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "my-app"
    display_name: str = "My App"
    description: str = ""
    app_type: str = "web_app"  # web_app, dashboard, ecommerce, blog, crud
    pages: List[Page] = field(default_factory=list)
    data_models: List[DataModel] = field(default_factory=list)
    endpoints: List[APIEndpoint] = field(default_factory=list)
    auth_enabled: bool = False
    database_type: str = "sqlite"  # sqlite, firestore, postgresql
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "app_type": self.app_type,
            "pages": [p.to_dict() for p in self.pages],
            "data_models": [m.to_dict() for m in self.data_models],
            "auth_enabled": self.auth_enabled,
            "database_type": self.database_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def add_page(self, name: str, route: str = None, requires_auth: bool = False) -> Page:
        """Add a new page to the project"""
        if route is None:
            route = "/" + name.lower().replace(" ", "-")
        page = Page(name=name, route=route, requires_auth=requires_auth)
        self.pages.append(page)
        return page

    def add_model(self, name: str, fields: List[Dict] = None) -> DataModel:
        """Add a new data model"""
        model = DataModel(
            name=name.lower().replace(" ", "_"),
            display_name=name,
            fields=[DataField(**f) for f in (fields or [])]
        )
        self.data_models.append(model)
        return model

    def get_page(self, name: str) -> Optional[Page]:
        """Get page by name"""
        for page in self.pages:
            if page.name.lower() == name.lower():
                return page
        return None

    def get_model(self, name: str) -> Optional[DataModel]:
        """Get model by name"""
        for model in self.data_models:
            if model.name.lower() == name.lower():
                return model
        return None


def create_default_project(name: str = "my-app", app_type: str = "web_app") -> AppProject:
    """Create a new project with default pages based on app type"""
    project = AppProject(
        name=name.lower().replace(" ", "-"),
        display_name=name.title(),
        app_type=app_type
    )

    # Add default pages based on app type
    if app_type == "web_app":
        project.add_page("Home", "/")
        project.add_page("About", "/about")
        project.add_page("Contact", "/contact")

    elif app_type == "dashboard":
        project.add_page("Login", "/login")
        project.add_page("Dashboard", "/dashboard", requires_auth=True)
        project.add_page("Users", "/users", requires_auth=True)
        project.add_page("Settings", "/settings", requires_auth=True)
        project.auth_enabled = True

    elif app_type == "ecommerce":
        project.add_page("Home", "/")
        project.add_page("Products", "/products")
        project.add_page("Product Detail", "/products/:id")
        project.add_page("Cart", "/cart")
        project.add_page("Checkout", "/checkout", requires_auth=True)
        project.add_page("Login", "/login")
        project.auth_enabled = True

    elif app_type == "blog":
        project.add_page("Home", "/")
        project.add_page("Blog", "/blog")
        project.add_page("Post", "/blog/:slug")
        project.add_page("Admin", "/admin", requires_auth=True)
        project.auth_enabled = True

    elif app_type == "crud":
        project.add_page("List", "/")
        project.add_page("Create", "/create")
        project.add_page("Edit", "/edit/:id")
        project.add_page("View", "/view/:id")

    return project
