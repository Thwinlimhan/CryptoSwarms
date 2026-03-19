#!/usr/bin/env python3
"""
CryptoSwarms Enhancement Integration Script

Integrates all 7 enhancements into the production pipeline:
1. MiroFish: Emergent swarm market simulation
2. Karpathy: Full code-level autonomous evolution  
3. Senpi AI: Smart-money + Sentinel inverted scanner
4. BkDplx: Microstructure recipe classification
5. Chub: Zero-hallucination API docs
6. Funding Arb: AR(12) predictor
7. Hyperspace: P2P consensus

Usage:
    python scripts/integrate_enhancements.py --check-only
    python scripts/integrate_enhancements.py --integrate-all
    python scripts/integrate_enhancements.py --component mirofish
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any
import argparse
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.settings import settings
from agents.orchestration.hyperspace_mesh import HyperspaceMeshClient
from agents.backtest.mirofish_simulator import MiroFishRegimeSimulator
from agents.research.SenpiHyperfeedConnector import SenpiHyperfeedConnector
from agents.research.lob_connector import HyperliquidLOBConnector
from agents.research.funding_rate_connector import HyperliquidFundingConnector
from agents.backtest.validation_pipeline import ValidationPipeline


class HTTPTransport:
    """Simple HTTP transport for testing connections."""
    
    def post(self, url: str, payload: dict) -> dict:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get(self, url: str, params: dict | None = None) -> dict:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()


def check_mirofish_integration() -> bool:
    """Check if MiroFish service is accessible."""
    print("🔍 Checking MiroFish integration...")
    
    try:
        transport = HTTPTransport()
        simulator = MiroFishRegimeSimulator(
            base_url=settings.mirofish_url,
            transport=transport,
        )
        
        # Test with minimal market data
        test_data = {
            "close": [50000.0, 50100.0, 50050.0],
            "volume": [100.0, 150.0, 120.0],
        }
        
        verdict = simulator.simulate(test_data)
        print(f"✅ MiroFish: {verdict.regime} (consensus: {verdict.consensus_score:.2f})")
        return True
        
    except Exception as e:
        print(f"❌ MiroFish: {e}")
        return False


def check_senpi_integration() -> bool:
    """Check if Senpi AI service is accessible."""
    print("🔍 Checking Senpi AI integration...")
    
    if not settings.senpi_api_key:
        print("❌ Senpi AI: SENPI_API_KEY not configured")
        return False
    
    try:
        transport = HTTPTransport()
        connector = SenpiHyperfeedConnector(
            base_url=settings.senpi_api_url,
            api_key=settings.senpi_api_key,
            transport=transport,
        )
        
        signal = connector.fetch_signal("BTC")
        print(f"✅ Senpi AI: {signal.direction} (confidence: {signal.confidence:.2f})")
        return True
        
    except Exception as e:
        print(f"❌ Senpi AI: {e}")
        return False


def check_hyperspace_integration() -> bool:
    """Check if Hyperspace mesh is accessible."""
    print("🔍 Checking Hyperspace mesh integration...")
    
    try:
        transport = HTTPTransport()
        mesh_client = HyperspaceMeshClient(
            node_url=settings.hyperspace_node_url,
            agent_id=settings.hyperspace_agent_id,
            transport=transport,
        )
        
        # Test mesh join
        joined = mesh_client.join_mesh()
        if joined:
            rank = mesh_client.fetch_agent_rank()
            print(f"✅ Hyperspace: Rank {rank.rank_score:.2f} (weight: {rank.consensus_weight:.2f})")
            mesh_client.leave_mesh()
            return True
        else:
            print("❌ Hyperspace: Failed to join mesh")
            return False
            
    except Exception as e:
        print(f"❌ Hyperspace: {e}")
        return False


def check_lob_integration() -> bool:
    """Check if Hyperliquid LOB connector works."""
    print("🔍 Checking Hyperliquid LOB integration...")
    
    try:
        transport = HTTPTransport()
        connector = HyperliquidLOBConnector(transport=transport)
        
        lob = connector.fetch_lob("BTC")
        trades = connector.fetch_recent_trades("BTC")
        
        print(f"✅ Hyperliquid LOB: {len(lob.bids)} bids, {len(lob.asks)} asks, {len(trades)} trades")
        return True
        
    except Exception as e:
        print(f"❌ Hyperliquid LOB: {e}")
        return False


def check_funding_integration() -> bool:
    """Check if funding rate connector works."""
    print("🔍 Checking funding rate integration...")
    
    try:
        transport = HTTPTransport()
        connector = HyperliquidFundingConnector(transport=transport)
        
        prediction = connector.fetch_funding_prediction("BTC")
        print(f"✅ Funding rates: {prediction.current_funding_rate:.1f} bps (yield score: {prediction.yield_opportunity_score:.2f})")
        return True
        
    except Exception as e:
        print(f"❌ Funding rates: {e}")
        return False


def check_chub_integration() -> bool:
    """Check if Chub CLI is installed."""
    print("🔍 Checking Chub CLI integration...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["chub", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0:
            print(f"✅ Chub CLI: {result.stdout.strip()}")
            return True
        else:
            print("❌ Chub CLI: Command failed")
            return False
            
    except FileNotFoundError:
        print("❌ Chub CLI: Not installed. Run: npm install -g @aisuite/chub")
        return False
    except Exception as e:
        print(f"❌ Chub CLI: {e}")
        return False


def check_sandbox_integration() -> bool:
    """Check if sandbox provider is configured."""
    print("🔍 Checking sandbox integration...")
    
    provider = settings.sandbox_provider
    
    if provider == "local":
        print("⚠️  Sandbox: Using local provider (no isolation)")
        return True
    elif provider == "modal":
        # Check if Modal is configured
        modal_token = os.getenv("MODAL_TOKEN_ID")
        if modal_token:
            print("✅ Sandbox: Modal configured")
            return True
        else:
            print("❌ Sandbox: Modal selected but MODAL_TOKEN_ID not set")
            return False
    elif provider == "langsmith":
        # Check if LangSmith is configured
        langsmith_key = os.getenv("LANGCHAIN_API_KEY")
        if langsmith_key:
            print("✅ Sandbox: LangSmith configured")
            return True
        else:
            print("❌ Sandbox: LangSmith selected but LANGCHAIN_API_KEY not set")
            return False
    else:
        print(f"❌ Sandbox: Unknown provider '{provider}'")
        return False


def check_all_integrations() -> dict[str, bool]:
    """Check all enhancement integrations."""
    print("🚀 CryptoSwarms Enhancement Integration Check\n")
    
    checks = {
        "mirofish": check_mirofish_integration(),
        "senpi": check_senpi_integration(),
        "hyperspace": check_hyperspace_integration(),
        "lob": check_lob_integration(),
        "funding": check_funding_integration(),
        "chub": check_chub_integration(),
        "sandbox": check_sandbox_integration(),
    }
    
    print(f"\n📊 Integration Status:")
    passed = sum(checks.values())
    total = len(checks)
    
    for component, status in checks.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {component.title()}")
    
    print(f"\n🎯 Overall: {passed}/{total} components ready")
    
    if passed == total:
        print("🎉 All enhancements are integrated and ready!")
    else:
        print("⚠️  Some components need attention before full integration.")
    
    return checks


def create_production_config() -> None:
    """Create production configuration with all enhancements enabled."""
    print("🔧 Creating production configuration...")
    
    config_template = """# CryptoSwarms Production Configuration
