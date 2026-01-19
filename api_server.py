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
# Coding Knowledge Hub Endpoints
# ============================================

# Global coding hub instance
coding_hub = None

def get_coding_hub():
    """Get or create the coding hub instance"""
    global coding_hub
    if coding_hub is None:
        from ai_dev_team.knowledge.coding_hub import CodingKnowledgeHub
        coding_hub = CodingKnowledgeHub()
    return coding_hub


@app.route('/api/hub/stats', methods=['GET'])
def hub_stats():
    """Get coding knowledge hub statistics"""
    hub = get_coding_hub()
    return jsonify({
        "success": True,
        "stats": hub.get_statistics()
    })


@app.route('/api/hub/snippet', methods=['POST'])
def store_snippet():
    """Store a code snippet in the knowledge hub"""
    data = request.get_json() or {}

    language = data.get('language', '')
    category = data.get('category', 'general')
    title = data.get('title', '')
    code = data.get('code', '')
    description = data.get('description', '')
    tags = data.get('tags', [])

    if not language or not title or not code:
        return jsonify({
            "success": False,
            "error": "language, title, and code are required"
        }), 400

    hub = get_coding_hub()
    snippet_id = hub.store_code_snippet(
        language=language,
        category=category,
        title=title,
        code=code,
        description=description,
        tags=tags,
        source=data.get('source', 'manual'),
    )

    return jsonify({
        "success": True,
        "snippet_id": snippet_id,
        "message": f"Stored snippet: {title}"
    })


@app.route('/api/hub/snippet/search', methods=['GET'])
def search_snippets():
    """Search for code snippets"""
    query = request.args.get('q', '')
    language = request.args.get('language')
    category = request.args.get('category')
    limit = int(request.args.get('limit', 10))

    if not query:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' is required"
        }), 400

    hub = get_coding_hub()
    snippets = hub.search_snippets(query, language=language, category=category, limit=limit)

    return jsonify({
        "success": True,
        "query": query,
        "count": len(snippets),
        "snippets": [
            {
                "id": s.snippet_id,
                "language": s.language,
                "category": s.category,
                "title": s.title,
                "description": s.description,
                "code": s.code,
                "tags": s.tags,
                "use_count": s.use_count,
            }
            for s in snippets
        ]
    })


@app.route('/api/hub/error-fix', methods=['POST'])
def store_error_fix():
    """Store an error -> fix mapping"""
    data = request.get_json() or {}

    error_pattern = data.get('error_pattern', '')
    fix_steps = data.get('fix_steps', [])
    language = data.get('language', '')

    if not error_pattern or not fix_steps or not language:
        return jsonify({
            "success": False,
            "error": "error_pattern, fix_steps, and language are required"
        }), 400

    hub = get_coding_hub()
    fix_id = hub.store_error_fix(
        error_pattern=error_pattern,
        fix_steps=fix_steps,
        language=language,
        error_type=data.get('error_type', 'runtime'),
        fix_code=data.get('fix_code'),
        explanation=data.get('explanation', ''),
        tags=data.get('tags', []),
    )

    return jsonify({
        "success": True,
        "fix_id": fix_id,
        "message": f"Stored error fix for: {error_pattern[:50]}..."
    })


@app.route('/api/hub/error-fix/search', methods=['GET'])
def find_error_fix():
    """Find fixes for an error message"""
    error = request.args.get('error', '')
    language = request.args.get('language')

    if not error:
        return jsonify({
            "success": False,
            "error": "Query parameter 'error' is required"
        }), 400

    hub = get_coding_hub()
    fixes = hub.find_fix_for_error(error, language=language)

    return jsonify({
        "success": True,
        "error_query": error[:100],
        "count": len(fixes),
        "fixes": [
            {
                "id": f.fix_id,
                "error_pattern": f.error_pattern,
                "error_type": f.error_type,
                "language": f.language,
                "fix_steps": f.fix_steps,
                "fix_code": f.fix_code,
                "explanation": f.explanation,
                "success_rate": f.success_count / max(f.success_count + f.failure_count, 1),
            }
            for f in fixes
        ]
    })


@app.route('/api/hub/pattern', methods=['POST'])
def store_pattern():
    """Store a framework pattern"""
    data = request.get_json() or {}

    framework = data.get('framework', '')
    pattern_name = data.get('pattern_name', '')
    description = data.get('description', '')
    code_template = data.get('code_template', '')

    if not framework or not pattern_name or not code_template:
        return jsonify({
            "success": False,
            "error": "framework, pattern_name, and code_template are required"
        }), 400

    hub = get_coding_hub()
    pattern_id = hub.store_framework_pattern(
        framework=framework,
        pattern_name=pattern_name,
        description=description,
        code_template=code_template,
        use_cases=data.get('use_cases', []),
        anti_patterns=data.get('anti_patterns', []),
    )

    return jsonify({
        "success": True,
        "pattern_id": pattern_id,
        "message": f"Stored pattern: {pattern_name} ({framework})"
    })


@app.route('/api/hub/pattern/search', methods=['GET'])
def search_patterns():
    """Search for framework patterns"""
    query = request.args.get('q', '')
    framework = request.args.get('framework')

    hub = get_coding_hub()

    if framework and not query:
        patterns = hub.get_patterns_for_framework(framework)
    elif query:
        patterns = hub.search_patterns(query, framework=framework)
    else:
        return jsonify({
            "success": False,
            "error": "Either 'q' or 'framework' parameter is required"
        }), 400

    return jsonify({
        "success": True,
        "count": len(patterns),
        "patterns": [
            {
                "id": p.pattern_id,
                "framework": p.framework,
                "pattern_name": p.pattern_name,
                "description": p.description,
                "code_template": p.code_template,
                "use_cases": p.use_cases,
                "anti_patterns": p.anti_patterns,
            }
            for p in patterns
        ]
    })


