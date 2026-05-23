"""Console event flow."""

from __future__ import annotations

from bab.console.event_effect_handlers import apply_event_effect
from rich.panel import Panel

from bab.console.io import console
from bab.console.views import print_event
from bab.systems.events import choose_random_event
from bab.models import EventChoice, EventDefinition
from bab.run.map import MapNode
from bab.run.state import RunState, complete_current_map_node


def choose_event_choice(event: EventDefinition) -> EventChoice:
    while True:
        command = console.input(
            "[bold yellow]Choose an event option number: [/bold yellow]"
        ).strip().lower()

        if not command.isdigit():
            console.print("[red]Invalid event choice.[/red]")
            continue

        choice_index = int(command)

        if choice_index < 0 or choice_index >= len(event.choices):
            console.print("[red]Invalid event choice number.[/red]")
            continue

        return event.choices[choice_index]


def resolve_event_node(run_state: RunState, node: MapNode) -> None:
    if node.event_type is None:
        raise ValueError("Event node is missing an event type.")

    event = choose_random_event(
        run_state.event_database,
        run_state.rng,
        act=run_state.act,
        event_type=node.event_type,
    )

    print_event(event)
    choice = choose_event_choice(event)

    console.print()
    console.print(Panel(choice.result_text, title="Event Result"))

    for effect in choice.effects:
        apply_event_effect(run_state, effect)

    complete_current_map_node(run_state)
