from __future__ import annotations

from agents.research.research_factory import KnowledgeBase, KnowledgeDocument


def cryptoskills_documents() -> list[KnowledgeDocument]:
    source = "https://cryptoskills.dev/"
    return [
        KnowledgeDocument(
            doc_id="cryptoskills-onchain-analysis",
            title="Onchain Analytics and Wallet Flow",
            source=source,
            content="Track exchange inflows/outflows, stablecoin issuance, and whale wallet clusters as probabilistic priors for market regimes.",
            tags=("onchain", "wallet", "flow", "regime"),
        ),
        KnowledgeDocument(
            doc_id="cryptoskills-defi-risk",
            title="DeFi Protocol Risk Evaluation",
            source=source,
            content="Evaluate TVL quality, oracle dependencies, liquidity concentration, and smart-contract risk before capital allocation.",
            tags=("defi", "risk", "tvl", "oracle"),
        ),
        KnowledgeDocument(
            doc_id="cryptoskills-derivatives-structure",
            title="Perpetuals and Derivatives Structure",
            source=source,
            content="Use funding, basis, open-interest structure, and liquidation maps to detect crowding and forced-flow setups.",
            tags=("perps", "funding", "oi", "liquidation"),
        ),
        KnowledgeDocument(
            doc_id="cryptoskills-tokenomics",
            title="Tokenomics and Supply Dynamics",
            source=source,
            content="Model unlock schedules, emissions, vesting, and treasury behavior to estimate forward sell pressure.",
            tags=("tokenomics", "supply", "unlocks"),
        ),
        KnowledgeDocument(
            doc_id="cryptoskills-execution-playbook",
            title="Crypto Execution and Slippage Control",
            source=source,
            content="Route orders by depth/impact, avoid toxic windows, and enforce slippage budgets across venues.",
            tags=("execution", "slippage", "routing"),
        ),
        KnowledgeDocument(
            doc_id="cryptoskills-research-validation",
            title="Research Validation and Promotion Discipline",
            source=source,
            content="Promote strategies only with out-of-sample stability, realistic costs, and governance-compliant attribution.",
            tags=("validation", "promotion", "governance"),
        ),
    ]


def cryptoskills_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(documents=cryptoskills_documents())
