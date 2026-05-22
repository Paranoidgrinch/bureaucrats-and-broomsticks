from random import Random

from bab.combat_state import CombatState, Combatant
from bab.deck import discard_hand, draw_cards
from bab.effects import resolve_effect


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

    if intent.intent_type == "attack":
        if intent.damage is None:
            raise ValueError(f"Attack intent {intent.id} requires damage.")

        run_basic_attack(state, enemy, base_damage=intent.damage)
        return

    if intent.intent_type == "block":
        if intent.block is None:
            raise ValueError(f"Block intent {intent.id} requires block.")

        enemy.gain_block(intent.block)
        state.log.append(f"{enemy.name} gains {intent.block} Block.")
        return

    if intent.intent_type in ["buff", "debuff", "special"]:
        for effect in intent.effects:
            resolve_effect(effect, state, target=enemy)
        return

    raise NotImplementedError(f"Enemy intent not implemented: {intent.intent_type}")


def run_basic_attack(state: CombatState, enemy: Combatant, base_damage: int) -> None:
    final_damage = base_damage

    doubt = enemy.get_status_amount("doubt")

    if doubt > 0:
        final_damage = max(0, round(base_damage * 0.75))
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