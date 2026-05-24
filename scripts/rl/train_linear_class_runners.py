from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.linear_q import (  # noqa: E402
    LinearQConfig,
    checkpoint_train_linear_from_characters,
    format_linear_training_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train checkpointed class-specific Linear-Q runners."
    )
    parser.add_argument("--characters", nargs="*", default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "rl_linear_class_runners")
    parser.add_argument("--seed", type=int, default=100001)
    parser.add_argument("--episodes", type=int, default=100000)
    parser.add_argument("--minutes", type=float, default=None)
    parser.add_argument("--checkpoint-interval", type=int, default=200)
    parser.add_argument("--eval-runs", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--imitation-episodes", type=int, default=300)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--alpha", type=float, default=0.04)
    parser.add_argument("--gamma", type=float, default=0.96)
    parser.add_argument("--epsilon-start", type=float, default=0.40)
    parser.add_argument("--epsilon-end", type=float, default=0.04)
    parser.add_argument("--epsilon-decay-episodes", type=int, default=2500)
    parser.add_argument("--gradient-clip", type=float, default=20.0)
    parser.add_argument("--weight-clip", type=float, default=50.0)
    parser.add_argument("--heuristic-explore-probability", type=float, default=0.65)
    parser.add_argument("--heuristic-tiebreak-margin", type=float, default=0.10)
    parser.add_argument("--no-heuristic-guidance", action="store_true")
    args = parser.parse_args()

    config = LinearQConfig(
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
        gradient_clip=args.gradient_clip,
        weight_clip=args.weight_clip,
        heuristic_explore_probability=args.heuristic_explore_probability,
        heuristic_tiebreak_margin=args.heuristic_tiebreak_margin,
    )

    result = checkpoint_train_linear_from_characters(
        character_ids=args.characters,
        output_dir=args.out_dir,
        seed=args.seed,
        episodes=args.episodes,
        minutes=args.minutes,
        checkpoint_interval=args.checkpoint_interval,
        eval_runs=args.eval_runs,
        max_steps=args.max_steps,
        imitation_episodes=args.imitation_episodes,
        workers=args.workers,
        config=config,
        use_heuristic_guidance=not args.no_heuristic_guidance,
    )

    print(format_linear_training_summary(result["characters"]))
    print("")
    print("Saved Linear-Q class runners:")
    print(f"  Manifest: {result['manifest_path']}")


if __name__ == "__main__":
    main()
