from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.auto_runner import SimConfig, format_summary, simulate_runs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run headless random simulations for balancing and bug hunting."
    )
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-combat-turns", type=int, default=80)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    summary = simulate_runs(
        SimConfig(
            runs=args.runs,
            seed=args.seed,
            max_combat_turns=args.max_combat_turns,
        ),
        raise_errors=args.fail_on_error,
    )

    print(format_summary(summary))

    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(summary.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote JSON summary to {args.json_out}")

    if args.fail_on_error and summary.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
