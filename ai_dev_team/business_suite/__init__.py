"""
AI Business Development Suite
=============================

Complete platform for building and delivering AI chat solutions to clients.

Features:
- Client Management & CRM
- AI Chat Builder
- Knowledge Base Management
- Integration Hub (APIs, Webhooks, Embeds)
- Deployment & Hosting
- Analytics & Monitoring
- Billing & Licensing
- White-Label Branding
"""

from .models import (
    Client,
    Project,
    ChatBot,
    KnowledgeBase,
    Deployment,
    Conversation,
    create_client,
    create_project,
)

from .chat_builder import (
    ChatBotBuilder,
    PersonaTemplate,
    ConversationFlow,
)

from .integrations import (
    APIKeyManager,
    WebhookManager,
    EmbedCodeGenerator,
)

__all__ = [
    # Models
    "Client",
    "Project",
    "ChatBot",
    "KnowledgeBase",
    "Deployment",
    "Conversation",
    "create_client",
    "create_project",
    # Chat Builder
    "ChatBotBuilder",
    "PersonaTemplate",
    "ConversationFlow",
    # Integrations
    "APIKeyManager",
    "WebhookManager",
    "EmbedCodeGenerator",
]
