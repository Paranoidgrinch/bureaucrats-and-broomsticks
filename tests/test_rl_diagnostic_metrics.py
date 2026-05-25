from bab.sim.metrics import summarize_policy_rollouts
from bab.sim.rl_env import RolloutResult


def test_summarize_policy_rollouts_reports_stalls_and_zero_damage() -> None:
    results = [
        RolloutResult(
            seed=1,
            steps=80,
            total_reward=-10.0,
            outcome="stalled",
            completed_nodes=0,
            fights_won=0,
            gold=0,
            deck_size=10,
            relic_count=0,
            damage_dealt=0,
            damage_taken=12,
            first_combat_damage_dealt=0,
            first_combat_damage_taken=12,
            first_combat_turns=80,
            first_combat_zero_damage=True,
        ),
        RolloutResult(
            seed=2,
            steps=20,
            total_reward=15.0,
            outcome="win",
            completed_nodes=3,
            fights_won=2,
            gold=42,
            deck_size=12,
            relic_count=1,
            damage_dealt=55,
            damage_taken=4,
            first_combat_damage_dealt=18,
            first_combat_damage_taken=2,
            first_combat_turns=3,
            first_combat_zero_damage=False,
        ),
    ]

    summary = summarize_policy_rollouts(results)

    assert summary["runs"] == 2
    assert summary["stalls"] == 1
    assert summary["zero_damage_runs"] == 1
    assert summary["first_combat_zero_damage_runs"] == 1
    assert summary["stall_rate"] == 0.5
    assert summary["first_combat_zero_damage_rate"] == 0.5
