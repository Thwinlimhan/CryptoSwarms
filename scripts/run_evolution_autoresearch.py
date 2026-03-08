import json
import os
from pathlib import Path

from agents.evolution.autoresearch import AutoResearchRunner, load_program_policy


def score_fn(params: dict[str, float]) -> float:
    alpha = float(params.get("alpha", 1.0))
    beta = float(params.get("beta", 1.0))
    slippage = float(params.get("slippage", 0.0))
    return 2.0 - abs(alpha - 1.15) - abs(beta - 2.0) * 0.2 - slippage


def main() -> None:
    default_program = Path(__file__).resolve().parents[1] / "agents" / "evolution" / "program.md"
    program_path = Path(os.getenv("AUTORESEARCH_PROGRAM_PATH", str(default_program)))
    policy = load_program_policy(program_path)

    incumbent_score = float(os.getenv("AUTORESEARCH_INCUMBENT_SCORE", "1.6"))
    base_params = {"alpha": 1.0, "beta": 2.0}

    report = AutoResearchRunner(
        score_fn=score_fn,
        base_params=base_params,
        policy=policy,
        slippage=0.004,
    ).run(incumbent_score=incumbent_score)

    payload = {
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "experiments_run": report.experiments_run,
        "final_incumbent_score": report.final_incumbent_score,
        "kept": [
            {
                "experiment_id": d.experiment_id,
                "best_score": d.best_score,
                "score_improvement": d.score_improvement,
                "reason": d.reason,
                "params": d.candidate.params if d.candidate else None,
            }
            for d in report.kept
        ],
        "discarded": [
            {
                "experiment_id": d.experiment_id,
                "best_score": d.best_score,
                "score_improvement": d.score_improvement,
                "reason": d.reason,
            }
            for d in report.discarded
        ],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
