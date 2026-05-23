"""Central configuration for the console prototype.

The game should remain content-first: adding cards, enemies, encounters,
events, statuses, and relics should usually mean editing JSON files rather
than changing gameplay orchestration code.
"""

from __future__ import annotations


CARD_DATA_FILES: tuple[str, ...] = (
    "data/cards/bureaucrat_starter.json",
    "data/cards/bureaucrat_rewards.json",
)

CHARACTER_CLASS_DATA_FILE = "data/classes/bureaucrat.json"

ENEMY_DATA_FILES: tuple[str, ...] = (
    "data/enemies/city_enemies.json",
)

ENCOUNTER_DATA_FILES: tuple[str, ...] = (
    "data/encounters/act_1_city.json",
)

STATUS_DATA_FILES: tuple[str, ...] = (
    "data/statuses/statuses.json",
)

EVENT_DATA_FILES: tuple[str, ...] = (
    "data/events/act_1_city_events.json",
)

RELIC_DATA_FILES: tuple[str, ...] = (
    "data/relics/act_1_relics.json",
)

DEFAULT_ACT = 1
DEFAULT_MAX_FIGHTS = 99
DEFAULT_MAP_STEPS_BEFORE_BOSS = 9
DEFAULT_MAP_WIDTH = 4

WAITING_ROOM_HEAL_PERCENT = 25
MIMIC_CHANCE = 0.20

TREASURE_MIMIC_ENCOUNTER_ID = "city_elite_02"
