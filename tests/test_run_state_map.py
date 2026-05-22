from random import Random

import pytest

from bab.combat_state import CombatState, Combatant
from bab.models import Card, CharacterClass, EncounterDefinition, EnemyDefinition
from bab.run_state import (
    complete_current_map_node,
    create_combat_state_for_next_encounter,
    create_new_run,
    enter_map_node,
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


def make_encounter_definition(
    encounter_id: str,
    *,
    difficulty: str,
) -> EncounterDefinition:
    return EncounterDefinition.model_validate(
        {
            "id": encounter_id,
            "name": encounter_id.replace("_", " ").title(),
            "act": 1,
            "difficulty": difficulty,
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

    encounters = [
        make_encounter_definition("easy_test_encounter", difficulty="easy"),
        make_encounter_definition("normal_test_encounter", difficulty="normal"),
        make_encounter_definition("elite_test_encounter", difficulty="elite"),
        make_encounter_definition("boss_test_encounter", difficulty="boss"),
    ]

    return create_new_run(
        character_class=make_character_class(),
        card_database=card_database,
        enemy_database={enemy.id: enemy},
        encounter_database={
            encounter.id: encounter
            for encounter in encounters
        },
        status_database={},
        rng=Random(1),
        max_fights=3,
        map_steps_before_boss=6,
        map_width=2,
    )


def test_new_run_has_map_but_no_current_node() -> None:
    run_state = make_run_state()

    assert run_state.run_map.act == 1
    assert run_state.current_node_id is None
    assert run_state.current_node() is None
    assert run_state.completed_node_ids == []


def test_available_map_nodes_returns_start_nodes_before_first_choice() -> None:
    run_state = make_run_state()

    available_nodes = run_state.available_map_nodes()

    assert [node.id for node in available_nodes] == list(run_state.run_map.start_node_ids)


def test_enter_map_node_can_choose_start_node() -> None:
    run_state = make_run_state()
    start_node_id = run_state.run_map.start_node_ids[0]

    enter_map_node(run_state, start_node_id)

    assert run_state.current_node_id == start_node_id
    assert run_state.current_node() == run_state.run_map.get_node(start_node_id)


def test_enter_map_node_rejects_non_start_node_before_run_begins() -> None:
    run_state = make_run_state()
    non_start_node_id = next(
        node.id
        for node in run_state.run_map.nodes.values()
        if node.id not in run_state.run_map.start_node_ids
    )

    with pytest.raises(ValueError, match="start nodes"):
        enter_map_node(run_state, non_start_node_id)


def test_cannot_advance_before_current_node_is_completed() -> None:
    run_state = make_run_state()
    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)

    next_node_id = run_state.current_node().next_node_ids[0]

    with pytest.raises(ValueError, match="must be completed"):
        enter_map_node(run_state, next_node_id)


def test_complete_current_node_and_advance_to_connected_node() -> None:
    run_state = make_run_state()
    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)

    complete_current_map_node(run_state)

    next_node_id = run_state.run_map.get_node(start_node_id).next_node_ids[0]
    enter_map_node(run_state, next_node_id)

    assert run_state.current_node_id == next_node_id
    assert run_state.completed_node_ids == [start_node_id]


def test_enter_map_node_rejects_unconnected_node() -> None:
    run_state = make_run_state()
    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)
    complete_current_map_node(run_state)

    current_node = run_state.run_map.get_node(start_node_id)
    unconnected_node_id = next(
        node.id
        for node in run_state.run_map.nodes.values()
        if node.id != start_node_id
        and node.id not in current_node.next_node_ids
    )

    with pytest.raises(ValueError, match="not connected"):
        enter_map_node(run_state, unconnected_node_id)


def test_finish_victorious_combat_completes_current_map_node() -> None:
    run_state = make_run_state()
    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)

    combat_state = CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=70,
            hp=55,
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

    assert run_state.current_hp == 55
    assert run_state.fight_number == 2
    assert run_state.completed_node_ids == [start_node_id]


def test_create_combat_state_uses_current_map_node_difficulty() -> None:
    run_state = make_run_state()
    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)

    combat_state = create_combat_state_for_next_encounter(run_state)

    assert "Encounter chosen: Easy Test Encounter." in combat_state.log


def test_create_combat_state_rejects_non_combat_current_node() -> None:
    run_state = make_run_state()
    event_node_id = next(
        node.id
        for node in run_state.run_map.nodes.values()
        if node.node_type == "event"
    )
    run_state.current_node_id = event_node_id

    with pytest.raises(ValueError, match="does not contain a combat encounter"):
        create_combat_state_for_next_encounter(run_state)