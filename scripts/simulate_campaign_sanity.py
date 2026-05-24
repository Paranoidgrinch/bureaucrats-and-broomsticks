from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from statistics import mean

from bab.content.catalog import ContentCatalog, load_content_catalog_from_act_manifest
from bab.sim.auto_runner import SimConfig, format_summary, simulate_runs


CHARACTER_IDS = [
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


def single_character_catalog(
    catalog: ContentCatalog,
    character_id: str,
) -> ContentCatalog:
    if character_id not in catalog.character_classes:
        raise ValueError(f"Unknown character class: {character_id}")

    return replace(
        catalog,
        character_classes={character_id: catalog.character_classes[character_id]},
        character_class=catalog.character_classes[character_id],
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def result_to_dict(result: object) -> dict:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"repr": repr(result)}


def path_history(result: dict) -> list[dict]:
    history = result.get("path_history")
    if isinstance(history, list):
        return [entry for entry in history if isinstance(entry, dict)]
    return []


def is_act_2_entry(entry: dict) -> bool:
    return str(entry.get("node_id", "")).startswith("act_2")


def act_2_entries(result: dict) -> list[dict]:
    return [entry for entry in path_history(result) if is_act_2_entry(entry)]


def reaches_act_2(result: dict) -> bool:
    return bool(act_2_entries(result))


def numeric_values(entries: list[dict], key: str) -> list[float]:
    values: list[float] = []
    for entry in entries:
        value = entry.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def top_counter(counter: Counter, limit: int = 10) -> list[dict[str, object]]:
    return [
        {"key": key, "count": count}
        for key, count in counter.most_common(limit)
    ]


def analyse_results(result_dicts: list[dict]) -> dict[str, object]:
    reached_results = [result for result in result_dicts if reaches_act_2(result)]
    act_2_deaths = [
        result
        for result in result_dicts
        if result.get("outcome") == "defeat" and reaches_act_2(result)
    ]
    pre_act_2_deaths = [
        result
        for result in result_dicts
        if result.get("outcome") == "defeat" and not reaches_act_2(result)
    ]
    act_2_wins = [
        result
        for result in result_dicts
        if result.get("outcome") == "win"
        and str(result.get("last_node_id", "")).startswith("act_2")
    ]

    first_act_2_entries = [
        act_2_entries(result)[0]
        for result in reached_results
        if act_2_entries(result)
    ]

    act_2_entry_hps = numeric_values(first_act_2_entries, "hp_before")
    act_2_entry_deck_sizes = numeric_values(first_act_2_entries, "deck_size_before")
    act_2_entry_relic_counts = numeric_values(first_act_2_entries, "relic_count_before")

    max_act_2_depths: list[float] = []
    for result in reached_results:
        depths = numeric_values(act_2_entries(result), "depth")
        if depths:
            max_act_2_depths.append(max(depths))

    death_encounters = Counter(
        str(result.get("last_encounter_id") or "<none>")
        for result in act_2_deaths
    )
    death_nodes = Counter(
        str(result.get("last_node_type") or "<none>")
        for result in act_2_deaths
    )

    first_act_2_nodes = Counter(
        str(entry.get("node_type") or "<none>")
        for entry in first_act_2_entries
    )

    total = len(result_dicts)

    return {
        "runs": total,
        "reached_act_2": len(reached_results),
        "reached_act_2_rate": len(reached_results) / total if total else 0.0,
        "pre_act_2_deaths": len(pre_act_2_deaths),
        "act_2_deaths": len(act_2_deaths),
        "act_2_wins": len(act_2_wins),
        "act_2_entry_avg_hp": mean(act_2_entry_hps) if act_2_entry_hps else None,
        "act_2_entry_min_hp": min(act_2_entry_hps) if act_2_entry_hps else None,
        "act_2_entry_max_hp": max(act_2_entry_hps) if act_2_entry_hps else None,
        "act_2_entry_avg_deck_size": mean(act_2_entry_deck_sizes) if act_2_entry_deck_sizes else None,
        "act_2_entry_avg_relic_count": mean(act_2_entry_relic_counts) if act_2_entry_relic_counts else None,
        "avg_max_act_2_depth": mean(max_act_2_depths) if max_act_2_depths else None,
        "max_act_2_depth_seen": max(max_act_2_depths) if max_act_2_depths else None,
        "first_act_2_node_types": top_counter(first_act_2_nodes),
        "top_act_2_death_encounters": top_counter(death_encounters),
        "top_act_2_death_node_types": top_counter(death_nodes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Act-1-to-Act-2 campaign sanity simulations per character."
    )
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=120200)
    parser.add_argument("--outdir", default="runs/campaign_sanity")
    parser.add_argument("--raise-errors", action="store_true")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base_catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")

    config = SimConfig(
        runs=args.runs,
        seed=args.seed,
        max_combat_turns=90,
        reward_skip_chance=0.12,
        card_play_stop_chance=0.06,
        shop_leave_chance=0.18,
    )

    overview_rows: list[dict[str, object]] = []
    combined_markdown: list[str] = [
        "# Campaign Sanity Simulation",
        "",
        "- Start act: `data/acts/act_1_city.json`",
        "- Act-2 reach is inferred from `path_history` node IDs starting with `act_2`.",
        f"- Runs per character: `{args.runs}`",
        f"- Seed base: `{args.seed}`",
        "",
    ]

    for offset, character_id in enumerate(CHARACTER_IDS):
        catalog = single_character_catalog(base_catalog, character_id)
        character_config = replace(config, seed=args.seed + offset * 10000)

        summary = simulate_runs(
            character_config,
            catalog=catalog,
            raise_errors=args.raise_errors,
        )

        result_dicts = [result_to_dict(result) for result in summary.results]
        diagnostics = analyse_results(result_dicts)

        summary_data = summary.to_dict()
        summary_data["campaign_diagnostics"] = diagnostics

        write_json(outdir / f"{character_id}.json", summary_data)
        write_json(outdir / f"{character_id}_results.json", result_dicts)

        summary_text = format_summary(summary)
        (outdir / f"{character_id}.md").write_text(summary_text + "\n", encoding="utf-8")

        overview_row = {
            "character_id": character_id,
            "runs": summary.total_runs,
            "wins": summary.wins,
            "defeats": summary.defeats,
            "errors": summary.errors,
            "stalled": summary.stalled,
            "win_rate": summary.win_rate,
            "defeat_rate": summary.defeat_rate,
            "error_rate": summary.error_rate,
            "average_completed_nodes": summary.average_completed_nodes,
            "average_fights_won": summary.average_fights_won,
            "average_gold": summary.average_gold,
            **diagnostics,
        }
        overview_rows.append(overview_row)

        combined_markdown.extend(
            [
                f"## {character_id}",
                "",
                "```text",
                summary_text,
                "```",
                "",
                f"- reached_act_2: `{diagnostics['reached_act_2']}` / `{args.runs}`",
                f"- reached_act_2_rate: `{diagnostics['reached_act_2_rate']:.3f}`",
                f"- pre_act_2_deaths: `{diagnostics['pre_act_2_deaths']}`",
                f"- act_2_deaths: `{diagnostics['act_2_deaths']}`",
                f"- act_2_wins: `{diagnostics['act_2_wins']}`",
                f"- act_2_entry_avg_hp: `{diagnostics['act_2_entry_avg_hp']}`",
                f"- avg_max_act_2_depth: `{diagnostics['avg_max_act_2_depth']}`",
                "",
                "Top Act-2 death encounters:",
                "```json",
                json.dumps(diagnostics["top_act_2_death_encounters"], indent=2),
                "```",
                "",
            ]
        )

    write_json(outdir / "overview.json", overview_rows)
    (outdir / "summary.md").write_text(
        "\n".join(combined_markdown) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote campaign sanity simulation results to {outdir}")
    print()
    print("Overview:")
    for row in overview_rows:
        print(
            f"{row['character_id']}: "
            f"runs={row['runs']}, "
            f"wins={row['wins']}, "
            f"defeats={row['defeats']}, "
            f"errors={row['errors']}, "
            f"stalled={row['stalled']}, "
            f"avg_nodes={row['average_completed_nodes']:.2f}, "
            f"reached_act_2={row['reached_act_2']}, "
            f"act_2_deaths={row['act_2_deaths']}, "
            f"act_2_wins={row['act_2_wins']}"
        )


if __name__ == "__main__":
    main()
