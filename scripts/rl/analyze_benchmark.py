from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.balance_report import (  # noqa: E402
    BalanceReportThresholds,
    build_balance_report,
    format_balance_report_console,
    load_benchmark_payload,
    write_balance_report_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a balance report from an agent benchmark JSON."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        required=True,
        help="Path to benchmark JSON created by scripts/benchmark_agents.py.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
    )
    parser.add_argument("--stem", type=str, default=None)
    parser.add_argument("--hard-threshold", type=float, default=0.10)
    parser.add_argument("--easy-threshold", type=float, default=0.75)
    parser.add_argument("--random-warning-threshold", type=float, default=0.10)
    parser.add_argument("--disagreement-threshold", type=float, default=0.10)
    args = parser.parse_args()

    payload = load_benchmark_payload(args.benchmark)
    thresholds = BalanceReportThresholds(
        hard_competent_win_rate=args.hard_threshold,
        easy_competent_win_rate=args.easy_threshold,
        random_warning_win_rate=args.random_warning_threshold,
        agent_disagreement_win_rate=args.disagreement_threshold,
    )
    report = build_balance_report(payload, thresholds=thresholds)

    out_dir = args.out_dir or args.benchmark.parent
    stem = args.stem or f"{args.benchmark.stem}_balance_report"

    json_path, markdown_path = write_balance_report_bundle(
        report,
        out_dir,
        stem=stem,
    )

    print(format_balance_report_console(report))
    print("")
    print("Saved balance report:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {markdown_path}")


if __name__ == "__main__":
    main()
