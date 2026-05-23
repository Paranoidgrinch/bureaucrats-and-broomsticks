from bab.combat.state import CombatState, Combatant
from bab.models import Card, Effect


def resolve_card(
    card: Card,
    state: CombatState,
    target: Combatant | None = None,
) -> None:
    state.log.append(f"Player plays {card.name}.")

    for effect in card.effects:
        resolve_effect(effect, state, target)


def resolve_effect(
    effect: Effect,
    state: CombatState,
    target: Combatant | None = None,
) -> None:
    if effect.type == "deal_damage":
        resolved_target = resolve_target(effect.target, state, target)
        amount = require_amount(effect.amount, effect.type)
        damage_dealt = resolved_target.take_damage(amount)
        state.log.append(
            f"{resolved_target.name} takes {damage_dealt} damage."
        )
        return

    if effect.type == "gain_block":
        resolved_target = resolve_target(effect.target, state, target)
        amount = require_amount(effect.amount, effect.type)
        resolved_target.gain_block(amount)
        state.log.append(
            f"{resolved_target.name} gains {amount} Block."
        )
        return

    if effect.type == "apply_status":
        resolved_target = resolve_target(effect.target, state, target)
        amount = require_amount(effect.amount, effect.type)

        if effect.status is None:
            raise ValueError("apply_status effect requires a status.")

        resolved_target.apply_status(effect.status, amount)
        status_name = state.status_name(effect.status)
        state.log.append(
            f"{resolved_target.name} gains {amount} {status_name}."
        )
        return

    if effect.type == "gain_strength":
        resolved_target = resolve_target(effect.target, state, target)
        amount = require_amount(effect.amount, effect.type)
        resolved_target.apply_status("strength", amount)
        state.log.append(
            f"{resolved_target.name} gains {amount} {state.status_name('strength')}."
        )
        return

    if effect.type == "damage_per_status":
        resolved_target = resolve_target(effect.target, state, target)

        if effect.status is None:
            raise ValueError("damage_per_status effect requires a status.")

        amount_per_stack = require_amount_per_stack(
            effect.amount_per_stack,
            effect.type,
        )
        stacks = resolved_target.get_status_amount(effect.status)
        total_damage = stacks * amount_per_stack
        damage_dealt = resolved_target.take_damage(total_damage)
        status_name = state.status_name(effect.status)
        state.log.append(
            f"{resolved_target.name} takes {damage_dealt} damage "
            f"from {status_name} scaling."
        )
        return

    raise NotImplementedError(f"Effect type not implemented yet: {effect.type}")


def resolve_target(
    target_type: str | None,
    state: CombatState,
    selected_target: Combatant | None,
) -> Combatant:
    if target_type == "self":
        return state.player

    if target_type == "owner":
        if selected_target is None:
            raise ValueError("owner target requires a selected owner.")
        return selected_target

    if target_type == "enemy":
        if selected_target is None:
            return state.first_enemy()
        return selected_target

    if target_type == "player":
        return state.player

    if target_type == "first_enemy":
        return state.first_enemy()

    raise NotImplementedError(f"Target type not implemented yet: {target_type}")


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