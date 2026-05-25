from random import Random

from bab.console.run_flow import create_run_state
from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.systems.shop import (
    DEFAULT_SHOP_CARD_OFFER_COUNT,
    DEFAULT_SHOP_RELIC_OFFER_COUNT,
    choose_shop_card_offers,
    choose_shop_relic_offers,
    eligible_shop_cards,
    eligible_shop_relics,
)


def _catalog_has_shop(catalog) -> bool:
    return any("shop" in event.tags for event in catalog.event_database.values())


def test_each_act_with_shop_has_enough_eligible_shop_cards_for_default_offer_count() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        if not _catalog_has_shop(catalog):
            continue

        for character_class_id in catalog.character_classes:
            eligible_cards = eligible_shop_cards(
                catalog.card_database,
                card_class=character_class_id,
                act=catalog.act_manifest.act,
                fight_number=1,
            )

            assert len(eligible_cards) >= DEFAULT_SHOP_CARD_OFFER_COUNT, (
                f"{catalog.act_manifest.id}/{character_class_id} has only "
                f"{len(eligible_cards)} eligible shop cards."
            )


def test_each_act_with_shop_has_enough_eligible_shop_relics_for_default_offer_count() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        if not _catalog_has_shop(catalog):
            continue

        eligible_relics = eligible_shop_relics(
            catalog.relic_database,
            [],
            act=catalog.act_manifest.act,
            fight_number=1,
        )

        assert len(eligible_relics) >= DEFAULT_SHOP_RELIC_OFFER_COUNT, (
            f"{catalog.act_manifest.id} has only "
            f"{len(eligible_relics)} eligible shop relics."
        )


def test_shop_generates_default_number_of_card_and_relic_offers() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        if not _catalog_has_shop(catalog):
            continue

        run_state = create_run_state(catalog=catalog, rng=Random(1))

        card_offers = choose_shop_card_offers(
            run_state.card_database,
            run_state.rng,
            card_class=run_state.character_class.id,
            act=run_state.act,
            fight_number=run_state.fight_number,
            count=DEFAULT_SHOP_CARD_OFFER_COUNT,
        )
        relic_offers = choose_shop_relic_offers(
            run_state.relic_database,
            run_state.relics,
            run_state.rng,
            act=run_state.act,
            fight_number=run_state.fight_number,
            count=DEFAULT_SHOP_RELIC_OFFER_COUNT,
        )

        assert len(card_offers) == DEFAULT_SHOP_CARD_OFFER_COUNT
        assert len(relic_offers) == DEFAULT_SHOP_RELIC_OFFER_COUNT
