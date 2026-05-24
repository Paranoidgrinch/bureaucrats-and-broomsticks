from __future__ import annotations

import argparse
import subprocess
import sys
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# --- subprocess worker helpers v1 ---
def _load_manifest_character_ids(manifest_path):
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if "characters" in payload:
        chars = payload["characters"]
        if isinstance(chars, dict):
            return list(chars.keys())
        if isinstance(chars, list):
            result = []
            for item in chars:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict) and "id" in item:
                    result.append(item["id"])
            if result:
                return result

    # Stable project fallback.
    return [
        "bureaucrat",
        "failed_wizard",
        "guild_assassin_apprentice",
        "hedge_witch",
        "mortuary_apprentice",
        "night_watch_recruit",
        "sewer_diplomat",
        "shroomancer",
        "witch_clerk",
    ]


def _read_csv_rows(path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv_rows(path, rows):
    path = Path(path)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_csv(path, rows):
    # Rebuild a simple summary compatible with the existing human output.
    groups = {}
    for row in rows:
        key = (row["policy"], row["character_id"])
        groups.setdefault(key, []).append(row)

    summary_rows = []
    for (policy, character_id), group in sorted(groups.items()):
        n = len(group)
        wins = sum(1 for r in group if str(r.get("outcome", "")).lower() == "win")
        def avg(name):
            vals = []
            for r in group:
                try:
                    vals.append(float(r.get(name, 0) or 0))
                except ValueError:
                    vals.append(0.0)
            return sum(vals) / len(vals) if vals else 0.0

        summary_rows.append({
            "policy": policy,
            "character_id": character_id,
            "runs": n,
            "wins": wins,
            "win_rate": wins / n if n else 0.0,
            "avg_reward": avg("total_reward"),
            "avg_nodes": avg("completed_nodes"),
            "avg_fights": avg("fights_won"),
            "avg_damage_dealt": avg("damage_dealt"),
            "avg_damage_taken": avg("damage_taken"),
        })

    _write_csv_rows(path, summary_rows)


def _run_parallel_character_subprocesses(args):
    characters = list(args.characters or _load_manifest_character_ids(args.manifest))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    worker_root = out_dir / "_character_workers"
    worker_root.mkdir(parents=True, exist_ok=True)

    max_workers = max(1, min(int(args.workers), len(characters)))
    script_path = Path(__file__).resolve()

    print(f"Running {len(characters)} character benchmarks with {max_workers} subprocess workers.")
    print("Characters:", ", ".join(characters))

    def run_one(index, character_id):
        char_dir = worker_root / character_id
        char_dir.mkdir(parents=True, exist_ok=True)
        char_stem = f"{args.stem}_{character_id}"

        cmd = [
            sys.executable,
            str(script_path),
            "--manifest", str(args.manifest),
            "--characters", character_id,
            "--runs-per-character", str(args.runs_per_character),
            "--seed", str(int(args.seed) + index * 1000003),
            "--max-steps", str(args.max_steps),
            "--out-dir", str(char_dir),
            "--stem", char_stem,
            "--workers", "1",
        ]

        completed = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                f"Worker for {character_id} failed with code {completed.returncode}\n"
                f"Command: {' '.join(cmd)}\n\n"
                f"{completed.stdout}"
            )

        print(f"\n--- {character_id} worker output ---")
        print(completed.stdout)

        return {
            "character_id": character_id,
            "json": char_dir / f"{char_stem}.json",
            "csv": char_dir / f"{char_stem}.csv",
            "summary": char_dir / f"{char_stem}_summary.csv",
        }

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_one, index, character_id): character_id
            for index, character_id in enumerate(characters)
        }
        for future in as_completed(futures):
            results.append(future.result())

    # Merge CSV rows. The analyzer consumes the JSON, but the current JSON format
    # in this project mirrors the row payload, so we rebuild it from the CSV rows.
    rows = []
    for result in sorted(results, key=lambda r: characters.index(r["character_id"])):
        rows.extend(_read_csv_rows(result["csv"]))

    json_path = out_dir / f"{args.stem}.json"
    csv_path = out_dir / f"{args.stem}.csv"
    summary_path = out_dir / f"{args.stem}_summary.csv"

    # Preserve numeric-looking values where possible.
    typed_rows = []
    for row in rows:
        typed = {}
        for key, value in row.items():
            if key in {"seed", "steps", "completed_nodes", "fights_won", "gold", "deck_size", "relic_count"}:
                try:
                    typed[key] = int(float(value))
                except ValueError:
                    typed[key] = value
            elif key in {"total_reward", "damage_dealt", "damage_taken"}:
                try:
                    typed[key] = float(value)
                except ValueError:
                    typed[key] = value
            else:
                typed[key] = value
        typed_rows.append(typed)

    payload = {
        "rows": typed_rows,
        "metadata": {
            "manifest": str(args.manifest),
            "runs_per_character": args.runs_per_character,
            "seed": args.seed,
            "max_steps": args.max_steps,
            "workers": args.workers,
            "characters": characters,
            "parallel_mode": "subprocess_per_character",
        },
    }

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv_rows(csv_path, typed_rows)
    _write_summary_csv(summary_path, typed_rows)

    print("\n=== Parallel benchmark merged ===")
    print(f"Saved Linear-Q benchmark:")
    print(f"  JSON:    {json_path}")
    print(f"  CSV:     {csv_path}")
    print(f"  Summary: {summary_path}")

    return True



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
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes for character-level benchmark parallelism.",
    )
    args = parser.parse_args()

    # PARALLEL_ALL_CHARACTER_BRANCH_V2
    if getattr(args, "workers", 1) > 1 and not getattr(args, "characters", None):
        _run_parallel_character_subprocesses(args)
        return

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
