from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.checkpoint_training import (  # noqa: E402
    checkpoint_train_from_manifest,
    format_checkpoint_training_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Checkpoint-train class-specific Q runners and keep best models."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to class_runners_manifest.json.",
    )
    parser.add_argument("--characters", nargs="*", default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_class_runners_checkpointed",
    )
    parser.add_argument("--seed", type=int, default=60001)
    parser.add_argument("--episodes", type=int, default=100000)
    parser.add_argument(
        "--minutes",
        type=float,
        default=None,
        help="Optional wall-clock limit per worker/class.",
    )
    parser.add_argument("--checkpoint-interval", type=int, default=200)
    parser.add_argument("--eval-runs", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel worker processes. 0 = auto, 1 = sequential.",
    )
    args = parser.parse_args()

    result = checkpoint_train_from_manifest(
        manifest_path=args.manifest,
        output_dir=args.out_dir,
        character_ids=args.characters,
        seed=args.seed,
        episodes=args.episodes,
        minutes=args.minutes,
        checkpoint_interval=args.checkpoint_interval,
        eval_runs=args.eval_runs,
        max_steps=args.max_steps,
        workers=args.workers,
    )

    print(format_checkpoint_training_summary(result["characters"]))
    print("")
    print("Saved checkpointed runners:")
    print(f"  Manifest: {result['manifest_path']}")


if __name__ == "__main__":
    main()
