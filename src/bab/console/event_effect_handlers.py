"""Console event effect handler registry."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from math import ceil

from bab.console.io import console
from bab.console.reward_flow import offer_card_reward, offer_card_upgrade
from bab.models import EventEffect
from bab.run.state import RunState

ConsoleEventEffectHandler = Callable[[RunState, EventEffect], None]


def apply_event_effect(run_state: RunState, effect: EventEffect) -> None:
    handler = CONSOLE_EVENT_EFFECT_HANDLERS.get(effect.type)

    if handler is None:
        console.print(f"[yellow]Unhandled event effect: {effect.type}.[/yellow]")
        return

    handler(run_state, effect)


def handle_none(run_state: RunState, effect: EventEffect) -> None:
    return


def handle_gain_card_reward(run_state: RunState, effect: EventEffect) -> None:
    amount = effect.amount or 1

    for _ in range(amount):
        offer_card_reward(run_state)


def handle_upgrade_card(run_state: RunState, effect: EventEffect) -> None:
    amount = effect.amount or 1

    for _ in range(amount):
        offer_card_upgrade(run_state)


def handle_lose_percent_max_hp(run_state: RunState, effect: EventEffect) -> None:
    percent = effect.amount or 0
    loss = ceil(run_state.character_class.max_hp * percent / 100)
    run_state.current_hp = max(1, run_state.current_hp - loss)
    console.print(
        f"[red]Lost {loss} HP. Current HP: "
        f"{run_state.current_hp}/{run_state.character_class.max_hp}.[/red]"
    )


def handle_gain_max_hp(run_state: RunState, effect: EventEffect) -> None:
    console.print("[yellow]Max HP events are not implemented yet.[/yellow]")


def handle_remove_card(run_state: RunState, effect: EventEffect) -> None:
    console.print("[yellow]Card removal is not implemented yet.[/yellow]")


CONSOLE_EVENT_EFFECT_HANDLERS: Mapping[str, ConsoleEventEffectHandler] = {
    "none": handle_none,
    "gain_card_reward": handle_gain_card_reward,
    "upgrade_card": handle_upgrade_card,
    "lose_percent_max_hp": handle_lose_percent_max_hp,
    "gain_max_hp": handle_gain_max_hp,
    "remove_card": handle_remove_card,
}
