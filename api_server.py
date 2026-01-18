#!/usr/bin/env python3
"""
AITeamPlatform API Server
=========================

REST API for the AI Team Platform, enabling integration with
FreddyMac IDE and other frontends.

Usage:
    python3 api_server.py

Endpoints:
    POST /api/ai/collaborate - Run parallel AI collaboration
    POST /api/ai/review - Code review with AI team
    POST /api/ai/fix - Fix issues in parallel
    GET /api/team/status - Get AI team status
    GET /api/providers - List available AI providers
    POST /api/providers/configure - Configure API keys
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam, ParallelCodingEngine
from ai_dev_team.integrations.github_webhooks import GitHubWebhookHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for FreddyMac IDE
CORS(app, origins=[
    "http://localhost:5173",      # Vite dev server
    "http://localhost:3000",      # React dev server
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://freddymac.web.app",  # Production
])

# Global team instance
team: Optional[AIDevTeam] = None
engine: Optional[ParallelCodingEngine] = None
webhook_handler: Optional[GitHubWebhookHandler] = None


def get_team():
    """Get or create the AI team instance"""
    global team, engine
    if team is None:
        team = AIDevTeam(project_name="api-server")
        engine = ParallelCodingEngine(team)
    return team, engine


def get_webhook_handler():
    """Get or create the GitHub webhook handler"""
    global webhook_handler
    if webhook_handler is None:
        from ai_dev_team.integrations.github import GitHubIntegration
        team_instance, _ = get_team()
        github_integration = GitHubIntegration(ai_team=team_instance)
        webhook_handler = GitHubWebhookHandler(
            webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET"),
            github_integration=github_integration,
        )
    return webhook_handler


def async_route(f):
    """Decorator to run async functions in Flask routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# ============================================
