"""Console run flow.

This module owns the high-level console prototype flow:
creating a run, choosing map nodes, resolving node types, and ending a run.

The lower-level interactive flows are intentionally split into dedicated
modules:
- combat_flow.py
- event_flow.py
- reward_flow.py
- treasure_flow.py
- waiting_room_flow.py
"""

from __future__ import annotations

from random import Random

from rich.panel import Panel

from bab.console.combat_flow import run_single_combat
from bab.console.io import console
from bab.console.views import (
    format_map_node,
    print_available_map_nodes,
    print_combat_state,
    print_full_log,
    print_run_state,
)
from bab.content.catalog import load_default_content_catalog
from bab.console.event_flow import resolve_event_node
from bab.game_config import DEFAULT_MAX_FIGHTS
from bab.console.reward_flow import offer_card_reward
from bab.run.map import MapNode
from bab.run.state import (
    RunState,
    create_new_run,
    enter_map_node,
    finish_victorious_combat,
)
from bab.console.treasure_flow import resolve_treasure_node
from bab.console.waiting_room_flow import resolve_waiting_room_node


def create_run_state() -> RunState:
    rng = Random()
    catalog = load_default_content_catalog()

    return create_new_run(
        character_class=catalog.character_class,
        card_database=catalog.card_database,
        enemy_database=catalog.enemy_database,
        encounter_database=catalog.encounter_database,
        status_database=catalog.status_database,
        event_database=catalog.event_database,
        relic_database=catalog.relic_database,
        rng=rng,
        act=catalog.act_manifest.act,
        max_fights=DEFAULT_MAX_FIGHTS,
        map_steps_before_boss=catalog.act_manifest.map.steps_before_boss,
        map_width=catalog.act_manifest.map.width,
    )


def choose_next_map_node(run_state: RunState) -> MapNode:
    available_nodes = run_state.available_map_nodes()

    while True:
        print_available_map_nodes(run_state)

        command = console.input(
            "[bold yellow]Choose a map node number or 'quit': [/bold yellow]"
        ).strip().lower()

        if command == "quit":
            raise SystemExit("Game quit.")

        if not command.isdigit():
            console.print("[red]Invalid map choice.[/red]")
            continue

        node_index = int(command)

        if node_index < 0 or node_index >= len(available_nodes):
            console.print("[red]Invalid map node number.[/red]")
            continue

        selected_node = available_nodes[node_index]
        enter_map_node(run_state, selected_node.id)
        return selected_node


def resolve_combat_node(run_state: RunState, node: MapNode) -> None:
    state = run_single_combat(run_state)

    console.print()
    print_combat_state(state)
    print_full_log(state)

    if state.is_defeat():
        run_state.current_hp = 0
        console.print("[bold red]Defeat. The bureaucracy was insufficient.[/bold red]")
        return

    finish_victorious_combat(run_state, state)

    if node.node_type == "boss":
        console.print("[bold green]Boss defeated! The act is complete.[/bold green]")
        return

    console.print("[bold green]Victory! The paperwork has prevailed.[/bold green]")
    offer_card_reward(run_state)


def resolve_map_node(run_state: RunState, node: MapNode) -> None:
    console.print()
    console.print(Panel(format_map_node(node), title="Entering Map Node"))

    if node.node_type in {"combat", "elite", "boss"}:
        resolve_combat_node(run_state, node)
        return

    if node.node_type == "event":
        resolve_event_node(run_state, node)
        return

    if node.node_type == "waiting_room":
        resolve_waiting_room_node(run_state)
        return
    
    if node.node_type == "treasure":
        resolve_treasure_node(run_state)
        return

    raise ValueError(f"Unsupported map node type: {node.node_type}")


def run_console_app() -> None:
    console.print("[bold green]Bureaucrats and Broomsticks[/bold green]")
    console.print("Interactive map prototype started.\n")

    run_state = create_run_state()

    while not run_state.is_complete() and not run_state.is_defeated():
        console.print()
        print_run_state(run_state)

        node = choose_next_map_node(run_state)
        resolve_map_node(run_state, node)

    console.print()
    print_run_state(run_state)

    if run_state.is_complete():
        console.print("[bold green]Run complete! The office survives another day.[/bold green]")
    elif run_state.is_defeated():
        console.print("[bold red]Run failed. The paperwork remains unfinished.[/bold red]")
