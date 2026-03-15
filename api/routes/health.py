from fastapi import APIRouter
from typing import Any
from api.utils import readiness_checks

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/live")
async def health_live() -> dict[str, str]:
    return {"status": "alive"}

@router.get("/ready")
async def health_ready() -> dict[str, Any]:
    return await readiness_checks()
