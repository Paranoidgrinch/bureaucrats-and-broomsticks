"""Relic effect handler registry."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from bab.combat.state import CombatState
from bab.models import RelicDefinition, RelicEffect

CombatStartRelicHandler = Callable[[RelicEffect, RelicDefinition, CombatState], None]
PickupRelicHandler = Callable[[RelicEffect, RelicDefinition, int, int], tuple[int, list[str]]]
RewardCountRelicHandler = Callable[[RelicEffect, RelicDefinition], int]


def resolve_combat_start_relic_effect(
    effect: RelicEffect,
    relic: RelicDefinition,
    state: CombatState,
) -> None:
    handler = RELIC_COMBAT_START_HANDLERS.get(effect.type)

    if handler is not None:
        handler(effect, relic, state)
        return

    if effect.type in NON_COMBAT_START_RELIC_EFFECT_TYPES:
        return

    raise NotImplementedError(f"Relic effect not implemented: {effect.type}")


def apply_pickup_relic_effect(
    effect: RelicEffect,
    relic: RelicDefinition,
    current_hp: int,
    max_hp: int,
) -> tuple[int, list[str]]:
    handler = RELIC_PICKUP_HANDLERS.get(effect.type)

    if handler is not None:
        return handler(effect, relic, current_hp, max_hp)

    return current_hp, []


def card_reward_count_from_relic_effect(
    effect: RelicEffect,
    relic: RelicDefinition,
) -> int:
    handler = RELIC_REWARD_COUNT_HANDLERS.get(effect.type)

    if handler is None:
        return 0

    return handler(effect, relic)


def handle_increase_max_energy(
    effect: RelicEffect,
    relic: RelicDefinition,
    state: CombatState,
) -> None:
    amount = require_amount(effect.amount, relic.name)
    state.max_energy += amount
    state.energy += amount
    state.log.append(f"{relic.name} increases Max Energy by {amount}.")


def handle_gain_block_at_combat_start(
    effect: RelicEffect,
    relic: RelicDefinition,
    state: CombatState,
) -> None:
    amount = require_amount(effect.amount, relic.name)
    state.player.gain_block(amount)
    state.log.append(f"{relic.name} grants {amount} Block.")


def handle_apply_status_to_all_enemies_at_combat_start(
    effect: RelicEffect,
    relic: RelicDefinition,
    state: CombatState,
) -> None:
    amount = require_amount(effect.amount, relic.name)

    if effect.status is None:
        raise ValueError(f"{relic.name} relic effect requires a status.")

    for enemy in state.living_enemies():
        enemy.apply_status(effect.status, amount)

    status_name = state.status_name(effect.status)
    state.log.append(f"{relic.name} applies {amount} {status_name} to all enemies.")


def handle_heal_on_pickup(
    effect: RelicEffect,
    relic: RelicDefinition,
    current_hp: int,
    max_hp: int,
) -> tuple[int, list[str]]:
    amount = require_amount(effect.amount, relic.name)
    new_hp = min(max_hp, current_hp + amount)
    healed = new_hp - current_hp

    return new_hp, [f"{relic.name} restores {healed} HP."]


def handle_increase_card_reward_count(
    effect: RelicEffect,
    relic: RelicDefinition,
) -> int:
    return require_amount(effect.amount, relic.name)


RELIC_COMBAT_START_HANDLERS: Mapping[str, CombatStartRelicHandler] = {
    "increase_max_energy": handle_increase_max_energy,
    "gain_block_at_combat_start": handle_gain_block_at_combat_start,
    "apply_status_to_all_enemies_at_combat_start": handle_apply_status_to_all_enemies_at_combat_start,
}

RELIC_PICKUP_HANDLERS: Mapping[str, PickupRelicHandler] = {
    "heal_on_pickup": handle_heal_on_pickup,
}

RELIC_REWARD_COUNT_HANDLERS: Mapping[str, RewardCountRelicHandler] = {
    "increase_card_reward_count": handle_increase_card_reward_count,
}

SUPPORTED_RELIC_EFFECT_TYPES = frozenset(
    {
        *RELIC_COMBAT_START_HANDLERS,
        *RELIC_PICKUP_HANDLERS,
        *RELIC_REWARD_COUNT_HANDLERS,
    }
)

NON_COMBAT_START_RELIC_EFFECT_TYPES = SUPPORTED_RELIC_EFFECT_TYPES - set(
    RELIC_COMBAT_START_HANDLERS
)


def require_amount(amount: int | None, relic_name: str) -> int:
    if amount is None:
        raise ValueError(f"{relic_name} relic effect requires an amount.")

    return amount