# Generated by integrate_enhancements.py

# ── Core Services ────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
TIMESCALEDB_HOST=timescaledb
TIMESCALEDB_PORT=5432

# ── Enhancement Services ─────────────────────────────────────
MIROFISH_URL=http://mirofish:5001
SENPI_API_URL=https://api.senpi.ai/v1
HYPERSPACE_NODE_URL=http://hyperspace:8545

# ── Sandbox Configuration ────────────────────────────────────
SANDBOX_PROVIDER=modal
SANDBOX_IMAGE=your-registry/cryptoswarms-sandbox:latest
SANDBOX_CPU=4
SANDBOX_MEMORY_GB=16

# ── Gate Thresholds ──────────────────────────────────────────
GATE_MIROFISH_CONSENSUS=0.65
GATE_RECIPE_SCORE=0.75
GATE_HYPERSPACE_CONSENSUS=0.70
GATE_FUNDING_YIELD_SCORE=0.35
GATE_FUNDING_CONFIDENCE=0.65

# ── API Keys (set these manually) ────────────────────────────
# SENPI_API_KEY=your_senpi_key_here
# LANGCHAIN_API_KEY=your_langsmith_key_here
# MODAL_TOKEN_ID=your_modal_token_here
"""
    
    config_path = Path(".env.production")
    config_path.write_text(config_template)
    print(f"✅ Production config written to {config_path}")


def main():
    parser = argparse.ArgumentParser(description="CryptoSwarms Enhancement Integration")
    parser.add_argument("--check-only", action="store_true", help="Only check integrations")
    parser.add_argument("--integrate-all", action="store_true", help="Full integration setup")
    parser.add_argument("--component", help="Check specific component")
    parser.add_argument("--create-config", action="store_true", help="Create production config")
    
    args = parser.parse_args()
    
    if args.component:
        # Check specific component
        component_checks = {
            "mirofish": check_mirofish_integration,
            "senpi": check_senpi_integration,
            "hyperspace": check_hyperspace_integration,
            "lob": check_lob_integration,
            "funding": check_funding_integration,
            "chub": check_chub_integration,
            "sandbox": check_sandbox_integration,
        }
        
        if args.component in component_checks:
            component_checks[args.component]()
        else:
            print(f"Unknown component: {args.component}")
            print(f"Available: {', '.join(component_checks.keys())}")
            sys.exit(1)
    
    elif args.create_config:
        create_production_config()
    
    elif args.integrate_all:
        # Full integration
        checks = check_all_integrations()
        
        if all(checks.values()):
            print("\n🚀 Starting full integration...")
            create_production_config()
            print("✅ Integration complete!")
        else:
            print("\n❌ Cannot proceed with full integration - fix failing components first")
            sys.exit(1)
    
    else:
        # Default: check all
        check_all_integrations()


if __name__ == "__main__":
    main()