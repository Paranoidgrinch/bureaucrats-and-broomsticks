from random import Random

from bab.combat_state import CombatState, Combatant
from bab.models import (
    Card,
    CharacterClass,
    EncounterDefinition,
    EnemyDefinition,
    RelicDefinition,
)
from bab.run_state import (
    create_combat_state_for_next_encounter,
    create_new_run,
    enter_map_node,
)


def make_card(card_id: str) -> Card:
    return Card.model_validate(
        {
            "id": card_id,
            "name": card_id.replace("_", " ").title(),
            "class": "bureaucrat",
            "type": "action",
            "cost": 1,
            "rarity": "starter",
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
                "paper_cut",
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
            "id": "easy_test_encounter",
            "name": "Easy Test Encounter",
            "act": 1,
            "difficulty": "easy",
            "enemies": ["test_enemy"],
            "weight": 1,
        }
    )


def make_relic(
    relic_id: str,
    *,
    effect_type: str,
    amount: int,
    status: str | None = None,
) -> RelicDefinition:
    effect: dict[str, object] = {
        "type": effect_type,
        "amount": amount,
    }

    if status is not None:
        effect["status"] = status

    return RelicDefinition.model_validate(
        {
            "id": relic_id,
            "name": relic_id.replace("_", " ").title(),
            "description": "Test relic.",
            "rarity": "common",
            "effects": [effect],
            "tags": [],
        }
    )


def make_run_state():
    card = make_card("paper_cut")
    enemy = make_enemy_definition()
    encounter = make_encounter_definition()

    return create_new_run(
        character_class=make_character_class(),
        card_database={card.id: card},
        enemy_database={enemy.id: enemy},
        encounter_database={encounter.id: encounter},
        status_database={},
        relic_database={},
        rng=Random(1),
        map_steps_before_boss=6,
        map_width=2,
    )


def test_run_state_stores_relic_definitions() -> None:
    run_state = make_run_state()
    relic = make_relic(
        "helpful_stapler",
        effect_type="gain_block_at_combat_start",
        amount=8,
    )

    run_state.relics.append(relic)

    assert run_state.relics[0].id == "helpful_stapler"
    assert run_state.relics[0].name == "Helpful Stapler"


def test_combat_start_relics_apply_when_combat_state_is_created() -> None:
    run_state = make_run_state()
    relic = make_relic(
        "self_inking_stamp",
        effect_type="apply_status_to_all_enemies_at_combat_start",
        amount=2,
        status="paperwork",
    )
    run_state.relics.append(relic)

    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)

    combat_state = create_combat_state_for_next_encounter(run_state)

    assert combat_state.enemies[0].get_status_amount("paperwork") == 2
    assert "Self Inking Stamp applies 2 Paperwork to all enemies." in combat_state.log


def test_energy_relic_applies_when_combat_state_is_created() -> None:
    run_state = make_run_state()
    relic = make_relic(
        "procedure_manual",
        effect_type="increase_max_energy",
        amount=1,
    )
    run_state.relics.append(relic)

    start_node_id = run_state.run_map.start_node_ids[0]
    enter_map_node(run_state, start_node_id)

    combat_state = create_combat_state_for_next_encounter(run_state)

    assert combat_state.max_energy == 4
    assert combat_state.energy == 4