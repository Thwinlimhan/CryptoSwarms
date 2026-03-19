# agents/scanner/recipe_classifier.py
"""
10-state microstructure recipe classifier.
Thresholds are placeholders — calibrate empirically on your
Hyperliquid historical LOB data before using in gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from agents.scanner.microstructure_primitives import MicrostructurePrimitives


# ── THRESHOLDS — tune these on your data ───────────────────────────────────
# Do NOT copy the 0.70-0.82 range from screenshots — those are output scores,
# not input thresholds. Calibrate on 30+ days of Hyperliquid LOB history.
OFI_STRONG     = 0.30   # strong directional imbalance
OFI_FLIP       = 0.05   # near-zero = potential flip
GRAVITY_STRONG = 0.001  # significant depth center-of-mass pull
FRAGILITY_HIGH = 0.60   # thin book
FRAGILITY_MOD  = 0.30   # moderate fragility
TAPE_STRONG    = 0.20   # 70%+ buy or sell domination
PERSIST_HIGH   = 0.75   # OFI same-signed 75%+ of recent candles
PERSIST_LOW    = 0.35   # OFI direction unstable


@dataclass(frozen=True)
class RecipeResult:
    recipe: str
    score: float          # 0.0–1.0 — calibrate meaning before using as gate threshold
    primitives: MicrostructurePrimitives
    active_signals: list[str]  # which primitives triggered this recipe


def classify_recipe(p: MicrostructurePrimitives) -> RecipeResult:
    """
    Rule-based recipe classification from microstructure primitives.

    IMPORTANT: Recipe score is a weighted sum of matching conditions.
    It does NOT mean "probability of success". Validate empirically before
    using as a gate_8 threshold. Start with conservative thresholds (>0.70).
    """
    scores: dict[str, tuple[float, list[str]]] = {}

    # ── 1. TREND ALIGN ─────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if abs(p.ofi) > OFI_STRONG: score += 0.35; signals.append("strong_ofi")
    if p.ofi_persistence > PERSIST_HIGH: score += 0.25; signals.append("ofi_persistence")
    if abs(p.liquidity_gravity) > GRAVITY_STRONG and \
       (p.liquidity_gravity > 0) == (p.ofi > 0): score += 0.25; signals.append("gravity_aligned")
    if p.book_fragility < FRAGILITY_MOD: score += 0.15; signals.append("book_supported")
    scores["Trend Align"] = (round(score, 3), signals)

    # ── 2. EXHAUSTION ──────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if p.ofi_persistence > PERSIST_HIGH: score += 0.30; signals.append("extended_run")
    if abs(p.ofi) < OFI_FLIP: score += 0.35; signals.append("ofi_stalling")
    if p.book_fragility > FRAGILITY_HIGH: score += 0.20; signals.append("thin_book_at_extreme")
    if abs(p.net_tape_pressure) < 0.10: score += 0.15; signals.append("tape_drying_up")
    scores["Exhaustion"] = (round(score, 3), signals)

    # ── 3. ABSORPTION ─────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if abs(p.net_tape_pressure) > TAPE_STRONG: score += 0.35; signals.append("strong_tape")
    if abs(p.ofi) < OFI_FLIP: score += 0.35; signals.append("price_not_moving")
    if abs(p.liquidity_gravity) > GRAVITY_STRONG and \
       (p.liquidity_gravity > 0) != (p.net_tape_pressure > 0): score += 0.30; signals.append("gravity_absorbing")
    scores["Absorption"] = (round(score, 3), signals)

    # ── 4. VACUUM ─────────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if p.book_fragility > 0.80: score += 0.50; signals.append("extreme_fragility")
    if abs(p.ofi) > OFI_STRONG: score += 0.30; signals.append("ofi_spike_into_vacuum")
    if abs(p.liquidity_gravity) < 0.0001: score += 0.20; signals.append("gravity_absent")
    scores["Vacuum"] = (round(score, 3), signals)

    # ── 5. TRAP ───────────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if p.ofi_persistence < PERSIST_LOW: score += 0.30; signals.append("ofi_unstable")
    if p.book_fragility > FRAGILITY_HIGH: score += 0.30; signals.append("thin_at_breakout")
    if abs(p.liquidity_gravity) > GRAVITY_STRONG and \
       (p.liquidity_gravity > 0) != (p.ofi > 0): score += 0.40; signals.append("gravity_opposing_ofi")
    scores["Trap"] = (round(score, 3), signals)

    # ── 6. STRUCTURAL DIVERGENCE ───────────────────────────────────────────
    signals = []
    score = 0.0
    if abs(p.ofi) > OFI_STRONG: score += 0.30; signals.append("price_flow_strong")
    if abs(p.liquidity_gravity) > GRAVITY_STRONG and \
       (p.liquidity_gravity > 0) != (p.ofi > 0): score += 0.40; signals.append("gravity_vs_flow")
    if p.ofi_persistence > 0.60 and \
       (p.net_tape_pressure > 0) != (p.ofi > 0): score += 0.30; signals.append("tape_vs_book")
    scores["Structural Divergence"] = (round(score, 3), signals)

    # ── 7. SHOCK ──────────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if p.book_fragility > FRAGILITY_HIGH: score += 0.35; signals.append("depth_collapsed")
    if abs(p.ofi) > 0.60: score += 0.40; signals.append("extreme_ofi")
    if abs(p.net_tape_pressure) > 0.35: score += 0.25; signals.append("tape_spike")
    scores["Shock"] = (round(score, 3), signals)

    # ── 8. DRIFT ──────────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if abs(p.ofi) < OFI_FLIP: score += 0.30; signals.append("weak_flow")
    if p.ofi_persistence < 0.50: score += 0.30; signals.append("inconsistent_direction")
    if abs(p.liquidity_gravity) > GRAVITY_STRONG and \
       (p.liquidity_gravity > 0) != (p.ofi > 0): score += 0.40; signals.append("grinding_against_gravity")
    scores["Drift"] = (round(score, 3), signals)

    # ── 9. COMPRESSION ────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if p.book_fragility > FRAGILITY_MOD and \
       p.book_fragility < FRAGILITY_HIGH: score += 0.35; signals.append("moderate_tension")
    if 0.15 < abs(p.ofi) < OFI_STRONG: score += 0.35; signals.append("building_imbalance")
    if abs(p.liquidity_gravity) < 0.0005: score += 0.30; signals.append("gravity_balanced")
    scores["Compression"] = (round(score, 3), signals)

    # ── 10. CONFLICT ──────────────────────────────────────────────────────
    signals = []
    score = 0.0
    if (p.liquidity_gravity > 0) != (p.ofi > 0): score += 0.35; signals.append("book_vs_flow")
    if (p.net_tape_pressure > 0) != (p.ofi > 0): score += 0.35; signals.append("tape_vs_book")
    if p.ofi_persistence < 0.50: score += 0.30; signals.append("no_dominant_direction")
    scores["Conflict"] = (round(score, 3), signals)

    # ── Select best recipe ─────────────────────────────────────────────────
    best_recipe = max(scores.items(), key=lambda x: x[1][0])
    recipe_name = best_recipe[0]
    recipe_score, active_signals = best_recipe[1]

    return RecipeResult(
        recipe=recipe_name,
        score=recipe_score,
        primitives=p,
        active_signals=active_signals,
    )