@app.route('/api/hub/api-knowledge', methods=['POST'])
def store_api_knowledge():
    """Store API usage knowledge"""
    data = request.get_json() or {}

    api_name = data.get('api_name', '')
    endpoint_or_method = data.get('endpoint_or_method', '')
    description = data.get('description', '')
    example_code = data.get('example_code', '')

    if not api_name or not endpoint_or_method or not example_code:
        return jsonify({
            "success": False,
            "error": "api_name, endpoint_or_method, and example_code are required"
        }), 400

    hub = get_coding_hub()
    api_id = hub.store_api_knowledge(
        api_name=api_name,
        endpoint_or_method=endpoint_or_method,
        description=description,
        example_code=example_code,
        parameters=data.get('parameters', {}),
        common_errors=data.get('common_errors', []),
        tips=data.get('tips', []),
    )

    return jsonify({
        "success": True,
        "api_id": api_id,
        "message": f"Stored API knowledge: {api_name} - {endpoint_or_method}"
    })


@app.route('/api/hub/api-knowledge/<api_name>', methods=['GET'])
def get_api_knowledge(api_name):
    """Get knowledge about an API"""
    query = request.args.get('q')

    hub = get_coding_hub()
    knowledge = hub.get_api_knowledge(api_name, query=query)

    return jsonify({
        "success": True,
        "api_name": api_name,
        "count": len(knowledge),
        "knowledge": [
            {
                "id": k.api_id,
                "endpoint_or_method": k.endpoint_or_method,
                "description": k.description,
                "example_code": k.example_code,
                "parameters": k.parameters,
                "common_errors": k.common_errors,
                "tips": k.tips,
            }
            for k in knowledge
        ]
    })


@app.route('/api/hub/context', methods=['POST'])
def get_coding_context():
    """Generate coding context for a task"""
    data = request.get_json() or {}

    task = data.get('task', '')
    if not task:
        return jsonify({
            "success": False,
            "error": "task description is required"
        }), 400

    hub = get_coding_hub()
    context = hub.generate_coding_context(
        task_description=task,
        language=data.get('language'),
        framework=data.get('framework'),
        include_snippets=data.get('include_snippets', True),
        include_patterns=data.get('include_patterns', True),
        include_error_fixes=data.get('include_error_fixes', True),
        max_items=data.get('max_items', 5),
    )

    return jsonify({
        "success": True,
        "task": task[:100],
        "context": context,
        "context_length": len(context)
    })


@app.route('/api/hub/learn', methods=['POST'])
def learn_from_code():
    """Auto-learn from successful code"""
    data = request.get_json() or {}

    code = data.get('code', '')
    language = data.get('language', '')
    task = data.get('task', '')

    if not code or not language or not task:
        return jsonify({
            "success": False,
            "error": "code, language, and task are required"
        }), 400

    hub = get_coding_hub()
    snippet_id = hub.learn_from_successful_code(
        code=code,
        language=language,
        task_description=task,
        framework=data.get('framework'),
    )

    if snippet_id:
        return jsonify({
            "success": True,
            "snippet_id": snippet_id,
            "message": "Learned from successful code"
        })
    else:
        return jsonify({
            "success": True,
            "message": "Code too simple to store"
        })


# ============================================
# Performance Tracking & Smart Routing
# ============================================

# Global performance tracker instance
performance_tracker = None

def get_performance_tracker():
    """Get or create the performance tracker instance"""
    global performance_tracker
    if performance_tracker is None:
        from ai_dev_team.routing import get_performance_tracker as get_tracker
        performance_tracker = get_tracker()
    return performance_tracker


@app.route('/api/router/stats', methods=['GET'])
def router_stats():
    """Get performance tracking statistics"""
    tracker = get_performance_tracker()
    return jsonify({
        "success": True,
        "stats": tracker.get_statistics()
    })


@app.route('/api/router/ranking', methods=['GET'])
def model_ranking():
    """Get ranked list of models for a task type"""
    task_type = request.args.get('task_type')

    team_instance, _ = get_team()
    available = list(team_instance.agents.keys())

    tracker = get_performance_tracker()
    rankings = tracker.get_model_ranking(available, task_type=task_type)

    return jsonify({
        "success": True,
        "task_type": task_type or "overall",
        "rankings": [
            {
                "model": name,
                "score": round(score, 3),
                "details": details
            }
            for name, score, details in rankings
        ]
    })


@app.route('/api/router/best', methods=['GET'])
def best_model():
    """Get the best model for a specific task"""
    task_type = request.args.get('task_type', 'coding')
    domain = request.args.get('domain')
    prefer_fast = request.args.get('prefer_fast', 'false').lower() == 'true'

    team_instance, _ = get_team()
    available = list(team_instance.agents.keys())

    tracker = get_performance_tracker()
    best, confidence = tracker.get_best_model(
        task_type=task_type,
        available_models=available,
        domain=domain,
        prefer_fast=prefer_fast,
    )

    return jsonify({
        "success": True,
        "task_type": task_type,
        "domain": domain,
        "best_model": best,
        "confidence": round(confidence, 3)
    })


