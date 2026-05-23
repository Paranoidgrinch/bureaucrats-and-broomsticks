"""Console waiting-room flow."""

from __future__ import annotations

from math import ceil

from rich.panel import Panel

from bab.console.io import console
from bab.game_config import WAITING_ROOM_HEAL_PERCENT
from bab.console.reward_flow import offer_card_upgrade
from bab.run_map import MapNode
from bab.run_state import RunState, complete_current_map_node


def resolve_waiting_room_node(run_state: RunState) -> None:
    console.print()
    console.print(
        Panel(
            "The Waiting Room smells faintly of dust, old coffee, and postponed decisions.",
            title="Waiting Room",
        )
    )

    table = Table(title="Waiting Room Choices")
    table.add_column("#", justify="right")
    table.add_column("Choice")
    table.add_column("Effect")

    table.add_row(
        "0",
        "Do something productive.",
        "Upgrade one card.",
    )
    table.add_row(
        "1",
        "Take a Nap.",
        f"Heal {WAITING_ROOM_HEAL_PERCENT}% of max HP.",
    )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose a Waiting Room option: [/bold yellow]"
        ).strip().lower()

        if command == "0":
            offer_card_upgrade(run_state)
            break

        if command == "1":
            heal_amount = ceil(
                run_state.character_class.max_hp
                * WAITING_ROOM_HEAL_PERCENT
                / 100
            )
            old_hp = run_state.current_hp
            run_state.current_hp = min(
                run_state.character_class.max_hp,
                run_state.current_hp + heal_amount,
            )
            healed = run_state.current_hp - old_hp
            console.print(
                f"[green]You take a nap and recover {healed} HP. "
                f"Current HP: {run_state.current_hp}/"
                f"{run_state.character_class.max_hp}.[/green]"
            )
            break

        console.print("[red]Invalid Waiting Room choice.[/red]")

    complete_current_map_node(run_state)
