import asyncio

from agents.orchestration.subagent_executor import SubagentExecutor, SubagentTask


async def _worker(task: SubagentTask) -> dict[str, object]:
    await asyncio.sleep(float(task.payload.get("sleep_s", 0.01)))
    return {"task": task.task_id}


async def _timeout_worker(task: SubagentTask) -> dict[str, object]:
    _ = task
    await asyncio.Event().wait()
    return {}


async def _error_worker(task: SubagentTask) -> dict[str, object]:
    _ = task
    raise RuntimeError("boom")


def test_subagent_executor_runs_tasks_with_bounded_parallelism():
    executor = SubagentExecutor(max_parallelism=2, timeout_seconds=1.0)
    tasks = [SubagentTask(task_id=f"t{i}", role="solver", payload={"sleep_s": 0.01}) for i in range(4)]
    out = asyncio.run(executor.run(tasks, _worker))
    assert out.total_tasks == 4
    assert out.completed == 4
    assert out.failed == 0
    assert out.timed_out == 0
    assert out.queued_tasks == 2
    assert out.estimated_waves == 2
    assert out.saturation is True
    assert out.queue_pressure_ratio == 2.0


def test_subagent_executor_reports_errors_and_timeouts():
    executor = SubagentExecutor(max_parallelism=1, timeout_seconds=0.01)
    out = asyncio.run(executor.run([SubagentTask(task_id="timeout", role="solver", payload={})], _timeout_worker))
    assert out.total_tasks == 1
    assert out.timed_out == 1
    assert out.timeout_rate == 1.0

    out_err = asyncio.run(executor.run([SubagentTask(task_id="err", role="solver", payload={})], _error_worker))
    assert out_err.failed == 1
    assert out_err.error_rate == 1.0
