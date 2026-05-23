"""Turn flow for combat."""

from __future__ import annotations

from random import Random

from bab.combat.deck import discard_hand, draw_cards
from bab.combat.effects import resolve_effect
from bab.combat.intents import actions_for_intent
from bab.combat.state import CombatState, Combatant
from bab.models import Effect


def start_player_turn(state: CombatState, rng: Random) -> None:
    state.log.append(f"--- Turn {state.turn} begins ---")
    state.player.block = 0
    state.reset_energy()

    draw_amount = 5
    panic = state.player.get_status_amount("panic")

    if panic > 0:
        draw_penalty = min(panic, draw_amount)
        draw_amount -= draw_penalty
        state.player.reduce_status("panic", 1)
        state.log.append(
            f"Player is affected by {state.status_name('panic')} "
            f"and draws {draw_penalty} fewer card(s)."
        )

    draw_cards(state, amount=draw_amount, rng=rng)


def end_player_turn(state: CombatState) -> None:
    state.log.append("Player ends the turn.")
    discard_hand(state)


def run_enemy_turn(state: CombatState) -> None:
    if state.is_victory():
        return

    state.log.append("Enemy turn begins.")

    for enemy in state.living_enemies():
        enemy.block = 0

    for enemy in list(state.living_enemies()):
        run_enemy_action(state, enemy)

        if enemy.is_alive():
            enemy.advance_intent()

    apply_enemy_turn_end_statuses(state)
    state.turn += 1


def run_enemy_action(state: CombatState, enemy: Combatant) -> None:
    intent = enemy.current_intent()

    if intent is None:
        run_basic_attack(state, enemy, base_damage=6)
        return

    state.log.append(f"{enemy.name} uses {intent.name}.")

    actions = actions_for_intent(intent)

    if not actions:
        state.log.append(f"{enemy.name} does nothing.")
        return

    for action in actions:
        run_enemy_effect_action(state, enemy, action)


def run_enemy_effect_action(
    state: CombatState,
    enemy: Combatant,
    action: Effect,
) -> None:
    """Execute one enemy action.

    Enemy damage to the player is routed through run_basic_attack so Strength
    and Doubt remain meaningful for multi-action moves.
    """

    if action.type == "deal_damage" and action.target == "player":
        if action.amount is None:
            raise ValueError("Enemy attack action requires an amount.")

        run_basic_attack(state, enemy, base_damage=action.amount)
        return

    resolve_effect(action, state, target=enemy)


def run_basic_attack(
    state: CombatState,
    enemy: Combatant,
    base_damage: int,
) -> None:
    strength = enemy.get_status_amount("strength")
    final_damage = base_damage + strength

    doubt = enemy.get_status_amount("doubt")

    if doubt > 0:
        final_damage = max(0, round(final_damage * 0.75))
        enemy.reduce_status("doubt", 1)
        state.log.append(
            f"{enemy.name} is affected by {state.status_name('doubt')}. "
            "Its attack is reduced."
        )

    damage_dealt = state.player.take_damage(final_damage)
    state.log.append(
        f"{enemy.name} attacks for {final_damage}. "
        f"Player takes {damage_dealt} damage."
    )


def apply_enemy_turn_end_statuses(state: CombatState) -> None:
    for enemy in state.living_enemies():
        paperwork = enemy.get_status_amount("paperwork")

        if paperwork <= 0:
            continue

        hp_lost = enemy.lose_hp(paperwork)
        state.log.append(
            f"{enemy.name} loses {hp_lost} HP from {state.status_name('paperwork')}."
        )
