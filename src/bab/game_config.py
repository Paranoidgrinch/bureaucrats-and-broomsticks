"""Central configuration for the console prototype.

Most gameplay content is configured through act manifests in data/acts/.
"""

from __future__ import annotations

ACT_MANIFEST_FILES: tuple[str, ...] = (
    "data/acts/act_1_city.json",
    "data/acts/act_2_archives.json",
    "data/acts/act_3_green_docket.json",
    "data/acts/act_4_licensing_labyrinth.json",
    "data/acts/act_5_divine_ledger.json",
)

DEFAULT_ACT_MANIFEST_FILE = ACT_MANIFEST_FILES[0]

# Temporary run-level default. This can later become campaign configuration.
DEFAULT_MAX_FIGHTS = 99
