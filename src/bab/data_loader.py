import json
from pathlib import Path
from typing import Any

from bab.models import (
    Card,
    CharacterClass,
    EncounterDefinition,
    EnemyDefinition,
    StatusDefinition,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path: str) -> Any:
    path = PROJECT_ROOT / relative_path

    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_cards(relative_path: str) -> list[Card]:
    raw_data = load_json(relative_path)

    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a list of cards in {relative_path}")

    return [Card.model_validate(card_data) for card_data in raw_data]


def load_card_database(relative_paths: list[str]) -> dict[str, Card]:
    card_database: dict[str, Card] = {}

    for relative_path in relative_paths:
        cards = load_cards(relative_path)

        for card in cards:
            if card.id in card_database:
                raise ValueError(f"Duplicate card id found: {card.id}")

            card_database[card.id] = card

    return card_database


def load_character_class(relative_path: str) -> CharacterClass:
    raw_data = load_json(relative_path)
    return CharacterClass.model_validate(raw_data)


def load_enemies(relative_path: str) -> list[EnemyDefinition]:
    raw_data = load_json(relative_path)

    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a list of enemies in {relative_path}")

    return [EnemyDefinition.model_validate(enemy_data) for enemy_data in raw_data]


def load_enemy_database(relative_paths: list[str]) -> dict[str, EnemyDefinition]:
    enemy_database: dict[str, EnemyDefinition] = {}

    for relative_path in relative_paths:
        enemies = load_enemies(relative_path)

        for enemy in enemies:
            if enemy.id in enemy_database:
                raise ValueError(f"Duplicate enemy id found: {enemy.id}")

            enemy_database[enemy.id] = enemy

    return enemy_database


def load_statuses(relative_path: str) -> list[StatusDefinition]:
    raw_data = load_json(relative_path)

    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a list of statuses in {relative_path}")

    return [StatusDefinition.model_validate(status_data) for status_data in raw_data]


def load_status_database(relative_paths: list[str]) -> dict[str, StatusDefinition]:
    status_database: dict[str, StatusDefinition] = {}

    for relative_path in relative_paths:
        statuses = load_statuses(relative_path)

        for status in statuses:
            if status.id in status_database:
                raise ValueError(f"Duplicate status id found: {status.id}")

            status_database[status.id] = status

    return status_database


def load_encounters(relative_path: str) -> list[EncounterDefinition]:
    raw_data = load_json(relative_path)

    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a list of encounters in {relative_path}")

    return [EncounterDefinition.model_validate(encounter_data) for encounter_data in raw_data]


def load_encounter_database(relative_paths: list[str]) -> dict[str, EncounterDefinition]:
    encounter_database: dict[str, EncounterDefinition] = {}

    for relative_path in relative_paths:
        encounters = load_encounters(relative_path)

        for encounter in encounters:
            if encounter.id in encounter_database:
                raise ValueError(f"Duplicate encounter id found: {encounter.id}")

            encounter_database[encounter.id] = encounter

    return encounter_database