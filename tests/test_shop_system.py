from random import Random

from bab.content.catalog import load_default_content_catalog
from bab.systems.shop import (
    card_removal_price,
    card_shop_price,
    choose_shop_card_offers,
    choose_shop_relic_offers,
    relic_shop_price,
    shop_tier,
)


def test_shop_tier_increases_with_run_progress() -> None:
    assert shop_tier(act=1, fight_number=1) == 0
    assert shop_tier(act=5, fight_number=12) > shop_tier(act=1, fight_number=1)


def test_card_shop_price_increases_with_run_progress() -> None:
    catalog = load_default_content_catalog()
    card = next(
        card
        for card in catalog.card_database.values()
        if card.class_ == "bureaucrat"
        and card.rarity == "common"
        and "upgraded" not in card.tags
    )

    early_price = card_shop_price(card, act=1, fight_number=1)
    late_price = card_shop_price(card, act=5, fight_number=12)

    assert late_price > early_price


def test_card_removal_price_increases_with_run_progress_and_repeat_removals() -> None:
    early_price = card_removal_price(act=1, fight_number=1)
    late_price = card_removal_price(act=5, fight_number=12)
    repeated_price = card_removal_price(
        act=1,
        fight_number=1,
        removals_purchased=1,
    )

    assert late_price > early_price
    assert repeated_price > early_price


def test_shop_card_offers_are_class_specific_and_exclude_starters_and_upgrades() -> None:
    catalog = load_default_content_catalog()

    offers = choose_shop_card_offers(
        catalog.card_database,
        Random(1),
        card_class="witch_clerk",
        act=1,
        fight_number=1,
        count=10,
    )

    assert offers
    assert {offer.card.class_ for offer in offers} == {"witch_clerk"}
    assert all(offer.card.rarity != "starter" for offer in offers)
    assert all("upgraded" not in offer.card.tags for offer in offers)
    assert all(offer.price > 0 for offer in offers)


def test_shop_relic_offers_exclude_owned_relics() -> None:
    catalog = load_default_content_catalog()
    owned_relic = next(iter(catalog.relic_database.values()))

    offers = choose_shop_relic_offers(
        catalog.relic_database,
        [owned_relic],
        Random(1),
        act=1,
        fight_number=1,
        count=20,
    )

    assert all(offer.relic.id != owned_relic.id for offer in offers)
    assert all(offer.price > 0 for offer in offers)


def test_relic_shop_price_increases_with_run_progress() -> None:
    catalog = load_default_content_catalog()
    relic = next(iter(catalog.relic_database.values()))

    early_price = relic_shop_price(relic, act=1, fight_number=1)
    late_price = relic_shop_price(relic, act=5, fight_number=12)

    assert late_price > early_price
