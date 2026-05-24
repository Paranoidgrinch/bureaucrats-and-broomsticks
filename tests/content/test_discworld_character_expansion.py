from random import Random

from bab.combat.state import CombatState, Combatant
from bab.combat.turns import apply_enemy_turn_end_statuses
from bab.console.run_flow import create_run_state
from bab.content.catalog import load_default_content_catalog
from bab.systems.shop import (
    DEFAULT_SHOP_CARD_OFFER_COUNT,
    eligible_shop_cards,
)


EXPECTED_NEW_CLASSES = {
    "night_watch_recruit",
    "hedge_witch",
    "guild_assassin_apprentice",
    "failed_wizard",
    "sewer_diplomat",
    "mortuary_apprentice",
    "shroomancer",
}


def test_new_discworld_inspired_classes_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_NEW_CLASSES <= set(catalog.character_classes)
    assert catalog.character_classes["shroomancer"].name == "Mike Cellium"


def test_new_classes_can_start_runs_with_their_own_decks() -> None:
    for class_id in EXPECTED_NEW_CLASSES:
        run_state = create_run_state(class_id, rng=Random(1))

        assert run_state.character_class.id == class_id
        assert len(run_state.run_deck) == 10
        assert {card.class_ for card in run_state.run_deck} == {class_id}


def test_new_classes_have_shop_eligible_reward_cards() -> None:
    catalog = load_default_content_catalog()

    for class_id in EXPECTED_NEW_CLASSES:
        eligible_cards = eligible_shop_cards(
            catalog.card_database,
            card_class=class_id,
            act=1,
            fight_number=1,
        )

        assert len(eligible_cards) >= DEFAULT_SHOP_CARD_OFFER_COUNT


def test_poison_status_exists_and_ticks_down_at_enemy_turn_end() -> None:
    catalog = load_default_content_catalog()
    poison = catalog.status_database["poison"]

    enemy = Combatant(
        id="target",
        name="Target",
        max_hp=30,
        hp=30,
    )
    enemy.apply_status("poison", 3)

    state = CombatState(
        player=Combatant(
            id="player",
            name="Player",
            max_hp=50,
            hp=50,
        ),
        enemies=[enemy],
        status_database=catalog.status_database,
    )

    apply_enemy_turn_end_statuses(state)

    assert enemy.hp == 27
    assert enemy.get_status_amount("poison") == 2
    assert poison.name == "Poison"


def test_new_starter_cards_have_upgrade_targets() -> None:
    catalog = load_default_content_catalog()

    for class_id in EXPECTED_NEW_CLASSES:
        starter_cards = [
            card
            for card in catalog.card_database.values()
            if (
                card.class_ == class_id
                and card.rarity == "starter"
                and "upgraded" not in card.tags
                and "generated" not in card.tags
            )
        ]

        assert starter_cards

        for card in starter_cards:
            assert card.upgrades_to is not None
            upgraded_card = catalog.card_database[card.upgrades_to]
            assert "upgraded" in upgraded_card.tags
