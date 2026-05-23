from bab.content.catalog import load_default_content_catalog


EXPECTED_BOSS_ENCOUNTERS = {
    "city_boss_01",
    "city_boss_02",
    "city_boss_03",
    "city_boss_04",
    "city_boss_05",
}

EXPECTED_NEW_BOSSES = {
    "queue_commissioner",
    "lord_sealkeeper",
    "municipal_dragon",
    "living_charter",
}


def test_act_1_has_five_boss_encounters() -> None:
    catalog = load_default_content_catalog()

    boss_encounter_ids = {
        encounter.id
        for encounter in catalog.encounter_database.values()
        if encounter.difficulty == "boss"
    }

    assert EXPECTED_BOSS_ENCOUNTERS <= boss_encounter_ids
    assert len(boss_encounter_ids) >= 5


def test_new_bosses_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_NEW_BOSSES <= set(catalog.enemy_database)


def test_new_bosses_use_named_multi_action_moves() -> None:
    catalog = load_default_content_catalog()

    for enemy_id in EXPECTED_NEW_BOSSES:
        enemy = catalog.enemy_database[enemy_id]

        assert enemy.intents

        for intent in enemy.intents:
            assert intent.id
            assert intent.name
            assert intent.actions, f"{enemy_id}/{intent.id} should use actions."


def test_all_act_1_boss_encounters_reference_existing_boss_enemies() -> None:
    catalog = load_default_content_catalog()
    enemy_ids = set(catalog.enemy_database)

    for encounter_id in EXPECTED_BOSS_ENCOUNTERS:
        encounter = catalog.encounter_database[encounter_id]

        assert encounter.difficulty == "boss"
        assert set(encounter.enemies) <= enemy_ids

        for enemy_id in encounter.enemies:
            assert "boss" in catalog.enemy_database[enemy_id].tags
