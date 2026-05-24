"""Checkpointed training for class-specific Q runners.

This keeps the best validated model instead of blindly saving the last model.
It is the intended workflow for producing one strong learned runner per class.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any

from bab.sim.agents import HeuristicPolicy, RandomPolicy, compare_policies
from bab.sim.class_runner_improvement import (
    load_class_runner_manifest,
    model_paths_from_class_runner_manifest,
)
from bab.sim.metrics import summarize_policy_rollouts
from bab.sim.q_learning import QLearningPolicy, epsilon_for_episode
from bab.sim.rl_env import RoguelikeEnv, RolloutResult


@dataclass(frozen=True)
class CheckpointSelection:
    wins: int
    average_reward: float
    average_damage_dealt: float
    average_damage_taken: float

    def score_tuple(self) -> tuple[int, float, float, float]:
        # Maximize wins, reward, damage dealt; minimize damage taken.
        return (
            self.wins,
            self.average_reward,
            self.average_damage_dealt,
            -self.average_damage_taken,
        )


def checkpoint_train_class_runner(
    *,
    character_id: str,
    model_path: str | Path,
    output_dir: str | Path,
    seed: int = 1,
    episodes: int = 5000,
    minutes: float | None = None,
    checkpoint_interval: int = 200,
    eval_runs: int = 50,
    max_steps: int = 800,
) -> dict[str, Any]:
    started = time.monotonic()
    model_path = Path(model_path)
    output_directory = Path(output_dir)
    character_dir = output_directory / character_id
    checkpoint_dir = character_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    policy = QLearningPolicy.load(model_path, seed=seed)

    history: list[dict[str, Any]] = []
    best_score: tuple[int, float, float, float] | None = None
    best_checkpoint: dict[str, Any] | None = None

    # Evaluate source model before additional training.
    initial = evaluate_checkpoint(
        policy,
        character_id=character_id,
        seed=seed + 900_000,
        eval_runs=eval_runs,
        max_steps=max_steps,
        episode=0,
    )
    history.append(initial)
    best_score = checkpoint_score(initial).score_tuple()
    best_checkpoint = initial
    best_model_path = policy.save(character_dir / "best_q_learning_agent.json")

    trained_episodes = 0
    checkpoint_index = 0

    while trained_episodes < episodes:
        if minutes is not None and (time.monotonic() - started) >= minutes * 60.0:
            break

        chunk = min(checkpoint_interval, episodes - trained_episodes)
        train_policy_chunk(
            policy,
            character_id=character_id,
            seed=seed + trained_episodes,
            start_episode=trained_episodes,
            episodes=chunk,
            max_steps=max_steps,
        )
        trained_episodes += chunk
        checkpoint_index += 1

        checkpoint_model_path = policy.save(
            checkpoint_dir / f"checkpoint_{trained_episodes:06d}.json"
        )
        evaluation = evaluate_checkpoint(
            policy,
            character_id=character_id,
            seed=seed + 900_000,
            eval_runs=eval_runs,
            max_steps=max_steps,
            episode=trained_episodes,
        )
        evaluation["checkpoint_model_path"] = str(checkpoint_model_path)
        history.append(evaluation)

        score = checkpoint_score(evaluation).score_tuple()
        if best_score is None or score > best_score:
            best_score = score
            best_checkpoint = evaluation
            best_model_path = policy.save(character_dir / "best_q_learning_agent.json")

    final_model_path = policy.save(character_dir / "last_q_learning_agent.json")
    history_path = character_dir / "checkpoint_history.json"
    manifest = {
        "schema_version": 1,
        "character_id": character_id,
        "source_model_path": str(model_path),
        "best_model_path": str(best_model_path),
        "last_model_path": str(final_model_path),
        "seed": seed,
        "requested_episodes": episodes,
        "trained_episodes": trained_episodes,
        "minutes": minutes,
        "checkpoint_interval": checkpoint_interval,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "best_checkpoint": best_checkpoint,
        "history_path": str(history_path),
        "q_table_entries": len(policy.q_table),
        "elapsed_seconds": time.monotonic() - started,
    }

    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "character_id": character_id,
                "history": history,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    manifest_path = character_dir / "checkpoint_training_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest["manifest_path"] = str(manifest_path)
    return manifest


def train_policy_chunk(
    policy: QLearningPolicy,
    *,
    character_id: str,
    seed: int,
    start_episode: int,
    episodes: int,
    max_steps: int,
) -> list[RolloutResult]:
    results: list[RolloutResult] = []

    for local_episode in range(episodes):
        global_episode = start_episode + local_episode
        episode_seed = seed + local_episode
        epsilon = epsilon_for_episode(global_episode, policy.config)

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


def evaluate_checkpoint(
    policy: QLearningPolicy,
    *,
    character_id: str,
    seed: int,
    eval_runs: int,
    max_steps: int,
    episode: int,
) -> dict[str, Any]:
    evaluation = compare_policies(
        [
            RandomPolicy(seed=seed),
            HeuristicPolicy(seed=seed),
            policy,
        ],
        runs=eval_runs,
        seed=seed,
        max_steps=max_steps,
        character_id=character_id,
    )
    q_summary = summarize_policy_rollouts(evaluation["q_learning"])
    q_results = evaluation["q_learning"]

    average_damage_dealt = (
        sum(result.damage_dealt for result in q_results) / len(q_results)
        if q_results
        else 0.0
    )
    average_damage_taken = (
        sum(result.damage_taken for result in q_results) / len(q_results)
        if q_results
        else 0.0
    )

    return {
        "episode": episode,
        "evaluation_summary": {
            policy_name: summarize_policy_rollouts(results)
            for policy_name, results in evaluation.items()
        },
        "q_wins": q_summary["wins"],
        "q_average_reward": q_summary["average_reward"],
        "q_average_completed_nodes": q_summary["average_completed_nodes"],
        "q_average_fights_won": q_summary["average_fights_won"],
        "q_average_damage_dealt": average_damage_dealt,
        "q_average_damage_taken": average_damage_taken,
    }


def checkpoint_score(checkpoint: dict[str, Any]) -> CheckpointSelection:
    return CheckpointSelection(
        wins=int(checkpoint.get("q_wins", 0)),
        average_reward=float(checkpoint.get("q_average_reward", 0.0)),
        average_damage_dealt=float(checkpoint.get("q_average_damage_dealt", 0.0)),
        average_damage_taken=float(checkpoint.get("q_average_damage_taken", 0.0)),
    )


def checkpoint_train_from_manifest(
    *,
    manifest_path: str | Path,
    output_dir: str | Path,
    character_ids: list[str] | None = None,
    seed: int = 60001,
    episodes: int = 5000,
    minutes: float | None = None,
    checkpoint_interval: int = 200,
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
            raise ValueError(f"No model path for character {character_id!r}.")
        tasks.append(
            {
                "character_id": character_id,
                "model_path": str(model_paths[character_id]),
                "output_dir": str(output_directory),
                "seed": seed + index * 100_000,
                "episodes": episodes,
                "minutes": minutes,
                "checkpoint_interval": checkpoint_interval,
                "eval_runs": eval_runs,
                "max_steps": max_steps,
            }
        )

    worker_count = resolve_worker_count(workers, len(tasks))

    if worker_count <= 1:
        results = [_checkpoint_task(task) for task in tasks]
    else:
        by_id: dict[str, dict[str, Any]] = {}
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(_checkpoint_task, task) for task in tasks]
            for future in as_completed(futures):
                result = future.result()
                by_id[result["character_id"]] = result
        results = [by_id[character_id] for character_id in character_ids]

    overview = {
        "schema_version": 1,
        "source_manifest_path": str(manifest_path),
        "output_dir": str(output_directory),
        "seed": seed,
        "episodes": episodes,
        "minutes": minutes,
        "checkpoint_interval": checkpoint_interval,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "workers": worker_count,
        "characters": results,
    }
    overview_path = output_directory / "checkpoint_training_manifest.json"
    overview_path.write_text(
        json.dumps(overview, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "manifest": overview,
        "manifest_path": overview_path,
        "characters": results,
    }


def _checkpoint_task(task: dict[str, Any]) -> dict[str, Any]:
    return checkpoint_train_class_runner(
        character_id=task["character_id"],
        model_path=task["model_path"],
        output_dir=task["output_dir"],
        seed=task["seed"],
        episodes=task["episodes"],
        minutes=task["minutes"],
        checkpoint_interval=task["checkpoint_interval"],
        eval_runs=task["eval_runs"],
        max_steps=task["max_steps"],
    )


def resolve_worker_count(workers: int | None, task_count: int) -> int:
    if task_count <= 0:
        return 1
    if workers is None or workers <= 0:
        return max(1, min(os.cpu_count() or 1, task_count))
    return max(1, min(workers, task_count))


def format_checkpoint_training_summary(results: list[dict[str, Any]]) -> str:
    lines = ["=== Checkpointed Class Runner Training Summary ==="]

    for result in results:
        best = result.get("best_checkpoint") or {}
        lines.append("")
        lines.append(f"Character: {result['character_id']}")
        lines.append(f"Trained episodes: {result['trained_episodes']}")
        lines.append(f"Q-table entries: {result['q_table_entries']}")
        lines.append(
            "Best checkpoint: "
            f"episode {best.get('episode')} | "
            f"wins {best.get('q_wins')} | "
            f"avg_reward {float(best.get('q_average_reward', 0.0)):.2f} | "
            f"avg_damage_dealt {float(best.get('q_average_damage_dealt', 0.0)):.1f} | "
            f"avg_damage_taken {float(best.get('q_average_damage_taken', 0.0)):.1f}"
        )
        lines.append(f"Best model: {result['best_model_path']}")

    return "\n".join(lines)
