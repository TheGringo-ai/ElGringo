"""
Singleton service providers for Command Center.
All ai_dev_team imports are centralized here.
"""

import logging

logger = logging.getLogger(__name__)

_sprint_manager = None
_content_generator = None
_content_queue = None
_scheduler = None
_standup_generator = None
_ai_team = None
_persona_library = None


def get_sprint_manager():
    global _sprint_manager
    if _sprint_manager is None:
        from ai_dev_team.workflow.sprint_manager import SprintManager
        _sprint_manager = SprintManager()
        logger.info(f"SprintManager: {len(_sprint_manager.tasks)} tasks, {len(_sprint_manager.sprints)} sprints")
    return _sprint_manager


def get_content_generator():
    global _content_generator
    if _content_generator is None:
        from ai_dev_team.workflow.content_generator import ContentGenerator
        _content_generator = ContentGenerator()
    return _content_generator


def get_content_queue():
    global _content_queue
    if _content_queue is None:
        from ai_dev_team.workflow.content_generator import ContentQueue
        _content_queue = ContentQueue()
    return _content_queue


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        from ai_dev_team.workflow.scheduler import TaskScheduler
        _scheduler = TaskScheduler()
    return _scheduler


def get_standup_generator():
    global _standup_generator
    if _standup_generator is None:
        from ai_dev_team.workflow.standup import StandupGenerator
        _standup_generator = StandupGenerator()
    return _standup_generator


def get_ai_team():
    global _ai_team
    if _ai_team is None:
        from ai_dev_team.orchestrator import AIDevTeam
        _ai_team = AIDevTeam(project_name="command-center", enable_memory=True)
        logger.info(f"AIDevTeam: {len(_ai_team.agents)} agents")
    return _ai_team


def get_persona_library():
    global _persona_library
    if _persona_library is None:
        from ai_dev_team.workflow.personas import PersonaLibrary
        _persona_library = PersonaLibrary()
    return _persona_library
