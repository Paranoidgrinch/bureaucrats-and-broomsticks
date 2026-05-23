from random import Random

from bab.combat.state import CombatState, Combatant
from bab.combat.deck import draw_cards, play_card_from_hand
from bab.combat.effects import resolve_card
from bab.models import Card, Effect, EnemyIntent, StatusDefinition
from bab.combat.turns import apply_enemy_turn_end_statuses, run_enemy_turn, start_player_turn


def make_card(
    card_id: str,
    name: str,
    cost: int,
    effects: list[Effect],
) -> Card:
    return Card.model_validate(
        {
            "id": card_id,
            "name": name,
            "class": "bureaucrat",
            "type": "form",
            "cost": cost,
            "rarity": "starter",
            "text": "Test card.",
            "effects": [effect.model_dump(exclude_none=True) for effect in effects],
            "tags": [],
        }
    )


def make_state(
    *,
    player_hp: int = 50,
    enemy_hp: int = 30,
    enemy_intents: list[EnemyIntent] | None = None,
) -> CombatState:
    return CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=player_hp,
            hp=player_hp,
        ),
        enemies=[
            Combatant(
                id="test_enemy",
                name="Test Enemy",
                max_hp=enemy_hp,
                hp=enemy_hp,
                intents=enemy_intents or [],
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
            "panic": StatusDefinition.model_validate(
                {
                    "id": "panic",
                    "name": "Panic",
                    "description": "Test Panic.",
                    "stacking": "intensity",
                    "trigger": "player_turn_start",
                    "is_negative": True,
                }
            ),
        },
    )


def test_damage_respects_block_and_reduces_block() -> None:
    state = make_state(enemy_hp=30)
    enemy = state.enemies[0]
    enemy.block = 4

    card = make_card(
        "test_strike",
        "Test Strike",
        1,
        [Effect(type="deal_damage", target="enemy", amount=6)],
    )

    resolve_card(card, state, target=enemy)

    assert enemy.hp == 28
    assert enemy.block == 0
    assert "Test Enemy takes 2 damage." in state.log


def test_paperwork_loses_hp_at_enemy_turn_end_and_ignores_block() -> None:
    state = make_state(enemy_hp=30)
    enemy = state.enemies[0]
    enemy.block = 99
    enemy.apply_status("paperwork", 5)

    apply_enemy_turn_end_statuses(state)

    assert enemy.hp == 25
    assert enemy.block == 99
    assert enemy.get_status_amount("paperwork") == 5


def test_retroactive_fee_scales_with_paperwork_stacks() -> None:
    state = make_state(enemy_hp=30)
    enemy = state.enemies[0]
    enemy.apply_status("paperwork", 4)

    retroactive_fee = make_card(
        "retroactive_fee",
        "Retroactive Fee",
        2,
        [
            Effect(
                type="damage_per_status",
                target="enemy",
                status="paperwork",
                amount_per_stack=3,
            )
        ],
    )

    resolve_card(retroactive_fee, state, target=enemy)

    assert enemy.hp == 18
    assert "Test Enemy takes 12 damage from Paperwork scaling." in state.log


def test_doubt_reduces_next_enemy_attack_and_consumes_one_stack() -> None:
    attack = EnemyIntent.model_validate(
        {
            "id": "test_attack",
            "name": "Test Attack",
            "intent_type": "attack",
            "damage": 8,
        }
    )
    state = make_state(player_hp=50, enemy_intents=[attack])
    enemy = state.enemies[0]
    enemy.apply_status("doubt", 2)

    run_enemy_turn(state)

    assert state.player.hp == 44
    assert enemy.get_status_amount("doubt") == 1
    assert enemy.intent_index == 0
    assert state.turn == 2


def test_panic_reduces_next_player_draw_and_consumes_one_stack() -> None:
    state = make_state()
    state.player.apply_status("panic", 2)
    state.draw_pile = [
        make_card(f"card_{index}", f"Card {index}", 0, [])
        for index in range(6)
    ]

    start_player_turn(state, Random(1))

    assert len(state.hand) == 3
    assert state.player.get_status_amount("panic") == 1
    assert state.energy == state.max_energy


def test_draw_cards_reshuffles_discard_when_draw_pile_is_empty() -> None:
    state = make_state()
    state.draw_pile = []
    state.discard_pile = [
        make_card("archived_form", "Archived Form", 0, []),
        make_card("misplaced_stamp", "Misplaced Stamp", 0, []),
    ]

    draw_cards(state, amount=2, rng=Random(1))

    assert len(state.hand) == 2
    assert len(state.draw_pile) == 0
    assert len(state.discard_pile) == 0
    assert "Discard pile is shuffled into draw pile." in state.log


def test_play_card_spends_energy_moves_card_to_discard_and_applies_effect() -> None:
    state = make_state(enemy_hp=20)
    enemy = state.enemies[0]
    card = make_card(
        "rubber_stamp",
        "Rubber Stamp",
        1,
        [
            Effect(type="deal_damage", target="enemy", amount=6),
            Effect(type="apply_status", target="enemy", status="paperwork", amount=1),
        ],
    )
    state.hand = [card]
    state.energy = 3

    play_card_from_hand(state, hand_index=0, target=enemy)

    assert state.energy == 2
    assert state.hand == []
    assert state.discard_pile == [card]
    assert enemy.hp == 14
    assert enemy.get_status_amount("paperwork") == 1


def test_not_enough_energy_keeps_card_in_hand_and_does_not_apply_effect() -> None:
    state = make_state(enemy_hp=20)
    enemy = state.enemies[0]
    card = make_card(
        "expensive_stamp",
        "Expensive Stamp",
        2,
        [Effect(type="deal_damage", target="enemy", amount=6)],
    )
    state.hand = [card]
    state.energy = 1

    play_card_from_hand(state, hand_index=0, target=enemy)

    assert state.energy == 1
    assert state.hand == [card]
    assert state.discard_pile == []
    assert enemy.hp == 20
    assert state.log[-1] == "Not enough Energy to play Expensive Stamp. Needed 2, had 1."