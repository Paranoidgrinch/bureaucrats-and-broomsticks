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
from bab.sim.heuristic_v2 import HeuristicV2Policy  # noqa: E402
from bab.sim.benchmark import (  # noqa: E402
    benchmark_policies_across_characters,
    format_benchmark_summary,
    write_benchmark_bundle,
)
from bab.sim.q_learning import QLearningPolicy  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Random, Heuristic, and trained Q-learning agents across characters."
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Optional path to a saved q_learning_agent.json model.",
    )
    parser.add_argument("--runs-per-character", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20001)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument(
        "--characters",
        nargs="*",
        default=None,
        help="Character ids to benchmark. Defaults to all loaded character classes.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_benchmarks",
    )
    parser.add_argument("--stem", type=str, default="agent_benchmark")
    parser.add_argument(
        "--no-random",
        action="store_true",
        help="Do not include RandomPolicy.",
    )
    parser.add_argument(
        "--no-heuristic",
        action="store_true",
        help="Do not include HeuristicPolicy.",
    )
    parser.add_argument(
        "--heuristic-v2",
        action="store_true",
        help="Include the stronger effect-aware HeuristicV2Policy.",
    )
    args = parser.parse_args()

    if args.characters:
        character_ids = args.characters
    else:
        catalog = load_default_content_catalog()
        character_ids = sorted(catalog.character_classes)

    policy_factories = {}

    if not args.no_random:
        policy_factories["random"] = lambda seed: RandomPolicy(seed=seed)

    if not args.no_heuristic:
        policy_factories["heuristic"] = lambda seed: HeuristicPolicy(seed=seed)

    if args.heuristic_v2:
        policy_factories["heuristic_v2"] = lambda seed: HeuristicV2Policy(seed=seed)

    if args.model is not None:
        model_path = args.model
        policy_factories["q_learning"] = lambda seed: QLearningPolicy.load(
            model_path,
            seed=seed,
        )

    if not policy_factories:
        raise SystemExit("No policies selected for benchmarking.")

    rows = benchmark_policies_across_characters(
        policy_factories,
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
    print("Saved benchmark:")
    print(f"  JSON:    {json_path}")
    print(f"  CSV:     {csv_path}")
    print(f"  Summary: {summary_path}")


if __name__ == "__main__":
    main()
