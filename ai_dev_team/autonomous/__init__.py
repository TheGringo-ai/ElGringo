"""
Autonomous AI capabilities for self-correction, task decomposition, and learning.
"""

from .self_corrector import SelfCorrector, CorrectionStrategy, CorrectionResult
from .task_decomposer import TaskDecomposer, SubTask, ExecutionGraph, GraphExecutor
from .session_learner import SessionLearner, AgentPerformance, TaskOutcome, TeamAdapter
from .file_watcher import (
    FileWatcher,
    WatchAction,
    NegativeSpaceWatcher,
    NegativeSpaceAlert,
    create_document_watcher,
    create_code_watcher,
    create_smart_watcher,
)

__all__ = [
    'SelfCorrector',
    'CorrectionStrategy',
    'CorrectionResult',
    'TaskDecomposer',
    'SubTask',
    'ExecutionGraph',
    'GraphExecutor',
    'SessionLearner',
    'AgentPerformance',
    'TaskOutcome',
    'TeamAdapter',
    # File Watcher
    'FileWatcher',
    'WatchAction',
    'create_document_watcher',
    'create_code_watcher',
    # Negative-Space Detection
    'NegativeSpaceWatcher',
    'NegativeSpaceAlert',
    'create_smart_watcher',
]
