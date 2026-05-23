from random import Random

import pytest

from bab.systems.encounters import choose_random_encounter
from bab.models import EncounterDefinition


def make_encounter(
    encounter_id: str,
    *,
    act: int = 1,
    difficulty: str = "normal",
    weight: int = 1,
) -> EncounterDefinition:
    return EncounterDefinition.model_validate(
        {
            "id": encounter_id,
            "name": encounter_id.replace("_", " ").title(),
            "act": act,
            "difficulty": difficulty,
            "enemies": ["test_enemy"],
            "weight": weight,
        }
    )


def test_choose_random_encounter_returns_the_only_available_encounter() -> None:
    encounter = make_encounter("city_test_01")
    encounter_database = {
        encounter.id: encounter,
    }

    chosen = choose_random_encounter(encounter_database, Random(1))

    assert chosen.id == "city_test_01"


def test_choose_random_encounter_can_filter_by_act() -> None:
    act_1_encounter = make_encounter("act_1_encounter", act=1)
    act_2_encounter = make_encounter("act_2_encounter", act=2)

    encounter_database = {
        act_1_encounter.id: act_1_encounter,
        act_2_encounter.id: act_2_encounter,
    }

    chosen = choose_random_encounter(
        encounter_database,
        Random(1),
        act=2,
    )

    assert chosen.id == "act_2_encounter"


def test_choose_random_encounter_can_filter_by_difficulty() -> None:
    easy_encounter = make_encounter("easy_encounter", difficulty="easy")
    normal_encounter = make_encounter("normal_encounter", difficulty="normal")

    encounter_database = {
        easy_encounter.id: easy_encounter,
        normal_encounter.id: normal_encounter,
    }

    chosen = choose_random_encounter(
        encounter_database,
        Random(1),
        difficulty="easy",
    )

    assert chosen.id == "easy_encounter"


def test_choose_random_encounter_can_filter_by_act_and_difficulty() -> None:
    wrong_act = make_encounter("wrong_act", act=2, difficulty="normal")
    wrong_difficulty = make_encounter("wrong_difficulty", act=1, difficulty="easy")
    correct_encounter = make_encounter("correct_encounter", act=1, difficulty="normal")

    encounter_database = {
        wrong_act.id: wrong_act,
        wrong_difficulty.id: wrong_difficulty,
        correct_encounter.id: correct_encounter,
    }

    chosen = choose_random_encounter(
        encounter_database,
        Random(1),
        act=1,
        difficulty="normal",
    )

    assert chosen.id == "correct_encounter"


def test_choose_random_encounter_raises_error_for_empty_database() -> None:
    with pytest.raises(ValueError, match="No encounters available"):
        choose_random_encounter({}, Random(1))


def test_choose_random_encounter_raises_error_when_filters_match_nothing() -> None:
    encounter = make_encounter("city_test_01", act=1, difficulty="easy")

    with pytest.raises(ValueError, match="No encounters available"):
        choose_random_encounter(
            {encounter.id: encounter},
            Random(1),
            act=2,
            difficulty="boss",
        )