"""Continue training existing class-specific Q runners.

This is the core workflow for the intended "good player" per class:
- load a saved per-character Q-learning model
- force the environment to that character
- let the model play more episodes
- update from rewards
- save an improved model
- evaluate against Random and Heuristic for that same class
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import json
from pathlib import Path
from typing import Any

from bab.sim.agents import HeuristicPolicy, RandomPolicy, compare_policies
from bab.sim.metrics import summarize_policy_rollouts, write_results_bundle
from bab.sim.q_learning import QLearningPolicy, epsilon_for_episode
from bab.sim.rl_env import RoguelikeEnv, RolloutResult


def continue_training_class_runner(
    *,
    character_id: str,
    model_path: str | Path,
    output_dir: str | Path,
    seed: int = 1,
    episodes: int = 800,
    eval_runs: int = 50,
    max_steps: int = 800,
) -> dict[str, Any]:
    model_path = Path(model_path)
    output_directory = Path(output_dir)
    character_dir = output_directory / character_id
    character_dir.mkdir(parents=True, exist_ok=True)

    policy = QLearningPolicy.load(model_path, seed=seed)
    training_results = continue_training_policy(
        policy,
        character_id=character_id,
        seed=seed,
        episodes=episodes,
        max_steps=max_steps,
    )

    improved_model_path = policy.save(character_dir / "q_learning_agent.json")

    training_json, training_csv = write_results_bundle(
        {"q_learning_continue_train": training_results},
        character_dir,
        stem="continued_training",
    )

    evaluation = compare_policies(
        [
            RandomPolicy(seed=seed),
            HeuristicPolicy(seed=seed),
            policy,
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

    result = {
        "character_id": character_id,
        "source_model_path": str(model_path),
        "model_path": str(improved_model_path),
        "seed": seed,
        "episodes": episodes,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "q_table_entries": len(policy.q_table),
        "training_json": str(training_json),
        "training_csv": str(training_csv),
        "evaluation_json": str(evaluation_json),
        "evaluation_csv": str(evaluation_csv),
        "evaluation_summary": {
            policy_name: summarize_policy_rollouts(policy_results)
            for policy_name, policy_results in evaluation.items()
        },
    }

    manifest_path = character_dir / "improved_runner_manifest.json"
    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    result["manifest_path"] = str(manifest_path)
    return result


def continue_training_policy(
    policy: QLearningPolicy,
    *,
    character_id: str,
    seed: int = 1,
    episodes: int = 800,
    max_steps: int = 800,
) -> list[RolloutResult]:
    results: list[RolloutResult] = []

    for episode_index in range(episodes):
        episode_seed = seed + episode_index
        epsilon = epsilon_for_episode(episode_index, policy.config)

        env = RoguelikeEnv(seed=episode_seed)
        observation = env.reset(seed=episode_seed, character_id=character_id)

        total_reward = 0.0
        steps = 0

        for step_index in range(max_steps):
            if observation.done:
                break

            action = policy.choose_action(
                observation,
                epsilon=epsilon,
                explore=True,
            )
            result = env.step(action)
            policy.update(
                observation,
                action,
                result.reward,
                result.observation,
                result.done,
            )

            observation = result.observation
            total_reward += result.reward
            steps = step_index + 1

        if not observation.done:
            env.done = True
            env.outcome = "truncated"
            env.phase = "terminal"
            observation = env.observation()

        assert env.run_state is not None
        results.append(
            RolloutResult(
                seed=episode_seed,
                steps=steps,
                total_reward=total_reward,
                outcome=observation.outcome or "unknown",
                completed_nodes=len(env.run_state.completed_node_ids),
                fights_won=max(0, env.run_state.fight_number - 1),
                gold=getattr(env.run_state, "gold", 0),
                deck_size=len(env.run_state.run_deck),
                relic_count=len(env.run_state.relics),
        damage_dealt=getattr(env, "damage_dealt", 0),
        damage_taken=getattr(env, "damage_taken", 0),
            )
        )

    return results


def load_class_runner_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def model_paths_from_class_runner_manifest(
    manifest: dict[str, Any],
) -> dict[str, Path]:
    paths: dict[str, Path] = {}

    for character in manifest.get("characters", []):
        character_id = character["character_id"]
        model_path = character.get("model_path")
        if model_path:
            paths[character_id] = Path(model_path)

    return paths


def improve_class_runners_from_manifest(
    *,
    manifest_path: str | Path,
    output_dir: str | Path,
    character_ids: list[str] | None = None,
    seed: int = 1,
    episodes: int = 800,
    eval_runs: int = 50,
    max_steps: int = 800,
    workers: int | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = load_class_runner_manifest(manifest_path)
    model_paths = model_paths_from_class_runner_manifest(manifest)

    if character_ids is None:
        character_ids = sorted(model_paths)

    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    tasks: list[dict[str, Any]] = []
    for index, character_id in enumerate(character_ids):
        if character_id not in model_paths:
            raise ValueError(
                f"No model path found for character {character_id!r} in {manifest_path}."
            )

        tasks.append(
            {
                "character_id": character_id,
                "model_path": str(model_paths[character_id]),
                "output_dir": str(output_directory),
                "seed": seed + index * 100_000,
                "episodes": episodes,
                "eval_runs": eval_runs,
                "max_steps": max_steps,
            }
        )

    worker_count = resolve_worker_count(workers, len(tasks))

    if worker_count <= 1:
        character_results = [
            _continue_training_class_runner_task(task)
            for task in tasks
        ]
    else:
        character_results_by_id: dict[str, dict[str, Any]] = {}
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(_continue_training_class_runner_task, task)
                for task in tasks
            ]
            for future in as_completed(futures):
                result = future.result()
                character_results_by_id[result["character_id"]] = result

        character_results = [
            character_results_by_id[character_id]
            for character_id in character_ids
        ]

    overview = {
        "schema_version": 1,
        "source_manifest_path": str(manifest_path),
        "seed": seed,
        "episodes": episodes,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "workers": worker_count,
        "characters": character_results,
    }

    overview_path = output_directory / "improved_class_runners_manifest.json"
    overview_path.write_text(
        json.dumps(overview, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "manifest": overview,
        "manifest_path": overview_path,
        "characters": character_results,
    }


def format_improvement_summary(results: list[dict[str, Any]]) -> str:
    lines = ["=== Continued Class Runner Training Summary ==="]

    for result in results:
        lines.append("")
        lines.append(f"Character: {result['character_id']}")
        lines.append(f"Q-table entries: {result['q_table_entries']}")

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


def _continue_training_class_runner_task(task: dict[str, Any]) -> dict[str, Any]:
    return continue_training_class_runner(
        character_id=task["character_id"],
        model_path=task["model_path"],
        output_dir=task["output_dir"],
        seed=task["seed"],
        episodes=task["episodes"],
        eval_runs=task["eval_runs"],
        max_steps=task["max_steps"],
    )
