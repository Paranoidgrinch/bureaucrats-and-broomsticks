"""Console combat flow.

This module contains the interactive console layer for running combat. Core
combat rules remain in combat_state.py, turns.py, effects.py, deck.py, and
enemies.py.
"""

from __future__ import annotations

from rich.table import Table

from bab.combat_state import CombatState, Combatant
from bab.console.io import console
from bab.console.views import (
    format_enemy_intent,
    print_combat_state,
    print_full_log,
    print_hand,
    print_piles,
    print_recent_log,
)
from bab.deck import play_card_from_hand
from bab.run_state import RunState, create_combat_state_for_next_encounter


def choose_target(state: CombatState) -> Combatant | None:
    living_enemies = state.living_enemies()
    if not living_enemies:
        return None

    if len(living_enemies) == 1:
        return living_enemies[0]

    table = Table(title="Choose Target")
    table.add_column("#", justify="right")
    table.add_column("Enemy", style="red")
    table.add_column("HP", justify="right")
    table.add_column("Block", justify="right")
    table.add_column("Statuses")
    table.add_column("Intent")

    for index, enemy in enumerate(state.enemies):
        if not enemy.is_alive():
            continue

        statuses = ", ".join(
            f"{state.status_name(status.id)}: {status.amount}"
            for status in enemy.statuses.values()
        )
        if not statuses:
            statuses = "-"

        intent_text = format_enemy_intent(enemy)

        table.add_row(
            str(index),
            enemy.name,
            f"{enemy.hp}/{enemy.max_hp}",
            str(enemy.block),
            statuses,
            intent_text,
        )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose target number or 'cancel': [/bold yellow]"
        ).strip().lower()

        if command == "cancel":
            return None

        if not command.isdigit():
            console.print("[red]Invalid target.[/red]")
            continue

        target_index = int(command)

        if target_index < 0 or target_index >= len(state.enemies):
            console.print("[red]Invalid target number.[/red]")
            continue

        target = state.enemies[target_index]
        if not target.is_alive():
            console.print("[red]That target is already defeated.[/red]")
            continue

        return target


def player_action_loop(state: CombatState) -> None:
    while True:
        if state.is_victory() or state.is_defeat():
            return

        console.print()
        print_combat_state(state)
        print_hand(state)
        print_piles(state)
        print_recent_log(state, lines=5)

        command = console.input(
            "\n[bold yellow]Choose a card number, 'end', 'log', or 'quit': [/bold yellow]"
        ).strip().lower()

        if command == "end":
            from bab.turns import end_player_turn

            end_player_turn(state)
            return

        if command == "log":
            print_full_log(state)
            continue

        if command == "quit":
            raise SystemExit("Game quit.")

        if not command.isdigit():
            console.print("[red]Invalid command.[/red]")
            continue

        hand_index = int(command)

        if hand_index < 0 or hand_index >= len(state.hand):
            console.print("[red]Invalid card number.[/red]")
            continue

        selected_card = state.hand[hand_index]
        if selected_card.cost > state.energy:
            message = (
                f"Not enough Energy to play {selected_card.name}. "
                f"Needed {selected_card.cost}, had {state.energy}."
            )
            state.log.append(message)
            console.print(f"[red]{message}[/red]")
            continue

        target = choose_target(state)
        if target is None:
            console.print("[yellow]Card play cancelled.[/yellow]")
            continue

        play_card_from_hand(state, hand_index=hand_index, target=target)
        print_recent_log(state, lines=5)

        if state.is_victory():
            return


def run_single_combat(run_state: RunState) -> CombatState:
    from bab.turns import run_enemy_turn, start_player_turn

    state = create_combat_state_for_next_encounter(run_state)

    while not state.is_victory() and not state.is_defeat():
        start_player_turn(state, run_state.rng)
        player_action_loop(state)

        if state.is_victory() or state.is_defeat():
            break

        run_enemy_turn(state)

    return state
