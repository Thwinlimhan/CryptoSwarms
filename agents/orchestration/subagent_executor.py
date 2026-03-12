from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from time import perf_counter
from typing import Awaitable, Callable


@dataclass(frozen=True)
class SubagentTask:
    task_id: str
    role: str
    payload: dict[str, object]


@dataclass(frozen=True)
class SubagentResult:
    task_id: str
    role: str
    status: str
    latency_ms: float
    output: dict[str, object]


@dataclass(frozen=True)
class SubagentExecutionReport:
    started_at: datetime
    ended_at: datetime
    total_tasks: int
    completed: int
    failed: int
    timed_out: int
    max_parallelism: int
    total_latency_ms: float
    queued_tasks: int
    estimated_waves: int
    queue_pressure_ratio: float
    saturation: bool
    timeout_rate: float
    error_rate: float
    results: list[SubagentResult]


AsyncSubagentFn = Callable[[SubagentTask], Awaitable[dict[str, object]]]


class SubagentExecutor:
    def __init__(self, *, max_parallelism: int = 3, timeout_seconds: float = 12.0) -> None:
        self.max_parallelism = max(1, int(max_parallelism))
        self.timeout_seconds = max(0.1, float(timeout_seconds))

    async def run(self, tasks: list[SubagentTask], fn: AsyncSubagentFn) -> SubagentExecutionReport:
        started = datetime.now(timezone.utc)
        sem = asyncio.Semaphore(self.max_parallelism)

        async def execute_one(task: SubagentTask) -> SubagentResult:
            t0 = perf_counter()
            async with sem:
                try:
                    out = await asyncio.wait_for(fn(task), timeout=self.timeout_seconds)
                    status = "ok"
                except asyncio.TimeoutError:
                    out = {"error": "timeout"}
                    status = "timeout"
                except Exception as exc:
                    out = {"error": str(exc)}
                    status = "error"
            return SubagentResult(
                task_id=task.task_id,
                role=task.role,
                status=status,
                latency_ms=round((perf_counter() - t0) * 1000.0, 3),
                output=out,
            )

        results = await asyncio.gather(*(execute_one(task) for task in tasks)) if tasks else []
        ended = datetime.now(timezone.utc)

        total_tasks = len(tasks)
        completed = sum(1 for r in results if r.status == "ok")
        timed_out = sum(1 for r in results if r.status == "timeout")
        failed = sum(1 for r in results if r.status == "error")
        total_latency = sum(r.latency_ms for r in results)

        queued_tasks = max(0, total_tasks - self.max_parallelism)
        estimated_waves = max(1, ceil(total_tasks / self.max_parallelism)) if total_tasks > 0 else 0
        queue_pressure_ratio = round(total_tasks / self.max_parallelism, 4) if total_tasks > 0 else 0.0
        saturation = total_tasks > self.max_parallelism
        timeout_rate = round(timed_out / total_tasks, 4) if total_tasks > 0 else 0.0
        error_rate = round(failed / total_tasks, 4) if total_tasks > 0 else 0.0

        return SubagentExecutionReport(
            started_at=started,
            ended_at=ended,
            total_tasks=total_tasks,
            completed=completed,
            failed=failed,
            timed_out=timed_out,
            max_parallelism=self.max_parallelism,
            total_latency_ms=round(total_latency, 3),
            queued_tasks=queued_tasks,
            estimated_waves=estimated_waves,
            queue_pressure_ratio=queue_pressure_ratio,
            saturation=saturation,
            timeout_rate=timeout_rate,
            error_rate=error_rate,
            results=results,
        )
