# Adding Relics

Relics are defined in JSON files under data/relics/.

A relic can be added without Python changes if it uses an existing relic effect type.

Current relic effect examples:
- gain_block_at_combat_start
- apply_status_to_all_enemies_at_combat_start
- increase_max_energy
- heal_on_pickup
- increase_card_reward_count

Python changes are required only for a new relic effect type.
