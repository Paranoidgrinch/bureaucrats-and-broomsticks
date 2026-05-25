from collections import Counter

from bab.content.catalog import load_content_catalog_from_act_manifest


TARGET_ENCOUNTERS = {
    "easy": 12,
    "normal": 21,
    "elite": 11,
    "boss": 7,
}


EXPECTED_NEW_ENEMIES = {
    "blue_slip_sprite",
    "booklice_cloud",
    "sleepy_stamp_golem",
    "unpaid_margin_note",
    "sorting_raven",
    "pencil_mandrake",
    "bookplate_ghost",
    "oathbound_indexer",
    "mildew_scholar",
    "brass_return_slot",
    "erasure_dryad",
    "red_string_oracle",
    "cupboard_of_minor_dooms",
    "untranslated_codex",
    "queue_of_one",
    "errata_jackal",
    "silence_enforcer",
    "redaction_sphinx",
    "rolling_stacks_colossus",
    "drawer_of_infinite_returns_mimic",
    "catalogue_trolley_mimic",
    "curator_of_misplaced_hours",
    "shelf_that_shelves_back",
    "catalogue_of_unwise_names",
    "auditor_of_returned_lives",
}


EXPECTED_NEW_ENCOUNTERS = {
    "archive_easy_06",
    "archive_easy_07",
    "archive_easy_08",
    "archive_easy_09",
    "archive_easy_10",
    "archive_easy_11",
    "archive_easy_12",
    "archive_normal_13",
    "archive_normal_14",
    "archive_normal_15",
    "archive_normal_16",
    "archive_normal_17",
    "archive_normal_18",
    "archive_normal_19",
    "archive_normal_20",
    "archive_normal_21",
    "archive_elite_06",
    "archive_elite_07",
    "archive_elite_08",
    "archive_elite_09",
    "archive_elite_10",
    "archive_boss_04",
    "archive_boss_05",
    "archive_boss_06",
    "archive_boss_07",
}


def test_act_2_encounter_counts_match_plus_30_percent_targets() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    counts = Counter(
        encounter.difficulty
        for encounter in catalog.encounter_database.values()
        if encounter.act == 2
    )

    for difficulty, target in TARGET_ENCOUNTERS.items():
        assert counts[difficulty] == target


def test_new_act_2_enemies_and_encounters_are_loaded() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    assert EXPECTED_NEW_ENEMIES.issubset(catalog.enemy_database)
    assert EXPECTED_NEW_ENCOUNTERS.issubset(catalog.encounter_database)


def test_act_2_encounters_reference_existing_enemies() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for encounter in catalog.encounter_database.values():
        if encounter.act != 2:
            continue

        assert encounter.enemies
        for enemy_id in encounter.enemies:
            assert enemy_id in catalog.enemy_database


def test_act_2_mimic_variety_is_present_but_not_bosses() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    mimic_enemies = [
        enemy
        for enemy in catalog.enemy_database.values()
        if "mimic" in enemy.tags and "archive" in enemy.tags
    ]

    assert len(mimic_enemies) >= 3
    assert all("boss" not in enemy.tags for enemy in mimic_enemies)
    assert any(enemy.id == "sealed_cabinet_mimic" for enemy in mimic_enemies)
    assert any(enemy.id == "drawer_of_infinite_returns_mimic" for enemy in mimic_enemies)
    assert any(enemy.id == "catalogue_trolley_mimic" for enemy in mimic_enemies)


def test_new_act_2_enemies_are_archive_themed_and_use_cycle_intents() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for enemy_id in EXPECTED_NEW_ENEMIES:
        enemy = catalog.enemy_database[enemy_id]

        assert "archive" in enemy.tags
        assert enemy.intent_pattern == "cycle"
        assert enemy.max_hp > 0
        assert enemy.intents
