"""
User Feedback Collector - Ratings and feedback for AI responses
================================================================

Collects user feedback (thumbs up/down, ratings, comments) and
feeds it into the performance tracking system for better routing.

Features:
- Simple thumbs up/down feedback
- 1-5 star ratings
- Text comments/corrections
- Automatic integration with performance tracker
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"  # 1-5 stars
    CORRECTION = "correction"  # User provided correct answer
    COMMENT = "comment"  # General feedback


@dataclass
class Feedback:
    """A single feedback entry"""
    feedback_id: str
    task_id: str
    model_name: str
    feedback_type: FeedbackType
    timestamp: str

    # Feedback data
    is_positive: bool = True
    rating: Optional[int] = None  # 1-5
    comment: Optional[str] = None
    correction: Optional[str] = None

    # Context
    task_type: Optional[str] = None
    prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "task_id": self.task_id,
            "model_name": self.model_name,
            "feedback_type": self.feedback_type.value,
            "timestamp": self.timestamp,
            "is_positive": self.is_positive,
            "rating": self.rating,
            "comment": self.comment,
            "correction": self.correction,
            "task_type": self.task_type,
            "prompt_preview": self.prompt_preview,
            "response_preview": self.response_preview,
        }


class FeedbackCollector:
    """
    Collects and processes user feedback for AI responses.

    Integrates with:
    - Performance tracker: Updates success metrics based on feedback
    - Learning system: Stores corrections for future reference
    - Analytics: Tracks user satisfaction over time

    Usage:
        collector = FeedbackCollector()

        # Simple thumbs up/down
        collector.submit_thumbs_up(task_id, model_name)
        collector.submit_thumbs_down(task_id, model_name, comment="Wrong answer")

        # Star rating
        collector.submit_rating(task_id, model_name, rating=4)

        # Correction
        collector.submit_correction(task_id, model_name, correction="The correct answer is...")
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/feedback",
        integrate_with_performance: bool = True,
    ):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.integrate_with_performance = integrate_with_performance

        self._feedback: List[Feedback] = []
        self._feedback_by_task: Dict[str, List[Feedback]] = {}
        self._feedback_by_model: Dict[str, List[Feedback]] = {}

        # Stats
        self._model_ratings: Dict[str, List[int]] = {}
        self._model_thumbs: Dict[str, Dict[str, int]] = {}

        self._load_data()

    def _load_data(self):
        """Load feedback data from disk"""
        try:
            feedback_file = self.storage_dir / "feedback.json"
            if feedback_file.exists():
                with open(feedback_file) as f:
                    data = json.load(f)

                for item in data.get("feedback", [])[-1000:]:  # Keep last 1000
                    item["feedback_type"] = FeedbackType(item["feedback_type"])
                    feedback = Feedback(**item)
                    self._feedback.append(feedback)
                    self._index_feedback(feedback)

                self._model_ratings = data.get("model_ratings", {})
                self._model_thumbs = data.get("model_thumbs", {})

                logger.info(f"Loaded {len(self._feedback)} feedback entries")
        except Exception as e:
            logger.warning(f"Error loading feedback data: {e}")

    def _save_data(self):
        """Save feedback data to disk"""
        try:
            data = {
                "feedback": [f.to_dict() for f in self._feedback[-1000:]],
                "model_ratings": self._model_ratings,
                "model_thumbs": self._model_thumbs,
                "last_saved": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.storage_dir / "feedback.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feedback data: {e}")

    def _index_feedback(self, feedback: Feedback):
        """Index feedback for quick lookup"""
        # By task
        if feedback.task_id not in self._feedback_by_task:
            self._feedback_by_task[feedback.task_id] = []
        self._feedback_by_task[feedback.task_id].append(feedback)

        # By model
        if feedback.model_name not in self._feedback_by_model:
            self._feedback_by_model[feedback.model_name] = []
        self._feedback_by_model[feedback.model_name].append(feedback)

    def _generate_id(self) -> str:
        """Generate unique feedback ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def _update_performance_tracker(self, model_name: str, is_positive: bool, rating: Optional[int] = None):
        """Update performance tracker with feedback"""
        if not self.integrate_with_performance:
            return

        try:
            from ..routing import get_performance_tracker
            tracker = get_performance_tracker()

            # Convert feedback to performance outcome
            # Positive feedback = success, negative = failure
            # Rating 4-5 = success, 1-2 = failure, 3 = neutral
            if rating is not None:
                success = rating >= 4
                confidence = rating / 5.0
            else:
                success = is_positive
                confidence = 0.8 if is_positive else 0.3

            tracker.record_outcome(
                model_name=model_name,
                task_type="user_feedback",
                success=success,
                confidence=confidence,
                response_time=0.0,  # Not applicable for feedback
                user_rating=rating,
            )

            logger.debug(f"Updated performance tracker for {model_name}: success={success}")
        except Exception as e:
            logger.warning(f"Could not update performance tracker: {e}")

    def submit_thumbs_up(
        self,
        task_id: str,
        model_name: str,
        task_type: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Submit positive feedback (thumbs up).

        Returns:
            Feedback ID
        """
        feedback = Feedback(
            feedback_id=self._generate_id(),
            task_id=task_id,
            model_name=model_name,
            feedback_type=FeedbackType.THUMBS_UP,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_positive=True,
            task_type=task_type,
            comment=comment,
        )

        self._feedback.append(feedback)
        self._index_feedback(feedback)

        # Update thumbs stats
        if model_name not in self._model_thumbs:
            self._model_thumbs[model_name] = {"up": 0, "down": 0}
        self._model_thumbs[model_name]["up"] += 1

        # Update performance tracker
        self._update_performance_tracker(model_name, is_positive=True)

        self._save_data()
        logger.info(f"Thumbs up for {model_name} on task {task_id}")

        return feedback.feedback_id

    def submit_thumbs_down(
        self,
        task_id: str,
        model_name: str,
        task_type: Optional[str] = None,
        comment: Optional[str] = None,
        correction: Optional[str] = None,
    ) -> str:
        """
        Submit negative feedback (thumbs down).

        Returns:
            Feedback ID
        """
        feedback = Feedback(
            feedback_id=self._generate_id(),
            task_id=task_id,
            model_name=model_name,
            feedback_type=FeedbackType.THUMBS_DOWN,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_positive=False,
            task_type=task_type,
            comment=comment,
            correction=correction,
        )

        self._feedback.append(feedback)
        self._index_feedback(feedback)

        # Update thumbs stats
        if model_name not in self._model_thumbs:
            self._model_thumbs[model_name] = {"up": 0, "down": 0}
        self._model_thumbs[model_name]["down"] += 1

        # Update performance tracker
        self._update_performance_tracker(model_name, is_positive=False)

        self._save_data()
        logger.info(f"Thumbs down for {model_name} on task {task_id}")

        return feedback.feedback_id

    def submit_rating(
        self,
        task_id: str,
        model_name: str,
        rating: int,
        task_type: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Submit star rating (1-5).

        Returns:
            Feedback ID
        """
        # Validate rating
        rating = max(1, min(5, rating))

        feedback = Feedback(
            feedback_id=self._generate_id(),
            task_id=task_id,
            model_name=model_name,
            feedback_type=FeedbackType.RATING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_positive=rating >= 3,
            rating=rating,
            task_type=task_type,
            comment=comment,
        )

        self._feedback.append(feedback)
        self._index_feedback(feedback)

        # Update rating stats
        if model_name not in self._model_ratings:
            self._model_ratings[model_name] = []
        self._model_ratings[model_name].append(rating)

        # Update performance tracker
        self._update_performance_tracker(model_name, is_positive=rating >= 4, rating=rating)

        self._save_data()
        logger.info(f"Rating {rating}/5 for {model_name} on task {task_id}")

        return feedback.feedback_id

    def submit_correction(
        self,
        task_id: str,
        model_name: str,
        correction: str,
        task_type: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """
        Submit a correction (the right answer).

        Returns:
            Feedback ID
        """
        feedback = Feedback(
            feedback_id=self._generate_id(),
            task_id=task_id,
            model_name=model_name,
            feedback_type=FeedbackType.CORRECTION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_positive=False,  # Correction implies wrong answer
            correction=correction,
            task_type=task_type,
            comment=comment,
        )

        self._feedback.append(feedback)
        self._index_feedback(feedback)

        # Update performance tracker (correction = failure)
        self._update_performance_tracker(model_name, is_positive=False)

        # Store correction in coding hub for learning
        self._store_correction_for_learning(feedback)

        self._save_data()
        logger.info(f"Correction submitted for {model_name} on task {task_id}")

        return feedback.feedback_id

    def _store_correction_for_learning(self, feedback: Feedback):
        """Store correction in knowledge hub for future reference"""
        if not feedback.correction:
            return

        try:
            from ..knowledge import get_coding_hub
            hub = get_coding_hub()

            # If correction contains code, store as snippet
            if "```" in feedback.correction or "def " in feedback.correction:
                # Try to extract language
                import re
                lang_match = re.search(r'```(\w+)', feedback.correction)
                language = lang_match.group(1) if lang_match else "python"

                hub.learn_from_successful_code(
                    code=feedback.correction,
                    language=language,
                    task_description=f"User correction for {feedback.task_type or 'task'}",
                )
                logger.debug(f"Stored correction as code snippet")
        except Exception as e:
            logger.warning(f"Could not store correction in coding hub: {e}")

    def get_feedback_for_task(self, task_id: str) -> List[Feedback]:
        """Get all feedback for a task"""
        return self._feedback_by_task.get(task_id, [])

    def get_feedback_for_model(self, model_name: str, limit: int = 50) -> List[Feedback]:
        """Get recent feedback for a model"""
        return self._feedback_by_model.get(model_name, [])[-limit:]

    def get_model_satisfaction(self, model_name: str) -> Dict[str, Any]:
        """Get satisfaction metrics for a model"""
        thumbs = self._model_thumbs.get(model_name, {"up": 0, "down": 0})
        ratings = self._model_ratings.get(model_name, [])

        total_thumbs = thumbs["up"] + thumbs["down"]
        thumbs_ratio = thumbs["up"] / total_thumbs if total_thumbs > 0 else 0.5

        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        rating_count = len(ratings)

        # Calculate overall satisfaction (weighted average)
        # Thumbs: 70% weight, Ratings: 30% weight
        if total_thumbs > 0 and rating_count > 0:
            satisfaction = (thumbs_ratio * 0.7) + ((avg_rating / 5) * 0.3)
        elif total_thumbs > 0:
            satisfaction = thumbs_ratio
        elif rating_count > 0:
            satisfaction = avg_rating / 5
        else:
            satisfaction = 0.5  # No data

        return {
            "model_name": model_name,
            "thumbs_up": thumbs["up"],
            "thumbs_down": thumbs["down"],
            "thumbs_ratio": round(thumbs_ratio, 3),
            "average_rating": round(avg_rating, 2),
            "rating_count": rating_count,
            "overall_satisfaction": round(satisfaction, 3),
            "total_feedback": total_thumbs + rating_count,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall feedback statistics"""
        total_feedback = len(self._feedback)

        # Count by type
        type_counts = {}
        for f in self._feedback:
            type_name = f.feedback_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Positive/negative ratio
        positive = sum(1 for f in self._feedback if f.is_positive)
        negative = total_feedback - positive

        # Model satisfaction
        model_satisfaction = {}
        for model in set(self._model_thumbs.keys()) | set(self._model_ratings.keys()):
            model_satisfaction[model] = self.get_model_satisfaction(model)

        return {
            "total_feedback": total_feedback,
            "positive_count": positive,
            "negative_count": negative,
            "positive_ratio": round(positive / total_feedback, 3) if total_feedback > 0 else 0.5,
            "feedback_by_type": type_counts,
            "model_satisfaction": model_satisfaction,
            "corrections_collected": type_counts.get("correction", 0),
        }


# Global instance
_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get or create the global feedback collector"""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector
