from bab.sim.linear_q import (
    linear_checkpoint_disqualification_reasons,
    linear_checkpoint_is_valid,
    linear_checkpoint_score,
)


def make_checkpoint(**overrides):
    checkpoint = {
        "linear_wins": 0,
        "linear_stalls": 0,
        "linear_truncated": 0,
        "linear_zero_damage_runs": 0,
        "linear_first_combat_zero_damage_runs": 0,
        "linear_zero_completed_nodes_runs": 0,
        "linear_average_reward": 0.0,
        "linear_average_damage_dealt": 1.0,
        "linear_average_damage_taken": 0.0,
        "linear_average_first_combat_damage_dealt": 1.0,
    }
    checkpoint.update(overrides)
    return checkpoint


def test_linear_checkpoint_gate_accepts_clean_checkpoint() -> None:
    checkpoint = make_checkpoint(linear_wins=1, linear_average_reward=10.0)

    assert linear_checkpoint_is_valid(checkpoint)
    assert linear_checkpoint_disqualification_reasons(checkpoint) == []


def test_linear_checkpoint_gate_rejects_stalls_and_zero_damage() -> None:
    checkpoint = make_checkpoint(
        linear_stalls=1,
        linear_zero_damage_runs=1,
        linear_first_combat_zero_damage_runs=1,
        linear_zero_completed_nodes_runs=1,
        linear_average_first_combat_damage_dealt=0.0,
    )

    reasons = linear_checkpoint_disqualification_reasons(checkpoint)

    assert not linear_checkpoint_is_valid(checkpoint)
    assert "stalls" in reasons
    assert "zero_damage_runs" in reasons
    assert "first_combat_zero_damage_runs" in reasons
    assert "zero_completed_nodes_runs" in reasons
    assert "average_first_combat_damage_dealt_non_positive" in reasons


def test_linear_checkpoint_score_prefers_clean_checkpoint_over_broken_winner() -> None:
    clean = make_checkpoint(linear_wins=0, linear_average_reward=0.0)
    broken = make_checkpoint(
        linear_wins=50,
        linear_average_reward=999.0,
        linear_stalls=1,
        linear_zero_damage_runs=1,
    )

    assert linear_checkpoint_score(clean) > linear_checkpoint_score(broken)

from pathlib import Path

from bab.sim.linear_q import linear_best_model_paths


def test_linear_checkpoint_gate_accepts_legacy_checkpoint_without_new_metrics() -> None:
    legacy_checkpoint = {
        "linear_wins": 1,
        "linear_average_reward": 10.0,
        "linear_average_damage_dealt": 100.0,
        "linear_average_damage_taken": 5.0,
    }

    assert linear_checkpoint_is_valid(legacy_checkpoint)
    assert linear_checkpoint_disqualification_reasons(legacy_checkpoint) == []


def test_linear_best_model_paths_skips_invalid_checkpoints(tmp_path: Path) -> None:
    valid_dir = tmp_path / "valid_character"
    invalid_dir = tmp_path / "invalid_character"
    valid_dir.mkdir()
    invalid_dir.mkdir()
    valid_model = valid_dir / "best_linear_q_agent.json"
    invalid_model = invalid_dir / "best_linear_q_agent.json"
    valid_model.write_text("{}", encoding="utf-8")
    invalid_model.write_text("{}", encoding="utf-8")

    manifest = {
        "characters": [
            {
                "character_id": "valid_character",
                "best_model_path": str(valid_model),
                "best_checkpoint": make_checkpoint(
                    linear_wins=1,
                    linear_average_reward=10.0,
                ),
            },
            {
                "character_id": "invalid_character",
                "best_model_path": str(invalid_model),
                "best_checkpoint": make_checkpoint(
                    linear_stalls=1,
                    linear_zero_damage_runs=1,
                ),
            },
        ],
    }

    paths = linear_best_model_paths(manifest, base_dir=tmp_path)

    assert paths == {"valid_character": valid_model}