@app.route('/api/router/record', methods=['POST'])
def record_outcome():
    """Record a task outcome for learning"""
    data = request.get_json() or {}

    model_name = data.get('model_name', '')
    task_type = data.get('task_type', '')
    success = data.get('success', False)

    if not model_name or not task_type:
        return jsonify({
            "success": False,
            "error": "model_name and task_type are required"
        }), 400

    tracker = get_performance_tracker()
    tracker.record_outcome(
        model_name=model_name,
        task_type=task_type,
        success=success,
        confidence=data.get('confidence', 0.5),
        response_time=data.get('response_time', 5.0),
        domain=data.get('domain', 'general'),
        task_id=data.get('task_id', ''),
        user_rating=data.get('user_rating'),
        code_executed=data.get('code_executed', False),
        code_passed=data.get('code_passed', False),
    )

    return jsonify({
        "success": True,
        "message": f"Recorded outcome for {model_name} on {task_type}"
    })


@app.route('/api/router/classify', methods=['POST'])
def classify_task():
    """Classify a task and get model recommendations"""
    data = request.get_json() or {}

    prompt = data.get('prompt', '')
    context = data.get('context', '')
    domain = data.get('domain')

    if not prompt:
        return jsonify({
            "success": False,
            "error": "prompt is required"
        }), 400

    from ai_dev_team.routing import TaskRouter

    team_instance, _ = get_team()
    available = list(team_instance.agents.keys())

    router = TaskRouter()
    classification = router.classify_with_performance(
        prompt=prompt,
        context=context,
        available_agents=available,
        domain=domain,
    )

    return jsonify({
        "success": True,
        "classification": {
            "primary_type": classification.primary_type.value,
            "secondary_types": [t.value for t in classification.secondary_types],
            "confidence": round(classification.confidence, 3),
            "complexity": classification.complexity,
            "recommended_agents": classification.recommended_agents,
            "recommended_mode": classification.recommended_mode,
        }
    })


# ============================================
# Model Health Monitoring
# ============================================

# Global health monitor instance
health_monitor = None

def get_health_monitor():
    """Get or create the health monitor instance"""
    global health_monitor
    if health_monitor is None:
        from ai_dev_team.monitoring import get_health_monitor as get_monitor
        health_monitor = get_monitor()
    return health_monitor


@app.route('/api/health/models', methods=['GET'])
def model_health():
    """Get health status for all models"""
    monitor = get_health_monitor()
    return jsonify({
        "success": True,
        "health": monitor.get_statistics()
    })


@app.route('/api/health/models/<model_name>', methods=['GET'])
def model_health_detail(model_name):
    """Get detailed health for a specific model"""
    monitor = get_health_monitor()
    health = monitor.get_health(model_name)

    if not health:
        return jsonify({
            "success": True,
            "model": model_name,
            "status": "no_data",
            "message": "No health data for this model yet"
        })

    return jsonify({
        "success": True,
        "model": model_name,
        "health": health.to_dict()
    })


@app.route('/api/health/available', methods=['GET'])
def available_models():
    """Get list of currently available (healthy) models"""
    team_instance, _ = get_team()
    all_models = list(team_instance.agents.keys())

    monitor = get_health_monitor()
    healthy = monitor.get_healthy_models(all_models)

    return jsonify({
        "success": True,
        "total_models": len(all_models),
        "available_models": healthy,
        "available_count": len(healthy)
    })


# ============================================
# Failover & Circuit Breaker
# ============================================

# Global failover manager instance
failover_manager = None

def get_failover_mgr():
    """Get or create the failover manager instance"""
    global failover_manager
    if failover_manager is None:
        from ai_dev_team.failover import get_failover_manager
        failover_manager = get_failover_manager()
        # Set available models
        team_instance, _ = get_team()
        failover_manager.set_available_models(list(team_instance.agents.keys()))
    return failover_manager


@app.route('/api/failover/stats', methods=['GET'])
def failover_stats():
    """Get failover and circuit breaker statistics"""
    manager = get_failover_mgr()
    return jsonify({
        "success": True,
        "stats": manager.get_statistics()
    })


@app.route('/api/failover/circuit/<model_name>', methods=['GET'])
def circuit_status(model_name):
    """Get circuit breaker status for a model"""
    from ai_dev_team.failover import get_circuit_breaker
    breaker = get_circuit_breaker()

    state = breaker.get_state(model_name)
    stats = breaker.get_stats(model_name)

    return jsonify({
        "success": True,
        "model": model_name,
        "state": state.value,
        "stats": stats.to_dict()
    })


@app.route('/api/failover/circuit/<model_name>/open', methods=['POST'])
def open_circuit(model_name):
    """Manually open circuit for a model"""
    data = request.get_json() or {}
    duration = data.get('duration', 60)

    from ai_dev_team.failover import get_circuit_breaker
    breaker = get_circuit_breaker()
    breaker.force_open(model_name, duration)

    return jsonify({
        "success": True,
        "message": f"Circuit opened for {model_name} for {duration}s"
    })


@app.route('/api/failover/circuit/<model_name>/close', methods=['POST'])
def close_circuit(model_name):
    """Manually close circuit for a model"""
    from ai_dev_team.failover import get_circuit_breaker
    breaker = get_circuit_breaker()
    breaker.force_close(model_name)

    return jsonify({
        "success": True,
        "message": f"Circuit closed for {model_name}"
    })


# ============================================
# Prompt Templates Library
# ============================================

# Global prompt library instance
prompt_library = None

def get_prompts():
    """Get or create the prompt library instance"""
    global prompt_library
    if prompt_library is None:
        from ai_dev_team.prompts import get_prompt_library
        prompt_library = get_prompt_library()
    return prompt_library


