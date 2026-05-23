"""Console event flow."""

from __future__ import annotations

from math import ceil

from rich.panel import Panel

from bab.console.io import console
from bab.console.views import print_event
from bab.events import choose_random_event
from bab.models import EventChoice, EventDefinition, EventEffect
from bab.console.reward_flow import offer_card_reward, offer_card_upgrade
from bab.run_map import MapNode
from bab.run_state import RunState, complete_current_map_node


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


def apply_event_effect(run_state: RunState, effect: EventEffect) -> None:
    if effect.type == "none":
        return

    if effect.type == "gain_card_reward":
        amount = effect.amount or 1
        for _ in range(amount):
            offer_card_reward(run_state)
        return

    if effect.type == "upgrade_card":
        amount = effect.amount or 1
        for _ in range(amount):
            offer_card_upgrade(run_state)
        return

    if effect.type == "lose_percent_max_hp":
        percent = effect.amount or 0
        loss = ceil(run_state.character_class.max_hp * percent / 100)
        run_state.current_hp = max(1, run_state.current_hp - loss)
        console.print(
            f"[red]Lost {loss} HP. Current HP: "
            f"{run_state.current_hp}/{run_state.character_class.max_hp}.[/red]"
        )
        return

    if effect.type == "gain_max_hp":
        console.print("[yellow]Max HP events are not implemented yet.[/yellow]")
        return

    if effect.type == "remove_card":
        console.print("[yellow]Card removal is not implemented yet.[/yellow]")
        return

    console.print(f"[yellow]Unhandled event effect: {effect.type}.[/yellow]")


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
