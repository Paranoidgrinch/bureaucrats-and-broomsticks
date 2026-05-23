from bab.combat.state import CombatState, Combatant
from bab.content.data_loader import (
    load_card_database,
    load_character_class,
    load_enemy_database,
    load_status_database,
)
from bab.combat.effects import resolve_effect
from bab.models import Effect
from bab.combat.turns import run_basic_attack


def test_bureaucrat_starter_deck_is_rebalanced() -> None:
    character_class = load_character_class("data/classes/bureaucrat.json")

    assert character_class.starting_deck.count("paper_cut") == 4
    assert character_class.starting_deck.count("cower_behind_a_desk") == 4
    assert character_class.starting_deck.count("strong_binder") == 1
    assert character_class.starting_deck.count("permit_a38") == 1
    assert "retroactive_fee" not in character_class.starting_deck
    assert "official_delay" not in character_class.starting_deck
    assert len(character_class.starting_deck) == 10


def test_rebalanced_starter_cards_load() -> None:
    card_database = load_card_database(
        [
            "data/cards/bureaucrat_starter.json",
            "data/cards/bureaucrat_rewards.json",
        ]
    )

    assert card_database["paper_cut"].effects[0].amount == 6
    assert card_database["cower_behind_a_desk"].effects[0].amount == 5
    assert card_database["strong_binder"].effects[0].amount == 7
    assert card_database["strong_binder"].effects[1].status == "doubt"
    assert card_database["permit_a38"].effects[0].status == "paperwork"
    assert card_database["permit_a38"].effects[0].amount == 5


def test_strength_status_loads() -> None:
    status_database = load_status_database(
        [
            "data/statuses/statuses.json",
        ]
    )

    assert "strength" in status_database
    assert status_database["strength"].is_negative is False


def test_gain_strength_effect_uses_owner_target() -> None:
    state = CombatState(
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
                max_hp=30,
                hp=30,
            )
        ],
    )
    enemy = state.enemies[0]
    effect = Effect(
        type="gain_strength",
        target="owner",
        amount=3,
    )

    resolve_effect(effect, state, target=enemy)

    assert enemy.get_status_amount("strength") == 3
    assert state.player.get_status_amount("strength") == 0


def test_enemy_strength_increases_attack_damage() -> None:
    state = CombatState(
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
                max_hp=30,
                hp=30,
            )
        ],
    )
    enemy = state.enemies[0]
    enemy.apply_status("strength", 4)

    run_basic_attack(state, enemy, base_damage=6)

    assert state.player.hp == 60
    assert "Test Enemy attacks for 10. Player takes 10 damage." in state.log


def test_enemy_pool_contains_strength_buffs() -> None:
    enemy_database = load_enemy_database(
        [
            "data/enemies/city_enemies.json",
        ]
    )

    strength_buff_count = 0

    for enemy in enemy_database.values():
        for intent in enemy.intents:
            for effect in intent.effects:
                if effect.type == "gain_strength":
                    strength_buff_count += 1

    assert strength_buff_count >= 5