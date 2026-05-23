from bab.models import Card


def upgradeable_card_indices(deck: list[Card]) -> list[int]:
    return [
        index
        for index, card in enumerate(deck)
        if card.upgrades_to is not None
    ]


def card_can_be_upgraded(card: Card) -> bool:
    return card.upgrades_to is not None


def upgrade_card_in_deck(
    deck: list[Card],
    card_database: dict[str, Card],
    deck_index: int,
) -> Card:
    if deck_index < 0 or deck_index >= len(deck):
        raise IndexError("Deck index is out of range.")

    card = deck[deck_index]

    if card.upgrades_to is None:
        raise ValueError(f"{card.name} cannot be upgraded.")

    if card.upgrades_to not in card_database:
        raise KeyError(f"Upgrade card not found: {card.upgrades_to}")

    upgraded_card = card_database[card.upgrades_to]
    deck[deck_index] = upgraded_card

    return upgraded_card