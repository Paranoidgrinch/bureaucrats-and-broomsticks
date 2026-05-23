"""Content catalog loading for the game.

The catalog is loaded from an act manifest. This keeps the game content-first:
new acts, cards, enemies, encounters, events, statuses, and relics should
usually be configured through JSON rather than console-flow code.
"""

from __future__ import annotations

from dataclasses import dataclass

from bab.content.data_loader import (
    load_act_manifest,
    load_card_database,
    load_character_class,
    load_encounter_database,
    load_enemy_database,
    load_event_database,
    load_relic_database,
    load_status_database,
)
from bab.game_config import DEFAULT_ACT_MANIFEST_FILE
from bab.models import (
    ActManifest,
    Card,
    CharacterClass,
    EncounterDefinition,
    EnemyDefinition,
    EventDefinition,
    RelicDefinition,
    StatusDefinition,
)


@dataclass(frozen=True)
class ContentCatalog:
    act_manifest: ActManifest
    character_classes: dict[str, CharacterClass]
    character_class: CharacterClass
    card_database: dict[str, Card]
    enemy_database: dict[str, EnemyDefinition]
    encounter_database: dict[str, EncounterDefinition]
    status_database: dict[str, StatusDefinition]
    event_database: dict[str, EventDefinition]
    relic_database: dict[str, RelicDefinition]


def load_content_catalog_from_act_manifest(relative_path: str) -> ContentCatalog:
    """Load a content catalog from a specific act manifest."""

    act_manifest = load_act_manifest(relative_path)

    character_classes = {
        character_class.id: character_class
        for character_class in (
            load_character_class(path)
            for path in act_manifest.character_class_files
        )
    }

    if act_manifest.default_character_class_id not in character_classes:
        raise ValueError(
            f"Default character class {act_manifest.default_character_class_id!r} "
            f"is not listed in {act_manifest.id}."
        )

    return ContentCatalog(
        act_manifest=act_manifest,
        character_classes=character_classes,
        character_class=character_classes[act_manifest.default_character_class_id],
        card_database=load_card_database(act_manifest.card_files),
        enemy_database=load_enemy_database(act_manifest.enemy_files),
        encounter_database=load_encounter_database(act_manifest.encounter_files),
        status_database=load_status_database(act_manifest.status_files),
        event_database=load_event_database(act_manifest.event_files),
        relic_database=load_relic_database(act_manifest.relic_files),
    )


def load_default_content_catalog() -> ContentCatalog:
    """Load the default content set used by the console prototype."""

    return load_content_catalog_from_act_manifest(DEFAULT_ACT_MANIFEST_FILE)
