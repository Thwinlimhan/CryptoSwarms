from __future__ import annotations

from agents.research.research_factory import KnowledgeBase, KnowledgeDocument


def readtheskill_crypto_documents() -> list[KnowledgeDocument]:
    source = "https://readtheskill.com/skills"
    return [
        KnowledgeDocument(
            doc_id="rts-crypto-market-microstructure",
            title="Crypto Market Microstructure",
            source=source,
            content="Model spread, depth, queue dynamics, and adverse selection to avoid paying unnecessary edge leakage.",
            tags=("execution", "microstructure", "risk"),
        ),
        KnowledgeDocument(
            doc_id="rts-funding-and-basis",
            title="Funding Rate and Basis Carry",
            source=source,
            content="Track perp funding, term basis, and cross-venue dislocations to extract carry while constraining liquidation risk.",
            tags=("perps", "carry", "basis"),
        ),
        KnowledgeDocument(
            doc_id="rts-liquidation-flow",
            title="Liquidation Cascade Detection",
            source=source,
            content="Detect forced-flow zones with open interest, liquidation maps, and volatility expansion filters.",
            tags=("liquidation", "volatility", "risk"),
        ),
        KnowledgeDocument(
            doc_id="rts-onchain-flow",
            title="Onchain Flow and Wallet Intelligence",
            source=source,
            content="Use wallet clusters, exchange inflow/outflow, and stablecoin velocity as probabilistic priors for market direction.",
            tags=("onchain", "flow", "signals"),
        ),
        KnowledgeDocument(
            doc_id="rts-regime-framework",
            title="Regime-Aware Crypto Strategy Selection",
            source=source,
            content="Switch risk budget and signal families across trend, chop, and stress regimes using explicit thresholds.",
            tags=("regime", "portfolio", "allocation"),
        ),
        KnowledgeDocument(
            doc_id="rts-risk-playbook",
            title="Crypto Risk Playbook",
            source=source,
            content="Enforce drawdown halts, correlation heat limits, and venue concentration caps before scaling exposure.",
            tags=("risk", "governance", "portfolio"),
        ),
        KnowledgeDocument(
            doc_id="rts-latency-arb",
            title="Cross-Venue Latency and Spread Arbitration",
            source=source,
            content="Monitor venue lead-lag and quote staleness to capture dislocations with strict legging controls.",
            tags=("arbitrage", "execution", "latency"),
        ),
        KnowledgeDocument(
            doc_id="rts-signal-validation",
            title="Signal Validation for Crypto",
            source=source,
            content="Require out-of-sample consistency, fee/slippage realism, and survivorship-adjusted scorecards before promotion.",
            tags=("validation", "backtest", "promotion"),
        ),
        KnowledgeDocument(
            doc_id="rts-news-probability",
            title="News-to-Probability Update",
            source=source,
            content="Convert event news to Bayesian likelihood updates, then route only positive-EV scenarios to execution.",
            tags=("bayes", "news", "probability"),
        ),
        KnowledgeDocument(
            doc_id="rts-sizing-discipline",
            title="Fractional Kelly Sizing Discipline",
            source=source,
            content="Use uncertainty-haircut Kelly sizing with hard caps and minimum liquidity constraints.",
            tags=("kelly", "sizing", "risk"),
        ),
    ]


def readtheskill_crypto_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(documents=readtheskill_crypto_documents())
