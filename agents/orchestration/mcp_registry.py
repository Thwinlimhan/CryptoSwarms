from __future__ import annotations

from dataclasses import dataclass


_RISK_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


_DEFAULT_FORBIDDEN_TOOL_PATTERNS = (
    "shell",
    "bash",
    "python_exec",
    "subprocess",
    "order_execute",
    "place_order",
)


@dataclass(frozen=True)
class MCPToolSpec:
    tool_id: str
    risk_tier: str
    side_effects: bool
    requires_approval: bool


@dataclass(frozen=True)
class MCPAuthorization:
    allowed: bool
    reason: str


class MCPRegistry:
    def __init__(
        self,
        tools: list[MCPToolSpec] | None = None,
        *,
        forbidden_tool_patterns: tuple[str, ...] = _DEFAULT_FORBIDDEN_TOOL_PATTERNS,
    ) -> None:
        self._tools: dict[str, MCPToolSpec] = {tool.tool_id: tool for tool in (tools or [])}
        self._forbidden_tool_patterns = tuple(p.lower() for p in forbidden_tool_patterns)

    def register(self, spec: MCPToolSpec) -> None:
        self._tools[spec.tool_id] = spec

    def get(self, tool_id: str) -> MCPToolSpec | None:
        return self._tools.get(tool_id)

    def authorize(self, *, tool_id: str, max_risk_tier: str = "medium", approval_granted: bool = False) -> MCPAuthorization:
        if self._is_forbidden(tool_id):
            return MCPAuthorization(False, f"tool forbidden on execution path: {tool_id}")

        spec = self.get(tool_id)
        if spec is None:
            return MCPAuthorization(False, f"tool not registered: {tool_id}")

        max_level = _RISK_LEVELS.get(max_risk_tier, _RISK_LEVELS["medium"])
        tool_level = _RISK_LEVELS.get(spec.risk_tier, _RISK_LEVELS["critical"])
        if tool_level > max_level:
            return MCPAuthorization(False, f"tool risk tier too high: {spec.risk_tier}")

        if spec.requires_approval and not approval_granted:
            return MCPAuthorization(False, "tool approval required")

        return MCPAuthorization(True, "ok")

    def _is_forbidden(self, tool_id: str) -> bool:
        value = tool_id.lower()
        return any(pattern in value for pattern in self._forbidden_tool_patterns)


def default_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()
    registry.register(MCPToolSpec(tool_id="read_metrics", risk_tier="low", side_effects=False, requires_approval=False))
    registry.register(MCPToolSpec(tool_id="score_decision", risk_tier="low", side_effects=False, requires_approval=False))
    registry.register(MCPToolSpec(tool_id="emit_report", risk_tier="medium", side_effects=True, requires_approval=False))
    return registry
