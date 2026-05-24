from bab.sim.class_runner_improvement import (
    continue_training_class_runner,
    continue_training_policy,
    model_paths_from_class_runner_manifest,
)
from bab.sim.q_learning import train_q_learning_agent


def test_continue_training_policy_smoke() -> None:
    training = train_q_learning_agent(
        character_id="hedge_witch",
        imitation_episodes=1,
        episodes=1,
        seed=1,
        max_steps=60,
    )

    results = continue_training_policy(
        training.policy,
        character_id="hedge_witch",
        seed=10,
        episodes=1,
        max_steps=60,
    )

    assert len(results) == 1
    assert results[0].steps > 0


def test_continue_training_class_runner_smoke(tmp_path) -> None:
    training = train_q_learning_agent(
        character_id="hedge_witch",
        imitation_episodes=1,
        episodes=1,
        seed=2,
        max_steps=60,
    )
    source_model = training.policy.save(tmp_path / "source_model.json")

    result = continue_training_class_runner(
        character_id="hedge_witch",
        model_path=source_model,
        output_dir=tmp_path / "out",
        seed=3,
        episodes=1,
        eval_runs=1,
        max_steps=60,
    )

    assert result["character_id"] == "hedge_witch"
    assert result["q_table_entries"] > 0
    assert result["evaluation_summary"]["q_learning"]["runs"] == 1
    assert (tmp_path / "out" / "hedge_witch" / "q_learning_agent.json").exists()


def test_model_paths_from_manifest() -> None:
    manifest = {
        "characters": [
            {
                "character_id": "a",
                "model_path": "runs/a/q_learning_agent.json",
            }
        ]
    }

    paths = model_paths_from_class_runner_manifest(manifest)

    assert "a" in paths
    assert str(paths["a"]).endswith("q_learning_agent.json")
