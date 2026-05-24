import csv
import json

from bab.sim.agents import HeuristicPolicy, RandomPolicy, compare_policies
from bab.sim.metrics import (
    results_to_json_payload,
    summarize_policy_rollouts,
    write_results_bundle,
    write_results_csv,
    write_results_json,
)


def test_summarize_policy_rollouts_handles_empty_results() -> None:
    summary = summarize_policy_rollouts([])

    assert summary["runs"] == 0
    assert summary["average_reward"] == 0.0
    assert summary["wins"] == 0


def test_results_to_json_payload_contains_policies_and_summary() -> None:
    results = compare_policies(
        [RandomPolicy(seed=1), HeuristicPolicy(seed=1)],
        runs=1,
        seed=1,
        max_steps=80,
    )

    payload = results_to_json_payload(results)

    assert payload["schema_version"] == 1
    assert set(payload["policies"]) == {"random", "heuristic"}
    assert set(payload["summary"]) == {"random", "heuristic"}
    assert payload["summary"]["random"]["runs"] == 1
    assert payload["summary"]["heuristic"]["runs"] == 1


def test_write_results_json(tmp_path) -> None:
    results = compare_policies(
        [RandomPolicy(seed=2)],
        runs=1,
        seed=2,
        max_steps=80,
    )

    output_path = write_results_json(results, tmp_path / "results.json")

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert "random" in payload["policies"]
    assert len(payload["policies"]["random"]) == 1


def test_write_results_csv(tmp_path) -> None:
    results = compare_policies(
        [HeuristicPolicy(seed=3)],
        runs=1,
        seed=3,
        max_steps=80,
    )

    output_path = write_results_csv(results, tmp_path / "results.csv")

    assert output_path.exists()
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["policy"] == "heuristic"
    assert rows[0]["outcome"] in {"win", "defeat", "stalled", "truncated"}


def test_write_results_bundle(tmp_path) -> None:
    results = compare_policies(
        [RandomPolicy(seed=4), HeuristicPolicy(seed=4)],
        runs=1,
        seed=4,
        max_steps=80,
    )

    json_path, csv_path = write_results_bundle(
        results,
        tmp_path,
        stem="test_bundle",
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert json_path.name == "test_bundle.json"
    assert csv_path.name == "test_bundle.csv"
