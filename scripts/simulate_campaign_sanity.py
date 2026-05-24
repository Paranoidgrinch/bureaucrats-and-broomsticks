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


def result_to_dict(result: object) -> dict:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"repr": repr(result)}


def safe_get_number(data: dict, *keys: str) -> float | int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return value
    return None


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
        "- Expected flow: Act 1 boss → Epic reward → full heal → Act 2",
        f"- Runs per character: `{args.runs}`",
        f"- Seed base: `{args.seed}`",
        "",
    ]

    result_key_rows: list[dict[str, object]] = []

    for offset, character_id in enumerate(CHARACTER_IDS):
        catalog = single_character_catalog(base_catalog, character_id)
        character_config = replace(config, seed=args.seed + offset * 10000)

        summary = simulate_runs(
            character_config,
            catalog=catalog,
            raise_errors=args.raise_errors,
        )

        summary_data = summary.to_dict()
        result_dicts = [result_to_dict(result) for result in summary.results]

        write_json(outdir / f"{character_id}.json", summary_data)
        write_json(outdir / f"{character_id}_results.json", result_dicts)

        summary_text = format_summary(summary)
        (outdir / f"{character_id}.md").write_text(summary_text + "\n", encoding="utf-8")

        key_union = sorted({key for result in result_dicts for key in result})
        result_key_rows.append({"character_id": character_id, "result_keys": key_union})

        # These keys are intentionally defensive because result payloads evolved during development.
        final_acts = [
            safe_get_number(result, "act", "final_act", "current_act")
            for result in result_dicts
        ]
        reached_act_2 = sum(1 for act in final_acts if act is not None and act >= 2)

        epic_cards_seen = 0
        for result in result_dicts:
            deck_ids = result.get("deck_ids") or result.get("run_deck_ids") or result.get("final_deck_ids")
            deck_rarities = result.get("deck_rarities") or result.get("final_deck_rarities")
            if isinstance(deck_ids, list) and any(str(card_id).startswith("epic_") for card_id in deck_ids):
                epic_cards_seen += 1
            elif isinstance(deck_rarities, list) and "epic" in deck_rarities:
                epic_cards_seen += 1

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
            "reached_act_2_if_reported": reached_act_2,
            "epic_cards_seen_if_reported": epic_cards_seen,
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
                f"- reached_act_2_if_reported: `{reached_act_2}`",
                f"- epic_cards_seen_if_reported: `{epic_cards_seen}`",
                "",
            ]
        )

    write_json(outdir / "overview.json", overview_rows)
    write_json(outdir / "result_keys.json", result_key_rows)
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
            f"reached_act_2_if_reported={row['reached_act_2_if_reported']}"
        )

    print()
    print(f"Result keys written to {outdir / 'result_keys.json'}")


if __name__ == "__main__":
    main()
