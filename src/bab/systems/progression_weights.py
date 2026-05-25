"""Shared act-progression weighting for card and relic offers."""

from __future__ import annotations

from collections.abc import Iterable


BASE_PROGRESSIVE_CONTENT_WEIGHT = 1
ACT_2_CONTENT_WEIGHT = 4
LATE_ACT_CURRENT_CONTENT_WEIGHT = 6
LATE_ACT_PREVIOUS_CONTENT_WEIGHT = 2


def content_progression_weight(
    tags: Iterable[str],
    *,
    act: int | None,
) -> int:
    """Return offer weight for content tagged by act progression.

    Act 2 keeps the original stronger preference for Act-2 content.
    From Act 3 onward, the current act is strongly preferred, the directly
    previous act remains available at lower weight, and older content remains
    rare at base weight.
    """

    if act is None or act <= 1:
        return BASE_PROGRESSIVE_CONTENT_WEIGHT

    tag_set = set(tags)

    if f"act_{act}" in tag_set:
        if act >= 3:
            return LATE_ACT_CURRENT_CONTENT_WEIGHT
        return ACT_2_CONTENT_WEIGHT

    if act >= 3 and f"act_{act - 1}" in tag_set:
        return LATE_ACT_PREVIOUS_CONTENT_WEIGHT

    return BASE_PROGRESSIVE_CONTENT_WEIGHT
