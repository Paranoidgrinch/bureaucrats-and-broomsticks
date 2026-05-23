from bab.content.catalog import load_default_content_catalog


EXPECTED_NEW_ACT_1_ENEMIES = {
    "queue_imp",
    "stamp_goblin",
    "clerkling_apprentice",
    "pigeon_courier",
    "ink_spattered_scribe",
    "seal_bearer_toad",
    "municipal_gargoyle",
    "red_tape_serpent",
    "civic_bell_ringer",
    "filing_beetle",
    "senior_clerk",
    "red_tape_golem",
    "deputy_undersecretary",
}


def test_new_act_1_enemies_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_NEW_ACT_1_ENEMIES <= set(catalog.enemy_database)


def test_new_act_1_enemies_use_named_multi_action_moves() -> None:
    catalog = load_default_content_catalog()

    for enemy_id in EXPECTED_NEW_ACT_1_ENEMIES:
        enemy = catalog.enemy_database[enemy_id]

        assert enemy.intents

        for intent in enemy.intents:
            assert intent.id
            assert intent.name
            assert intent.actions, f"{enemy_id}/{intent.id} should use actions."


def test_act_1_has_varied_easy_normal_elite_and_boss_encounters() -> None:
    catalog = load_default_content_catalog()

    encounters_by_difficulty = {
        "easy": [],
        "normal": [],
        "elite": [],
        "boss": [],
    }

    for encounter in catalog.encounter_database.values():
        if encounter.difficulty in encounters_by_difficulty:
            encounters_by_difficulty[encounter.difficulty].append(encounter)

    assert len(encounters_by_difficulty["easy"]) >= 5
    assert len(encounters_by_difficulty["normal"]) >= 8
    assert len(encounters_by_difficulty["elite"]) >= 2
    assert len(encounters_by_difficulty["boss"]) >= 1


def test_act_1_mimic_uses_dedicated_mimic_encounter_and_elite_still_exists() -> None:
    catalog = load_default_content_catalog()

    assert "city_elite_02" in catalog.encounter_database
    assert "city_mimic_01" in catalog.encounter_database
    assert catalog.act_manifest.treasure.mimic_encounter_id == "city_mimic_01"
    assert catalog.encounter_database["city_mimic_01"].difficulty == "mimic"
