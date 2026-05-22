from random import Random

import pytest

from bab.combat_state import CombatState, Combatant
from bab.models import Card, CharacterClass, EncounterDefinition, EnemyDefinition
from bab.run_state import (
    create_combat_state_for_next_encounter,
    create_new_run,
    finish_victorious_combat,
)


def make_card(
    card_id: str,
    *,
    rarity: str = "starter",
) -> Card:
    return Card.model_validate(
        {
            "id": card_id,
            "name": card_id.replace("_", " ").title(),
            "class": "bureaucrat",
            "type": "form",
            "cost": 1,
            "rarity": rarity,
            "text": "Test card.",
            "effects": [],
            "tags": [],
        }
    )


def make_character_class() -> CharacterClass:
    return CharacterClass.model_validate(
        {
            "id": "bureaucrat",
            "name": "Bureaucrat",
            "max_hp": 70,
            "starting_energy": 3,
            "starting_relic": None,
            "starting_deck": [
                "rubber_stamp",
                "official_delay",
            ],
            "starting_resources": {},
        }
    )


def make_enemy_definition() -> EnemyDefinition:
    return EnemyDefinition.model_validate(
        {
            "id": "test_enemy",
            "name": "Test Enemy",
            "max_hp": 20,
            "intent_pattern": "cycle",
            "intents": [],
            "tags": [],
        }
    )


def make_encounter_definition() -> EncounterDefinition:
    return EncounterDefinition.model_validate(
        {
            "id": "test_encounter",
            "name": "Test Encounter",
            "act": 1,
            "difficulty": "normal",
            "enemies": ["test_enemy"],
            "weight": 1,
        }
    )


def make_run_state():
    rubber_stamp = make_card("rubber_stamp")
    official_delay = make_card("official_delay")
    card_database = {
        rubber_stamp.id: rubber_stamp,
        official_delay.id: official_delay,
    }

    enemy = make_enemy_definition()
    encounter = make_encounter_definition()

    return create_new_run(
        character_class=make_character_class(),
        card_database=card_database,
        enemy_database={enemy.id: enemy},
        encounter_database={encounter.id: encounter},
        status_database={},
        rng=Random(1),
        max_fights=3,
    )


def test_create_new_run_builds_starting_deck() -> None:
    run_state = make_run_state()

    assert run_state.current_hp == 70
    assert run_state.fight_number == 1
    assert run_state.max_fights == 3
    assert [card.id for card in run_state.run_deck] == [
        "rubber_stamp",
        "official_delay",
    ]


def test_create_combat_state_uses_current_hp_and_run_deck() -> None:
    run_state = make_run_state()
    reward = make_card("compliance_review", rarity="common")
    run_state.run_deck.append(reward)
    run_state.current_hp = 42

    combat_state = create_combat_state_for_next_encounter(run_state)

    assert combat_state.player.hp == 42
    assert combat_state.player.max_hp == 70
    assert sorted(card.id for card in combat_state.draw_pile) == [
        "compliance_review",
        "official_delay",
        "rubber_stamp",
    ]
    assert [enemy.id for enemy in combat_state.enemies] == ["test_enemy"]
    assert "Encounter chosen: Test Encounter." in combat_state.log


def test_finish_victorious_combat_persists_hp_and_advances_fight_number() -> None:
    run_state = make_run_state()
    combat_state = CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=70,
            hp=33,
        ),
        enemies=[
            Combatant(
                id="test_enemy",
                name="Test Enemy",
                max_hp=20,
                hp=0,
            )
        ],
    )

    finish_victorious_combat(run_state, combat_state)

    assert run_state.current_hp == 33
    assert run_state.fight_number == 2


def test_finish_victorious_combat_rejects_unfinished_combat() -> None:
    run_state = make_run_state()
    combat_state = CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=70,
            hp=70,
        ),
        enemies=[
            Combatant(
                id="test_enemy",
                name="Test Enemy",
                max_hp=20,
                hp=20,
            )
        ],
    )

    with pytest.raises(ValueError, match="enemies are still alive"):
        finish_victorious_combat(run_state, combat_state)


def test_cannot_start_combat_after_run_is_complete() -> None:
    run_state = make_run_state()
    run_state.fight_number = 4
    run_state.max_fights = 3

    with pytest.raises(ValueError, match="run is already complete"):
        create_combat_state_for_next_encounter(run_state)


def test_cannot_start_combat_when_player_has_no_hp() -> None:
    run_state = make_run_state()
    run_state.current_hp = 0

    with pytest.raises(ValueError, match="player has no HP"):
        create_combat_state_for_next_encounter(run_state)