import os
from fastapi import APIRouter
from typing import Any
from urllib.parse import urlparse
from cryptoswarms.tracing import langsmith_enabled
import asyncio

router = APIRouter(tags=["tracing"])

@router.get("/api/tracing/status")
async def tracing_status() -> dict[str, Any]:
    deepflow_enabled = os.environ.get("DEEPFLOW_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    return {
        "langsmith_enabled": langsmith_enabled(dict(os.environ)),
        "deepflow_service_expected": deepflow_enabled,
    }

@router.get("/api/paper-mcp/status")
async def paper_mcp_status() -> dict[str, Any]:
    enabled = os.environ.get("PAPER_MCP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    server_url = os.environ.get("PAPER_MCP_SERVER_URL", "").strip()

    host = ""
    port = 0
    reachable = False
    if server_url:
        parsed = urlparse(server_url)
        host = parsed.hostname or ""
        port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        if host and port > 0:
            try:
                connection = asyncio.open_connection(host=host, port=port)
                reader, writer = await asyncio.wait_for(connection, timeout=1.5)
                writer.close()
                await writer.wait_closed()
                reachable = True
            except Exception:
                import logging
                logging.getLogger(__name__).debug("paper_mcp_status connection failed", exc_info=True)
                reachable = False

    mode = "paper-mcp" if enabled and server_url else "paper-local"
    return {
        "enabled": enabled,
        "mode": mode,
        "server_url": server_url,
        "host": host,
        "port": port,
        "reachable": reachable,
    }
