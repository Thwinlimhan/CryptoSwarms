from __future__ import annotations

import importlib
import inspect
import math
import py_compile
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol

from .models import GateResult, GateStatus, StrategyCandidate


class BacktestRunner(Protocol):
    def __call__(self, strategy_module: str, class_name: str, params: dict[str, float], market_data: Any) -> list[float]: ...


class JesseWalkForwardRunner(Protocol):
    def __call__(self, strategy_module: str, class_name: str, params: dict[str, float], market_data: Any, folds: int) -> list[list[float]]: ...


class ActiveReturnsProvider(Protocol):
    def __call__(self) -> dict[str, list[float]]: ...


@dataclass(slots=True)
class ValidationThresholds:
    min_sharpe: float = 0.5
    sensitivity_ratio: float = 0.8
    slippage_degradation_limit: float = 0.35
    min_wfe: float = 0.5
    max_correlation: float = 0.8
    max_missing_ratio: float = 0.02
    max_zero_return_ratio: float = 0.15
    max_abs_outlier_return: float = 0.3


def _safe_stdev(values: Iterable[float]) -> float:
    sequence = list(values)
    if len(sequence) < 2:
        return 0.0
    return statistics.pstdev(sequence)


def sharpe_ratio(returns: list[float]) -> float:
    if not returns:
        return 0.0
    std = _safe_stdev(returns)
    if std == 0:
        return 0.0
    return statistics.fmean(returns) / std * math.sqrt(252)


