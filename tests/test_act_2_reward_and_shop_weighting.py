from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import (
    build_card_reward_pool,
    card_progression_weight,
    choose_card_rewards,
)
from bab.systems.shop import (
    choose_shop_card_offers,
    choose_shop_relic_offers,
    eligible_shop_cards,
    eligible_shop_relics,
    shop_progression_weight,
)


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


def test_act_2_card_rewards_weight_act_specific_cards_higher() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        act_2_cards = [card for card in reward_pool if "act_2" in card.tags]
        older_cards = [card for card in reward_pool if "act_2" not in card.tags]

        assert act_2_cards
        assert older_cards

        assert all(
            card_progression_weight(card, act=2) == 4
            for card in act_2_cards
        )
        assert all(
            card_progression_weight(card, act=2) == 1
            for card in older_cards
        )


def test_act_2_card_rewards_keep_epics_out_of_normal_rewards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        rewards = choose_card_rewards(
            catalog.card_database,
            Random(1234),
            count=5,
            card_class=character_id,
            act=2,
        )

        assert rewards
        assert all(card.rarity != "epic" for card in rewards)
        assert all("epic" not in card.tags for card in rewards)


def test_act_2_shop_cards_weight_act_specific_cards_higher_and_exclude_epics() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        shop_cards = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=2,
            fight_number=4,
        )

        act_2_cards = [card for card in shop_cards if "act_2" in card.tags]
        older_cards = [card for card in shop_cards if "act_2" not in card.tags]

        assert act_2_cards
        assert older_cards
        assert all(card.rarity != "epic" for card in shop_cards)

        assert all(shop_progression_weight(card, act=2) == 4 for card in act_2_cards)
        assert all(shop_progression_weight(card, act=2) == 1 for card in older_cards)

        offers = choose_shop_card_offers(
            catalog.card_database,
            Random(5678),
            card_class=character_id,
            act=2,
            fight_number=4,
            count=5,
        )

        assert offers
        assert all(offer.card.rarity != "epic" for offer in offers)


def test_act_2_shop_relics_weight_act_specific_relics_higher() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    shop_relics = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=2,
        fight_number=4,
    )

    act_2_relics = [relic for relic in shop_relics if "act_2" in relic.tags]
    older_relics = [relic for relic in shop_relics if "act_2" not in relic.tags]

    assert act_2_relics
    assert older_relics

    assert all(shop_progression_weight(relic, act=2) == 4 for relic in act_2_relics)
    assert all(shop_progression_weight(relic, act=2) == 1 for relic in older_relics)

    offers = choose_shop_relic_offers(
        catalog.relic_database,
        owned_relics=[],
        rng=Random(9012),
        act=2,
        fight_number=4,
        count=3,
    )

    assert offers
    assert all(offer.relic.rarity != "boss" for offer in offers)
