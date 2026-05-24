from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.content.catalog import load_default_content_catalog  # noqa: E402
from bab.sim.agents import HeuristicPolicy, RandomPolicy  # noqa: E402
from bab.sim.benchmark import (  # noqa: E402
    benchmark_policies_across_characters,
    format_benchmark_summary,
    write_benchmark_bundle,
)
from bab.sim.good_player import (  # noqa: E402
    GoodPlayerPolicy,
    format_good_player_selection,
    load_class_runners_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the selected per-class GoodPlayerPolicy."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to class_runners_manifest.json.",
    )
    parser.add_argument("--runs-per-character", type=int, default=50)
    parser.add_argument("--seed", type=int, default=40001)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument(
        "--characters",
        nargs="*",
        default=None,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_good_player",
    )
    parser.add_argument("--stem", type=str, default="good_player_benchmark")
    parser.add_argument(
        "--prefer-q-on-equal-wins",
        action="store_true",
    )
    args = parser.parse_args()

    if args.characters:
        character_ids = args.characters
    else:
        catalog = load_default_content_catalog()
        character_ids = sorted(catalog.character_classes)

    manifest = load_class_runners_manifest(args.manifest)
    print(format_good_player_selection(
        manifest,
        prefer_q_on_equal_wins=args.prefer_q_on_equal_wins,
    ))
    print("")

    manifest_path = args.manifest

    rows = benchmark_policies_across_characters(
        {
            "random": lambda seed: RandomPolicy(seed=seed),
            "heuristic": lambda seed: HeuristicPolicy(seed=seed),
            "good_player": lambda seed: GoodPlayerPolicy(
                manifest_path=manifest_path,
                seed=seed,
                prefer_q_on_equal_wins=args.prefer_q_on_equal_wins,
            ),
        },
        character_ids=character_ids,
        runs_per_character=args.runs_per_character,
        seed=args.seed,
        max_steps=args.max_steps,
    )

    json_path, csv_path, summary_path = write_benchmark_bundle(
        rows,
        args.out_dir,
        stem=args.stem,
    )

    print(format_benchmark_summary(rows))
    print("")
    print("Saved good-player benchmark:")
    print(f"  JSON:    {json_path}")
    print(f"  CSV:     {csv_path}")
    print(f"  Summary: {summary_path}")


if __name__ == "__main__":
    main()
