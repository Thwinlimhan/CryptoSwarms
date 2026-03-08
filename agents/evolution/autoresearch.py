from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from agents.evolution.deap_nightly import NightlyOptimizer, OptimizationCandidate


@dataclass(frozen=True)
class AutoResearchPolicy:
    max_runtime_minutes: int = 20
    max_experiments: int = 3
    generations_per_experiment: int = 6
    mutation_step: float = 0.05
    min_score_improvement: float = 0.02
    keep_top_k: int = 1

    @property
    def max_runtime(self) -> timedelta:
        return timedelta(minutes=self.max_runtime_minutes)


@dataclass(frozen=True)
class ExperimentDecision:
    experiment_id: int
    best_score: float
    incumbent_before: float
    score_improvement: float
    kept: bool
    reason: str
    candidate: OptimizationCandidate | None


@dataclass(frozen=True)
class AutoResearchReport:
    started_at: datetime
    finished_at: datetime
    experiments_run: int
    final_incumbent_score: float
    kept: list[ExperimentDecision]
    discarded: list[ExperimentDecision]


def load_program_policy(path: str | Path) -> AutoResearchPolicy:
    parsed: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        raw = stripped[2:]
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        parsed[key.strip()] = value.strip()

    return AutoResearchPolicy(
        max_runtime_minutes=int(parsed.get("max_runtime_minutes", 20)),
        max_experiments=int(parsed.get("max_experiments", 3)),
        generations_per_experiment=int(parsed.get("generations_per_experiment", 6)),
        mutation_step=float(parsed.get("mutation_step", 0.05)),
        min_score_improvement=float(parsed.get("min_score_improvement", 0.02)),
        keep_top_k=int(parsed.get("keep_top_k", 1)),
    )


@dataclass(slots=True)
class AutoResearchRunner:
    score_fn: Callable[[dict[str, float]], float]
    base_params: dict[str, float]
    policy: AutoResearchPolicy
    slippage: float = 0.004

    def run(
        self,
        incumbent_score: float,
        now_provider: Callable[[], datetime] | None = None,
    ) -> AutoResearchReport:
        now_fn = now_provider or (lambda: datetime.now(timezone.utc))
        started_at = _as_utc(now_fn())
        deadline = started_at + self.policy.max_runtime
        kept: list[ExperimentDecision] = []
        discarded: list[ExperimentDecision] = []
        incumbent = float(incumbent_score)
        experiments = 0

        for experiment_id in range(1, self.policy.max_experiments + 1):
            if _as_utc(now_fn()) >= deadline:
                break
            optimizer = NightlyOptimizer(
                score_fn=self.score_fn,
                base_params=self.base_params,
                slippage=self.slippage,
            )
            candidates = optimizer.run(
                generations=self.policy.generations_per_experiment,
                step=self.policy.mutation_step,
            )
            experiments += 1
            if not candidates:
                discarded.append(
                    ExperimentDecision(
                        experiment_id=experiment_id,
                        best_score=incumbent,
                        incumbent_before=incumbent,
                        score_improvement=0.0,
                        kept=False,
                        reason="no_candidates",
                        candidate=None,
                    )
                )
                continue

            top = sorted(candidates, key=lambda c: c.score, reverse=True)[0]
            delta = top.score - incumbent
            keep = delta >= self.policy.min_score_improvement
            decision = ExperimentDecision(
                experiment_id=experiment_id,
                best_score=top.score,
                incumbent_before=incumbent,
                score_improvement=round(delta, 6),
                kept=keep,
                reason="promoted" if keep else "below_threshold",
                candidate=top if keep else None,
            )
            if keep:
                kept.append(decision)
                incumbent = top.score
            else:
                discarded.append(decision)

        kept = sorted(kept, key=lambda d: d.best_score, reverse=True)[: self.policy.keep_top_k]
        finished_at = _as_utc(now_fn())
        return AutoResearchReport(
            started_at=started_at,
            finished_at=finished_at,
            experiments_run=experiments,
            final_incumbent_score=round(incumbent, 6),
            kept=kept,
            discarded=discarded,
        )


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
