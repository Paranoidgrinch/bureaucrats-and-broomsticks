"""Seed-by-seed diagnostics for policy comparison.

Aggregate win rates are useful, but for improving agents we need to know which
exact seeds differ between policies. This module compares policies on identical
environment seeds and writes a flat CSV/JSON table for inspection.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable

from bab.sim.agents import Policy, run_policy_rollout
from bab.sim.rl_env import RolloutResult

PolicyFactory = Callable[[int], Policy]

RESULT_FIELDS = (
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
    "first_combat_damage_dealt",
    "first_combat_damage_taken",
    "first_combat_turns",
    "first_combat_zero_damage",
)


def compare_policies_by_seed(
    policy_factories: dict[str, PolicyFactory],
    *,
    runs: int = 100,
    seed: int = 10_001,
    max_steps: int = 1000,
    character_id: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(runs):
        run_seed = seed + index
        row: dict[str, Any] = {"seed": run_seed}
        for policy_name, factory in policy_factories.items():
            policy = factory(run_seed)
            result = run_policy_rollout(
                policy,
                seed=run_seed,
                max_steps=max_steps,
                character_id=character_id,
            )
            _add_result_to_row(row, policy_name, result)
        rows.append(row)
    return rows


def summarize_seed_diagnostics(
    rows: list[dict[str, Any]],
    *,
    teacher_policy: str = "heuristic",
    learned_policy: str = "q_learning",
) -> dict[str, Any]:
    if not rows:
        return {
            "runs": 0,
            "teacher_policy": teacher_policy,
            "learned_policy": learned_policy,
        }

    teacher_outcome_key = f"{teacher_policy}_outcome"
    learned_outcome_key = f"{learned_policy}_outcome"
    teacher_reward_key = f"{teacher_policy}_total_reward"
    learned_reward_key = f"{learned_policy}_total_reward"
    learned_damage_key = f"{learned_policy}_damage_dealt"
    learned_first_zero_key = f"{learned_policy}_first_combat_zero_damage"

    teacher_wins = [
        row for row in rows if row.get(teacher_outcome_key) == "win"
    ]
    learned_wins = [
        row for row in rows if row.get(learned_outcome_key) == "win"
    ]
    both_win = [
        row for row in rows
        if row.get(teacher_outcome_key) == "win"
        and row.get(learned_outcome_key) == "win"
    ]
    teacher_only_wins = [
        row for row in rows
        if row.get(teacher_outcome_key) == "win"
        and row.get(learned_outcome_key) != "win"
    ]
    learned_only_wins = [
        row for row in rows
        if row.get(teacher_outcome_key) != "win"
        and row.get(learned_outcome_key) == "win"
    ]
    both_defeat = [
        row for row in rows
        if row.get(teacher_outcome_key) == "defeat"
        and row.get(learned_outcome_key) == "defeat"
    ]
    learned_stalls = [row for row in rows if row.get(learned_outcome_key) == "stalled"]
    learned_truncated = [row for row in rows if row.get(learned_outcome_key) == "truncated"]
    learned_zero_damage = [
        row for row in rows if float(row.get(learned_damage_key, 0.0) or 0.0) <= 0.0
    ]
    learned_first_combat_zero_damage = [
        row for row in rows if _truthy(row.get(learned_first_zero_key))
    ]

    reward_deltas = [
        float(row.get(learned_reward_key, 0.0))
        - float(row.get(teacher_reward_key, 0.0))
        for row in rows
    ]
    sorted_by_delta = sorted(
        rows,
        key=lambda row: (
            float(row.get(learned_reward_key, 0.0))
            - float(row.get(teacher_reward_key, 0.0))
        ),
    )

    return {
        "runs": len(rows),
        "teacher_policy": teacher_policy,
        "learned_policy": learned_policy,
        "teacher_wins": len(teacher_wins),
        "learned_wins": len(learned_wins),
        "both_win": len(both_win),
        "teacher_only_wins": len(teacher_only_wins),
        "learned_only_wins": len(learned_only_wins),
        "both_defeat": len(both_defeat),
        "learned_stalls": len(learned_stalls),
        "learned_truncated": len(learned_truncated),
        "learned_zero_damage_runs": len(learned_zero_damage),
        "learned_first_combat_zero_damage_runs": len(learned_first_combat_zero_damage),
        "learned_stall_rate": len(learned_stalls) / len(rows),
        "learned_truncated_rate": len(learned_truncated) / len(rows),
        "learned_zero_damage_rate": len(learned_zero_damage) / len(rows),
        "learned_first_combat_zero_damage_rate": (
            len(learned_first_combat_zero_damage) / len(rows)
        ),
        "average_reward_delta_learned_minus_teacher": (
            sum(reward_deltas) / len(reward_deltas)
        ),
        "best_learned_delta_seeds": [
            _seed_delta_entry(row, teacher_reward_key, learned_reward_key)
            for row in reversed(sorted_by_delta[-10:])
        ],
        "worst_learned_delta_seeds": [
            _seed_delta_entry(row, teacher_reward_key, learned_reward_key)
            for row in sorted_by_delta[:10]
        ],
        "teacher_only_win_seeds": [int(row["seed"]) for row in teacher_only_wins],
        "learned_only_win_seeds": [int(row["seed"]) for row in learned_only_wins],
        "learned_stall_seeds": [int(row["seed"]) for row in learned_stalls],
        "learned_truncated_seeds": [int(row["seed"]) for row in learned_truncated],
        "learned_zero_damage_seeds": [int(row["seed"]) for row in learned_zero_damage],
        "learned_first_combat_zero_damage_seeds": [
            int(row["seed"]) for row in learned_first_combat_zero_damage
        ],
    }


def write_seed_diagnostics_json(
    rows: list[dict[str, Any]],
    path: str | Path,
    *,
    teacher_policy: str = "heuristic",
    learned_policy: str = "q_learning",
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "summary": summarize_seed_diagnostics(
            rows,
            teacher_policy=teacher_policy,
            learned_policy=learned_policy,
        ),
        "rows": rows,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def write_seed_diagnostics_csv(
    rows: list[dict[str, Any]],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _collect_fieldnames(rows)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def write_seed_diagnostics_bundle(
    rows: list[dict[str, Any]],
    output_dir: str | Path,
    *,
    stem: str = "seed_diagnostics",
    teacher_policy: str = "heuristic",
    learned_policy: str = "q_learning",
) -> tuple[Path, Path]:
    output_directory = Path(output_dir)
    json_path = output_directory / f"{stem}.json"
    csv_path = output_directory / f"{stem}.csv"
    return (
        write_seed_diagnostics_json(
            rows,
            json_path,
            teacher_policy=teacher_policy,
            learned_policy=learned_policy,
        ),
        write_seed_diagnostics_csv(rows, csv_path),
    )


def format_seed_diagnostics_summary(summary: dict[str, Any]) -> str:
    lines = [
        "=== Seed-by-Seed Diagnostics ===",
        f"Runs: {summary.get('runs', 0)}",
        f"Teacher policy: {summary.get('teacher_policy')}",
        f"Learned policy: {summary.get('learned_policy')}",
        "",
        "=== Outcome overlap ===",
        f"Teacher wins: {summary.get('teacher_wins', 0)}",
        f"Learned wins: {summary.get('learned_wins', 0)}",
        f"Both win: {summary.get('both_win', 0)}",
        f"Teacher-only wins: {summary.get('teacher_only_wins', 0)}",
        f"Learned-only wins: {summary.get('learned_only_wins', 0)}",
        f"Both defeat: {summary.get('both_defeat', 0)}",
        "",
        "=== Learned policy health ===",
        f"Stalls: {summary.get('learned_stalls', 0)} "
        f"({summary.get('learned_stall_rate', 0.0):.1%})",
        f"Truncated: {summary.get('learned_truncated', 0)} "
        f"({summary.get('learned_truncated_rate', 0.0):.1%})",
        f"Zero-damage runs: {summary.get('learned_zero_damage_runs', 0)} "
        f"({summary.get('learned_zero_damage_rate', 0.0):.1%})",
        "First-combat zero-damage runs: "
        f"{summary.get('learned_first_combat_zero_damage_runs', 0)} "
        f"({summary.get('learned_first_combat_zero_damage_rate', 0.0):.1%})",
        "",
        "=== Reward delta ===",
        (
            "Average learned minus teacher reward: "
            f"{summary.get('average_reward_delta_learned_minus_teacher', 0.0):.2f}"
        ),
    ]

    teacher_only = summary.get("teacher_only_win_seeds", [])
    learned_only = summary.get("learned_only_win_seeds", [])
    stall_seeds = summary.get("learned_stall_seeds", [])
    first_zero = summary.get("learned_first_combat_zero_damage_seeds", [])

    lines.append("")
    lines.append("Teacher-only win seeds:")
    lines.append(", ".join(str(seed) for seed in teacher_only[:20]) or "-")
    lines.append("")
    lines.append("Learned-only win seeds:")
    lines.append(", ".join(str(seed) for seed in learned_only[:20]) or "-")
    lines.append("")
    lines.append("Learned stall seeds:")
    lines.append(", ".join(str(seed) for seed in stall_seeds[:20]) or "-")
    lines.append("")
    lines.append("Learned first-combat zero-damage seeds:")
    lines.append(", ".join(str(seed) for seed in first_zero[:20]) or "-")
    return "\n".join(lines)


def _add_result_to_row(
    row: dict[str, Any],
    policy_name: str,
    result: RolloutResult,
) -> None:
    row[f"{policy_name}_outcome"] = result.outcome
    row[f"{policy_name}_total_reward"] = result.total_reward
    row[f"{policy_name}_steps"] = result.steps
    row[f"{policy_name}_completed_nodes"] = result.completed_nodes
    row[f"{policy_name}_fights_won"] = result.fights_won
    row[f"{policy_name}_gold"] = result.gold
    row[f"{policy_name}_deck_size"] = result.deck_size
    row[f"{policy_name}_relic_count"] = result.relic_count
    row[f"{policy_name}_damage_dealt"] = result.damage_dealt
    row[f"{policy_name}_damage_taken"] = result.damage_taken
    row[f"{policy_name}_first_combat_damage_dealt"] = result.first_combat_damage_dealt
    row[f"{policy_name}_first_combat_damage_taken"] = result.first_combat_damage_taken
    row[f"{policy_name}_first_combat_turns"] = result.first_combat_turns
    row[f"{policy_name}_first_combat_zero_damage"] = result.first_combat_zero_damage


def _seed_delta_entry(
    row: dict[str, Any],
    teacher_reward_key: str,
    learned_reward_key: str,
) -> dict[str, Any]:
    teacher_reward = float(row.get(teacher_reward_key, 0.0))
    learned_reward = float(row.get(learned_reward_key, 0.0))
    return {
        "seed": int(row["seed"]),
        "delta": learned_reward - teacher_reward,
        "teacher_reward": teacher_reward,
        "learned_reward": learned_reward,
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["seed"]
    fieldnames: list[str] = ["seed"]
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames
