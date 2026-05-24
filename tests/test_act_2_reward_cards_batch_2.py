from collections import Counter

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool
from bab.systems.shop import eligible_shop_cards


TARGETS = {
    "hedge_witch": {"common": 10, "uncommon": 8, "rare": 3},
    "mortuary_apprentice": {"common": 9, "uncommon": 7, "rare": 4},
    "night_watch_recruit": {"common": 9, "uncommon": 8, "rare": 4},
}


def act_2_cards_for(catalog, character_id: str):
    return [
        card
        for card in catalog.card_database.values()
        if card.class_ == character_id
        and "act_2" in card.tags
        and card.rarity in {"common", "uncommon", "rare"}
    ]


def test_batch_2_classes_match_act_1_reward_counts_and_rarities() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id, target_counts in TARGETS.items():
        cards = act_2_cards_for(catalog, character_id)
        counts = Counter(card.rarity for card in cards)

        assert sum(counts.values()) == sum(target_counts.values())

        for rarity, target in target_counts.items():
            assert counts[rarity] == target


def test_batch_2_cards_are_in_rewards_and_shop_but_not_epic() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in TARGETS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        shop_pool = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=2,
            fight_number=4,
        )

        reward_ids = {card.id for card in reward_pool}
        shop_ids = {card.id for card in shop_pool}

        for card in act_2_cards_for(catalog, character_id):
            assert card.id in reward_ids
            assert card.id in shop_ids
            assert card.rarity != "epic"
            assert "archive_reward" in card.tags
