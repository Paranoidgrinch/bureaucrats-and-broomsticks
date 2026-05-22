from random import Random

import pytest

from bab.data_loader import load_card_database
from bab.models import Card
from bab.rewards import (
    add_card_reward_to_deck,
    build_card_reward_pool,
    choose_card_rewards,
)


def make_card(
    card_id: str,
    *,
    rarity: str = "common",
) -> Card:
    return Card.model_validate(
        {
            "id": card_id,
            "name": card_id.replace("_", " ").title(),
            "class": "bureaucrat",
            "type": "form",
            "cost": 1,
            "rarity": rarity,
            "text": "Test card.",
            "effects": [],
            "tags": [],
        }
    )


def test_build_card_reward_pool_excludes_starter_cards_by_default() -> None:
    starter_card = make_card("starter_card", rarity="starter")
    common_card = make_card("common_card", rarity="common")
    uncommon_card = make_card("uncommon_card", rarity="uncommon")
    rare_card = make_card("rare_card", rarity="rare")

    card_database = {
        starter_card.id: starter_card,
        common_card.id: common_card,
        uncommon_card.id: uncommon_card,
        rare_card.id: rare_card,
    }

    reward_pool = build_card_reward_pool(card_database)

    assert [card.id for card in reward_pool] == [
        "common_card",
        "uncommon_card",
        "rare_card",
    ]


def test_choose_card_rewards_returns_requested_number_of_unique_cards() -> None:
    card_database = {
        f"reward_{index}": make_card(f"reward_{index}")
        for index in range(5)
    }

    rewards = choose_card_rewards(card_database, Random(1), count=3)

    assert len(rewards) == 3
    assert len({card.id for card in rewards}) == 3


def test_choose_card_rewards_is_deterministic_with_seeded_rng() -> None:
    card_database = {
        f"reward_{index}": make_card(f"reward_{index}")
        for index in range(5)
    }

    first_rewards = choose_card_rewards(card_database, Random(1), count=3)
    second_rewards = choose_card_rewards(card_database, Random(1), count=3)

    assert [card.id for card in first_rewards] == [
        card.id for card in second_rewards
    ]


def test_choose_card_rewards_raises_error_when_count_is_zero() -> None:
    card_database = {
        "reward_1": make_card("reward_1"),
    }

    with pytest.raises(ValueError, match="greater than zero"):
        choose_card_rewards(card_database, Random(1), count=0)


def test_choose_card_rewards_raises_error_when_pool_is_too_small() -> None:
    card_database = {
        "reward_1": make_card("reward_1"),
    }

    with pytest.raises(ValueError, match="Not enough reward cards"):
        choose_card_rewards(card_database, Random(1), count=3)


def test_add_card_reward_to_deck_appends_selected_card() -> None:
    deck = [
        make_card("existing_card"),
    ]
    reward = make_card("new_reward")

    add_card_reward_to_deck(deck, reward)

    assert [card.id for card in deck] == [
        "existing_card",
        "new_reward",
    ]


def test_bureaucrat_reward_data_loads_and_produces_three_rewards() -> None:
    card_database = load_card_database(
        [
            "data/cards/bureaucrat_starter.json",
            "data/cards/bureaucrat_rewards.json",
        ]
    )

    rewards = choose_card_rewards(card_database, Random(1), count=3)

    assert len(rewards) == 3
    assert all(card.class_ == "bureaucrat" for card in rewards)
    assert all(card.rarity != "starter" for card in rewards)