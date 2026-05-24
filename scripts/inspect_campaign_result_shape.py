from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path

from bab.content.catalog import ContentCatalog, load_content_catalog_from_act_manifest
from bab.sim.auto_runner import SimConfig, simulate_runs


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
    return replace(
        catalog,
        character_classes={character_id: catalog.character_classes[character_id]},
        character_class=catalog.character_classes[character_id],
    )


def result_to_dict(result: object) -> dict:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {"repr": repr(result)}


def main() -> None:
    print("Inspecting campaign simulation result shape...")
    print()

    base_catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")

    config = SimConfig(
        runs=40,
        seed=777001,
        max_combat_turns=90,
        reward_skip_chance=0.12,
        card_play_stop_chance=0.06,
        shop_leave_chance=0.18,
    )

    first_result_seen = False

    for offset, character_id in enumerate(CHARACTER_IDS):
        catalog = single_character_catalog(base_catalog, character_id)
        summary = simulate_runs(
            replace(config, seed=config.seed + offset * 10000),
            catalog=catalog,
            raise_errors=True,
        )

        result_dicts = [result_to_dict(result) for result in summary.results]
        keys = sorted({key for result in result_dicts for key in result})

        print(f"## {character_id}")
        print(
            f"runs={summary.total_runs}, wins={summary.wins}, "
            f"defeats={summary.defeats}, errors={summary.errors}, "
            f"stalled={summary.stalled}, avg_nodes={summary.average_completed_nodes:.2f}"
        )

        if not first_result_seen and summary.results:
            first = summary.results[0]
            print()
            print("SimulatedRun dataclass fields:")
            if is_dataclass(first):
                print([field.name for field in fields(first)])
            else:
                print("not a dataclass")

            print()
            print("Result dict keys:")
            print(keys)
            first_result_seen = True

        deep_runs = [
            result
            for result in result_dicts
            if isinstance(result.get("completed_nodes"), int)
            and result["completed_nodes"] > 9
        ]

        print(f"runs with completed_nodes > 9: {len(deep_runs)}")

        if deep_runs:
            sample = deep_runs[0]
            print("sample deep run:")
            for key in [
                "outcome",
                "completed_nodes",
                "fights_won",
                "last_node_type",
                "last_node_id",
                "last_encounter_id",
                "deck_size",
                "relic_count",
                "gold",
            ]:
                if key in sample:
                    print(f"  {key}: {sample[key]}")

            path_history = sample.get("path_history")
            if isinstance(path_history, list):
                print(f"  path_history length: {len(path_history)}")
                print("  last path entries:")
                for entry in path_history[-5:]:
                    print(f"    {entry}")
            else:
                print("  no path_history list")

        print()

    print("Inspection complete.")


if __name__ == "__main__":
    main()
