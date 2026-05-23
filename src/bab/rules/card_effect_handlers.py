"""Card and enemy effect handler registry."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from bab.combat.state import CombatState, Combatant
from bab.models import Effect

CardEffectHandler = Callable[[Effect, CombatState, Combatant | None], None]


def resolve_card_effect(
    effect: Effect,
    state: CombatState,
    selected_target: Combatant | None = None,
) -> None:
    handler = CARD_EFFECT_HANDLERS.get(effect.type)

    if handler is None:
        raise NotImplementedError(f"Effect type not implemented yet: {effect.type}")

    handler(effect, state, selected_target)


def handle_deal_damage(
    effect: Effect,
    state: CombatState,
    selected_target: Combatant | None,
) -> None:
    amount = require_amount(effect.amount, effect.type)

    for resolved_target in resolve_targets(effect.target, state, selected_target):
        damage_dealt = resolved_target.take_damage(amount)
        state.log.append(f"{resolved_target.name} takes {damage_dealt} damage.")


def handle_gain_block(
    effect: Effect,
    state: CombatState,
    selected_target: Combatant | None,
) -> None:
    amount = require_amount(effect.amount, effect.type)

    for resolved_target in resolve_targets(effect.target, state, selected_target):
        resolved_target.gain_block(amount)
        state.log.append(f"{resolved_target.name} gains {amount} Block.")


def handle_apply_status(
    effect: Effect,
    state: CombatState,
    selected_target: Combatant | None,
) -> None:
    amount = require_amount(effect.amount, effect.type)

    if effect.status is None:
        raise ValueError("apply_status effect requires a status.")

    for resolved_target in resolve_targets(effect.target, state, selected_target):
        resolved_target.apply_status(effect.status, amount)
        status_name = state.status_name(effect.status)
        state.log.append(f"{resolved_target.name} gains {amount} {status_name}.")


def handle_gain_strength(
    effect: Effect,
    state: CombatState,
    selected_target: Combatant | None,
) -> None:
    amount = require_amount(effect.amount, effect.type)

    for resolved_target in resolve_targets(effect.target, state, selected_target):
        resolved_target.apply_status("strength", amount)
        state.log.append(
            f"{resolved_target.name} gains {amount} {state.status_name('strength')}."
        )


def handle_damage_per_status(
    effect: Effect,
    state: CombatState,
    selected_target: Combatant | None,
) -> None:
    if effect.status is None:
        raise ValueError("damage_per_status effect requires a status.")

    amount_per_stack = require_amount_per_stack(
        effect.amount_per_stack,
        effect.type,
    )

    for resolved_target in resolve_targets(effect.target, state, selected_target):
        stacks = resolved_target.get_status_amount(effect.status)
        total_damage = stacks * amount_per_stack
        damage_dealt = resolved_target.take_damage(total_damage)
        status_name = state.status_name(effect.status)
        state.log.append(
            f"{resolved_target.name} takes {damage_dealt} damage "
            f"from {status_name} scaling."
        )


CARD_EFFECT_HANDLERS: Mapping[str, CardEffectHandler] = {
    "deal_damage": handle_deal_damage,
    "gain_block": handle_gain_block,
    "apply_status": handle_apply_status,
    "gain_strength": handle_gain_strength,
    "damage_per_status": handle_damage_per_status,
}


def resolve_targets(
    target_type: str | None,
    state: CombatState,
    selected_target: Combatant | None,
) -> list[Combatant]:
    if target_type == "self":
        return [state.player]

    if target_type == "owner":
        if selected_target is None:
            raise ValueError("owner target requires a selected owner.")
        return [selected_target]

    if target_type == "enemy":
        if selected_target is None:
            return [state.first_enemy()]
        return [selected_target]

    if target_type == "all_enemies":
        return state.living_enemies()

    if target_type == "random_enemy":
        # CombatState does not own an RNG yet. Keep this deterministic for now.
        return [state.first_enemy()]

    if target_type == "player":
        return [state.player]

    if target_type == "first_enemy":
        return [state.first_enemy()]

    raise NotImplementedError(f"Target type not implemented yet: {target_type}")


def resolve_target(
    target_type: str | None,
    state: CombatState,
    selected_target: Combatant | None,
) -> Combatant:
    targets = resolve_targets(target_type, state, selected_target)

    if len(targets) != 1:
        raise ValueError(f"Expected exactly one target for {target_type}, got {len(targets)}.")

    return targets[0]


def require_amount(amount: int | None, effect_type: str) -> int:
    if amount is None:
        raise ValueError(f"{effect_type} effect requires an amount.")

    return amount


def require_amount_per_stack(
    amount_per_stack: int | None,
    effect_type: str,
) -> int:
    if amount_per_stack is None:
        raise ValueError(f"{effect_type} effect requires amount_per_stack.")

    return amount_per_stack
