import csv
import json

from bab.sim.agents import HeuristicPolicy, RandomPolicy
from bab.sim.diagnostics import (
    compare_policies_by_seed,
    format_seed_diagnostics_summary,
    summarize_seed_diagnostics,
    write_seed_diagnostics_bundle,
)


def test_compare_policies_by_seed_smoke() -> None:
    rows = compare_policies_by_seed(
        {
            "random": lambda seed: RandomPolicy(seed=seed),
            "heuristic": lambda seed: HeuristicPolicy(seed=seed),
        },
        runs=2,
        seed=1,
        max_steps=80,
    )

    assert len(rows) == 2
    assert "seed" in rows[0]
    assert "random_outcome" in rows[0]
    assert "heuristic_outcome" in rows[0]


def test_summarize_seed_diagnostics_smoke() -> None:
    rows = [
        {
            "seed": 1,
            "heuristic_outcome": "win",
            "heuristic_total_reward": 10.0,
            "q_learning_outcome": "defeat",
            "q_learning_total_reward": 3.0,
        },
        {
            "seed": 2,
            "heuristic_outcome": "defeat",
            "heuristic_total_reward": 4.0,
            "q_learning_outcome": "win",
            "q_learning_total_reward": 12.0,
        },
    ]

    summary = summarize_seed_diagnostics(rows)

    assert summary["runs"] == 2
    assert summary["teacher_wins"] == 1
    assert summary["learned_wins"] == 1
    assert summary["teacher_only_wins"] == 1
    assert summary["learned_only_wins"] == 1

    text = format_seed_diagnostics_summary(summary)
    assert "Teacher-only wins" in text
    assert "Learned-only wins" in text


def test_write_seed_diagnostics_bundle(tmp_path) -> None:
    rows = compare_policies_by_seed(
        {
            "random": lambda seed: RandomPolicy(seed=seed),
            "heuristic": lambda seed: HeuristicPolicy(seed=seed),
        },
        runs=1,
        seed=3,
        max_steps=80,
    )

    json_path, csv_path = write_seed_diagnostics_bundle(
        rows,
        tmp_path,
        stem="diagnostics",
        teacher_policy="random",
        learned_policy="heuristic",
    )

    assert json_path.exists()
    assert csv_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert len(payload["rows"]) == 1

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert len(csv_rows) == 1
