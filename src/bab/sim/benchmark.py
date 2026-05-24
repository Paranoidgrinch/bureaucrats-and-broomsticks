"""Benchmark helpers for evaluating agents across characters.

This is intended for balance diagnostics, not final balancing by itself.
It evaluates multiple policies across fixed seeds and one or more character
classes, then exports flat rows plus aggregate summaries.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
from typing import Any, Callable

from bab.content.catalog import load_default_content_catalog
from bab.sim.agents import Policy, run_policy_rollout


PolicyFactory = Callable[[int], Policy]


ROW_FIELDS = (
    "policy",
    "character_id",
    "seed",
    "outcome",
    "total_reward",
    "steps",
    "completed_nodes",
    "fights_won",
    "gold",
    "deck_size",
    "relic_count",
    "damage_dealt",
    "damage_taken",
)


def benchmark_policies_across_characters(
    policy_factories: dict[str, PolicyFactory],
    *,
    character_ids: list[str] | None = None,
    runs_per_character: int = 100,
    seed: int = 20_001,
    max_steps: int = 800,
) -> list[dict[str, Any]]:
    if character_ids is None:
        catalog = load_default_content_catalog()
        character_ids = sorted(catalog.character_classes)

    rows: list[dict[str, Any]] = []

    for character_index, character_id in enumerate(character_ids):
        character_seed_base = seed + character_index * 100_000

        for run_index in range(runs_per_character):
            run_seed = character_seed_base + run_index

            for policy_name, factory in policy_factories.items():
                policy = factory(run_seed)
                result = run_policy_rollout(
                    policy,
                    seed=run_seed,
                    max_steps=max_steps,
                    character_id=character_id,
                )

                rows.append(
                    {
                        "policy": policy_name,
                        "character_id": character_id,
                        "seed": run_seed,
                        "outcome": result.outcome,
                        "total_reward": result.total_reward,
                        "steps": result.steps,
                        "completed_nodes": result.completed_nodes,
                        "fights_won": result.fights_won,
                        "gold": result.gold,
                        "deck_size": result.deck_size,
                        "relic_count": result.relic_count,
                        "damage_dealt": result.damage_dealt,
                        "damage_taken": result.damage_taken,
                    }
                )

    return rows


def aggregate_benchmark_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        groups[(str(row["policy"]), str(row["character_id"]))].append(row)
        groups[(str(row["policy"]), "__overall__")].append(row)

    summaries: list[dict[str, Any]] = []
    for (policy, character_id), group_rows in sorted(groups.items()):
        summaries.append(summarize_group(policy, character_id, group_rows))

    return summaries


def summarize_group(
    policy: str,
    character_id: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    runs = len(rows)
    if runs == 0:
        return {
            "policy": policy,
            "character_id": character_id,
            "runs": 0,
        }

    return {
        "policy": policy,
        "character_id": character_id,
        "runs": runs,
        "wins": count_outcome(rows, "win"),
        "defeats": count_outcome(rows, "defeat"),
        "stalls": count_outcome(rows, "stalled"),
        "truncated": count_outcome(rows, "truncated"),
        "win_rate": count_outcome(rows, "win") / runs,
        "average_reward": average(rows, "total_reward"),
        "average_steps": average(rows, "steps"),
        "average_completed_nodes": average(rows, "completed_nodes"),
        "average_fights_won": average(rows, "fights_won"),
        "average_gold": average(rows, "gold"),
        "average_deck_size": average(rows, "deck_size"),
        "average_relic_count": average(rows, "relic_count"),
        "average_damage_dealt": average(rows, "damage_dealt"),
        "average_damage_taken": average(rows, "damage_taken"),
    }


def count_outcome(rows: list[dict[str, Any]], outcome: str) -> int:
    return sum(1 for row in rows if row.get("outcome") == outcome)


def average(rows: list[dict[str, Any]], key: str) -> float:
    return sum(float(row.get(key, 0.0)) for row in rows) / len(rows)


def benchmark_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rows": rows,
        "summary": aggregate_benchmark_rows(rows),
    }


def write_benchmark_json(
    rows: list[dict[str, Any]],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(benchmark_payload(rows), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def write_benchmark_csv(
    rows: list[dict[str, Any]],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def write_benchmark_summary_csv(
    rows: list[dict[str, Any]],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summaries = aggregate_benchmark_rows(rows)
    fieldnames = collect_summary_fields(summaries)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)

    return output_path


def write_benchmark_bundle(
    rows: list[dict[str, Any]],
    output_dir: str | Path,
    *,
    stem: str = "agent_benchmark",
) -> tuple[Path, Path, Path]:
    output_directory = Path(output_dir)
    return (
        write_benchmark_json(rows, output_directory / f"{stem}.json"),
        write_benchmark_csv(rows, output_directory / f"{stem}.csv"),
        write_benchmark_summary_csv(rows, output_directory / f"{stem}_summary.csv"),
    )


def format_benchmark_summary(rows: list[dict[str, Any]]) -> str:
    summaries = aggregate_benchmark_rows(rows)
    overall = [
        summary for summary in summaries
        if summary["character_id"] == "__overall__"
    ]
    per_character = [
        summary for summary in summaries
        if summary["character_id"] != "__overall__"
    ]

    lines = ["=== Agent Benchmark Summary ==="]

    if overall:
        lines.append("")
        lines.append("Overall:")
        for summary in sorted(overall, key=lambda item: item["policy"]):
            lines.append(format_summary_line(summary))

    if per_character:
        lines.append("")
        lines.append("By character:")
        for summary in sorted(
            per_character,
            key=lambda item: (item["character_id"], item["policy"]),
        ):
            lines.append(format_summary_line(summary))

    return "\n".join(lines)


def format_summary_line(summary: dict[str, Any]) -> str:
    return (
        f"{summary['policy']} | {summary['character_id']} | "
        f"runs {summary['runs']} | "
        f"wins {summary['wins']} | "
        f"win_rate {summary['win_rate']:.1%} | "
        f"avg_reward {summary['average_reward']:.2f} | "
        f"avg_nodes {summary['average_completed_nodes']:.2f} | "
        f"avg_fights {summary['average_fights_won']:.2f} | "
        f"avg_dmg_dealt {summary.get('average_damage_dealt', 0.0):.1f} | "
        f"avg_dmg_taken {summary.get('average_damage_taken', 0.0):.1f}"
    )


def collect_summary_fields(summaries: list[dict[str, Any]]) -> list[str]:
    if not summaries:
        return ["policy", "character_id"]

    fields: list[str] = []
    for summary in summaries:
        for key in summary:
            if key not in fields:
                fields.append(key)
    return fields
