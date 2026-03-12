from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable


@dataclass
class RuntimeContext:
    payload: dict[str, object]
    checkpoints: dict[str, dict[str, object]] = field(default_factory=dict)
    timeline: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeResult:
    ok: bool
    stages: list[str]
    retries: dict[str, int]
    duration_ms: float
    checkpoints: dict[str, dict[str, object]]


class RuntimeMiddleware:
    name: str = "middleware"

    def run(self, ctx: RuntimeContext, nxt: Callable[[RuntimeContext], RuntimeContext]) -> RuntimeContext:
        return nxt(ctx)


class RuntimeOrchestrator:
    """Deterministic middleware runner with per-stage retries and checkpoints."""

    def __init__(self, middlewares: list[RuntimeMiddleware], *, max_retries: int = 1) -> None:
        self.middlewares = list(middlewares)
        self.max_retries = max(0, int(max_retries))

    def execute(self, payload: dict[str, object]) -> RuntimeResult:
        started = perf_counter()
        ctx = RuntimeContext(payload=dict(payload))
        retries: dict[str, int] = {}

        def terminal(c: RuntimeContext) -> RuntimeContext:
            c.timeline.append("terminal")
            return c

        nxt = terminal
        for middleware in reversed(self.middlewares):
            current = middleware
            previous = nxt

            def wrapped(c: RuntimeContext, mw: RuntimeMiddleware = current, n: Callable[[RuntimeContext], RuntimeContext] = previous) -> RuntimeContext:
                stage = mw.name
                attempts = 0
                while True:
                    attempts += 1
                    try:
                        c.timeline.append(stage)
                        out = mw.run(c, n)
                        c.checkpoints[stage] = {
                            "ok": True,
                            "attempt": attempts,
                        }
                        retries[stage] = attempts - 1
                        return out
                    except Exception as exc:
                        c.checkpoints[stage] = {
                            "ok": False,
                            "attempt": attempts,
                            "error": str(exc),
                        }
                        if attempts > self.max_retries + 1:
                            retries[stage] = attempts - 1
                            raise

            nxt = wrapped

        ok = True
        try:
            ctx = nxt(ctx)
        except Exception:
            ok = False

        duration_ms = (perf_counter() - started) * 1000.0
        return RuntimeResult(
            ok=ok,
            stages=ctx.timeline,
            retries=retries,
            duration_ms=round(duration_ms, 3),
            checkpoints=ctx.checkpoints,
        )


class StageFlagMiddleware(RuntimeMiddleware):
    def __init__(self, name: str, *, required_flag: str | None = None) -> None:
        self.name = name
        self.required_flag = required_flag

    def run(self, ctx: RuntimeContext, nxt: Callable[[RuntimeContext], RuntimeContext]) -> RuntimeContext:
        if self.required_flag is not None:
            value = bool(ctx.payload.get(self.required_flag, False))
            if not value:
                raise ValueError(f"required flag missing: {self.required_flag}")
        return nxt(ctx)


def default_runtime_orchestrator() -> RuntimeOrchestrator:
    return RuntimeOrchestrator(
        middlewares=[
            StageFlagMiddleware("scope", required_flag="scope_ok"),
            StageFlagMiddleware("input_guardrail", required_flag="input_ok"),
            StageFlagMiddleware("tool_guardrail", required_flag="tool_ok"),
            StageFlagMiddleware("debate"),
            StageFlagMiddleware("governor", required_flag="governor_ok"),
        ],
        max_retries=1,
    )
