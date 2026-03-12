from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectScope:
    project_id: str
    strategy_ids: tuple[str, ...] = ()
    allowed_secret_envs: tuple[str, ...] = ()
    memory_namespace: str | None = None


@dataclass(frozen=True)
class ProjectScopeDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class ProjectWorkspaceLayout:
    project_id: str
    root_dir: Path
    research_dir: Path
    backtest_dir: Path
    artifacts_dir: Path
    immutable_artifacts_dir: Path


class ProjectScopeManager:
    def __init__(self, scopes: list[ProjectScope] | None = None, *, workspace_base_dir: str | Path = "artifacts/projects") -> None:
        self._scopes: dict[str, ProjectScope] = {scope.project_id: scope for scope in (scopes or [])}
        self._workspace_base_dir = Path(workspace_base_dir)

    def register(self, scope: ProjectScope) -> None:
        self._scopes[scope.project_id] = scope

    def resolve(self, project_id: str) -> ProjectScope | None:
        return self._scopes.get(project_id)

    def authorize_strategy(self, *, project_id: str, strategy_id: str) -> ProjectScopeDecision:
        scope = self.resolve(project_id)
        if scope is None:
            return ProjectScopeDecision(False, f"unknown project scope: {project_id}")
        if scope.strategy_ids and strategy_id not in set(scope.strategy_ids):
            return ProjectScopeDecision(False, f"strategy not allowed in project: {strategy_id}")
        return ProjectScopeDecision(True, "ok")

    def authorize_secret_envs(self, *, project_id: str, requested_envs: tuple[str, ...]) -> ProjectScopeDecision:
        scope = self.resolve(project_id)
        if scope is None:
            return ProjectScopeDecision(False, f"unknown project scope: {project_id}")
        allowed = set(scope.allowed_secret_envs)
        for env_name in requested_envs:
            if env_name not in allowed:
                return ProjectScopeDecision(False, f"secret env not allowed for project: {env_name}")
        return ProjectScopeDecision(True, "ok")

    def scoped_topic(self, *, project_id: str, strategy_id: str) -> str:
        scope = self.resolve(project_id)
        namespace = scope.memory_namespace if scope and scope.memory_namespace else project_id
        return f"{namespace}::{strategy_id}"

    def workspace_layout(self, *, project_id: str) -> ProjectWorkspaceLayout:
        root = (self._workspace_base_dir / project_id).resolve()
        research = root / "research"
        backtest = root / "backtest"
        artifacts = root / "artifacts"
        immutable = artifacts / "immutable"
        for path in (research, backtest, artifacts, immutable):
            path.mkdir(parents=True, exist_ok=True)
        return ProjectWorkspaceLayout(
            project_id=project_id,
            root_dir=root,
            research_dir=research,
            backtest_dir=backtest,
            artifacts_dir=artifacts,
            immutable_artifacts_dir=immutable,
        )

    def resolve_project_path(
        self,
        *,
        project_id: str,
        strategy_id: str,
        category: str,
        filename: str,
        immutable: bool = False,
    ) -> Path:
        safe_category = _safe_slug(category)
        safe_strategy = _safe_slug(strategy_id)
        safe_filename = _safe_filename(filename)

        layout = self.workspace_layout(project_id=project_id)
        base = layout.immutable_artifacts_dir if immutable else layout.artifacts_dir
        out = (base / safe_strategy / safe_category / safe_filename).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        self._assert_within_root(out, layout.root_dir)
        return out

    @staticmethod
    def _assert_within_root(path: Path, root: Path) -> None:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path escapes project workspace root: {path}") from exc


def default_project_scope_manager() -> ProjectScopeManager:
    manager = ProjectScopeManager()
    manager.register(
        ProjectScope(
            project_id="default",
            strategy_ids=(),
            allowed_secret_envs=(
                "EXCHANGE_API_KEY",
                "EXCHANGE_API_SECRET",
                "POLYMARKET_API_KEY",
            ),
            memory_namespace="default",
        )
    )
    return manager


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip())
    out = "-".join(part for part in cleaned.split("-") if part)
    return out or "default"


def _safe_filename(value: str) -> str:
    name = Path(value).name
    return name if name else "artifact.txt"
