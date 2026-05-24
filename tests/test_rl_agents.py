from bab.sim.agents import (
    HeuristicPolicy,
    RandomPolicy,
    compare_policies,
    run_policy_rollout,
    summarize_policy_results,
)
from bab.sim.rl_env import RoguelikeEnv


def test_random_policy_returns_legal_action() -> None:
    env = RoguelikeEnv(seed=1)
    observation = env.reset()

    policy = RandomPolicy(seed=1)
    action = policy.choose_action(observation)

    assert action in observation.legal_actions


def test_heuristic_policy_returns_legal_actions_over_steps() -> None:
    env = RoguelikeEnv(seed=2)
    observation = env.reset()

    policy = HeuristicPolicy(seed=2)

    for _ in range(40):
        if observation.done:
            break
        action = policy.choose_action(observation)
        assert action in observation.legal_actions
        observation = env.step(action).observation


def test_heuristic_policy_rollout_does_not_crash() -> None:
    result = run_policy_rollout(
        HeuristicPolicy(seed=3),
        seed=3,
        max_steps=300,
    )

    assert result.steps > 0
    assert result.outcome in {"win", "defeat", "stalled", "truncated"}
    assert result.completed_nodes >= 0
    assert result.deck_size > 0


def test_compare_policies_produces_results_for_each_policy() -> None:
    results = compare_policies(
        [
            RandomPolicy(seed=10),
            HeuristicPolicy(seed=10),
        ],
        runs=2,
        seed=10,
        max_steps=200,
    )

    assert set(results) == {"random", "heuristic"}
    assert len(results["random"]) == 2
    assert len(results["heuristic"]) == 2

    summary = summarize_policy_results(results)
    assert "Policy: random" in summary
    assert "Policy: heuristic" in summary
