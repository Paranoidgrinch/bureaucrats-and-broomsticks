import csv
import json

from bab.sim.agents import HeuristicPolicy, RandomPolicy
from bab.sim.tracing import (
    action_summary,
    trace_policies_for_seed,
    trace_policy_rollout,
    write_trace_bundle,
)
from bab.sim.rl_env import RoguelikeEnv


def test_trace_policy_rollout_smoke() -> None:
    trace = trace_policy_rollout(
        RandomPolicy(seed=1),
        policy_name="random",
        seed=1,
        max_steps=40,
    )

    assert trace["policy"] == "random"
    assert trace["seed"] == 1
    assert "summary" in trace
    assert "steps" in trace
    assert trace["summary"]["steps"] >= 1


def test_trace_policies_for_seed_smoke() -> None:
    trace = trace_policies_for_seed(
        {
            "random": RandomPolicy(seed=2),
            "heuristic": HeuristicPolicy(seed=2),
        },
        seed=2,
        max_steps=40,
    )

    assert trace["seed"] == 2
    assert set(trace["traces"]) == {"random", "heuristic"}
    assert set(trace["summary"]) == {"random", "heuristic"}


def test_action_summary_for_initial_action() -> None:
    env = RoguelikeEnv(seed=3)
    observation = env.reset()
    action = observation.legal_actions[0]

    summary = action_summary(observation, action)

    assert summary["kind"] == action.kind
    assert "index" in summary


def test_write_trace_bundle(tmp_path) -> None:
    trace = trace_policies_for_seed(
        {
            "random": RandomPolicy(seed=4),
            "heuristic": HeuristicPolicy(seed=4),
        },
        seed=4,
        max_steps=40,
    )

    json_path, csv_path = write_trace_bundle(
        trace,
        tmp_path,
        stem="trace",
    )

    assert json_path.exists()
    assert csv_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert "policy" in rows[0]
    assert "action_kind" in rows[0]
