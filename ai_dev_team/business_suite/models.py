"""
Business Suite Data Models
==========================

Core data structures for managing clients, projects, chatbots, and deployments.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid
import json
import os


class ClientStatus(Enum):
    PROSPECT = "prospect"
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHURNED = "churned"


class ProjectStatus(Enum):
    DISCOVERY = "discovery"
    REQUIREMENTS = "requirements"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYED = "deployed"
    MAINTENANCE = "maintenance"


class ChatBotStatus(Enum):
    DRAFT = "draft"
    TESTING = "testing"
    LIVE = "live"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DeploymentType(Enum):
    MANAGED_CLOUD = "managed_cloud"
    SELF_HOSTED = "self_hosted"
    EMBED_WIDGET = "embed_widget"
    API_ONLY = "api_only"


class PricingTier(Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


@dataclass
class Contact:
    """Contact person at a client company."""
    name: str
    email: str
    phone: str = ""
    role: str = ""
    is_primary: bool = False


@dataclass
class Client:
    """A business client."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    company_name: str = ""
    industry: str = ""
    website: str = ""
    contacts: List[Contact] = field(default_factory=list)
    status: str = "prospect"
    pricing_tier: str = "starter"
    monthly_value: float = 0.0
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "company_name": self.company_name,
            "industry": self.industry,
            "website": self.website,
            "contacts": [{"name": c.name, "email": c.email, "phone": c.phone,
                         "role": c.role, "is_primary": c.is_primary} for c in self.contacts],
            "status": self.status,
            "pricing_tier": self.pricing_tier,
            "monthly_value": self.monthly_value,
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_contact(self, name: str, email: str, phone: str = "", role: str = "", is_primary: bool = False):
        contact = Contact(name=name, email=email, phone=phone, role=role, is_primary=is_primary)
        self.contacts.append(contact)
        return contact


@dataclass
class Milestone:
    """Project milestone."""
    name: str
    due_date: str = ""
    completed: bool = False
    notes: str = ""


@dataclass
class Project:
    """A client project for building an AI chatbot."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    client_id: str = ""
    name: str = ""
    description: str = ""
    status: str = "discovery"
    requirements: Dict[str, Any] = field(default_factory=dict)
    milestones: List[Milestone] = field(default_factory=list)
    budget: float = 0.0
    start_date: str = ""
    target_date: str = ""
    chatbot_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "requirements": self.requirements,
            "milestones": [{"name": m.name, "due_date": m.due_date,
                          "completed": m.completed, "notes": m.notes} for m in self.milestones],
            "budget": self.budget,
            "start_date": self.start_date,
            "target_date": self.target_date,
            "chatbot_ids": self.chatbot_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_milestone(self, name: str, due_date: str = "", notes: str = ""):
        milestone = Milestone(name=name, due_date=due_date, notes=notes)
        self.milestones.append(milestone)
        return milestone


@dataclass
class Persona:
    """Chatbot personality configuration."""
    name: str = "Assistant"
    tone: str = "professional"  # professional, friendly, casual, formal
    language: str = "en"
    greeting: str = "Hello! How can I help you today?"
    fallback_message: str = "I'm sorry, I don't have information about that. Let me connect you with a human agent."
    personality_traits: List[str] = field(default_factory=list)
    restricted_topics: List[str] = field(default_factory=list)
    custom_instructions: str = ""


@dataclass
class ChatBot:
    """An AI chatbot configuration."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_id: str = ""
    name: str = ""
    description: str = ""
    model: str = "claude-sonnet"  # claude-sonnet, claude-opus, gpt-4o, gemini, grok
    persona: Persona = field(default_factory=Persona)
    system_prompt: str = ""
    knowledge_base_ids: List[str] = field(default_factory=list)
    status: str = "draft"
    temperature: float = 0.7
    max_tokens: int = 1024
    features: Dict[str, bool] = field(default_factory=lambda: {
        "memory": True,
        "citations": False,
        "escalation": True,
        "sentiment_detection": False,
        "multi_language": False,
    })
    widget_config: Dict[str, Any] = field(default_factory=lambda: {
        "position": "bottom-right",
        "primary_color": "#3b82f6",
        "header_text": "Chat with us",
        "show_branding": True,
    })
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "persona": {
                "name": self.persona.name,
                "tone": self.persona.tone,
                "language": self.persona.language,
                "greeting": self.persona.greeting,
                "fallback_message": self.persona.fallback_message,
                "personality_traits": self.persona.personality_traits,
                "restricted_topics": self.persona.restricted_topics,
                "custom_instructions": self.persona.custom_instructions,
            },
            "system_prompt": self.system_prompt,
            "knowledge_base_ids": self.knowledge_base_ids,
            "status": self.status,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "features": self.features,
            "widget_config": self.widget_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class KnowledgeSource:
    """A source of knowledge for the chatbot."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_type: str = "document"  # document, url, faq, database
    name: str = ""
    path_or_url: str = ""
    status: str = "pending"  # pending, processing, ready, error
    document_count: int = 0
    chunk_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class KnowledgeBase:
    """Knowledge base for training chatbots."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    sources: List[KnowledgeSource] = field(default_factory=list)
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50
    total_documents: int = 0
    total_chunks: int = 0
    status: str = "empty"  # empty, processing, ready
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sources": [{"id": s.id, "type": s.source_type, "name": s.name,
                        "path_or_url": s.path_or_url, "status": s.status,
                        "document_count": s.document_count, "chunk_count": s.chunk_count,
                        "last_updated": s.last_updated} for s in self.sources],
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_source(self, source_type: str, name: str, path_or_url: str):
        source = KnowledgeSource(source_type=source_type, name=name, path_or_url=path_or_url)
        self.sources.append(source)
        return source


