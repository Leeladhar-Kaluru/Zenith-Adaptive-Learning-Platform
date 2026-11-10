from fastapi import APIRouter, Response

from app.core.ai_provider import ai_provider
from app.core.config import settings
from app.core.database import check_db_health

router = APIRouter()


@router.get("/health")
def liveness():
    """Liveness probe: the process is up. Never touches external services."""
    return {"status": "ok", "product": settings.APP_NAME}


@router.get("/health/ready")
async def readiness(response: Response):
    """Readiness probe: database reachable; AI provider status reported.

    The AI provider is optional for readiness: ZENITH degrades gracefully when
    it is unavailable. Never exposes keys or secrets.
    """
    db_ok = check_db_health()
    ai_status = await ai_provider.check_health()
    if not db_ok:
        response.status_code = 503
    return {
        "status": "ready" if db_ok else "unavailable",
        "components": {
            "database": {"connected": db_ok},
            "ai_provider": {
                "provider": ai_status.get("provider"),
                "chat_ready": ai_status.get("chat_ready", False),
            },
        },
    }
