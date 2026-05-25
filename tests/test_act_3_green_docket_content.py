from collections import Counter
from pathlib import Path
import json

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool


ACT_3_MANIFEST = "data/acts/act_3_green_docket.json"


def test_act_3_green_docket_manifest_uses_green_docket_content_files() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    manifest = catalog.act_manifest

    assert manifest.id == "act_3_green_docket"
    assert manifest.name == "Act III: The Green Docket"
    assert "data/enemies/act_3_green_docket_enemies.json" in manifest.enemy_files
    assert manifest.encounter_files == ["data/encounters/act_3_green_docket.json"]
    assert manifest.treasure.mimic_encounter_id == "green_docket_mimic_01"


def test_act_3_has_longer_elite_heavy_green_docket_map_config() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    map_config = catalog.act_manifest.map

    assert map_config.steps_before_boss == 17
    assert map_config.width == 5
    assert map_config.first_elite_depth == 3
    assert map_config.elite_weight_multiplier == 1.3


def test_act_3_has_dedicated_green_docket_enemy_pool() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    expected_ids = {
        "permit_hare",
        "moss_covered_clerk",
        "swarm_of_authorized_ants",
        "spider_of_minor_clauses",
        "ancient_entitlement",
        "grandmother_web",
        "ant_queen_of_the_proper_line",
        "green_witch_of_provisional_mercy",
        "bureaucratic_hollow_mimic",
        "forest_ombudsman",
    }

    assert expected_ids.issubset(set(catalog.enemy_database))


def test_act_3_has_substantial_green_docket_encounter_pool() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    act_3_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.act == 3
    ]

    counts = Counter(encounter.difficulty for encounter in act_3_encounters)

    assert counts["easy"] >= 8
    assert counts["normal"] >= 18
    assert counts["elite"] >= 7
    assert counts["boss"] >= 3


def test_act_3_encounters_use_green_docket_enemies() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    enemy_data = json.loads(
        Path("data/enemies/act_3_green_docket_enemies.json").read_text(
            encoding="utf-8"
        )
    )
    act_3_enemy_ids = {enemy["id"] for enemy in enemy_data}

    for encounter in catalog.encounter_database.values():
        if encounter.act != 3:
            continue
        assert set(encounter.enemies).issubset(act_3_enemy_ids)


def test_act_3_normal_rewards_still_exclude_epic_transition_cards() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    reward_pool = build_card_reward_pool(catalog.card_database, card_class="bureaucrat")

    assert reward_pool
    assert all(card.rarity != "epic" for card in reward_pool)
    assert all("transition_reward" not in card.tags for card in reward_pool)