@dataclass
class Deployment:
    """A deployed chatbot instance."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    chatbot_id: str = ""
    environment: str = "production"  # development, staging, production
    deployment_type: str = "embed_widget"
    url: str = ""
    api_key: str = ""
    embed_code: str = ""
    custom_domain: str = ""
    ssl_enabled: bool = True
    status: str = "pending"  # pending, deploying, live, error, stopped
    version: str = "1.0.0"
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "chatbot_id": self.chatbot_id,
            "environment": self.environment,
            "deployment_type": self.deployment_type,
            "url": self.url,
            "api_key": self.api_key,
            "embed_code": self.embed_code,
            "custom_domain": self.custom_domain,
            "ssl_enabled": self.ssl_enabled,
            "status": self.status,
            "version": self.version,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Message:
    """A message in a conversation."""
    role: str = "user"  # user, assistant, system
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation with the chatbot."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    deployment_id: str = ""
    session_id: str = ""
    user_id: str = ""
    messages: List[Message] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""
    satisfaction_score: int = 0  # 0-5
    resolved: bool = False
    escalated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "deployment_id": self.deployment_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [{"role": m.role, "content": m.content,
                         "timestamp": m.timestamp, "metadata": m.metadata} for m in self.messages],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "satisfaction_score": self.satisfaction_score,
            "resolved": self.resolved,
            "escalated": self.escalated,
            "metadata": self.metadata,
        }

    def add_message(self, role: str, content: str, metadata: Dict = None):
        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        return message


# ============================================================
# FACTORY FUNCTIONS
# ============================================================

def create_client(company_name: str, industry: str = "", contact_name: str = "",
                  contact_email: str = "", pricing_tier: str = "starter") -> Client:
    """Create a new client with optional primary contact."""
    client = Client(
        company_name=company_name,
        industry=industry,
        pricing_tier=pricing_tier,
        status="prospect"
    )
    if contact_name and contact_email:
        client.add_contact(name=contact_name, email=contact_email, is_primary=True)
    return client


def create_project(client_id: str, name: str, description: str = "",
                   budget: float = 0.0) -> Project:
    """Create a new project for a client."""
    project = Project(
        client_id=client_id,
        name=name,
        description=description,
        budget=budget,
        status="discovery"
    )
    # Add default milestones
    project.add_milestone("Requirements Gathering")
    project.add_milestone("Design & Architecture")
    project.add_milestone("Development")
    project.add_milestone("Testing & QA")
    project.add_milestone("Deployment")
    project.add_milestone("Training & Handoff")
    return project


def create_chatbot(project_id: str, name: str, model: str = "claude-sonnet",
                   persona_name: str = "Assistant", persona_tone: str = "professional") -> ChatBot:
    """Create a new chatbot for a project."""
    persona = Persona(name=persona_name, tone=persona_tone)
    chatbot = ChatBot(
        project_id=project_id,
        name=name,
        model=model,
        persona=persona,
        status="draft"
    )
    return chatbot


def create_knowledge_base(name: str, description: str = "") -> KnowledgeBase:
    """Create a new knowledge base."""
    return KnowledgeBase(name=name, description=description)


# ============================================================
# PERSISTENCE (Simple JSON file storage)
# ============================================================

class BusinessDataStore:
    """Simple JSON-based data store for business suite."""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/.ai-dev-team/business")
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_path(self, collection: str) -> str:
        return os.path.join(self.storage_dir, f"{collection}.json")

    def _load_collection(self, collection: str) -> List[Dict]:
        path = self._get_path(collection)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return []

    def _save_collection(self, collection: str, data: List[Dict]):
        path = self._get_path(collection)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def save_client(self, client: Client):
        clients = self._load_collection("clients")
        # Update or add
        found = False
        for i, c in enumerate(clients):
            if c["id"] == client.id:
                clients[i] = client.to_dict()
                found = True
                break
        if not found:
            clients.append(client.to_dict())
        self._save_collection("clients", clients)

    def get_clients(self) -> List[Dict]:
        return self._load_collection("clients")

    def get_client(self, client_id: str) -> Optional[Dict]:
        clients = self._load_collection("clients")
        for c in clients:
            if c["id"] == client_id:
                return c
        return None

    def save_project(self, project: Project):
        projects = self._load_collection("projects")
        found = False
        for i, p in enumerate(projects):
            if p["id"] == project.id:
                projects[i] = project.to_dict()
                found = True
                break
        if not found:
            projects.append(project.to_dict())
        self._save_collection("projects", projects)

    def get_projects(self, client_id: str = None) -> List[Dict]:
        projects = self._load_collection("projects")
        if client_id:
            return [p for p in projects if p["client_id"] == client_id]
        return projects

    def save_chatbot(self, chatbot: ChatBot):
        chatbots = self._load_collection("chatbots")
        found = False
        for i, c in enumerate(chatbots):
            if c["id"] == chatbot.id:
                chatbots[i] = chatbot.to_dict()
                found = True
                break
        if not found:
            chatbots.append(chatbot.to_dict())
        self._save_collection("chatbots", chatbots)

    def get_chatbots(self, project_id: str = None) -> List[Dict]:
        chatbots = self._load_collection("chatbots")
        if project_id:
            return [c for c in chatbots if c["project_id"] == project_id]
        return chatbots

    def save_deployment(self, deployment: Deployment):
        deployments = self._load_collection("deployments")
        found = False
        for i, d in enumerate(deployments):
            if d["id"] == deployment.id:
                deployments[i] = deployment.to_dict()
                found = True
                break
        if not found:
            deployments.append(deployment.to_dict())
        self._save_collection("deployments", deployments)

    def get_deployments(self, chatbot_id: str = None) -> List[Dict]:
        deployments = self._load_collection("deployments")
        if chatbot_id:
            return [d for d in deployments if d["chatbot_id"] == chatbot_id]
        return deployments
