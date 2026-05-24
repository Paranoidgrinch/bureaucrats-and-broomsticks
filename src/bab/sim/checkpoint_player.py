"""Policy wrapper for best checkpointed class-specific Q runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bab.sim.agents import HeuristicPolicy
from bab.sim.q_learning import QLearningPolicy
from bab.sim.rl_env import Action, Observation


class CheckpointBestPolicy:
    """Load and use the best checkpointed Q model for each character class.

    This is closer to the intended "good player" runner than the earlier
    GoodPlayerPolicy: it always tries to use the learned per-class model.
    If a model path is missing, it falls back to the heuristic to avoid crashes.
    """

    name = "checkpoint_q"

    def __init__(
        self,
        *,
        manifest_path: str | Path,
        seed: int | None = None,
        fallback_to_heuristic: bool = True,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest = load_checkpoint_manifest(self.manifest_path)
        self.seed = seed
        self.fallback_to_heuristic = fallback_to_heuristic
        self.model_paths = best_checkpoint_model_paths(
            self.manifest,
            base_dir=self.manifest_path.parent,
        )
        self._policies: dict[str, QLearningPolicy] = {}
        self._heuristic = HeuristicPolicy(seed=seed)

    def choose_action(self, observation: Observation) -> Action:
        character_id = observation.character_id
        policy = self._policy_for_character(character_id)
        if policy is not None:
            return policy.choose_action(observation)

        if self.fallback_to_heuristic:
            return self._heuristic.choose_action(observation)

        legal = observation.legal_actions
        if legal:
            return legal[0]
        return Action("noop")

    def _policy_for_character(
        self,
        character_id: str,
    ) -> QLearningPolicy | None:
        if character_id in self._policies:
            return self._policies[character_id]

        model_path = self.model_paths.get(character_id)
        if model_path is None or not model_path.exists():
            return None

        policy = QLearningPolicy.load(model_path, seed=self.seed)
        self._policies[character_id] = policy
        return policy


def load_checkpoint_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def best_checkpoint_model_paths(
    manifest: dict[str, Any],
    *,
    base_dir: Path,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}

    for character in manifest.get("characters", []):
        character_id = character.get("character_id")
        model_path_value = character.get("best_model_path")
        if not character_id or not model_path_value:
            continue

        model_path = Path(model_path_value)
        if not model_path.is_absolute() and not model_path.exists():
            candidate = base_dir / character_id / "best_q_learning_agent.json"
            if candidate.exists():
                model_path = candidate

        paths[character_id] = model_path

    return paths


def format_checkpoint_selection(manifest: dict[str, Any]) -> str:
    lines = ["=== Best Checkpoint Runner Selection ==="]

    for character in manifest.get("characters", []):
        best = character.get("best_checkpoint") or {}
        lines.append(
            f"{character.get('character_id')}: "
            f"episode {best.get('episode')} | "
            f"wins {best.get('q_wins')} | "
            f"avg_reward {float(best.get('q_average_reward', 0.0)):.2f} | "
            f"avg_damage_dealt {float(best.get('q_average_damage_dealt', 0.0)):.1f} | "
            f"avg_damage_taken {float(best.get('q_average_damage_taken', 0.0)):.1f}"
        )

    return "\n".join(lines)
