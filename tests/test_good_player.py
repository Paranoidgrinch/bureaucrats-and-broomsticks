import json

from bab.sim.good_player import (
    GoodPlayerPolicy,
    format_good_player_selection,
    select_runner_types,
)
from bab.sim.rl_env import RoguelikeEnv


def sample_manifest(tmp_path):
    return {
        "schema_version": 1,
        "characters": [
            {
                "character_id": "hedge_witch",
                "model_path": str(tmp_path / "missing_q_model.json"),
                "evaluation_summary": {
                    "heuristic": {
                        "runs": 10,
                        "wins": 8,
                        "average_reward": 100.0,
                    },
                    "q_learning": {
                        "runs": 10,
                        "wins": 7,
                        "average_reward": 90.0,
                    },
                },
            },
            {
                "character_id": "witch_clerk",
                "model_path": str(tmp_path / "missing_q_model.json"),
                "evaluation_summary": {
                    "heuristic": {
                        "runs": 10,
                        "wins": 4,
                        "average_reward": 50.0,
                    },
                    "q_learning": {
                        "runs": 10,
                        "wins": 5,
                        "average_reward": 60.0,
                    },
                },
            },
        ],
    }


def test_select_runner_types() -> None:
    manifest = {
        "characters": [
            {
                "character_id": "a",
                "evaluation_summary": {
                    "heuristic": {"wins": 3, "average_reward": 10.0},
                    "q_learning": {"wins": 5, "average_reward": 20.0},
                },
            },
            {
                "character_id": "b",
                "evaluation_summary": {
                    "heuristic": {"wins": 6, "average_reward": 30.0},
                    "q_learning": {"wins": 4, "average_reward": 40.0},
                },
            },
        ]
    }

    selections = select_runner_types(manifest)

    assert selections["a"] == "q_learning"
    assert selections["b"] == "heuristic"


def test_format_good_player_selection(tmp_path) -> None:
    text = format_good_player_selection(sample_manifest(tmp_path))

    assert "Good Player Runner Selection" in text
    assert "hedge_witch" in text
    assert "witch_clerk" in text


def test_good_player_policy_returns_legal_action_with_missing_q_model_fallback(tmp_path) -> None:
    manifest = sample_manifest(tmp_path)
    manifest_path = tmp_path / "class_runners_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    env = RoguelikeEnv(seed=1)
    observation = env.reset(character_id="witch_clerk")

    policy = GoodPlayerPolicy(manifest_path=manifest_path, seed=1)
    action = policy.choose_action(observation)

    assert action in observation.legal_actions
