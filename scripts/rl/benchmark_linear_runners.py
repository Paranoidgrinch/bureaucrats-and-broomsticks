from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.benchmark import format_benchmark_summary  # noqa: E402
from bab.sim.linear_q import (  # noqa: E402
    benchmark_linear_checkpoint_policy,
    format_linear_checkpoint_selection,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark best checkpointed class-specific Linear-Q runners."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--characters", nargs="*", default=None)
    parser.add_argument("--runs-per-character", type=int, default=50)
    parser.add_argument("--seed", type=int, default=110001)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--out-dir", type=Path, default=Path("runs") / "rl_linear_benchmarks")
    parser.add_argument("--stem", type=str, default="linear_q_benchmark")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(format_linear_checkpoint_selection(manifest))
    print("")

    json_path, csv_path, summary_path, rows = benchmark_linear_checkpoint_policy(
        manifest_path=args.manifest,
        character_ids=args.characters,
        runs_per_character=args.runs_per_character,
        seed=args.seed,
        max_steps=args.max_steps,
        output_dir=args.out_dir,
        stem=args.stem,
    )

    print(format_benchmark_summary(rows))
    print("")
    print("Saved Linear-Q benchmark:")
    print(f"  JSON:    {json_path}")
    print(f"  CSV:     {csv_path}")
    print(f"  Summary: {summary_path}")


if __name__ == "__main__":
    main()
