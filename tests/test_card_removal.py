from bab.models import Card, Effect
from bab.systems.card_removal import remove_card_from_deck, removable_card_indices


def make_card(
    card_id: str,
    name: str,
    *,
    tags: list[str] | None = None,
) -> Card:
    return Card.model_validate(
        {
            "id": card_id,
            "name": name,
            "class": "bureaucrat",
            "type": "action",
            "cost": 1,
            "rarity": "common",
            "text": "Test card.",
            "effects": [
                {
                    "type": "deal_damage",
                    "target": "enemy",
                    "amount": 1,
                }
            ],
            "tags": tags or [],
        }
    )


def test_removable_card_indices_returns_all_cards_when_deck_has_multiple_cards() -> None:
    deck = [
        make_card("card_a", "Card A"),
        make_card("card_b", "Card B"),
    ]

    assert removable_card_indices(deck) == [0, 1]


def test_removable_card_indices_can_filter_by_card_id() -> None:
    deck = [
        make_card("card_a", "Card A"),
        make_card("card_b", "Card B"),
    ]

    assert removable_card_indices(deck, card_id="card_b") == [1]


def test_removable_card_indices_can_filter_by_tag() -> None:
    deck = [
        make_card("card_a", "Card A", tags=["starter"]),
        make_card("card_b", "Card B", tags=["reward"]),
    ]

    assert removable_card_indices(deck, tag="starter") == [0]


def test_removable_card_indices_rejects_final_card() -> None:
    deck = [make_card("card_a", "Card A")]

    assert removable_card_indices(deck) == []


def test_remove_card_from_deck_removes_and_returns_card() -> None:
    deck = [
        make_card("card_a", "Card A"),
        make_card("card_b", "Card B"),
    ]

    removed_card = remove_card_from_deck(deck, 0)

    assert removed_card.id == "card_a"
    assert [card.id for card in deck] == ["card_b"]
