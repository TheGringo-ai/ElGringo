"""
Integration Tools
=================

API keys, webhooks, and embed code generation for chatbot deployment.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import secrets
import hashlib
import json
import html


# ============================================================
# API KEY MANAGEMENT
# ============================================================

@dataclass
class APIKey:
    """An API key for accessing a chatbot."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    key: str = field(default_factory=lambda: f"sk-{secrets.token_hex(24)}")
    name: str = ""
    deployment_id: str = ""
    permissions: List[str] = field(default_factory=lambda: ["chat"])
    rate_limit: int = 100  # requests per minute
    monthly_quota: int = 10000  # total monthly requests
    usage_count: int = 0
    last_used: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: str = ""
    is_active: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "key": self.key[:8] + "..." + self.key[-4:],  # Masked
            "name": self.name,
            "deployment_id": self.deployment_id,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "monthly_quota": self.monthly_quota,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
        }


class APIKeyManager:
    """Manages API keys for chatbot deployments."""

    PERMISSIONS = [
        "chat",           # Send/receive messages
        "history",        # Access conversation history
        "analytics",      # View analytics
        "knowledge",      # Manage knowledge base
        "settings",       # Modify settings
        "admin",          # Full access
    ]

    def __init__(self):
        self.keys: Dict[str, APIKey] = {}

    def create_key(self, name: str, deployment_id: str,
                  permissions: List[str] = None,
                  rate_limit: int = 100,
                  monthly_quota: int = 10000) -> APIKey:
        """Create a new API key."""
        key = APIKey(
            name=name,
            deployment_id=deployment_id,
            permissions=permissions or ["chat"],
            rate_limit=rate_limit,
            monthly_quota=monthly_quota,
        )
        self.keys[key.id] = key
        return key

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID."""
        return self.keys.get(key_id)

    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """Validate an API key string and return the key object if valid."""
        for key in self.keys.values():
            if key.key == api_key and key.is_active:
                return key
        return None

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self.keys:
            self.keys[key_id].is_active = False
            return True
        return False

    def rotate_key(self, key_id: str) -> Optional[APIKey]:
        """Rotate an API key (create new, revoke old)."""
        old_key = self.keys.get(key_id)
        if old_key:
            new_key = self.create_key(
                name=old_key.name,
                deployment_id=old_key.deployment_id,
                permissions=old_key.permissions,
                rate_limit=old_key.rate_limit,
                monthly_quota=old_key.monthly_quota,
            )
            self.revoke_key(key_id)
            return new_key
        return None

    def list_keys(self, deployment_id: str = None) -> List[APIKey]:
        """List all API keys, optionally filtered by deployment."""
        keys = list(self.keys.values())
        if deployment_id:
            keys = [k for k in keys if k.deployment_id == deployment_id]
        return keys

    def record_usage(self, key_id: str):
        """Record API key usage."""
        if key_id in self.keys:
            self.keys[key_id].usage_count += 1
            self.keys[key_id].last_used = datetime.now().isoformat()


# ============================================================
# WEBHOOK MANAGEMENT
# ============================================================

@dataclass
class Webhook:
    """A webhook configuration."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    url: str = ""
    deployment_id: str = ""
    events: List[str] = field(default_factory=list)
    secret: str = field(default_factory=lambda: secrets.token_hex(16))
    headers: Dict[str, str] = field(default_factory=dict)
    is_active: bool = True
    retry_count: int = 3
    timeout: int = 30
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "deployment_id": self.deployment_id,
            "events": self.events,
            "secret": self.secret[:8] + "...",
            "headers": self.headers,
            "is_active": self.is_active,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "created_at": self.created_at,
        }


