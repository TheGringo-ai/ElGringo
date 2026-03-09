"""
Feedback Trainer
================

Triggers MLX fine-tuning with accumulated feedback data.
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .capture import get_feedback_capture

logger = logging.getLogger(__name__)

MLX_TRAINING_DIR = Path(__file__).parent.parent.parent / 'mlx-training'


@dataclass
class TrainingResult:
    """Result of a training run."""
    success: bool
    entries_trained: int
    duration_seconds: float
    output_path: Optional[str] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = None


class FeedbackTrainer:
    """
    Manages training with feedback data.
    
    Usage:
        trainer = FeedbackTrainer()
        
        # Check if ready to train
        if trainer.should_train():
            result = await trainer.train()
            print(f"Trained on {result.entries_trained} examples")
    """

    def __init__(
        self,
        min_entries: int = 20,
        auto_train: bool = False,
        training_script: str = None
    ):
        """
        Initialize the feedback trainer.
        
        Args:
            min_entries: Minimum feedback entries before training
            auto_train: Automatically train when threshold reached
            training_script: Path to MLX training script
        """
        self.min_entries = min_entries
        self.auto_train = auto_train
        self.training_script = training_script or str(
            MLX_TRAINING_DIR / 'scripts' / 'train_qwen_coder.py'
        )
        
        self.capture = get_feedback_capture()
        self._last_train_time: Optional[datetime] = None
        self._training_history: List[TrainingResult] = []

    def should_train(self) -> bool:
        """Check if we have enough data for training."""
        return self.capture.get_pending_count() >= self.min_entries

    def get_status(self) -> Dict[str, Any]:
        """Get trainer status."""
        pending = self.capture.get_pending_count()
        return {
            'pending_entries': pending,
            'min_entries': self.min_entries,
            'ready_to_train': pending >= self.min_entries,
            'last_training': self._last_train_time.isoformat() if self._last_train_time else None,
            'total_trainings': len(self._training_history),
            'auto_train': self.auto_train
        }

    async def train(
        self,
        iterations: int = 100,
        category: str = None,
        dry_run: bool = False
    ) -> TrainingResult:
        """
        Run training with accumulated feedback.
        
        Args:
            iterations: Training iterations
            category: Only train on specific category
            dry_run: Just export data, don't actually train
            
        Returns:
            TrainingResult with outcome
        """
        start_time = datetime.now()
        
        # Export feedback to training format
        export_path = self.capture.export_to_mlx(
            min_entries=1 if dry_run else self.min_entries,
            category=category
        )
        
        if not export_path:
            return TrainingResult(
                success=False,
                entries_trained=0,
                duration_seconds=0,
                error=f"Not enough entries (need {self.min_entries})"
            )
        
        # Count entries
        with open(export_path) as f:
            entries_count = sum(1 for _ in f)
        
        if dry_run:
            return TrainingResult(
                success=True,
                entries_trained=entries_count,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                output_path=str(export_path),
                metrics={'dry_run': True}
            )
        
        # Run MLX training
        try:
            logger.info(f"Starting MLX training with {entries_count} entries...")
            
            result = subprocess.run(
                [
                    'python', self.training_script,
                    '--iters', str(iterations),
                    '--data', str(export_path.parent)
                ],
                cwd=str(MLX_TRAINING_DIR),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour max
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                self._last_train_time = datetime.now()
                
                training_result = TrainingResult(
                    success=True,
                    entries_trained=entries_count,
                    duration_seconds=duration,
                    output_path=str(MLX_TRAINING_DIR / 'models' / 'qwen-coder-lora'),
                    metrics={
                        'iterations': iterations,
                        'stdout': result.stdout[-1000:] if result.stdout else None
                    }
                )
            else:
                training_result = TrainingResult(
                    success=False,
                    entries_trained=entries_count,
                    duration_seconds=duration,
                    error=result.stderr[-500:] if result.stderr else "Unknown error"
                )
            
            self._training_history.append(training_result)
            return training_result
            
        except subprocess.TimeoutExpired:
            return TrainingResult(
                success=False,
                entries_trained=entries_count,
                duration_seconds=3600,
                error="Training timed out (1 hour limit)"
            )
        except Exception as e:
            return TrainingResult(
                success=False,
                entries_trained=entries_count,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )

    async def maybe_auto_train(self) -> Optional[TrainingResult]:
        """
        Check and run training if auto_train is enabled and threshold met.
        
        Call this periodically or after adding feedback.
        """
        if self.auto_train and self.should_train():
            logger.info("Auto-training triggered!")
            return await self.train()
        return None


# Global instance
_trainer_instance: Optional[FeedbackTrainer] = None


def get_feedback_trainer(auto_train: bool = False) -> FeedbackTrainer:
    """Get or create the global feedback trainer instance."""
    global _trainer_instance
    if _trainer_instance is None:
        _trainer_instance = FeedbackTrainer(auto_train=auto_train)
    return _trainer_instance
