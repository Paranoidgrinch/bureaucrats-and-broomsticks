from random import Random

from bab.console.run_flow import create_run_state
from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.run.state import (
    complete_current_map_node,
    create_combat_state_for_next_encounter,
    enter_map_node,
)


def test_act_5_divine_ledger_is_three_boss_gauntlet() -> None:
    catalog = load_content_catalog_from_act_manifest(
        "data/acts/act_5_divine_ledger.json"
    )
    run_state = create_run_state(catalog=catalog, rng=Random(123))

    manifest = catalog.act_manifest
    assert manifest.id == "act_5_divine_ledger"
    assert manifest.name == "Act V: The Divine Ledger"
    assert manifest.map.layout == "boss_gauntlet"
    assert manifest.map.boss_count == 3
    assert len(manifest.map.boss_encounter_ids) == 4

    assert manifest.event_files == []
    assert catalog.event_database == {}
    assert manifest.treasure.mimic_chance == 0
    assert manifest.treasure.mimic_encounter_id is None

    run_map = run_state.run_map
    assert run_map.start_node_ids == ("act_5_boss_01",)
    assert run_map.boss_node_id == "act_5_boss_03"
    assert list(run_map.nodes) == [
        "act_5_boss_01",
        "act_5_boss_02",
        "act_5_boss_03",
    ]

    boss_nodes = list(run_map.nodes.values())
    assert {node.node_type for node in boss_nodes} == {"boss"}
    assert {node.encounter_difficulty for node in boss_nodes} == {"boss"}
    assert {node.event_type for node in boss_nodes} == {None}
    assert [node.next_node_ids for node in boss_nodes] == [
        ("act_5_boss_02",),
        ("act_5_boss_03",),
        (),
    ]

    chosen_encounter_ids = [node.encounter_id for node in boss_nodes]
    assert all(encounter_id in manifest.map.boss_encounter_ids for encounter_id in chosen_encounter_ids)
    assert len(set(chosen_encounter_ids)) == 3

    for encounter_id in manifest.map.boss_encounter_ids:
        encounter = catalog.encounter_database[encounter_id]
        assert encounter.act == 5
        assert encounter.difficulty == "boss"
        assert len(encounter.enemies) == 1
        assert encounter.enemies[0] in catalog.enemy_database


def test_act_5_divine_ledger_fixed_boss_encounters_and_completion() -> None:
    catalog = load_content_catalog_from_act_manifest(
        "data/acts/act_5_divine_ledger.json"
    )
    run_state = create_run_state(catalog=catalog, rng=Random(123))

    expected_node_ids = [
        "act_5_boss_01",
        "act_5_boss_02",
        "act_5_boss_03",
    ]

    for index, node_id in enumerate(expected_node_ids):
        enter_map_node(run_state, node_id)

        node = run_state.current_node()
        assert node is not None
        assert node.encounter_id is not None

        combat_state = create_combat_state_for_next_encounter(run_state)
        assert combat_state.encounter_id == node.encounter_id

        complete_current_map_node(run_state)

        if index < 2:
            assert not run_state.is_complete()
        else:
            assert run_state.is_complete()
