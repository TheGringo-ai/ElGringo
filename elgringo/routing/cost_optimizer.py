"""
Cost Optimizer - Cost-aware agent selection for AI team
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model cost tiers"""
    BUDGET = 1      # Haiku, GPT-3.5, Gemini Flash - simple tasks
    STANDARD = 2    # Sonnet, GPT-4o-mini, Grok-fast - routine tasks
    PREMIUM = 3     # Opus, GPT-4, Grok-3 - complex tasks


# Model to tier mapping
MODEL_TIER_MAPPING: Dict[str, ModelTier] = {
    # Claude models
    "claude-3-haiku-20240307": ModelTier.BUDGET,
    "claude-3-5-haiku-20241022": ModelTier.BUDGET,
    "claude-sonnet-4-20250514": ModelTier.STANDARD,
    "claude-3-5-sonnet-20241022": ModelTier.STANDARD,
    "claude-opus-4-20250514": ModelTier.PREMIUM,
    # OpenAI models
    "gpt-3.5-turbo": ModelTier.BUDGET,
    "gpt-4o-mini": ModelTier.STANDARD,
    "gpt-4o": ModelTier.PREMIUM,
    "gpt-4-turbo": ModelTier.PREMIUM,
    # Gemini models
    "gemini-1.5-flash": ModelTier.BUDGET,
    "gemini-2.0-flash": ModelTier.BUDGET,
    "gemini-2.5-flash": ModelTier.BUDGET,
    "gemini-1.5-pro": ModelTier.STANDARD,
    "gemini-2.5-pro": ModelTier.PREMIUM,
    # Grok models
    "grok-3-fast": ModelTier.STANDARD,
    "grok-3": ModelTier.PREMIUM,
    # MLX Native (free - always cheapest tier)
    "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit": ModelTier.BUDGET,
    "mlx-community/Qwen2.5-3B-Instruct-4bit": ModelTier.BUDGET,
    "mlx-community/Phi-3.5-mini-instruct-4bit": ModelTier.BUDGET,
    "mlx-community/Mistral-7B-Instruct-v0.3-4bit": ModelTier.BUDGET,
}

# Cost per 1M tokens (input/output) - approximate
MODEL_COSTS: Dict[str, Tuple[float, float]] = {
    # Claude (input, output per 1M tokens)
    "claude-3-haiku-20240307": (0.25, 1.25),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-opus-4-20250514": (15.00, 75.00),
    # OpenAI
    "gpt-3.5-turbo": (0.50, 1.50),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Gemini
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    # Gemini 2.5
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    # Grok
    "grok-3-fast": (5.00, 25.00),
    "grok-3": (3.00, 15.00),
    # Local Ollama (free)
    "llama3.2:3b": (0.0, 0.0),
    "qwen-coder-custom:latest": (0.0, 0.0),
    "qwen2.5-coder:7b": (0.0, 0.0),
    # MLX Native (free - Apple Silicon local)
    "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit": (0.0, 0.0),
    "mlx-community/Qwen2.5-3B-Instruct-4bit": (0.0, 0.0),
    "mlx-community/Phi-3.5-mini-instruct-4bit": (0.0, 0.0),
    "mlx-community/Mistral-7B-Instruct-v0.3-4bit": (0.0, 0.0),
    # Llama Cloud (Groq/Together)
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}

# Complexity to tier mapping
COMPLEXITY_TO_TIER: Dict[str, ModelTier] = {
    "low": ModelTier.BUDGET,
    "medium": ModelTier.STANDARD,
    "high": ModelTier.PREMIUM,
}


@dataclass
class CostEstimate:
    """Estimated cost for a request"""
    model: str
    tier: ModelTier
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float


@dataclass
class BudgetStatus:
    """Current budget status"""
    daily_limit: float
    daily_spent: float
    monthly_limit: float
    monthly_spent: float
    remaining_daily: float
    remaining_monthly: float


