"""
AI Chat Builder
===============

Tools for building and configuring custom AI chatbots.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


# ============================================================
# PERSONA TEMPLATES
# ============================================================

PERSONA_TEMPLATES = {
    "professional_assistant": {
        "name": "Professional Assistant",
        "description": "Formal, helpful business assistant",
        "tone": "professional",
        "greeting": "Hello! Welcome to {company_name}. How may I assist you today?",
        "fallback_message": "I apologize, but I don't have information about that specific topic. Would you like me to connect you with one of our team members?",
        "personality_traits": ["helpful", "professional", "concise", "knowledgeable"],
        "system_prompt_template": """You are a professional AI assistant for {company_name}.
Your role is to help customers with their inquiries in a professional and helpful manner.

Key guidelines:
- Be polite and professional at all times
- Provide accurate information based on the knowledge base
- If you don't know something, admit it and offer to connect them with a human
- Keep responses concise but thorough
- Use proper grammar and business language

Company context:
{company_context}
"""
    },
    "friendly_helper": {
        "name": "Friendly Helper",
        "description": "Warm, approachable customer service agent",
        "tone": "friendly",
        "greeting": "Hey there! Welcome to {company_name}. What can I help you with today?",
        "fallback_message": "Hmm, I'm not sure about that one. Let me get you connected with someone who can help!",
        "personality_traits": ["friendly", "warm", "enthusiastic", "patient"],
        "system_prompt_template": """You are a friendly AI assistant for {company_name}.
Your role is to provide warm, approachable customer support.

Key guidelines:
- Be warm and friendly in your responses
- Use casual but professional language
- Show enthusiasm when helping
- Be patient with repeated questions
- Add appropriate emoji occasionally to feel more personable

Company context:
{company_context}
"""
    },
    "technical_expert": {
        "name": "Technical Expert",
        "description": "Knowledgeable technical support specialist",
        "tone": "technical",
        "greeting": "Hello! I'm the technical support assistant for {company_name}. What technical issue can I help you troubleshoot?",
        "fallback_message": "I don't have documentation on that specific issue. For complex technical problems, I recommend opening a support ticket so our engineering team can assist.",
        "personality_traits": ["technical", "precise", "thorough", "solution-oriented"],
        "system_prompt_template": """You are a technical support AI for {company_name}.
Your role is to help users troubleshoot technical issues and provide detailed technical guidance.

Key guidelines:
- Provide step-by-step technical instructions
- Use proper technical terminology
- Ask clarifying questions to diagnose issues
- Include code examples when relevant
- Suggest workarounds when main solutions aren't available
- Reference documentation when possible

Company context:
{company_context}
"""
    },
    "sales_consultant": {
        "name": "Sales Consultant",
        "description": "Helpful sales and product advisor",
        "tone": "persuasive",
        "greeting": "Hi there! I'm here to help you find the perfect solution from {company_name}. What are you looking for today?",
        "fallback_message": "Great question! Let me connect you with one of our sales specialists who can provide detailed pricing and customization options.",
        "personality_traits": ["helpful", "knowledgeable", "consultative", "solution-focused"],
        "system_prompt_template": """You are a sales consultant AI for {company_name}.
Your role is to help potential customers understand products/services and guide them toward solutions.

Key guidelines:
- Understand the customer's needs before recommending
- Highlight relevant features and benefits
- Be honest about capabilities and limitations
- Provide pricing information when available
- Offer to schedule demos or connect with sales team
- Never be pushy or aggressive

Company context:
{company_context}
"""
    },
    "appointment_scheduler": {
        "name": "Appointment Scheduler",
        "description": "Efficient booking and scheduling assistant",
        "tone": "efficient",
        "greeting": "Hello! I can help you schedule an appointment with {company_name}. What type of appointment are you looking to book?",
        "fallback_message": "I'm not able to help with that specific request. For scheduling questions, please call us at {phone} or email {email}.",
        "personality_traits": ["efficient", "organized", "clear", "accommodating"],
        "system_prompt_template": """You are a scheduling assistant AI for {company_name}.
