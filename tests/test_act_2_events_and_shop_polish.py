from collections import Counter
from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.console.event_effect_handlers import CONSOLE_EVENT_EFFECT_HANDLERS
from bab.systems.shop import (
    DEFAULT_SHOP_CARD_OFFER_COUNT,
    DEFAULT_SHOP_RELIC_OFFER_COUNT,
    choose_shop_card_offers,
    choose_shop_relic_offers,
    eligible_shop_cards,
    eligible_shop_relics,
)


EXPECTED_NEW_EVENTS = {
    "act_2_misfiled_door",
    "act_2_whispering_catalogue",
    "act_2_librarians_empty_chair",
    "act_2_shelf_that_knows_your_name",
    "act_2_overdue_soul",
    "act_2_index_of_unfinished_jobs",
    "act_2_restricted_reading_room",
    "act_2_ink_well_at_the_bottom",
    "act_2_helpful_footnote",
    "act_2_locked_return_slot",
}


SUPPORTED_EVENT_EFFECTS = {
    "none",
    "gain_card_reward",
    "upgrade_card",
    "lose_percent_max_hp",
    "remove_card",
    "open_shop",
}


CHARACTER_IDS = {
    "bureaucrat",
    "failed_wizard",
    "guild_assassin_apprentice",
    "hedge_witch",
    "mortuary_apprentice",
    "night_watch_recruit",
    "sewer_diplomat",
    "shroomancer",
    "witch_clerk",
}


def test_act_2_has_ten_new_archive_events_loaded() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    assert EXPECTED_NEW_EVENTS.issubset(catalog.event_database)

    act_2_events = [
        event
        for event in catalog.event_database.values()
        if event.act == 2 and "archive" in event.tags
    ]
    assert len(act_2_events) >= 23


def test_act_2_events_use_supported_implemented_effects() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for event in catalog.event_database.values():
        if event.act != 2:
            continue

        assert event.choices
        assert "archive" in event.tags

        for choice in event.choices:
            assert choice.result_text

            for effect in choice.effects:
                assert effect.type in SUPPORTED_EVENT_EFFECTS
                assert effect.type in CONSOLE_EVENT_EFFECT_HANDLERS
                assert effect.type != "gain_max_hp"


def test_new_act_2_events_have_meaningful_choice_structure() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for event_id in EXPECTED_NEW_EVENTS:
        event = catalog.event_database[event_id]

        assert len(event.choices) >= 3

        effectful_choices = [
            choice
            for choice in event.choices
            if choice.effects
        ]
        safe_choices = [
            choice
            for choice in event.choices
            if not choice.effects
        ]

        assert effectful_choices
        assert safe_choices


def test_act_2_shop_explicitly_excludes_epic_cards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        cards = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=2,
            fight_number=6,
        )
        offers = choose_shop_card_offers(
            catalog.card_database,
            Random(12345),
            card_class=character_id,
            act=2,
            fight_number=6,
        )

        assert all(card.rarity != "epic" for card in cards)
        assert all("epic" not in card.tags for card in cards)
        assert len(offers) == DEFAULT_SHOP_CARD_OFFER_COUNT
        assert all(offer.card.rarity != "epic" for offer in offers)


def test_act_2_shop_filters_class_specific_relics_by_character() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        relics = eligible_shop_relics(
            catalog.relic_database,
            owned_relics=[],
            act=2,
            fight_number=6,
            card_class=character_id,
        )
        offers = choose_shop_relic_offers(
            catalog.relic_database,
            owned_relics=[],
            rng=Random(54321),
            act=2,
            fight_number=6,
            card_class=character_id,
        )

        assert len(offers) == DEFAULT_SHOP_RELIC_OFFER_COUNT

        for relic in relics:
            assert not relic.allowed_classes or character_id in relic.allowed_classes

        for offer in offers:
            relic = offer.relic
            assert not relic.allowed_classes or character_id in relic.allowed_classes


def test_act_2_shop_prefers_act_2_content_available_for_each_class() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        cards = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=2,
            fight_number=6,
        )
        relics = eligible_shop_relics(
            catalog.relic_database,
            owned_relics=[],
            act=2,
            fight_number=6,
            card_class=character_id,
        )

        assert any("act_2" in card.tags for card in cards)
        assert any("act_2" in relic.tags for relic in relics)
