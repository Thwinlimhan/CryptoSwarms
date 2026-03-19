"""
Sandbox backend factory for DeepAgentEvolver.
Supports Modal (available now), Daytona (available now),
and LangSmith Sandbox (available when preview access granted).

Selection priority:
  1. SANDBOX_PROVIDER=langsmith → LangSmith Sandbox (requires waitlist access)
  2. SANDBOX_PROVIDER=modal     → Modal (GPU support, good for backtesting)
  3. SANDBOX_PROVIDER=daytona   → Daytona (fast cold starts, native git)
  4. SANDBOX_PROVIDER=local     → FilesystemBackend with virtual_mode=True (dev only)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


SANDBOX_IMAGE = os.getenv(
    "SANDBOX_IMAGE",
    "your-registry/cryptoswarms-sandbox:latest",
)
SANDBOX_CPU = int(os.getenv("SANDBOX_CPU", "2"))
SANDBOX_MEMORY_GB = int(os.getenv("SANDBOX_MEMORY_GB", "8"))


def build_sandbox_backend(
    thread_id: str,
    *,
    seed_files: list[tuple[str, bytes]] | None = None,
) -> tuple[Any, Any]:
    """
    Build the appropriate sandbox backend based on SANDBOX_PROVIDER env var.
    Returns a deepagents-compatible BackendProtocol instance and the sandbox handle.

    Args:
        thread_id: LangGraph thread ID; each thread gets its own isolated sandbox.
        seed_files: list of (absolute_path, content_bytes) to upload before agent runs.
                    Include the strategy file being evolved + any config files.
                    NEVER include .env files or credential files.
    """
    provider = os.getenv("SANDBOX_PROVIDER", "modal").lower()

    if provider == "langsmith":
        return _build_langsmith_sandbox(thread_id, seed_files)
    elif provider == "modal":
        return _build_modal_sandbox(thread_id, seed_files)
    elif provider == "daytona":
        return _build_daytona_sandbox(thread_id, seed_files)
    elif provider == "local":
        return _build_local_backend()
    else:
        raise ValueError(
            f"Unknown SANDBOX_PROVIDER={provider!r}. "
            "Valid values: langsmith, modal, daytona, local"
        )


def _build_modal_sandbox(thread_id: str, seed_files: list[tuple[str, bytes]] | None):
    """Modal sandbox — available today. Best for GPU-accelerated backtesting."""
    import modal
    from langchain_modal import ModalSandbox

    app = modal.App.lookup(
        os.getenv("MODAL_APP_NAME", "cryptoswarms-evolution"),
        create_if_missing=True,
    )
    sandbox = modal.Sandbox.create(
        app=app,
        image=modal.Image.from_registry(SANDBOX_IMAGE),
        cpu=SANDBOX_CPU,
        memory=SANDBOX_MEMORY_GB * 1024,
        timeout=3600,  # 1hr max; nightly evolution runs end here
        labels={"thread_id": thread_id, "component": "cryptoswarms-evolution"},
    )
    backend = ModalSandbox(sandbox=sandbox)
    if seed_files:
        backend.upload_files(seed_files)
    return backend, sandbox  # return sandbox for cleanup in finally block


def _build_daytona_sandbox(thread_id: str, seed_files: list[tuple[str, bytes]] | None):
    """Daytona sandbox — available today. Fast cold starts, native git operations."""
    from daytona import Daytona, CreateSandboxFromSnapshotParams
    from langchain_daytona import DaytonaSandbox

    client = Daytona()

    # Get-or-create by thread_id for conversation continuity
    try:
        sandbox = client.find_one(labels={"thread_id": thread_id})
    except Exception:
        sandbox = client.create(CreateSandboxFromSnapshotParams(
            snapshot=SANDBOX_IMAGE,
            labels={"thread_id": thread_id, "component": "cryptoswarms-evolution"},
            auto_delete_interval=7200,  # 2hr TTL
        ))

    backend = DaytonaSandbox(sandbox=sandbox)
    if seed_files:
        backend.upload_files(seed_files)
    return backend, sandbox


def _build_langsmith_sandbox(thread_id: str, seed_files: list[tuple[str, bytes]] | None):
    """
    LangSmith Sandbox — requires Private Preview access.
    """
    raise NotImplementedError(
        "LangSmith Sandboxes requires Private Preview access. "
        "Sign up at: langchain.com/langsmith-sandboxes-waitlist\n"
        "Use SANDBOX_PROVIDER=modal or SANDBOX_PROVIDER=daytona in the meantime."
    )


def _build_local_backend():
    """
    Local FilesystemBackend — DEV ONLY.
    Never use in production: no isolation, strategies run on your host.
    """
    import warnings
    from deepagents.backends import FilesystemBackend
    warnings.warn(
        "Using LOCAL sandbox backend — no isolation! "
        "Strategy code executes on your host machine. "
        "Set SANDBOX_PROVIDER=modal for safe execution.",
        stacklevel=3,
    )
    return FilesystemBackend(root_dir=str(Path.cwd()), virtual_mode=True), None
