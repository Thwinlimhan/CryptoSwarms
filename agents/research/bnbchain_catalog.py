from __future__ import annotations

from agents.research.research_factory import KnowledgeBase, KnowledgeDocument


def bnbchain_skill_documents() -> list[KnowledgeDocument]:
    source = "https://github.com/bnb-chain/bnbchain-skills"
    return [
        KnowledgeDocument(
            doc_id="bnbchain-skill-install",
            title="BNB Chain MCP Skill Installation",
            source=source,
            content="Install and configure bnbchain-mcp via npx @bnb-chain/mcp@latest and MCP client settings for agent usage.",
            tags=("bnbchain", "mcp", "installation"),
        ),
        KnowledgeDocument(
            doc_id="bnbchain-evm-tools",
            title="BNB Chain EVM Tools Reference",
            source=source,
            content="Use block, transaction, contract, token, NFT, wallet, and network tools for BSC, opBNB, and EVM-compatible chains.",
            tags=("evm", "blocks", "transactions", "contracts", "tokens", "nft", "wallet"),
        ),
        KnowledgeDocument(
            doc_id="bnbchain-erc8004-tools",
            title="ERC-8004 Agent Registry Tools",
            source=source,
            content="Register and resolve ERC-8004 agents and metadata profiles with identity registry operations.",
            tags=("erc8004", "agent", "identity"),
        ),
        KnowledgeDocument(
            doc_id="bnbchain-greenfield-tools",
            title="Greenfield Storage and Payment Tools",
            source=source,
            content="Manage buckets, objects, and payment-related operations on Greenfield through MCP actions.",
            tags=("greenfield", "storage", "payments"),
        ),
        KnowledgeDocument(
            doc_id="bnbchain-credentials-safety",
            title="BNB Chain Credentials and Safety",
            source=source,
            content="Configure private keys and endpoints safely with strict credential handling and no secret exposure in prompts.",
            tags=("security", "credentials", "ops"),
        ),
        KnowledgeDocument(
            doc_id="bnbchain-agent-prompts",
            title="BNB Chain MCP Prompt Patterns",
            source=source,
            content="Prompt patterns for querying balances, blocks, contract reads, transfers, and Greenfield actions using MCP tools.",
            tags=("prompts", "agent", "tooling"),
        ),
    ]


def bnbchain_skill_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(documents=bnbchain_skill_documents())
