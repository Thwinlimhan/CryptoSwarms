from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class OptimizationCandidate:
    params: dict[str, float]
    score: float


@dataclass(slots=True)
class NightlyOptimizer:
    score_fn: Callable[[dict[str, float]], float]
    base_params: dict[str, float]
    slippage: float = 0.004

    def run(self, generations: int = 10, step: float = 0.05) -> list[OptimizationCandidate]:
        current = dict(self.base_params)
        best: list[OptimizationCandidate] = []

        for _ in range(generations):
            neighborhood = self._mutate(current, step)
            scored = [OptimizationCandidate(params=p, score=self.score_fn(self._with_slippage(p))) for p in neighborhood]
            scored.sort(key=lambda x: x.score, reverse=True)
            current = dict(scored[0].params)
            best.extend(scored[:2])

        best.sort(key=lambda x: x.score, reverse=True)
        dedup: list[OptimizationCandidate] = []
        seen: set[tuple[tuple[str, float], ...]] = set()
        for cand in best:
            key = tuple(sorted((k, float(v)) for k, v in cand.params.items()))
            if key in seen:
                continue
            seen.add(key)
            dedup.append(cand)
        return dedup[:5]

    def _mutate(self, params: dict[str, float], step: float) -> list[dict[str, float]]:
        variants = [dict(params)]
        for k, v in params.items():
            variants.append({**params, k: float(v) * (1.0 + step)})
            variants.append({**params, k: float(v) * (1.0 - step)})
        return variants

    def _with_slippage(self, params: dict[str, float]) -> dict[str, float]:
        return {**params, "slippage": self.slippage}
