import json

from bab.sim.class_runners import (
    rollout_results_to_benchmark_rows,
    train_class_runner,
    train_class_runners_for_characters,
)
from bab.sim.rl_env import RolloutResult


def test_rollout_results_to_benchmark_rows() -> None:
    rows = rollout_results_to_benchmark_rows(
        {
            "q_learning": [
                RolloutResult(
                    seed=1,
                    steps=10,
                    total_reward=12.5,
                    outcome="win",
                    completed_nodes=10,
                    fights_won=8,
                    gold=100,
                    deck_size=15,
                    relic_count=2,
                )
            ]
        },
        character_id="hedge_witch",
    )

    assert len(rows) == 1
    assert rows[0]["policy"] == "q_learning"
    assert rows[0]["character_id"] == "hedge_witch"
    assert rows[0]["outcome"] == "win"


def test_train_class_runner_smoke(tmp_path) -> None:
    result = train_class_runner(
        character_id="hedge_witch",
        output_dir=tmp_path,
        seed=1,
        imitation_episodes=1,
        episodes=1,
        eval_runs=1,
        max_steps=60,
    )

    assert result["character_id"] == "hedge_witch"
    assert result["q_table_entries"] > 0
    assert result["evaluation_summary"]["q_learning"]["runs"] == 1
    assert (tmp_path / "hedge_witch" / "q_learning_agent.json").exists()
    assert (tmp_path / "hedge_witch" / "class_runner_manifest.json").exists()


def test_train_class_runners_for_characters_smoke(tmp_path) -> None:
    result = train_class_runners_for_characters(
        character_ids=["hedge_witch"],
        output_dir=tmp_path,
        seed=2,
        imitation_episodes=1,
        episodes=1,
        eval_runs=1,
        max_steps=60,
    )

    assert result["manifest_path"].exists()
    assert result["benchmark_json"].exists()
    assert result["benchmark_csv"].exists()
    assert result["benchmark_summary_csv"].exists()

    manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
    assert manifest["character_ids"] == ["hedge_witch"]
    assert manifest["characters"][0]["character_id"] == "hedge_witch"
