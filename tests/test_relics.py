from random import Random

import pytest

from bab.combat_state import CombatState, Combatant
from bab.data_loader import load_relic_database
from bab.models import RelicDefinition
from bab.relics import (
    apply_combat_start_relics,
    apply_relic_pickup_effects,
    card_reward_count_bonus,
    choose_random_unowned_relic,
)


def make_relic(
    relic_id: str,
    *,
    effect_type: str,
    amount: int = 1,
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


def make_state() -> CombatState:
    return CombatState(
        player=Combatant(
            id="bureaucrat",
            name="Bureaucrat",
            max_hp=70,
            hp=70,
        ),
        enemies=[
            Combatant(
                id="enemy_1",
                name="Enemy 1",
                max_hp=20,
                hp=20,
            ),
            Combatant(
                id="enemy_2",
                name="Enemy 2",
                max_hp=20,
                hp=20,
            ),
        ],
    )


def test_relic_database_loads() -> None:
    relic_database = load_relic_database(
        [
            "data/relics/act_1_relics.json",
        ]
    )

    assert "self_inking_stamp" in relic_database
    assert "certified_tea_mug" in relic_database
    assert "generous_requisition_form" in relic_database


def test_choose_random_unowned_relic_excludes_owned_relics() -> None:
    relic_a = make_relic(
        "relic_a",
        effect_type="gain_block_at_combat_start",
        amount=5,
    )
    relic_b = make_relic(
        "relic_b",
        effect_type="gain_block_at_combat_start",
        amount=5,
    )

    chosen = choose_random_unowned_relic(
        {
            relic_a.id: relic_a,
            relic_b.id: relic_b,
        },
        [relic_a],
        Random(1),
    )

    assert chosen.id == "relic_b"


def test_choose_random_unowned_relic_raises_when_empty() -> None:
    relic = make_relic(
        "relic_a",
        effect_type="gain_block_at_combat_start",
        amount=5,
    )

    with pytest.raises(ValueError, match="No unowned relics"):
        choose_random_unowned_relic(
            {relic.id: relic},
            [relic],
            Random(1),
        )


def test_start_combat_block_relic_grants_block() -> None:
    state = make_state()
    relic = make_relic(
        "helpful_stapler",
        effect_type="gain_block_at_combat_start",
        amount=8,
    )

    apply_combat_start_relics(state, [relic])

    assert state.player.block == 8
    assert "Helpful Stapler grants 8 Block." in state.log


def test_start_combat_status_relic_applies_status_to_all_enemies() -> None:
    state = make_state()
    relic = make_relic(
        "self_inking_stamp",
        effect_type="apply_status_to_all_enemies_at_combat_start",
        amount=2,
        status="paperwork",
    )

    apply_combat_start_relics(state, [relic])

    assert state.enemies[0].get_status_amount("paperwork") == 2
    assert state.enemies[1].get_status_amount("paperwork") == 2


def test_max_energy_relic_increases_energy() -> None:
    state = make_state()
    state.max_energy = 3
    state.energy = 3
    relic = make_relic(
        "procedure_manual",
        effect_type="increase_max_energy",
        amount=1,
    )

    apply_combat_start_relics(state, [relic])

    assert state.max_energy == 4
    assert state.energy == 4


def test_heal_on_pickup_relic_restores_hp_without_exceeding_max() -> None:
    relic = make_relic(
        "tea_mug",
        effect_type="heal_on_pickup",
        amount=12,
    )

    new_hp, messages = apply_relic_pickup_effects(
        current_hp=64,
        max_hp=70,
        relic=relic,
    )

    assert new_hp == 70
    assert messages == ["Tea Mug restores 6 HP."]


def test_reward_count_relic_adds_reward_option() -> None:
    relic = make_relic(
        "generous_requisition_form",
        effect_type="increase_card_reward_count",
        amount=1,
    )

    assert card_reward_count_bonus([relic]) == 1