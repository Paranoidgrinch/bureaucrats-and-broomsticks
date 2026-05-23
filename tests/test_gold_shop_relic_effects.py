from random import Random

from bab.console.run_flow import create_run_state
from bab.models import RelicDefinition
from bab.run.state import create_combat_state_for_next_encounter, enter_map_node, finish_victorious_combat
from bab.systems.relics import (
    apply_relic_pickup_effects_to_run_state,
    gold_reward_bonus,
    shop_price_discount_percent,
)
from bab.systems.shop import discounted_shop_price


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


def test_gain_gold_on_pickup_effect_adds_gold_to_run_state() -> None:
    run_state = create_run_state()
    relic = make_relic({"type": "gain_gold_on_pickup", "amount": 40})

    messages = apply_relic_pickup_effects_to_run_state(run_state, relic)

    assert run_state.gold == 40
    assert "Test Relic grants 40 Gold." in messages


def test_increase_gold_rewards_effect_adds_bonus_after_combat() -> None:
    run_state = create_run_state(rng=Random(1))
    relic = make_relic({"type": "increase_gold_rewards", "amount": 10})
    run_state.relics.append(relic)

    first_node = run_state.available_map_nodes()[0]
    enter_map_node(run_state, first_node.id)
    combat_state = create_combat_state_for_next_encounter(run_state)

    for enemy in combat_state.enemies:
        enemy.hp = 0

    reward = finish_victorious_combat(run_state, combat_state)

    assert reward >= 10
    assert run_state.gold == reward
    assert gold_reward_bonus(run_state.relics) == 10


def test_shop_price_discount_effect_reduces_prices() -> None:
    relic = make_relic({"type": "shop_price_discount", "amount": 10})

    assert shop_price_discount_percent([relic]) == 10
    assert discounted_shop_price(100, 10) == 90


def test_shop_price_discount_is_capped() -> None:
    relics = [
        make_relic({"type": "shop_price_discount", "amount": 50}),
        make_relic({"type": "shop_price_discount", "amount": 50}),
    ]

    assert shop_price_discount_percent(relics) == 75
    assert discounted_shop_price(100, 75) == 25
