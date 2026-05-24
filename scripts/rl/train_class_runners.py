from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.benchmark import format_benchmark_summary  # noqa: E402
from bab.sim.class_runners import (  # noqa: E402
    format_class_runners_overview,
    train_class_runners_for_characters,
)
from bab.sim.q_learning import QLearningConfig  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train one specialist Q-learning runner per character class."
    )
    parser.add_argument(
        "--characters",
        nargs="*",
        default=None,
        help="Character ids to train. Defaults to all character classes.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_class_runners",
    )
    parser.add_argument("--seed", type=int, default=30001)
    parser.add_argument("--imitation-episodes", type=int, default=300)
    parser.add_argument("--episodes", type=int, default=800)
    parser.add_argument("--eval-runs", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--alpha", type=float, default=0.15)
    parser.add_argument("--gamma", type=float, default=0.96)
    parser.add_argument("--epsilon-start", type=float, default=0.45)
    parser.add_argument("--epsilon-end", type=float, default=0.04)
    parser.add_argument("--epsilon-decay-episodes", type=int, default=350)
    parser.add_argument("--heuristic-explore-probability", type=float, default=0.75)
    parser.add_argument("--heuristic-tiebreak-margin", type=float, default=0.10)
    parser.add_argument("--imitation-bonus", type=float, default=5.0)
    parser.add_argument("--imitation-margin", type=float, default=1.0)
    parser.add_argument(
        "--disable-risk-aware-fallback",
        action="store_true",
    )
    parser.add_argument("--low-hp-fallback-ratio", type=float, default=0.35)
    parser.add_argument("--medium-hp-fallback-ratio", type=float, default=0.55)
    parser.add_argument("--low-hp-fallback-margin", type=float, default=6.0)
    parser.add_argument("--medium-hp-fallback-margin", type=float, default=2.0)
    parser.add_argument("--card-reward-fallback-margin", type=float, default=0.75)
    parser.add_argument("--map-fallback-margin", type=float, default=0.50)
    parser.add_argument(
        "--no-heuristic-guidance",
        action="store_true",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Reuse existing per-character manifests where present.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel worker processes. 0 = auto, 1 = sequential.",
    )
    args = parser.parse_args()

    config = QLearningConfig(
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
        heuristic_explore_probability=args.heuristic_explore_probability,
        heuristic_tiebreak_margin=args.heuristic_tiebreak_margin,
        imitation_bonus=args.imitation_bonus,
        imitation_margin=args.imitation_margin,
        risk_aware_fallback=not args.disable_risk_aware_fallback,
        low_hp_fallback_ratio=args.low_hp_fallback_ratio,
        medium_hp_fallback_ratio=args.medium_hp_fallback_ratio,
        low_hp_fallback_margin=args.low_hp_fallback_margin,
        medium_hp_fallback_margin=args.medium_hp_fallback_margin,
        card_reward_fallback_margin=args.card_reward_fallback_margin,
        map_fallback_margin=args.map_fallback_margin,
    )

    result = train_class_runners_for_characters(
        character_ids=args.characters,
        output_dir=args.out_dir,
        seed=args.seed,
        imitation_episodes=args.imitation_episodes,
        episodes=args.episodes,
        eval_runs=args.eval_runs,
        max_steps=args.max_steps,
        config=config,
        use_heuristic_guidance=not args.no_heuristic_guidance,
        skip_existing=args.skip_existing,
        workers=args.workers,
    )

    character_results = result["manifest"]["characters"]

    print(format_class_runners_overview(character_results))
    print("")
    print(format_benchmark_summary(result["benchmark_rows"]))
    print("")
    print("Saved class runners:")
    print(f"  Manifest: {result['manifest_path']}")
    print(f"  Benchmark JSON: {result['benchmark_json']}")
    print(f"  Benchmark CSV:  {result['benchmark_csv']}")
    print(f"  Benchmark Summary CSV: {result['benchmark_summary_csv']}")


if __name__ == "__main__":
    main()
