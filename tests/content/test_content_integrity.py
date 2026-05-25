import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.content.data_loader import load_act_manifest, load_json
from bab.game_config import ACT_MANIFEST_FILES
from bab.models import Effect


SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _assert_snake_case(value: str, context: str) -> None:
    assert SNAKE_CASE_RE.fullmatch(value), f"{context} is not snake_case: {value!r}"


def _raw_content_objects(relative_path: str) -> list[dict[str, Any]]:
    raw_data = load_json(relative_path)

    if isinstance(raw_data, list):
        return [item for item in raw_data if isinstance(item, dict)]

    if isinstance(raw_data, dict):
        if "id" in raw_data:
            return [raw_data]

        for key in (
            "cards",
            "enemies",
            "encounters",
            "statuses",
            "events",
            "relics",
            "classes",
        ):
            value = raw_data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _effect_status_references(effects: Iterable[Effect]) -> set[str]:
    status_ids: set[str] = set()

    for effect in effects:
        if effect.status:
            status_ids.add(effect.status)

        if effect.condition and effect.condition.status:
            status_ids.add(effect.condition.status)

    return status_ids


def _assert_no_duplicate_raw_ids(paths: Iterable[str], context: str) -> None:
    ids: list[str] = []

    for path in paths:
        ids.extend(
            item["id"]
            for item in _raw_content_objects(path)
            if isinstance(item.get("id"), str)
        )

    duplicates = sorted(
        content_id
        for content_id, count in Counter(ids).items()
        if count > 1
    )

    assert not duplicates, f"Duplicate ids in {context}: {duplicates}"


def test_all_manifest_file_references_exist_and_load() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        manifest = load_act_manifest(manifest_path)

        referenced_files = [
            *manifest.character_class_files,
            *manifest.card_files,
            *manifest.enemy_files,
            *manifest.encounter_files,
            *manifest.status_files,
            *manifest.event_files,
            *manifest.relic_files,
        ]

        for relative_path in referenced_files:
            assert load_json(relative_path), f"{manifest.id} references an empty or missing file: {relative_path}"


def test_no_duplicate_raw_ids_inside_manifest_content_groups() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        manifest = load_act_manifest(manifest_path)

        _assert_no_duplicate_raw_ids(manifest.card_files, f"{manifest.id} card files")
        _assert_no_duplicate_raw_ids(manifest.enemy_files, f"{manifest.id} enemy files")
        _assert_no_duplicate_raw_ids(manifest.encounter_files, f"{manifest.id} encounter files")
        _assert_no_duplicate_raw_ids(manifest.status_files, f"{manifest.id} status files")
        _assert_no_duplicate_raw_ids(manifest.event_files, f"{manifest.id} event files")
        _assert_no_duplicate_raw_ids(manifest.relic_files, f"{manifest.id} relic files")


def test_all_content_ids_are_snake_case() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        _assert_snake_case(catalog.act_manifest.id, f"{catalog.act_manifest.id} manifest id")

        for content_id in catalog.card_database:
            _assert_snake_case(content_id, f"{catalog.act_manifest.id} card id")

        for content_id in catalog.enemy_database:
            _assert_snake_case(content_id, f"{catalog.act_manifest.id} enemy id")

        for enemy in catalog.enemy_database.values():
            for intent in enemy.intents:
                _assert_snake_case(intent.id, f"{enemy.id} intent id")

        for content_id in catalog.encounter_database:
            _assert_snake_case(content_id, f"{catalog.act_manifest.id} encounter id")

        for content_id in catalog.status_database:
            _assert_snake_case(content_id, f"{catalog.act_manifest.id} status id")

        for content_id in catalog.event_database:
            _assert_snake_case(content_id, f"{catalog.act_manifest.id} event id")

        for event in catalog.event_database.values():
            for choice in event.choices:
                _assert_snake_case(choice.id, f"{event.id} choice id")

        for content_id in catalog.relic_database:
            _assert_snake_case(content_id, f"{catalog.act_manifest.id} relic id")


def test_card_upgrade_targets_exist_and_are_marked_upgraded() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        for card in catalog.card_database.values():
            if card.upgrades_to is None:
                continue

            assert card.upgrades_to in catalog.card_database, (
                f"{card.id} upgrades to missing card {card.upgrades_to!r}"
            )

            upgraded_card = catalog.card_database[card.upgrades_to]
            assert "upgraded" in upgraded_card.tags, (
                f"{card.id} upgrades to {upgraded_card.id}, but target is not tagged 'upgraded'"
            )


def test_card_effect_status_references_exist() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        known_status_ids = set(catalog.status_database)

        for card in catalog.card_database.values():
            missing = _effect_status_references(card.effects) - known_status_ids
            assert not missing, f"{card.id} references missing statuses: {sorted(missing)}"


def test_enemy_intent_status_references_exist() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        known_status_ids = set(catalog.status_database)

        for enemy in catalog.enemy_database.values():
            for intent in enemy.intents:
                missing = _effect_status_references(intent.effects) - known_status_ids
                assert not missing, (
                    f"{enemy.id}/{intent.id} references missing statuses: {sorted(missing)}"
                )


def test_encounters_reference_existing_enemies() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        known_enemy_ids = set(catalog.enemy_database)

        for encounter in catalog.encounter_database.values():
            missing = sorted(set(encounter.enemies) - known_enemy_ids)
            assert not missing, f"{encounter.id} references missing enemies: {missing}"


def test_treasure_mimic_encounter_exists_in_each_act_catalog() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        mimic_encounter_id = catalog.act_manifest.treasure.mimic_encounter_id
        mimic_chance = catalog.act_manifest.treasure.mimic_chance

        if mimic_chance <= 0:
            assert mimic_encounter_id is None
            continue

        assert mimic_encounter_id is not None
        assert mimic_encounter_id in catalog.encounter_database, (
            f"{catalog.act_manifest.id} treasure mimic encounter does not exist: "
            f"{mimic_encounter_id!r}"
        )

def test_event_effect_card_references_exist() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        known_card_ids = set(catalog.card_database)

        for event in catalog.event_database.values():
            for choice in event.choices:
                for effect in choice.effects:
                    if effect.card_id is not None:
                        assert effect.card_id in known_card_ids, (
                            f"{event.id}/{choice.id} references missing card {effect.card_id!r}"
                        )


def test_relic_status_references_exist() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        known_status_ids = set(catalog.status_database)

        for relic in catalog.relic_database.values():
            missing = {
                effect.status
                for effect in relic.effects
                if effect.status is not None and effect.status not in known_status_ids
            }

            assert not missing, f"{relic.id} references missing statuses: {sorted(missing)}"


def test_default_character_class_is_available_in_each_act() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        assert catalog.act_manifest.default_character_class_id in catalog.character_classes
        assert catalog.character_class is catalog.character_classes[
            catalog.act_manifest.default_character_class_id
        ]


def test_character_starting_decks_reference_existing_cards() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        for character_class in catalog.character_classes.values():
            missing = sorted(set(character_class.starting_deck) - set(catalog.card_database))
            assert not missing, (
                f"{catalog.act_manifest.id}/{character_class.id} "
                f"starting deck references missing cards: {missing}"
            )

