# Adding Statuses

Statuses are defined in JSON files under data/statuses/.

Current stacking styles:
- intensity
- duration

Current triggers:
- none
- player_turn_start
- enemy_turn_start
- enemy_turn_end
- before_owner_attack

A status definition alone does not create behavior. If the status needs a new trigger behavior, Python code must implement it.
