from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class IsolationPolicy:
    network_access: bool
    filesystem_scope: str
    allow_shell: bool


def input_guardrail(*, text: str, max_chars: int = 5000, banned_patterns: tuple[str, ...] = ()) -> GuardrailResult:
    if len(text) > max(1, int(max_chars)):
        return GuardrailResult(False, "input too large")
    lower = text.lower()
    for pattern in banned_patterns:
        if pattern.lower() in lower:
            return GuardrailResult(False, f"input contains banned pattern: {pattern}")
    return GuardrailResult(True, "ok")


def tool_guardrail(*, action: str, allowed_actions: tuple[str, ...], requires_approval: bool) -> GuardrailResult:
    if action not in set(allowed_actions):
        return GuardrailResult(False, f"action not allowed: {action}")
    if requires_approval:
        return GuardrailResult(False, "approval required")
    return GuardrailResult(True, "ok")


def output_guardrail(*, payload: dict[str, object], required_keys: tuple[str, ...]) -> GuardrailResult:
    missing = [k for k in required_keys if k not in payload]
    if missing:
        return GuardrailResult(False, f"missing required fields: {','.join(missing)}")
    return GuardrailResult(True, "ok")


def filter_credentials(*, text: str, secret_markers: tuple[str, ...] = ("api_key", "secret", "token", "password")) -> str:
    out = text
    for marker in secret_markers:
        out = out.replace(marker, "[REDACTED]")
        out = out.replace(marker.upper(), "[REDACTED]")
    return out
