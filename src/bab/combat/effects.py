"""Card effect resolution facade."""

from __future__ import annotations

from bab.combat.state import CombatState, Combatant
from bab.models import Card, Effect
from bab.rules.card_effect_handlers import (
    require_amount,
    require_amount_per_stack,
    resolve_card_effect,
    resolve_target,
    resolve_targets,
)


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
    resolve_card_effect(effect, state, target)


__all__ = [
    "resolve_card",
    "resolve_effect",
    "resolve_target",
    "resolve_targets",
    "require_amount",
    "require_amount_per_stack",
]
