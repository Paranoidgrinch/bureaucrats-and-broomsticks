# Adding Events

Events are defined in JSON files under data/events/.

Events contain player choices. Choices apply event effects.

Current event effect examples:
- none
- gain_card_reward
- upgrade_card
- remove_card
  - optional card_id restricts removal to a specific card
  - optional tag restricts removal to cards with that tag
- lose_percent_max_hp
- gain_max_hp
- open_shop

Python changes are required only for a new event effect type.
