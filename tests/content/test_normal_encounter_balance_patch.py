from bab.content.catalog import load_default_content_catalog
from bab.run.map import combat_difficulty_for_depth


def test_depth_three_still_uses_easy_encounters() -> None:
    assert combat_difficulty_for_depth(1, 9) == "easy"
    assert combat_difficulty_for_depth(2, 9) == "easy"
    assert combat_difficulty_for_depth(3, 9) == "easy"
    assert combat_difficulty_for_depth(4, 9) == "normal"


def test_high_pressure_normal_enemies_were_softened() -> None:
    catalog = load_default_content_catalog()

    assert catalog.enemy_database["civic_bell_ringer"].max_hp <= 34
    assert catalog.enemy_database["seal_bearer_toad"].max_hp <= 28
    assert catalog.enemy_database["ink_spattered_scribe"].max_hp <= 30
    assert catalog.enemy_database["filing_beetle"].max_hp <= 32
    assert catalog.enemy_database["pigeon_courier"].max_hp <= 22
    assert catalog.enemy_database["cobblestone_bailiff"].max_hp <= 38


def test_normal_spike_encounters_have_lower_weights() -> None:
    catalog = load_default_content_catalog()

    for encounter_id in {
        "city_normal_02",
        "city_normal_03",
        "city_normal_06",
        "city_normal_08",
        "city_normal_09",
        "city_normal_12",
        "city_normal_15",
        "city_normal_16",
    }:
        encounter = catalog.encounter_database[encounter_id]

        assert encounter.difficulty == "normal"
        assert encounter.weight <= 1
