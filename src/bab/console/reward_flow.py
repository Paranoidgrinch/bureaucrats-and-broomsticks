"""Console reward and upgrade flows."""

from __future__ import annotations

from rich.table import Table

from bab.console.io import console
from bab.console.views import print_card_rewards
from bab.systems.relics import card_reward_count_bonus
from bab.systems.rewards import add_card_reward_to_deck, choose_card_rewards
from bab.run.state import RunState
from bab.systems.upgrades import upgrade_card_in_deck, upgradeable_card_indices


def offer_card_reward(run_state: RunState) -> None:
    reward_count = 3 + card_reward_count_bonus(run_state.relics)
    rewards = choose_card_rewards(
        run_state.card_database,
        run_state.rng,
        count=reward_count,
    )

    console.print()
    print_card_rewards(rewards)

    while True:
        command = console.input(
            "[bold yellow]Choose a reward number or 'skip': [/bold yellow]"
        ).strip().lower()

        if command == "skip":
            console.print("[yellow]No reward chosen.[/yellow]")
            return

        if not command.isdigit():
            console.print("[red]Invalid reward choice.[/red]")
            continue

        reward_index = int(command)

        if reward_index < 0 or reward_index >= len(rewards):
            console.print("[red]Invalid reward number.[/red]")
            continue

        selected_reward = rewards[reward_index]
        add_card_reward_to_deck(run_state.run_deck, selected_reward)
        console.print(
            f"[green]Added {selected_reward.name} to deck. "
            f"Current deck size: {len(run_state.run_deck)}.[/green]"
        )
        return


def offer_card_upgrade(run_state: RunState) -> None:
    upgradeable_indices = upgradeable_card_indices(run_state.run_deck)

    if not upgradeable_indices:
        console.print("[yellow]There are no cards that can be upgraded.[/yellow]")
        return

    table = Table(title="Upgradeable Cards")
    table.add_column("#", justify="right")
    table.add_column("Current Card", style="cyan")
    table.add_column("Upgrade")
    table.add_column("Current Text")
    table.add_column("Upgraded Text")

    visible_options: list[int] = []

    for visible_index, deck_index in enumerate(upgradeable_indices):
        card = run_state.run_deck[deck_index]

        if card.upgrades_to is None:
            continue

        upgraded_card = run_state.card_database[card.upgrades_to]
        visible_options.append(deck_index)

        table.add_row(
            str(visible_index),
            card.name,
            upgraded_card.name,
            card.text,
            upgraded_card.text,
        )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose a card to upgrade or 'skip': [/bold yellow]"
        ).strip().lower()

        if command == "skip":
            console.print("[yellow]No card upgraded.[/yellow]")
            return

        if not command.isdigit():
            console.print("[red]Invalid upgrade choice.[/red]")
            continue

        visible_index = int(command)

        if visible_index < 0 or visible_index >= len(visible_options):
            console.print("[red]Invalid upgrade number.[/red]")
            continue

        deck_index = visible_options[visible_index]
        old_card = run_state.run_deck[deck_index]
        upgraded_card = upgrade_card_in_deck(
            run_state.run_deck,
            run_state.card_database,
            deck_index,
        )

        console.print(
            f"[green]Upgraded {old_card.name} into {upgraded_card.name}.[/green]"
        )
        return
