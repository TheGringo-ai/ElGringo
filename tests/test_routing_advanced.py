"""
Tests for advanced routing: PerformanceTracker, DecisionLogger, CostTracker
"""

import pytest
from ai_dev_team.routing.performance_tracker import (
    PerformanceTracker,
    ModelPerformance,
    get_performance_tracker,
)
from ai_dev_team.routing.decision import (
    RoutingDecision,
    AgentScore,
    DecisionFactor,
    DecisionLogger,
    get_decision_logger,
)
from ai_dev_team.routing.cost_tracker import CostTracker, get_cost_tracker


class TestModelPerformance:
    """Test ModelPerformance dataclass"""

    def test_default_success_rate(self):
        mp = ModelPerformance(model_name="test")
        assert mp.success_rate == 0.5  # Default when no tasks

    def test_success_rate_with_data(self):
        mp = ModelPerformance(model_name="test", total_tasks=10, successful_tasks=8)
        assert mp.success_rate == 0.8

    def test_default_avg_response_time(self):
        mp = ModelPerformance(model_name="test")
        assert mp.avg_response_time == 5.0  # Default

    def test_avg_response_time_with_data(self):
        mp = ModelPerformance(model_name="test", total_tasks=4, total_response_time=12.0)
        assert mp.avg_response_time == 3.0

    def test_recent_trend_insufficient_data(self):
        mp = ModelPerformance(model_name="test", recent_outcomes=[True, False])
        assert mp.recent_trend == 0.0  # Not enough data

    def test_recent_trend_improving(self):
        # First half: all failures, second half: all successes
        outcomes = [False] * 10 + [True] * 10
        mp = ModelPerformance(model_name="test", recent_outcomes=outcomes)
        assert mp.recent_trend > 0  # Improving

    def test_recent_trend_declining(self):
        outcomes = [True] * 10 + [False] * 10
        mp = ModelPerformance(model_name="test", recent_outcomes=outcomes)
        assert mp.recent_trend < 0  # Declining

    def test_get_task_type_score_no_data(self):
        mp = ModelPerformance(model_name="test")
        assert mp.get_task_type_score("coding") == 0.5

    def test_get_task_type_score_with_data(self):
        mp = ModelPerformance(
            model_name="test",
            task_type_stats={"coding": {"success": 8, "total": 10}}
        )
        assert mp.get_task_type_score("coding") == 0.8

    def test_get_domain_score_no_data(self):
        mp = ModelPerformance(model_name="test")
        assert mp.get_domain_score("web") == 0.5


class TestPerformanceTracker:
    """Test PerformanceTracker"""

    @pytest.fixture
    def tracker(self, tmp_path):
        return PerformanceTracker(storage_dir=str(tmp_path / "perf"))

    def test_init(self, tracker):
        assert tracker is not None

    def test_record_outcome(self, tracker):
        tracker.record_outcome(
            model_name="gpt-4o", task_type="coding",
            success=True, confidence=0.9, response_time=2.5, domain="web",
        )
        stats = tracker.get_statistics()
        assert stats["total_outcomes"] >= 1

    def test_record_multiple_outcomes(self, tracker):
        for i in range(5):
            tracker.record_outcome(
                model_name="gpt-4o", task_type="coding",
                success=i % 2 == 0, confidence=0.8, response_time=2.0, domain="web",
            )

        stats = tracker.get_statistics()
        assert stats["total_outcomes"] == 5

    def test_get_best_model(self, tracker):
        for i in range(5):
            tracker.record_outcome(
                model_name="model-a", task_type="coding",
                success=True, confidence=0.9, response_time=1.0,
            )
        for i in range(5):
            tracker.record_outcome(
                model_name="model-b", task_type="coding",
                success=False, confidence=0.3, response_time=5.0,
            )

        model, score = tracker.get_best_model(
            task_type="coding",
            available_models=["model-a", "model-b"],
        )
        assert model == "model-a"

    def test_get_model_ranking(self, tracker):
        tracker.record_outcome(
            model_name="fast", task_type="coding",
            success=True, confidence=0.9, response_time=1.0,
        )
        rankings = tracker.get_model_ranking(["fast", "unknown"], "coding")
        assert len(rankings) > 0

    def test_get_performance_tracker_singleton(self):
        t1 = get_performance_tracker()
        t2 = get_performance_tracker()
        assert t1 is t2


class TestRoutingDecision:
    """Test RoutingDecision"""

    def test_basic_explain(self):
        decision = RoutingDecision(
            selected_agent="chatgpt-coder",
            task_type="coding",
            complexity="medium",
            confidence=0.85,
            primary_reason="Best coding performance",
        )
        explanation = decision.explain()
        assert "chatgpt-coder" in explanation
        assert "coding" in explanation

    def test_explain_with_fallback(self):
        decision = RoutingDecision(
            selected_agent="grok-coder",
            task_type="coding",
            complexity="high",
            confidence=0.7,
            primary_reason="Fallback",
            is_fallback=True,
            original_choice="chatgpt-coder",
        )
        explanation = decision.explain()
        assert "Fallback" in explanation
        assert "chatgpt-coder" in explanation

    def test_explain_verbose(self):
        decision = RoutingDecision(
            selected_agent="chatgpt-coder",
            task_type="coding",
            complexity="medium",
            confidence=0.9,
            primary_reason="Best match",
            candidates=[
                AgentScore(agent_name="chatgpt-coder", total_score=0.9),
                AgentScore(agent_name="grok-coder", total_score=0.7),
            ],
        )
        explanation = decision.explain(verbose=True)
        assert "Candidate" in explanation


class TestAgentScore:
    def test_basic(self):
        score = AgentScore(agent_name="test", total_score=0.85)
        assert score.eligible
        assert score.rejection_reason is None

    def test_rejected(self):
        score = AgentScore(
            agent_name="test", total_score=0.0,
            eligible=False, rejection_reason="Over budget"
        )
        assert not score.eligible


class TestDecisionFactor:
    def test_factors_exist(self):
        assert DecisionFactor.TASK_TYPE_MATCH.value == "task_type_match"
        assert DecisionFactor.PERFORMANCE_HISTORY.value == "performance_history"
        assert DecisionFactor.COST_CONSTRAINT.value == "cost_constraint"
        assert DecisionFactor.FALLBACK.value == "fallback"


class TestDecisionLogger:
    def test_get_decision_logger(self):
        dl = get_decision_logger()
        assert isinstance(dl, DecisionLogger)


class TestCostTracker:
    def test_get_cost_tracker(self):
        ct = get_cost_tracker()
        assert isinstance(ct, CostTracker)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
