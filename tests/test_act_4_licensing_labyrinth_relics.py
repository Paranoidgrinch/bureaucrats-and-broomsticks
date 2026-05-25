import json
from collections import Counter
from pathlib import Path
from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.relics import card_reward_count_bonus, choose_random_unowned_relic
from bab.systems.shop import eligible_shop_relics


ACT_4_MANIFEST = "data/acts/act_4_licensing_labyrinth.json"
ACT_4_CLASS_RELIC_FILE = Path("data/relics/act_4_licensing_labyrinth_class_relics.json")

EXPECTED_CLASS_RELICS_BY_CLASS = {
    "bureaucrat": {
        "act4_bureaucrat_red_docket_thread",
        "act4_bureaucrat_memory_palace_ledger",
        "act4_bureaucrat_sun_lamp_of_authority",
        "act4_bureaucrat_sealed_water_flask",
        "act4_bureaucrat_cartouche_seal_case",
        "act4_bureaucrat_threaded_reward_map",
    },
    "witch_clerk": {
        "act4_witch_clerk_moonlit_thread_charm",
        "act4_witch_clerk_canopic_tea_lantern",
        "act4_witch_clerk_sandstone_hex_stamp",
        "act4_witch_clerk_burial_mouse_permit",
        "act4_witch_clerk_memory_kettle",
        "act4_witch_clerk_blessed_water_inkpot",
    },
    "night_watch_recruit": {
        "act4_night_watch_recruit_lantern_of_the_inner_stair",
        "act4_night_watch_recruit_approved_patrol_rope",
        "act4_night_watch_recruit_watchmans_water_skin",
        "act4_night_watch_recruit_granite_truncheon",
        "act4_night_watch_recruit_tomb_incident_log",
        "act4_night_watch_recruit_colossus_boots",
    },
    "hedge_witch": {
        "act4_hedge_witch_red_root_thread",
        "act4_hedge_witch_desert_poultice_satchel",
        "act4_hedge_witch_canopic_crow_perch",
        "act4_hedge_witch_memory_herb_tablet",
        "act4_hedge_witch_moon_water_gourd",
        "act4_hedge_witch_scorpion_brew_lamp",
    },
    "guild_assassin_apprentice": {
        "act4_guild_assassin_silk_labyrinth_thread",
        "act4_guild_assassin_death_mask_alibi_case",
        "act4_guild_assassin_black_water_vial",
        "act4_guild_assassin_cartouche_contract_case",
        "act4_guild_assassin_silent_entry_memory_map",
        "act4_guild_assassin_serpent_pin_reliquary",
    },
    "failed_wizard": {
        "act4_failed_wizard_sun_rune_lens",
        "act4_failed_wizard_memory_glyph_tablet",
        "act4_failed_wizard_sealed_water_thaum_flask",
        "act4_failed_wizard_unstable_torch_sconce",
        "act4_failed_wizard_incorrect_hieroglyph_rubbing",
        "act4_failed_wizard_blueprint_that_misremembers",
    },
    "sewer_diplomat": {
        "act4_sewer_diplomat_red_rat_thread",
        "act4_sewer_diplomat_canopic_cheese_cache",
        "act4_sewer_diplomat_hidden_drain_memory_map",
        "act4_sewer_diplomat_black_water_canteen",
        "act4_sewer_diplomat_rat_king_cartouche",
        "act4_sewer_diplomat_tomb_gutter_lantern",
    },
    "mortuary_apprentice": {
        "act4_mortuary_canopic_certificate_box",
        "act4_mortuary_black_linen_thread",
        "act4_mortuary_spirit_lantern_of_the_scale",
        "act4_mortuary_water_for_the_named_dead",
        "act4_mortuary_bone_memory_tablet",
        "act4_mortuary_unfinished_obelisk_record",
    },
    "shroomancer": {
        "act4_shroomancer_red_mycelium_thread",
        "act4_shroomancer_tomb_bloom_satchel",
        "act4_shroomancer_cool_water_mushroom_skin",
        "act4_shroomancer_luminous_mould_lantern",
        "act4_shroomancer_memory_spore_map",
        "act4_shroomancer_canopic_compost_jar",
    },
}


def _relics():
    return json.loads(ACT_4_CLASS_RELIC_FILE.read_text(encoding="utf-8"))


def test_act_4_manifest_loads_class_relic_file() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)

    assert (
        "data/relics/act_4_licensing_labyrinth_class_relics.json"
        in catalog.act_manifest.relic_files
    )

    for relic_ids in EXPECTED_CLASS_RELICS_BY_CLASS.values():
        for relic_id in relic_ids:
            assert relic_id in catalog.relic_database


def test_act_4_class_relics_are_closed_strong_packages() -> None:
    relics = _relics()

    assert len(relics) == 54
    assert Counter(relic["rarity"] for relic in relics) == {
        "rare": 45,
        "uncommon": 9,
    }

    counts_by_class = Counter(relic["allowed_classes"][0] for relic in relics)
    assert counts_by_class == {
        "bureaucrat": 6,
        "witch_clerk": 6,
        "night_watch_recruit": 6,
        "hedge_witch": 6,
        "guild_assassin_apprentice": 6,
        "failed_wizard": 6,
        "sewer_diplomat": 6,
        "mortuary_apprentice": 6,
        "shroomancer": 6,
    }

    for relic in relics:
        assert "act_4" in relic["tags"]
        assert "pyramid" in relic["tags"]
        assert "licensing_labyrinth" in relic["tags"]
        assert "class_specific" in relic["tags"]
        assert relic["allowed_classes"][0] in EXPECTED_CLASS_RELICS_BY_CLASS
        assert relic["effects"]


def test_act_4_class_relics_are_only_eligible_for_their_allowed_class() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)

    for class_id, expected_relic_ids in EXPECTED_CLASS_RELICS_BY_CLASS.items():
        eligible_ids = {
            relic.id
            for relic in eligible_shop_relics(
                catalog.relic_database,
                owned_relics=[],
                act=4,
                fight_number=10,
                card_class=class_id,
            )
        }
        assert expected_relic_ids <= eligible_ids

        for other_class_id, other_relic_ids in EXPECTED_CLASS_RELICS_BY_CLASS.items():
            if other_class_id == class_id:
                continue
            assert not other_relic_ids & eligible_ids


def test_act_4_class_specific_relic_selection_respects_allowed_classes() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)
    class_specific_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if "act_4" in relic.tags and "class_specific" in relic.tags
    }

    for index, class_id in enumerate(EXPECTED_CLASS_RELICS_BY_CLASS):
        for seed in range(10):
            relic = choose_random_unowned_relic(
                class_specific_only,
                owned_relics=[],
                rng=Random(seed + index * 100),
                character_id=class_id,
            )
            assert relic.allowed_classes == [class_id]


def test_act_4_bureaucrat_threaded_reward_map_offsets_reward_restriction() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)
    relic = catalog.relic_database["act4_bureaucrat_threaded_reward_map"]

    assert card_reward_count_bonus([relic]) == 1
