import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import agent_runner
from cryptoswarms.backtest_engine import BacktestEngine


class RunBacktestBody(BaseModel):
    strategy_id: str
    symbols: list[str] | None = None
    days: int = 14

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backtest", tags=["backtest"])

REPORT_DIR = Path("data")
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DEFAULT_DAYS = 14


async def _fetch_historical_candles(symbol: str, days: int = 14, interval: str = "15m") -> list[list[Any]]:
    """Fetch OHLCV candles from Binance spot API."""
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    all_candles: list[list[Any]] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        current_start = start_ts
        while current_start < end_ts:
            resp = await client.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_ts,
                    "limit": 1000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            all_candles.extend(data)
            current_start = data[-1][0] + 1
            if len(data) < 1000:
                break
    return all_candles


def _summary_to_response(summary: dict[str, Any], strategy_id: str) -> dict[str, Any]:
    """Convert engine.pm.summary() to API response shape (numeric where frontend expects)."""
    total_pnl = summary.get("total_pnl")
    if isinstance(total_pnl, str) and total_pnl.startswith("$"):
        try:
            total_pnl = float(total_pnl.replace("$", "").replace(",", "").strip())
        except ValueError:
            total_pnl = 0.0
    win_rate = summary.get("win_rate")
    if isinstance(win_rate, str) and "%" in win_rate:
        try:
            win_rate = float(win_rate.replace("%", "").strip()) / 100.0
        except ValueError:
            win_rate = 0.0
    trades = summary.get("total_trades", 0)
    if isinstance(trades, str):
        try:
            trades = int(trades)
        except ValueError:
            trades = 0
    return {
        "_synthetic": False,
        "strategy_id": strategy_id,
        "total_pnl": total_pnl if isinstance(total_pnl, (int, float)) else 0.0,
        "sharpe": None,
        "win_rate": win_rate if isinstance(win_rate, (int, float)) else 0.0,
        "trades": trades,
        "max_drawdown": None,
        "equity_curve": [],
        "message": summary.get("message"),
    }


def _load_strategies_from_loader() -> list[dict[str, Any]]:
    """Build strategy list from StrategyLoader so UI has options before any signals."""
    strategies = []
    try:
        loader = agent_runner.strategy_loader
        loaded = loader.load_all() if loader else {}
        for strat_id, strategy in loaded.items():
            strategies.append({
                "id": strat_id,
                "name": getattr(strategy.config, "name", strat_id),
                "group": "LOADED",
                "last_run": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass
    return strategies


@router.get("/strategies")
async def backtest_strategies() -> list[dict[str, Any]]:
    """Return strategies from loader and from recent scanner signals."""
    seen_ids: set[str] = set()
    strategies = []

    for s in _load_strategies_from_loader():
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            strategies.append(s)

    for i, sig in enumerate(agent_runner.last_signals[:8]):
        sig_type = sig.get("signal_type", "UNKNOWN")
        symbol = sig.get("symbol", "UNKNOWN")
        strat_name = f"{symbol}_{sig_type}_V1"
        strat_id = f"stub-{i+1:03d}"
        if strat_id not in seen_ids:
            seen_ids.add(strat_id)
            strategies.append({
                "id": strat_id,
                "name": strat_name,
                "group": "SCANNER_DETECTIONS",
                "last_run": datetime.now(timezone.utc).isoformat(),
                "is_stub": True,
            })
    return strategies


def _parse_latest_backtest_report() -> dict[str, Any] | None:
    """If a recent backtest report exists in data/, parse it and return metrics."""
    if not REPORT_DIR.exists():
        return None
    reports = sorted(REPORT_DIR.glob("backtest_report_multi_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return None
    path = reports[0]
    data: dict[str, Any] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("Multi-") and not line.startswith("Symbols") and not line.startswith("Period"):
                key, _, value = line.partition(":")
                key = key.strip().replace(" ", "_").lower()
                data[key] = value.strip()
    except Exception:
        return None
    return data if data else None


@router.get("/results/{strategy_id}")
async def backtest_results(strategy_id: str) -> dict[str, Any]:
    """Return backtest results from latest report file if present, else stub.

    Run scripts/backtest_runner.py to generate data/backtest_report_multi_*.txt; the API
    will use the most recent report. Otherwise returns a stub so the frontend can show a message.
    """
    report = _parse_latest_backtest_report()
    if report:
        total_pnl = report.get("total_pnl")
        if isinstance(total_pnl, str) and total_pnl.startswith("$"):
            try:
                total_pnl = float(total_pnl.replace("$", "").replace(",", "").strip())
            except ValueError:
                total_pnl = None
        win_rate = report.get("win_rate")
        if isinstance(win_rate, str) and "%" in str(win_rate):
            try:
                win_rate = float(str(win_rate).replace("%", "").strip()) / 100.0
            except ValueError:
                win_rate = None
        trades = report.get("total_trades") or report.get("trades")
        if isinstance(trades, str):
            try:
                trades = int(trades)
            except ValueError:
                trades = None
        return {
            "_synthetic": False,
            "strategy_id": strategy_id,
            "total_pnl": total_pnl,
            "sharpe": report.get("sharpe"),
            "win_rate": win_rate,
            "trades": trades,
            "max_drawdown": report.get("max_drawdown"),
            "equity_curve": [],
            "message": report.get("message"),
        }
    return {
        "_synthetic": True,
        "_warning": (
            "No backtest report found. Click RUN_BACKTEST above to run a live backtest, "
            "or run: python scripts/backtest_runner.py"
        ),
        "strategy_id": strategy_id,
        "total_pnl": None,
        "sharpe": None,
        "win_rate": None,
        "trades": None,
        "max_drawdown": None,
        "equity_curve": [],
    }


@router.post("/run")
async def run_backtest(body: RunBacktestBody) -> dict[str, Any]:
    """Run a backtest for the given strategy: fetch candles from Binance, run engine, return results.

    Body: strategy_id (required), symbols (optional), days (optional, default 14).
    """
    strategy_id = body.strategy_id
    symbols = body.symbols
    days = body.days
    loader = agent_runner.strategy_loader
    strategies = loader.load_all() if loader else {}
    if strategy_id.startswith("stub-"):
        return {
            "_synthetic": True,
            "_warning": f"Cannot run direct backtest on scanner detection '{strategy_id}'. Please select a formal strategy from the LOADED group.",
            "strategy_id": strategy_id,
            "total_pnl": 0,
            "sharpe": 0,
            "win_rate": 0,
            "trades": 0,
            "max_drawdown": 0,
            "equity_curve": [],
        }

    if strategy_id not in strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy '{strategy_id}' not found. Ensure it is defined in strategies/ and loaded by the StrategyLoader. Available: {list(strategies.keys())}",
        )
    strategy = strategies[strategy_id]
    syms = symbols or DEFAULT_SYMBOLS
    days = max(7, min(90, days))

    engine = BacktestEngine(base_bankroll=10000.0)
    for symbol in syms:
        try:
            candles = await _fetch_historical_candles(symbol, days=days)
            if len(candles) < 300:
                logger.warning("Not enough candles for %s (%d), skipping", symbol, len(candles))
                continue
            await engine.run(strategy, candles, symbol)
        except Exception as e:
            logger.warning("Backtest failed for %s: %s", symbol, e)

    summary = engine.pm.summary()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"backtest_report_multi_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Multi-Asset Backtest Report: {strategy.config.name}\n")
        f.write(f"Symbols: {', '.join(syms)}\n")
        f.write(f"Period: {days} days\n\n")
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")
    logger.info("Backtest report saved to %s", report_path)
    return _summary_to_response(summary, strategy_id)
