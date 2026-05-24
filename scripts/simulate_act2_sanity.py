from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run direct Act-2 sanity simulations per character."
    )
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=220200)
    parser.add_argument("--outdir", default="runs/act2_sanity")
    parser.add_argument("--raise-errors", action="store_true")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base_catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    config = SimConfig(
        runs=args.runs,
        seed=args.seed,
        max_combat_turns=80,
        reward_skip_chance=0.15,
        card_play_stop_chance=0.08,
        shop_leave_chance=0.20,
    )

    overview_rows: list[dict[str, object]] = []
    combined_markdown: list[str] = [
        "# Act 2 Direct Sanity Simulation",
        "",
        f"- Runs per character: `{args.runs}`",
        f"- Seed base: `{args.seed}`",
        f"- Act manifest: `data/acts/act_2_archives.json`",
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

        summary_data = summary.to_dict()
        write_json(outdir / f"{character_id}.json", summary_data)

        summary_text = format_summary(summary)
        (outdir / f"{character_id}.md").write_text(summary_text + "\n", encoding="utf-8")

        overview_rows.append(
            {
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
            }
        )

        combined_markdown.extend(
            [
                f"## {character_id}",
                "",
                "```text",
                summary_text,
                "```",
                "",
            ]
        )

    write_json(outdir / "overview.json", overview_rows)
    (outdir / "summary.md").write_text(
        "\n".join(combined_markdown) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote Act-2 sanity simulation results to {outdir}")
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
            f"avg_nodes={row['average_completed_nodes']:.2f}"
        )


if __name__ == "__main__":
    main()
