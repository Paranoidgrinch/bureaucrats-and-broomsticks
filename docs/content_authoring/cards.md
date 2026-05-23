# Adding Cards

Cards are defined in JSON files under data/cards/.

A card can be added without Python changes if it only uses existing effect types and targets.

Required fields:
- id
- name
- class
- type
- cost
- rarity
- text
- effects
- tags

Upgrade convention:
- base cards may use upgrades_to
- upgraded target cards must exist
- upgraded target cards must include the tag upgraded
- upgraded cards should not appear as normal rewards

Common effect examples:
- deal_damage
- gain_block
- apply_status
- gain_strength
- damage_per_status

Python changes are required only when a card needs a genuinely new effect type.
