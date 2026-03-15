from pathlib import Path

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List

from api.dependencies import agent_runner
from api.dashboard_repository import DashboardRepository

router = APIRouter(prefix="/api/research", tags=["swarm-research"])

@router.get("/reports")
async def get_research_reports(limit: int = 10):
    """Fetch recent research reports from the database."""
    # This would normally go through a repository
    pool = agent_runner._db._pool
    if not pool:
        raise HTTPException(status_code=503, detail="Database offline")
        
    rows = await pool.fetch(
        "SELECT * FROM research_reports ORDER BY time DESC LIMIT $1",
        limit
    )
    return [dict(r) for r in rows]

@router.get("/experiments")
async def get_research_experiments(theme: str = None, limit: int = 20):
    """Fetch details of research experiments."""
    pool = agent_runner._db._pool
    if not pool:
        raise HTTPException(status_code=503, detail="Database offline")
        
    if theme:
        rows = await pool.fetch(
            "SELECT * FROM research_experiments WHERE theme = $1 ORDER BY time DESC LIMIT $2",
            theme, limit
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM research_experiments ORDER BY time DESC LIMIT $1",
            limit
        )
    return [dict(r) for r in rows]

@router.post("/reports/{report_id}/apply")
async def apply_research_recommendation(report_id: str):
    """
    Apply a research recommendation to the swarm.
    Note: In a production system, this would trigger a config update or CI/CD pulse.
    """
    pool = agent_runner._db._pool
    if not pool:
        raise HTTPException(status_code=503, detail="Database offline")
        
    await pool.execute(
        "UPDATE research_reports SET applied = TRUE, applied_at = NOW() WHERE id = $1",
        report_id
    )
    return {"status": "SUCCESS", "message": "Recommendation applied (simulated)"}

@router.get("/memory")
async def get_research_memory():
    """Fetch the full research Memory DAG."""
    if not agent_runner.dag:
        return {"nodes": [], "edges": []}
    return agent_runner.dag.to_dict()

def _safe_strategy_basename(name: str) -> str | None:
    """Return a safe basename (no path traversal). None if invalid."""
    if not name or not isinstance(name, str):
        return None
    name = name.strip()
    if ".." in name or "/" in name or "\\" in name:
        return None
    base = Path(name).name
    if not base or base != name:
        return None
    return base if base.endswith(".py") else f"{base}.py"


@router.post("/refinements/{node_id}/apply")
async def apply_strategy_refinement(node_id: str):
    """Write proposed parameters back into the strategy source file.

    Node must have node_type=strategy_refinement and metadata source_file (e.g. breakout_trend.py)
    and proposed_parameters (dict). Path traversal in source_file is rejected.
    """
    import re
    import json

    if not node_id or not node_id.strip():
        raise HTTPException(status_code=400, detail="node_id is required")

    node = agent_runner.dag.get_node(node_id.strip())
    if not node or node.node_type != "strategy_refinement":
        raise HTTPException(status_code=404, detail="Refinement proposal not found")

    raw_source = node.metadata.get("source_file")
    proposed = node.metadata.get("proposed_parameters")

    if not raw_source:
        raise HTTPException(status_code=400, detail="Missing source_file in node metadata")
    source_file = _safe_strategy_basename(str(raw_source))
    if not source_file:
        raise HTTPException(status_code=400, detail="Invalid source_file (no path traversal)")
    if not isinstance(proposed, dict) or not proposed:
        raise HTTPException(status_code=400, detail="proposed_parameters must be a non-empty dict")

    base = Path("strategies").resolve()
    path = (base / source_file).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Strategy path must be under strategies/")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Strategy file {source_file} not found")

    try:
        content = path.read_text(encoding="utf-8")
        pattern = r"(parameters\s*=\s*\{)(.*?)(\}\s*,?\n?\s*\))"
        params_str = json.dumps(proposed, indent=8)
        if params_str.startswith("{") and params_str.endswith("}"):
            params_str = params_str[1:-1].strip()

        def replacement(match):
            return f"{match.group(1)}\n        {params_str}\n    {match.group(3)}"

        new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
        if new_content == content:
            raise HTTPException(
                status_code=400,
                detail="Could not find parameters={...} block in strategy file; check file format",
            )
        path.write_text(new_content, encoding="utf-8")
        return {
            "status": "SUCCESS",
            "message": f"Applied {len(proposed)} parameter updates to {source_file}",
            "updated_params": proposed,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply refinement: {str(e)}")
