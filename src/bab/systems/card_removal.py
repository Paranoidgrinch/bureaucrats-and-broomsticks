"""Deck card removal helpers."""

from __future__ import annotations

from bab.models import Card


def removable_card_indices(
    deck: list[Card],
    *,
    card_id: str | None = None,
    tag: str | None = None,
) -> list[int]:
    """Return deck indices that may be removed.

    The final card in a deck cannot be removed. Optional filters allow events
    to restrict removal to a specific card id or cards with a specific tag.
    """

    if len(deck) <= 1:
        return []

    indices: list[int] = []

    for index, card in enumerate(deck):
        if card_id is not None and card.id != card_id:
            continue

        if tag is not None and tag not in card.tags:
            continue

        indices.append(index)

    return indices


def remove_card_from_deck(deck: list[Card], deck_index: int) -> Card:
    if len(deck) <= 1:
        raise ValueError("Cannot remove the final card from the deck.")

    if deck_index < 0 or deck_index >= len(deck):
        raise IndexError("Deck index is out of range.")

    return deck.pop(deck_index)
