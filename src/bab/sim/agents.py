"""Simple policy agents for the RL environment.

This module is intentionally framework-free. It provides:
- a random policy baseline
- a deterministic-ish heuristic policy baseline
- rollout helpers for comparing policies through RoguelikeEnv

The learned agent will be added later on top of the same small interface.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from random import Random
from typing import Protocol

from bab.sim.rl_env import Action, Observation, RoguelikeEnv, RolloutResult


class Policy(Protocol):
    name: str

    def choose_action(self, observation: Observation) -> Action:
        """Choose one legal action for the current observation."""


class RandomPolicy:
    name = "random"

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = Random(seed)

    def choose_action(self, observation: Observation) -> Action:
        if not observation.legal_actions:
            return Action("noop")
        return self.rng.choice(list(observation.legal_actions))


class HeuristicPolicy:
    """A small, transparent baseline policy.

    This is not meant to be optimal. It is meant to be:
    - stable
    - explainable
    - better than pure random in at least some situations
    - useful as a benchmark before adding a learned agent
    """

    name = "heuristic"

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = Random(seed)

    def choose_action(self, observation: Observation) -> Action:
        legal_actions = [action for action in observation.legal_actions if action.kind != "noop"]
        if not legal_actions:
            return Action("noop")

        if observation.phase == "combat":
            return self._choose_combat_action(observation, legal_actions)

        if observation.phase == "map":
            return self._choose_map_action(observation, legal_actions)

        if observation.phase == "card_reward":
            return self._choose_card_reward_action(observation, legal_actions)

        return self.rng.choice(legal_actions)

    def _choose_combat_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        play_actions = [action for action in legal_actions if action.kind == "play_card"]
        if not play_actions:
            return self._end_turn_or_random(legal_actions)

        scored_actions = [
            (self._score_combat_action(observation, action), action)
            for action in play_actions
        ]
        return self._best_action(scored_actions)

    def _score_combat_action(self, observation: Observation, action: Action) -> float:
        if action.index is None or action.index >= len(observation.hand_card_ids):
            return -999.0

        card_id = observation.hand_card_ids[action.index]
        cost = observation.hand_card_costs[action.index]
        card_text = card_id.lower()
        hp_ratio = observation.hp / max(1, observation.max_hp)

        score = 1.0
        score += cost * 0.25

        attack_words = (
            "attack",
            "strike",
            "stab",
            "hit",
            "damage",
            "blast",
            "bolt",
            "fire",
            "zap",
            "smite",
            "paper_cut",
            "stamp",
            "bonk",
        )
        block_words = (
            "block",
            "defend",
            "guard",
            "shield",
            "ward",
            "barrier",
            "armor",
            "armour",
            "parry",
            "dodge",
        )
        draw_words = (
            "draw",
            "ink",
            "copy",
            "file",
            "form",
            "memo",
            "report",
            "archive",
        )
        energy_words = (
            "energy",
            "free",
            "refund",
            "coffee",
            "tea",
            "haste",
        )

        if any(word in card_text for word in attack_words):
            score += 4.0
        if any(word in card_text for word in block_words):
            score += 3.0
            if hp_ratio < 0.55:
                score += 2.5
            if hp_ratio < 0.35:
                score += 3.5
        if any(word in card_text for word in draw_words):
            score += 1.5
        if any(word in card_text for word in energy_words):
            score += 1.5

        if action.target_index is not None and action.target_index < len(observation.enemy_hp):
            target_hp = observation.enemy_hp[action.target_index]
            target_block = observation.enemy_block[action.target_index]
            effective_target_hp = target_hp + target_block

            # Prefer focusing weakened enemies.
            score += max(0.0, 20.0 - effective_target_hp) * 0.08

            # If all else is equal, prefer enemies that are not already dead.
            if target_hp > 0:
                score += 0.5

        return score

    def _choose_map_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        map_actions = [
            action for action in legal_actions
            if action.kind == "choose_map_node" and action.index is not None
        ]
        if not map_actions:
            return self.rng.choice(legal_actions)

        scored_actions = [
            (self._score_map_action(observation, action), action)
            for action in map_actions
        ]
        return self._best_action(scored_actions)

    def _score_map_action(self, observation: Observation, action: Action) -> float:
        if action.index is None or action.index >= len(observation.available_map_node_types):
            return -999.0

        node_type = observation.available_map_node_types[action.index]
        hp_ratio = observation.hp / max(1, observation.max_hp)

        base_scores = {
            "boss": 100.0,
            "treasure": 35.0,
            "combat": 24.0,
            "event": 18.0,
            "shop": 12.0,
            "elite": 8.0,
            "waiting_room": 6.0,
        }
        score = base_scores.get(node_type, 0.0)

        if node_type == "waiting_room":
            if hp_ratio < 0.45:
                score += 45.0
            elif hp_ratio < 0.65:
                score += 20.0

        if node_type == "elite":
            if hp_ratio >= 0.75:
                score += 25.0
            elif hp_ratio >= 0.6:
                score += 8.0
            else:
                score -= 20.0

        if node_type == "shop":
            if observation.gold >= 100:
                score += 25.0
            elif observation.gold >= 60:
                score += 12.0
            else:
                score -= 8.0

        return score

    def _choose_card_reward_action(
        self,
        observation: Observation,
        legal_actions: list[Action],
    ) -> Action:
        reward_actions = [
            action for action in legal_actions
            if action.kind == "choose_card_reward" and action.index is not None
        ]
        if not reward_actions:
            return self.rng.choice(legal_actions)

        scored_actions = [
            (self._score_reward_card(observation, action), action)
            for action in reward_actions
        ]
        best_reward_action = self._best_action(scored_actions)
        best_score = max(score for score, _action in scored_actions)

        skip_actions = [action for action in legal_actions if action.kind == "skip_card_reward"]
        if skip_actions and best_score < 0.0:
            return skip_actions[0]

        return best_reward_action

    def _score_reward_card(self, observation: Observation, action: Action) -> float:
        if action.index is None or action.index >= len(observation.reward_card_ids):
            return -999.0

        card_id = observation.reward_card_ids[action.index].lower()
        score = 1.0

        bad_words = ("curse", "junk", "wound", "dead_weight", "clutter")
        strong_words = (
            "draw",
            "energy",
            "relic",
            "upgrade",
            "block",
            "guard",
            "shield",
            "strike",
            "attack",
            "damage",
            "stamp",
            "form",
            "file",
            "archive",
            "memo",
        )

        if any(word in card_id for word in bad_words):
            score -= 10.0
        if any(word in card_id for word in strong_words):
            score += 3.0

        # Do not overvalue deck bloat once the deck is already large.
        if observation.deck_size >= 25:
            score -= 1.0
        if observation.deck_size >= 35:
            score -= 2.0

        return score

    def _end_turn_or_random(self, legal_actions: list[Action]) -> Action:
        for action in legal_actions:
            if action.kind == "end_turn":
                return action
        return self.rng.choice(legal_actions)

    def _best_action(self, scored_actions: list[tuple[float, Action]]) -> Action:
        best_score = max(score for score, _action in scored_actions)
        best_actions = [
            action for score, action in scored_actions
            if score == best_score
        ]
        return self.rng.choice(best_actions)


@dataclass
class PolicySummary:
    policy_name: str
    runs: int
    average_reward: float
    average_steps: float
    average_completed_nodes: float
    average_fights_won: float
    wins: int
    defeats: int
    stalls: int
    truncated: int


def run_policy_rollout(
    policy: Policy,
    *,
    seed: int = 1,
    max_steps: int = 1000,
    character_id: str | None = None,
) -> RolloutResult:
    env = RoguelikeEnv(seed=seed)
    observation = env.reset(seed=seed, character_id=character_id)

    total_reward = 0.0
    steps = 0

    for step_index in range(max_steps):
        if observation.done:
            break

        action = policy.choose_action(observation)
        result = env.step(action)

        observation = result.observation
        total_reward += result.reward
        steps = step_index + 1

    if not observation.done:
        env.done = True
        env.outcome = "truncated"
        env.phase = "terminal"
        observation = env.observation()

    assert env.run_state is not None
    return RolloutResult(
        seed=seed,
        steps=steps,
        total_reward=total_reward,
        outcome=observation.outcome or "unknown",
        final_act=env.run_state.act,
        max_act_seen=getattr(env, "max_act_seen", env.run_state.act),
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


def compare_policies(
    policies: list[Policy],
    *,
    runs: int = 20,
    seed: int = 1,
    max_steps: int = 1000,
    character_id: str | None = None,
) -> dict[str, list[RolloutResult]]:
    results: dict[str, list[RolloutResult]] = {}

    for policy in policies:
        policy_results = [
            run_policy_rollout(
                policy,
                seed=seed + index,
                max_steps=max_steps,
                character_id=character_id,
            )
            for index in range(runs)
        ]
        results[policy.name] = policy_results

    return results


def summarize_policy_results(
    results: dict[str, list[RolloutResult]],
) -> str:
    lines = ["=== Policy Comparison ==="]

    for policy_name, policy_results in results.items():
        if not policy_results:
            lines.append("")
            lines.append(f"{policy_name}: no results")
            continue

        outcomes = Counter(result.outcome for result in policy_results)
        runs = len(policy_results)
        average_reward = sum(result.total_reward for result in policy_results) / runs
        average_steps = sum(result.steps for result in policy_results) / runs
        average_nodes = sum(result.completed_nodes for result in policy_results) / runs
        average_fights = sum(result.fights_won for result in policy_results) / runs

        lines.append("")
        lines.append(f"Policy: {policy_name}")
        lines.append(f"Runs: {runs}")
        lines.append(f"Average reward: {average_reward:.2f}")
        lines.append(f"Average steps: {average_steps:.2f}")
        lines.append(f"Average completed nodes: {average_nodes:.2f}")
        lines.append(f"Average fights won: {average_fights:.2f}")
        lines.append("Outcomes:")
        for outcome, count in outcomes.most_common():
            lines.append(f"  {outcome}: {count}")

    return "\n".join(lines)
