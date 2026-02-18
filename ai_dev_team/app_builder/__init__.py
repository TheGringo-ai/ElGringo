"""
AI Team App Builder
===================

No-code application builder that generates complete apps from visual designs.

Features:
- Visual component palette
- Natural language app creation
- Auto-generated backend (FastAPI)
- Auto-generated database (SQLite/Firestore)
- Production-ready code export
"""

from .models import (
    AppProject,
    Page,
    Component,
    DataModel,
    DataField,
    create_default_project,
)

from .components import (
    COMPONENT_PALETTE,
    APP_TYPE_TEMPLATES,
    COMPONENT_TEMPLATES,
    FULL_APP_TEMPLATES,
    get_component_by_type,
    get_all_component_types,
    get_template_by_name,
    get_app_template,
    get_full_app_template,
    count_components,
)

from .generator import (
    VisualAppBuilder,
    IntentDetector,
    SchemaGenerator,
    BackendGenerator,
    FrontendGenerator,
)

__all__ = [
    # Models
    "AppProject",
    "Page",
    "Component",
    "DataModel",
    "DataField",
    "create_default_project",
    # Components
    "COMPONENT_PALETTE",
    "APP_TYPE_TEMPLATES",
    "COMPONENT_TEMPLATES",
    "FULL_APP_TEMPLATES",
    "get_component_by_type",
    "get_all_component_types",
    "get_template_by_name",
    "get_app_template",
    "get_full_app_template",
    "count_components",
    # Generators
    "AppGenerator",
    "IntentDetector",
    "SchemaGenerator",
    "BackendGenerator",
    "FrontendGenerator",
]
