from pathlib import Path

from bab.content.catalog import load_content_catalog_from_act_manifest


LATE_ACT_TARGETS = {
    "data/acts/act_4_licensing_labyrinth.json": {
        "enemy": "data/enemies/act_4_licensing_labyrinth_enemies.json",
        "cards": "data/cards/act_4_licensing_labyrinth_rewards.json",
        "relics": "data/relics/act_4_licensing_labyrinth_relics.json",
        "class_relics": "data/relics/act_4_licensing_labyrinth_class_relics.json",
    },
    "data/acts/act_5_ministry_spire.json": {
        "enemy": "data/enemies/act_5_ministry_spire_enemies.json",
        "cards": "data/cards/act_5_ministry_spire_rewards.json",
        "relics": "data/relics/act_5_ministry_spire_relics.json",
        "class_relics": "data/relics/act_5_ministry_spire_class_relics.json",
    },
}


def test_late_acts_have_dedicated_future_content_target_files() -> None:
    for targets in LATE_ACT_TARGETS.values():
        for target_path in targets.values():
            assert Path(target_path).exists()


def test_empty_late_act_target_files_are_not_referenced_by_manifests_yet() -> None:
    for manifest_path, targets in LATE_ACT_TARGETS.items():
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        manifest = catalog.act_manifest

        active_references = {
            *manifest.enemy_files,
            *manifest.card_files,
            *manifest.relic_files,
        }

        for target_path in targets.values():
            assert Path(target_path).read_text(encoding="utf-8").strip() == "[]"
            assert target_path not in active_references
