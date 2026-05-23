from bab.combat.state import Combatant
from bab.models import EncounterDefinition, EnemyDefinition


def create_enemy(
    enemy_id: str,
    enemy_database: dict[str, EnemyDefinition],
) -> Combatant:
    if enemy_id not in enemy_database:
        raise ValueError(f"Unknown enemy id: {enemy_id}")

    enemy_definition = enemy_database[enemy_id]

    return Combatant(
        id=enemy_definition.id,
        name=enemy_definition.name,
        max_hp=enemy_definition.max_hp,
        hp=enemy_definition.max_hp,
        intents=enemy_definition.intents,
    )


def create_enemies_for_encounter(
    encounter_id: str,
    encounter_database: dict[str, EncounterDefinition],
    enemy_database: dict[str, EnemyDefinition],
) -> list[Combatant]:
    if encounter_id not in encounter_database:
        raise ValueError(f"Unknown encounter id: {encounter_id}")

    encounter = encounter_database[encounter_id]

    return [
        create_enemy(enemy_id, enemy_database)
        for enemy_id in encounter.enemies
    ]