"""Small tabular Q-learning agent for the RL environment.

This module is deliberately dependency-free. It uses:
- heuristic-guided exploration
- effect-aware card roles
- optional imitation pretraining from a teacher policy

The goal is not a final ML solution yet. It is a robust learned baseline that
can later be replaced by a linear approximator or PyTorch model if needed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from random import Random
from typing import Any

from bab.sim.agents import HeuristicPolicy, Policy, run_policy_rollout
from bab.sim.card_features import (
    CardFeatureIndex,
    keyword_card_role,
    safe_load_default_card_feature_index,
)
from bab.sim.rl_env import Action, Observation, RoguelikeEnv, RolloutResult


@dataclass
class QLearningConfig:
    alpha: float = 0.15
    gamma: float = 0.96
    epsilon_start: float = 0.45
    epsilon_end: float = 0.04
    epsilon_decay_episodes: int = 350
    initial_q: float = 0.0
    heuristic_explore_probability: float = 0.75
    heuristic_tiebreak_margin: float = 0.10

    # Patch 7: imitation pretraining.
    imitation_bonus: float = 5.0
    imitation_margin: float = 1.0

    # Patch 11: risk-aware heuristic fallback.
    # These margins do not replace Q-learning. They only say how much better
    # the learned action must be before it is allowed to overrule the heuristic
    # in dangerous situations.
    risk_aware_fallback: bool = True
    low_hp_fallback_ratio: float = 0.35
    medium_hp_fallback_ratio: float = 0.55
    low_hp_fallback_margin: float = 6.0
    medium_hp_fallback_margin: float = 2.0
    card_reward_fallback_margin: float = 0.75
    map_fallback_margin: float = 0.50


@dataclass
class TrainingResult:
    policy: "QLearningPolicy"
    episode_results: list[RolloutResult]
    imitation_results: list[RolloutResult]


class QLearningPolicy:
    name = "q_learning"

    def __init__(
        self,
        *,
        config: QLearningConfig | None = None,
        q_table: dict[str, float] | None = None,
        seed: int | None = None,
        fallback_policy: Policy | None = None,
        card_features: CardFeatureIndex | None = None,
    ) -> None:
        self.config = config or QLearningConfig()
        self.q_table: dict[str, float] = q_table or {}
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
        return self.q_table.get(
            self._q_key(observation, action),
            self.config.initial_q,
        )

    def update(
        self,
        observation: Observation,
        action: Action,
        reward: float,
        next_observation: Observation,
        done: bool,
    ) -> None:
        key = self._q_key(observation, action)
        old_value = self.q_table.get(key, self.config.initial_q)

        if done:
            future_value = 0.0
        else:
            next_actions = [
                candidate for candidate in next_observation.legal_actions
                if candidate.kind != "noop"
            ]
            if next_actions:
                future_value = max(
                    self.q_value(next_observation, candidate)
                    for candidate in next_actions
                )
            else:
                future_value = 0.0

        target = reward + self.config.gamma * future_value
        self.q_table[key] = old_value + self.config.alpha * (target - old_value)

    def imitation_update(
        self,
        observation: Observation,
        expert_action: Action,
    ) -> None:
        """Nudge the table so the expert action beats alternatives in this state."""

        legal_actions = [
            action for action in observation.legal_actions
            if action.kind != "noop"
        ]
        if expert_action not in legal_actions:
            return

        expert_key = self._q_key(observation, expert_action)
        old_value = self.q_table.get(expert_key, self.config.initial_q)

        other_values = [
            self.q_value(observation, action)
            for action in legal_actions
            if action != expert_action
        ]
        best_other = max(other_values, default=self.config.initial_q)

        target = max(
            self.config.imitation_bonus,
            best_other + self.config.imitation_margin,
        )
        self.q_table[expert_key] = old_value + self.config.alpha * (
            target - old_value
        )

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "name": self.name,
            "config": asdict(self.config),
            "q_table": self.q_table,
            "uses_heuristic_guidance": self.fallback_policy is not None,
            "uses_effect_aware_card_features": True,
            "supports_imitation_pretraining": True,
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
    ) -> "QLearningPolicy":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        config = QLearningConfig(**payload["config"])
        q_table = {
            str(key): float(value)
            for key, value in payload["q_table"].items()
        }
        fallback_policy = HeuristicPolicy(seed=seed) if use_heuristic_guidance else None
        return cls(
            config=config,
            q_table=q_table,
            seed=seed,
            fallback_policy=fallback_policy,
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
        scored_actions = [
            (self.q_value(observation, action), action)
            for action in legal_actions
        ]
        best_value = max(value for value, _action in scored_actions)

        if self.fallback_policy is not None:
            fallback_action = self.fallback_policy.choose_action(observation)
            if fallback_action in legal_actions:
                fallback_value = self.q_value(observation, fallback_action)
                fallback_margin = self._fallback_margin_for_observation(observation)
                if fallback_value >= best_value - fallback_margin:
                    return fallback_action

        best_actions = [
            action for value, action in scored_actions
            if value == best_value
        ]
        return self.rng.choice(best_actions)

    def _fallback_margin_for_observation(
        self,
        observation: Observation,
    ) -> float:
        margin = self.config.heuristic_tiebreak_margin

        if not self.config.risk_aware_fallback:
            return margin

        hp_ratio = self._hp_ratio(observation)

        if hp_ratio <= self.config.low_hp_fallback_ratio:
            margin = max(margin, self.config.low_hp_fallback_margin)
        elif hp_ratio <= self.config.medium_hp_fallback_ratio:
            margin = max(margin, self.config.medium_hp_fallback_margin)

        if observation.phase == "card_reward":
            margin = max(margin, self.config.card_reward_fallback_margin)

        if observation.phase == "map":
            margin = max(margin, self.config.map_fallback_margin)

        return margin

    @staticmethod
    def _hp_ratio(observation: Observation) -> float:
        if observation.max_hp <= 0:
            return 0.0
        return max(0.0, min(1.0, observation.hp / observation.max_hp))

    def _q_key(self, observation: Observation, action: Action) -> str:
        return json.dumps(
            [
                abstract_state_key(observation, self.card_features),
                abstract_action_key(observation, action, self.card_features),
            ],
            sort_keys=True,
            separators=(",", ":"),
        )


def train_q_learning_agent(
    *,
    episodes: int = 500,
    imitation_episodes: int = 250,
    seed: int = 1,
    max_steps: int = 1000,
    character_id: str | None = None,
    config: QLearningConfig | None = None,
    use_heuristic_guidance: bool = True,
) -> TrainingResult:
    card_features = safe_load_default_card_feature_index()
    fallback_policy = HeuristicPolicy(seed=seed) if use_heuristic_guidance else None
    policy = QLearningPolicy(
        config=config,
        seed=seed,
        fallback_policy=fallback_policy,
        card_features=card_features,
    )

    imitation_results: list[RolloutResult] = []
    if imitation_episodes > 0:
        teacher = HeuristicPolicy(seed=seed + 50_000)
        imitation_results = pretrain_from_policy_demonstrations(
            policy,
            teacher,
            episodes=imitation_episodes,
            seed=seed + 50_000,
            max_steps=max_steps,
            character_id=character_id,
        )

    episode_results: list[RolloutResult] = []
    for episode_index in range(episodes):
        episode_seed = seed + episode_index
        epsilon = epsilon_for_episode(
            episode_index,
            policy.config,
        )

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
        episode_results.append(
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

    return TrainingResult(
        policy=policy,
        episode_results=episode_results,
        imitation_results=imitation_results,
    )


def pretrain_from_policy_demonstrations(
    learner: QLearningPolicy,
    teacher: Policy,
    *,
    episodes: int = 250,
    seed: int = 50_000,
    max_steps: int = 1000,
    character_id: str | None = None,
) -> list[RolloutResult]:
    results: list[RolloutResult] = []

    for episode_index in range(episodes):
        episode_seed = seed + episode_index
        env = RoguelikeEnv(seed=episode_seed)
        observation = env.reset(seed=episode_seed, character_id=character_id)

        total_reward = 0.0
        steps = 0

        for step_index in range(max_steps):
            if observation.done:
                break

            action = teacher.choose_action(observation)
            learner.imitation_update(observation, action)

            result = env.step(action)
            learner.update(
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


def evaluate_q_learning_agent(
    policy: QLearningPolicy,
    *,
    runs: int = 50,
    seed: int = 10_000,
    max_steps: int = 1000,
    character_id: str | None = None,
) -> list[RolloutResult]:
    return [
        run_policy_rollout(
            policy,
            seed=seed + index,
            max_steps=max_steps,
            character_id=character_id,
        )
        for index in range(runs)
    ]


def epsilon_for_episode(
    episode_index: int,
    config: QLearningConfig,
) -> float:
    if config.epsilon_decay_episodes <= 0:
        return config.epsilon_end

    progress = min(1.0, episode_index / config.epsilon_decay_episodes)
    return config.epsilon_start + progress * (
        config.epsilon_end - config.epsilon_start
    )


def abstract_state_key(
    observation: Observation,
    card_features: CardFeatureIndex | None = None,
) -> tuple[Any, ...]:
    hp_bucket = bucket_ratio(observation.hp, observation.max_hp, buckets=6)
    gold_bucket = bucket_value(observation.gold, (0, 50, 100, 200, 350))
    deck_bucket = bucket_value(observation.deck_size, (10, 15, 20, 30, 40))
    relic_bucket = bucket_value(observation.relic_count, (0, 1, 2, 4, 7))

    if observation.phase == "combat":
        enemy_count = sum(1 for hp in observation.enemy_hp if hp > 0)
        total_enemy_hp = sum(max(0, hp) for hp in observation.enemy_hp)
        weakest_enemy_hp = min(
            [hp for hp in observation.enemy_hp if hp > 0],
            default=0,
        )
        hand_roles = tuple(
            sorted(card_role(card_id, card_features) for card_id in observation.hand_card_ids)
        )
        role_counts = tuple(
            (role, hand_roles.count(role))
            for role in sorted(set(hand_roles))
        )

        return (
            "combat",
            hp_bucket,
            min(observation.energy or 0, 5),
            bucket_value(observation.combat_turn or 0, (1, 2, 4, 7, 12)),
            enemy_count,
            bucket_value(total_enemy_hp, (15, 35, 60, 100, 160)),
            bucket_value(weakest_enemy_hp, (8, 16, 30, 50, 80)),
            role_counts,
        )

    if observation.phase == "map":
        return (
            "map",
            hp_bucket,
            gold_bucket,
            deck_bucket,
            relic_bucket,
            tuple(observation.available_map_node_types),
        )

    if observation.phase == "card_reward":
        return (
            "card_reward",
            hp_bucket,
            deck_bucket,
            relic_bucket,
            tuple(card_role(card_id, card_features) for card_id in observation.reward_card_ids),
        )

    return (
        observation.phase,
        hp_bucket,
        gold_bucket,
        deck_bucket,
        relic_bucket,
    )


def abstract_action_key(
    observation: Observation,
    action: Action,
    card_features: CardFeatureIndex | None = None,
) -> tuple[Any, ...]:
    if action.kind == "choose_map_node":
        node_type = "unknown"
        if action.index is not None and action.index < len(observation.available_map_node_types):
            node_type = observation.available_map_node_types[action.index]
        return ("choose_map_node", node_type)

    if action.kind == "play_card":
        card_id = "unknown"
        cost = -1
        if action.index is not None and action.index < len(observation.hand_card_ids):
            card_id = observation.hand_card_ids[action.index]
            cost = observation.hand_card_costs[action.index]

        target_bucket = "none"
        target_is_weakest = False
        if (
            action.target_index is not None
            and action.target_index < len(observation.enemy_hp)
        ):
            target_hp = observation.enemy_hp[action.target_index]
            target_bucket = bucket_value(target_hp, (8, 16, 30, 50, 80))
            living_enemy_hp = [hp for hp in observation.enemy_hp if hp > 0]
            if living_enemy_hp:
                target_is_weakest = target_hp == min(living_enemy_hp)

        return (
            "play_card",
            card_role(card_id, card_features),
            min(cost, 5),
            target_bucket,
            target_is_weakest,
        )

    if action.kind == "choose_card_reward":
        card_id = "unknown"
        if action.index is not None and action.index < len(observation.reward_card_ids):
            card_id = observation.reward_card_ids[action.index]
        return ("choose_card_reward", card_role(card_id, card_features))

    return (action.kind,)


def card_role(
    card_id: str,
    card_features: CardFeatureIndex | None = None,
) -> str:
    if card_features is not None:
        return card_features.role_for(card_id)
    return keyword_card_role(card_id)


def bucket_ratio(value: int, maximum: int, *, buckets: int) -> int:
    if maximum <= 0:
        return 0
    ratio = max(0.0, min(1.0, value / maximum))
    return min(buckets - 1, int(ratio * buckets))


def bucket_value(value: int, thresholds: tuple[int, ...]) -> int:
    for index, threshold in enumerate(thresholds):
        if value <= threshold:
            return index
    return len(thresholds)


# === PATCH: richer intent/deck/card-quality abstractions ===

def abstract_state_key(
    observation: Observation,
    card_features: CardFeatureIndex | None = None,
) -> tuple[Any, ...]:
    hp_bucket = bucket_ratio(observation.hp, observation.max_hp, buckets=6)
    gold_bucket = bucket_value(observation.gold, (0, 50, 100, 200, 350))
    deck_bucket = bucket_value(observation.deck_size, (10, 15, 20, 30, 40))
    relic_bucket = bucket_value(observation.relic_count, (0, 1, 2, 4, 7))
    deck_profile = card_collection_profile(
        getattr(observation, "deck_card_ids", ()),
        card_features,
    )

    if observation.phase == "combat":
        enemy_count = sum(1 for hp in observation.enemy_hp if hp > 0)
        total_enemy_hp = sum(max(0, hp) for hp in observation.enemy_hp)
        weakest_enemy_hp = min(
            [hp for hp in observation.enemy_hp if hp > 0],
            default=0,
        )
        hand_profile = card_collection_profile(
            observation.hand_card_ids,
            card_features,
        )
        hand_quality = bucket_value(
            int(sum(card_quality(card_id, card_features) for card_id in observation.hand_card_ids)),
            (0, 5, 10, 15, 25, 40),
        )
        intent_profile = tuple(sorted(set(getattr(observation, "enemy_intents", ()))))
        incoming_damage = getattr(observation, "incoming_damage", 0)

        return (
            "combat",
            hp_bucket,
            min(observation.energy or 0, 5),
            bucket_value(observation.combat_turn or 0, (1, 2, 4, 7, 12)),
            enemy_count,
            bucket_value(total_enemy_hp, (15, 35, 60, 100, 160)),
            bucket_value(weakest_enemy_hp, (8, 16, 30, 50, 80)),
            bucket_value(incoming_damage, (0, 5, 10, 15, 25, 40)),
            intent_profile,
            hand_profile,
            hand_quality,
            deck_profile,
        )

    if observation.phase == "map":
        return (
            "map",
            hp_bucket,
            gold_bucket,
            deck_bucket,
            relic_bucket,
            tuple(observation.available_map_node_types),
            deck_profile,
        )

    if observation.phase == "card_reward":
        reward_profile = card_collection_profile(
            observation.reward_card_ids,
            card_features,
        )
        reward_quality = tuple(
            card_quality_bucket(card_id, card_features)
            for card_id in observation.reward_card_ids
        )
        return (
            "card_reward",
            hp_bucket,
            deck_bucket,
            relic_bucket,
            deck_profile,
            reward_profile,
            reward_quality,
        )

    return (
        observation.phase,
        hp_bucket,
        gold_bucket,
        deck_bucket,
        relic_bucket,
        deck_profile,
    )


def abstract_action_key(
    observation: Observation,
    action: Action,
    card_features: CardFeatureIndex | None = None,
) -> tuple[Any, ...]:
    if action.kind == "choose_map_node":
        node_type = "unknown"
        if action.index is not None and action.index < len(observation.available_map_node_types):
            node_type = observation.available_map_node_types[action.index]
        return ("choose_map_node", node_type)

    if action.kind == "play_card":
        card_id = "unknown"
        cost = -1
        if action.index is not None and action.index < len(observation.hand_card_ids):
            card_id = observation.hand_card_ids[action.index]
            cost = observation.hand_card_costs[action.index]

        target_bucket = "none"
        target_is_weakest = False
        if (
            action.target_index is not None
            and action.target_index < len(observation.enemy_hp)
        ):
            target_hp = observation.enemy_hp[action.target_index]
            target_bucket = bucket_value(target_hp, (8, 16, 30, 50, 80))
            living_enemy_hp = [hp for hp in observation.enemy_hp if hp > 0]
            if living_enemy_hp:
                target_is_weakest = target_hp == min(living_enemy_hp)

        feature = card_feature(card_id, card_features)
        return (
            "play_card",
            feature.role,
            min(cost, 5),
            bucket_value(feature.damage, (0, 4, 8, 12, 20, 35)),
            bucket_value(feature.block, (0, 4, 8, 12, 20, 35)),
            bucket_value(int(feature.utility_score), (0, 2, 4, 8, 12)),
            card_quality_bucket(card_id, card_features),
            target_bucket,
            target_is_weakest,
        )

    if action.kind == "choose_card_reward":
        card_id = "unknown"
        if action.index is not None and action.index < len(observation.reward_card_ids):
            card_id = observation.reward_card_ids[action.index]
        feature = card_feature(card_id, card_features)
        return (
            "choose_card_reward",
            feature.role,
            bucket_value(feature.damage, (0, 4, 8, 12, 20, 35)),
            bucket_value(feature.block, (0, 4, 8, 12, 20, 35)),
            bucket_value(int(feature.utility_score), (0, 2, 4, 8, 12)),
            card_quality_bucket(card_id, card_features),
        )

    return (action.kind,)


def card_collection_profile(
    card_ids: tuple[str, ...],
    card_features: CardFeatureIndex | None = None,
) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for card_id in card_ids:
        role = card_role(card_id, card_features)
        counts[role] = counts.get(role, 0) + 1

    # Cap counts to keep the tabular state space smaller.
    return tuple(
        (role, min(count, 9))
        for role, count in sorted(counts.items())
    )


def card_feature(
    card_id: str,
    card_features: CardFeatureIndex | None = None,
):
    if card_features is not None:
        return card_features.feature_for(card_id)
    from bab.sim.card_features import keyword_card_feature
    return keyword_card_feature(card_id)


def card_quality(
    card_id: str,
    card_features: CardFeatureIndex | None = None,
) -> float:
    return card_feature(card_id, card_features).quality_score


def card_quality_bucket(
    card_id: str,
    card_features: CardFeatureIndex | None = None,
) -> int:
    return bucket_value(int(card_quality(card_id, card_features)), (-5, 0, 3, 6, 10, 16))


def card_role(
    card_id: str,
    card_features: CardFeatureIndex | None = None,
) -> str:
    return card_feature(card_id, card_features).role
