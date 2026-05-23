"""Gold reward helpers."""

from __future__ import annotations

from random import Random
from typing import Any


GOLD_REWARD_RANGES: dict[str, tuple[int, int]] = {
    "easy": (15, 25),
    "normal": (25, 40),
    "elite": (60, 90),
    "boss": (100, 140),
}


def gold_reward_for_difficulty(
    difficulty: str | None,
    rng: Random,
) -> int:
    normalized_difficulty = difficulty or "normal"

    if normalized_difficulty not in GOLD_REWARD_RANGES:
        normalized_difficulty = "normal"

    minimum, maximum = GOLD_REWARD_RANGES[normalized_difficulty]
    return rng.randint(minimum, maximum)


def gold_reward_for_map_node(
    map_node: Any | None,
    rng: Random,
) -> int:
    if map_node is None:
        return gold_reward_for_difficulty("normal", rng)

    node_type = getattr(map_node, "node_type", None)
    difficulty = getattr(map_node, "difficulty", None)

    if node_type == "boss":
        return gold_reward_for_difficulty("boss", rng)

    return gold_reward_for_difficulty(difficulty, rng)