class WebhookManager:
    """Manages webhooks for chatbot events."""

    EVENTS = [
        "conversation.started",
        "conversation.ended",
        "message.received",
        "message.sent",
        "escalation.requested",
        "feedback.received",
        "error.occurred",
    ]

    def __init__(self):
        self.webhooks: Dict[str, Webhook] = {}

    def create_webhook(self, name: str, url: str, deployment_id: str,
                      events: List[str] = None,
                      headers: Dict[str, str] = None) -> Webhook:
        """Create a new webhook."""
        webhook = Webhook(
            name=name,
            url=url,
            deployment_id=deployment_id,
            events=events or ["conversation.started", "conversation.ended"],
            headers=headers or {},
        )
        self.webhooks[webhook.id] = webhook
        return webhook

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self.webhooks.get(webhook_id)

    def update_webhook(self, webhook_id: str, **kwargs) -> Optional[Webhook]:
        """Update a webhook."""
        webhook = self.webhooks.get(webhook_id)
        if webhook:
            for key, value in kwargs.items():
                if hasattr(webhook, key):
                    setattr(webhook, key, value)
            return webhook
        return None

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            return True
        return False

    def list_webhooks(self, deployment_id: str = None) -> List[Webhook]:
        """List all webhooks, optionally filtered by deployment."""
        webhooks = list(self.webhooks.values())
        if deployment_id:
            webhooks = [w for w in webhooks if w.deployment_id == deployment_id]
        return webhooks

    def generate_signature(self, webhook: Webhook, payload: str) -> str:
        """Generate HMAC signature for webhook payload."""
        return hashlib.sha256(
            f"{webhook.secret}{payload}".encode()
        ).hexdigest()

    def get_sample_payload(self, event: str) -> Dict:
        """Get a sample payload for an event type."""
        samples = {
            "conversation.started": {
                "event": "conversation.started",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "deployment_id": "dep_456",
                    "session_id": "sess_789",
                    "user_agent": "Mozilla/5.0...",
                    "ip_address": "192.168.1.1",
                }
            },
            "conversation.ended": {
                "event": "conversation.ended",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "deployment_id": "dep_456",
                    "message_count": 5,
                    "duration_seconds": 120,
                    "resolved": True,
                }
            },
            "message.received": {
                "event": "message.received",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "message_id": "msg_001",
                    "content": "Hello, I have a question",
                    "role": "user",
                }
            },
            "message.sent": {
                "event": "message.sent",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "message_id": "msg_002",
                    "content": "Hello! How can I help you?",
                    "role": "assistant",
                }
            },
            "escalation.requested": {
                "event": "escalation.requested",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "reason": "user_requested",
                    "messages": [],
                }
            },
            "feedback.received": {
                "event": "feedback.received",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "message_id": "msg_002",
                    "rating": "positive",  # positive, negative
                    "comment": "",
                }
            },
            "error.occurred": {
                "event": "error.occurred",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "conversation_id": "conv_123",
                    "error_type": "api_error",
                    "error_message": "Rate limit exceeded",
                }
            },
        }
        return samples.get(event, {"event": event, "data": {}})


# ============================================================
# EMBED CODE GENERATOR
# ============================================================

