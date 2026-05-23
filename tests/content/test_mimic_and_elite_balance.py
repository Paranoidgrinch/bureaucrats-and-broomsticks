from random import Random

from bab.content.catalog import load_default_content_catalog
from bab.run.map import FIRST_ELITE_DEPTH, generate_act_map
from bab.sim.auto_runner import SimConfig, simulate_runs


def test_act_1_treasure_mimic_uses_dedicated_mimic_encounter() -> None:
    catalog = load_default_content_catalog()

    assert catalog.act_manifest.treasure.mimic_chance == 0.05
    assert catalog.act_manifest.treasure.mimic_encounter_id == "city_mimic_01"

    encounter = catalog.encounter_database["city_mimic_01"]
    assert encounter.difficulty == "mimic"
    assert encounter.enemies == ["receipt_mimic"]

    mimic = catalog.enemy_database["receipt_mimic"]
    assert "mimic" in mimic.tags
    assert "elite" not in mimic.tags
    assert "boss" not in mimic.tags


def test_generated_maps_do_not_place_elites_before_first_elite_depth() -> None:
    for seed in range(100):
        run_map = generate_act_map(
            Random(seed),
            act=1,
            steps_before_boss=9,
            width=4,
        )

        elite_nodes = [
            node
            for node in run_map.nodes.values()
            if node.node_type == "elite"
        ]

        assert all(node.depth >= FIRST_ELITE_DEPTH for node in elite_nodes)


def test_elite_nerf_sanity_values() -> None:
    catalog = load_default_content_catalog()

    assert catalog.enemy_database["red_tape_golem"].max_hp <= 96
    assert catalog.enemy_database["stampede_of_stamps"].max_hp <= 66
    assert catalog.enemy_database["licensed_chimera"].max_hp <= 90


def test_simulation_results_include_extended_diagnostics() -> None:
    summary = simulate_runs(
        SimConfig(
            runs=3,
            seed=500,
            max_combat_turns=60,
        ),
        raise_errors=True,
    )

    assert summary.errors == 0

    for result in summary.results:
        assert result.path_history is not None
        assert result.last_player_hp_before_node is not None
        assert result.last_player_hp_after_node is not None

        if result.last_node_type in {"combat", "elite", "boss", "treasure"}:
            assert result.last_node_id is not None
