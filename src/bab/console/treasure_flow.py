"""Console treasure, mimic, and relic pickup flow."""

from __future__ import annotations

from rich.panel import Panel

from bab.console.combat_flow import player_action_loop
from bab.combat.state import CombatState, Combatant
from bab.console.io import console
from bab.console.views import print_combat_state, print_full_log
from bab.combat.deck import shuffle_draw_pile
from bab.systems.encounters import choose_random_encounter
from bab.combat.enemies import create_enemies_for_encounter
from bab.systems.relics import (
    apply_combat_start_relics,
    apply_relic_pickup_effects_to_run_state,
    choose_random_unowned_relic,
)
from bab.run.state import RunState, complete_current_map_node, finish_victorious_combat


def grant_random_relic(run_state: RunState) -> None:
    relic = choose_random_unowned_relic(
        run_state.relic_database,
        run_state.relics,
        run_state.rng,
    )

    run_state.relics.append(relic)

    console.print(f"[bold green]Found relic: {relic.name}.[/bold green]")
    console.print(relic.description)

    messages = apply_relic_pickup_effects_to_run_state(
        run_state,
        relic,
    )

    for message in messages:
        console.print(f"[green]{message}[/green]")


def create_treasure_mimic_combat_state(run_state: RunState) -> CombatState:
    mimic_encounter_id = run_state.treasure_mimic_encounter_id

    if mimic_encounter_id in run_state.encounter_database:
        encounter = run_state.encounter_database[mimic_encounter_id]
    else:
        encounter = choose_random_encounter(
            run_state.encounter_database,
            run_state.rng,
            act=run_state.act,
            difficulty="elite",
        )

    enemies = create_enemies_for_encounter(
        encounter.id,
        run_state.encounter_database,
        run_state.enemy_database,
    )

    player = Combatant(
        id=run_state.character_class.id,
        name=run_state.character_class.name,
        max_hp=run_state.character_class.max_hp,
        hp=run_state.current_hp,
    )

    state = CombatState(
        player=player,
        enemies=enemies,
        max_energy=run_state.character_class.starting_energy,
        energy=run_state.character_class.starting_energy,
        draw_pile=list(run_state.run_deck),
        status_database=run_state.status_database,
    )
    state.log.append(f"Treasure chest was a Mimic: {encounter.name}.")
    apply_combat_start_relics(state, run_state.relics)
    shuffle_draw_pile(state, run_state.rng)

    return state


def run_treasure_mimic_combat(run_state: RunState) -> CombatState:
    from bab.combat.turns import run_enemy_turn, start_player_turn

    state = create_treasure_mimic_combat_state(run_state)

    while not state.is_victory() and not state.is_defeat():
        start_player_turn(state, run_state.rng)
        player_action_loop(state)

        if state.is_victory() or state.is_defeat():
            break

        run_enemy_turn(state)

    return state


def resolve_treasure_node(run_state: RunState) -> None:
    console.print()
    console.print(
        Panel(
            "A heavy chest sits in the corridor. It looks valuable, smug, and possibly employed.",
            title="Treasure Chest",
        )
    )

    if run_state.rng.random() < run_state.mimic_chance:
        console.print("[bold red]The chest was a Mimic![/bold red]")

        state = run_treasure_mimic_combat(run_state)

        console.print()
        print_combat_state(state)
        print_full_log(state)

        if state.is_defeat():
            run_state.current_hp = 0
            console.print("[bold red]Defeat. The chest has filed you under snacks.[/bold red]")
            return

        finish_victorious_combat(run_state, state)
        console.print("[bold green]The Mimic is defeated.[/bold green]")
        grant_random_relic(run_state)
        return

    grant_random_relic(run_state)
    complete_current_map_node(run_state)
