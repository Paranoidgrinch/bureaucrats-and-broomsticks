from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.cwd()

ACT1_MANIFEST = ROOT / "data/acts/act_1_city.json"
ACT2_MANIFEST = ROOT / "data/acts/act_2_archives.json"

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


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def manifest_relic_paths(manifest_path: Path) -> list[Path]:
    manifest = load_json(manifest_path)
    paths = []
    for rel_path in manifest.get("relic_files", []):
        paths.append(ROOT / rel_path)
    return paths


def load_relics_from_paths(paths: list[Path]) -> list[tuple[Path, dict]]:
    relics: list[tuple[Path, dict]] = []
    for path in paths:
        if not path.exists():
            print(f"WARNING missing relic file: {path}")
            continue
        for relic in load_json(path):
            relics.append((path, relic))
    return relics


def rarity_counts(relics: list[dict]) -> dict[str, int]:
    return dict(Counter(relic.get("rarity", "<missing>") for relic in relics))


def is_class_specific(relic: dict) -> bool:
    return bool(relic.get("allowed_classes"))


def class_targets(relics: list[dict]) -> dict[str, list[dict]]:
    by_class: dict[str, list[dict]] = defaultdict(list)
    for relic in relics:
        allowed_classes = relic.get("allowed_classes") or []
        for character_id in allowed_classes:
            by_class[character_id].append(relic)
    return by_class


def general_relics(relics: list[dict]) -> list[dict]:
    return [relic for relic in relics if not is_class_specific(relic)]


def class_specific_relics(relics: list[dict]) -> list[dict]:
    return [relic for relic in relics if is_class_specific(relic)]


def print_file_breakdown(label: str, relic_items: list[tuple[Path, dict]]) -> None:
    print(f"## {label} relic files")
    by_file: dict[Path, list[dict]] = defaultdict(list)

    for path, relic in relic_items:
        by_file[path].append(relic)

    for path in sorted(by_file):
        relics = by_file[path]
        class_specific = class_specific_relics(relics)
        general = general_relics(relics)

        print(f"{path.relative_to(ROOT)}")
        print(f"  total={len(relics)} general={len(general)} class_specific={len(class_specific)}")
        print(f"  rarities={rarity_counts(relics)}")

        classes = Counter()
        for relic in class_specific:
            for character_id in relic.get("allowed_classes", []):
                classes[character_id] += 1

        if classes:
            print(f"  allowed_classes={dict(sorted(classes.items()))}")
        print()


def print_summary(label: str, relics: list[dict]) -> None:
    general = general_relics(relics)
    class_specific = class_specific_relics(relics)
    by_class = class_targets(class_specific)

    print(f"## {label} summary")
    print(f"total={len(relics)}")
    print(f"general={len(general)} rarities={rarity_counts(general)}")
    print(f"class_specific={len(class_specific)} rarities={rarity_counts(class_specific)}")

    print("class_specific_by_class:")
    for character_id in CHARACTER_IDS:
        class_relics = by_class.get(character_id, [])
        print(
            f"  {character_id}: "
            f"{len(class_relics)} rarities={rarity_counts(class_relics)}"
        )
    print()


def main() -> None:
    act1_paths = manifest_relic_paths(ACT1_MANIFEST)
    act2_paths = manifest_relic_paths(ACT2_MANIFEST)

    act1_items = load_relics_from_paths(act1_paths)
    act2_items = load_relics_from_paths(act2_paths)

    act1_relics = [relic for _, relic in act1_items]
    act2_relics = [relic for _, relic in act2_items]

    act1_general = general_relics(act1_relics)
    act2_general_act_specific = [
        relic
        for relic in general_relics(act2_relics)
        if "act_2" in relic.get("tags", [])
    ]

    act1_class_specific_by_class = class_targets(class_specific_relics(act1_relics))
    act2_class_specific_by_class = class_targets(
        [
            relic
            for relic in class_specific_relics(act2_relics)
            if "act_2" in relic.get("tags", [])
        ]
    )

    print("# Relic Target Audit")
    print()

    print_file_breakdown("Act 1 manifest", act1_items)
    print_file_breakdown("Act 2 manifest", act2_items)

    print_summary("Act 1 manifest", act1_relics)
    print_summary("Act 2 manifest", act2_relics)

    print("## Proposed Act-2 relic targets")
    print(
        "General Act-2 relic target is based on Act-1 general relic count, "
        "not total Act-1 relic count."
    )
    print(
        f"general_act1={len(act1_general)} "
        f"general_act2_current={len(act2_general_act_specific)} "
        f"missing={max(0, len(act1_general) - len(act2_general_act_specific))}"
    )
    print(f"general_act1_rarities={rarity_counts(act1_general)}")
    print(f"general_act2_current_rarities={rarity_counts(act2_general_act_specific)}")
    print()

    print("Class-specific Act-2 relic targets by class:")
    for character_id in CHARACTER_IDS:
        target = len(act1_class_specific_by_class.get(character_id, []))
        current = len(act2_class_specific_by_class.get(character_id, []))
        print(
            f"{character_id}: "
            f"target={target} current={current} missing={max(0, target - current)} "
            f"target_rarities={rarity_counts(act1_class_specific_by_class.get(character_id, []))} "
            f"current_rarities={rarity_counts(act2_class_specific_by_class.get(character_id, []))}"
        )


if __name__ == "__main__":
    main()
