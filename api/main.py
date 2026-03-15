"""FastAPI application entrypoint."""

import asyncio
import logging
import math
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.middleware.auth import APIKeyMiddleware
from api.middleware.logging import RequestLoggingMiddleware

from api.settings import settings
from api.dependencies import agent_runner, load_decision_dag, save_decision_dag
from api.routes import router as api_router

logger = logging.getLogger("api.main")

from api.utils import readiness_checks

@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_decision_dag()
    try:
        from api.dependencies import dashboard_repo
        await dashboard_repo.connect()
        await agent_runner.start()
    except Exception as e:
        logger.error(f"Failed to start AgentRunner: {e}")
    yield
    try:
        from api.dependencies import dashboard_repo
        await dashboard_repo.close()
        await agent_runner.stop()
        save_decision_dag()
    except Exception as e:
        logger.error(f"Failed to stop AgentRunner cleanly: {e}")

from api.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)

def _uvicorn_run_kwargs() -> dict[str, Any]:
    ssl_certfile = settings.ssl_certfile.strip()
    ssl_keyfile = settings.ssl_keyfile.strip()
    if bool(ssl_certfile) != bool(ssl_keyfile):
        raise ValueError("SSL_CERTFILE and SSL_KEYFILE must both be set to enable HTTPS.")

    kwargs: dict[str, Any] = {
        "host": settings.api_host,
        "port": settings.api_port,
        "reload": False,
    }
    if ssl_certfile:
        kwargs["ssl_certfile"] = ssl_certfile
        kwargs["ssl_keyfile"] = ssl_keyfile
    return kwargs

def run() -> None:
    uvicorn.run("api.main:app", **_uvicorn_run_kwargs())

if __name__ == "__main__":
    run()
