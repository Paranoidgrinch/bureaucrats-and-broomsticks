import csv
import json

from bab.sim.agents import HeuristicPolicy, RandomPolicy
from bab.sim.benchmark import (
    aggregate_benchmark_rows,
    benchmark_policies_across_characters,
    format_benchmark_summary,
    write_benchmark_bundle,
)


def test_benchmark_policies_across_characters_smoke() -> None:
    rows = benchmark_policies_across_characters(
        {
            "random": lambda seed: RandomPolicy(seed=seed),
            "heuristic": lambda seed: HeuristicPolicy(seed=seed),
        },
        character_ids=["hedge_witch"],
        runs_per_character=1,
        seed=1,
        max_steps=80,
    )

    assert len(rows) == 2
    assert {row["policy"] for row in rows} == {"random", "heuristic"}
    assert rows[0]["character_id"] == "hedge_witch"


def test_aggregate_benchmark_rows_contains_overall_and_character() -> None:
    rows = [
        {
            "policy": "random",
            "character_id": "hedge_witch",
            "seed": 1,
            "outcome": "defeat",
            "total_reward": 1.0,
            "steps": 10,
            "completed_nodes": 2,
            "fights_won": 1,
            "gold": 20,
            "deck_size": 10,
            "relic_count": 0,
        },
        {
            "policy": "random",
            "character_id": "hedge_witch",
            "seed": 2,
            "outcome": "win",
            "total_reward": 100.0,
            "steps": 20,
            "completed_nodes": 10,
            "fights_won": 8,
            "gold": 200,
            "deck_size": 15,
            "relic_count": 2,
        },
    ]

    summaries = aggregate_benchmark_rows(rows)

    assert any(summary["character_id"] == "hedge_witch" for summary in summaries)
    assert any(summary["character_id"] == "__overall__" for summary in summaries)
    assert any(summary["wins"] == 1 for summary in summaries)

    text = format_benchmark_summary(rows)
    assert "Agent Benchmark Summary" in text
    assert "win_rate" in text


def test_write_benchmark_bundle(tmp_path) -> None:
    rows = benchmark_policies_across_characters(
        {
            "random": lambda seed: RandomPolicy(seed=seed),
        },
        character_ids=["hedge_witch"],
        runs_per_character=1,
        seed=3,
        max_steps=80,
    )

    json_path, csv_path, summary_path = write_benchmark_bundle(
        rows,
        tmp_path,
        stem="benchmark",
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert summary_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["rows"]

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert csv_rows

    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert summary_rows
