"""
Feedback Loop System
====================

Captures successful Fred interactions for continuous model improvement.
"""

from .capture import FeedbackCapture, capture_feedback, get_feedback_capture
from .trainer import FeedbackTrainer, get_feedback_trainer

__all__ = [
    'FeedbackCapture', 
    'capture_feedback', 
    'get_feedback_capture',
    'FeedbackTrainer',
    'get_feedback_trainer'
]
