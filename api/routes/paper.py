from fastapi import APIRouter, HTTPException
from typing import Any
import logging

from api.settings import settings
from cryptoswarms.adapters.hyperliquid_adapter import HyperliquidAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/paper", tags=["paper-trading"])


@router.get("/status")
async def get_paper_status() -> dict[str, Any]:
    """Fetch status from HyPaper backend. Returns offline with message if backend unreachable."""
    adapter = HyperliquidAdapter()
    try:
        meta = await adapter.get_meta()
        if not meta:
            return {"status": "offline", "message": "HyPaper backend not reachable"}
        state = await adapter.get_user_state()
        history = await adapter.info("userFills", user=adapter.wallet)
        return {
            "status": "online",
            "wallet": adapter.wallet,
            "mode": settings.hyperliquid_mode,
            "account_value": (state or {}).get("marginSummary", {}).get("accountValue", "0.0"),
            "positions": (state or {}).get("assetPositions", []),
            "recent_fills": (history or [])[:10],
        }
    except Exception as e:
        logger.debug("Paper status failed: %s", e, exc_info=True)
        return {
            "status": "offline",
            "message": "HyPaper backend not reachable",
            "error": str(e),
        }
    finally:
        await adapter.close()


@router.post("/reset")
async def reset_paper_account() -> dict[str, Any]:
    """Reset the paper trading account (HyPaper only). Requires HyPaper backend with /hypaper endpoint."""
    if settings.hyperliquid_mode != "paper":
        raise HTTPException(status_code=400, detail="Reset only allowed in paper mode")
    adapter = HyperliquidAdapter()
    try:
        resp = await adapter._client.post(
            "/hypaper", json={"type": "reset", "user": adapter.wallet}, timeout=15.0
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Paper reset failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"HyPaper reset failed. Is the backend running and does it expose POST /hypaper? {str(e)}",
        )
    finally:
        await adapter.close()
