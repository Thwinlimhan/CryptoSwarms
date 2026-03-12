from agents.orchestration.mcp_registry import MCPRegistry, MCPToolSpec


def test_mcp_registry_blocks_unregistered_tool():
    registry = MCPRegistry()
    out = registry.authorize(tool_id="unknown_tool", max_risk_tier="medium", approval_granted=False)
    assert out.allowed is False


def test_mcp_registry_blocks_risk_tier_above_limit():
    registry = MCPRegistry([MCPToolSpec(tool_id="score_decision", risk_tier="critical", side_effects=True, requires_approval=False)])
    out = registry.authorize(tool_id="score_decision", max_risk_tier="medium", approval_granted=False)
    assert out.allowed is False
    assert "risk tier" in out.reason


def test_mcp_registry_blocks_forbidden_execution_path_tool_patterns():
    registry = MCPRegistry([MCPToolSpec(tool_id="shell_exec", risk_tier="low", side_effects=False, requires_approval=False)])
    out = registry.authorize(tool_id="shell_exec", max_risk_tier="critical", approval_granted=True)
    assert out.allowed is False
    assert "forbidden" in out.reason
