from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.agents import HeuristicPolicy, RandomPolicy  # noqa: E402
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
        "--model",
        type=Path,
        required=True,
        help="Path to saved q_learning_agent.json.",
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

    trace = trace_policies_for_seed(
        {
            "random": RandomPolicy(seed=args.seed),
            "heuristic": HeuristicPolicy(seed=args.seed),
            "q_learning": QLearningPolicy.load(args.model, seed=args.seed),
        },
        seed=args.seed,
        max_steps=args.max_steps,
        character_id=args.character_id,
    )

    stem = args.stem or f"seed_{args.seed}_trace"
    json_path, csv_path = write_trace_bundle(
        trace,
        args.out_dir,
        stem=stem,
    )

    print(format_trace_summary(trace))
    print("")
    print("Saved trace:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")


if __name__ == "__main__":
    main()