@app.route('/api/prompts/list', methods=['GET'])
def list_prompts():
    """List all prompt templates"""
    category = request.args.get('category')

    library = get_prompts()
    if category:
        templates = library.get_by_category(category)
    else:
        templates = list(library._templates.values())

    return jsonify({
        "success": True,
        "count": len(templates),
        "templates": [t.to_dict() for t in templates]
    })


@app.route('/api/prompts/categories', methods=['GET'])
def prompt_categories():
    """Get available prompt categories"""
    library = get_prompts()
    return jsonify({
        "success": True,
        "categories": library.get_categories()
    })


@app.route('/api/prompts/<template_id>', methods=['GET'])
def get_prompt(template_id):
    """Get a specific prompt template"""
    library = get_prompts()
    template = library.get_template(template_id)

    if not template:
        return jsonify({
            "success": False,
            "error": f"Template {template_id} not found"
        }), 404

    return jsonify({
        "success": True,
        "template": template.to_dict()
    })


@app.route('/api/prompts/use', methods=['POST'])
def use_prompt():
    """Use a prompt template with variables"""
    data = request.get_json() or {}

    template_id = data.get('template_id', '')
    variables = data.get('variables', {})

    if not template_id:
        return jsonify({
            "success": False,
            "error": "template_id is required"
        }), 400

    library = get_prompts()
    rendered = library.use_template(template_id, variables)

    if rendered is None:
        return jsonify({
            "success": False,
            "error": f"Template {template_id} not found"
        }), 404

    return jsonify({
        "success": True,
        "template_id": template_id,
        "rendered_prompt": rendered
    })


@app.route('/api/prompts/suggest', methods=['POST'])
def suggest_prompt():
    """Suggest a template based on task description"""
    data = request.get_json() or {}
    task = data.get('task', '')

    if not task:
        return jsonify({
            "success": False,
            "error": "task description is required"
        }), 400

    library = get_prompts()
    suggested = library.suggest_template(task)

    if suggested:
        return jsonify({
            "success": True,
            "suggested": suggested.to_dict()
        })
    else:
        return jsonify({
            "success": True,
            "suggested": None,
            "message": "No matching template found"
        })


@app.route('/api/prompts/create', methods=['POST'])
def create_prompt():
    """Create a custom prompt template"""
    data = request.get_json() or {}

    name = data.get('name', '')
    category = data.get('category', '')
    template = data.get('template', '')

    if not name or not category or not template:
        return jsonify({
            "success": False,
            "error": "name, category, and template are required"
        }), 400

    library = get_prompts()
    template_id = library.add_template(
        name=name,
        category=category,
        template=template,
        description=data.get('description', ''),
        tags=data.get('tags', []),
        example_values=data.get('example_values', {}),
    )

    return jsonify({
        "success": True,
        "template_id": template_id,
        "message": f"Template '{name}' created"
    })


@app.route('/api/prompts/stats', methods=['GET'])
def prompt_stats():
    """Get prompt library statistics"""
    library = get_prompts()
    return jsonify({
        "success": True,
        "stats": library.get_statistics()
    })


@app.route('/api/prompts/<template_id>/success', methods=['POST'])
def record_prompt_success(template_id):
    """Record success/failure for a template"""
    data = request.get_json() or {}
    success = data.get('success', True)

    library = get_prompts()
    library.record_success(template_id, success)

    return jsonify({
        "success": True,
        "message": f"Recorded {'success' if success else 'failure'} for {template_id}"
    })


# ============================================
# Cost Tracking
# ============================================

# Global cost tracker instance
cost_tracker = None

def get_cost_tracker():
    """Get or create the cost tracker instance"""
    global cost_tracker
    if cost_tracker is None:
        from ai_dev_team.routing import get_cost_tracker as get_tracker
        cost_tracker = get_tracker()
    return cost_tracker


@app.route('/api/costs/stats', methods=['GET'])
def cost_stats():
    """Get comprehensive cost statistics"""
    tracker = get_cost_tracker()
    return jsonify({
        "success": True,
        "stats": tracker.get_statistics()
    })


@app.route('/api/costs/budget', methods=['GET'])
def cost_budget():
    """Get current budget status"""
    tracker = get_cost_tracker()
    return jsonify({
        "success": True,
        "budget": tracker.get_budget_status()
    })


@app.route('/api/costs/budget', methods=['POST'])
def set_budget():
    """Set budget limits"""
    data = request.get_json() or {}

    tracker = get_cost_tracker()
    tracker.set_budget(
        daily=data.get('daily'),
        monthly=data.get('monthly'),
    )

    return jsonify({
        "success": True,
        "message": "Budget updated",
        "budget": tracker.get_budget_status()
    })


@app.route('/api/costs/daily', methods=['GET'])
def daily_costs():
    """Get daily cost report"""
    date = request.args.get('date')  # Optional: YYYY-MM-DD

    tracker = get_cost_tracker()
    report = tracker.get_daily_report(date)

    return jsonify({
        "success": True,
        "report": report
    })


@app.route('/api/costs/weekly', methods=['GET'])
def weekly_costs():
    """Get weekly cost report"""
    tracker = get_cost_tracker()
    return jsonify({
        "success": True,
        "report": tracker.get_weekly_report()
    })


@app.route('/api/costs/monthly', methods=['GET'])
def monthly_costs():
    """Get monthly cost report"""
    tracker = get_cost_tracker()
    return jsonify({
        "success": True,
        "report": tracker.get_monthly_report()
    })


@app.route('/api/costs/by-model', methods=['GET'])
def costs_by_model():
    """Get cost breakdown by model"""
    tracker = get_cost_tracker()
    return jsonify({
        "success": True,
        "models": tracker.get_model_costs()
    })


