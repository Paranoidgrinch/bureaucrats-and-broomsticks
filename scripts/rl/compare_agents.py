from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.agents import (  # noqa: E402
    HeuristicPolicy,
    RandomPolicy,
    compare_policies,
    summarize_policy_results,
)
from bab.sim.metrics import write_results_bundle  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare simple policies through the RL environment."
    )
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--character-id", type=str, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Optional directory for JSON/CSV metric exports.",
    )
    parser.add_argument(
        "--stem",
        type=str,
        default="agent_comparison",
        help="Output filename stem used with --out-dir.",
    )
    args = parser.parse_args()

    policies = [
        RandomPolicy(seed=args.seed),
        HeuristicPolicy(seed=args.seed),
    ]

    results = compare_policies(
        policies,
        runs=args.runs,
        seed=args.seed,
        max_steps=args.max_steps,
        character_id=args.character_id,
    )

    print(summarize_policy_results(results))

    if args.out_dir is not None:
        json_path, csv_path = write_results_bundle(
            results,
            args.out_dir,
            stem=args.stem,
        )
        print("")
        print("Saved metric exports:")
        print(f"  JSON: {json_path}")
        print(f"  CSV:  {csv_path}")


if __name__ == "__main__":
    main()
