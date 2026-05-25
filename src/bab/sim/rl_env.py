"""RL-ready headless environment for Bureaucrats and Broomsticks.

Patch 1 keeps this deliberately framework-free and small:
- manual decisions for map movement, combat card play, and combat card rewards
- existing simulator code is reused for events, shops, treasure, and waiting rooms
- reward shaping is exposed in one place so later agents can use the same signal
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from random import Random
from typing import Any

from bab.combat.effects import resolve_card
from bab.combat.deck import card_exhausts_when_played, card_is_unplayable
from bab.combat.state import CombatState, Combatant
from bab.combat.turns import end_player_turn, run_enemy_turn, start_player_turn
from bab.console.run_flow import create_run_state
from bab.content.catalog import ContentCatalog, load_default_content_catalog
from bab.models import Card
from bab.run.state import (
    RunState,
    create_combat_state_for_next_encounter,
    enter_map_node,
    finish_victorious_combat,
)
from bab.sim.auto_runner import (
    SimConfig,
    ensure_gold_field,
    initialize_run_diagnostics,
    resolve_random_map_node,
)
from bab.systems.relics import card_reward_count_bonus
from bab.systems.rewards import choose_card_rewards


@dataclass(frozen=True)
class Action:
    """One discrete action for the current environment phase."""

    kind: str
    index: int | None = None
    target_index: int | None = None


@dataclass
class Observation:
    phase: str
    legal_actions: tuple[Action, ...]
    character_id: str
    act: int
    fight_number: int
    hp: int
    max_hp: int
    gold: int
    deck_size: int
    relic_count: int
    completed_nodes: int
    current_node_id: str | None
    current_node_type: str | None
    available_map_node_ids: tuple[str, ...]
    available_map_node_types: tuple[str, ...]
    combat_turn: int | None = None
    energy: int | None = None
    hand_card_ids: tuple[str, ...] = ()
    hand_card_costs: tuple[int, ...] = ()
    enemy_ids: tuple[str, ...] = ()
    enemy_hp: tuple[int, ...] = ()
    enemy_block: tuple[int, ...] = ()
    reward_card_ids: tuple[str, ...] = ()
    enemy_intents: tuple[str, ...] = ()
    incoming_damage: int = 0
    deck_card_ids: tuple[str, ...] = ()
    done: bool = False
    outcome: str | None = None


@dataclass
class StepResult:
    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvConfig:
    max_combat_turns: int = 80
    invalid_actions_raise: bool = False
    reward_skip_action: bool = True


@dataclass
class RewardConfig:
    step_penalty: float = -0.01
    combat_step_penalty: float = -0.02
    hp_lost_penalty: float = -0.35
    enemy_kill_reward: float = 2.0
    damage_dealt_reward: float = 0.02
    damage_taken_penalty: float = 0.05
    combat_win_reward: float = 8.0
    node_complete_reward: float = 1.0
    gold_reward: float = 0.03
    card_gain_reward: float = 0.35
    relic_gain_reward: float = 2.0
    run_win_reward: float = 50.0
    death_penalty: float = -40.0
    stall_penalty: float = -10.0
    invalid_action_penalty: float = -3.0


@dataclass(frozen=True)
class RewardSnapshot:
    phase: str
    hp: int
    gold: int
    deck_size: int
    relic_count: int
    completed_nodes: int
    fights_won: int
    living_enemies: int
    total_enemy_hp: int


@dataclass
class RolloutResult:
    seed: int
    steps: int
    total_reward: float
    outcome: str
    completed_nodes: int
    fights_won: int
    gold: int
    deck_size: int
    relic_count: int
    damage_dealt: int = 0
    damage_taken: int = 0
    first_combat_damage_dealt: int = 0
    first_combat_damage_taken: int = 0
    first_combat_turns: int = 0
    first_combat_zero_damage: bool = False


class RoguelikeEnv:
    """Small reset/step wrapper around the current run/combat systems."""

    def __init__(
        self,
        *,
        seed: int = 1,
        catalog: ContentCatalog | None = None,
        config: EnvConfig | None = None,
        reward_config: RewardConfig | None = None,
    ) -> None:
        self.seed = seed
        self._provided_catalog = catalog
        self.config = config or EnvConfig()
        self.reward_config = reward_config or RewardConfig()
        self.rng = Random(seed)

        self.catalog: ContentCatalog | None = None
        self.run_state: RunState | None = None
        self.combat_state: CombatState | None = None

        self.phase = "uninitialized"
        self.done = False
        self.outcome: str | None = None
        self.combat_turns_played = 0
        self.reward_cards: list[Card] = []
        self.damage_dealt = 0
        self.damage_taken = 0
        self.first_combat_damage_dealt = 0
        self.first_combat_damage_taken = 0
        self.first_combat_turns = 0
        self.first_combat_zero_damage = False

    def reset(
        self,
        *,
        seed: int | None = None,
        character_id: str | None = None,
    ) -> Observation:
        if seed is not None:
            self.seed = seed
        self.rng = Random(self.seed)

        self.catalog = self._provided_catalog or load_default_content_catalog()
        if character_id is None:
            character_id = self.rng.choice(sorted(self.catalog.character_classes))

        self.run_state = create_run_state(
            character_id,
            catalog=self.catalog,
            rng=self.rng,
        )
        ensure_gold_field(self.run_state)
        initialize_run_diagnostics(self.run_state)

        self.combat_state = None
        self.reward_cards = []
        self.damage_dealt = 0
        self.damage_taken = 0
        self.first_combat_damage_dealt = 0
        self.first_combat_damage_taken = 0
        self.first_combat_turns = 0
        self.first_combat_zero_damage = False
        self.phase = "map"
        self.done = False
        self.outcome = None
        self.combat_turns_played = 0
        self._sync_terminal_state()
        return self.observation()

    def observation(self) -> Observation:
        self._require_run()
        self._sync_terminal_state()
        assert self.run_state is not None

        current_node = self.run_state.current_node()
        available_nodes = self.run_state.available_map_nodes()

        combat_turn: int | None = None
        energy: int | None = None
        hand_card_ids: tuple[str, ...] = ()
        hand_card_costs: tuple[int, ...] = ()
        enemy_ids: tuple[str, ...] = ()
        enemy_hp: tuple[int, ...] = ()
        enemy_block: tuple[int, ...] = ()
        enemy_intents: tuple[str, ...] = ()
        incoming_damage = 0

        if self.combat_state is not None:
            combat_turn = self.combat_state.turn
            energy = self.combat_state.energy
            hand_card_ids = tuple(card.id for card in self.combat_state.hand)
            hand_card_costs = tuple(card.cost for card in self.combat_state.hand)
            enemy_ids = tuple(enemy.id for enemy in self.combat_state.enemies)
            enemy_hp = tuple(enemy.hp for enemy in self.combat_state.enemies)
            enemy_block = tuple(enemy.block for enemy in self.combat_state.enemies)
            enemy_intents = tuple(self._enemy_intent_label(enemy) for enemy in self.combat_state.enemies)
            incoming_damage = self._incoming_damage()

        return Observation(
            phase=self.phase,
            legal_actions=self.legal_actions(),
            character_id=self.run_state.character_class.id,
            act=self.run_state.act,
            fight_number=self.run_state.fight_number,
            hp=self._current_hp(),
            max_hp=self.run_state.character_class.max_hp,
            gold=getattr(self.run_state, "gold", 0),
            deck_size=len(self.run_state.run_deck),
            relic_count=len(self.run_state.relics),
            completed_nodes=len(self.run_state.completed_node_ids),
            current_node_id=self.run_state.current_node_id,
            current_node_type=current_node.node_type if current_node is not None else None,
            available_map_node_ids=tuple(node.id for node in available_nodes),
            available_map_node_types=tuple(node.node_type for node in available_nodes),
            combat_turn=combat_turn,
            energy=energy,
            hand_card_ids=hand_card_ids,
            hand_card_costs=hand_card_costs,
            enemy_ids=enemy_ids,
            enemy_hp=enemy_hp,
            enemy_block=enemy_block,
            reward_card_ids=tuple(card.id for card in self.reward_cards),
            enemy_intents=enemy_intents,
            incoming_damage=incoming_damage,
            deck_card_ids=tuple(card.id for card in self.run_state.run_deck),
            done=self.done,
            outcome=self.outcome,
        )

    def legal_actions(self) -> tuple[Action, ...]:
        if self.done:
            return (Action("noop"),)
        self._require_run()
        assert self.run_state is not None

        if self.phase == "map":
            return tuple(
                Action("choose_map_node", index=index)
                for index, _node in enumerate(self.run_state.available_map_nodes())
            )

        if self.phase == "combat":
            self._require_combat()
            assert self.combat_state is not None
            actions: list[Action] = [Action("end_turn")]
            living_enemies = self.combat_state.living_enemies()

            for card_index, card in enumerate(self.combat_state.hand):
                if card_is_unplayable(card):
                    continue
                if card.cost > self.combat_state.energy:
                    continue
                if self._card_needs_enemy_target(card):
                    for target_index, _enemy in enumerate(living_enemies):
                        actions.append(
                            Action(
                                "play_card",
                                index=card_index,
                                target_index=target_index,
                            )
                        )
                else:
                    actions.append(Action("play_card", index=card_index))
            return tuple(actions)

        if self.phase == "card_reward":
            actions = []
            if self.config.reward_skip_action:
                actions.append(Action("skip_card_reward"))
            actions.extend(
                Action("choose_card_reward", index=index)
                for index, _card in enumerate(self.reward_cards)
            )
            return tuple(actions)

        return ()

    def sample_action(self, observation: Observation | None = None) -> Action:
        actions = observation.legal_actions if observation is not None else self.legal_actions()
        if not actions:
            return Action("noop")
        return self.rng.choice(list(actions))

    def step(self, action: Action) -> StepResult:
        self._require_run()
        if self.done:
            return StepResult(self.observation(), 0.0, True, {"already_done": True})

        legal_actions = self.legal_actions()
        if action not in legal_actions:
            if self.config.invalid_actions_raise:
                raise ValueError(f"Invalid action {action!r} in phase {self.phase!r}.")
            return StepResult(
                self.observation(),
                self.reward_config.invalid_action_penalty,
                self.done,
                {"invalid_action": action, "legal_actions": legal_actions},
            )

        before = self._snapshot()
        info: dict[str, Any] = {"action": action}

        if action.kind == "choose_map_node":
            self._step_map(action, info)
        elif action.kind == "play_card":
            self._step_play_card(action, info)
        elif action.kind == "end_turn":
            self._step_end_turn(info)
        elif action.kind in {"choose_card_reward", "skip_card_reward"}:
            self._step_card_reward(action, info)
        elif action.kind == "noop":
            pass
        else:
            raise ValueError(f"Unsupported action kind: {action.kind!r}")

        self._sync_terminal_state()
        after = self._snapshot()
        damage_dealt = max(0, before.total_enemy_hp - after.total_enemy_hp)
        damage_taken = max(0, before.hp - after.hp)
        self.damage_dealt += damage_dealt
        self.damage_taken += damage_taken
        if before.phase == "combat" and before.fights_won == 0:
            self.first_combat_damage_dealt += damage_dealt
            self.first_combat_damage_taken += damage_taken
            if action.kind == "end_turn":
                self.first_combat_turns = max(self.first_combat_turns, self.combat_turns_played)
            else:
                self.first_combat_turns = max(self.first_combat_turns, self.combat_turns_played + 1)
            if after.fights_won > before.fights_won or self.done:
                self.first_combat_zero_damage = self.first_combat_damage_dealt == 0
        reward = self._calculate_reward_from_snapshots(before, after)
        return StepResult(self.observation(), reward, self.done, info)

    def _step_map(self, action: Action, info: dict[str, Any]) -> None:
        assert self.run_state is not None
        if action.index is None:
            raise ValueError("choose_map_node requires an index.")

        node = self.run_state.available_map_nodes()[action.index]
        enter_map_node(self.run_state, node.id)
        info["node_id"] = node.id
        info["node_type"] = node.node_type

        if node.node_type in {"combat", "elite", "boss"}:
            self._start_combat(create_combat_state_for_next_encounter(self.run_state))
            return

        # Patch 1 keeps non-combat flows stable by delegating to the proven
        # simulator. Later patches can split event/shop/treasure into phases.
        resolve_random_map_node(
            self.run_state,
            node,
            self.rng,
            SimConfig(max_combat_turns=self.config.max_combat_turns),
        )
        self.phase = "map"

    def _start_combat(self, combat_state: CombatState) -> None:
        self.combat_state = combat_state
        self.combat_turns_played = 0
        start_player_turn(self.combat_state, self.rng)
        self.phase = "combat"

    def _step_play_card(self, action: Action, info: dict[str, Any]) -> None:
        self._require_combat()
        assert self.combat_state is not None
        if action.index is None:
            raise ValueError("play_card requires a hand index.")

        card = self.combat_state.hand[action.index]
        if card_is_unplayable(card):
            info["card_id"] = card.id
            info["unplayable"] = True
            return
        target: Combatant | None = None
        if action.target_index is not None:
            target = self.combat_state.living_enemies()[action.target_index]

        self.combat_state.energy -= card.cost
        self.combat_state.hand.pop(action.index)
        resolve_card(card, self.combat_state, target)
        if card_exhausts_when_played(card):
            self.combat_state.exhaust_pile.append(card)
            self.combat_state.log.append(f"{card.name} is exhausted.")
        else:
            self.combat_state.discard_pile.append(card)

        info["card_id"] = card.id
        info["target_id"] = target.id if target is not None else None
        self._finish_combat_if_needed()

    def _step_end_turn(self, info: dict[str, Any]) -> None:
        self._require_combat()
        assert self.combat_state is not None

        end_player_turn(self.combat_state)
        run_enemy_turn(self.combat_state)
        self.combat_turns_played += 1
        info["combat_turns_played"] = self.combat_turns_played

        if self._finish_combat_if_needed():
            return

        if self.combat_turns_played >= self.config.max_combat_turns:
            self.done = True
            self.outcome = "stalled"
            self.phase = "terminal"
            return

        start_player_turn(self.combat_state, self.rng)

    def _finish_combat_if_needed(self) -> bool:
        assert self.run_state is not None
        if self.combat_state is None:
            return False

        if self.combat_state.is_victory():
            finish_victorious_combat(self.run_state, self.combat_state)
            self.combat_state = None

            if self.run_state.is_complete():
                self.done = True
                self.outcome = "win"
                self.phase = "terminal"
                return True

            self._open_card_reward()
            return True

        if self.combat_state.is_defeat():
            self.run_state.current_hp = 0
            self.done = True
            self.outcome = "defeat"
            self.phase = "terminal"
            return True

        self.run_state.current_hp = self.combat_state.player.hp
        return False

    def _open_card_reward(self) -> None:
        assert self.run_state is not None
        reward_count = 3 + card_reward_count_bonus(self.run_state.relics)
        try:
            self.reward_cards = choose_card_rewards(
                self.run_state.card_database,
                self.rng,
                count=reward_count,
                card_class=self.run_state.character_class.id,
            )
        except ValueError:
            self.reward_cards = []

        self.phase = "card_reward" if self.reward_cards else "map"

    def _step_card_reward(self, action: Action, info: dict[str, Any]) -> None:
        assert self.run_state is not None

        if action.kind == "choose_card_reward":
            if action.index is None:
                raise ValueError("choose_card_reward requires an index.")
            card = self.reward_cards[action.index]
            self.run_state.run_deck.append(card)
            info["card_id"] = card.id
        else:
            info["skipped_card_reward"] = True

        self.reward_cards = []
        self.phase = "map"

    def _snapshot(self) -> RewardSnapshot:
        assert self.run_state is not None
        return RewardSnapshot(
            phase=self.phase,
            hp=self._current_hp(),
            gold=getattr(self.run_state, "gold", 0),
            deck_size=len(self.run_state.run_deck),
            relic_count=len(self.run_state.relics),
            completed_nodes=len(self.run_state.completed_node_ids),
            fights_won=max(0, self.run_state.fight_number - 1),
            living_enemies=self._living_enemy_count(),
            total_enemy_hp=self._total_enemy_hp(),
        )

    def _calculate_reward_from_snapshots(
        self,
        before: RewardSnapshot,
        after: RewardSnapshot,
    ) -> float:
        cfg = self.reward_config
        reward = cfg.step_penalty

        if before.phase == "combat":
            reward += cfg.combat_step_penalty

        hp_delta = after.hp - before.hp
        if hp_delta < 0:
            reward += -hp_delta * cfg.hp_lost_penalty

        damage_dealt = max(0, before.total_enemy_hp - after.total_enemy_hp)
        damage_taken = max(0, before.hp - after.hp)
        reward += damage_dealt * cfg.damage_dealt_reward
        reward -= damage_taken * cfg.damage_taken_penalty

        reward += max(0, before.living_enemies - after.living_enemies) * cfg.enemy_kill_reward
        reward += max(0, after.fights_won - before.fights_won) * cfg.combat_win_reward
        reward += max(0, after.completed_nodes - before.completed_nodes) * cfg.node_complete_reward
        reward += max(0, after.gold - before.gold) * cfg.gold_reward
        reward += max(0, after.deck_size - before.deck_size) * cfg.card_gain_reward
        reward += max(0, after.relic_count - before.relic_count) * cfg.relic_gain_reward

        if self.done:
            if self.outcome == "win":
                reward += cfg.run_win_reward
            elif self.outcome == "defeat":
                reward += cfg.death_penalty
            elif self.outcome == "stalled":
                reward += cfg.stall_penalty

        return reward

    def _sync_terminal_state(self) -> None:
        if self.run_state is None or self.done:
            return
        if self.run_state.is_complete():
            self.done = True
            self.outcome = "win"
            self.phase = "terminal"
            return
        if self.run_state.is_defeated():
            self.done = True
            self.outcome = "defeat"
            self.phase = "terminal"
            return
        if self.phase == "map" and not self.run_state.available_map_nodes():
            self.done = True
            self.outcome = "stalled"
            self.phase = "terminal"

    def _current_hp(self) -> int:
        if self.combat_state is not None:
            return self.combat_state.player.hp
        assert self.run_state is not None
        return self.run_state.current_hp

    def _living_enemy_count(self) -> int:
        if self.combat_state is None:
            return 0
        return len(self.combat_state.living_enemies())

    def _total_enemy_hp(self) -> int:
        if self.combat_state is None:
            return 0
        return sum(max(0, enemy.hp) for enemy in self.combat_state.living_enemies())


    def _incoming_damage(self) -> int:
        if self.combat_state is None:
            return 0

        total = 0
        for enemy in self.combat_state.living_enemies():
            total += self._incoming_damage_from_enemy(enemy)
        return max(0, total)

    def _incoming_damage_from_enemy(self, enemy: Combatant) -> int:
        intent_values = []
        for attr_name in (
            "intent",
            "next_intent",
            "current_intent",
            "planned_intent",
            "selected_intent",
        ):
            value = getattr(enemy, attr_name, None)
            if value is not None:
                intent_values.append(value)

        # Some enemies store the selected action/intent under action-ish names.
        for attr_name in (
            "action",
            "next_action",
            "current_action",
            "intent_action",
            "planned_action",
        ):
            value = getattr(enemy, attr_name, None)
            if value is not None:
                intent_values.append(value)

        total = 0
        for value in intent_values:
            total += self._incoming_damage_from_value(value)
        return max(0, total)

    def _incoming_damage_from_value(self, value: object, *, depth: int = 0) -> int:
        if value is None or depth > 4:
            return 0

        if isinstance(value, (int, float)):
            return 0

        if isinstance(value, str):
            return 0

        if isinstance(value, dict):
            type_text = str(
                value.get("type")
                or value.get("intent")
                or value.get("id")
                or value.get("name")
                or ""
            ).lower()

            damage = 0
            if any(word in type_text for word in ("attack", "damage", "strike", "hit")):
                for amount_key in ("amount", "damage", "base_damage", "value"):
                    amount = value.get(amount_key)
                    if isinstance(amount, (int, float)):
                        damage += int(amount)

            for nested_key in ("actions", "effects", "subactions", "items"):
                nested = value.get(nested_key)
                damage += self._incoming_damage_from_value(nested, depth=depth + 1)

            return max(0, damage)

        if isinstance(value, (list, tuple)):
            return sum(
                self._incoming_damage_from_value(item, depth=depth + 1)
                for item in value
            )

        type_text = str(
            getattr(value, "type", "")
            or getattr(value, "intent", "")
            or getattr(value, "id", "")
            or getattr(value, "name", "")
        ).lower()

        damage = 0
        if any(word in type_text for word in ("attack", "damage", "strike", "hit")):
            for amount_attr in ("amount", "damage", "base_damage", "value"):
                amount = getattr(value, amount_attr, None)
                if isinstance(amount, (int, float)):
                    damage += int(amount)

        for nested_attr in ("actions", "effects", "subactions", "items"):
            nested = getattr(value, nested_attr, None)
            if nested is not None:
                damage += self._incoming_damage_from_value(nested, depth=depth + 1)

        return max(0, damage)

    def _enemy_intent_label(self, enemy: Combatant) -> str:
        for attr_name in (
            "intent",
            "next_intent",
            "current_intent",
            "planned_intent",
            "selected_intent",
            "action",
            "next_action",
            "current_action",
            "intent_action",
            "planned_action",
        ):
            value = getattr(enemy, attr_name, None)
            label = self._intent_label_from_value(value)
            if label != "unknown":
                return label
        return "unknown"

    def _intent_label_from_value(self, value: object) -> str:
        if value is None:
            return "unknown"

        if isinstance(value, str):
            return value.lower()

        if isinstance(value, dict):
            for key in ("type", "intent", "id", "name"):
                raw = value.get(key)
                if raw:
                    return str(raw).lower()

            actions = value.get("actions")
            if isinstance(actions, list) and actions:
                return "+".join(
                    self._intent_label_from_value(action)
                    for action in actions
                )

            return "unknown"

        if isinstance(value, (list, tuple)) and value:
            return "+".join(
                self._intent_label_from_value(item)
                for item in value
            )

        for attr_name in ("type", "intent", "id", "name"):
            raw = getattr(value, attr_name, None)
            if raw:
                return str(raw).lower()

        return "unknown"


    @staticmethod
    def _card_needs_enemy_target(card: Card) -> bool:
        return any(
            getattr(effect, "target", None) in {"enemy", "first_enemy", "random_enemy"}
            for effect in card.effects
        )

    def _require_run(self) -> None:
        if self.run_state is None:
            raise RuntimeError("Call reset() before using the environment.")

    def _require_combat(self) -> None:
        if self.combat_state is None:
            raise RuntimeError("Environment is not currently in combat.")


def rollout_random_policy(
    *,
    seed: int = 1,
    max_steps: int = 1000,
    character_id: str | None = None,
    env_config: EnvConfig | None = None,
    reward_config: RewardConfig | None = None,
) -> RolloutResult:
    env = RoguelikeEnv(
        seed=seed,
        config=env_config,
        reward_config=reward_config,
    )
    observation = env.reset(character_id=character_id)

    total_reward = 0.0
    steps = 0
    for step_index in range(max_steps):
        if observation.done:
            break
        result = env.step(env.sample_action(observation))
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


def summarize_rollouts(results: list[RolloutResult]) -> str:
    if not results:
        return "No rollouts."

    outcomes = Counter(result.outcome for result in results)
    average_reward = sum(result.total_reward for result in results) / len(results)
    average_steps = sum(result.steps for result in results) / len(results)
    average_nodes = sum(result.completed_nodes for result in results) / len(results)

    lines = [
        "=== RL Environment Random Policy Rollout ===",
        f"Runs: {len(results)}",
        f"Average reward: {average_reward:.2f}",
        f"Average steps: {average_steps:.2f}",
        f"Average completed nodes: {average_nodes:.2f}",
        "",
        "=== Outcomes ===",
    ]
    for outcome, count in outcomes.most_common():
        lines.append(f"{outcome}: {count}")
    return "\n".join(lines)