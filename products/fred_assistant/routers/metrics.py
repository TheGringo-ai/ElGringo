"""CEO Lens metrics router — live metrics, snapshots, custom metric logging."""

from fastapi import APIRouter, Query

from products.fred_assistant.models import MetricLogRequest
from products.fred_assistant.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/current")
def get_current():
    return metrics_service.get_current_metrics()


@router.get("/history")
def get_history(days: int = Query(30, ge=1, le=365)):
    return metrics_service.get_snapshots(days)


@router.post("/snapshot")
def save_snapshot():
    return metrics_service.save_snapshot()


@router.post("/log")
def log_metric(data: MetricLogRequest):
    return metrics_service.log_metric(data.name, data.value)
