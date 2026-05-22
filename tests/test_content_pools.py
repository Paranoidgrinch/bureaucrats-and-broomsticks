from bab.data_loader import (
    load_encounter_database,
    load_enemy_database,
    load_event_database,
)


def test_act_1_city_enemy_pool_loads() -> None:
    enemy_database = load_enemy_database(
        [
            "data/enemies/city_enemies.json",
        ]
    )

    assert len(enemy_database) >= 9
    assert "chairman_of_the_subcommittee" in enemy_database
    assert "middle_management_ogre" in enemy_database
    assert "departmental_mimic" in enemy_database


def test_act_1_city_encounters_reference_known_enemies() -> None:
    enemy_database = load_enemy_database(
        [
            "data/enemies/city_enemies.json",
        ]
    )
    encounter_database = load_encounter_database(
        [
            "data/encounters/act_1_city.json",
        ]
    )

    for encounter in encounter_database.values():
        for enemy_id in encounter.enemies:
            assert enemy_id in enemy_database


def test_act_1_city_encounter_pool_contains_progression_difficulties() -> None:
    encounter_database = load_encounter_database(
        [
            "data/encounters/act_1_city.json",
        ]
    )

    difficulties = {
        encounter.difficulty
        for encounter in encounter_database.values()
    }

    assert {"easy", "normal", "elite", "boss"} <= difficulties


def test_act_1_city_boss_encounter_uses_boss_enemy() -> None:
    enemy_database = load_enemy_database(
        [
            "data/enemies/city_enemies.json",
        ]
    )
    encounter_database = load_encounter_database(
        [
            "data/encounters/act_1_city.json",
        ]
    )

    boss_encounters = [
        encounter
        for encounter in encounter_database.values()
        if encounter.difficulty == "boss"
    ]

    assert boss_encounters

    for encounter in boss_encounters:
        assert len(encounter.enemies) == 1
        boss_enemy = enemy_database[encounter.enemies[0]]
        assert "boss" in boss_enemy.tags


def test_act_1_city_event_pool_loads() -> None:
    event_database = load_event_database(
        [
            "data/events/act_1_city_events.json",
        ]
    )

    assert len(event_database) >= 4
    assert "misfiled_prophecy" in event_database
    assert "haunted_suggestion_box" in event_database


def test_act_1_city_events_have_player_choices() -> None:
    event_database = load_event_database(
        [
            "data/events/act_1_city_events.json",
        ]
    )

    for event in event_database.values():
        assert event.choices
        assert all(choice.text for choice in event.choices)
        assert all(choice.result_text for choice in event.choices)