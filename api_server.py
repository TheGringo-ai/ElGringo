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


def get_team():
    """Get or create the AI team instance"""
    global team, engine
    if team is None:
        team = AIDevTeam(project_name="api-server")
        engine = ParallelCodingEngine(team)
    return team, engine


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
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Initialize team on startup
    get_team()

    app.run(
        host='0.0.0.0',
        port=5050,
        debug=True
    )
