from collections import Counter

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.shop import eligible_shop_relics


TARGET_RARITIES = {
    "common": 13,
    "uncommon": 15,
    "rare": 13,
}


SUPPORTED_EFFECT_TYPES = {
    "increase_max_energy",
    "gain_energy_at_combat_start",
    "gain_block_at_combat_start",
    "gain_strength_at_combat_start",
    "heal_at_combat_start",
    "apply_status_to_player_at_combat_start",
    "apply_status_to_all_enemies_at_combat_start",
    "heal_on_pickup",
    "increase_card_reward_count",
    "gain_gold_on_pickup",
    "increase_gold_rewards",
    "shop_price_discount",
}


def test_general_act_2_relic_pool_matches_act_1_general_size() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    act_2_general_relics = [
        relic
        for relic in catalog.relic_database.values()
        if "act_2" in relic.tags
        and "archive" in relic.tags
        and not relic.allowed_classes
    ]

    assert len(act_2_general_relics) == 41

    rarity_counts = Counter(relic.rarity for relic in act_2_general_relics)
    for rarity, target in TARGET_RARITIES.items():
        assert rarity_counts[rarity] == target


def test_general_act_2_relics_are_shop_eligible_and_supported() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    shop_relics = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=2,
        fight_number=4,
    )
    shop_ids = {relic.id for relic in shop_relics}

    act_2_general_relics = [
        relic
        for relic in catalog.relic_database.values()
        if "act_2" in relic.tags
        and "archive" in relic.tags
        and not relic.allowed_classes
    ]

    for relic in act_2_general_relics:
        assert relic.id in shop_ids
        assert relic.rarity != "boss"

        for effect in relic.effects:
            assert effect.type in SUPPORTED_EFFECT_TYPES
