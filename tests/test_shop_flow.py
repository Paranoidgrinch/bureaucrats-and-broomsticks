from random import Random

from bab.console.run_flow import create_run_state
from bab.console.shop_flow import buy_shop_card_offer
from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.systems.shop import choose_shop_card_offers, choose_shop_relic_offers


def test_shop_card_offers_are_drawn_from_current_act_catalog() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        run_state = create_run_state(catalog=catalog, rng=Random(1))

        offers = choose_shop_card_offers(
            run_state.card_database,
            run_state.rng,
            card_class=run_state.character_class.id,
            act=run_state.act,
            fight_number=run_state.fight_number,
            count=3,
        )

        assert offers
        assert all(offer.card.id in run_state.card_database for offer in offers)
        assert all(offer.card.class_ == run_state.character_class.id for offer in offers)


def test_shop_relic_offers_are_drawn_from_current_act_catalog() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        run_state = create_run_state(catalog=catalog, rng=Random(1))

        offers = choose_shop_relic_offers(
            run_state.relic_database,
            run_state.relics,
            run_state.rng,
            act=run_state.act,
            fight_number=run_state.fight_number,
            count=2,
        )

        assert offers
        assert all(offer.relic.id in run_state.relic_database for offer in offers)


def test_buy_shop_card_offer_spends_gold_and_adds_card_to_deck() -> None:
    run_state = create_run_state(rng=Random(1))

    offer = choose_shop_card_offers(
        run_state.card_database,
        run_state.rng,
        card_class=run_state.character_class.id,
        act=run_state.act,
        fight_number=run_state.fight_number,
        count=1,
    )[0]

    run_state.gold = offer.price

    deck_size_before = len(run_state.run_deck)
    bought = buy_shop_card_offer(run_state, offer)

    assert bought is True
    assert run_state.gold == 0
    assert len(run_state.run_deck) == deck_size_before + 1
    assert run_state.run_deck[-1].id == offer.card.id


def test_buy_shop_card_offer_rejects_insufficient_gold() -> None:
    run_state = create_run_state(rng=Random(1))

    offer = choose_shop_card_offers(
        run_state.card_database,
        run_state.rng,
        card_class=run_state.character_class.id,
        act=run_state.act,
        fight_number=run_state.fight_number,
        count=1,
    )[0]

    run_state.gold = offer.price - 1

    deck_size_before = len(run_state.run_deck)
    bought = buy_shop_card_offer(run_state, offer)

    assert bought is False
    assert run_state.gold == offer.price - 1
    assert len(run_state.run_deck) == deck_size_before
