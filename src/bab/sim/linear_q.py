"""Linear approximated Q-learning for class-specific runners.

Unlike the tabular Q agent, this policy does not memorize exact state/action
keys. It learns weights for reusable features, such as:
- incoming damage
- low HP
- action kind
- card damage/block/utility/quality
- deck role composition
- reward card marginal value
- map risk features

This is still dependency-free and intentionally lightweight.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
from random import Random
import time
from typing import Any

from bab.content.catalog import load_default_content_catalog
from bab.sim.agents import HeuristicPolicy, Policy, RandomPolicy, compare_policies
from bab.sim.benchmark import (
    benchmark_policies_across_characters,
    write_benchmark_bundle,
)
from bab.sim.card_features import (
    CardFeature,
    CardFeatureIndex,
    keyword_card_feature,
    safe_load_default_card_feature_index,
)
from bab.sim.metrics import summarize_policy_rollouts
from bab.sim.q_learning import epsilon_for_episode
from bab.sim.rl_env import Action, Observation, RoguelikeEnv, RolloutResult


@dataclass
class LinearQConfig:
    alpha: float = 0.04
    gamma: float = 0.96
    epsilon_start: float = 0.40
    epsilon_end: float = 0.04
    epsilon_decay_episodes: int = 2500
    gradient_clip: float = 20.0
    weight_clip: float = 50.0
    heuristic_explore_probability: float = 0.65
    heuristic_tiebreak_margin: float = 0.10
    risk_aware_fallback: bool = True
    low_hp_fallback_ratio: float = 0.35
    medium_hp_fallback_ratio: float = 0.55
    low_hp_fallback_margin: float = 4.0
    medium_hp_fallback_margin: float = 1.5
    card_reward_fallback_margin: float = 0.25
    map_fallback_margin: float = 0.25
    imitation_alpha: float = 0.04
    imitation_margin: float = 1.0
    imitation_target: float = 2.0


class LinearQPolicy:
    name = "linear_q"

    def __init__(
        self,
        *,
        config: LinearQConfig | None = None,
        weights: dict[str, float] | None = None,
        seed: int | None = None,
        fallback_policy: Policy | None = None,
        card_features: CardFeatureIndex | None = None,
    ) -> None:
        self.config = config or LinearQConfig()
        self.weights: dict[str, float] = weights or {}
        self.rng = Random(seed)
        self.fallback_policy = fallback_policy
        self.card_features = card_features or safe_load_default_card_feature_index()

    def choose_action(
        self,
        observation: Observation,
        *,
        epsilon: float = 0.0,
        explore: bool = False,
    ) -> Action:
        legal_actions = [
            action for action in observation.legal_actions
            if action.kind != "noop"
        ]
        if not legal_actions:
            return Action("noop")

        if explore and self.rng.random() < epsilon:
            return self._choose_exploration_action(observation, legal_actions)

        return self._choose_greedy_action(observation, legal_actions)

    def q_value(self, observation: Observation, action: Action) -> float:
        features = linear_features(observation, action, self.card_features)
        return sum(self.weights.get(name, 0.0) * value for name, value in features.items())

    def update(
        self,
        observation: Observation,
        action: Action,
        reward: float,
        next_observation: Observation,
        done: bool,
    ) -> None:
        prediction = self.q_value(observation, action)

        if done:
            future_value = 0.0
        else:
            next_actions = [
                candidate for candidate in next_observation.legal_actions
                if candidate.kind != "noop"
            ]
            future_value = (
                max(self.q_value(next_observation, candidate) for candidate in next_actions)
                if next_actions
                else 0.0
            )

        target = reward + self.config.gamma * future_value
        td_error = target - prediction
        self._apply_gradient(
            linear_features(observation, action, self.card_features),
            td_error,
            alpha=self.config.alpha,
        )

    def imitation_update(
        self,
        observation: Observation,
        expert_action: Action,
    ) -> None:
        legal_actions = [
            action for action in observation.legal_actions
            if action.kind != "noop"
        ]
        if expert_action not in legal_actions:
            return

        expert_value = self.q_value(observation, expert_action)
        other_values = [
            self.q_value(observation, action)
            for action in legal_actions
            if action != expert_action
        ]
        best_other = max(other_values, default=0.0)
        target = max(
            self.config.imitation_target,
            best_other + self.config.imitation_margin,
        )
        self._apply_gradient(
            linear_features(observation, expert_action, self.card_features),
            target - expert_value,
            alpha=self.config.imitation_alpha,
        )

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "name": self.name,
            "config": asdict(self.config),
            "weights": self.weights,
            "uses_linear_approximation": True,
        }
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        seed: int | None = None,
        use_heuristic_guidance: bool = True,
    ) -> "LinearQPolicy":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        config = LinearQConfig(**payload["config"])
        weights = {
            str(key): float(value)
            for key, value in payload["weights"].items()
        }
        fallback = HeuristicPolicy(seed=seed) if use_heuristic_guidance else None
        return cls(
            config=config,
            weights=weights,
            seed=seed,
            fallback_policy=fallback,
        )

    def _apply_gradient(
        self,
        features: dict[str, float],
        td_error: float,
        *,
        alpha: float,
    ) -> None:
        clipped_error = max(
            -self.config.gradient_clip,
            min(self.config.gradient_clip, td_error),
        )

        for name, value in features.items():
            if value == 0:
                continue
            updated = self.weights.get(name, 0.0) + alpha * clipped_error * value
            self.weights[name] = max(
                -self.config.weight_clip,
                min(self.config.weight_clip, updated),
            )

    def _choose_exploration_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        if (
            self.fallback_policy is not None
            and self.rng.random() < self.config.heuristic_explore_probability
        ):
            fallback_action = self.fallback_policy.choose_action(observation)
            if fallback_action in legal_actions:
                return fallback_action

        return self.rng.choice(legal_actions)

    def _choose_greedy_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        scored = [
            (self.q_value(observation, action), action)
            for action in legal_actions
        ]
        best_value = max(value for value, _action in scored)

        if self.fallback_policy is not None:
            fallback_action = self.fallback_policy.choose_action(observation)
            if fallback_action in legal_actions:
                fallback_value = self.q_value(observation, fallback_action)
                margin = self._fallback_margin_for_observation(observation)
                if fallback_value >= best_value - margin:
                    return fallback_action

        best_actions = [
            action for value, action in scored
            if value == best_value
        ]
        return self.rng.choice(best_actions)

    def _fallback_margin_for_observation(self, observation: Observation) -> float:
        margin = self.config.heuristic_tiebreak_margin

        if not self.config.risk_aware_fallback:
            return margin

        hp_ratio = safe_ratio(observation.hp, observation.max_hp)
        if hp_ratio <= self.config.low_hp_fallback_ratio:
            margin = max(margin, self.config.low_hp_fallback_margin)
        elif hp_ratio <= self.config.medium_hp_fallback_ratio:
            margin = max(margin, self.config.medium_hp_fallback_margin)

        if observation.phase == "card_reward":
            margin = max(margin, self.config.card_reward_fallback_margin)
        elif observation.phase == "map":
            margin = max(margin, self.config.map_fallback_margin)

        return margin


def linear_features(
    observation: Observation,
    action: Action,
    card_features: CardFeatureIndex | None = None,
) -> dict[str, float]:
    features: dict[str, float] = {}

    def add(name: str, value: float = 1.0) -> None:
        if not math.isfinite(value) or value == 0:
            return
        features[name] = features.get(name, 0.0) + float(value)

    phase = observation.phase
    action_kind = action.kind
    hp_ratio = safe_ratio(observation.hp, observation.max_hp)
    incoming_damage = float(getattr(observation, "incoming_damage", 0) or 0)
    incoming_ratio = incoming_damage / max(1.0, float(observation.max_hp))

    add("bias")
    add(f"phase:{phase}")
    add(f"action:{action_kind}")
    add(f"phase:{phase}|action:{action_kind}")
    add("hp_ratio", hp_ratio)
    add("missing_hp_ratio", 1.0 - hp_ratio)
    add("low_hp", 1.0 if hp_ratio <= 0.35 else 0.0)
    add("critical_hp", 1.0 if hp_ratio <= 0.20 else 0.0)
    add("gold_norm", min(observation.gold, 300) / 300.0)
    add("deck_size_norm", min(observation.deck_size, 40) / 40.0)
    add("relic_count_norm", min(observation.relic_count, 8) / 8.0)

    deck_profile = role_profile(getattr(observation, "deck_card_ids", ()), card_features)
    for role, value in deck_profile.items():
        add(f"deck_role:{role}", value)

    if phase == "combat":
        enemy_count = sum(1 for hp in observation.enemy_hp if hp > 0)
        total_enemy_hp = sum(max(0, hp) for hp in observation.enemy_hp)
        weakest_enemy_hp = min([hp for hp in observation.enemy_hp if hp > 0], default=0)

        add("energy_norm", min(observation.energy or 0, 5) / 5.0)
        add("turn_norm", min(observation.combat_turn or 0, 12) / 12.0)
        add("enemy_count_norm", min(enemy_count, 4) / 4.0)
        add("enemy_total_hp_norm", min(total_enemy_hp, 220) / 220.0)
        add("weakest_enemy_hp_norm", min(weakest_enemy_hp, 90) / 90.0)
        add("incoming_damage_norm", min(incoming_damage, 50) / 50.0)
        add("incoming_ratio", min(incoming_ratio, 1.0))
        add("incoming_at_low_hp", min(incoming_ratio, 1.0) * (1.0 - hp_ratio))

        for intent in getattr(observation, "enemy_intents", ()):
            add(f"enemy_intent:{intent}")

        hand_profile = role_profile(observation.hand_card_ids, card_features)
        for role, value in hand_profile.items():
            add(f"hand_role:{role}", value)
            add(f"hand_role:{role}|incoming", value * min(incoming_ratio, 1.0))

    if action_kind == "play_card":
        card_id = indexed(observation.hand_card_ids, action.index, default="")
        cost = indexed(observation.hand_card_costs, action.index, default=0)
        feature = feature_for(card_id, card_features)

        add_card_action_features(add, feature, prefix="play")
        add("play_cost_norm", min(max(cost, 0), 5) / 5.0)
        add(f"play_role:{feature.role}")
        add(f"play_role:{feature.role}|phase:{phase}")
        add("play_block_vs_incoming", min(feature.block, 40) / 40.0 * min(incoming_ratio, 1.0))
        add("play_damage_vs_weak_enemy", min(feature.damage, 40) / 40.0 * (1.0 if weakest_enemy(observation, action) else 0.0))
        add("play_quality_at_low_hp", normalize_quality(feature.quality_score) * (1.0 - hp_ratio))

        if action.target_index is not None and action.target_index < len(observation.enemy_hp):
            target_hp = observation.enemy_hp[action.target_index]
            add("target_hp_norm", min(max(target_hp, 0), 120) / 120.0)
            add("target_is_weakest", 1.0 if weakest_enemy(observation, action) else 0.0)
            add("target_damage_lethal", 1.0 if feature.damage >= target_hp > 0 else 0.0)

    elif action_kind == "choose_card_reward":
        card_id = indexed(observation.reward_card_ids, action.index, default="")
        feature = feature_for(card_id, card_features)

        add_card_action_features(add, feature, prefix="reward")
        add(f"reward_role:{feature.role}")
        add("reward_quality", normalize_quality(feature.quality_score))
        add("reward_low_deck_attack", role_need(deck_profile, "attack") * role_match(feature, "attack"))
        add("reward_low_deck_block", role_need(deck_profile, "block") * role_match(feature, "block"))
        add("reward_low_deck_draw", role_need(deck_profile, "draw") * role_match(feature, "draw"))
        add("reward_low_deck_scaling", role_need(deck_profile, "scaling") * role_match(feature, "scaling"))
        add("reward_bad_card", 1.0 if feature.role == "bad" else 0.0)

    elif action_kind == "skip_card_reward":
        add("skip_reward")
        add("skip_reward_large_deck", min(observation.deck_size, 40) / 40.0)

    elif action_kind == "choose_map_node":
        node_type = indexed(observation.available_map_node_types, action.index, default="unknown")
        add(f"map_node:{node_type}")
        add(f"map_node:{node_type}|low_hp", 1.0 if hp_ratio <= 0.35 else 0.0)
        add("map_elite_at_low_hp", 1.0 if node_type == "elite" and hp_ratio <= 0.45 else 0.0)
        add("map_waiting_room_at_low_hp", 1.0 if node_type == "waiting_room" and hp_ratio <= 0.65 else 0.0)
        add("map_treasure")
        if node_type != "treasure":
            features.pop("map_treasure", None)

    elif action_kind == "end_turn":
        add("end_turn_incoming", min(incoming_ratio, 1.0))
        add("end_turn_low_hp_incoming", min(incoming_ratio, 1.0) * (1.0 - hp_ratio))

    return features


def add_card_action_features(add, feature: CardFeature, *, prefix: str) -> None:
    add(f"{prefix}_damage_norm", min(feature.damage, 40) / 40.0)
    add(f"{prefix}_block_norm", min(feature.block, 40) / 40.0)
    add(f"{prefix}_draw_norm", min(feature.draw, 5) / 5.0)
    add(f"{prefix}_energy_norm", min(feature.energy, 5) / 5.0)
    add(f"{prefix}_strength_norm", min(feature.strength, 5) / 5.0)
    add(f"{prefix}_status_norm", min(feature.status_applications, 5) / 5.0)
    add(f"{prefix}_utility_norm", min(max(feature.utility_score, 0.0), 20.0) / 20.0)
    add(f"{prefix}_quality_norm", normalize_quality(feature.quality_score))
    add(f"{prefix}_damage_per_cost", min(feature.damage_per_cost, 20.0) / 20.0)
    add(f"{prefix}_block_per_cost", min(feature.block_per_cost, 20.0) / 20.0)


def feature_for(
    card_id: str,
    card_features: CardFeatureIndex | None = None,
) -> CardFeature:
    if card_features is not None:
        return card_features.feature_for(card_id)
    return keyword_card_feature(card_id)


def role_profile(
    card_ids: tuple[str, ...],
    card_features: CardFeatureIndex | None = None,
) -> dict[str, float]:
    if not card_ids:
        return {}

    counts: dict[str, int] = {}
    for card_id in card_ids:
        role = feature_for(card_id, card_features).role
        counts[role] = counts.get(role, 0) + 1

    total = max(1, len(card_ids))
    return {
        role: min(count, 12) / total
        for role, count in counts.items()
    }


def role_need(deck_profile: dict[str, float], role: str) -> float:
    current = deck_profile.get(role, 0.0)
    return max(0.0, min(1.0, 0.35 - current) / 0.35)


def role_match(feature: CardFeature, role: str) -> float:
    if feature.role == role:
        return 1.0
    if role == "attack" and feature.damage > 0:
        return 1.0
    if role == "block" and feature.block > 0:
        return 1.0
    if role == "draw" and feature.draw > 0:
        return 1.0
    if role == "scaling" and feature.strength > 0:
        return 1.0
    return 0.0


def normalize_quality(value: float) -> float:
    return max(-1.0, min(1.0, value / 20.0))


def safe_ratio(value: int, maximum: int) -> float:
    if maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, value / maximum))


def indexed(values, index: int | None, *, default):
    if index is None:
        return default
    if 0 <= index < len(values):
        return values[index]
    return default


def weakest_enemy(observation: Observation, action: Action) -> bool:
    if action.target_index is None or action.target_index >= len(observation.enemy_hp):
        return False
    living = [hp for hp in observation.enemy_hp if hp > 0]
    if not living:
        return False
    return observation.enemy_hp[action.target_index] == min(living)


def train_linear_policy_chunk(
    policy: LinearQPolicy,
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
                first_combat_damage_dealt=getattr(env, "first_combat_damage_dealt", 0),
                first_combat_damage_taken=getattr(env, "first_combat_damage_taken", 0),
                first_combat_turns=getattr(env, "first_combat_turns", 0),
                first_combat_zero_damage=bool(getattr(env, "first_combat_zero_damage", False)),
            )
        )

    return results


def pretrain_linear_from_heuristic(
    policy: LinearQPolicy,
    *,
    character_id: str,
    seed: int,
    episodes: int,
    max_steps: int,
) -> None:
    teacher = HeuristicPolicy(seed=seed)

    for episode_index in range(episodes):
        episode_seed = seed + episode_index
        env = RoguelikeEnv(seed=episode_seed)
        observation = env.reset(seed=episode_seed, character_id=character_id)

        for _step_index in range(max_steps):
            if observation.done:
                break
            action = teacher.choose_action(observation)
            policy.imitation_update(observation, action)
            result = env.step(action)
            observation = result.observation


def checkpoint_train_linear_class_runner(
    *,
    character_id: str,
    output_dir: str | Path,
    seed: int = 1,
    episodes: int = 100000,
    minutes: float | None = None,
    checkpoint_interval: int = 200,
    eval_runs: int = 50,
    max_steps: int = 800,
    imitation_episodes: int = 300,
    config: LinearQConfig | None = None,
    use_heuristic_guidance: bool = True,
) -> dict[str, Any]:
    started = time.monotonic()
    output_directory = Path(output_dir)
    character_dir = output_directory / character_id
    checkpoint_dir = character_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    fallback = HeuristicPolicy(seed=seed) if use_heuristic_guidance else None
    policy = LinearQPolicy(
        config=config,
        seed=seed,
        fallback_policy=fallback,
    )

    if imitation_episodes > 0:
        pretrain_linear_from_heuristic(
            policy,
            character_id=character_id,
            seed=seed + 50_000,
            episodes=imitation_episodes,
            max_steps=max_steps,
        )

    history: list[dict[str, Any]] = []
    initial = evaluate_linear_checkpoint(
        policy,
        character_id=character_id,
        seed=seed + 900_000,
        eval_runs=eval_runs,
        max_steps=max_steps,
        episode=0,
    )
    history.append(initial)

    best_score = linear_checkpoint_score(initial)
    best_checkpoint = initial
    best_model_path = policy.save(character_dir / "best_linear_q_agent.json")

    trained_episodes = 0
    while trained_episodes < episodes:
        if minutes is not None and (time.monotonic() - started) >= minutes * 60.0:
            break

        chunk = min(checkpoint_interval, episodes - trained_episodes)
        train_linear_policy_chunk(
            policy,
            character_id=character_id,
            seed=seed + trained_episodes,
            start_episode=trained_episodes,
            episodes=chunk,
            max_steps=max_steps,
        )
        trained_episodes += chunk

        checkpoint_model_path = policy.save(
            checkpoint_dir / f"checkpoint_{trained_episodes:06d}.json"
        )
        evaluation = evaluate_linear_checkpoint(
            policy,
            character_id=character_id,
            seed=seed + 900_000,
            eval_runs=eval_runs,
            max_steps=max_steps,
            episode=trained_episodes,
        )
        evaluation["checkpoint_model_path"] = str(checkpoint_model_path)
        history.append(evaluation)

        score = linear_checkpoint_score(evaluation)
        if score > best_score:
            best_score = score
            best_checkpoint = evaluation
            best_model_path = policy.save(character_dir / "best_linear_q_agent.json")

    last_model_path = policy.save(character_dir / "last_linear_q_agent.json")
    history_path = character_dir / "linear_checkpoint_history.json"
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

    manifest = {
        "schema_version": 1,
        "character_id": character_id,
        "best_model_path": str(best_model_path),
        "last_model_path": str(last_model_path),
        "seed": seed,
        "requested_episodes": episodes,
        "trained_episodes": trained_episodes,
        "minutes": minutes,
        "checkpoint_interval": checkpoint_interval,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "imitation_episodes": imitation_episodes,
        "best_checkpoint": best_checkpoint,
        "history_path": str(history_path),
        "weight_count": len(policy.weights),
        "elapsed_seconds": time.monotonic() - started,
    }

    manifest_path = character_dir / "linear_checkpoint_training_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def evaluate_linear_checkpoint(
    policy: LinearQPolicy,
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
    q_summary = summarize_policy_rollouts(evaluation["linear_q"])
    q_results = evaluation["linear_q"]

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
        "linear_wins": q_summary["wins"],
        "linear_average_reward": q_summary["average_reward"],
        "linear_average_completed_nodes": q_summary["average_completed_nodes"],
        "linear_average_fights_won": q_summary["average_fights_won"],
        "linear_average_damage_dealt": average_damage_dealt,
        "linear_average_damage_taken": average_damage_taken,
    }


def linear_checkpoint_score(checkpoint: dict[str, Any]) -> tuple[int, float, float, float]:
    return (
        int(checkpoint.get("linear_wins", 0)),
        float(checkpoint.get("linear_average_reward", 0.0)),
        float(checkpoint.get("linear_average_damage_dealt", 0.0)),
        -float(checkpoint.get("linear_average_damage_taken", 0.0)),
    )


def checkpoint_train_linear_from_characters(
    *,
    character_ids: list[str] | None,
    output_dir: str | Path,
    seed: int = 100001,
    episodes: int = 100000,
    minutes: float | None = None,
    checkpoint_interval: int = 200,
    eval_runs: int = 50,
    max_steps: int = 800,
    imitation_episodes: int = 300,
    workers: int | None = None,
    config: LinearQConfig | None = None,
    use_heuristic_guidance: bool = True,
) -> dict[str, Any]:
    if character_ids is None:
        catalog = load_default_content_catalog()
        character_ids = sorted(catalog.character_classes)

    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    tasks = [
        {
            "character_id": character_id,
            "output_dir": str(output_directory),
            "seed": seed + index * 100_000,
            "episodes": episodes,
            "minutes": minutes,
            "checkpoint_interval": checkpoint_interval,
            "eval_runs": eval_runs,
            "max_steps": max_steps,
            "imitation_episodes": imitation_episodes,
            "config": config,
            "use_heuristic_guidance": use_heuristic_guidance,
        }
        for index, character_id in enumerate(character_ids)
    ]

    worker_count = resolve_worker_count(workers, len(tasks))

    if worker_count <= 1:
        results = [_linear_checkpoint_task(task) for task in tasks]
    else:
        by_id: dict[str, dict[str, Any]] = {}
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(_linear_checkpoint_task, task) for task in tasks]
            for future in as_completed(futures):
                result = future.result()
                by_id[result["character_id"]] = result
        results = [by_id[character_id] for character_id in character_ids]

    manifest = {
        "schema_version": 1,
        "agent_type": "linear_q",
        "output_dir": str(output_directory),
        "seed": seed,
        "episodes": episodes,
        "minutes": minutes,
        "checkpoint_interval": checkpoint_interval,
        "eval_runs": eval_runs,
        "max_steps": max_steps,
        "imitation_episodes": imitation_episodes,
        "workers": worker_count,
        "characters": results,
    }
    manifest_path = output_directory / "linear_checkpoint_training_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "characters": results,
    }


def _linear_checkpoint_task(task: dict[str, Any]) -> dict[str, Any]:
    return checkpoint_train_linear_class_runner(
        character_id=task["character_id"],
        output_dir=task["output_dir"],
        seed=task["seed"],
        episodes=task["episodes"],
        minutes=task["minutes"],
        checkpoint_interval=task["checkpoint_interval"],
        eval_runs=task["eval_runs"],
        max_steps=task["max_steps"],
        imitation_episodes=task["imitation_episodes"],
        config=task["config"],
        use_heuristic_guidance=task["use_heuristic_guidance"],
    )


def resolve_worker_count(workers: int | None, task_count: int) -> int:
    if task_count <= 0:
        return 1
    if workers is None or workers <= 0:
        return max(1, min(os.cpu_count() or 1, task_count))
    return max(1, min(workers, task_count))


class LinearCheckpointPolicy:
    name = "linear_q"

    def __init__(
        self,
        *,
        manifest_path: str | Path,
        seed: int | None = None,
        fallback_to_heuristic: bool = True,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.seed = seed
        self.fallback_to_heuristic = fallback_to_heuristic
        self.model_paths = linear_best_model_paths(
            self.manifest,
            base_dir=self.manifest_path.parent,
        )
        self._policies: dict[str, LinearQPolicy] = {}
        self._heuristic = HeuristicPolicy(seed=seed)

    def choose_action(self, observation: Observation) -> Action:
        policy = self._policy_for_character(observation.character_id)
        if policy is not None:
            return policy.choose_action(observation)

        if self.fallback_to_heuristic:
            return self._heuristic.choose_action(observation)

        if observation.legal_actions:
            return observation.legal_actions[0]
        return Action("noop")

    def _policy_for_character(self, character_id: str) -> LinearQPolicy | None:
        if character_id in self._policies:
            return self._policies[character_id]

        model_path = self.model_paths.get(character_id)
        if model_path is None or not model_path.exists():
            return None

        policy = LinearQPolicy.load(model_path, seed=self.seed)
        self._policies[character_id] = policy
        return policy


def linear_best_model_paths(
    manifest: dict[str, Any],
    *,
    base_dir: Path,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}

    for character in manifest.get("characters", []):
        character_id = character.get("character_id")
        value = character.get("best_model_path")
        if not character_id or not value:
            continue

        model_path = Path(value)
        if not model_path.is_absolute() and not model_path.exists():
            candidate = base_dir / character_id / "best_linear_q_agent.json"
            if candidate.exists():
                model_path = candidate

        paths[character_id] = model_path

    return paths


def format_linear_training_summary(results: list[dict[str, Any]]) -> str:
    lines = ["=== Linear-Q Checkpointed Class Runner Training Summary ==="]

    for result in results:
        best = result.get("best_checkpoint") or {}
        lines.append("")
        lines.append(f"Character: {result['character_id']}")
        lines.append(f"Trained episodes: {result['trained_episodes']}")
        lines.append(f"Weight count: {result['weight_count']}")
        lines.append(
            "Best checkpoint: "
            f"episode {best.get('episode')} | "
            f"wins {best.get('linear_wins')} | "
            f"avg_reward {float(best.get('linear_average_reward', 0.0)):.2f} | "
            f"avg_damage_dealt {float(best.get('linear_average_damage_dealt', 0.0)):.1f} | "
            f"avg_damage_taken {float(best.get('linear_average_damage_taken', 0.0)):.1f}"
        )
        lines.append(f"Best model: {result['best_model_path']}")

    return "\n".join(lines)


def format_linear_checkpoint_selection(manifest: dict[str, Any]) -> str:
    lines = ["=== Best Linear-Q Runner Selection ==="]

    for character in manifest.get("characters", []):
        best = character.get("best_checkpoint") or {}
        lines.append(
            f"{character.get('character_id')}: "
            f"episode {best.get('episode')} | "
            f"wins {best.get('linear_wins')} | "
            f"avg_reward {float(best.get('linear_average_reward', 0.0)):.2f} | "
            f"avg_damage_dealt {float(best.get('linear_average_damage_dealt', 0.0)):.1f} | "
            f"avg_damage_taken {float(best.get('linear_average_damage_taken', 0.0)):.1f}"
        )

    return "\n".join(lines)


def benchmark_linear_checkpoint_policy(
    *,
    manifest_path: str | Path,
    character_ids: list[str] | None,
    runs_per_character: int,
    seed: int,
    max_steps: int,
    output_dir: str | Path,
    stem: str,
) -> tuple[Path, Path, Path, list[dict[str, Any]]]:
    if character_ids is None:
        catalog = load_default_content_catalog()
        character_ids = sorted(catalog.character_classes)

    manifest_path = Path(manifest_path)
    rows = benchmark_policies_across_characters(
        {
            "random": lambda policy_seed: RandomPolicy(seed=policy_seed),
            "heuristic": lambda policy_seed: HeuristicPolicy(seed=policy_seed),
            "linear_q": lambda policy_seed: LinearCheckpointPolicy(
                manifest_path=manifest_path,
                seed=policy_seed,
            ),
        },
        character_ids=character_ids,
        runs_per_character=runs_per_character,
        seed=seed,
        max_steps=max_steps,
    )

    json_path, csv_path, summary_path = write_benchmark_bundle(
        rows,
        output_dir,
        stem=stem,
    )
    return json_path, csv_path, summary_path, rows


# --- worker-aware linear checkpoint benchmark wrapper v1 ---
_original_benchmark_linear_checkpoint_policy = benchmark_linear_checkpoint_policy


def benchmark_linear_checkpoint_policy(*args, workers: int = 1, **kwargs):
    """Wrapper that keeps old behavior for workers <= 1 and enables the
    worker-aware benchmark backend for larger all-character benchmark runs.
    """
    if "workers" in kwargs:
        workers = kwargs.pop("workers")

    if workers is None or workers <= 1:
        return _original_benchmark_linear_checkpoint_policy(*args, **kwargs)

    import bab.sim.benchmark as benchmark_module

    old_local_benchmark = globals().get("benchmark_policies_across_characters")

    def _benchmark_with_workers(*benchmark_args, **benchmark_kwargs):
        benchmark_kwargs["workers"] = workers
        return benchmark_module.benchmark_policies_across_characters(
            *benchmark_args,
            **benchmark_kwargs,
        )

    globals()["benchmark_policies_across_characters"] = _benchmark_with_workers
    try:
        return _original_benchmark_linear_checkpoint_policy(*args, **kwargs)
    finally:
        globals()["benchmark_policies_across_characters"] = old_local_benchmark
