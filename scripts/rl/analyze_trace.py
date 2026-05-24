from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.trace_analysis import (  # noqa: E402
    analyze_trace_difference,
    format_trace_difference_analysis,
    load_trace,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze where two policies diverge inside a trace JSON."
    )
    parser.add_argument(
        "--trace",
        type=Path,
        required=True,
        help="Path to a trace JSON created by scripts/trace_seed.py.",
    )
    parser.add_argument("--baseline", type=str, default="heuristic")
    parser.add_argument("--challenger", type=str, default="q_learning")
    parser.add_argument("--max-differences", type=int, default=20)
    args = parser.parse_args()

    trace = load_trace(args.trace)
    analysis = analyze_trace_difference(
        trace,
        baseline_policy=args.baseline,
        challenger_policy=args.challenger,
        max_differences=args.max_differences,
    )

    print(format_trace_difference_analysis(analysis))


if __name__ == "__main__":
    main()
