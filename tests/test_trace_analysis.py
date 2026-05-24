from bab.sim.agents import HeuristicPolicy, RandomPolicy
from bab.sim.trace_analysis import (
    analyze_trace_difference,
    action_label,
    action_signature,
    format_trace_difference_analysis,
)
from bab.sim.tracing import trace_policies_for_seed


def test_action_signature_and_label_for_map_action() -> None:
    action = {
        "kind": "choose_map_node",
        "node_type": "combat",
        "node_id": "node_1",
    }

    assert action_signature(action) == ("choose_map_node", "combat", "node_1")
    assert action_label(action) == "choose_map_node:combat[node_1]"


def test_trace_difference_analysis_smoke() -> None:
    trace = trace_policies_for_seed(
        {
            "random": RandomPolicy(seed=1),
            "heuristic": HeuristicPolicy(seed=1),
        },
        seed=1,
        max_steps=60,
    )

    analysis = analyze_trace_difference(
        trace,
        baseline_policy="random",
        challenger_policy="heuristic",
    )

    assert analysis["seed"] == 1
    assert analysis["baseline_policy"] == "random"
    assert analysis["challenger_policy"] == "heuristic"
    assert "baseline_map_path" in analysis
    assert "challenger_map_path" in analysis

    text = format_trace_difference_analysis(analysis)
    assert "Trace Difference Analysis" in text
    assert "Map paths" in text
