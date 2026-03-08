from datetime import datetime, timedelta, timezone

from agents.evolution.autoresearch import AutoResearchPolicy, AutoResearchRunner, load_program_policy


def test_load_program_policy_parses_markdown_bullets(tmp_path):
    program = tmp_path / "program.md"
    program.write_text(
        "\n".join(
            [
                "# Program",
                "- max_runtime_minutes: 7",
                "- max_experiments: 4",
                "- generations_per_experiment: 5",
                "- mutation_step: 0.11",
                "- min_score_improvement: 0.03",
                "- keep_top_k: 2",
            ]
        ),
        encoding="utf-8",
    )

    policy = load_program_policy(program)

    assert policy.max_runtime_minutes == 7
    assert policy.max_experiments == 4
    assert policy.generations_per_experiment == 5
    assert policy.mutation_step == 0.11
    assert policy.min_score_improvement == 0.03
    assert policy.keep_top_k == 2


def test_autoresearch_discards_when_improvement_is_below_threshold():
    policy = AutoResearchPolicy(max_runtime_minutes=10, max_experiments=2, min_score_improvement=0.1)
    runner = AutoResearchRunner(
        score_fn=lambda p: 1.62 - p.get("slippage", 0.0),
        base_params={"alpha": 1.0, "beta": 2.0},
        policy=policy,
    )

    report = runner.run(incumbent_score=1.6)

    assert report.experiments_run >= 1
    assert len(report.kept) == 0
    assert len(report.discarded) >= 1
    assert report.final_incumbent_score == 1.6


def test_autoresearch_keeps_and_updates_incumbent():
    policy = AutoResearchPolicy(max_runtime_minutes=10, max_experiments=2, min_score_improvement=0.01, keep_top_k=1)
    runner = AutoResearchRunner(
        score_fn=lambda p: 1.7 - abs(p.get("alpha", 1.0) - 1.1) - p.get("slippage", 0.0),
        base_params={"alpha": 1.0, "beta": 2.0},
        policy=policy,
    )

    report = runner.run(incumbent_score=1.6)

    assert len(report.kept) >= 1
    assert report.final_incumbent_score > 1.6
    assert report.kept[0].reason == "promoted"


def test_autoresearch_respects_runtime_timebox():
    policy = AutoResearchPolicy(max_runtime_minutes=1, max_experiments=10)
    runner = AutoResearchRunner(
        score_fn=lambda p: 1.7 - p.get("slippage", 0.0),
        base_params={"alpha": 1.0, "beta": 2.0},
        policy=policy,
    )

    base = datetime(2026, 3, 8, tzinfo=timezone.utc)
    calls = {"n": 0}

    def now_provider() -> datetime:
        calls["n"] += 1
        return base + timedelta(minutes=calls["n"])

    report = runner.run(incumbent_score=1.6, now_provider=now_provider)

    assert report.experiments_run <= 1
