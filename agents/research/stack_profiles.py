from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalStackProfile:
    name: str
    category: str
    role: str
    integration_status: str
    priority: int
    notes: str


def recommended_stack_profiles() -> list[ExternalStackProfile]:
    profiles = [
        ExternalStackProfile(
            name="autoresearch",
            category="research_loop",
            role="time-boxed experiment and keep/discard policy",
            integration_status="integrated",
            priority=1,
            notes="Use as core pattern for autonomous research iteration.",
        ),
        ExternalStackProfile(
            name="RD-Agent",
            category="agentic_r_and_d",
            role="multi-agent research and experiment planning",
            integration_status="planned",
            priority=2,
            notes="Map agent roles to research, validation, and optimizer workers.",
        ),
        ExternalStackProfile(
            name="OpenBB Workspace",
            category="analyst_ui",
            role="interactive research and insight application UX",
            integration_status="planned",
            priority=3,
            notes="Use as dashboard and analyst workflow inspiration.",
        ),
        ExternalStackProfile(
            name="Freqtrade",
            category="execution_ops",
            role="battle-tested crypto bot operations reference",
            integration_status="benchmarking",
            priority=4,
            notes="Use as benchmark for execution reliability and ops playbooks.",
        ),
        ExternalStackProfile(
            name="QuantConnect Lean",
            category="institutional_process",
            role="research-backtest-live governance benchmark",
            integration_status="benchmarking",
            priority=5,
            notes="Use for institutional lifecycle standards and acceptance criteria.",
        ),
        ExternalStackProfile(
            name="Qlib",
            category="quant_research",
            role="dataset and factor pipeline reference",
            integration_status="planned",
            priority=6,
            notes="Use for advanced research dataset and feature workflows.",
        ),
        ExternalStackProfile(
            name="Jesse",
            category="crypto_backtest",
            role="backtest runtime engine",
            integration_status="integrated",
            priority=7,
            notes="Already wired in strict D10 runtime checks.",
        ),
        ExternalStackProfile(
            name="vectorbt",
            category="crypto_backtest",
            role="fast strategy screening engine",
            integration_status="integrated",
            priority=8,
            notes="Already wired in strict D10 runtime checks; verify license fit.",
        ),
    ]
    return sorted(profiles, key=lambda p: p.priority)
