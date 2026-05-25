from collections import Counter
from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.shop import (
    choose_shop_relic_offers,
    eligible_shop_relics,
    shop_progression_weight,
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


def test_act_3_manifest_loads_green_docket_relic_files() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    assert "data/relics/act_3_green_docket_relics.json" in catalog.act_manifest.relic_files
    assert "data/relics/act_3_green_docket_class_relics.json" in catalog.act_manifest.relic_files
    assert "sun_warmed_stone" in catalog.relic_database
    assert "act3_bureaucrat_portable_queue_rope" in catalog.relic_database


def test_act_3_has_substantial_general_relic_pool() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    act_3_general_relics = [
        relic
        for relic in catalog.relic_database.values()
        if "act_3" in relic.tags
        and "green_docket" in relic.tags
        and "class_specific" not in relic.tags
    ]

    counts = Counter(relic.rarity for relic in act_3_general_relics)

    assert len(act_3_general_relics) >= 18
    assert counts["common"] >= 6
    assert counts["uncommon"] >= 5
    assert counts["rare"] >= 5


def test_each_character_gets_act_3_class_specific_relics() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    class_relics = [
        relic
        for relic in catalog.relic_database.values()
        if "act_3" in relic.tags
        and "green_docket" in relic.tags
        and "class_specific" in relic.tags
    ]

    counts = Counter(relic.allowed_classes[0] for relic in class_relics)

    assert set(counts) == CHARACTER_IDS
    assert all(count >= 2 for count in counts.values())


def test_act_3_class_specific_relics_only_offer_to_matching_class() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for character_id in CHARACTER_IDS:
        relic_pool = eligible_shop_relics(
            catalog.relic_database,
            owned_relics=[],
            act=3,
            fight_number=8,
            card_class=character_id,
        )
        wrong_class_relics = [
            relic
            for relic in relic_pool
            if "class_specific" in relic.tags
            and relic.allowed_classes
            and character_id not in relic.allowed_classes
        ]

        assert not wrong_class_relics


def test_act_3_relic_shop_uses_progression_weights() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    relic_pool = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=3,
        fight_number=8,
        card_class="bureaucrat",
    )

    act_3_relics = [relic for relic in relic_pool if "act_3" in relic.tags]
    act_2_relics = [relic for relic in relic_pool if "act_2" in relic.tags]
    older_relics = [
        relic
        for relic in relic_pool
        if "act_2" not in relic.tags and "act_3" not in relic.tags
    ]

    assert act_3_relics
    assert act_2_relics
    assert older_relics

    assert all(shop_progression_weight(relic, act=3) == 6 for relic in act_3_relics)
    assert all(shop_progression_weight(relic, act=3) == 2 for relic in act_2_relics)
    assert all(shop_progression_weight(relic, act=3) == 1 for relic in older_relics)


def test_act_3_relic_shop_can_offer_green_docket_relics() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    offers = choose_shop_relic_offers(
        catalog.relic_database,
        owned_relics=[],
        rng=Random(42),
        act=3,
        fight_number=8,
        card_class="bureaucrat",
        count=5,
    )

    assert offers
    assert all(offer.relic.rarity != "boss" for offer in offers)

    eligible = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=3,
        fight_number=8,
        card_class="bureaucrat",
    )
    assert any("act_3" in relic.tags and "green_docket" in relic.tags for relic in eligible)
