import json

from bab.sim.checkpoint_player import (
    CheckpointBestPolicy,
    best_checkpoint_model_paths,
    format_checkpoint_selection,
)
from bab.sim.rl_env import RoguelikeEnv


def sample_manifest(tmp_path):
    return {
        "schema_version": 1,
        "characters": [
            {
                "character_id": "hedge_witch",
                "best_model_path": str(tmp_path / "missing.json"),
                "best_checkpoint": {
                    "episode": 200,
                    "q_wins": 5,
                    "q_average_reward": 42.0,
                    "q_average_damage_dealt": 123.0,
                    "q_average_damage_taken": 45.0,
                },
            }
        ],
    }


def test_best_checkpoint_model_paths(tmp_path) -> None:
    manifest = sample_manifest(tmp_path)
    paths = best_checkpoint_model_paths(manifest, base_dir=tmp_path)

    assert "hedge_witch" in paths
    assert str(paths["hedge_witch"]).endswith("missing.json")


def test_format_checkpoint_selection(tmp_path) -> None:
    text = format_checkpoint_selection(sample_manifest(tmp_path))

    assert "Best Checkpoint Runner Selection" in text
    assert "hedge_witch" in text
    assert "avg_damage_dealt" in text


def test_checkpoint_best_policy_falls_back_when_model_missing(tmp_path) -> None:
    manifest_path = tmp_path / "checkpoint_training_manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest(tmp_path)), encoding="utf-8")

    env = RoguelikeEnv(seed=1)
    observation = env.reset(character_id="hedge_witch")

    policy = CheckpointBestPolicy(manifest_path=manifest_path, seed=1)
    action = policy.choose_action(observation)

    assert action in observation.legal_actions
