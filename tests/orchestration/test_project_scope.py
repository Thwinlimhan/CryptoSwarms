from agents.orchestration.project_scope import ProjectScope, ProjectScopeManager


def test_project_scope_strategy_authorization():
    manager = ProjectScopeManager(
        [ProjectScope(project_id="alpha", strategy_ids=("s1",), allowed_secret_envs=("EXCHANGE_API_KEY",))]
    )

    allowed = manager.authorize_strategy(project_id="alpha", strategy_id="s1")
    blocked = manager.authorize_strategy(project_id="alpha", strategy_id="s2")

    assert allowed.allowed is True
    assert blocked.allowed is False


def test_project_scope_secret_authorization():
    manager = ProjectScopeManager(
        [ProjectScope(project_id="alpha", strategy_ids=(), allowed_secret_envs=("EXCHANGE_API_KEY",))]
    )

    allowed = manager.authorize_secret_envs(project_id="alpha", requested_envs=("EXCHANGE_API_KEY",))
    blocked = manager.authorize_secret_envs(project_id="alpha", requested_envs=("EXCHANGE_API_SECRET",))

    assert allowed.allowed is True
    assert blocked.allowed is False


def test_project_scope_workspace_layout_and_immutable_path(tmp_path):
    manager = ProjectScopeManager([ProjectScope(project_id="alpha")], workspace_base_dir=tmp_path)

    layout = manager.workspace_layout(project_id="alpha")
    assert layout.root_dir.exists()
    assert layout.research_dir.exists()
    assert layout.backtest_dir.exists()
    assert layout.artifacts_dir.exists()
    assert layout.immutable_artifacts_dir.exists()

    out = manager.resolve_project_path(
        project_id="alpha",
        strategy_id="phase1-btc-breakout-15m",
        category="backtest",
        filename="candidate.json",
        immutable=True,
    )
    assert str(out).startswith(str(layout.root_dir))
    assert "immutable" in str(out)


def test_project_scope_path_resolution_strips_traversal(tmp_path):
    manager = ProjectScopeManager([ProjectScope(project_id="alpha")], workspace_base_dir=tmp_path)
    out = manager.resolve_project_path(
        project_id="alpha",
        strategy_id="../bad",
        category="../../evil",
        filename="../x.json",
        immutable=False,
    )
    assert out.name == "x.json"
    assert str(out).startswith(str((tmp_path / "alpha").resolve()))
