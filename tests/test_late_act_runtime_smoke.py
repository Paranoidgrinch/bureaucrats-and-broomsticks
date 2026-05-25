from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.run.map import generate_act_map
from bab.systems.rewards import build_card_reward_pool, choose_card_rewards
from bab.systems.shop import (
    choose_shop_card_offers,
    choose_shop_relic_offers,
    eligible_shop_cards,
    eligible_shop_relics,
)


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


def test_act_3_catalog_has_layered_reward_card_pool_for_each_class() -> None:
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
        assert all(card.rarity != "epic" for card in reward_pool)
        assert all("transition_reward" not in card.tags for card in reward_pool)


def test_act_3_can_generate_normal_card_rewards_for_each_class() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for index, character_id in enumerate(sorted(CHARACTER_IDS)):
        rewards = choose_card_rewards(
            catalog.card_database,
            Random(10_000 + index),
            count=3,
            card_class=character_id,
            act=3,
        )

        assert len(rewards) == 3
        assert all(card.class_ == character_id for card in rewards)
        assert all(card.rarity != "epic" for card in rewards)
        assert all("upgraded" not in card.tags for card in rewards)


def test_act_3_shop_can_generate_card_and_relic_offers_for_each_class() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for index, character_id in enumerate(sorted(CHARACTER_IDS)):
        card_offers = choose_shop_card_offers(
            catalog.card_database,
            Random(20_000 + index),
            card_class=character_id,
            act=3,
            fight_number=8,
            count=5,
        )
        relic_offers = choose_shop_relic_offers(
            catalog.relic_database,
            owned_relics=[],
            rng=Random(30_000 + index),
            act=3,
            fight_number=8,
            card_class=character_id,
            count=3,
        )

        assert card_offers
        assert relic_offers

        assert all(offer.card.class_ == character_id for offer in card_offers)
        assert all(offer.card.rarity != "epic" for offer in card_offers)
        assert all("upgraded" not in offer.card.tags for offer in card_offers)

        for offer in relic_offers:
            relic = offer.relic
            assert relic.rarity != "boss"
            assert not relic.allowed_classes or character_id in relic.allowed_classes


def test_act_3_shop_pools_contain_current_previous_and_older_content() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    card_pool = eligible_shop_cards(
        catalog.card_database,
        card_class="bureaucrat",
        act=3,
        fight_number=8,
    )
    relic_pool = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=3,
        fight_number=8,
        card_class="bureaucrat",
    )

    assert any("act_3" in card.tags for card in card_pool)
    assert any("act_2" in card.tags for card in card_pool)
    assert any("act_2" not in card.tags and "act_3" not in card.tags for card in card_pool)

    assert any("act_3" in relic.tags for relic in relic_pool)
    assert any("act_2" in relic.tags for relic in relic_pool)
    assert any(
        "act_2" not in relic.tags and "act_3" not in relic.tags
        for relic in relic_pool
    )


def test_act_3_map_runtime_config_is_long_and_elite_heavy() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    map_config = catalog.act_manifest.map

    elite_counts = []
    earliest_elite_depths = []

    for seed in range(100):
        run_map = generate_act_map(
            Random(seed),
            act=3,
            steps_before_boss=map_config.steps_before_boss,
            width=map_config.width,
            first_elite_depth=map_config.first_elite_depth,
            elite_weight_multiplier=map_config.elite_weight_multiplier,
        )

        boss = run_map.get_node(run_map.boss_node_id)
        elites = [
            node
            for node in run_map.nodes.values()
            if node.node_type == "elite"
        ]

        assert boss.depth == 18
        assert elites

        elite_counts.append(len(elites))
        earliest_elite_depths.append(min(node.depth for node in elites))

    assert min(elite_counts) >= 1
    assert sum(elite_counts) / len(elite_counts) >= 5.5
    assert min(earliest_elite_depths) == 3
