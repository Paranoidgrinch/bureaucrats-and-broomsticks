from bab.models import Card, Effect
from bab.sim.heuristic_v2 import HeuristicV2Policy


def make_card(card_id: str, effects: list[Effect]) -> Card:
    return Card(
        id=card_id,
        name=card_id.replace("_", " ").title(),
        class_="bureaucrat",
        type="action",
        cost=1,
        rarity="common",
        text="test",
        effects=effects,
        tags=[],
    )


def test_heuristic_v2_recognizes_gain_resource_energy() -> None:
    policy = HeuristicV2Policy(seed=1)
    card = make_card(
        "test_energy",
        [Effect(type="gain_resource", target="self", resource="energy", amount=2)],
    )

    estimate = policy._estimate_card(card.id, card)

    assert estimate.energy == 2


def test_heuristic_v2_recognizes_gain_strength_as_scaling() -> None:
    policy = HeuristicV2Policy(seed=1)
    card = make_card(
        "test_strength",
        [Effect(type="gain_strength", target="self", amount=3)],
    )

    estimate = policy._estimate_card(card.id, card)

    assert estimate.self_strength == 3
    assert estimate.scaling == 3


def test_heuristic_v2_recognizes_damage_per_status_amount_per_stack() -> None:
    policy = HeuristicV2Policy(seed=1)
    card = make_card(
        "test_paperwork_scaler",
        [
            Effect(
                type="damage_per_status",
                target="enemy",
                status="paperwork",
                amount_per_stack=4,
            )
        ],
    )

    estimate = policy._estimate_card(card.id, card)

    assert estimate.damage == 4
    assert estimate.scaling == 4
    assert estimate.paperwork == 1


def test_heuristic_v2_recognizes_create_card_utility() -> None:
    policy = HeuristicV2Policy(seed=1)
    card = make_card(
        "test_create_card",
        [
            Effect(
                type="create_card",
                target="self",
                card_id="bureaucrat_basic_strike",
                destination="hand",
                copies=2,
            )
        ],
    )

    estimate = policy._estimate_card(card.id, card)

    assert estimate.utility >= 4


def test_heuristic_v2_recognizes_all_enemy_damage() -> None:
    policy = HeuristicV2Policy(seed=1)
    card = make_card(
        "test_aoe",
        [Effect(type="deal_damage", target="all_enemies", amount=7)],
    )

    estimate = policy._estimate_card(card.id, card)

    assert estimate.aoe_damage == 7
