from bab.combat.state import CombatState, Combatant
from bab.models import RelicDefinition, StatusDefinition
from bab.systems.relics import apply_combat_start_relics


def make_state() -> CombatState:
    return CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=50,
            hp=35,
        ),
        enemies=[
            Combatant(
                id="queue_imp",
                name="Queue Imp",
                max_hp=20,
                hp=20,
            )
        ],
        energy=3,
        max_energy=3,
        status_database={
            "strength": StatusDefinition.model_validate(
                {
                    "id": "strength",
                    "name": "Strength",
                    "description": "Increases attack damage.",
                    "stacking": "intensity",
                    "trigger": "none",
                    "is_negative": False,
                }
            ),
            "paperwork": StatusDefinition.model_validate(
                {
                    "id": "paperwork",
                    "name": "Paperwork",
                    "description": "Loses HP at end of turn.",
                    "stacking": "intensity",
                    "trigger": "enemy_turn_end",
                    "is_negative": True,
                }
            ),
            "doubt": StatusDefinition.model_validate(
                {
                    "id": "doubt",
                    "name": "Doubt",
                    "description": "Reduces next attack.",
                    "stacking": "intensity",
                    "trigger": "before_owner_attack",
                    "is_negative": True,
                }
            ),
        },
    )


def make_relic(effect: dict) -> RelicDefinition:
    return RelicDefinition.model_validate(
        {
            "id": "test_relic",
            "name": "Test Relic",
            "description": "Test relic.",
            "rarity": "common",
            "effects": [effect],
            "tags": [],
        }
    )


def test_gain_energy_at_combat_start_relic_effect() -> None:
    state = make_state()
    relic = make_relic(
        {
            "type": "gain_energy_at_combat_start",
            "amount": 2,
        }
    )

    apply_combat_start_relics(state, [relic])

    assert state.energy == 5
    assert state.max_energy == 3
    assert "Test Relic grants 2 Energy." in state.log


def test_gain_strength_at_combat_start_relic_effect() -> None:
    state = make_state()
    relic = make_relic(
        {
            "type": "gain_strength_at_combat_start",
            "amount": 1,
        }
    )

    apply_combat_start_relics(state, [relic])

    assert state.player.get_status_amount("strength") == 1
    assert "Test Relic grants 1 Strength." in state.log


def test_heal_at_combat_start_relic_effect() -> None:
    state = make_state()
    relic = make_relic(
        {
            "type": "heal_at_combat_start",
            "amount": 8,
        }
    )

    apply_combat_start_relics(state, [relic])

    assert state.player.hp == 43
    assert "Test Relic restores 8 HP." in state.log


def test_heal_at_combat_start_does_not_exceed_max_hp() -> None:
    state = make_state()
    relic = make_relic(
        {
            "type": "heal_at_combat_start",
            "amount": 99,
        }
    )

    apply_combat_start_relics(state, [relic])

    assert state.player.hp == 50
    assert "Test Relic restores 15 HP." in state.log


def test_apply_status_to_player_at_combat_start_relic_effect() -> None:
    state = make_state()
    relic = make_relic(
        {
            "type": "apply_status_to_player_at_combat_start",
            "status": "paperwork",
            "amount": 2,
        }
    )

    apply_combat_start_relics(state, [relic])

    assert state.player.get_status_amount("paperwork") == 2
    assert "Test Relic applies 2 Paperwork to the player." in state.log
