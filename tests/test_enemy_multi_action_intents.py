from bab.combat.state import CombatState, Combatant
from bab.combat.turns import run_enemy_turn
from bab.console.views import format_enemy_intent
from bab.models import EnemyIntent, StatusDefinition


def make_state(enemy_intents: list[EnemyIntent]) -> CombatState:
    return CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=50,
            hp=50,
        ),
        enemies=[
            Combatant(
                id="stamp_goblin",
                name="Stamp Goblin",
                max_hp=30,
                hp=30,
                intents=enemy_intents,
            )
        ],
        status_database={
            "paperwork": StatusDefinition.model_validate(
                {
                    "id": "paperwork",
                    "name": "Paperwork",
                    "description": "Test Paperwork.",
                    "stacking": "intensity",
                    "trigger": "enemy_turn_end",
                    "is_negative": True,
                }
            ),
            "doubt": StatusDefinition.model_validate(
                {
                    "id": "doubt",
                    "name": "Doubt",
                    "description": "Test Doubt.",
                    "stacking": "intensity",
                    "trigger": "before_owner_attack",
                    "is_negative": True,
                }
            ),
            "strength": StatusDefinition.model_validate(
                {
                    "id": "strength",
                    "name": "Strength",
                    "description": "Test Strength.",
                    "stacking": "intensity",
                    "trigger": "none",
                    "is_negative": False,
                }
            ),
        },
    )


def test_enemy_intent_can_execute_multiple_ordered_actions() -> None:
    intent = EnemyIntent.model_validate(
        {
            "id": "stamped_in_triplicate",
            "name": "Stamped in Triplicate",
            "intent_type": "mixed",
            "actions": [
                {
                    "type": "gain_block",
                    "target": "owner",
                    "amount": 5,
                },
                {
                    "type": "deal_damage",
                    "target": "player",
                    "amount": 6,
                },
                {
                    "type": "apply_status",
                    "target": "player",
                    "status": "paperwork",
                    "amount": 1,
                },
            ],
        }
    )
    state = make_state([intent])
    enemy = state.enemies[0]

    run_enemy_turn(state)

    assert enemy.block == 5
    assert state.player.hp == 44
    assert state.player.get_status_amount("paperwork") == 1
    assert state.log.index("Stamp Goblin gains 5 Block.") < state.log.index(
        "Stamp Goblin attacks for 6. Player takes 6 damage."
    )


def test_multi_action_enemy_attack_uses_strength_and_doubt() -> None:
    intent = EnemyIntent.model_validate(
        {
            "id": "press_the_case",
            "name": "Press the Case",
            "intent_type": "mixed",
            "actions": [
                {
                    "type": "deal_damage",
                    "target": "player",
                    "amount": 8,
                }
            ],
        }
    )
    state = make_state([intent])
    enemy = state.enemies[0]
    enemy.apply_status("strength", 2)
    enemy.apply_status("doubt", 1)

    run_enemy_turn(state)

    assert state.player.hp == 42
    assert enemy.get_status_amount("doubt") == 0
    assert "Stamp Goblin attacks for 8. Player takes 8 damage." in state.log


def test_format_enemy_intent_shows_move_name_and_action_summary() -> None:
    intent = EnemyIntent.model_validate(
        {
            "id": "stamped_in_triplicate",
            "name": "Stamped in Triplicate",
            "intent_type": "mixed",
            "actions": [
                {
                    "type": "gain_block",
                    "target": "owner",
                    "amount": 5,
                },
                {
                    "type": "deal_damage",
                    "target": "player",
                    "amount": 6,
                },
                {
                    "type": "apply_status",
                    "target": "player",
                    "status": "paperwork",
                    "amount": 1,
                },
            ],
        }
    )
    combatant = Combatant(
        id="stamp_goblin",
        name="Stamp Goblin",
        max_hp=30,
        hp=30,
        intents=[intent],
    )

    assert format_enemy_intent(combatant) == (
        'intends to use "Stamped in Triplicate": '
        "gain 5 Block, attack for 6 damage, apply 1 Paperwork"
    )


def test_legacy_enemy_intent_fields_still_work() -> None:
    legacy_attack = EnemyIntent.model_validate(
        {
            "id": "test_attack",
            "name": "Test Attack",
            "intent_type": "attack",
            "damage": 7,
        }
    )
    state = make_state([legacy_attack])

    run_enemy_turn(state)

    assert state.player.hp == 43
    assert "Stamp Goblin uses Test Attack." in state.log
