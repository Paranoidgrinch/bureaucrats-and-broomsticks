"""Content catalog loading for the game.

This module is the central bridge between JSON content files and the runtime
engine. Most new cards, enemies, encounters, events, statuses, and relics
should be added through data files rather than through console or flow code.
"""

from __future__ import annotations

from dataclasses import dataclass

from bab.content.data_loader import (
    load_card_database,
    load_character_class,
    load_encounter_database,
    load_enemy_database,
    load_event_database,
    load_relic_database,
    load_status_database,
)
from bab.game_config import (
    CARD_DATA_FILES,
    CHARACTER_CLASS_DATA_FILE,
    ENCOUNTER_DATA_FILES,
    ENEMY_DATA_FILES,
    EVENT_DATA_FILES,
    RELIC_DATA_FILES,
    STATUS_DATA_FILES,
)
from bab.models import (
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
    character_class: CharacterClass
    card_database: dict[str, Card]
    enemy_database: dict[str, EnemyDefinition]
    encounter_database: dict[str, EncounterDefinition]
    status_database: dict[str, StatusDefinition]
    event_database: dict[str, EventDefinition]
    relic_database: dict[str, RelicDefinition]


def load_default_content_catalog() -> ContentCatalog:
    """Load the default content set used by the console prototype."""

    return ContentCatalog(
        character_class=load_character_class(CHARACTER_CLASS_DATA_FILE),
        card_database=load_card_database(CARD_DATA_FILES),
        enemy_database=load_enemy_database(ENEMY_DATA_FILES),
        encounter_database=load_encounter_database(ENCOUNTER_DATA_FILES),
        status_database=load_status_database(STATUS_DATA_FILES),
        event_database=load_event_database(EVENT_DATA_FILES),
        relic_database=load_relic_database(RELIC_DATA_FILES),
    )
