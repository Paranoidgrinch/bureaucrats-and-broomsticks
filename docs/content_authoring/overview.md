# Content Authoring Overview

Bureaucrats and Broomsticks is intended to be content-first.

Most new gameplay content should be added through JSON files:
- cards
- enemies
- encounters
- events
- relics
- statuses
- act manifests
- character classes

Python code should usually only change when a genuinely new rule, effect type, target type, or flow behavior is introduced.

All player-facing game content must be in English.

All technical IDs should be English snake_case, for example:
- paper_cut
- certified_tea_mug
- archive_goblin
- procedural_delay

Do not use German text in game content.
