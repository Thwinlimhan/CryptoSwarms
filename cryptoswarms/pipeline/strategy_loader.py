"""Dynamic strategy loading from filesystem."""

from __future__ import annotations

import importlib.util
import os
import logging
from pathlib import Path
from typing import Any, Type

from schemas.strategy import StrategyConfig
from cryptoswarms.common.strategy import BaseStrategy

logger = logging.getLogger("swarm.pipeline.loader")


class StrategyLoader:
    """Loads strategy definitions and configurations."""
    
    def __init__(self, strategies_dir: str = "strategies") -> None:
        self.strategies_dir = Path(strategies_dir)
        self.loaded_strategies: dict[str, BaseStrategy] = {}

    def load_all(self) -> dict[str, BaseStrategy]:
        """Discovery and load all strategies in the directory."""
        if not self.strategies_dir.exists():
            logger.warning("Strategy directory %s does not exist", self.strategies_dir)
            return {}

        for file in self.strategies_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue
            
            try:
                strategy_cls = self._load_strategy_class(file)
                if strategy_cls:
                    # Look for a companion CONFIG in the same module
                    module = importlib.import_module(f"strategies.{file.stem}")
                    config = getattr(module, "CONFIG", None)
                    if config:
                        strat_instance = strategy_cls(config)
                        self.loaded_strategies[config.id] = strat_instance
                        logger.info("Loaded strategy: %s (%s)", config.name, config.id)
            except Exception as e:
                logger.error("Failed to load strategy from %s: %s", file, e)
        
        return self.loaded_strategies

    def _load_strategy_class(self, path: Path) -> Type[BaseStrategy] | None:
        """Find the subclass of BaseStrategy in the given file."""
        spec = importlib.util.spec_from_file_location(path.stem, str(path))
        if not spec or not spec.loader:
            return None
            
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Exec error in {path}: {e}")
            return None
        
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, BaseStrategy) and 
                obj is not BaseStrategy):
                return obj
            
        return None