class EmbedCodeGenerator:
    """Generates embed codes for chatbot widgets."""

    def __init__(self):
        self.cdn_url = "https://cdn.aiteamstudio.com/widget/v1"

    def generate_embed_code(self, deployment_id: str, api_key: str,
                           config: Dict = None) -> str:
        """Generate JavaScript embed code for a chatbot widget."""
        config = config or {}

        # Default configuration
        widget_config = {
            "deploymentId": deployment_id,
            "apiKey": api_key,
            "position": config.get("position", "bottom-right"),
            "primaryColor": config.get("primary_color", "#3b82f6"),
            "headerText": config.get("header_text", "Chat with us"),
            "showBranding": config.get("show_branding", True),
            "autoOpen": config.get("auto_open", False),
            "openDelay": config.get("open_delay", 0),
            "greeting": config.get("greeting", ""),
        }

        config_json = json.dumps(widget_config, indent=4)

        embed_code = f'''<!-- AI Team Studio Chat Widget -->
<script>
  window.AIChatConfig = {config_json};
</script>
<script src="{self.cdn_url}/chat-widget.js" async></script>
'''
        return embed_code

    def generate_react_component(self, deployment_id: str, api_key: str,
                                config: Dict = None) -> str:
        """Generate React component code for embedding."""
        config = config or {}

        props = {
            "deploymentId": deployment_id,
            "apiKey": api_key,
            **{k: v for k, v in config.items()}
        }

        props_str = ",\n      ".join([f'{k}="{v}"' if isinstance(v, str) else f'{k}={{{v}}}' for k, v in props.items()])

        react_code = f'''// Install: npm install @aiteamstudio/react-chat
import {{ ChatWidget }} from '@aiteamstudio/react-chat';

function App() {{
  return (
    <div>
      {{/* Your app content */}}
      <ChatWidget
        {props_str}
      />
    </div>
  );
}}

export default App;
'''
        return react_code

    def generate_iframe_embed(self, deployment_id: str, width: str = "400px",
                             height: str = "600px") -> str:
        """Generate iframe embed code."""
        iframe_code = f'''<!-- AI Team Studio Chat Widget (iframe) -->
<iframe
  src="https://chat.aiteamstudio.com/embed/{deployment_id}"
  width="{width}"
  height="{height}"
  frameborder="0"
  allow="microphone"
  style="border: none; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
></iframe>
'''
        return iframe_code

    def generate_api_example(self, api_key: str, deployment_id: str) -> str:
        """Generate REST API usage example."""
        api_example = f'''# AI Team Studio Chat API

## Send a message

```bash
curl -X POST https://api.aiteamstudio.com/v1/chat \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "deployment_id": "{deployment_id}",
    "session_id": "user_session_123",
    "message": "Hello, I have a question"
  }}'
```

## Response

```json
{{
  "id": "msg_abc123",
  "role": "assistant",
  "content": "Hello! How can I help you today?",
  "created_at": "2024-01-15T10:30:00Z"
}}
```

## Python Example

```python
import requests

response = requests.post(
    "https://api.aiteamstudio.com/v1/chat",
    headers={{
        "Authorization": "Bearer {api_key}",
        "Content-Type": "application/json"
    }},
    json={{
        "deployment_id": "{deployment_id}",
        "session_id": "user_session_123",
        "message": "Hello!"
    }}
)

print(response.json())
```

## JavaScript Example

```javascript
const response = await fetch('https://api.aiteamstudio.com/v1/chat', {{
  method: 'POST',
  headers: {{
    'Authorization': 'Bearer {api_key}',
    'Content-Type': 'application/json'
  }},
  body: JSON.stringify({{
    deployment_id: '{deployment_id}',
    session_id: 'user_session_123',
    message: 'Hello!'
  }})
}});

const data = await response.json();
console.log(data);
```
'''
        return api_example

    def generate_full_page_chat(self, deployment_id: str, api_key: str,
                               config: Dict = None) -> str:
        """Generate a complete HTML page with the chat widget."""
        config = config or {}
        primary_color = config.get("primary_color", "#3b82f6")
        header_text = html.escape(config.get("header_text", "Chat with us"))
        company_name = html.escape(config.get("company_name", "Company"))

        full_page = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{header_text} - {company_name}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background: {primary_color};
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 600;
        }}
        .chat-container {{
            flex: 1;
            max-width: 800px;
            margin: 20px auto;
            width: 100%;
            padding: 0 20px;
        }}
        #chat-widget {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            height: calc(100vh - 160px);
            min-height: 500px;
        }}
        .footer {{
            text-align: center;
            padding: 16px;
            color: #64748b;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{header_text}</h1>
    </div>
    <div class="chat-container">
        <div id="chat-widget"></div>
    </div>
    <div class="footer">
        Powered by AI Team Studio
    </div>

    <script>
        window.AIChatConfig = {{
            deploymentId: "{deployment_id}",
            apiKey: "{api_key}",
            container: "#chat-widget",
            mode: "inline",
            primaryColor: "{primary_color}",
            showBranding: true
        }};
    </script>
    <script src="{self.cdn_url}/chat-widget.js" async></script>
</body>
</html>
'''
        return full_page


# ============================================================
# CRM INTEGRATIONS
# ============================================================

CRM_INTEGRATIONS = {
    "salesforce": {
        "name": "Salesforce",
        "description": "Sync leads and conversations with Salesforce CRM",
        "auth_type": "oauth2",
        "fields_mapping": {
            "lead": ["Name", "Email", "Phone", "Company", "Description"],
            "case": ["Subject", "Description", "Status", "Priority"],
        },
        "events": ["conversation.ended", "escalation.requested"],
    },
    "hubspot": {
        "name": "HubSpot",
        "description": "Create contacts and deals from chat conversations",
        "auth_type": "oauth2",
        "fields_mapping": {
            "contact": ["firstname", "lastname", "email", "phone"],
            "deal": ["dealname", "amount", "dealstage"],
        },
        "events": ["conversation.ended", "escalation.requested"],
    },
    "zendesk": {
        "name": "Zendesk",
        "description": "Create support tickets from escalated chats",
        "auth_type": "api_key",
        "fields_mapping": {
            "ticket": ["subject", "description", "priority", "tags"],
        },
        "events": ["escalation.requested"],
    },
    "intercom": {
        "name": "Intercom",
        "description": "Sync conversations with Intercom",
        "auth_type": "oauth2",
        "fields_mapping": {
            "conversation": ["body", "user_id"],
            "user": ["name", "email"],
        },
        "events": ["message.received", "message.sent"],
    },
    "slack": {
        "name": "Slack",
        "description": "Send notifications and escalations to Slack",
        "auth_type": "oauth2",
        "fields_mapping": {
            "message": ["text", "channel"],
        },
        "events": ["escalation.requested", "conversation.ended"],
    },
    "teams": {
        "name": "Microsoft Teams",
        "description": "Deploy bot to Teams and receive notifications",
        "auth_type": "oauth2",
        "fields_mapping": {
            "message": ["text", "channel"],
        },
        "events": ["escalation.requested"],
    },
}


def get_available_integrations() -> List[Dict]:
    """Get list of available CRM integrations."""
    return [
        {
            "id": key,
            "name": data["name"],
            "description": data["description"],
            "auth_type": data["auth_type"],
        }
        for key, data in CRM_INTEGRATIONS.items()
    ]
