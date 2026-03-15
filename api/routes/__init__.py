from fastapi import APIRouter
from api.routes import (
    health, costs, dashboard, decision, 
    orchestration, tracing, backtest, agents, websocket,
    failure_ledger, paper, research, portfolio
)

router = APIRouter()
router.include_router(health.router)
router.include_router(costs.router)
router.include_router(dashboard.router)
router.include_router(decision.router)
router.include_router(orchestration.router)
router.include_router(tracing.router)
router.include_router(backtest.router)
router.include_router(agents.router)
router.include_router(websocket.router)
router.include_router(failure_ledger.router)
router.include_router(paper.router)
router.include_router(research.router)
router.include_router(portfolio.router)
