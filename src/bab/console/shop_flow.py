"""Console shop flow."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from bab.console.io import console
from bab.models import RelicDefinition
from bab.run.state import RunState
from bab.systems.card_removal import remove_card_from_deck, removable_card_indices
from bab.systems.relics import apply_relic_pickup_effects
from bab.systems.shop import (
    ShopCardOffer,
    ShopRelicOffer,
    card_removal_price,
    choose_shop_card_offers,
    choose_shop_relic_offers,
)


def open_shop(run_state: RunState) -> None:
    card_offers = choose_shop_card_offers(
        run_state.card_database,
        run_state.rng,
        card_class=run_state.character_class.id,
        act=run_state.act,
        fight_number=run_state.fight_number,
        count=3,
    )
    relic_offers = choose_shop_relic_offers(
        run_state.relic_database,
        run_state.relics,
        run_state.rng,
        act=run_state.act,
        fight_number=run_state.fight_number,
        count=2,
    )

    purchased_card_indices: set[int] = set()
    purchased_relic_indices: set[int] = set()
    card_removal_purchased = False

    console.print(
        Panel(
            "A vendor displays stamped wares, each price backed by excessive paperwork. "
            "Buy as much as you can afford, then leave.",
            title="Shop",
        )
    )

    while True:
        print_shop_offers(
            run_state,
            card_offers=card_offers,
            relic_offers=relic_offers,
            purchased_card_indices=purchased_card_indices,
            purchased_relic_indices=purchased_relic_indices,
            card_removal_purchased=card_removal_purchased,
        )

        command = console.input(
            "[bold yellow]Buy c#, buy r#, 'remove', or 'leave': [/bold yellow]"
        ).strip().lower()

        if command in {"leave", "l", "quit", "q"}:
            console.print("[yellow]You leave the shop.[/yellow]")
            return

        if command == "remove":
            if card_removal_purchased:
                console.print("[yellow]Card removal has already been purchased here.[/yellow]")
                continue

            removed = offer_shop_card_removal(run_state)

            if removed:
                card_removal_purchased = True

            continue

        if len(command) < 2:
            console.print("[red]Invalid shop command.[/red]")
            continue

        offer_type = command[0]
        offer_index_text = command[1:]

        if not offer_index_text.isdigit():
            console.print("[red]Invalid shop offer number.[/red]")
            continue

        offer_index = int(offer_index_text)

        if offer_type == "c":
            if offer_index in purchased_card_indices:
                console.print("[yellow]That card has already been purchased.[/yellow]")
                continue

            if offer_index < 0 or offer_index >= len(card_offers):
                console.print("[red]Invalid card offer.[/red]")
                continue

            bought = buy_shop_card_offer(run_state, card_offers[offer_index])

            if bought:
                purchased_card_indices.add(offer_index)

            continue

        if offer_type == "r":
            if offer_index in purchased_relic_indices:
                console.print("[yellow]That relic has already been purchased.[/yellow]")
                continue

            if offer_index < 0 or offer_index >= len(relic_offers):
                console.print("[red]Invalid relic offer.[/red]")
                continue

            bought = buy_shop_relic_offer(run_state, relic_offers[offer_index])

            if bought:
                purchased_relic_indices.add(offer_index)

            continue

        console.print("[red]Invalid shop command.[/red]")


def print_shop_offers(
    run_state: RunState,
    *,
    card_offers: list[ShopCardOffer],
    relic_offers: list[ShopRelicOffer],
    purchased_card_indices: set[int],
    purchased_relic_indices: set[int],
    card_removal_purchased: bool,
) -> None:
    table = Table(title=f"Shop ? Gold: {run_state.gold}")
    table.add_column("Code", style="cyan")
    table.add_column("Type")
    table.add_column("Item")
    table.add_column("Rarity")
    table.add_column("Price", justify="right")
    table.add_column("Description")
    table.add_column("Status")

    for index, offer in enumerate(card_offers):
        status = "sold" if index in purchased_card_indices else "available"
        table.add_row(
            f"c{index}",
            "Card",
            offer.card.name,
            offer.card.rarity,
            str(offer.price),
            offer.card.text,
            status,
        )

    for index, offer in enumerate(relic_offers):
        status = "sold" if index in purchased_relic_indices else "available"
        table.add_row(
            f"r{index}",
            "Relic",
            offer.relic.name,
            offer.relic.rarity,
            str(offer.price),
            offer.relic.description,
            status,
        )

    removal_price = card_removal_price(
        act=run_state.act,
        fight_number=run_state.fight_number,
    )
    table.add_row(
        "remove",
        "Service",
        "Card Removal",
        "-",
        str(removal_price),
        "Remove one card from your deck.",
        "sold" if card_removal_purchased else "available",
    )

    console.print(table)


def buy_shop_card_offer(
    run_state: RunState,
    offer: ShopCardOffer,
) -> bool:
    if run_state.gold < offer.price:
        console.print("[red]Not enough Gold.[/red]")
        return False

    run_state.gold -= offer.price
    run_state.run_deck.append(offer.card)

    console.print(
        f"[green]Bought {offer.card.name} for {offer.price} Gold. "
        f"Gold left: {run_state.gold}.[/green]"
    )
    return True


def buy_shop_relic_offer(
    run_state: RunState,
    offer: ShopRelicOffer,
) -> bool:
    if run_state.gold < offer.price:
        console.print("[red]Not enough Gold.[/red]")
        return False

    if any(relic.id == offer.relic.id for relic in run_state.relics):
        console.print("[yellow]You already own that relic.[/yellow]")
        return False

    run_state.gold -= offer.price
    run_state.relics.append(offer.relic)

    run_state.current_hp, pickup_messages = apply_relic_pickup_effects(
        current_hp=run_state.current_hp,
        max_hp=run_state.character_class.max_hp,
        relic=offer.relic,
    )

    console.print(
        f"[green]Bought {offer.relic.name} for {offer.price} Gold. "
        f"Gold left: {run_state.gold}.[/green]"
    )

    for message in pickup_messages:
        console.print(f"[green]{message}[/green]")

    return True


def offer_shop_card_removal(run_state: RunState) -> bool:
    price = card_removal_price(
        act=run_state.act,
        fight_number=run_state.fight_number,
    )

    if run_state.gold < price:
        console.print("[red]Not enough Gold for card removal.[/red]")
        return False

    removable_indices = removable_card_indices(run_state.run_deck)

    if not removable_indices:
        console.print("[yellow]There are no cards that can be removed.[/yellow]")
        return False

    table = Table(title=f"Card Removal ? Cost: {price} Gold")
    table.add_column("#", justify="right")
    table.add_column("Card", style="cyan")
    table.add_column("Cost", justify="right")
    table.add_column("Type")
    table.add_column("Text")

    visible_options: list[int] = []

    for visible_index, deck_index in enumerate(removable_indices):
        card = run_state.run_deck[deck_index]
        visible_options.append(deck_index)
        table.add_row(
            str(visible_index),
            card.name,
            str(card.cost),
            card.type,
            card.text,
        )

    console.print(table)

    while True:
        command = console.input(
            "[bold yellow]Choose a card to remove or 'skip': [/bold yellow]"
        ).strip().lower()

        if command == "skip":
            console.print("[yellow]No card removed.[/yellow]")
            return False

        if not command.isdigit():
            console.print("[red]Invalid removal choice.[/red]")
            continue

        visible_index = int(command)

        if visible_index < 0 or visible_index >= len(visible_options):
            console.print("[red]Invalid removal number.[/red]")
            continue

        deck_index = visible_options[visible_index]
        removed_card = remove_card_from_deck(run_state.run_deck, deck_index)
        run_state.gold -= price

        console.print(
            f"[green]Removed {removed_card.name} for {price} Gold. "
            f"Gold left: {run_state.gold}.[/green]"
        )
        return True
