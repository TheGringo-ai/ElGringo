"""Seed Fred's memory with project knowledge, architecture, and key facts.

Run once on the VM (or locally) to populate the memories table + RAG index.
  python -m products.fred_assistant.seed_memories
"""

from products.fred_assistant.database import init_db
from products.fred_assistant.services.memory_service import remember

SEEDS = [
    # ── Projects: Identity & Purpose ─────────────────────────────
    ("projects", "chatterfix", "AI-powered CMMS for field technicians. Hands-free operation via voice, OCR, and NLP. Flagship product.", "https://chatterfix.com — Cloud Run", 9),
    ("projects", "managers_dashboard", "Multi-tenant CMMS analytics dashboard for maintenance managers. KPI tracking, equipment health scoring, AI audit reports.", "https://dashboard.chatterfix.com — VM 136.113.48.166", 9),
    ("projects", "fredai_platform", "Multi-agent AI orchestration platform. Coordinates GPT-4, Gemini, Grok, Claude. 12 services on dedicated VM.", "https://ai.chatterfix.com — VM 34.61.174.254", 9),
    ("projects", "fix_it_fred", "AI-powered DIY troubleshooting and home repair assistant for homeowners. Step-by-step diagnosis, parts price comparison.", "https://fixitfred.app — Cloud Run", 8),
    ("projects", "linesmart", "AI-powered training platform for manufacturing. Adaptive learning, skill gap analysis, competency tracking.", "Cloud Run deployment", 7),
    ("projects", "safetyfix", "AI-powered workplace safety management. Incident reporting, OSHA compliance, predictive hazard detection.", "In development — targets OSHA, ISO 45001", 7),
    ("projects", "artproof", "NFT certificate of authenticity generator for artworks on Polygon blockchain. Photo processing + IPFS storage.", "In development — React + Solidity", 6),
    ("projects", "freddy_mac_ide", "Web-based IDE with multi-AI integration. 6 specialist agents, semantic search, code editing.", "In development — React + Node.js", 6),
    ("projects", "ai_repo_review", "Static analysis tool for Python repos. Security issues, code quality, deprecated patterns. No code execution.", "Ready — CLI tool", 6),

    # ── Projects: Key Distinctions ───────────────────────────────
    ("projects", "dashboard_vs_chatterfix", "Managers Dashboard is NOT ChatterFix. Separate product, separate codebase, separate deployment.", "Dashboard = analytics for managers. ChatterFix = CMMS for technicians.", 10),
    ("projects", "fredai_is_the_brain", "FredAI Platform is the central brain. Fred Assistant is the hub connecting all 12 services via localhost HTTP.", "Services: API, PR Bot, Chat, Studio, Fred API, Code Audit, Test Gen, Doc Gen, Command Center, Assistant", 9),

    # ── Architecture: Infrastructure ─────────────────────────────
    ("infrastructure", "dashboard_vm", "Managers Dashboard runs on VM 136.113.48.166 (e2-medium). CI/CD: GitHub Actions → SCP → systemd.", "Domain: dashboard.chatterfix.com", 8),
    ("infrastructure", "fredai_vm", "FredAI runs on VM 34.61.174.254 (e2-medium, Debian 12, 4GB RAM). 12 systemd services + nginx.", "Domain: ai.chatterfix.com", 8),
    ("infrastructure", "chatterfix_deploy", "ChatterFix deploys to Google Cloud Run. CI/CD via GitHub Actions on push to main.", "Domain: chatterfix.com", 8),
    ("infrastructure", "vm_cost", "FredAI VM: ~$27-30/mo (e2-medium + disk + egress). Dashboard VM: similar. Total infra: ~$55-60/mo.", "No cost increase from RAG — runs in-process, zero API calls.", 7),

    # ── Architecture: Tech Stack ─────────────────────────────────
    ("tech_stack", "ai_providers", "6 AI providers: OpenAI GPT-4, Google Gemini 2.5 Flash, X.AI Grok 3, Anthropic Claude, Ollama (local), LlamaCloud.", "FredAI orchestrates all of them with intelligent routing.", 8),
    ("tech_stack", "databases", "Firestore (multi-tenant, 42+ collections), SQLite (Fred Assistant local), Redis (FredAI caching), MongoDB (ArtProof).", "PostgreSQL planned for SafetyFix.", 7),
    ("tech_stack", "python_backend", "All backends use Python + FastAPI except ArtProof (Node.js/Express). Testing: pytest across all projects.", "661 tests passing in FredAI alone.", 7),
    ("tech_stack", "frontend", "React 18 + Vite + Tailwind (Dashboard, Fix It Fred). React Native (ChatterFix mobile). Styled Components (ArtProof, IDE).", "", 7),
    ("tech_stack", "auth_patterns", "Firebase Auth (all projects). PIN login (Dashboard clients). Bearer tokens (APIs). bcrypt hashing.", "DASHBOARD_PIN_HASH env var required on VM.", 8),

    # ── Architecture: Fred Assistant ─────────────────────────────
    ("fred_assistant", "rag_system", "Local RAG using sentence-transformers (all-MiniLM-L6-v2) + ChromaDB. 5 collections: memories, tasks, chat, service_results, projects.", "Semantic retrieval replaces dump-everything context. Falls back to old builder if unavailable.", 9),
    ("fred_assistant", "context_builder", "Real-time sections always included: stats, boards, today's tasks, inbox, focus, CRM, platform status, PR reviews.", "RAG sections: relevant memories, related tasks, service results, project knowledge.", 8),
    ("fred_assistant", "chat_model", "Gemini 2.5 Flash for chat. Action execution loop (up to 5 rounds). Tools for tasks, memory, calendar, goals, content, platform services.", "FRED_CHAT_MODEL env var to override.", 8),
    ("fred_assistant", "service_count", "Fred Assistant has 16 routers, 68+ endpoints. Manages: boards, tasks, memory, chat, briefing, calendar, content, coach, focus, CRM, metrics, inbox, playbooks, projects.", "Port 7870 on both local and VM.", 7),

    # ── Key Principles ───────────────────────────────────────────
    ("principles", "no_duplicates", "Never create redundant or duplicate files. Keep the project clean. One deploy script, one set of Docker requirements.", "Core principle from Fred.", 10),
    ("principles", "ai_team_collaboration", "All AI models (Claude, GPT, Gemini, Grok) work as a team. They should learn from each other and build the most powerful apps.", "Cross-model learning, mistake prevention, solution sharing.", 9),
    ("principles", "never_repeat_mistakes", "Every mistake must be logged and prevented from recurring. The platform learns from every interaction.", "Mistake patterns stored in memory, injected into future prompts.", 9),
    ("principles", "technician_first", "ChatterFix is technician-first. Hands-free is the default. Voice commands, OCR, AR. Not office-worker software.", "Safety-aware, professional tone in all outputs.", 8),
    ("principles", "security_first", "Never deploy without testing. No hardcoded secrets. bcrypt for passwords. Auth middleware on all API routes.", "Known mistakes: datetime.utcnow(), samesite=strict, missing credentials:include", 8),

    # ── Deployment: Known Issues ─────────────────────────────────
    ("deployment", "dashboard_clientapi_pattern", "clientApi paths NEVER include /api/ prefix. Interceptors in App.jsx add it. Using /api/ causes double /api/api/.", "Global axios interceptors handle auth tokens + client_id.", 9),
    ("deployment", "dashboard_dark_mode", "Always test dark mode before deploying Dashboard. Known past mistake: deploying without dark mode testing.", "form-light, modal-light classes for accessibility.", 8),
    ("deployment", "fredai_deploy_command", "Deploy FredAI: ./deploy-vm.sh from local Mac. Packages tar, SCPs to VM, runs ci-deploy-fredai.sh.", "Deploy Dashboard: push to master triggers GitHub Actions CI/CD.", 8),
    ("deployment", "nginx_config", "FredAI nginx: sites-available/ai.chatterfix.com is a COPY not symlink. Deploy script copies from sites-available.", "Routes: /v1/ → Fred API, /audit/ → Code Audit, /api/ → Main API, /webhook → PR Bot", 7),
]


def seed():
    init_db()
    count = 0
    for category, key, value, context, importance in SEEDS:
        remember(category, key, value, context=context, importance=importance)
        count += 1
    print(f"Seeded {count} memories into Fred's brain.")


if __name__ == "__main__":
    seed()
