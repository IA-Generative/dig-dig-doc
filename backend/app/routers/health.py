from fastapi import APIRouter, Response, status

from app.connectors import redis_connector
from app.schemas.health import HealthReport

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness check",
    response_model=HealthReport,
)
def health_ready(response: Response) -> HealthReport:
    dependencies = [redis_connector.get_health()]
    api_status = "healthy"
    for dependency in dependencies:
        if dependency.status == "unhealthy":
            api_status = "unhealthy"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthReport(name="dig-dig-doc-backend", status=api_status, dependencies=dependencies)
