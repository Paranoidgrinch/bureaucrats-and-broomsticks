from bab.sim.auto_runner import SimConfig, simulate_runs


def test_auto_runner_can_simulate_multiple_random_runs_without_engine_errors() -> None:
    summary = simulate_runs(
        SimConfig(
            runs=5,
            seed=123,
            max_combat_turns=60,
        ),
        raise_errors=True,
    )

    assert summary.total_runs == 5
    assert summary.errors == 0
    assert summary.wins + summary.defeats + summary.stalled == 5
