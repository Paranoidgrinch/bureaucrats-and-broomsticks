from random import Random

import pytest

from bab.run_map import (
    RunMap,
    combat_difficulty_for_depth,
    generate_act_map,
)


def test_generate_act_map_creates_start_nodes_and_boss() -> None:
    run_map = generate_act_map(
        Random(1),
        act=1,
        steps_before_boss=6,
        width=3,
    )

    assert isinstance(run_map, RunMap)
    assert run_map.act == 1
    assert len(run_map.start_node_ids) == 3
    assert run_map.boss_node_id == "act_1_boss"

    boss_node = run_map.get_node(run_map.boss_node_id)

    assert boss_node.node_type == "boss"
    assert boss_node.encounter_difficulty == "boss"
    assert boss_node.next_node_ids == ()


def test_generate_act_map_uses_expected_number_of_nodes() -> None:
    steps_before_boss = 6
    width = 3

    run_map = generate_act_map(
        Random(1),
        act=1,
        steps_before_boss=steps_before_boss,
        width=width,
    )

    expected_nodes = steps_before_boss * width + 1

    assert len(run_map.nodes) == expected_nodes


def test_every_non_boss_node_points_to_later_nodes() -> None:
    run_map = generate_act_map(
        Random(1),
        act=1,
        steps_before_boss=6,
        width=3,
    )

    for node in run_map.nodes.values():
        if node.node_type == "boss":
            assert node.next_node_ids == ()
            continue

        assert node.next_node_ids

        for next_node_id in node.next_node_ids:
            next_node = run_map.get_node(next_node_id)
            assert next_node.depth > node.depth


def test_available_next_nodes_returns_node_objects() -> None:
    run_map = generate_act_map(
        Random(1),
        act=1,
        steps_before_boss=6,
        width=3,
    )

    start_node = run_map.get_node(run_map.start_node_ids[0])
    next_nodes = run_map.available_next_nodes(start_node.id)

    assert next_nodes
    assert all(next_node.id in start_node.next_node_ids for next_node in next_nodes)


def test_standard_act_map_contains_core_node_types() -> None:
    run_map = generate_act_map(
        Random(1),
        act=1,
        steps_before_boss=6,
        width=3,
    )

    node_types = {
        node.node_type
        for node in run_map.nodes.values()
    }

    assert {
        "combat",
        "elite",
        "event",
        "waiting_room",
        "boss",
    } <= node_types


def test_combat_and_special_nodes_have_expected_payloads() -> None:
    run_map = generate_act_map(
        Random(1),
        act=1,
        steps_before_boss=6,
        width=3,
    )

    for node in run_map.nodes.values():
        if node.node_type == "combat":
            assert node.encounter_difficulty in {"easy", "normal"}
            assert node.event_type is None

        if node.node_type == "elite":
            assert node.encounter_difficulty == "elite"
            assert node.event_type is None

        if node.node_type == "boss":
            assert node.encounter_difficulty == "boss"
            assert node.event_type is None

        if node.node_type == "event":
            assert node.encounter_difficulty is None
            assert node.event_type in {"narrative", "risk_reward", "deck"}

        if node.node_type == "waiting_room":
            assert node.encounter_difficulty is None
            assert node.event_type is None


def test_combat_difficulty_for_depth_starts_easy_then_becomes_normal() -> None:
    assert combat_difficulty_for_depth(1, 6) == "easy"
    assert combat_difficulty_for_depth(2, 6) == "normal"
    assert combat_difficulty_for_depth(6, 6) == "normal"


def test_generate_act_map_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError, match="Act must be at least 1"):
        generate_act_map(Random(1), act=0)

    with pytest.raises(ValueError, match="at least 4 steps"):
        generate_act_map(Random(1), steps_before_boss=3)

    with pytest.raises(ValueError, match="width must be at least 2"):
        generate_act_map(Random(1), width=1)


def test_unknown_node_id_raises_clear_error() -> None:
    run_map = generate_act_map(Random(1))

    with pytest.raises(KeyError, match="Unknown map node id"):
        run_map.get_node("missing_node")