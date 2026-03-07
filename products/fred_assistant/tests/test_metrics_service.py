"""Tests for metrics_service — CEO Lens metrics."""

from products.fred_assistant.services import metrics_service


def test_get_current_metrics():
    metrics = metrics_service.get_current_metrics()
    assert "mrr" in metrics
    assert "leads_contacted" in metrics
    assert "sprint_completion_pct" in metrics
    assert "overdue_tasks" in metrics
    assert "focus_minutes_today" in metrics


def test_save_snapshot():
    snapshot = metrics_service.save_snapshot()
    assert snapshot["date"]
    assert "mrr" in snapshot


def test_get_snapshots_empty():
    snapshots = metrics_service.get_snapshots(days=30)
    assert isinstance(snapshots, list)


def test_log_metric_mrr():
    result = metrics_service.log_metric("mrr", 5000)
    assert result["mrr"] == 5000


def test_log_metric_revenue():
    result = metrics_service.log_metric("revenue", 12000)
    assert result["revenue"] == 12000


def test_log_metric_custom():
    result = metrics_service.log_metric("churn_rate", 3.5)
    assert result["custom_metrics"]["churn_rate"] == 3.5


def test_save_and_retrieve_snapshot():
    metrics_service.log_metric("mrr", 8000)
    metrics_service.save_snapshot()
    snapshots = metrics_service.get_snapshots(days=1)
    assert len(snapshots) >= 1
