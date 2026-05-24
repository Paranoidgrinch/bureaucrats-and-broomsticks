from bab.content.catalog import load_content_catalog_from_act_manifest


def test_act_2_has_substantial_elite_pool() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    elite_enemies = [
        enemy
        for enemy in catalog.enemy_database.values()
        if "archive" in enemy.tags and "elite" in enemy.tags
    ]

    assert len(elite_enemies) >= 5
    assert "shelf_golem" in catalog.enemy_database
    assert "chain_catalogue_serpent" in catalog.enemy_database
    assert "overdue_oathkeeper" in catalog.enemy_database
    assert "archivist_lich" in catalog.enemy_database
    assert "sealed_cabinet_mimic" in catalog.enemy_database


def test_act_2_has_multiple_non_mimic_elite_encounters() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    elite_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.act == 2 and encounter.difficulty == "elite"
    ]

    non_mimic_elite_encounters = []
    for encounter in elite_encounters:
        encounter_enemies = [
            catalog.enemy_database[enemy_id]
            for enemy_id in encounter.enemies
        ]
        if all("mimic" not in enemy.tags for enemy in encounter_enemies):
            non_mimic_elite_encounters.append(encounter)

    assert len(non_mimic_elite_encounters) >= 4


def test_act_2_treasure_mimic_encounter_contains_only_mimics() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    mimic_encounter_id = catalog.act_manifest.treasure.mimic_encounter_id
    mimic_encounter = catalog.encounter_database[mimic_encounter_id]

    assert mimic_encounter.id == "archive_mimic_01"
    assert mimic_encounter.difficulty == "elite"

    for enemy_id in mimic_encounter.enemies:
        enemy = catalog.enemy_database[enemy_id]
        assert "mimic" in enemy.tags
        assert "elite" in enemy.tags


def test_act_2_elite_encounters_use_archive_elite_enemies() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    elite_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.act == 2 and encounter.difficulty == "elite"
    ]

    assert elite_encounters

    for encounter in elite_encounters:
        for enemy_id in encounter.enemies:
            enemy = catalog.enemy_database[enemy_id]
            assert "archive" in enemy.tags
            if encounter.id != catalog.act_manifest.treasure.mimic_encounter_id:
                assert "mimic" not in enemy.tags