# ============================================
# User Feedback Collection
# ============================================

# Global feedback collector instance
feedback_collector = None

def get_feedback():
    """Get or create the feedback collector instance"""
    global feedback_collector
    if feedback_collector is None:
        from ai_dev_team.feedback import get_feedback_collector
        feedback_collector = get_feedback_collector()
    return feedback_collector


@app.route('/api/feedback/thumbs-up', methods=['POST'])
def thumbs_up():
    """Submit thumbs up feedback"""
    data = request.get_json() or {}

    task_id = data.get('task_id', '')
    model_name = data.get('model_name', '')

    if not task_id or not model_name:
        return jsonify({
            "success": False,
            "error": "task_id and model_name are required"
        }), 400

    collector = get_feedback()
    feedback_id = collector.submit_thumbs_up(
        task_id=task_id,
        model_name=model_name,
        task_type=data.get('task_type'),
        comment=data.get('comment'),
    )

    return jsonify({
        "success": True,
        "feedback_id": feedback_id,
        "message": f"Thanks for the positive feedback on {model_name}!"
    })


@app.route('/api/feedback/thumbs-down', methods=['POST'])
def thumbs_down():
    """Submit thumbs down feedback"""
    data = request.get_json() or {}

    task_id = data.get('task_id', '')
    model_name = data.get('model_name', '')

    if not task_id or not model_name:
        return jsonify({
            "success": False,
            "error": "task_id and model_name are required"
        }), 400

    collector = get_feedback()
    feedback_id = collector.submit_thumbs_down(
        task_id=task_id,
        model_name=model_name,
        task_type=data.get('task_type'),
        comment=data.get('comment'),
        correction=data.get('correction'),
    )

    return jsonify({
        "success": True,
        "feedback_id": feedback_id,
        "message": "Thanks for the feedback. We'll use it to improve!"
    })


@app.route('/api/feedback/rating', methods=['POST'])
def submit_rating():
    """Submit star rating (1-5)"""
    data = request.get_json() or {}

    task_id = data.get('task_id', '')
    model_name = data.get('model_name', '')
    rating = data.get('rating')

    if not task_id or not model_name or rating is None:
        return jsonify({
            "success": False,
            "error": "task_id, model_name, and rating are required"
        }), 400

    collector = get_feedback()
    feedback_id = collector.submit_rating(
        task_id=task_id,
        model_name=model_name,
        rating=int(rating),
        task_type=data.get('task_type'),
        comment=data.get('comment'),
    )

    return jsonify({
        "success": True,
        "feedback_id": feedback_id,
        "message": f"Thanks for rating {model_name} {rating}/5 stars!"
    })


@app.route('/api/feedback/correction', methods=['POST'])
def submit_correction():
    """Submit a correction (the right answer)"""
    data = request.get_json() or {}

    task_id = data.get('task_id', '')
    model_name = data.get('model_name', '')
    correction = data.get('correction', '')

    if not task_id or not model_name or not correction:
        return jsonify({
            "success": False,
            "error": "task_id, model_name, and correction are required"
        }), 400

    collector = get_feedback()
    feedback_id = collector.submit_correction(
        task_id=task_id,
        model_name=model_name,
        correction=correction,
        task_type=data.get('task_type'),
        comment=data.get('comment'),
    )

    return jsonify({
        "success": True,
        "feedback_id": feedback_id,
        "message": "Thanks for the correction! We'll learn from this."
    })


@app.route('/api/feedback/stats', methods=['GET'])
def feedback_stats():
    """Get feedback statistics"""
    collector = get_feedback()
    return jsonify({
        "success": True,
        "stats": collector.get_statistics()
    })


