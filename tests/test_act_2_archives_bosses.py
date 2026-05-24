from bab.content.catalog import load_content_catalog_from_act_manifest


def test_act_2_has_three_archive_bosses() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    boss_enemies = [
        enemy
        for enemy in catalog.enemy_database.values()
        if "archive" in enemy.tags and "boss" in enemy.tags
    ]

    assert len(boss_enemies) >= 3
    assert "grand_cross_reference" in catalog.enemy_database
    assert "chief_under_archivist" in catalog.enemy_database
    assert "living_index" in catalog.enemy_database


def test_act_2_has_three_boss_encounters() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    boss_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.act == 2 and encounter.difficulty == "boss"
    ]

    assert len(boss_encounters) >= 3
    assert "archive_boss_01" in catalog.encounter_database
    assert "archive_boss_02" in catalog.encounter_database
    assert "archive_boss_03" in catalog.encounter_database


def test_act_2_boss_encounters_use_only_archive_boss_enemies() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    boss_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.act == 2 and encounter.difficulty == "boss"
    ]

    assert boss_encounters

    for encounter in boss_encounters:
        assert encounter.enemies
        for enemy_id in encounter.enemies:
            enemy = catalog.enemy_database[enemy_id]
            assert "archive" in enemy.tags
            assert "boss" in enemy.tags
            assert "elite" not in enemy.tags
            assert "mimic" not in enemy.tags


def test_act_2_bosses_are_not_reused_as_normal_or_elite_encounters() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    boss_enemy_ids = {
        enemy.id
        for enemy in catalog.enemy_database.values()
        if "boss" in enemy.tags
    }

    for encounter in catalog.encounter_database.values():
        if encounter.act != 2:
            continue
        if encounter.difficulty == "boss":
            continue

        for enemy_id in encounter.enemies:
            assert enemy_id not in boss_enemy_ids
