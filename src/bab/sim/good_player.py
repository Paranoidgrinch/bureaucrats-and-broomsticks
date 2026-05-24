"""Good-player policy built from class-specific runner evaluations.

This policy is intended for future balance diagnostics:
- it is not a per-seed oracle
- it selects one runner type per character class from validation results
- if the class-specific Q runner outperformed the heuristic for that class,
  it loads that class model
- otherwise it falls back to the heuristic policy
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bab.sim.agents import HeuristicPolicy, Policy
from bab.sim.q_learning import QLearningPolicy
from bab.sim.rl_env import Action, Observation


class GoodPlayerPolicy:
    name = "good_player"

    def __init__(
        self,
        *,
        manifest_path: str | Path,
        seed: int | None = None,
        prefer_q_on_equal_wins: bool = False,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest = load_class_runners_manifest(self.manifest_path)
        self.seed = seed
        self.prefer_q_on_equal_wins = prefer_q_on_equal_wins

        self.runner_types = select_runner_types(
            self.manifest,
            prefer_q_on_equal_wins=prefer_q_on_equal_wins,
        )
        self.model_paths = collect_model_paths(
            self.manifest,
            base_dir=self.manifest_path.parent,
        )

        self.heuristic = HeuristicPolicy(seed=seed)
        self._q_policies: dict[str, QLearningPolicy] = {}

    def choose_action(self, observation: Observation) -> Action:
        character_id = observation.character_id
        runner_type = self.runner_types.get(character_id, "heuristic")

        if runner_type == "q_learning":
            policy = self._q_policy_for_character(character_id)
            if policy is not None:
                return policy.choose_action(observation)

        return self.heuristic.choose_action(observation)

    def _q_policy_for_character(
        self,
        character_id: str,
    ) -> QLearningPolicy | None:
        if character_id in self._q_policies:
            return self._q_policies[character_id]

        model_path = self.model_paths.get(character_id)
        if model_path is None or not model_path.exists():
            return None

        policy = QLearningPolicy.load(model_path, seed=self.seed)
        self._q_policies[character_id] = policy
        return policy


def load_class_runners_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_runner_types(
    manifest: dict[str, Any],
    *,
    prefer_q_on_equal_wins: bool = False,
) -> dict[str, str]:
    selections: dict[str, str] = {}

    for character in manifest.get("characters", []):
        character_id = character["character_id"]
        evaluation = character.get("evaluation_summary", {})

        heuristic = evaluation.get("heuristic", {})
        q_learning = evaluation.get("q_learning", {})

        heuristic_wins = int(heuristic.get("wins", 0))
        q_wins = int(q_learning.get("wins", 0))
        heuristic_reward = float(heuristic.get("average_reward", 0.0))
        q_reward = float(q_learning.get("average_reward", 0.0))

        use_q = False
        if q_wins > heuristic_wins:
            use_q = True
        elif q_wins == heuristic_wins:
            if prefer_q_on_equal_wins:
                use_q = q_reward >= heuristic_reward
            else:
                use_q = q_reward > heuristic_reward

        selections[character_id] = "q_learning" if use_q else "heuristic"

    return selections


def collect_model_paths(
    manifest: dict[str, Any],
    *,
    base_dir: Path,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}

    for character in manifest.get("characters", []):
        character_id = character["character_id"]
        model_path_value = character.get("model_path")
        if not model_path_value:
            continue

        model_path = Path(model_path_value)
        if not model_path.is_absolute():
            # Most manifests currently store paths relative to the repository root.
            # Try that path first; if it does not exist, fall back to manifest dir.
            if not model_path.exists():
                model_path = base_dir / model_path.name
        paths[character_id] = model_path

    return paths


def format_good_player_selection(
    manifest: dict[str, Any],
    *,
    prefer_q_on_equal_wins: bool = False,
) -> str:
    selections = select_runner_types(
        manifest,
        prefer_q_on_equal_wins=prefer_q_on_equal_wins,
    )

    lines = ["=== Good Player Runner Selection ==="]
    for character in manifest.get("characters", []):
        character_id = character["character_id"]
        evaluation = character.get("evaluation_summary", {})
        heuristic = evaluation.get("heuristic", {})
        q_learning = evaluation.get("q_learning", {})

        lines.append(
            f"{character_id}: {selections.get(character_id, 'heuristic')} | "
            f"H wins {heuristic.get('wins', 0)}/{heuristic.get('runs', 0)}, "
            f"Q wins {q_learning.get('wins', 0)}/{q_learning.get('runs', 0)} | "
            f"H reward {float(heuristic.get('average_reward', 0.0)):.2f}, "
            f"Q reward {float(q_learning.get('average_reward', 0.0)):.2f}"
        )

    return "\n".join(lines)
