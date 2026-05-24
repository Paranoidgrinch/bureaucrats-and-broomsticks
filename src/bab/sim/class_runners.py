"""Train one specialist runner per character class.

The global Q-learning agent is useful as a proof of concept, but each character
has different HP, starter cards, relics, reward pools, and risk profile. For
balance diagnostics we want a specialist runner per class that approximates a
competent player for that class.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import json
from pathlib import Path
from typing import Any

from bab.content.catalog import load_default_content_catalog
from bab.sim.agents import HeuristicPolicy, RandomPolicy, compare_policies
from bab.sim.benchmark import write_benchmark_bundle
from bab.sim.metrics import summarize_policy_rollouts, write_results_bundle
from bab.sim.q_learning import QLearningConfig, train_q_learning_agent
from bab.sim.rl_env import RolloutResult


def default_character_ids() -> list[str]:
    catalog = load_default_content_catalog()
    return sorted(catalog.character_classes)


def train_class_runner(
    *,
    character_id: str,
    output_dir: str | Path,
    seed: int = 1,
    imitation_episodes: int = 300,
    episodes: int = 800,
    eval_runs: int = 50,
    max_steps: int = 800,
    config: QLearningConfig | None = None,
    use_heuristic_guidance: bool = True,
) -> dict[str, Any]:
    output_directory = Path(output_dir)
    character_dir = output_directory / character_id
    character_dir.mkdir(parents=True, exist_ok=True)

    training = train_q_learning_agent(
        episodes=episodes,
        imitation_episodes=imitation_episodes,
        seed=seed,
        max_steps=max_steps,
        character_id=character_id,
        config=config,
        use_heuristic_guidance=use_heuristic_guidance,
    )

    model_path = training.policy.save(character_dir / "q_learning_agent.json")

    training_results: dict[str, list[RolloutResult]] = {}
    if training.imitation_results:
        training_results["q_learning_imitation"] = training.imitation_results
    training_results["q_learning_train"] = training.episode_results

    training_json, training_csv = write_results_bundle(
        training_results,
        character_dir,
        stem="training",
    )

    evaluation = compare_policies(
        [
            RandomPolicy(seed=seed),
            HeuristicPolicy(seed=seed),
            training.policy,
        ],
        runs=eval_runs,
        seed=seed + 10_000,
        max_steps=max_steps,
        character_id=character_id,
    )

    evaluation_json, evaluation_csv = write_results_bundle(
        evaluation,
        character_dir,
        stem="evaluation",
    )

    benchmark_rows = rollout_results_to_benchmark_rows(
        evaluation,
        character_id=character_id,
    )

    result = {
        "character_id": character_id,
        "seed": seed,
        "imitation_episodes": imitation_episodes,
        "episodes": episodes,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "q_table_entries": len(training.policy.q_table),
        "model_path": str(model_path),
        "training_json": str(training_json),
        "training_csv": str(training_csv),
        "evaluation_json": str(evaluation_json),
        "evaluation_csv": str(evaluation_csv),
        "evaluation_summary": {
            policy_name: summarize_policy_rollouts(policy_results)
            for policy_name, policy_results in evaluation.items()
        },
        "benchmark_rows": benchmark_rows,
    }

    write_character_manifest(result, character_dir / "class_runner_manifest.json")
    return result


def train_class_runners_for_characters(
    *,
    character_ids: list[str] | None = None,
    output_dir: str | Path,
    seed: int = 1,
    imitation_episodes: int = 300,
    episodes: int = 800,
    eval_runs: int = 50,
    max_steps: int = 800,
    config: QLearningConfig | None = None,
    use_heuristic_guidance: bool = True,
    skip_existing: bool = False,
    workers: int | None = None,
) -> dict[str, Any]:
    if character_ids is None:
        character_ids = default_character_ids()

    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    worker_count = resolve_worker_count(workers, len(character_ids))

    if worker_count <= 1:
        character_results = []
        for index, character_id in enumerate(character_ids):
            character_results.append(
                _train_class_runner_task(
                    {
                        "character_id": character_id,
                        "output_dir": str(output_directory),
                        "seed": seed + index * 100_000,
                        "imitation_episodes": imitation_episodes,
                        "episodes": episodes,
                        "eval_runs": eval_runs,
                        "max_steps": max_steps,
                        "config": config,
                        "use_heuristic_guidance": use_heuristic_guidance,
                        "skip_existing": skip_existing,
                    }
                )
            )
    else:
        tasks = [
            {
                "character_id": character_id,
                "output_dir": str(output_directory),
                "seed": seed + index * 100_000,
                "imitation_episodes": imitation_episodes,
                "episodes": episodes,
                "eval_runs": eval_runs,
                "max_steps": max_steps,
                "config": config,
                "use_heuristic_guidance": use_heuristic_guidance,
                "skip_existing": skip_existing,
            }
            for index, character_id in enumerate(character_ids)
        ]

        character_results_by_id: dict[str, dict[str, Any]] = {}
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(_train_class_runner_task, task)
                for task in tasks
            ]
            for future in as_completed(futures):
                result = future.result()
                character_results_by_id[result["character_id"]] = result

        character_results = [
            character_results_by_id[character_id]
            for character_id in character_ids
        ]

    benchmark_rows: list[dict[str, Any]] = []
    for result in character_results:
        benchmark_rows.extend(result.get("benchmark_rows", []))

    benchmark_json, benchmark_csv, benchmark_summary_csv = write_benchmark_bundle(
        benchmark_rows,
        output_directory,
        stem="class_runners_benchmark",
    )

    manifest = {
        "schema_version": 1,
        "character_ids": character_ids,
        "seed": seed,
        "imitation_episodes": imitation_episodes,
        "episodes": episodes,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "use_heuristic_guidance": use_heuristic_guidance,
        "workers": worker_count,
        "characters": [
            strip_large_fields(result)
            for result in character_results
        ],
        "benchmark_json": str(benchmark_json),
        "benchmark_csv": str(benchmark_csv),
        "benchmark_summary_csv": str(benchmark_summary_csv),
    }

    manifest_path = output_directory / "class_runners_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "benchmark_rows": benchmark_rows,
        "benchmark_json": benchmark_json,
        "benchmark_csv": benchmark_csv,
        "benchmark_summary_csv": benchmark_summary_csv,
    }


def rollout_results_to_benchmark_rows(
    results_by_policy: dict[str, list[RolloutResult]],
    *,
    character_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for policy_name, policy_results in results_by_policy.items():
        for result in policy_results:
            rows.append(
                {
                    "policy": policy_name,
                    "character_id": character_id,
                    "seed": result.seed,
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


def write_character_manifest(
    result: dict[str, Any],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(strip_large_fields(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def strip_large_fields(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key != "benchmark_rows"
    }


def format_class_runner_summary(result: dict[str, Any]) -> str:
    lines = [
        f"Character: {result['character_id']}",
        f"Q-table entries: {result['q_table_entries']}",
    ]

    for policy_name, summary in result["evaluation_summary"].items():
        runs = summary["runs"]
        wins = summary["wins"]
        win_rate = wins / runs if runs else 0.0
        lines.append(
            f"  {policy_name}: wins {wins}/{runs} "
            f"({win_rate:.1%}), avg_reward {summary['average_reward']:.2f}, "
            f"avg_nodes {summary['average_completed_nodes']:.2f}"
        )

    return "\n".join(lines)


def format_class_runners_overview(results: list[dict[str, Any]]) -> str:
    lines = ["=== Class Runner Training Summary ==="]

    for result in results:
        lines.append("")
        lines.append(format_class_runner_summary(result))

    return "\n".join(lines)


def resolve_worker_count(
    workers: int | None,
    task_count: int,
) -> int:
    if task_count <= 0:
        return 1

    if workers is None or workers <= 0:
        cpu_count = os.cpu_count() or 1
        return max(1, min(cpu_count, task_count))

    return max(1, min(workers, task_count))


def _train_class_runner_task(task: dict[str, Any]) -> dict[str, Any]:
    character_id = task["character_id"]
    output_dir = Path(task["output_dir"])
    manifest_path = output_dir / character_id / "class_runner_manifest.json"

    if task["skip_existing"] and manifest_path.exists():
        result = json.loads(manifest_path.read_text(encoding="utf-8"))
        benchmark_rows = result.get("benchmark_rows")
        if benchmark_rows is None:
            # Old manifests intentionally omit the large benchmark rows, so if
            # skip_existing is used with such a manifest, regenerate the run.
            pass
        else:
            return result

    return train_class_runner(
        character_id=character_id,
        output_dir=output_dir,
        seed=task["seed"],
        imitation_episodes=task["imitation_episodes"],
        episodes=task["episodes"],
        eval_runs=task["eval_runs"],
        max_steps=task["max_steps"],
        config=task["config"],
        use_heuristic_guidance=task["use_heuristic_guidance"],
    )
