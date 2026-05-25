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
from rich.table import Table

from bab.console.combat_flow import run_single_combat
from bab.console.io import console
from bab.console.views import (
    format_map_node,
    print_available_map_nodes,
    print_combat_state,
    print_full_log,
    print_run_state,
)
from bab.content.catalog import ContentCatalog, load_default_content_catalog
from bab.console.event_flow import resolve_event_node
from bab.game_config import DEFAULT_MAX_FIGHTS
from bab.systems.act_progression import advance_to_next_act, has_next_act
from bab.models import CharacterClass
from bab.console.reward_flow import offer_card_reward, offer_epic_card_reward
from bab.run.map import MapNode
from bab.run.state import (
    RunState,
    create_new_run,
    enter_map_node,
    finish_victorious_combat,
)
from bab.console.treasure_flow import resolve_treasure_node
from bab.console.waiting_room_flow import resolve_waiting_room_node


def resolve_character_class(
    catalog: ContentCatalog,
    character_class_id: str | None,
) -> CharacterClass:
    if character_class_id is None:
        return catalog.character_class

    try:
        return catalog.character_classes[character_class_id]
    except KeyError as exc:
        available_ids = ", ".join(sorted(catalog.character_classes))
        raise ValueError(
            f"Unknown character class {character_class_id!r}. "
            f"Available character classes: {available_ids}."
        ) from exc


def create_run_state(
    character_class_id: str | None = None,
    *,
    catalog: ContentCatalog | None = None,
    rng: Random | None = None,
) -> RunState:
    if rng is None:
        rng = Random()

    if catalog is None:
        catalog = load_default_content_catalog()

    character_class = resolve_character_class(catalog, character_class_id)

    return create_new_run(
        character_class=character_class,
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
        map_first_elite_depth=catalog.act_manifest.map.first_elite_depth,
        map_elite_weight_multiplier=catalog.act_manifest.map.elite_weight_multiplier,
        mimic_chance=catalog.act_manifest.treasure.mimic_chance,
        treasure_mimic_encounter_id=catalog.act_manifest.treasure.mimic_encounter_id,
        waiting_room_heal_percent=catalog.act_manifest.waiting_room.heal_percent,
        card_reward_choices=catalog.act_manifest.rewards.card_choices,
    )


def choose_character_class(
    catalog: ContentCatalog,
    rng: Random,
) -> CharacterClass | None:
    character_classes = list(catalog.character_classes.values())

    if not character_classes:
        raise ValueError("No character classes are available.")

    console.print(
        Panel(
            "Choose who will brave the office today. "
            "Press Enter for the default character or type 'random'.",
            title="Character Selection",
        )
    )

    table = Table(title="Available Characters")
    table.add_column("#", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("HP", justify="right")
    table.add_column("Energy", justify="right")
    table.add_column("Deck", justify="right")
    table.add_column("ID")

    for index, character_class in enumerate(character_classes):
        default_marker = " [default]" if character_class.id == catalog.character_class.id else ""
        table.add_row(
            str(index),
            f"{character_class.name}{default_marker}",
            str(character_class.max_hp),
            str(character_class.starting_energy),
            str(len(character_class.starting_deck)),
            character_class.id,
        )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose a character number, 'random', Enter for default, or 'quit': [/bold yellow]"
        ).strip().lower()

        if command in {"quit", "q"}:
            return None

        if command == "":
            selected_character = catalog.character_class
            console.print(f"[green]Selected {selected_character.name}.[/green]")
            return selected_character

        if command in {"random", "r"}:
            selected_character = rng.choice(character_classes)
            console.print(f"[green]Randomly selected {selected_character.name}.[/green]")
            return selected_character

        if not command.isdigit():
            console.print("[red]Invalid character choice.[/red]")
            continue

        character_index = int(command)

        if character_index < 0 or character_index >= len(character_classes):
            console.print("[red]Invalid character number.[/red]")
            continue

        selected_character = character_classes[character_index]
        console.print(f"[green]Selected {selected_character.name}.[/green]")
        return selected_character


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
        if has_next_act(run_state):
            offer_epic_card_reward(run_state)
            if advance_to_next_act(run_state):
                console.print(
                    f"[bold green]You are fully healed. Act {run_state.act} begins.[/bold green]"
                )
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

    catalog = load_default_content_catalog()
    rng = Random()
    selected_character_class = choose_character_class(catalog, rng)

    if selected_character_class is None:
        console.print("[yellow]Game quit.[/yellow]")
        return

    run_state = create_run_state(
        selected_character_class.id,
        catalog=catalog,
        rng=rng,
    )

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
