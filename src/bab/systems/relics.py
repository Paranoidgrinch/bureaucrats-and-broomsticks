"""Relic system helpers."""

from __future__ import annotations

from random import Random
from typing import Any

from bab.combat.state import CombatState
from bab.models import RelicDefinition
from bab.rules.relic_effect_handlers import (
    apply_pickup_relic_effect,
    card_reward_count_from_relic_effect,
    gold_pickup_from_relic_effect,
    gold_reward_bonus_from_relic_effect,
    require_amount,
    resolve_combat_start_relic_effect,
    shop_discount_from_relic_effect,
)


def choose_random_unowned_relic(
    relic_database: dict[str, RelicDefinition],
    owned_relics: list[RelicDefinition],
    rng: Random,
) -> RelicDefinition:
    owned_ids = {relic.id for relic in owned_relics}
    available_relics = [
        relic
        for relic in relic_database.values()
        if relic.id not in owned_ids
    ]

    if not available_relics:
        raise ValueError("No unowned relics available.")

    return rng.choice(available_relics)


def apply_combat_start_relics(
    state: CombatState,
    relics: list[RelicDefinition],
) -> None:
    for relic in relics:
        for effect in relic.effects:
            resolve_combat_start_relic_effect(effect, relic, state)


def apply_relic_pickup_effects(
    *,
    current_hp: int,
    max_hp: int,
    relic: RelicDefinition,
) -> tuple[int, list[str]]:
    new_hp = current_hp
    messages: list[str] = []

    for effect in relic.effects:
        new_hp, new_messages = apply_pickup_relic_effect(
            effect,
            relic,
            current_hp=new_hp,
            max_hp=max_hp,
        )
        messages.extend(new_messages)

    return new_hp, messages


def apply_relic_pickup_effects_to_run_state(
    run_state: Any,
    relic: RelicDefinition,
) -> list[str]:
    """Apply all pickup effects directly to a RunState-like object."""

    run_state.current_hp, messages = apply_relic_pickup_effects(
        current_hp=run_state.current_hp,
        max_hp=run_state.character_class.max_hp,
        relic=relic,
    )

    for effect in relic.effects:
        gold = gold_pickup_from_relic_effect(effect, relic)

        if gold <= 0:
            continue

        run_state.gold += gold
        messages.append(f"{relic.name} grants {gold} Gold.")

    return messages


def card_reward_count_bonus(relics: list[RelicDefinition]) -> int:
    bonus = 0

    for relic in relics:
        for effect in relic.effects:
            bonus += card_reward_count_from_relic_effect(effect, relic)

    return bonus


def gold_reward_bonus(relics: list[RelicDefinition]) -> int:
    bonus = 0

    for relic in relics:
        for effect in relic.effects:
            bonus += gold_reward_bonus_from_relic_effect(effect, relic)

    return bonus


def shop_price_discount_percent(relics: list[RelicDefinition]) -> int:
    discount = 0

    for relic in relics:
        for effect in relic.effects:
            discount += shop_discount_from_relic_effect(effect, relic)

    return min(discount, 75)


__all__ = [
    "apply_combat_start_relics",
    "apply_relic_pickup_effects",
    "apply_relic_pickup_effects_to_run_state",
    "card_reward_count_bonus",
    "choose_random_unowned_relic",
    "gold_reward_bonus",
    "require_amount",
    "shop_price_discount_percent",
]
