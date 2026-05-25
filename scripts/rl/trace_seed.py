from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.agents import HeuristicPolicy, RandomPolicy  # noqa: E402
from bab.sim.linear_q import LinearCheckpointPolicy, LinearQPolicy  # noqa: E402
from bab.sim.q_learning import QLearningPolicy  # noqa: E402
from bab.sim.tracing import (  # noqa: E402
    format_trace_summary,
    trace_policies_for_seed,
    write_trace_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trace policy decisions step-by-step for one seed."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--policy",
        choices=("q_learning", "linear_q", "linear_checkpoint"),
        default="linear_checkpoint",
        help=(
            "Learned policy type. Use linear_checkpoint with a checkpoint "
            "training manifest, linear_q with one best_linear_q_agent.json, or "
            "q_learning with the old tabular model."
        ),
    )
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to model JSON or Linear-Q checkpoint training manifest.",
    )
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--character-id", type=str, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_traces",
    )
    parser.add_argument("--stem", type=str, default=None)
    args = parser.parse_args()

    if args.policy == "q_learning":
        learned = QLearningPolicy.load(args.model, seed=args.seed)
        learned_name = "q_learning"
    elif args.policy == "linear_q":
        learned = LinearQPolicy.load(args.model, seed=args.seed)
        learned_name = "linear_q"
    else:
        learned = LinearCheckpointPolicy(manifest_path=args.model, seed=args.seed)
        learned_name = "linear_checkpoint"

    trace = trace_policies_for_seed(
        {
            "random": RandomPolicy(seed=args.seed),
            "heuristic": HeuristicPolicy(seed=args.seed),
            learned_name: learned,
        },
        seed=args.seed,
        max_steps=args.max_steps,
        character_id=args.character_id,
    )

    character_part = f"_{args.character_id}" if args.character_id else ""
    stem = args.stem or f"seed_{args.seed}{character_part}_{learned_name}_trace"
    json_path, csv_path = write_trace_bundle(
        trace,
        args.out_dir,
        stem=stem,
    )

    print(format_trace_summary(trace))
    print("")
    print("Saved trace:")
    print(f"  JSON: {json_path}")
    print(f"  CSV: {csv_path}")


if __name__ == "__main__":
    main()
