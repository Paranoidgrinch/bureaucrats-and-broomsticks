from random import Random

import pytest

from bab.console.run_flow import create_run_state
from bab.content.catalog import load_default_content_catalog
from bab.systems.rewards import choose_card_rewards


def test_create_run_state_uses_default_character_class() -> None:
    run_state = create_run_state()

    assert run_state.character_class.id == "bureaucrat"
    assert run_state.current_hp == run_state.character_class.max_hp
    assert run_state.run_deck


def test_create_run_state_can_start_as_witch_clerk() -> None:
    run_state = create_run_state("witch_clerk")

    assert run_state.character_class.id == "witch_clerk"
    assert run_state.character_class.name == "Witch Clerk"
    assert run_state.current_hp == run_state.character_class.max_hp
    assert {card.class_ for card in run_state.run_deck} == {"witch_clerk"}


def test_create_run_state_rejects_unknown_character_class() -> None:
    with pytest.raises(ValueError, match="Unknown character class"):
        create_run_state("not_a_real_class")


def test_witch_clerk_rewards_only_include_witch_clerk_cards() -> None:
    catalog = load_default_content_catalog()

    rewards = choose_card_rewards(
        catalog.card_database,
        Random(1),
        count=3,
        card_class="witch_clerk",
    )

    assert rewards
    assert {card.class_ for card in rewards} == {"witch_clerk"}


def test_bureaucrat_rewards_only_include_bureaucrat_cards() -> None:
    catalog = load_default_content_catalog()

    rewards = choose_card_rewards(
        catalog.card_database,
        Random(1),
        count=3,
        card_class="bureaucrat",
    )

    assert rewards
    assert {card.class_ for card in rewards} == {"bureaucrat"}
