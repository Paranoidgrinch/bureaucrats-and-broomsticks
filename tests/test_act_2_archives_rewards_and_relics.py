from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool
from bab.systems.shop import eligible_shop_cards, eligible_shop_relics


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


def test_act_2_manifest_loads_archive_reward_cards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    assert "act2_archive_cross_reference" in catalog.card_database
    assert "act2_senior_filing_authority" in catalog.card_database
    assert "act2_fungal_appendix" in catalog.card_database


def test_each_character_gets_act_2_reward_cards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        act_2_cards = [
            card
            for card in catalog.card_database.values()
            if card.class_ == character_id and "act_2" in card.tags
        ]

        assert len(act_2_cards) >= 2
        assert all(card.rarity in {"common", "uncommon", "rare"} for card in act_2_cards)
        assert all("epic" not in card.tags for card in act_2_cards)


def test_act_2_normal_reward_pool_includes_act_2_cards_but_not_epics() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )

        assert any("act_2" in card.tags for card in reward_pool)
        assert all(card.rarity != "starter" for card in reward_pool)
        assert all(card.rarity != "boss" for card in reward_pool)
        assert all(card.rarity != "epic" for card in reward_pool)


def test_act_2_shop_card_pool_can_offer_act_2_cards_but_not_epics() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        shop_pool = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=2,
            fight_number=1,
        )

        assert any("act_2" in card.tags for card in shop_pool)
        assert all(card.rarity != "starter" for card in shop_pool)
        assert all(card.rarity != "boss" for card in shop_pool)
        assert all(card.rarity != "epic" for card in shop_pool)


def test_act_2_has_stronger_archive_relic_pool() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    act_2_relics = [
        relic
        for relic in catalog.relic_database.values()
        if "act_2" in relic.tags and "archive" in relic.tags
    ]

    assert len(act_2_relics) >= 10
    assert "iron_bookmark" in catalog.relic_database
    assert "restricted_shelf_key" in catalog.relic_database
    assert "patron_of_the_stacks" in catalog.relic_database


def test_act_2_shop_relic_pool_includes_act_2_relics() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    shop_relics = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=2,
        fight_number=1,
    )

    assert any("act_2" in relic.tags for relic in shop_relics)
    assert all(relic.rarity != "boss" for relic in shop_relics)


def test_act_2_relic_effects_are_supported_existing_effects() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    supported_effects = {
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

    for relic in catalog.relic_database.values():
        if "act_2" not in relic.tags:
            continue

        for effect in relic.effects:
            assert effect.type in supported_effects

