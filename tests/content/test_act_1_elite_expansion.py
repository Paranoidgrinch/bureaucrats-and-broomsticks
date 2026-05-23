from bab.content.catalog import load_default_content_catalog


EXPECTED_ELITE_ENCOUNTERS = {
    "city_elite_01",
    "city_elite_02",
    "city_elite_03",
    "city_elite_04",
    "city_elite_05",
    "city_elite_06",
    "city_elite_07",
    "city_elite_08",
}

EXPECTED_NEW_ELITE_ENEMIES = {
    "counter_of_denial",
    "counter_of_delay",
    "counter_of_certification",
    "archivists_hound",
    "stampede_of_stamps",
    "bailiff_of_writs",
    "bailiff_of_warrants",
    "ink_witch_auditor",
    "licensed_chimera",
}


def test_act_1_has_eight_elite_encounters() -> None:
    catalog = load_default_content_catalog()

    elite_encounter_ids = {
        encounter.id
        for encounter in catalog.encounter_database.values()
        if encounter.difficulty == "elite"
    }

    assert EXPECTED_ELITE_ENCOUNTERS <= elite_encounter_ids
    assert len(elite_encounter_ids) >= 8


def test_new_elite_enemies_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_NEW_ELITE_ENEMIES <= set(catalog.enemy_database)


def test_new_elite_enemies_use_named_multi_action_moves() -> None:
    catalog = load_default_content_catalog()

    for enemy_id in EXPECTED_NEW_ELITE_ENEMIES:
        enemy = catalog.enemy_database[enemy_id]

        assert enemy.intents

        for intent in enemy.intents:
            assert intent.id
            assert intent.name
            assert intent.actions, f"{enemy_id}/{intent.id} should use actions."


def test_all_new_elite_encounters_reference_existing_enemies() -> None:
    catalog = load_default_content_catalog()
    enemy_ids = set(catalog.enemy_database)

    for encounter_id in EXPECTED_ELITE_ENCOUNTERS:
        encounter = catalog.encounter_database[encounter_id]

        assert encounter.difficulty == "elite"
        assert set(encounter.enemies) <= enemy_ids


def test_mimic_elite_still_uses_city_elite_02() -> None:
    catalog = load_default_content_catalog()

    assert catalog.act_manifest.treasure.mimic_encounter_id == "city_elite_02"
    assert "city_elite_02" in catalog.encounter_database