def _correlation(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a_slice = a[:n]
    b_slice = b[:n]
    a_mu = statistics.fmean(a_slice)
    b_mu = statistics.fmean(b_slice)
    cov = sum((x - a_mu) * (y - b_mu) for x, y in zip(a_slice, b_slice)) / n
    a_std = _safe_stdev(a_slice)
    b_std = _safe_stdev(b_slice)
    if a_std == 0 or b_std == 0:
        return 0.0
    return cov / (a_std * b_std)


def _extract_close_series(market_data: Any) -> list[float]:
    if isinstance(market_data, dict):
        if "close" in market_data and isinstance(market_data["close"], list):
            return [float(v) if v is not None else float("nan") for v in market_data["close"]]
        if "candles" in market_data and isinstance(market_data["candles"], list):
            closes: list[float] = []
            for row in market_data["candles"]:
                if isinstance(row, dict):
                    value = row.get("close")
                elif isinstance(row, (list, tuple)) and len(row) >= 5:
                    value = row[4]
                else:
                    value = None
                closes.append(float(value) if value is not None else float("nan"))
            return closes
    return []


def gate_0_data_quality(candidate: StrategyCandidate, thresholds: ValidationThresholds) -> GateResult:
    closes = _extract_close_series(candidate.market_data)
    if not closes:
        return GateResult(
            gate_number=0,
            gate_name="data_quality_precheck",
            status=GateStatus.FAIL,
            score=0.0,
            details={"reason": "missing_close_series"},
        )

    total = len(closes)
    missing = sum(1 for value in closes if not math.isfinite(value) or value <= 0)
    valid = [value for value in closes if math.isfinite(value) and value > 0]

    returns: list[float] = []
    for index in range(1, len(valid)):
        previous = valid[index - 1]
        current = valid[index]
        if previous <= 0:
            continue
        returns.append((current / previous) - 1)

    zero_return_ratio = 0.0
    if returns:
        zero_count = sum(1 for value in returns if abs(value) < 1e-12)
        zero_return_ratio = zero_count / len(returns)

    max_abs_return = max((abs(value) for value in returns), default=0.0)
    missing_ratio = missing / total if total else 1.0

    passed = (
        missing_ratio <= thresholds.max_missing_ratio
        and zero_return_ratio <= thresholds.max_zero_return_ratio
        and max_abs_return <= thresholds.max_abs_outlier_return
    )

    return GateResult(
        gate_number=0,
        gate_name="data_quality_precheck",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        score=1.0 - min(1.0, missing_ratio + zero_return_ratio),
        details={
            "total_points": total,
            "missing_ratio": missing_ratio,
            "zero_return_ratio": zero_return_ratio,
            "max_abs_return": max_abs_return,
            "thresholds": {
                "max_missing_ratio": thresholds.max_missing_ratio,
                "max_zero_return_ratio": thresholds.max_zero_return_ratio,
                "max_abs_outlier_return": thresholds.max_abs_outlier_return,
            },
        },
    )


def gate_1_syntax_check(candidate: StrategyCandidate) -> GateResult:
    try:
        py_compile.compile(candidate.module_path, doraise=True)
        module = importlib.import_module(candidate.module_path.replace("/", ".").removesuffix(".py"))
        strategy_class = getattr(module, candidate.class_name)
        is_class = inspect.isclass(strategy_class)
        status = GateStatus.PASS if is_class else GateStatus.FAIL
        return GateResult(
            gate_number=1,
            gate_name="syntax_import_compile",
            status=status,
            score=1.0 if is_class else 0.0,
            details={"class_found": is_class, "module": candidate.module_path},
        )
    except Exception as exc:  # pragma: no cover - defensive path
        return GateResult(
            gate_number=1,
            gate_name="syntax_import_compile",
            status=GateStatus.ERROR,
            score=0.0,
            details={"error": str(exc), "module": candidate.module_path},
        )


def gate_2_sensitivity(
    candidate: StrategyCandidate,
    backtest_runner: BacktestRunner,
    thresholds: ValidationThresholds,
) -> GateResult:
    base_returns = backtest_runner(candidate.module_path, candidate.class_name, candidate.params, candidate.market_data)
    base_sharpe = sharpe_ratio(base_returns)

    sharpe_samples: list[float] = [base_sharpe]
    for key, value in candidate.params.items():
        if not isinstance(value, (float, int)):
            continue
        for delta in (-0.1, 0.1):
            mutated = dict(candidate.params)
            mutated[key] = float(value) * (1 + delta)
            sample_returns = backtest_runner(candidate.module_path, candidate.class_name, mutated, candidate.market_data)
            sharpe_samples.append(sharpe_ratio(sample_returns))

    worst_sample = min(sharpe_samples) if sharpe_samples else 0.0
    robustness_ratio = (worst_sample / base_sharpe) if base_sharpe > 0 else 0.0
    passed = base_sharpe >= thresholds.min_sharpe and robustness_ratio >= thresholds.sensitivity_ratio

    return GateResult(
        gate_number=2,
        gate_name="sensitivity_robustness",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        score=robustness_ratio,
        details={
            "base_sharpe": base_sharpe,
            "worst_perturbed_sharpe": worst_sample,
            "robustness_ratio": robustness_ratio,
        },
    )


def gate_3_vectorbt_screen(
    candidate: StrategyCandidate,
    fast_screen_runner: BacktestRunner,
    thresholds: ValidationThresholds,
) -> GateResult:
    optimistic = fast_screen_runner(candidate.module_path, candidate.class_name, candidate.params, {**candidate.market_data, "slippage_bps": 1})
    conservative = fast_screen_runner(candidate.module_path, candidate.class_name, candidate.params, {**candidate.market_data, "slippage_bps": 10})

    optimistic_sharpe = sharpe_ratio(optimistic)
    conservative_sharpe = sharpe_ratio(conservative)
    if optimistic_sharpe <= 0:
        degradation = 1.0
    else:
        degradation = max(0.0, (optimistic_sharpe - conservative_sharpe) / optimistic_sharpe)

    passed = conservative_sharpe >= thresholds.min_sharpe and degradation <= thresholds.slippage_degradation_limit
    return GateResult(
        gate_number=3,
        gate_name="vectorbt_fast_screen",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        score=conservative_sharpe,
        details={
            "optimistic_sharpe": optimistic_sharpe,
            "conservative_sharpe": conservative_sharpe,
            "degradation": degradation,
        },
    )


def gate_4_walk_forward(
    candidate: StrategyCandidate,
    jesse_runner: JesseWalkForwardRunner,
    thresholds: ValidationThresholds,
    folds: int = 4,
) -> GateResult:
    fold_returns = jesse_runner(candidate.module_path, candidate.class_name, candidate.params, candidate.market_data, folds)
    fold_sharpes = [sharpe_ratio(series) for series in fold_returns]
    in_sample = max(fold_sharpes) if fold_sharpes else 0.0
    out_of_sample = statistics.fmean(fold_sharpes[1:]) if len(fold_sharpes) > 1 else 0.0
    wfe = (out_of_sample / in_sample) if in_sample > 0 else 0.0
    passed = wfe >= thresholds.min_wfe

    return GateResult(
        gate_number=4,
        gate_name="jesse_walk_forward",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        score=wfe,
        details={"fold_sharpes": fold_sharpes, "wfe": wfe, "folds": folds},
    )


def gate_5_regime_evaluation(
    candidate: StrategyCandidate,
    backtest_runner: BacktestRunner,
    thresholds: ValidationThresholds,
    regime_tagger: Callable[[Any], dict[str, Any]],
) -> GateResult:
    tagged = regime_tagger(candidate.market_data)
    regimes: dict[str, Any] = tagged.get("regimes", {})
    regime_scores: dict[str, float] = {}
    for regime_name, regime_data in regimes.items():
        returns = backtest_runner(candidate.module_path, candidate.class_name, candidate.params, regime_data)
        regime_scores[regime_name] = sharpe_ratio(returns)

    weak_regimes = [name for name, score in regime_scores.items() if score < thresholds.min_sharpe]
    passed = not weak_regimes and bool(regime_scores)

    return GateResult(
        gate_number=5,
        gate_name="regime_segmented_eval",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        score=min(regime_scores.values()) if regime_scores else 0.0,
        details={"regime_scores": regime_scores, "weak_regimes": weak_regimes, "regime_tags": list(regimes.keys())},
    )


def gate_6_correlation_check(
    candidate: StrategyCandidate,
    backtest_runner: BacktestRunner,
    active_returns_provider: ActiveReturnsProvider,
    thresholds: ValidationThresholds,
) -> GateResult:
    candidate_returns = backtest_runner(candidate.module_path, candidate.class_name, candidate.params, candidate.market_data)
    active = active_returns_provider()
    corr_by_strategy = {name: _correlation(candidate_returns, values) for name, values in active.items()}
    max_corr = max((abs(v) for v in corr_by_strategy.values()), default=0.0)
    passed = max_corr <= thresholds.max_correlation

    return GateResult(
        gate_number=6,
        gate_name="active_correlation",
        status=GateStatus.PASS if passed else GateStatus.FAIL,
        score=1 - max_corr,
        details={"max_abs_correlation": max_corr, "correlations": corr_by_strategy},
    )


# ── Gate 7: Swarm Regime Gate ──────────────────────────────────────────────

from agents.backtest.mirofish_simulator import MiroFishRegimeSimulator


def gate_7_swarm_regime(
    candidate: StrategyCandidate,
    simulator: MiroFishRegimeSimulator,
    min_consensus: float = 0.55,
) -> GateResult:
    """Gate 7 — MiroFish emergent swarm consensus check.

    Runs thousands of personality-driven simulated traders against the
    candidate's market_data. Fails candidates the swarm collectively fades.

    Args:
        candidate: strategy candidate with market_data dict
        simulator: configured MiroFishRegimeSimulator instance
        min_consensus: minimum agent agreement fraction (default 0.55)
    """
    try:
        verdict = simulator.simulate(
            candidate.market_data if isinstance(candidate.market_data, dict) else {}
        )
    except Exception as exc:
        return GateResult(
            gate_number=7,
            gate_name="swarm_regime_consensus",
            status=GateStatus.ERROR,
            score=0.0,
            details={"error": str(exc)},
        )

    tradeable = simulator.is_tradeable(verdict)
    return GateResult(
        gate_number=7,
        gate_name="swarm_regime_consensus",
        status=GateStatus.PASS if tradeable else GateStatus.FAIL,
        score=verdict.consensus_score,
        details={
            "regime": verdict.regime,
            "consensus_score": verdict.consensus_score,
            "whale_pressure": verdict.whale_pressure,
            "momentum_pct": verdict.momentum_agents_pct,
            "mean_revert_pct": verdict.mean_revert_agents_pct,
            "noise_pct": verdict.noise_agents_pct,
            "min_consensus_threshold": min_consensus,
        },
    )


# ── Gate 8: Recipe Alignment Gate ──────────────────────────────────────────

from agents.scanner.recipe_classifier import classify_recipe
from agents.scanner.microstructure_primitives import compute_primitives
from agents.research.lob_connector import HyperliquidLOBConnector


def gate_8_recipe_alignment(
    candidate: StrategyCandidate,
    lob_connector: HyperliquidLOBConnector,
    min_recipe_score: float = 0.70,
    preferred_recipes: list[str] | None = None,
) -> GateResult:
    """Gate 8 — Microstructure recipe alignment check.

    Classifies current market microstructure into one of 10 behavioral recipes
    and validates that the strategy aligns with favorable regimes.

    Args:
        candidate: strategy candidate with market_data dict
        lob_connector: configured HyperliquidLOBConnector for LOB data
        min_recipe_score: minimum recipe confidence score (0.0-1.0)
        preferred_recipes: list of recipe names to prefer, defaults to favorable ones
    """
    if preferred_recipes is None:
        preferred_recipes = ["Trend Align", "Absorption", "Vacuum", "Shock"]
    
    symbol = candidate.params.get("symbol", "BTC")
    
    try:
        # Fetch current LOB snapshot and recent trades
        lob = lob_connector.fetch_lob(symbol)
        trades = lob_connector.fetch_recent_trades(symbol)
        
        # Compute microstructure primitives
        primitives = compute_primitives(
            lob=lob,
            trades=trades,
            ofi_history=[],  # Would be populated from historical data in production
        )
        
        # Classify into recipe
        result = classify_recipe(primitives)
        
    except Exception as exc:
        return GateResult(
            gate_number=8,
            gate_name="recipe_alignment",
            status=GateStatus.ERROR,
            score=0.0,
            details={"error": str(exc)},
        )

    # Check if recipe score meets threshold and is in preferred list
    score_ok = result.score >= min_recipe_score
    recipe_ok = result.recipe in preferred_recipes
    
    return GateResult(
        gate_number=8,
        gate_name="recipe_alignment",
        status=GateStatus.PASS if (score_ok and recipe_ok) else GateStatus.FAIL,
        score=result.score,
        details={
            "detected_recipe": result.recipe,
            "recipe_score": result.score,
            "active_signals": result.active_signals,
            "ofi": result.primitives.ofi,
            "liquidity_gravity": result.primitives.liquidity_gravity,
            "book_fragility": result.primitives.book_fragility,
            "tape_pressure": result.primitives.net_tape_pressure,
            "ofi_persistence": result.primitives.ofi_persistence,
            "preferred_recipes": preferred_recipes,
            "score_threshold": min_recipe_score,
        },
    )


# ── Gate 9: Hyperspace Consensus Gate ──────────────────────────────────────

from agents.orchestration.hyperspace_mesh import HyperspaceMeshClient


def gate_9_hyperspace_consensus(
    candidate: StrategyCandidate,
    mesh_client: HyperspaceMeshClient,
    min_consensus: float = 0.60,
    min_participating_nodes: int = 3,
) -> GateResult:
    """Gate 9 — Hyperspace P2P mesh consensus check.

    Fetches consensus from the decentralized Hyperspace network about
    this strategy's validation. Requires agreement from multiple peer nodes.

    Args:
        candidate: strategy candidate
        mesh_client: configured HyperspaceMeshClient
        min_consensus: minimum consensus fraction (0.0-1.0)
        min_participating_nodes: minimum number of nodes that must participate
    """
    try:
        consensus = mesh_client.fetch_mesh_consensus(candidate.strategy_id)
    except Exception as exc:
        return GateResult(
            gate_number=9,
            gate_name="hyperspace_consensus",
            status=GateStatus.ERROR,
            score=0.0,
            details={"error": str(exc)},
        )

    # Check consensus thresholds
    consensus_ok = consensus.consensus_score >= min_consensus
    participation_ok = consensus.participating_nodes >= min_participating_nodes
    
    return GateResult(
        gate_number=9,
        gate_name="hyperspace_consensus",
        status=GateStatus.PASS if (consensus_ok and participation_ok) else GateStatus.FAIL,
        score=consensus.rank_weighted_score,
        details={
            "consensus_score": consensus.consensus_score,
            "rank_weighted_score": consensus.rank_weighted_score,
            "participating_nodes": consensus.participating_nodes,
            "dissenting_nodes": consensus.dissenting_nodes,
            "min_consensus_threshold": min_consensus,
            "min_participating_nodes": min_participating_nodes,
            "timestamp": consensus.timestamp.isoformat(),
        },
    )


# ── Gate 10: Funding Arbitrage Validation ──────────────────────────────────

from agents.research.funding_rate_connector import HyperliquidFundingConnector


def gate_10_funding_arbitrage(
    candidate: StrategyCandidate,
    funding_connector: HyperliquidFundingConnector,
    min_yield_score: float = 0.30,
    min_confidence: float = 0.60,
) -> GateResult:
    """Gate 10 — Funding arbitrage opportunity validation.

    Validates that funding rate arbitrage opportunities exist with sufficient
    yield potential and prediction confidence.

    Args:
        candidate: strategy candidate (should be funding arbitrage type)
        funding_connector: configured HyperliquidFundingConnector
        min_yield_score: minimum yield opportunity score (0.0-1.0)
        min_confidence: minimum prediction confidence (0.0-1.0)
    """
    symbol = candidate.params.get("symbol", "BTC")
    
    try:
        prediction = funding_connector.fetch_funding_prediction(symbol)
    except Exception as exc:
        return GateResult(
            gate_number=10,
            gate_name="funding_arbitrage",
            status=GateStatus.ERROR,
            score=0.0,
            details={"error": str(exc)},
        )

    # Check yield and confidence thresholds
    yield_ok = prediction.yield_opportunity_score >= min_yield_score
    confidence_ok = prediction.confidence >= min_confidence
    
    # Additional check: funding rate should be significant enough to trade
    funding_significant = abs(prediction.current_funding_rate) >= 5.0  # 5 bps minimum
    
    all_checks_pass = yield_ok and confidence_ok and funding_significant
    
    return GateResult(
        gate_number=10,
        gate_name="funding_arbitrage",
        status=GateStatus.PASS if all_checks_pass else GateStatus.FAIL,
        score=prediction.yield_opportunity_score * prediction.confidence,
        details={
            "current_funding_rate": prediction.current_funding_rate,
            "predicted_funding_rate": prediction.predicted_funding_rate,
            "predicted_flip_in_minutes": prediction.predicted_flip_in_minutes,
            "confidence": prediction.confidence,
            "yield_opportunity_score": prediction.yield_opportunity_score,
            "min_yield_threshold": min_yield_score,
            "min_confidence_threshold": min_confidence,
            "funding_significant": funding_significant,
            "venue": prediction.venue,
        },
    )


