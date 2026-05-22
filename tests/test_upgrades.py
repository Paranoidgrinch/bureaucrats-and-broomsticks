import pytest

from bab.data_loader import load_card_database
from bab.models import Card
from bab.rewards import build_card_reward_pool
from bab.upgrades import (
    card_can_be_upgraded,
    upgrade_card_in_deck,
    upgradeable_card_indices,
)


def make_card(
    card_id: str,
    *,
    upgrades_to: str | None = None,
    tags: list[str] | None = None,
) -> Card:
    return Card.model_validate(
        {
            "id": card_id,
            "name": card_id.replace("_", " ").title(),
            "class": "bureaucrat",
            "type": "action",
            "cost": 1,
            "rarity": "common",
            "text": "Test card.",
            "effects": [],
            "tags": tags or [],
            "upgrades_to": upgrades_to,
        }
    )


def test_card_can_be_upgraded_when_upgrade_id_exists() -> None:
    card = make_card("paper_cut", upgrades_to="paper_cut_plus")

    assert card_can_be_upgraded(card)


def test_upgradeable_card_indices_returns_only_upgradeable_cards() -> None:
    deck = [
        make_card("paper_cut", upgrades_to="paper_cut_plus"),
        make_card("paper_cut_plus", tags=["upgraded"]),
        make_card("fireball", upgrades_to="fireball_plus"),
    ]

    assert upgradeable_card_indices(deck) == [0, 2]


def test_upgrade_card_in_deck_replaces_card_with_upgrade() -> None:
    card = make_card("paper_cut", upgrades_to="paper_cut_plus")
    upgraded_card = make_card("paper_cut_plus", tags=["upgraded"])
    deck = [card]
    card_database = {
        card.id: card,
        upgraded_card.id: upgraded_card,
    }

    result = upgrade_card_in_deck(deck, card_database, 0)

    assert result.id == "paper_cut_plus"
    assert deck[0].id == "paper_cut_plus"


def test_upgrade_card_in_deck_rejects_non_upgradeable_card() -> None:
    card = make_card("paper_cut_plus", tags=["upgraded"])
    deck = [card]
    card_database = {
        card.id: card,
    }

    with pytest.raises(ValueError, match="cannot be upgraded"):
        upgrade_card_in_deck(deck, card_database, 0)


def test_upgrade_card_in_deck_rejects_missing_upgrade_card() -> None:
    card = make_card("paper_cut", upgrades_to="paper_cut_plus")
    deck = [card]
    card_database = {
        card.id: card,
    }

    with pytest.raises(KeyError, match="Upgrade card not found"):
        upgrade_card_in_deck(deck, card_database, 0)


def test_real_card_database_contains_starter_upgrades() -> None:
    card_database = load_card_database(
        [
            "data/cards/bureaucrat_starter.json",
            "data/cards/bureaucrat_rewards.json",
        ]
    )

    assert card_database["paper_cut"].upgrades_to == "paper_cut_plus"
    assert card_database["paper_cut_plus"].effects[0].amount == 8

    assert card_database["cower_behind_a_desk"].upgrades_to == "cower_behind_a_desk_plus"
    assert card_database["cower_behind_a_desk_plus"].effects[0].amount == 7

    assert card_database["strong_binder"].upgrades_to == "strong_binder_plus"
    assert card_database["strong_binder_plus"].effects[0].amount == 9
    assert card_database["strong_binder_plus"].effects[1].amount == 2

    assert card_database["permit_a38"].upgrades_to == "permit_a38_plus"
    assert card_database["permit_a38_plus"].cost == 1


def test_reward_pool_excludes_upgraded_cards() -> None:
    card_database = {
        "fireball": make_card("fireball", upgrades_to="fireball_plus"),
        "fireball_plus": make_card("fireball_plus", tags=["upgraded"]),
    }

    reward_pool = build_card_reward_pool(card_database)

    assert [card.id for card in reward_pool] == ["fireball"]