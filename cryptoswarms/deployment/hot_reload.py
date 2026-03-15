"""Hot Reload Manager — hot-swap strategies without system downtime.

Enables loading/reloading trading strategies at runtime by:
1. Gracefully draining existing positions
2. Loading the new strategy version
3. Resuming operations
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger("swarm.deployment.hot_reload")


@dataclass
class StrategyInfo:
    """Information about a loaded strategy."""
    strategy_id: str
    module_path: str
    version: str
    loaded_at: datetime
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReloadResult:
    """Result of a hot reload operation."""
    strategy_id: str
    success: bool
    old_version: str | None
    new_version: str | None
    positions_drained: int
    duration_ms: float
    message: str


class HotReloadManager:
    """Manages hot reloading of trading strategies.

    Provides zero-downtime strategy updates by:
    1. Draining open positions for the strategy
    2. Unregistering the old strategy
    3. Loading the new version
    4. Registering the new strategy
    """

    def __init__(
        self,
        drain_timeout_seconds: float = 60.0,
        position_manager: Any = None,
    ) -> None:
        self.strategy_registry: dict[str, Any] = {}
        self._strategy_info: dict[str, StrategyInfo] = {}
        self._drain_timeout = drain_timeout_seconds
        self._position_manager = position_manager
        self._reload_history: list[ReloadResult] = []
        self._lock = asyncio.Lock()

    def register_strategy(
        self,
        strategy_id: str,
        strategy: Any,
        module_path: str = "",
        version: str = "1.0.0",
    ) -> None:
        """Register a new strategy."""
        self.strategy_registry[strategy_id] = strategy
        self._strategy_info[strategy_id] = StrategyInfo(
            strategy_id=strategy_id,
            module_path=module_path,
            version=version,
            loaded_at=datetime.now(timezone.utc),
        )
        logger.info("Strategy registered: %s v%s", strategy_id, version)

    async def reload_strategy(
        self,
        strategy_id: str,
        new_module_path: str | None = None,
        new_version: str | None = None,
    ) -> ReloadResult:
        """Hot reload a strategy.

        Args:
            strategy_id: ID of the strategy to reload.
            new_module_path: Module path for the new version (or reload existing).
            new_version: Version string for the new strategy.

        Returns:
            ReloadResult with the outcome.
        """
        start_time = time.monotonic()

        async with self._lock:
            old_info = self._strategy_info.get(strategy_id)
            old_version = old_info.version if old_info else None
            module_path = new_module_path or (old_info.module_path if old_info else "")

            try:
                # Step 1: Drain positions
                positions_drained = await self._drain_strategy_positions(strategy_id)

                # Step 2: Load new version
                new_strategy = self._load_strategy_from_module(module_path)
                if new_strategy is None:
                    raise RuntimeError(f"Failed to load strategy from {module_path}")

                # Step 3: Register new version
                version = new_version or (
                    f"{old_version}_reload" if old_version else "1.0.0"
                )
                self.strategy_registry[strategy_id] = new_strategy
                self._strategy_info[strategy_id] = StrategyInfo(
                    strategy_id=strategy_id,
                    module_path=module_path,
                    version=version,
                    loaded_at=datetime.now(timezone.utc),
                )

                duration = (time.monotonic() - start_time) * 1000
                result = ReloadResult(
                    strategy_id=strategy_id,
                    success=True,
                    old_version=old_version,
                    new_version=version,
                    positions_drained=positions_drained,
                    duration_ms=round(duration, 2),
                    message=f"Strategy {strategy_id} reloaded: {old_version} → {version}",
                )
                logger.info(result.message)

            except Exception as exc:
                duration = (time.monotonic() - start_time) * 1000
                result = ReloadResult(
                    strategy_id=strategy_id,
                    success=False,
                    old_version=old_version,
                    new_version=None,
                    positions_drained=0,
                    duration_ms=round(duration, 2),
                    message=f"Failed to reload {strategy_id}: {exc}",
                )
                logger.error(result.message)

            self._reload_history.append(result)
            return result

    async def _drain_strategy_positions(self, strategy_id: str) -> int:
        """Gracefully drain all positions for a strategy.

        Returns the number of positions drained.
        """
        if self._position_manager is None:
            return 0

        drained = 0
        try:
            positions = getattr(self._position_manager, "open_positions", {})
            strategy_positions = [
                p for p in positions.values()
                if getattr(p, "strategy_id", None) == strategy_id
            ]

            for pos in strategy_positions:
                try:
                    # Request close at market price
                    await asyncio.wait_for(
                        self._close_position(pos),
                        timeout=self._drain_timeout,
                    )
                    drained += 1
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timeout draining position %s",
                        getattr(pos, "position_id", "unknown"),
                    )
                except Exception as exc:
                    logger.error("Failed to drain position: %s", exc)

        except Exception as exc:
            logger.error("Error during position drain: %s", exc)

        return drained

    async def _close_position(self, position: Any) -> None:
        """Close a single position (placeholder)."""
        # In production, this would submit a market order
        logger.info(
            "Draining position %s", getattr(position, "position_id", "unknown"),
        )

    def _load_strategy_from_module(self, module_path: str) -> Any:
        """Load a strategy class from a Python module."""
        if not module_path:
            return None

        try:
            module = importlib.import_module(module_path)
            importlib.reload(module)

            # Look for a class with 'Strategy' in the name
            for attr_name in dir(module):
                if "strategy" in attr_name.lower():
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type):
                        return attr()

            # Fallback: return the module itself
            return module
        except Exception as exc:
            logger.error("Failed to load module '%s': %s", module_path, exc)
            return None

    def get_loaded_strategies(self) -> dict[str, dict[str, Any]]:
        """Get info about all loaded strategies."""
        return {
            sid: {
                "version": info.version,
                "loaded_at": info.loaded_at.isoformat(),
                "is_active": info.is_active,
                "module_path": info.module_path,
            }
            for sid, info in self._strategy_info.items()
        }

    @property
    def reload_history(self) -> list[ReloadResult]:
        return list(self._reload_history)
