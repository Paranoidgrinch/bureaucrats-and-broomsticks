from bab.content.catalog import load_content_catalog_from_act_manifest


def test_act_2_uses_archive_specific_enemy_pool() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    assert "tax_ghoul" not in catalog.enemy_database
    assert "departmental_mimic" not in catalog.enemy_database
    assert "dust_indexer" in catalog.enemy_database
    assert "whispering_catalogue" in catalog.enemy_database
    assert "sealed_cabinet_mimic" in catalog.enemy_database


def test_act_2_has_substantial_normal_enemy_pool() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    normal_archive_enemies = [
        enemy
        for enemy in catalog.enemy_database.values()
        if "archive" in enemy.tags and "normal" in enemy.tags
    ]

    assert len(normal_archive_enemies) >= 12


def test_act_2_normal_encounters_use_only_normal_archive_enemies() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    normal_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.act == 2 and encounter.difficulty in {"easy", "normal"}
    ]

    assert len(normal_encounters) >= 12

    for encounter in normal_encounters:
        for enemy_id in encounter.enemies:
            enemy = catalog.enemy_database[enemy_id]
            assert "archive" in enemy.tags
            assert "normal" in enemy.tags


def test_act_2_map_is_longer_than_act_1() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    assert catalog.act_manifest.map.steps_before_boss >= 12
    assert catalog.act_manifest.treasure.mimic_chance == 0.05
    assert catalog.act_manifest.treasure.mimic_encounter_id == "archive_mimic_01"
