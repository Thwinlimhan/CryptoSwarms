"""Tests for microstructure primitives and recipe classification."""

import pytest
from agents.scanner.microstructure_primitives import (
    MicrostructurePrimitives,
    compute_ofi,
    compute_multilevel_ofi,
    compute_liquidity_gravity,
    compute_book_fragility,
    compute_net_tape_pressure,
    compute_primitives,
)
from agents.scanner.recipe_classifier import classify_recipe, RecipeResult
from agents.research.lob_connector import LOBSnapshot


@pytest.fixture
def sample_lob():
    """Sample LOB snapshot for testing."""
    return LOBSnapshot(
        symbol="BTC",
        bids=[(50000.0, 1.5), (49999.0, 2.0), (49998.0, 1.0)],  # price, size
        asks=[(50001.0, 1.0), (50002.0, 1.5), (50003.0, 2.0)],
        timestamp_ms=1640995200000,
    )


@pytest.fixture
def sample_trades():
    """Sample trade tape for testing."""
    return [
        {"sz": "0.5", "side": "B"},  # buy
        {"sz": "1.0", "side": "A"},  # sell
        {"sz": "0.3", "side": "B"},  # buy
        {"sz": "0.8", "side": "A"},  # sell
        {"sz": "1.2", "side": "B"},  # buy
    ]


def test_compute_ofi_basic(sample_lob):
    """Test basic OFI computation."""
    ofi = compute_ofi(sample_lob)
    
    # bid_size = 1.5, ask_size = 1.0
    # ofi = (1.5 - 1.0) / (1.5 + 1.0) = 0.5 / 2.5 = 0.2
    assert abs(ofi - 0.2) < 1e-6


def test_compute_ofi_empty_book():
    """Test OFI with empty order book."""
    empty_lob = LOBSnapshot("BTC", [], [], 0)
    ofi = compute_ofi(empty_lob)
    assert ofi == 0.0


def test_compute_multilevel_ofi(sample_lob):
    """Test multi-level OFI computation."""
    ofi = compute_multilevel_ofi(sample_lob, n_levels=3)
    
    # Should weight closer levels higher
    assert -1.0 <= ofi <= 1.0
    assert isinstance(ofi, float)


def test_compute_liquidity_gravity(sample_lob):
    """Test liquidity gravity computation."""
    gravity = compute_liquidity_gravity(sample_lob, n_levels=3)
    
    # Should return normalized deviation from mid-price
    assert isinstance(gravity, float)
    # Gravity should be reasonable relative to mid-price
    mid = (sample_lob.bids[0][0] + sample_lob.asks[0][0]) / 2.0
    assert abs(gravity) < mid  # Sanity check


def test_compute_book_fragility(sample_lob):
    """Test book fragility computation."""
    fragility = compute_book_fragility(sample_lob)
    
    # Should be between 0 and 1
    assert 0.0 <= fragility <= 1.0
    assert isinstance(fragility, float)


def test_compute_net_tape_pressure(sample_trades):
    """Test net tape pressure computation."""
    pressure = compute_net_tape_pressure(sample_trades)
    
    # Buy volume: 0.5 + 0.3 + 1.2 = 2.0
    # Total volume: 0.5 + 1.0 + 0.3 + 0.8 + 1.2 = 3.8
    # Buy fraction: 2.0 / 3.8 ≈ 0.526
    # Net pressure: 0.526 - 0.5 = 0.026
    expected = (2.0 / 3.8) - 0.5
    assert abs(pressure - expected) < 1e-3


def test_compute_primitives_integration(sample_lob, sample_trades):
    """Test full primitives computation."""
    ofi_history = [0.1, -0.2, 0.3, 0.1, 0.2]  # Some history for persistence
    
    primitives = compute_primitives(
        lob=sample_lob,
        trades=sample_trades,
        ofi_history=ofi_history,
        n_levels=3,
        persistence_window=5,
    )
    
    assert isinstance(primitives, MicrostructurePrimitives)
    assert -1.0 <= primitives.ofi <= 1.0
    assert isinstance(primitives.liquidity_gravity, float)
    assert 0.0 <= primitives.book_fragility <= 1.0
    assert -0.5 <= primitives.net_tape_pressure <= 0.5
    assert 0.0 <= primitives.ofi_persistence <= 1.0
    assert primitives.mid_price > 0


def test_classify_recipe_trend_align():
    """Test recipe classification for Trend Align pattern."""
    # Create primitives that should trigger Trend Align
    primitives = MicrostructurePrimitives(
        ofi=0.35,           # Strong positive OFI
        liquidity_gravity=0.002,  # Positive gravity aligned with OFI
        book_fragility=0.25,      # Low fragility (supported)
        net_tape_pressure=0.15,   # Moderate buy pressure
        ofi_persistence=0.80,     # High persistence
        mid_price=50000.0,
    )
    
    result = classify_recipe(primitives)
    
    assert isinstance(result, RecipeResult)
    assert result.recipe == "Trend Align"
    assert result.score > 0.5  # Should have decent score
    assert "strong_ofi" in result.active_signals
    assert "ofi_persistence" in result.active_signals


def test_classify_recipe_exhaustion():
    """Test recipe classification for Exhaustion pattern."""
    # Create primitives that should trigger Exhaustion
    primitives = MicrostructurePrimitives(
        ofi=0.02,           # Near-zero OFI (stalling)
        liquidity_gravity=0.0001,
        book_fragility=0.70,      # High fragility (thin book)
        net_tape_pressure=0.05,   # Low tape pressure (drying up)
        ofi_persistence=0.85,     # High persistence (extended run)
        mid_price=50000.0,
    )
    
    result = classify_recipe(primitives)
    
    assert isinstance(result, RecipeResult)
    assert result.recipe == "Exhaustion"
    assert "extended_run" in result.active_signals
    assert "ofi_stalling" in result.active_signals


def test_classify_recipe_vacuum():
    """Test recipe classification for Vacuum pattern."""
    # Create primitives that should trigger Vacuum
    primitives = MicrostructurePrimitives(
        ofi=0.45,           # Strong OFI spike
        liquidity_gravity=0.00005,  # Near-zero gravity
        book_fragility=0.85,      # Extreme fragility
        net_tape_pressure=0.20,
        ofi_persistence=0.60,
        mid_price=50000.0,
    )
    
    result = classify_recipe(primitives)
    
    assert isinstance(result, RecipeResult)
    assert result.recipe == "Vacuum"
    assert "extreme_fragility" in result.active_signals


def test_classify_recipe_conflict():
    """Test recipe classification for Conflict pattern."""
    # Create primitives that should trigger Conflict
    primitives = MicrostructurePrimitives(
        ofi=0.25,           # Positive OFI
        liquidity_gravity=-0.002,  # Negative gravity (opposing)
        book_fragility=0.40,
        net_tape_pressure=-0.15,   # Negative tape pressure (opposing)
        ofi_persistence=0.40,      # Low persistence (no dominant direction)
        mid_price=50000.0,
    )
    
    result = classify_recipe(primitives)
    
    assert isinstance(result, RecipeResult)
    assert result.recipe == "Conflict"
    assert "book_vs_flow" in result.active_signals or "tape_vs_book" in result.active_signals