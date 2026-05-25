from collections import Counter

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool, card_progression_weight
from bab.systems.shop import eligible_shop_cards, shop_progression_weight


ACT_3_MANIFEST = "data/acts/act_3_green_docket.json"
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


def test_act_3_manifest_loads_green_docket_reward_cards() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    assert "data/cards/act_3_green_docket_rewards.json" in catalog.act_manifest.card_files
    assert "act3_bureaucrat_trail_permit" in catalog.card_database
    assert "act3_shroomancer_spore_path" in catalog.card_database


def test_each_character_gets_act_3_reward_cards_with_upgrades() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    act_3_cards = [
        card
        for card in catalog.card_database.values()
        if "act_3" in card.tags and "green_docket_reward" in card.tags
    ]

    counts = Counter(
        card.class_
        for card in act_3_cards
        if "upgraded" not in card.tags
    )

    assert set(counts) == CHARACTER_IDS
    assert all(count >= 2 for count in counts.values())

    for card in act_3_cards:
        if "upgraded" in card.tags:
            continue
        assert card.upgrades_to
        assert card.upgrades_to in catalog.card_database
        upgraded_card = catalog.card_database[card.upgrades_to]
        assert "upgraded" in upgraded_card.tags
        assert upgraded_card.class_ == card.class_


def test_act_3_reward_pool_includes_act_3_cards_and_excludes_upgrades() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )

        act_3_rewards = [
            card
            for card in reward_pool
            if "act_3" in card.tags and "green_docket_reward" in card.tags
        ]

        assert len(act_3_rewards) >= 2
        assert all(card.class_ == character_id for card in act_3_rewards)
        assert all("upgraded" not in card.tags for card in reward_pool)
        assert all(card.rarity != "epic" for card in reward_pool)


def test_act_3_cards_are_weighted_above_act_2_and_older_cards() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        act_3_cards = [card for card in reward_pool if "act_3" in card.tags]
        act_2_cards = [card for card in reward_pool if "act_2" in card.tags]
        older_cards = [
            card
            for card in reward_pool
            if "act_2" not in card.tags and "act_3" not in card.tags
        ]

        assert act_3_cards
        assert act_2_cards
        assert older_cards

        assert all(card_progression_weight(card, act=3) == 6 for card in act_3_cards)
        assert all(card_progression_weight(card, act=3) == 2 for card in act_2_cards)
        assert all(card_progression_weight(card, act=3) == 1 for card in older_cards)


def test_act_3_shop_cards_can_offer_green_docket_cards() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for character_id in CHARACTER_IDS:
        shop_pool = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=3,
            fight_number=7,
        )
        act_3_shop_cards = [
            card
            for card in shop_pool
            if "act_3" in card.tags and "green_docket_reward" in card.tags
        ]

        assert act_3_shop_cards
        assert all(shop_progression_weight(card, act=3) == 6 for card in act_3_shop_cards)
        assert all(card.rarity != "epic" for card in shop_pool)
        assert all("upgraded" not in card.tags for card in shop_pool)

def test_act_3_green_docket_reward_card_count_matches_act_2_by_character() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    act_2_counts = Counter(
        card.class_
        for card in catalog.card_database.values()
        if "act_2" in card.tags
        and "upgraded" not in card.tags
        and card.rarity != "epic"
    )
    act_3_counts = Counter(
        card.class_
        for card in catalog.card_database.values()
        if "act_3" in card.tags
        and "green_docket_reward" in card.tags
        and "upgraded" not in card.tags
        and card.rarity != "epic"
    )

    assert set(act_3_counts) == CHARACTER_IDS
    assert act_3_counts == act_2_counts

