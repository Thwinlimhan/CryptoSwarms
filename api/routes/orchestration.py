from fastapi import APIRouter, Query
from typing import Any
import asyncio
from agents.orchestration.subagent_executor import SubagentTask
from api.dependencies import runtime_orchestrator, subagent_executor

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])

@router.get("/runtime-preview")
async def runtime_preview(
    scope_ok: bool = Query(default=True),
    input_ok: bool = Query(default=True),
    tool_ok: bool = Query(default=True),
    governor_ok: bool = Query(default=True),
) -> dict[str, Any]:
    result = runtime_orchestrator.execute(
        {
            "scope_ok": scope_ok,
            "input_ok": input_ok,
            "tool_ok": tool_ok,
            "governor_ok": governor_ok,
        }
    )
    return {
        "ok": result.ok,
        "duration_ms": result.duration_ms,
        "stages": result.stages,
        "retries": result.retries,
        "checkpoints": result.checkpoints,
    }

async def _demo_subagent_worker(task: SubagentTask) -> dict[str, object]:
    role = task.role
    sleep_s = float(task.payload.get("sleep_s", 0.05))
    await asyncio.sleep(max(0.0, sleep_s))
    if bool(task.payload.get("force_error", False)):
        raise RuntimeError(f"subagent error: {role}")
    return {
        "role": role,
        "decision_hint": task.payload.get("decision_hint", "hold"),
    }

@router.get("/subagents-preview")
async def subagents_preview(
    tasks: int = Query(default=4, ge=1, le=20),
    force_timeout: bool = Query(default=False),
) -> dict[str, Any]:
    payloads: list[SubagentTask] = []
    for idx in range(tasks):
        payloads.append(
            SubagentTask(
                task_id=f"task-{idx+1}",
                role=f"solver_{idx+1}",
                payload={
                    "sleep_s": 9.0 if force_timeout and idx == tasks - 1 else 0.05,
                    "decision_hint": "go" if idx % 2 == 0 else "hold",
                },
            )
        )

    report = await subagent_executor.run(payloads, _demo_subagent_worker)
    return {
        "started_at": report.started_at.isoformat(),
        "ended_at": report.ended_at.isoformat(),
        "total_tasks": report.total_tasks,
        "completed": report.completed,
        "failed": report.failed,
        "timed_out": report.timed_out,
        "max_parallelism": report.max_parallelism,
        "queued_tasks": report.queued_tasks,
        "estimated_waves": report.estimated_waves,
        "queue_pressure_ratio": report.queue_pressure_ratio,
        "saturation": report.saturation,
        "timeout_rate": report.timeout_rate,
        "error_rate": report.error_rate,
        "total_latency_ms": report.total_latency_ms,
        "results": [
            {
                "task_id": r.task_id,
                "role": r.role,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "output": r.output,
            }
            for r in report.results
        ],
    }
