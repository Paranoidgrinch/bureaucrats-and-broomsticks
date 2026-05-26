from dataclasses import replace

from bab.models import Card, Effect
from bab.sim.heuristic_v2 import HeuristicV2Policy
from bab.sim.rl_env import Action, Observation


def add_test_cards(policy: HeuristicV2Policy) -> None:
    policy.card_database["test_paperwork_scaler"] = Card(
        id="test_paperwork_scaler",
        name="Test Paperwork Scaler",
        class_="bureaucrat",
        type="action",
        cost=1,
        rarity="common",
        text="Deal damage per Paperwork.",
        effects=[
            Effect(
                type="damage_per_status",
                target="enemy",
                status="paperwork",
                amount_per_stack=4,
            )
        ],
        tags=["paperwork", "damage"],
    )
    policy.card_database["test_plain_strike"] = Card(
        id="test_plain_strike",
        name="Test Plain Strike",
        class_="bureaucrat",
        type="action",
        cost=1,
        rarity="common",
        text="Deal 8 damage.",
        effects=[
            Effect(
                type="deal_damage",
                target="enemy",
                amount=8,
            )
        ],
        tags=["damage"],
    )
    policy.card_database["test_paperwork_form"] = Card(
        id="test_paperwork_form",
        name="Test Paperwork Form",
        class_="bureaucrat",
        type="action",
        cost=1,
        rarity="common",
        text="Apply Paperwork.",
        effects=[
            Effect(
                type="apply_status",
                target="enemy",
                status="paperwork",
                amount=4,
            )
        ],
        tags=["paperwork", "form"],
    )


def base_observation() -> Observation:
    return Observation(
        phase="combat",
        legal_actions=(
            Action("play_card", index=0, target_index=0),
            Action("play_card", index=1, target_index=0),
            Action("end_turn"),
        ),
        character_id="bureaucrat",
        act=1,
        fight_number=1,
        hp=50,
        max_hp=60,
        gold=0,
        deck_size=10,
        relic_count=0,
        completed_nodes=0,
        current_node_id="node",
        current_node_type="combat",
        available_map_node_ids=(),
        available_map_node_types=(),
        combat_turn=1,
        energy=3,
        hand_card_ids=(
            "test_paperwork_scaler",
            "test_plain_strike",
        ),
        hand_card_costs=(1, 1),
        enemy_ids=("enemy",),
        enemy_hp=(40,),
        enemy_block=(0,),
        enemy_status_ids=(("paperwork",),),
        enemy_status_amounts=((8,),),
        incoming_damage=0,
        deck_card_ids=("bureaucrat_basic_strike",),
    )


def test_heuristic_v2_uses_enemy_paperwork_status_for_scaler_cards() -> None:
    policy = HeuristicV2Policy(seed=1)
    add_test_cards(policy)
    observation = base_observation()

    action = policy.choose_action(observation)

    assert action.kind == "play_card"
    assert action.index == 0


def test_heuristic_v2_relic_synergy_prefers_matching_cards() -> None:
    policy = HeuristicV2Policy(seed=1)
    add_test_cards(policy)
    observation = replace(
        base_observation(),
        relic_ids=("paperwork_engine_relic",),
        hand_card_ids=("test_paperwork_form", "test_plain_strike"),
    )

    action = policy.choose_action(observation)

    assert action.kind == "play_card"
    assert action.index == 0
