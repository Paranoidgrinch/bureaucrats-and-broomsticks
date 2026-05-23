"""Enemy intent helpers.

Enemy intents are named moves. New content should prefer the `actions` field:
a move can execute several ordered Effect objects in one enemy turn.

Legacy intent fields (`damage`, `block`, `effects`) remain supported so older
content does not need to be rewritten immediately.
"""

from __future__ import annotations

from bab.combat.state import Combatant
from bab.models import Effect, EnemyIntent


def actions_for_intent(intent: EnemyIntent) -> list[Effect]:
    """Return the ordered actions an enemy intent should execute."""

    if intent.actions:
        return list(intent.actions)

    actions: list[Effect] = []

    if intent.block is not None:
        actions.append(
            Effect(
                type="gain_block",
                target="owner",
                amount=intent.block,
            )
        )

    if intent.damage is not None:
        actions.append(
            Effect(
                type="deal_damage",
                target="player",
                amount=intent.damage,
            )
        )

    actions.extend(intent.effects)

    return actions


def summarize_intent_for_display(
    intent: EnemyIntent,
    combatant: Combatant,
) -> str:
    action_summaries = [
        summarize_action_for_display(action, combatant)
        for action in actions_for_intent(intent)
    ]
    action_summaries = [
        summary
        for summary in action_summaries
        if summary
    ]

    if not action_summaries:
        return f'intends to use "{intent.name}"'

    return f'intends to use "{intent.name}": ' + ", ".join(action_summaries)


def summarize_action_for_display(
    action: Effect,
    combatant: Combatant,
) -> str:
    if action.type == "deal_damage":
        amount = action.amount or 0

        if action.target == "player":
            amount += combatant.get_status_amount("strength")

        return f"attack for {amount} damage"

    if action.type == "gain_block":
        return f"gain {action.amount or 0} Block"

    if action.type == "apply_status":
        status_name = format_status_id(action.status)
        return f"apply {action.amount or 0} {status_name}"

    if action.type == "gain_strength":
        return f"gain {action.amount or 0} Strength"

    if action.type == "damage_per_status":
        status_name = format_status_id(action.status)
        return f"damage per {status_name}"

    return action.type.replace("_", " ")


def format_status_id(status_id: str | None) -> str:
    if status_id is None:
        return "status"

    return status_id.replace("_", " ").title()
