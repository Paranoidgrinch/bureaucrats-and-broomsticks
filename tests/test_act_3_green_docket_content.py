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

def test_act_3_has_thirty_percent_more_dedicated_enemies_than_act_2() -> None:
    import json
    import math
    from collections import Counter
    from pathlib import Path

    def role(enemy: dict) -> str | None:
        tags = set(enemy.get("tags", []))
        if "boss" in tags:
            return "boss"
        if "elite" in tags:
            return "elite"
        if "normal" in tags:
            return "normal"
        return None

    act_2 = json.loads(Path("data/enemies/act_2_archives_enemies.json").read_text(encoding="utf-8"))
    act_3 = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))

    act_2_counts = Counter(role(enemy) for enemy in act_2 if role(enemy))
    act_3_counts = Counter(role(enemy) for enemy in act_3 if role(enemy))

    for enemy_role in ["normal", "elite", "boss"]:
        assert act_3_counts[enemy_role] >= math.ceil(act_2_counts[enemy_role] * 1.3)

def test_all_dedicated_act_3_enemies_are_used_by_act_3_encounters() -> None:
    import json
    from pathlib import Path

    enemies = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))
    encounters = json.loads(Path("data/encounters/act_3_green_docket.json").read_text(encoding="utf-8"))

    dedicated_enemy_ids = {
        enemy["id"]
        for enemy in enemies
        if "act_3" in enemy.get("tags", [])
        and "green_docket" in enemy.get("tags", [])
    }

    used_enemy_ids = {
        enemy_id
        for encounter in encounters
        if encounter.get("act") == 3
        for enemy_id in encounter.get("enemies", [])
    }

    assert dedicated_enemy_ids <= used_enemy_ids

def test_act_3_has_thirty_percent_more_dedicated_enemies_than_act_2_by_role() -> None:
    import json
    import math
    from collections import Counter
    from pathlib import Path

    def role(enemy: dict) -> str | None:
        tags = set(enemy.get("tags", []))
        if "boss" in tags:
            return "boss"
        if "elite" in tags:
            return "elite"
        if "normal" in tags:
            return "normal"
        return None

    act_2 = json.loads(Path("data/enemies/act_2_archives_enemies.json").read_text(encoding="utf-8"))
    act_3 = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))

    act_2_counts = Counter(role(enemy) for enemy in act_2 if role(enemy))
    act_3_counts = Counter(role(enemy) for enemy in act_3 if role(enemy))

    for enemy_role in ["normal", "elite", "boss"]:
        assert act_3_counts[enemy_role] >= math.ceil(act_2_counts[enemy_role] * 1.3)


def test_all_dedicated_act_3_enemies_are_used_by_act_3_encounters() -> None:
    import json
    from pathlib import Path

    enemies = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))
    encounters = json.loads(Path("data/encounters/act_3_green_docket.json").read_text(encoding="utf-8"))

    dedicated_enemy_ids = {
        enemy["id"]
        for enemy in enemies
        if "act_3" in enemy.get("tags", [])
        and "green_docket" in enemy.get("tags", [])
    }

    used_enemy_ids = {
        enemy_id
        for encounter in encounters
        if encounter.get("act") == 3
        for enemy_id in encounter.get("enemies", [])
    }

    assert dedicated_enemy_ids <= used_enemy_ids


def test_act_3_boss_encounters_cover_every_dedicated_act_3_boss() -> None:
    import json
    from pathlib import Path

    enemies = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))
    encounters = json.loads(Path("data/encounters/act_3_green_docket.json").read_text(encoding="utf-8"))

    dedicated_boss_ids = {
        enemy["id"]
        for enemy in enemies
        if "act_3" in enemy.get("tags", [])
        and "green_docket" in enemy.get("tags", [])
        and "boss" in enemy.get("tags", [])
    }

    boss_encounter_enemy_ids = {
        enemy_id
        for encounter in encounters
        if encounter.get("act") == 3
        and encounter.get("difficulty") == "boss"
        for enemy_id in encounter.get("enemies", [])
    }

    assert dedicated_boss_ids <= boss_encounter_enemy_ids


def test_act_3_elite_encounters_cover_every_dedicated_act_3_elite() -> None:
    import json
    from pathlib import Path

    enemies = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))
    encounters = json.loads(Path("data/encounters/act_3_green_docket.json").read_text(encoding="utf-8"))

    dedicated_elite_ids = {
        enemy["id"]
        for enemy in enemies
        if "act_3" in enemy.get("tags", [])
        and "green_docket" in enemy.get("tags", [])
        and "elite" in enemy.get("tags", [])
    }

    elite_encounter_enemy_ids = {
        enemy_id
        for encounter in encounters
        if encounter.get("act") == 3
        and encounter.get("difficulty") == "elite"
        for enemy_id in encounter.get("enemies", [])
    }

    assert dedicated_elite_ids <= elite_encounter_enemy_ids


def test_act_3_has_enough_multi_enemy_normal_encounters() -> None:
    import json
    from pathlib import Path

    encounters = json.loads(Path("data/encounters/act_3_green_docket.json").read_text(encoding="utf-8"))

    multi_enemy_normal_encounters = [
        encounter
        for encounter in encounters
        if encounter.get("act") == 3
        and encounter.get("difficulty") == "normal"
        and len(encounter.get("enemies", [])) >= 2
    ]

    assert len(multi_enemy_normal_encounters) >= 10


def test_act_3_boss_encounters_are_single_boss_showdowns() -> None:
    import json
    from pathlib import Path

    enemies = json.loads(Path("data/enemies/act_3_green_docket_enemies.json").read_text(encoding="utf-8"))
    encounters = json.loads(Path("data/encounters/act_3_green_docket.json").read_text(encoding="utf-8"))

    enemy_tags_by_id = {
        enemy["id"]: set(enemy.get("tags", []))
        for enemy in enemies
    }

    boss_encounters = [
        encounter
        for encounter in encounters
        if encounter.get("act") == 3
        and encounter.get("difficulty") == "boss"
    ]

    assert boss_encounters

    for encounter in boss_encounters:
        assert len(encounter.get("enemies", [])) == 1
        boss_id = encounter["enemies"][0]
        assert "boss" in enemy_tags_by_id[boss_id]

