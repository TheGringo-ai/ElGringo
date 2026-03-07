"""
Feedback Capture System
=======================

Captures successful AI interactions for model fine-tuning.
Stores in MLX-compatible JSONL format with ChatML template.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Storage paths
FEEDBACK_DIR = Path.home() / '.ai-dev-team' / 'feedback'
MLX_TRAINING_DIR = Path(__file__).parent.parent.parent / 'mlx-training' / 'data'


@dataclass
class FeedbackEntry:
    """A single feedback entry for training."""
    prompt: str
    response: str
    system_prompt: str = "You are an expert AI coding assistant."
    rating: float = 1.0  # 0.0 to 1.0, higher is better
    category: str = "general"  # general, firebase, python, etc.
    agent: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_chatml(self) -> str:
        """Convert to ChatML format for MLX training."""
        return (
            f"<|im_start|>system\n{self.system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{self.prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n{self.response}<|im_end|>"
        )

    def to_training_dict(self) -> Dict[str, str]:
        """Convert to training JSONL format."""
        return {"text": self.to_chatml()}


class FeedbackCapture:
    """
    Captures and stores feedback from Fred interactions.
    
    Usage:
        capture = FeedbackCapture()
        
        # Capture a successful interaction
        capture.add(
            prompt="How do I query Firestore?",
            response="Use db.collection('users').where(...)",
            category="firebase",
            rating=1.0
        )
        
        # Export to MLX training format
        capture.export_to_mlx()
    """

    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or FEEDBACK_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.feedback_file = self.storage_dir / 'feedback.jsonl'
        self.pending_file = self.storage_dir / 'pending.jsonl'
        
        self._pending: List[FeedbackEntry] = []
        self._load_pending()

    def _load_pending(self):
        """Load pending feedback entries."""
        if self.pending_file.exists():
            try:
                with open(self.pending_file) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            self._pending.append(FeedbackEntry(**data))
            except Exception as e:
                logger.warning(f"Error loading pending feedback: {e}")

    def _save_pending(self):
        """Save pending feedback entries."""
        try:
            with open(self.pending_file, 'w') as f:
                for entry in self._pending:
                    f.write(json.dumps(asdict(entry)) + '\n')
        except Exception as e:
            logger.error(f"Error saving pending feedback: {e}")

    def add(
        self,
        prompt: str,
        response: str,
        system_prompt: str = None,
        rating: float = 1.0,
        category: str = "general",
        agent: str = "unknown",
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Add a feedback entry.
        
        Args:
            prompt: User's question/request
            response: AI's response
            system_prompt: System prompt used (optional)
            rating: Quality rating 0.0-1.0 (default 1.0 for approved)
            category: Category for filtering (firebase, python, etc.)
            agent: Which agent produced this response
            metadata: Additional metadata
            
        Returns:
            Entry ID
        """
        entry = FeedbackEntry(
            prompt=prompt,
            response=response,
            system_prompt=system_prompt or "You are an expert AI coding assistant.",
            rating=rating,
            category=category,
            agent=agent,
            metadata=metadata or {}
        )
        
        # Save immediately to feedback log
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
        
        # Add to pending for next training batch
        if rating >= 0.8:  # Only high-quality responses
            self._pending.append(entry)
            self._save_pending()
            logger.info(f"Captured feedback: {category} ({len(self._pending)} pending)")
        
        return entry.timestamp

    def get_pending_count(self) -> int:
        """Get number of pending entries."""
        return len(self._pending)

    def get_pending(self, category: str = None) -> List[FeedbackEntry]:
        """Get pending entries, optionally filtered by category."""
        if category:
            return [e for e in self._pending if e.category == category]
        return self._pending.copy()

    def export_to_mlx(
        self,
        output_dir: Path = None,
        min_entries: int = 10,
        category: str = None
    ) -> Optional[Path]:
        """
        Export pending feedback to MLX training format.
        
        Args:
            output_dir: Output directory (default: mlx-training/data)
            min_entries: Minimum entries required to export
            category: Filter by category
            
        Returns:
            Path to exported file, or None if not enough entries
        """
        entries = self.get_pending(category)
        
        if len(entries) < min_entries:
            logger.info(f"Not enough entries ({len(entries)}/{min_entries})")
            return None
        
        output_dir = output_dir or MLX_TRAINING_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'feedback_{timestamp}.jsonl'
        
        # Write in MLX training format
        with open(output_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry.to_training_dict()) + '\n')
        
        # Also append to main training file
        train_file = output_dir / 'train.jsonl'
        with open(train_file, 'a') as f:
            for entry in entries:
                f.write(json.dumps(entry.to_training_dict()) + '\n')
        
        logger.info(f"Exported {len(entries)} entries to {output_file}")
        
        # Clear exported entries from pending
        if category:
            self._pending = [e for e in self._pending if e.category != category]
        else:
            self._pending = []
        self._save_pending()
        
        return output_file

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        total = 0
        categories = {}
        
        if self.feedback_file.exists():
            with open(self.feedback_file) as f:
                for line in f:
                    if line.strip():
                        total += 1
                        try:
                            data = json.loads(line)
                            cat = data.get('category', 'unknown')
                            categories[cat] = categories.get(cat, 0) + 1
                        except Exception:
                            logger.debug("Failed to parse feedback line: %s", line.strip())
        
        return {
            'total_captured': total,
            'pending_for_training': len(self._pending),
            'by_category': categories
        }


# Global instance
_capture_instance: Optional[FeedbackCapture] = None


def get_feedback_capture() -> FeedbackCapture:
    """Get or create the global feedback capture instance."""
    global _capture_instance
    if _capture_instance is None:
        _capture_instance = FeedbackCapture()
    return _capture_instance


def capture_feedback(
    prompt: str,
    response: str,
    category: str = "general",
    rating: float = 1.0,
    agent: str = "unknown",
    **kwargs
) -> str:
    """
    Convenience function to capture feedback.
    
    Example:
        from ai_dev_team.feedback import capture_feedback
        
        capture_feedback(
            prompt="How do I batch write to Firestore?",
            response="Use batch = db.batch(); batch.set(...); batch.commit()",
            category="firebase",
            agent="chatgpt-coder"
        )
    """
    capture = get_feedback_capture()
    return capture.add(
        prompt=prompt,
        response=response,
        category=category,
        rating=rating,
        agent=agent,
        **kwargs
    )
