from __future__ import annotations

import json
from typing import Protocol

from .models import GateResult


class DBConnection(Protocol):
    def cursor(self): ...

    def commit(self) -> None: ...


def ensure_validations_table(connection: DBConnection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS validations (
            id BIGSERIAL PRIMARY KEY,
            run_id TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            gate_number INTEGER NOT NULL,
            gate_name TEXT NOT NULL,
            status TEXT NOT NULL,
            score DOUBLE PRECISION,
            details JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    connection.commit()


def persist_gate_result(connection: DBConnection, run_id: str, strategy_id: str, result: GateResult) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO validations (
            run_id,
            strategy_id,
            gate_number,
            gate_name,
            status,
            score,
            details,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        """,
        (
            run_id,
            strategy_id,
            result.gate_number,
            result.gate_name,
            result.status.value,
            result.score,
            json.dumps(result.details),
            result.created_at,
        ),
    )
    connection.commit()