@app.route('/api/feedback/model/<model_name>', methods=['GET'])
def model_feedback(model_name):
    """Get feedback and satisfaction for a model"""
    collector = get_feedback()
    satisfaction = collector.get_model_satisfaction(model_name)
    recent = collector.get_feedback_for_model(model_name, limit=10)

    return jsonify({
        "success": True,
        "model": model_name,
        "satisfaction": satisfaction,
        "recent_feedback": [
            {
                "type": f.feedback_type.value,
                "is_positive": f.is_positive,
                "rating": f.rating,
                "comment": f.comment,
                "timestamp": f.timestamp,
            }
            for f in recent
        ]
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
# Code Execution Sandbox
# ============================================

# Global sandbox instance
code_executor = None

def get_executor():
    """Get or create the code executor instance"""
    global code_executor
    if code_executor is None:
        from ai_dev_team.sandbox import get_code_executor
        code_executor = get_code_executor()
    return code_executor


@app.route('/api/sandbox/execute', methods=['POST'])
@async_route
async def execute_code():
    """Execute code in sandbox"""
    data = request.get_json() or {}

    code = data.get('code', '')
    language = data.get('language', 'python')
    timeout = data.get('timeout')
    validate = data.get('validate', True)

    if not code:
        return jsonify({
            "success": False,
            "error": "code is required"
        }), 400

    executor = get_executor()

    if validate:
        result = await executor.execute_with_validation(code, language, timeout)
    else:
        result = await executor.execute(code, language, timeout)

    return jsonify({
        "success": result.success,
        "result": result.to_dict()
    })


@app.route('/api/sandbox/validate', methods=['POST'])
def validate_code():
    """Validate code without executing"""
    data = request.get_json() or {}

    code = data.get('code', '')
    language = data.get('language', 'python')

    if not code:
        return jsonify({
            "success": False,
            "error": "code is required"
        }), 400

    if language.lower() != 'python':
        return jsonify({
            "success": True,
            "validation": {
                "valid": True,
                "warnings": ["Validation only available for Python"],
                "blocked": []
            }
        })

    executor = get_executor()
    validation = executor.validate_python_code(code)

    return jsonify({
        "success": True,
        "validation": validation
    })


@app.route('/api/sandbox/history', methods=['GET'])
def execution_history():
    """Get recent execution history"""
    limit = request.args.get('limit', 50, type=int)

    executor = get_executor()
    history = executor.get_execution_history(limit)

    return jsonify({
        "success": True,
        "history": history,
        "count": len(history)
    })


@app.route('/api/sandbox/stats', methods=['GET'])
def sandbox_stats():
    """Get sandbox statistics"""
    executor = get_executor()
    stats = executor.get_statistics()

    return jsonify({
        "success": True,
        "stats": stats
    })


# ============================================
# Real-time Streaming (SSE)
# ============================================

# Global stream manager instance
stream_manager = None

def get_streams():
    """Get or create the stream manager instance"""
    global stream_manager
    if stream_manager is None:
        from ai_dev_team.streaming import get_stream_manager
        stream_manager = get_stream_manager()
    return stream_manager


@app.route('/api/stream/create', methods=['POST'])
def create_stream():
    """Create a new stream for SSE"""
    from ai_dev_team.streaming import StreamType
    data = request.get_json() or {}

    stream_type_str = data.get('type', 'ai_response')
    metadata = data.get('metadata', {})

    try:
        stream_type = StreamType(stream_type_str)
    except ValueError:
        return jsonify({
            "success": False,
            "error": f"Invalid stream type. Valid types: {[t.value for t in StreamType]}"
        }), 400

    manager = get_streams()
    stream = manager.create_stream(stream_type, metadata)

    return jsonify({
        "success": True,
        "stream_id": stream.stream_id,
        "stream_type": stream.stream_type.value,
        "sse_url": f"/api/stream/{stream.stream_id}/events"
    })


@app.route('/api/stream/<stream_id>/events', methods=['GET'])
def stream_events(stream_id):
    """SSE endpoint - subscribe to stream events"""
    from flask import Response

    manager = get_streams()
    stream = manager.get_stream(stream_id)

    if not stream:
        return jsonify({
            "success": False,
            "error": "Stream not found"
        }), 404

    def generate():
        for event_sse in manager.get_stream_events_sse(stream_id):
            yield event_sse

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


@app.route('/api/stream/<stream_id>/emit', methods=['POST'])
def emit_to_stream(stream_id):
    """Emit an event to a stream"""
    data = request.get_json() or {}

    event_type = data.get('event_type', 'message')
    event_data = data.get('data', {})

    manager = get_streams()
    success = manager.emit_to_stream(stream_id, event_type, event_data)

    if success:
        return jsonify({
            "success": True,
            "message": f"Event emitted to stream {stream_id}"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Stream not found or not active"
        }), 404


@app.route('/api/stream/<stream_id>/complete', methods=['POST'])
def complete_stream(stream_id):
    """Complete a stream"""
    data = request.get_json() or {}
    final_data = data.get('data')

    manager = get_streams()
    manager.complete_stream(stream_id, final_data)

    return jsonify({
        "success": True,
        "message": f"Stream {stream_id} completed"
    })


@app.route('/api/stream/<stream_id>', methods=['GET'])
def get_stream_info(stream_id):
    """Get stream information"""
    manager = get_streams()
    stream = manager.get_stream(stream_id)

    if not stream:
        return jsonify({
            "success": False,
            "error": "Stream not found"
        }), 404

    return jsonify({
        "success": True,
        "stream": stream.to_dict()
    })


@app.route('/api/stream/active', methods=['GET'])
def list_active_streams():
    """List all active streams"""
    manager = get_streams()
    streams = manager.get_active_streams()

    return jsonify({
        "success": True,
        "streams": streams,
        "count": len(streams)
    })


@app.route('/api/stream/stats', methods=['GET'])
def stream_stats():
    """Get streaming statistics"""
    manager = get_streams()
    stats = manager.get_statistics()

    return jsonify({
        "success": True,
        "stats": stats
    })


@app.route('/api/stream/demo', methods=['POST'])
def demo_stream():
    """Create a demo stream that emits sample tokens"""
    import threading
    import time

    data = request.get_json() or {}
    message = data.get('message', 'Hello! This is a demo of real-time AI response streaming.')

    manager = get_streams()
    from ai_dev_team.streaming import StreamType
    stream = manager.create_stream(
        StreamType.AI_RESPONSE,
        metadata={'demo': True, 'model': 'demo'}
    )

    def emit_tokens():
        words = message.split()
        for i, word in enumerate(words):
            manager.emit_to_stream(
                stream.stream_id,
                'token',
                {'token': word + ' ', 'index': i}
            )
            time.sleep(0.1)  # Simulate token generation delay
        manager.complete_stream(
            stream.stream_id,
            {'full_response': message, 'token_count': len(words)}
        )

    thread = threading.Thread(target=emit_tokens)
    thread.start()

    return jsonify({
        "success": True,
        "stream_id": stream.stream_id,
        "sse_url": f"/api/stream/{stream.stream_id}/events",
        "message": "Demo stream created. Connect to SSE URL to receive tokens."
    })


# ============================================
# Cross-Project Learning
# ============================================

# Global cross-project learning instance
cross_learning = None

def get_learning():
    """Get or create the cross-project learning instance"""
    global cross_learning
    if cross_learning is None:
        from ai_dev_team.learning import get_cross_project_learning
        cross_learning = get_cross_project_learning()
    return cross_learning


@app.route('/api/learning/projects', methods=['GET'])
def list_learning_projects():
    """List all registered projects"""
    learner = get_learning()
    projects = learner.list_projects()

    return jsonify({
        "success": True,
        "projects": projects,
        "count": len(projects)
    })


@app.route('/api/learning/projects', methods=['POST'])
def register_project():
    """Register a new project for cross-project learning"""
    data = request.get_json() or {}

    name = data.get('name')
    domain = data.get('domain')
    description = data.get('description', '')
    technologies = data.get('technologies', [])
    frameworks = data.get('frameworks', [])
    challenges = data.get('challenges', [])

    if not name or not domain:
        return jsonify({
            "success": False,
            "error": "name and domain are required"
        }), 400

    learner = get_learning()
    profile = learner.register_project(
        name=name,
        domain=domain,
        description=description,
        technologies=technologies,
        frameworks=frameworks,
        challenges=challenges,
    )

    return jsonify({
        "success": True,
        "project": profile.to_dict()
    })


@app.route('/api/learning/projects/<project_name>', methods=['GET'])
def get_learning_project(project_name):
    """Get a project profile"""
    learner = get_learning()
    profile = learner.get_project(project_name)

    if not profile:
        return jsonify({
            "success": False,
            "error": "Project not found"
        }), 404

    return jsonify({
        "success": True,
        "project": profile.to_dict()
    })


@app.route('/api/learning/projects/<project_name>/similar', methods=['GET'])
def find_similar_projects(project_name):
    """Find projects similar to the given project"""
    learner = get_learning()
    min_similarity = request.args.get('min_similarity', 0.3, type=float)

    similar = learner.find_similar_projects(project_name, min_similarity)

    return jsonify({
        "success": True,
        "similar_projects": similar,
        "count": len(similar)
    })


@app.route('/api/learning/knowledge', methods=['POST'])
def add_knowledge():
    """Add a new knowledge entry"""
    data = request.get_json() or {}

    source_project = data.get('source_project')
    entry_type = data.get('entry_type')
    title = data.get('title')
    description = data.get('description', '')
    content = data.get('content')
    tags = data.get('tags', [])
    technologies = data.get('technologies')

    if not source_project or not entry_type or not title or not content:
        return jsonify({
            "success": False,
            "error": "source_project, entry_type, title, and content are required"
        }), 400

    learner = get_learning()
    entry = learner.add_knowledge(
        source_project=source_project,
        entry_type=entry_type,
        title=title,
        description=description,
        content=content,
        tags=tags,
        technologies=technologies,
    )

    return jsonify({
        "success": True,
        "entry": entry.to_dict()
    })


@app.route('/api/learning/knowledge/search', methods=['GET'])
def search_knowledge():
    """Search the knowledge base"""
    learner = get_learning()

    query = request.args.get('query')
    entry_type = request.args.get('type')
    tags = request.args.getlist('tags')
    technologies = request.args.getlist('technologies')
    project = request.args.get('project')
    limit = request.args.get('limit', 20, type=int)

    results = learner.search_knowledge(
        query=query,
        entry_type=entry_type,
        tags=tags if tags else None,
        technologies=technologies if technologies else None,
        project=project,
        limit=limit,
    )

    return jsonify({
        "success": True,
        "results": results,
        "count": len(results)
    })


@app.route('/api/learning/knowledge/<entry_id>', methods=['GET'])
def get_knowledge_entry(entry_id):
    """Get a knowledge entry by ID"""
    learner = get_learning()
    entry = learner.get_knowledge(entry_id)

    if not entry:
        return jsonify({
            "success": False,
            "error": "Entry not found"
        }), 404

    return jsonify({
        "success": True,
        "entry": entry.to_dict()
    })


@app.route('/api/learning/knowledge/<entry_id>/usage', methods=['POST'])
def record_knowledge_usage(entry_id):
    """Record when knowledge is used by a project"""
    data = request.get_json() or {}

    target_project = data.get('target_project')
    success = data.get('success', True)

    if not target_project:
        return jsonify({
            "success": False,
            "error": "target_project is required"
        }), 400

    learner = get_learning()
    learner.record_usage(entry_id, target_project, success)

    return jsonify({
        "success": True,
        "message": f"Recorded {'successful' if success else 'unsuccessful'} usage"
    })


@app.route('/api/learning/recommendations/<project_name>', methods=['GET'])
def get_recommendations(project_name):
    """Get knowledge recommendations for a project"""
    learner = get_learning()

    context = request.args.get('context')
    limit = request.args.get('limit', 10, type=int)

    recommendations = learner.get_recommendations_for_project(
        project_name,
        context=context,
        limit=limit,
    )

    return jsonify({
        "success": True,
        "recommendations": recommendations,
        "count": len(recommendations)
    })


@app.route('/api/learning/transfer', methods=['POST'])
def transfer_knowledge():
    """Transfer knowledge to another project"""
    data = request.get_json() or {}

    entry_id = data.get('entry_id')
    target_project = data.get('target_project')

    if not entry_id or not target_project:
        return jsonify({
            "success": False,
            "error": "entry_id and target_project are required"
        }), 400

    learner = get_learning()
    result = learner.transfer_knowledge(entry_id, target_project)

    return jsonify(result)


@app.route('/api/learning/insights', methods=['GET'])
def get_insights():
    """Get cross-project insights"""
    learner = get_learning()
    insights = learner.generate_insights()

    return jsonify({
        "success": True,
        "insights": insights,
        "count": len(insights)
    })


@app.route('/api/learning/stats', methods=['GET'])
def learning_stats():
    """Get cross-project learning statistics"""
    learner = get_learning()
    stats = learner.get_statistics()

    return jsonify({
        "success": True,
        "stats": stats
    })


# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║              AITeamPlatform API Server                            ║
╠═══════════════════════════════════════════════════════════════════╣
║  AI Collaboration:                                                ║
║    GET  /api/health         - Health check                        ║
║    GET  /api/team/status    - Team status                         ║
║    GET  /api/providers      - List AI providers                   ║
║    POST /api/ai/collaborate - Parallel collaboration              ║
║    POST /api/ai/review      - Code review                         ║
║    POST /api/ai/fix         - Fix issues                          ║
║    POST /api/ai/ask         - Ask the team                        ║
║  Memory & Learning:                                               ║
║    POST /api/memory/mistake - Store mistake pattern               ║
║    POST /api/memory/solution - Store solution pattern             ║
║    GET  /api/memory/search  - Search mistakes & solutions         ║
║    GET  /api/memory/stats   - Memory system statistics            ║
║  Coding Knowledge Hub:                                            ║
║    GET  /api/hub/stats      - Hub statistics                      ║
║    POST /api/hub/snippet    - Store code snippet                  ║
║    GET  /api/hub/snippet/search - Search snippets                 ║
║    POST /api/hub/error-fix  - Store error->fix mapping            ║
║    GET  /api/hub/error-fix/search - Find fix for error            ║
║    POST /api/hub/pattern    - Store framework pattern             ║
║    GET  /api/hub/pattern/search - Search patterns                 ║
║    POST /api/hub/api-knowledge - Store API knowledge              ║
║    POST /api/hub/context    - Generate coding context             ║
║    POST /api/hub/learn      - Auto-learn from code                ║
║  Performance & Smart Routing:                                     ║
║    GET  /api/router/stats   - Performance statistics              ║
║    GET  /api/router/ranking - Ranked models by task type          ║
║    GET  /api/router/best    - Best model for task                 ║
║    POST /api/router/record  - Record task outcome                 ║
║    POST /api/router/classify - Classify task & get recommendations║
║  Model Health & Failover:                                         ║
║    GET  /api/health/models  - All models health status            ║
║    GET  /api/health/models/<name> - Specific model health         ║
║    GET  /api/health/available - List healthy models               ║
║    GET  /api/failover/stats - Failover statistics                 ║
║    GET  /api/failover/circuit/<name> - Circuit breaker status     ║
║    POST /api/failover/circuit/<name>/open - Open circuit          ║
║    POST /api/failover/circuit/<name>/close - Close circuit        ║
║  User Feedback:                                                   ║
║    POST /api/feedback/thumbs-up - Submit positive feedback        ║
║    POST /api/feedback/thumbs-down - Submit negative feedback      ║
║    POST /api/feedback/rating - Submit 1-5 star rating             ║
║    POST /api/feedback/correction - Submit correction              ║
║    GET  /api/feedback/stats - Feedback statistics                 ║
║    GET  /api/feedback/model/<name> - Model satisfaction           ║
║  Cost Tracking:                                                   ║
║    GET  /api/costs/stats - Comprehensive cost statistics          ║
║    GET  /api/costs/budget - Current budget status                 ║
║    POST /api/costs/budget - Set budget limits                     ║
║    GET  /api/costs/daily - Daily cost report                      ║
║    GET  /api/costs/weekly - Weekly cost report                    ║
║    GET  /api/costs/monthly - Monthly cost report                  ║
║    GET  /api/costs/by-model - Cost breakdown by model             ║
║  Prompt Templates:                                                ║
║    GET  /api/prompts/list - List all templates                    ║
║    GET  /api/prompts/categories - Get categories                  ║
║    GET  /api/prompts/<id> - Get specific template                 ║
║    POST /api/prompts/use - Use template with variables            ║
║    POST /api/prompts/suggest - Suggest template for task          ║
║    POST /api/prompts/create - Create custom template              ║
║    GET  /api/prompts/stats - Template usage statistics            ║
║  Code Sandbox:                                                    ║
║    POST /api/sandbox/execute - Execute code safely                ║
║    POST /api/sandbox/validate - Validate code (Python)            ║
║    GET  /api/sandbox/history - Recent executions                  ║
║    GET  /api/sandbox/stats - Sandbox statistics                   ║
║  Real-time Streaming (SSE):                                       ║
║    POST /api/stream/create - Create a new stream                  ║
║    GET  /api/stream/<id>/events - SSE event stream                ║
║    POST /api/stream/<id>/emit - Emit event to stream              ║
║    POST /api/stream/<id>/complete - Complete stream               ║
║    GET  /api/stream/active - List active streams                  ║
║    GET  /api/stream/stats - Streaming statistics                  ║
║    POST /api/stream/demo - Demo token streaming                   ║
║  Cross-Project Learning:                                          ║
║    GET  /api/learning/projects - List all projects                ║
║    POST /api/learning/projects - Register project                 ║
║    GET  /api/learning/projects/<name>/similar - Find similar      ║
║    POST /api/learning/knowledge - Add knowledge entry             ║
║    GET  /api/learning/knowledge/search - Search knowledge         ║
║    GET  /api/learning/recommendations/<project> - Get suggestions ║
║    POST /api/learning/transfer - Transfer knowledge               ║
║    GET  /api/learning/insights - Cross-project insights           ║
║    GET  /api/learning/stats - Learning statistics                 ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    # Initialize team on startup
    get_team()

    app.run(
        host='0.0.0.0',
        port=5050,
        debug=True
    )
