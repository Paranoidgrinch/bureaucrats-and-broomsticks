"""Metric export helpers for RL/agent rollouts."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bab.sim.rl_env import RolloutResult

RESULT_FIELDS = (
    "seed",
    "steps",
    "total_reward",
    "outcome",
    "final_act",
    "max_act_seen",
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


def rollout_result_to_dict(result: RolloutResult) -> dict[str, Any]:
    return asdict(result)


def results_to_json_payload(
    results_by_policy: dict[str, list[RolloutResult]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "policies": {
            policy_name: [
                rollout_result_to_dict(result)
                for result in policy_results
            ]
            for policy_name, policy_results in results_by_policy.items()
        },
        "summary": {
            policy_name: summarize_policy_rollouts(policy_results)
            for policy_name, policy_results in results_by_policy.items()
        },
    }


def summarize_policy_rollouts(
    results: list[RolloutResult],
) -> dict[str, Any]:
    if not results:
        return {
            "runs": 0,
            "average_reward": 0.0,
            "average_steps": 0.0,
            "average_final_act": 0.0,
            "average_max_act_seen": 0.0,
            "average_completed_nodes": 0.0,
            "average_fights_won": 0.0,
            "average_damage_dealt": 0.0,
            "average_damage_taken": 0.0,
            "average_first_combat_damage_dealt": 0.0,
            "average_first_combat_damage_taken": 0.0,
            "average_first_combat_turns": 0.0,
            "wins": 0,
            "defeats": 0,
            "stalls": 0,
            "truncated": 0,
            "zero_damage_runs": 0,
            "first_combat_zero_damage_runs": 0,
            "win_rate": 0.0,
            "stall_rate": 0.0,
            "truncated_rate": 0.0,
            "zero_damage_rate": 0.0,
            "first_combat_zero_damage_rate": 0.0,
        }

    runs = len(results)
    wins = sum(1 for result in results if result.outcome == "win")
    defeats = sum(1 for result in results if result.outcome == "defeat")
    stalls = sum(1 for result in results if result.outcome == "stalled")
    truncated = sum(1 for result in results if result.outcome == "truncated")
    zero_damage_runs = sum(1 for result in results if result.damage_dealt <= 0)
    first_combat_zero_damage_runs = sum(
        1 for result in results if result.first_combat_zero_damage
    )

    return {
        "runs": runs,
        "average_reward": sum(result.total_reward for result in results) / runs,
        "average_steps": sum(result.steps for result in results) / runs,
        "average_final_act": sum(result.final_act for result in results) / runs,
        "average_max_act_seen": sum(result.max_act_seen for result in results) / runs,
        "average_completed_nodes": (
            sum(result.completed_nodes for result in results) / runs
        ),
        "average_fights_won": sum(result.fights_won for result in results) / runs,
        "average_damage_dealt": sum(result.damage_dealt for result in results) / runs,
        "average_damage_taken": sum(result.damage_taken for result in results) / runs,
        "average_first_combat_damage_dealt": (
            sum(result.first_combat_damage_dealt for result in results) / runs
        ),
        "average_first_combat_damage_taken": (
            sum(result.first_combat_damage_taken for result in results) / runs
        ),
        "average_first_combat_turns": (
            sum(result.first_combat_turns for result in results) / runs
        ),
        "wins": wins,
        "defeats": defeats,
        "stalls": stalls,
        "truncated": truncated,
        "zero_damage_runs": zero_damage_runs,
        "first_combat_zero_damage_runs": first_combat_zero_damage_runs,
        "win_rate": wins / runs,
        "stall_rate": stalls / runs,
        "truncated_rate": truncated / runs,
        "zero_damage_rate": zero_damage_runs / runs,
        "first_combat_zero_damage_rate": first_combat_zero_damage_runs / runs,
    }


def write_results_json(
    results_by_policy: dict[str, list[RolloutResult]],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = results_to_json_payload(results_by_policy)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def write_results_csv(
    results_by_policy: dict[str, list[RolloutResult]],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ("policy",) + RESULT_FIELDS
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for policy_name, policy_results in results_by_policy.items():
            for result in policy_results:
                row = rollout_result_to_dict(result)
                row["policy"] = policy_name
                writer.writerow(row)
    return output_path


def write_results_bundle(
    results_by_policy: dict[str, list[RolloutResult]],
    output_dir: str | Path,
    *,
    stem: str = "agent_comparison",
) -> tuple[Path, Path]:
    output_directory = Path(output_dir)
    json_path = output_directory / f"{stem}.json"
    csv_path = output_directory / f"{stem}.csv"
    return (
        write_results_json(results_by_policy, json_path),
        write_results_csv(results_by_policy, csv_path),
    )
