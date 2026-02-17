"""
Auto-Learning System - Continuously learns from every interaction
==================================================================

Automatically extracts lessons, prompts, patterns, and knowledge
from AI team interactions without manual intervention.
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .teaching import TeachingSystem, Lesson
from .data_manager import DataManager, DataLimits, get_data_manager

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPrompt:
    """A successful prompt pattern extracted from interactions"""
    prompt_id: str
    original_prompt: str
    refined_prompt: str  # Improved version
    task_type: str
    domains: List[str]
    success_indicators: List[str]
    usage_count: int = 1
    success_rate: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class InteractionInsight:
    """Insight extracted from an interaction"""
    insight_type: str  # "lesson", "pattern", "mistake", "solution", "prompt"
    content: str
    confidence: float
    domains: List[str]
    source_interaction_id: str
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConversationContext:
    """Context from a conversation for learning"""
    conversation_id: str
    user_intent: str
    prompts_used: List[str]
    responses: List[Dict[str, Any]]
    outcome: str  # "success", "partial", "failure"
    domains_involved: List[str]
    task_type: str
    duration_seconds: float
    models_used: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutoLearner:
    """
    Automatically learns from every AI team interaction.

    Extracts:
    - Lessons from successful outcomes
    - Patterns that work well
    - Mistakes to avoid
    - Effective prompts
    - Domain-specific knowledge
    """

    def __init__(
        self,
        teaching_system: Optional[TeachingSystem] = None,
        storage_dir: str = "~/.ai-dev-team/auto-learning",
        data_limits: Optional[DataLimits] = None
    ):
        self.teaching_system = teaching_system or TeachingSystem()
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data manager for size limits and cleanup
        self._data_manager = get_data_manager(os.path.expanduser("~/.ai-dev-team"))
        if data_limits:
            self._data_manager.limits = data_limits

        self._prompts: List[ExtractedPrompt] = []
        self._insights: List[InteractionInsight] = []
        self._conversations: List[ConversationContext] = []
        self._pending_analysis: List[ConversationContext] = []

        # Learning thresholds
        self._min_confidence_for_lesson = 0.7
        self._min_success_rate_for_prompt = 0.8
        self._analysis_batch_size = 5

        self._load_data()

        # Background learning task
        self._learning_task: Optional[asyncio.Task] = None

        # Auto-cleanup on init if needed
        self._check_and_cleanup()

    def _load_data(self):
        """Load existing auto-learned data"""
        try:
            prompts_file = self.storage_dir / "prompts.json"
            if prompts_file.exists():
                with open(prompts_file) as f:
                    data = json.load(f)
                    self._prompts = [ExtractedPrompt(**p) for p in data]

            insights_file = self.storage_dir / "insights.json"
            if insights_file.exists():
                with open(insights_file) as f:
                    data = json.load(f)
                    self._insights = [InteractionInsight(**i) for i in data]

            conversations_file = self.storage_dir / "conversations.json"
            if conversations_file.exists():
                with open(conversations_file) as f:
                    data = json.load(f)
                    self._conversations = [ConversationContext(**c) for c in data]

        except Exception as e:
            logger.warning(f"Error loading auto-learning data: {e}")

    def _check_and_cleanup(self):
        """Check limits and cleanup if needed"""
        limits = self._data_manager.limits

        # Check if in-memory data exceeds limits
        needs_cleanup = False

        if len(self._prompts) > limits.max_prompts:
            self._prune_prompts(limits.max_prompts)
            needs_cleanup = True

        if len(self._insights) > limits.max_insights:
            self._prune_insights(limits.max_insights)
            needs_cleanup = True

        if len(self._conversations) > limits.max_conversations:
            self._prune_conversations(limits.max_conversations)
            needs_cleanup = True

        if needs_cleanup:
            logger.info("Auto-cleanup performed to stay within limits")
            self._save_data()

    def _prune_prompts(self, max_count: int):
        """Prune prompts to max_count, keeping most valuable"""
        if len(self._prompts) <= max_count:
            return

        # Score by success_rate * 0.6 + usage_normalized * 0.4
        max_usage = max((p.usage_count for p in self._prompts), default=1)

        scored = []
        for p in self._prompts:
            usage_norm = p.usage_count / max_usage
            score = p.success_rate * 0.6 + usage_norm * 0.4
            scored.append((p, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        self._prompts = [p for p, _ in scored[:max_count]]
        logger.info(f"Pruned prompts to {len(self._prompts)}")

    def _prune_insights(self, max_count: int):
        """Prune insights to max_count, keeping most valuable"""
        if len(self._insights) <= max_count:
            return

        # Score by confidence and type
        type_weights = {"solution": 1.0, "pattern": 0.9, "lesson": 0.8, "mistake": 0.7, "prompt": 0.6}

        scored = []
        for i in self._insights:
            type_weight = type_weights.get(i.insight_type, 0.5)
            score = i.confidence * 0.7 + type_weight * 0.3
            scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        self._insights = [i for i, _ in scored[:max_count]]
        logger.info(f"Pruned insights to {len(self._insights)}")

    def _prune_conversations(self, max_count: int):
        """Prune conversations to max_count, keeping recent and successful"""
        if len(self._conversations) <= max_count:
            return

        # Score by recency and success
        scored = []
        for c in self._conversations:
            # More recent = higher score
            recency = 1.0  # Default high
            success = 1.0 if c.outcome == "success" else 0.3
            score = recency * 0.5 + success * 0.5
            scored.append((c, score, c.timestamp))

        # Sort by timestamp (most recent first) and score
        scored.sort(key=lambda x: (x[2], x[1]), reverse=True)
        self._conversations = [c for c, _, _ in scored[:max_count]]
        logger.info(f"Pruned conversations to {len(self._conversations)}")

    def _save_data(self):
        """Save auto-learned data with size limits"""
        try:
            # Check limits before saving
            self._check_and_cleanup()

            with open(self.storage_dir / "prompts.json", "w") as f:
                json.dump([asdict(p) for p in self._prompts], f, indent=2)

            with open(self.storage_dir / "insights.json", "w") as f:
                json.dump([asdict(i) for i in self._insights], f, indent=2)

            with open(self.storage_dir / "conversations.json", "w") as f:
                json.dump([asdict(c) for c in self._conversations], f, indent=2)

            # Register with data manager for tracking
            for p in self._prompts[-10:]:  # Only track recent additions
                self._data_manager.register_item("prompts", p.prompt_id, {
                    "success_rate": p.success_rate,
                    "usage": p.usage_count,
                    "task_type": p.task_type
                })

        except Exception as e:
            logger.error(f"Error saving auto-learning data: {e}")

    async def capture_interaction(
        self,
        user_prompt: str,
        ai_responses: List[Dict[str, Any]],
        outcome: str,
        task_type: str = "general",
        domains: Optional[List[str]] = None,
        models_used: Optional[List[str]] = None,
        duration_seconds: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Capture an interaction for learning.

        This should be called after every AI team interaction.
        """
        import hashlib
        conversation_id = hashlib.sha256(
            f"{user_prompt}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Detect domains if not provided
        if not domains:
            domains = self._detect_domains(user_prompt, ai_responses)

        context = ConversationContext(
            conversation_id=conversation_id,
            user_intent=self._extract_intent(user_prompt),
            prompts_used=[user_prompt],
            responses=ai_responses,
            outcome=outcome,
            domains_involved=domains,
            task_type=task_type,
            duration_seconds=duration_seconds,
            models_used=models_used or []
        )

        self._conversations.append(context)
        self._pending_analysis.append(context)

        # Trigger immediate learning for successful interactions
        if outcome == "success":
            await self._learn_from_success(context)
        elif outcome == "failure":
            await self._learn_from_failure(context)

        # Batch analysis when enough interactions accumulate
        if len(self._pending_analysis) >= self._analysis_batch_size:
            await self._analyze_batch()

        self._save_data()
        logger.info(f"Captured interaction {conversation_id} for learning")
        return conversation_id

    def _detect_domains(
        self,
        prompt: str,
        responses: List[Dict[str, Any]]
    ) -> List[str]:
        """Detect domains from prompt and responses"""
        domains = []
        text = prompt.lower()

        # Add response content to analysis
        for resp in responses:
            if isinstance(resp, dict) and "content" in resp:
                text += " " + resp["content"].lower()

        # Domain detection patterns
        domain_patterns = {
            "frontend": ["react", "vue", "angular", "css", "html", "ui", "component", "jsx", "tsx"],
            "backend": ["api", "server", "endpoint", "database", "rest", "graphql", "fastapi", "express"],
            "database": ["sql", "query", "postgres", "mysql", "mongo", "redis", "index", "migration"],
            "devops": ["docker", "kubernetes", "deploy", "ci/cd", "terraform", "aws", "gcp"],
            "security": ["auth", "jwt", "oauth", "encrypt", "password", "vulnerability", "xss", "sql injection"],
            "architecture": ["microservice", "design", "pattern", "scale", "architecture", "system design"],
            "testing": ["test", "jest", "pytest", "cypress", "coverage", "mock", "assertion"],
            "fred_ecosystem": ["chatterfix", "fixitfred", "linesmart", "artproof", "freddymac", "thegringoai", "voice", "ai team"]
        }

        for domain, keywords in domain_patterns.items():
            if any(kw in text for kw in keywords):
                domains.append(domain)

        return domains if domains else ["general"]

    def _extract_intent(self, prompt: str) -> str:
        """Extract the core intent from a prompt"""
        # Remove common prefixes
        intent = prompt.strip()
        prefixes_to_remove = [
            "can you", "could you", "please", "i want to", "i need to",
            "help me", "i'd like to", "let's"
        ]

        lower_intent = intent.lower()
        for prefix in prefixes_to_remove:
            if lower_intent.startswith(prefix):
                intent = intent[len(prefix):].strip()
                lower_intent = intent.lower()

        # Capitalize first letter
        if intent:
            intent = intent[0].upper() + intent[1:]

        return intent[:200]  # Limit length

    async def _learn_from_success(self, context: ConversationContext):
        """Extract lessons from successful interactions"""
        # Extract effective prompt pattern
        await self._extract_prompt_pattern(context)

        # Create lesson from successful approach
        for response in context.responses:
            if isinstance(response, dict) and response.get("success"):
                # Extract key insights from successful response
                content = response.get("content", "")
                if len(content) > 100:  # Meaningful response
                    insight = InteractionInsight(
                        insight_type="solution",
                        content=f"Successful approach for '{context.user_intent}': {content[:500]}",
                        confidence=0.8,
                        domains=context.domains_involved,
                        source_interaction_id=context.conversation_id
                    )
                    self._insights.append(insight)

    async def _learn_from_failure(self, context: ConversationContext):
        """Learn what to avoid from failed interactions"""
        insight = InteractionInsight(
            insight_type="mistake",
            content=f"Failed approach for '{context.user_intent}'. Task type: {context.task_type}. Review and avoid similar patterns.",
            confidence=0.7,
            domains=context.domains_involved,
            source_interaction_id=context.conversation_id
        )
        self._insights.append(insight)

        # Add as anti-pattern lesson
        if context.domains_involved:
            self.teaching_system.add_lesson(
                domain=context.domains_involved[0],
                topic=f"Failed approach: {context.user_intent[:50]}",
                content=f"This approach did not work: {context.prompts_used[0][:300]}",
                anti_patterns=[f"Avoid: {context.user_intent[:100]}"],
                source="auto_learning"
            )

    async def _extract_prompt_pattern(self, context: ConversationContext):
        """Extract and store effective prompt patterns"""
        import hashlib

        for prompt in context.prompts_used:
            # Check if similar prompt already exists
            similar = self._find_similar_prompt(prompt)

            if similar:
                # Update existing prompt stats
                similar.usage_count += 1
                similar.last_used = datetime.now(timezone.utc).isoformat()
                if context.outcome == "success":
                    # Increase success rate
                    total = similar.usage_count
                    successes = int(similar.success_rate * (total - 1)) + 1
                    similar.success_rate = successes / total
            else:
                # Create new prompt pattern
                prompt_id = hashlib.sha256(prompt.encode()).hexdigest()[:12]

                extracted = ExtractedPrompt(
                    prompt_id=prompt_id,
                    original_prompt=prompt,
                    refined_prompt=self._refine_prompt(prompt),
                    task_type=context.task_type,
                    domains=context.domains_involved,
                    success_indicators=self._extract_success_indicators(context)
                )
                self._prompts.append(extracted)

    def _find_similar_prompt(self, prompt: str) -> Optional[ExtractedPrompt]:
        """Find a similar existing prompt"""
        prompt_lower = prompt.lower()
        prompt_words = set(prompt_lower.split())

        for existing in self._prompts:
            existing_words = set(existing.original_prompt.lower().split())
            # Jaccard similarity
            intersection = len(prompt_words & existing_words)
            union = len(prompt_words | existing_words)
            if union > 0 and intersection / union > 0.7:
                return existing

        return None

    def _refine_prompt(self, prompt: str) -> str:
        """Create a refined version of the prompt"""
        # Basic refinement - add structure
        refined = prompt.strip()

        # Ensure it starts with an action verb if it doesn't
        action_verbs = ["create", "build", "implement", "fix", "update", "add", "remove", "refactor"]
        first_word = refined.split()[0].lower() if refined else ""

        if first_word not in action_verbs and not refined.endswith("?"):
            # Try to infer action
            if "bug" in refined.lower() or "error" in refined.lower():
                refined = f"Fix: {refined}"
            elif "new" in refined.lower() or "add" in refined.lower():
                refined = f"Implement: {refined}"
            elif "change" in refined.lower() or "update" in refined.lower():
                refined = f"Update: {refined}"

        return refined

    def _extract_success_indicators(self, context: ConversationContext) -> List[str]:
        """Extract what made this interaction successful"""
        indicators = []

        if context.outcome == "success":
            indicators.append(f"Task type: {context.task_type}")
            indicators.append(f"Domains: {', '.join(context.domains_involved)}")
            if context.models_used:
                indicators.append(f"Models: {', '.join(context.models_used)}")
            if context.duration_seconds > 0:
                indicators.append(f"Completed in {context.duration_seconds:.1f}s")

        return indicators

    async def _analyze_batch(self):
        """Analyze accumulated interactions for patterns"""
        if not self._pending_analysis:
            return

        # Group by task type
        by_task_type: Dict[str, List[ConversationContext]] = {}
        for ctx in self._pending_analysis:
            if ctx.task_type not in by_task_type:
                by_task_type[ctx.task_type] = []
            by_task_type[ctx.task_type].append(ctx)

        # Look for patterns in each task type
        for task_type, contexts in by_task_type.items():
            successful = [c for c in contexts if c.outcome == "success"]
            failed = [c for c in contexts if c.outcome == "failure"]

            if len(successful) >= 2:
                # Extract common patterns from successes
                await self._extract_success_patterns(task_type, successful)

            if len(failed) >= 2:
                # Extract common failure patterns
                await self._extract_failure_patterns(task_type, failed)

        # Clear pending
        self._pending_analysis = []

    async def _extract_success_patterns(
        self,
        task_type: str,
        contexts: List[ConversationContext]
    ):
        """Extract patterns from multiple successful interactions"""
        # Find common domains
        domain_counts: Dict[str, int] = {}
        for ctx in contexts:
            for domain in ctx.domains_involved:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        common_domains = [d for d, count in domain_counts.items() if count >= 2]

        if common_domains:
            # Create a lesson about this pattern
            self.teaching_system.add_lesson(
                domain=common_domains[0],
                topic=f"Successful {task_type} pattern",
                content=f"Multiple successful {task_type} tasks used these domains: {', '.join(common_domains)}. "
                        f"This pattern has worked {len(contexts)} times.",
                best_practices=[f"Use {', '.join(common_domains)} for {task_type} tasks"],
                source="auto_learning"
            )

            logger.info(f"Auto-learned pattern for {task_type}: {common_domains}")

    async def _extract_failure_patterns(
        self,
        task_type: str,
        contexts: List[ConversationContext]
    ):
        """Extract patterns from multiple failed interactions"""
        # Find common aspects of failures
        common_intents = []
        for ctx in contexts:
            common_intents.append(ctx.user_intent[:50])

        if len(common_intents) >= 2:
            self.teaching_system.add_lesson(
                domain="architecture",  # General lesson
                topic=f"Failure pattern: {task_type}",
                content=f"Multiple {task_type} tasks failed. Common intents: {'; '.join(common_intents[:3])}",
                anti_patterns=[f"Review approach for {task_type} tasks"],
                source="auto_learning"
            )

    def get_effective_prompts(
        self,
        task_type: Optional[str] = None,
        domain: Optional[str] = None,
        min_success_rate: float = 0.8
    ) -> List[ExtractedPrompt]:
        """Get effective prompts for a task type or domain"""
        prompts = self._prompts

        if task_type:
            prompts = [p for p in prompts if p.task_type == task_type]

        if domain:
            prompts = [p for p in prompts if domain in p.domains]

        # Filter by success rate
        prompts = [p for p in prompts if p.success_rate >= min_success_rate]

        # Sort by usage and success rate
        prompts.sort(key=lambda p: (p.success_rate, p.usage_count), reverse=True)

        return prompts

    def get_insights(
        self,
        insight_type: Optional[str] = None,
        domain: Optional[str] = None,
        min_confidence: float = 0.7
    ) -> List[InteractionInsight]:
        """Get insights filtered by type and domain"""
        insights = self._insights

        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]

        if domain:
            insights = [i for i in insights if domain in i.domains]

        insights = [i for i in insights if i.confidence >= min_confidence]
        insights.sort(key=lambda i: i.confidence, reverse=True)

        return insights

    def suggest_prompt_improvement(self, prompt: str) -> Optional[str]:
        """Suggest improvements to a prompt based on learned patterns"""
        # Find similar successful prompts
        similar = self._find_similar_prompt(prompt)
        if similar and similar.success_rate >= 0.8:
            return similar.refined_prompt

        # Look for domain-specific improvements
        domains = self._detect_domains(prompt, [])
        for domain in domains:
            effective = self.get_effective_prompts(domain=domain)
            if effective:
                # Return the most successful similar prompt
                return effective[0].refined_prompt

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get auto-learning statistics"""
        successful_prompts = [p for p in self._prompts if p.success_rate >= 0.8]

        # Get health report from data manager
        health = self._data_manager.get_health_report()

        return {
            "total_conversations": len(self._conversations),
            "total_prompts_learned": len(self._prompts),
            "effective_prompts": len(successful_prompts),
            "total_insights": len(self._insights),
            "insights_by_type": {
                itype: len([i for i in self._insights if i.insight_type == itype])
                for itype in ["lesson", "pattern", "mistake", "solution", "prompt"]
            },
            "domains_covered": list(set(
                d for p in self._prompts for d in p.domains
            )),
            "pending_analysis": len(self._pending_analysis),
            # Health metrics
            "health_score": health["health_score"],
            "health_status": health["status"],
            "storage_mb": health["stats"]["total_size_mb"],
            "limits": {
                "max_prompts": self._data_manager.limits.max_prompts,
                "max_insights": self._data_manager.limits.max_insights,
                "max_conversations": self._data_manager.limits.max_conversations,
                "prompts_used": len(self._prompts),
                "insights_used": len(self._insights),
                "conversations_used": len(self._conversations),
            }
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        return self._data_manager.get_health_report()

    def force_cleanup(self) -> Dict[str, int]:
        """Force cleanup regardless of limits"""
        logger.info("Forcing cleanup...")

        before = {
            "prompts": len(self._prompts),
            "insights": len(self._insights),
            "conversations": len(self._conversations)
        }

        # Prune to 80% of limits
        limits = self._data_manager.limits
        self._prune_prompts(int(limits.max_prompts * 0.8))
        self._prune_insights(int(limits.max_insights * 0.8))
        self._prune_conversations(int(limits.max_conversations * 0.8))

        self._save_data()

        # Also run data manager cleanup
        self._data_manager.cleanup(force=True)
        self._data_manager.archive_old_data()
        self._data_manager.compact_storage()

        after = {
            "prompts": len(self._prompts),
            "insights": len(self._insights),
            "conversations": len(self._conversations)
        }

        removed = {
            "prompts": before["prompts"] - after["prompts"],
            "insights": before["insights"] - after["insights"],
            "conversations": before["conversations"] - after["conversations"]
        }

        logger.info(f"Cleanup complete: {sum(removed.values())} items removed")
        return removed

    async def start_background_learning(self):
        """Start background learning task"""
        if self._learning_task is None or self._learning_task.done():
            self._learning_task = asyncio.create_task(self._background_learning_loop())
            logger.info("Started background auto-learning")

    async def _background_learning_loop(self):
        """Background loop for continuous learning"""
        cleanup_counter = 0
        while True:
            try:
                # Analyze any pending interactions
                if self._pending_analysis:
                    await self._analyze_batch()

                # Periodic consolidation of insights into lessons
                await self._consolidate_insights()

                # Save data periodically
                self._save_data()

                # Periodic cleanup (every 10 cycles = ~10 minutes)
                cleanup_counter += 1
                if cleanup_counter >= 10:
                    cleanup_counter = 0
                    health = self.get_health_report()
                    if health["health_score"] < 70:
                        logger.info(f"Health score {health['health_score']:.0f} below threshold, running cleanup")
                        self._data_manager.cleanup()
                    if health["health_score"] < 50:
                        logger.warning(f"Health critical ({health['health_score']:.0f}), forcing aggressive cleanup")
                        self.force_cleanup()

            except Exception as e:
                logger.error(f"Error in background learning: {e}")

            # Run every 60 seconds
            await asyncio.sleep(60)

    async def _consolidate_insights(self):
        """Consolidate insights into formal lessons"""
        # Group insights by domain
        by_domain: Dict[str, List[InteractionInsight]] = {}
        for insight in self._insights:
            for domain in insight.domains:
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(insight)

        # Create lessons from accumulated insights
        for domain, insights in by_domain.items():
            solutions = [i for i in insights if i.insight_type == "solution"]
            mistakes = [i for i in insights if i.insight_type == "mistake"]

            # If we have enough insights, create a consolidated lesson
            if len(solutions) >= 3:
                best_practices = [s.content[:100] for s in solutions[:5]]
                self.teaching_system.add_lesson(
                    domain=domain,
                    topic=f"Auto-learned best practices for {domain}",
                    content=f"Consolidated from {len(solutions)} successful interactions.",
                    best_practices=best_practices,
                    source="auto_learning_consolidated"
                )
                # Clear processed insights
                for s in solutions[:5]:
                    if s in self._insights:
                        self._insights.remove(s)

            if len(mistakes) >= 3:
                anti_patterns = [m.content[:100] for m in mistakes[:5]]
                self.teaching_system.add_lesson(
                    domain=domain,
                    topic=f"Auto-learned anti-patterns for {domain}",
                    content=f"Consolidated from {len(mistakes)} failed interactions.",
                    anti_patterns=anti_patterns,
                    source="auto_learning_consolidated"
                )
                for m in mistakes[:5]:
                    if m in self._insights:
                        self._insights.remove(m)


# Convenience function for quick integration
def create_auto_learner(teaching_system: Optional[TeachingSystem] = None) -> AutoLearner:
    """Create an AutoLearner instance"""
    return AutoLearner(teaching_system=teaching_system)
