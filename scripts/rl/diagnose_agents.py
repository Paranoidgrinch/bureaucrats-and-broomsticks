from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.agents import HeuristicPolicy, RandomPolicy  # noqa: E402
from bab.sim.diagnostics import (  # noqa: E402
    compare_policies_by_seed,
    format_seed_diagnostics_summary,
    summarize_seed_diagnostics,
    write_seed_diagnostics_bundle,
)
from bab.sim.linear_q import LinearCheckpointPolicy, LinearQPolicy  # noqa: E402
from bab.sim.q_learning import QLearningPolicy  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare policies seed-by-seed on identical run seeds."
    )
    parser.add_argument(
        "--policy",
        choices=("q_learning", "linear_q", "linear_checkpoint"),
        default="linear_checkpoint",
        help="Learned policy type to compare against heuristic.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to model JSON or Linear-Q checkpoint training manifest.",
    )
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=10001)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--character-id", type=str, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_diagnostics",
    )
    parser.add_argument("--stem", type=str, default="seed_diagnostics")
    args = parser.parse_args()

    model_path = args.model

    if args.policy == "q_learning":
        learned_name = "q_learning"
        learned_factory = lambda policy_seed: QLearningPolicy.load(
            model_path,
            seed=policy_seed,
        )
    elif args.policy == "linear_q":
        learned_name = "linear_q"
        learned_factory = lambda policy_seed: LinearQPolicy.load(
            model_path,
            seed=policy_seed,
        )
    else:
        learned_name = "linear_checkpoint"
        learned_factory = lambda policy_seed: LinearCheckpointPolicy(
            manifest_path=model_path,
            seed=policy_seed,
        )

    rows = compare_policies_by_seed(
        {
            "random": lambda policy_seed: RandomPolicy(seed=policy_seed),
            "heuristic": lambda policy_seed: HeuristicPolicy(seed=policy_seed),
            learned_name: learned_factory,
        },
        runs=args.runs,
        seed=args.seed,
        max_steps=args.max_steps,
        character_id=args.character_id,
    )
    summary = summarize_seed_diagnostics(
        rows,
        teacher_policy="heuristic",
        learned_policy=learned_name,
    )
    json_path, csv_path = write_seed_diagnostics_bundle(
        rows,
        args.out_dir,
        stem=args.stem,
        teacher_policy="heuristic",
        learned_policy=learned_name,
    )

    print(format_seed_diagnostics_summary(summary))
    print("")
    print("Saved diagnostics:")
    print(f"  JSON: {json_path}")
    print(f"  CSV: {csv_path}")


if __name__ == "__main__":
    main()
