from collections import Counter, defaultdict

from bab.content.catalog import load_content_catalog_from_act_manifest


BATCH_TARGETS = {
    "bureaucrat": {"common": 3, "uncommon": 3, "rare": 2},
    "failed_wizard": {"common": 4, "uncommon": 3, "rare": 3},
    "guild_assassin_apprentice": {"common": 4, "uncommon": 4, "rare": 3},
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


def test_act_2_class_relics_batch_1_counts_match_targets() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    by_class = defaultdict(list)
    for relic in catalog.relic_database.values():
        if "act_2" not in relic.tags or "class_specific" not in relic.tags:
            continue
        for character_id in relic.allowed_classes:
            by_class[character_id].append(relic)

    for character_id, targets in BATCH_TARGETS.items():
        relics = by_class[character_id]
        rarity_counts = Counter(relic.rarity for relic in relics)

        assert len(relics) == sum(targets.values())

        for rarity, target in targets.items():
            assert rarity_counts[rarity] == target


def test_act_2_class_relics_batch_1_are_class_specific_and_supported() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for relic in catalog.relic_database.values():
        if "act_2" not in relic.tags or "class_specific" not in relic.tags:
            continue

        if relic.allowed_classes[0] not in BATCH_TARGETS:
            continue

        assert len(relic.allowed_classes) == 1
        assert relic.rarity in {"common", "uncommon", "rare"}

        for effect in relic.effects:
            assert effect.type in SUPPORTED_EFFECT_TYPES