# Health & Status Endpoints
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AITeamPlatform",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/team/status', methods=['GET'])
def team_status():
    """Get AI team status"""
    team_instance, _ = get_team()
    status = team_instance.get_team_status()

    return jsonify({
        "success": True,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/providers', methods=['GET'])
def list_providers():
    """List available AI providers"""
    team_instance, _ = get_team()

    providers = []
    for name, agent in team_instance.agents.items():
        providers.append({
            "id": name,
            "name": agent.name,
            "role": agent.role,
            "available": True
        })

    return jsonify({
        "success": True,
        "providers": providers,
        "count": len(providers)
    })


@app.route('/api/providers/configure', methods=['POST'])
def configure_providers():
    """Configure AI provider API keys"""
    data = request.get_json() or {}

    configured = []

    if data.get('openai'):
        os.environ['OPENAI_API_KEY'] = data['openai']
        configured.append('openai')

    if data.get('anthropic'):
        os.environ['ANTHROPIC_API_KEY'] = data['anthropic']
        configured.append('anthropic')

    if data.get('google'):
        os.environ['GEMINI_API_KEY'] = data['google']
        configured.append('google')

    if data.get('xai'):
        os.environ['XAI_API_KEY'] = data['xai']
        configured.append('xai')

    # Reinitialize team with new keys
    global team, engine
    team = None
    engine = None
    get_team()

    return jsonify({
        "success": True,
        "configured": configured,
        "message": f"Configured {len(configured)} provider(s)"
    })


# ============================================
# AI Collaboration Endpoints
# ============================================

@app.route('/api/ai/collaborate', methods=['POST'])
@async_route
async def collaborate():
    """Run parallel AI collaboration"""
    data = request.get_json() or {}

    prompt = data.get('prompt', '')
    mode = data.get('mode', 'parallel')  # parallel, sequential, consensus
    context = data.get('context', {})

    if not prompt:
        return jsonify({
            "success": False,
            "error": "No prompt provided"
        }), 400

    team_instance, _ = get_team()

    try:
        result = await team_instance.collaborate(prompt, mode=mode)

        return jsonify({
            "success": True,
            "response": result.final_answer,
            "agents": result.participating_agents,
            "confidence": result.confidence_score,
            "mode": mode,
            "total_time": result.total_time
        })
    except Exception as e:
        logger.error(f"Collaboration error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ai/review', methods=['POST'])
@async_route
async def code_review():
    """Review code with AI team"""
    data = request.get_json() or {}

    project_path = data.get('project_path', '')
    focus_areas = data.get('focus_areas', None)

    if not project_path:
        return jsonify({
            "success": False,
            "error": "No project_path provided"
        }), 400

    _, engine_instance = get_team()

    try:
        result = await engine_instance.review_project(project_path, focus_areas=focus_areas)

        return jsonify({
            "success": True,
            "session_id": result.session_id,
            "summary": result.summary,
            "agent_results": result.agent_results,
            "proposed_fixes": len(result.proposed_fixes),
            "total_time": result.total_time
        })
    except Exception as e:
        logger.error(f"Review error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ai/security', methods=['POST'])
@async_route
async def security_audit():
    """Run security audit on project"""
    data = request.get_json() or {}

    project_path = data.get('project_path', '')
    severity = data.get('severity', 'medium')

    if not project_path:
        return jsonify({
            "success": False,
            "error": "No project_path provided"
        }), 400

    _, engine_instance = get_team()

    try:
        result = await engine_instance.security_audit(project_path, severity_threshold=severity)

        return jsonify({
            "success": True,
            "session_id": result.session_id,
            "summary": result.summary,
            "findings": result.agent_results,
            "proposed_fixes": len(result.proposed_fixes),
            "total_time": result.total_time
        })
    except Exception as e:
        logger.error(f"Security audit error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ai/fix', methods=['POST'])
@async_route
async def fix_issues():
    """Fix issues in parallel"""
    data = request.get_json() or {}

    project_path = data.get('project_path', '')
    issues = data.get('issues', [])
    auto_apply = data.get('auto_apply', False)

    if not project_path:
        return jsonify({
            "success": False,
            "error": "No project_path provided"
        }), 400

    _, engine_instance = get_team()

    try:
        result = await engine_instance.fix_issues(issues, project_path, auto_apply=auto_apply)

        return jsonify({
            "success": True,
            "session_id": result.session_id,
            "summary": result.summary,
            "fixes_proposed": len(result.proposed_fixes),
            "auto_applied": auto_apply,
            "total_time": result.total_time
        })
    except Exception as e:
        logger.error(f"Fix error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ai/ask', methods=['POST'])
@async_route
async def ask_team():
    """Ask the AI team a question"""
    data = request.get_json() or {}

    question = data.get('question', '')
    context = data.get('context', {})

    if not question:
        return jsonify({
            "success": False,
            "error": "No question provided"
        }), 400

    team_instance, _ = get_team()

    # Build contextual prompt
    prompt = question
    if context.get('current_file'):
        prompt = f"Context: Working on file {context['current_file']}\n\n{question}"
    if context.get('selected_code'):
        prompt = f"{prompt}\n\nSelected code:\n```\n{context['selected_code']}\n```"

    try:
        result = await team_instance.collaborate(prompt, mode='parallel')

        return jsonify({
            "success": True,
            "answer": result.final_answer,
            "agents": result.participating_agents,
            "confidence": result.confidence_score
        })
    except Exception as e:
        logger.error(f"Ask error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================
# GitHub Webhook Endpoint
# ============================================

@app.route('/webhooks/github', methods=['POST'])
@async_route
async def github_webhook():
    """Handle GitHub webhook events"""
    handler = get_webhook_handler()

    event_type = request.headers.get('X-GitHub-Event', '')
    delivery_id = request.headers.get('X-GitHub-Delivery', '')
    signature = request.headers.get('X-Hub-Signature-256', '')

    # Verify signature
    if not handler.verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401

    payload = request.get_json() or {}

    result = await handler.process_webhook(
        event_type=event_type,
        payload=payload,
        delivery_id=delivery_id,
        signature=signature,
    )

    return jsonify(result)


# ============================================
# Memory & Learning Endpoints
# ============================================

# Global memory instance
memory_system = None

def get_memory():
    """Get or create the memory system instance"""
    global memory_system
    if memory_system is None:
        from ai_dev_team.memory.system import MemorySystem
        memory_system = MemorySystem(use_firestore=True)
    return memory_system


@app.route('/api/memory/mistake', methods=['POST'])
@async_route
async def store_mistake():
    """Store a mistake pattern for learning (used by CI/CD and GitHub Actions)"""
    data = request.get_json() or {}

    description = data.get('description', '')
    mistake_type = data.get('mistake_type', 'deployment_failure')
    severity = data.get('severity', 'high')
    resolution = data.get('resolution', '')
    prevention_strategy = data.get('prevention_strategy', '')
    project = data.get('project', 'chatterfix')
    context = data.get('context', {})

    if not description:
        return jsonify({
            "success": False,
            "error": "No description provided"
        }), 400

    from ai_dev_team.memory.system import MistakeType

    mistake_type_map = {
        "code_error": MistakeType.CODE_ERROR,
        "architecture_flaw": MistakeType.ARCHITECTURE_FLAW,
        "performance_issue": MistakeType.PERFORMANCE_ISSUE,
        "security_vulnerability": MistakeType.SECURITY_VULNERABILITY,
        "deployment_failure": MistakeType.DEPLOYMENT_FAILURE,
        "logic_error": MistakeType.LOGIC_ERROR,
        "integration_issue": MistakeType.INTEGRATION_ISSUE,
    }

    memory = get_memory()

    try:
        mistake_id = await memory.capture_mistake(
            mistake_type=mistake_type_map.get(mistake_type, MistakeType.DEPLOYMENT_FAILURE),
            description=description,
            context=context,
            resolution=resolution,
            prevention_strategy=prevention_strategy,
            severity=severity,
            project=project,
            tags=data.get('tags', ['ci-cd', 'automated'])
        )

        logger.info(f"Stored mistake pattern: {mistake_id}")

        return jsonify({
            "success": True,
            "mistake_id": mistake_id,
            "message": f"Mistake pattern stored: {description[:50]}...",
            "stats": memory.get_statistics()
        })
    except Exception as e:
        logger.error(f"Error storing mistake: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/memory/solution', methods=['POST'])
@async_route
async def store_solution():
    """Store a solution pattern for learning"""
    data = request.get_json() or {}

    problem_pattern = data.get('problem_pattern', '')
    solution_steps = data.get('solution_steps', [])
    project = data.get('project', 'chatterfix')

    if not problem_pattern or not solution_steps:
        return jsonify({
            "success": False,
            "error": "problem_pattern and solution_steps are required"
        }), 400

    memory = get_memory()

    try:
        solution_id = await memory.capture_solution(
            problem_pattern=problem_pattern,
            solution_steps=solution_steps,
            success_rate=data.get('success_rate', 1.0),
            project=project,
            best_practices=data.get('best_practices', []),
            tags=data.get('tags', ['automated'])
        )

        return jsonify({
            "success": True,
            "solution_id": solution_id,
            "message": f"Solution pattern stored: {problem_pattern[:50]}..."
        })
    except Exception as e:
        logger.error(f"Error storing solution: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/memory/search', methods=['GET'])
@async_route
async def search_memory():
    """Search memory for mistakes and solutions"""
    query = request.args.get('q', '')

    if not query:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' is required"
        }), 400

    memory = get_memory()

    try:
        results = await memory.search_all(query, limit=10)

        return jsonify({
            "success": True,
            "query": query,
            "mistakes": [
                {
                    "id": m.mistake_id,
                    "type": m.mistake_type,
                    "description": m.description,
                    "severity": m.severity,
                    "prevention": m.prevention_strategy
                }
                for m in results["mistakes"]
            ],
            "solutions": [
                {
                    "id": s.solution_id,
                    "problem": s.problem_pattern,
                    "steps": s.solution_steps,
                    "success_rate": s.success_rate
                }
                for s in results["solutions"]
            ],
            "total_results": results["total_results"]
        })
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/memory/stats', methods=['GET'])
def memory_stats():
    """Get memory system statistics"""
    memory = get_memory()
    return jsonify({
        "success": True,
        "stats": memory.get_statistics()
    })


# ============================================
# WebSocket Support (for real-time updates)
# ============================================

# Note: For production, consider using Flask-SocketIO
# This is a placeholder for the WebSocket implementation

@app.route('/api/ws/info', methods=['GET'])
def websocket_info():
    """Get WebSocket connection info"""
    return jsonify({
        "message": "WebSocket support coming soon",
        "alternative": "Use polling with /api/team/status for real-time updates"
    })


# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║              AITeamPlatform API Server                            ║
╠═══════════════════════════════════════════════════════════════════╣
║  Endpoints:                                                       ║
║    GET  /api/health         - Health check                        ║
║    GET  /api/team/status    - Team status                         ║
║    GET  /api/providers      - List AI providers                   ║
║    POST /api/providers/configure - Configure API keys             ║
║    POST /api/ai/collaborate - Parallel collaboration              ║
║    POST /api/ai/review      - Code review                         ║
║    POST /api/ai/security    - Security audit                      ║
║    POST /api/ai/fix         - Fix issues                          ║
║    POST /api/ai/ask         - Ask the team                        ║
║    POST /webhooks/github    - GitHub webhook handler              ║
║  Memory & Learning:                                               ║
║    POST /api/memory/mistake - Store mistake pattern (CI/CD)       ║
║    POST /api/memory/solution - Store solution pattern             ║
║    GET  /api/memory/search  - Search mistakes & solutions         ║
║    GET  /api/memory/stats   - Memory system statistics            ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Initialize team on startup
    get_team()

    app.run(
        host='0.0.0.0',
        port=5050,
        debug=True
    )
