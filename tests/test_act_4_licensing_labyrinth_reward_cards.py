import json
from collections import Counter
from pathlib import Path
from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool, choose_card_rewards


ACT_4_MANIFEST = "data/acts/act_4_licensing_labyrinth.json"
ACT_4_REWARD_FILE = Path("data/cards/act_4_licensing_labyrinth_rewards.json")

EXPECTED_BASE_CARDS_BY_CLASS = {
    "bureaucrat": {
        "burial_license_appeal",
        "cartouche_of_authority",
        "weigh_the_application",
        "final_authorization",
    },
    "witch_clerk": {
        "canopic_tea_ward",
        "moonlit_cartouche_hex",
        "burial_shaft_familiar",
        "forbidden_canopic_copy",
    },
    "night_watch_recruit": {
        "sealed_stair_patrol",
        "torchlit_trespass_notice",
        "summon_tomb_constables",
        "riot_act_of_the_dead",
    },
    "hedge_witch": {
        "desert_poultice_cache",
        "canopic_knot_charm",
        "scorpion_jar_brew",
        "featherless_omen",
    },
    "guild_assassin_apprentice": {
        "cartouche_contract",
        "silent_tomb_entry",
        "poisoned_burial_pin",
        "death_mask_alibi",
    },
    "failed_wizard": {
        "borrowed_sun_rune",
        "pyramid_fragment_cascade",
        "incorrect_hieroglyph",
        "sarcophagus_backfire",
    },
    "sewer_diplomat": {
        "rat_envoy_to_the_afterlife",
        "canopic_cheese_favour",
        "hidden_drain_under_the_tomb",
        "mummified_rat_king_favour",
    },
    "mortuary_apprentice": {
        "canopic_death_certificate",
        "black_ribbon_of_the_scale",
        "weigh_the_named_remains",
        "unfinished_burial_record",
    },
    "shroomancer": {
        "tomb_bloom_spores",
        "mycelium_under_the_pyramid",
        "canopic_compost_conditions",
        "pharaohs_rot_garden",
    },
}


def _cards():
    return json.loads(ACT_4_REWARD_FILE.read_text(encoding="utf-8"))


def test_act_4_reward_cards_are_closed_pyramid_packages_by_class() -> None:
    cards = _cards()

    assert len(cards) == 72
    assert set(EXPECTED_BASE_CARDS_BY_CLASS) == {card["class"] for card in cards}

    counts_by_class = Counter(card["class"] for card in cards)
    assert counts_by_class == {
        "bureaucrat": 8,
        "witch_clerk": 8,
        "night_watch_recruit": 8,
        "hedge_witch": 8,
        "guild_assassin_apprentice": 8,
        "failed_wizard": 8,
        "sewer_diplomat": 8,
        "mortuary_apprentice": 8,
        "shroomancer": 8,
    }

    for card in cards:
        assert "act_4" in card["tags"]
        assert "pyramid" in card["tags"]
        assert "licensing_labyrinth" in card["tags"]
        assert card["rarity"] in {"uncommon", "rare"}

    base_cards = [card for card in cards if "upgraded" not in card["tags"]]
    assert len(base_cards) == 36
    assert sum(card["rarity"] == "rare" for card in base_cards) == 27
    assert sum(card["rarity"] == "uncommon" for card in base_cards) == 9

    card_ids = {card["id"] for card in cards}
    for card in base_cards:
        assert card["upgrades_to"] in card_ids


def test_act_4_reward_cards_load_into_catalog_and_class_pools() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)

    for class_id, expected_ids in EXPECTED_BASE_CARDS_BY_CLASS.items():
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=class_id,
        )
        act_4_rewards = {
            card.id for card in reward_pool if "act_4" in card.tags
        }

        assert act_4_rewards == expected_ids

        for card_id in expected_ids:
            card = catalog.card_database[card_id]
            assert card.class_ == class_id
            assert "act_4" in card.tags
            assert "upgraded" not in card.tags


def test_act_4_supported_classes_can_receive_two_card_rewards() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)

    for index, class_id in enumerate(EXPECTED_BASE_CARDS_BY_CLASS):
        rewards = choose_card_rewards(
            catalog.card_database,
            Random(44_004 + index),
            count=catalog.act_manifest.rewards.card_choices,
            card_class=class_id,
            act=4,
        )

        assert len(rewards) == 2
        assert all(card.class_ == class_id for card in rewards)
        assert all(card.rarity != "epic" for card in rewards)
        assert all("upgraded" not in card.tags for card in rewards)
