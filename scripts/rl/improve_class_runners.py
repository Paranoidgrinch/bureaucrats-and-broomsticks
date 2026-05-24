from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.class_runner_improvement import (  # noqa: E402
    format_improvement_summary,
    improve_class_runners_from_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Continue training existing class-specific Q runners."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to class_runners_manifest.json from scripts/train_class_runners.py.",
    )
    parser.add_argument(
        "--characters",
        nargs="*",
        default=None,
        help="Character ids to continue training. Defaults to all in manifest.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_class_runners_improved",
    )
    parser.add_argument("--seed", type=int, default=50001)
    parser.add_argument("--episodes", type=int, default=800)
    parser.add_argument("--eval-runs", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel worker processes. 0 = auto, 1 = sequential.",
    )
    args = parser.parse_args()

    result = improve_class_runners_from_manifest(
        manifest_path=args.manifest,
        output_dir=args.out_dir,
        character_ids=args.characters,
        seed=args.seed,
        episodes=args.episodes,
        eval_runs=args.eval_runs,
        max_steps=args.max_steps,
        workers=args.workers,
    )

    print(format_improvement_summary(result["characters"]))
    print("")
    print("Saved improved class runners:")
    print(f"  Manifest: {result['manifest_path']}")


if __name__ == "__main__":
    main()
