from bab.content.catalog import load_default_content_catalog


EXPECTED_SECOND_BATCH_ENEMIES = {
    "form_rat_swarm",
    "permit_beggar",
    "tollhouse_sprite",
    "street_ordinance_wisp",
    "registry_moth",
    "overdue_page",
    "appointment_leech",
    "minor_tax_familiar",
    "cobblestone_bailiff",
    "lantern_inspector",
}


def test_second_batch_act_1_enemies_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_SECOND_BATCH_ENEMIES <= set(catalog.enemy_database)


def test_second_batch_act_1_enemies_use_named_multi_action_moves() -> None:
    catalog = load_default_content_catalog()

    for enemy_id in EXPECTED_SECOND_BATCH_ENEMIES:
        enemy = catalog.enemy_database[enemy_id]

        assert enemy.intents

        for intent in enemy.intents:
            assert intent.id
            assert intent.name
            assert intent.actions, f"{enemy_id}/{intent.id} should use actions."


def test_act_1_now_has_large_normal_encounter_variety() -> None:
    catalog = load_default_content_catalog()

    easy_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.difficulty == "easy"
    ]
    normal_encounters = [
        encounter
        for encounter in catalog.encounter_database.values()
        if encounter.difficulty == "normal"
    ]

    assert len(easy_encounters) >= 8
    assert len(normal_encounters) >= 14


def test_act_1_normal_encounters_use_broad_enemy_pool() -> None:
    catalog = load_default_content_catalog()

    normal_enemy_ids = {
        enemy_id
        for encounter in catalog.encounter_database.values()
        if encounter.difficulty == "normal"
        for enemy_id in encounter.enemies
    }

    assert len(normal_enemy_ids) >= 15