Your role is to help customers book appointments efficiently.

Key guidelines:
- Confirm appointment type, date, time preferences
- Check availability and offer alternatives
- Collect necessary contact information
- Send confirmation details
- Handle rescheduling and cancellation requests
- Be efficient but not rushed

Company context:
{company_context}
"""
    },
}


# ============================================================
# CONVERSATION FLOW TEMPLATES
# ============================================================

FLOW_TEMPLATES = {
    "customer_support": {
        "name": "Customer Support Flow",
        "description": "Standard customer support conversation flow",
        "intents": [
            {"name": "greeting", "examples": ["hello", "hi", "hey", "good morning"]},
            {"name": "product_inquiry", "examples": ["tell me about", "what is", "how does"]},
            {"name": "pricing", "examples": ["how much", "price", "cost", "pricing"]},
            {"name": "support_request", "examples": ["help", "issue", "problem", "not working"]},
            {"name": "human_handoff", "examples": ["speak to human", "talk to agent", "real person"]},
            {"name": "goodbye", "examples": ["bye", "goodbye", "thanks", "thank you"]},
        ],
        "flow_nodes": [
            {"id": "start", "type": "greeting", "next": "intent_detection"},
            {"id": "intent_detection", "type": "classifier", "branches": {
                "product_inquiry": "product_info",
                "pricing": "pricing_info",
                "support_request": "support_flow",
                "human_handoff": "escalate",
                "goodbye": "end",
            }},
            {"id": "product_info", "type": "knowledge_query", "next": "satisfaction_check"},
            {"id": "pricing_info", "type": "knowledge_query", "next": "satisfaction_check"},
            {"id": "support_flow", "type": "troubleshoot", "next": "satisfaction_check"},
            {"id": "satisfaction_check", "type": "question", "prompt": "Did that help answer your question?",
             "branches": {"yes": "anything_else", "no": "escalate"}},
            {"id": "anything_else", "type": "question", "prompt": "Is there anything else I can help with?",
             "branches": {"yes": "intent_detection", "no": "end"}},
            {"id": "escalate", "type": "handoff", "message": "Let me connect you with a team member."},
            {"id": "end", "type": "goodbye", "message": "Thank you for chatting with us!"},
        ]
    },
    "lead_qualification": {
        "name": "Lead Qualification Flow",
        "description": "Qualify sales leads through conversation",
        "intents": [
            {"name": "interested", "examples": ["interested", "tell me more", "want to learn"]},
            {"name": "budget_question", "examples": ["budget", "afford", "price range"]},
            {"name": "timeline", "examples": ["when", "how soon", "timeline"]},
            {"name": "decision_maker", "examples": ["decide", "authority", "approval"]},
        ],
        "flow_nodes": [
            {"id": "start", "type": "greeting", "next": "initial_interest"},
            {"id": "initial_interest", "type": "question", "prompt": "What brings you here today?", "next": "qualify_need"},
            {"id": "qualify_need", "type": "question", "prompt": "What challenges are you trying to solve?", "next": "qualify_budget"},
            {"id": "qualify_budget", "type": "question", "prompt": "Do you have a budget in mind for this solution?", "next": "qualify_timeline"},
            {"id": "qualify_timeline", "type": "question", "prompt": "What's your timeline for implementing a solution?", "next": "qualify_authority"},
            {"id": "qualify_authority", "type": "question", "prompt": "Who else is involved in this decision?", "next": "schedule_demo"},
            {"id": "schedule_demo", "type": "cta", "message": "Based on what you've shared, I think a demo would be helpful.", "next": "end"},
            {"id": "end", "type": "goodbye"},
        ]
    },
    "faq_bot": {
        "name": "FAQ Bot Flow",
        "description": "Simple FAQ answering flow",
        "intents": [
            {"name": "faq", "examples": ["question", "how do I", "what is", "can you tell me"]},
        ],
        "flow_nodes": [
            {"id": "start", "type": "greeting", "next": "answer_question"},
            {"id": "answer_question", "type": "knowledge_query", "next": "more_questions"},
            {"id": "more_questions", "type": "question", "prompt": "Do you have any other questions?",
             "branches": {"yes": "answer_question", "no": "end"}},
            {"id": "end", "type": "goodbye"},
        ]
    },
}


# ============================================================
# INDUSTRY PRESETS
# ============================================================

INDUSTRY_PRESETS = {
    "saas": {
        "name": "SaaS / Software",
        "suggested_persona": "technical_expert",
        "suggested_flow": "customer_support",
        "common_intents": ["feature_request", "bug_report", "pricing_plans", "integration_help", "account_issues"],
        "sample_faqs": [
            "How do I reset my password?",
            "What integrations do you support?",
            "How do I upgrade my plan?",
            "Where can I find the API documentation?",
        ],
    },
    "ecommerce": {
        "name": "E-commerce / Retail",
        "suggested_persona": "friendly_helper",
        "suggested_flow": "customer_support",
        "common_intents": ["order_status", "returns", "product_availability", "shipping", "payment_issues"],
        "sample_faqs": [
            "Where is my order?",
            "How do I return an item?",
            "What payment methods do you accept?",
            "Do you ship internationally?",
        ],
    },
    "healthcare": {
        "name": "Healthcare",
        "suggested_persona": "professional_assistant",
        "suggested_flow": "faq_bot",
        "common_intents": ["appointment", "insurance", "services", "location", "hours"],
        "sample_faqs": [
            "How do I schedule an appointment?",
            "What insurance do you accept?",
            "What are your office hours?",
            "Where are you located?",
        ],
    },
    "finance": {
        "name": "Financial Services",
        "suggested_persona": "professional_assistant",
        "suggested_flow": "lead_qualification",
        "common_intents": ["account_info", "transactions", "products", "rates", "security"],
        "sample_faqs": [
            "What are your current interest rates?",
            "How do I open an account?",
            "Is my money secure?",
            "What investment options do you offer?",
        ],
    },
    "real_estate": {
        "name": "Real Estate",
        "suggested_persona": "sales_consultant",
        "suggested_flow": "lead_qualification",
        "common_intents": ["property_search", "schedule_viewing", "pricing", "neighborhood", "mortgage"],
        "sample_faqs": [
            "What properties are available in my budget?",
            "Can I schedule a viewing?",
            "What's the neighborhood like?",
            "Do you help with financing?",
        ],
    },
    "education": {
        "name": "Education",
        "suggested_persona": "friendly_helper",
        "suggested_flow": "faq_bot",
        "common_intents": ["courses", "enrollment", "schedule", "pricing", "certificates"],
        "sample_faqs": [
            "What courses do you offer?",
            "How do I enroll?",
            "What's the course schedule?",
            "Do you provide certificates?",
        ],
    },
}


# ============================================================
# CHAT BUILDER CLASS
# ============================================================

@dataclass
class PersonaTemplate:
    """A persona template for chatbots."""
    id: str
    name: str
    description: str
    tone: str
    greeting: str
    fallback_message: str
    personality_traits: List[str]
    system_prompt_template: str


@dataclass
class ConversationFlow:
    """A conversation flow definition."""
    id: str
    name: str
    description: str
    intents: List[Dict]
    flow_nodes: List[Dict]


class ChatBotBuilder:
    """Builder class for creating AI chatbots."""

    def __init__(self):
        self.personas = PERSONA_TEMPLATES
        self.flows = FLOW_TEMPLATES
        self.industries = INDUSTRY_PRESETS

    def get_persona_templates(self) -> List[Dict]:
        """Get all available persona templates."""
        return [
            {
                "id": key,
                "name": data["name"],
                "description": data["description"],
                "tone": data["tone"],
            }
            for key, data in self.personas.items()
        ]

    def get_flow_templates(self) -> List[Dict]:
        """Get all available conversation flow templates."""
        return [
            {
                "id": key,
                "name": data["name"],
                "description": data["description"],
            }
            for key, data in self.flows.items()
        ]

    def get_industry_presets(self) -> List[Dict]:
        """Get all available industry presets."""
        return [
            {
                "id": key,
                "name": data["name"],
                "suggested_persona": data["suggested_persona"],
                "suggested_flow": data["suggested_flow"],
            }
            for key, data in self.industries.items()
        ]

    def get_persona(self, persona_id: str) -> Optional[Dict]:
        """Get a specific persona template."""
        return self.personas.get(persona_id)

    def get_flow(self, flow_id: str) -> Optional[Dict]:
        """Get a specific flow template."""
        return self.flows.get(flow_id)

    def get_industry(self, industry_id: str) -> Optional[Dict]:
        """Get a specific industry preset."""
        return self.industries.get(industry_id)

    def build_system_prompt(self, persona_id: str, company_name: str,
                           company_context: str = "", custom_instructions: str = "") -> str:
        """Build a complete system prompt from a persona template."""
        persona = self.personas.get(persona_id)
        if not persona:
            persona = self.personas["professional_assistant"]

        prompt = persona["system_prompt_template"].format(
            company_name=company_name,
            company_context=company_context or f"{company_name} is a company."
        )

        if custom_instructions:
            prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"

        return prompt

    def generate_greeting(self, persona_id: str, company_name: str) -> str:
        """Generate a greeting message from persona template."""
        persona = self.personas.get(persona_id)
        if not persona:
            persona = self.personas["professional_assistant"]

        return persona["greeting"].format(company_name=company_name)

    def generate_embed_config(self, chatbot_name: str, primary_color: str = "#3b82f6",
                             position: str = "bottom-right", header_text: str = "Chat with us",
                             show_branding: bool = True) -> Dict:
        """Generate widget embed configuration."""
        return {
            "chatbot_name": chatbot_name,
            "position": position,
            "primary_color": primary_color,
            "header_text": header_text,
            "show_branding": show_branding,
            "theme": {
                "primary": primary_color,
                "background": "#ffffff",
                "text": "#1f2937",
                "user_bubble": primary_color,
                "bot_bubble": "#f3f4f6",
            },
            "features": {
                "file_upload": False,
                "voice_input": False,
                "typing_indicator": True,
                "message_timestamps": False,
                "feedback_buttons": True,
            }
        }

    def preview_chatbot(self, system_prompt: str, greeting: str,
                       test_messages: List[str] = None) -> List[Dict]:
        """Generate preview responses for testing (mock)."""
        # In real implementation, this would call the AI model
        preview = [{"role": "assistant", "content": greeting}]

        if test_messages:
            for msg in test_messages:
                preview.append({"role": "user", "content": msg})
                preview.append({
                    "role": "assistant",
                    "content": f"[Preview response for: '{msg}'] This is a mock response. In production, the {system_prompt[:50]}... would generate a real response."
                })

        return preview

    def export_chatbot_config(self, chatbot_id: str, name: str, persona_id: str,
                             company_name: str, company_context: str,
                             model: str = "claude-sonnet", **kwargs) -> Dict:
        """Export complete chatbot configuration."""
        persona = self.personas.get(persona_id, self.personas["professional_assistant"])

        return {
            "id": chatbot_id,
            "name": name,
            "model": model,
            "system_prompt": self.build_system_prompt(persona_id, company_name, company_context),
            "greeting": self.generate_greeting(persona_id, company_name),
            "fallback_message": persona["fallback_message"],
            "persona": {
                "id": persona_id,
                "name": persona["name"],
                "tone": persona["tone"],
                "personality_traits": persona["personality_traits"],
            },
            "config": {
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1024),
                "features": kwargs.get("features", {
                    "memory": True,
                    "citations": False,
                    "escalation": True,
                }),
            },
            "widget": self.generate_embed_config(
                name,
                kwargs.get("primary_color", "#3b82f6"),
                kwargs.get("position", "bottom-right"),
                kwargs.get("header_text", f"Chat with {company_name}"),
                kwargs.get("show_branding", True),
            ),
        }
