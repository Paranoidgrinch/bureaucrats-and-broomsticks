# Adding Character Classes

Character classes are defined in JSON files under data/classes/.

A class defines:
- id
- name
- max_hp
- starting_energy
- optional starting_relic
- starting_deck
- starting_resources

The class id must also be allowed in src/bab/models/types.py.

Each act manifest lists available class files through character_class_files.

The default class for a manifest is selected through default_character_class_id.

A new class usually also needs:
- starter cards
- reward cards
- entries in the relevant act manifests

All player-facing class, card, and relic text must be in English.
