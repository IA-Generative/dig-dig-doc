from fastapi import APIRouter, Response, status

from app.connectors import db_connector, redis_connector, s3_connector
from app.schemas.health import Health, HealthReport, HealthStatus

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness check", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get(
    "/health/ready",
    summary="Readiness check",
    response_model=HealthReport,
)
async def health_ready(response: Response) -> HealthReport:
    dependencies: list[Health] = [
        await db_connector.get_health(),
        redis_connector.get_health(),
        s3_connector.get_health(),
    ]
    api_status = "healthy"
    for dependency in dependencies:
        if dependency.status == "unhealthy":
            api_status = "unhealthy"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthReport(name="dig-dig-doc-backend", status=api_status, dependencies=dependencies)