class CostOptimizer:
    """
    Cost-aware agent selection optimizer.

    Selects appropriate model tiers based on task complexity
    and tracks spending against budgets.
    """

    def __init__(
        self,
        daily_budget: float = 10.0,
        monthly_budget: float = 100.0,
    ):
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self._daily_spent = 0.0
        self._monthly_spent = 0.0
        self._request_log: List[CostEstimate] = []

    def get_tier_for_complexity(self, complexity: str) -> ModelTier:
        """Get recommended model tier for task complexity"""
        return COMPLEXITY_TO_TIER.get(complexity, ModelTier.STANDARD)

    def get_model_tier(self, model_name: str) -> ModelTier:
        """Get tier for a specific model"""
        return MODEL_TIER_MAPPING.get(model_name, ModelTier.STANDARD)

    def select_optimal_agent(
        self,
        available_agents: List[str],
        agent_models: Dict[str, str],
        complexity: str,
        task_type_scores: Optional[Dict[str, float]] = None,
    ) -> Optional[str]:
        """
        Select the optimal agent based on cost and capability.

        Args:
            available_agents: List of available agent names
            agent_models: Mapping of agent name to model name
            complexity: Task complexity ("low", "medium", "high")
            task_type_scores: Optional scores from task router

        Returns:
            Selected agent name or None
        """
        target_tier = self.get_tier_for_complexity(complexity)

        # For low/medium-complexity tasks, prefer free local models (Qwen/MLX/Ollama)
        if complexity in ("low", "medium"):
            free_agents = [
                a for a in available_agents
                if MODEL_COSTS.get(agent_models.get(a, ""), (1, 1)) == (0.0, 0.0)
            ]
            if free_agents:
                # Among free agents, prefer Qwen/MLX over Ollama (faster on Apple Silicon)
                preferred_local = [a for a in free_agents if any(k in a.lower() for k in ("qwen", "mlx"))]
                if preferred_local:
                    return preferred_local[0]
                return free_agents[0]

        # Score each agent
        scored_agents = []
        for agent_name in available_agents:
            model = agent_models.get(agent_name, "")
            agent_tier = self.get_model_tier(model)

            # Base score from tier match
            tier_diff = abs(agent_tier.value - target_tier.value)
            tier_score = 1.0 - (tier_diff * 0.3)

            # Add task type score if available
            task_score = task_type_scores.get(agent_name, 0.5) if task_type_scores else 0.5

            # Free models get a strong cost bonus to prefer local-first
            model_cost = MODEL_COSTS.get(model, (1.0, 5.0))
            cost_bonus = 0.25 if model_cost == (0.0, 0.0) else 0.0

            # Combined score (weighted)
            combined_score = (tier_score * 0.4) + (task_score * 0.6) + cost_bonus

            scored_agents.append((agent_name, combined_score, agent_tier))

        if not scored_agents:
            return None

        # Sort by score descending
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # Check budget constraints
        for agent_name, score, tier in scored_agents:
            model = agent_models.get(agent_name, "")
            estimated_cost = self.estimate_cost(model, 1000, 2000)

            if self._can_afford(estimated_cost.estimated_cost):
                return agent_name

        # Fallback to cheapest option if over budget
        cheapest = min(
            scored_agents,
            key=lambda x: MODEL_COSTS.get(agent_models.get(x[0], ""), (999, 999))[0]
        )
        return cheapest[0]

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        """Estimate cost for a request"""
        costs = MODEL_COSTS.get(model, (1.0, 5.0))
        input_cost = (input_tokens / 1_000_000) * costs[0]
        output_cost = (output_tokens / 1_000_000) * costs[1]

        return CostEstimate(
            model=model,
            tier=self.get_model_tier(model),
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost=input_cost + output_cost,
        )

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        """Record actual token usage and update spending"""
        estimate = self.estimate_cost(model, input_tokens, output_tokens)

        self._daily_spent += estimate.estimated_cost
        self._monthly_spent += estimate.estimated_cost
        self._request_log.append(estimate)

        return estimate

    def _can_afford(self, cost: float) -> bool:
        """Check if we can afford the estimated cost"""
        return (
            self._daily_spent + cost <= self.daily_budget and
            self._monthly_spent + cost <= self.monthly_budget
        )

    def get_budget_status(self) -> BudgetStatus:
        """Get current budget status"""
        return BudgetStatus(
            daily_limit=self.daily_budget,
            daily_spent=self._daily_spent,
            monthly_limit=self.monthly_budget,
            monthly_spent=self._monthly_spent,
            remaining_daily=max(0, self.daily_budget - self._daily_spent),
            remaining_monthly=max(0, self.monthly_budget - self._monthly_spent),
        )

    def health_details(self):
        """Returns current spending as a percentage of daily and monthly budgets."""
        daily_pct = (self._daily_spent / self.daily_budget * 100) if self.daily_budget > 0 else 0.0
        monthly_pct = (self._monthly_spent / self.monthly_budget * 100) if self.monthly_budget > 0 else 0.0
        
        return {
            "daily_pct": daily_pct,
            "monthly_pct": monthly_pct,
        }

    def reset_daily(self):
        """Reset daily spending counter"""
        self._daily_spent = 0.0

    def reset_monthly(self):
        """Reset monthly spending counter"""
        self._monthly_spent = 0.0
        self._daily_spent = 0.0

    def get_cost_report(self) -> Dict:
        """Get cost report summary"""
        if not self._request_log:
            return {"total_requests": 0, "total_cost": 0.0}

        total_cost = sum(r.estimated_cost for r in self._request_log)
        by_tier = {}
        for r in self._request_log:
            tier_name = r.tier.name
            if tier_name not in by_tier:
                by_tier[tier_name] = {"count": 0, "cost": 0.0}
            by_tier[tier_name]["count"] += 1
            by_tier[tier_name]["cost"] += r.estimated_cost

        return {
            "total_requests": len(self._request_log),
            "total_cost": total_cost,
            "by_tier": by_tier,
            "budget_status": {
                "daily_remaining": self.daily_budget - self._daily_spent,
                "monthly_remaining": self.monthly_budget - self._monthly_spent,
            },
        }
