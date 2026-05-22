from dataclasses import dataclass
from random import Random

from bab.combat_state import CombatState, Combatant
from bab.deck import build_deck, shuffle_draw_pile
from bab.encounters import choose_random_encounter
from bab.enemies import create_enemies_for_encounter
from bab.models import (
    Card,
    CharacterClass,
    EncounterDefinition,
    EncounterDifficulty,
    EnemyDefinition,
    StatusDefinition,
)


@dataclass
class RunState:
    character_class: CharacterClass
    card_database: dict[str, Card]
    enemy_database: dict[str, EnemyDefinition]
    encounter_database: dict[str, EncounterDefinition]
    status_database: dict[str, StatusDefinition]
    rng: Random
    run_deck: list[Card]
    current_hp: int
    act: int = 1
    fight_number: int = 1
    max_fights: int = 3

    def is_complete(self) -> bool:
        return self.fight_number > self.max_fights

    def is_defeated(self) -> bool:
        return self.current_hp <= 0


def create_new_run(
    *,
    character_class: CharacterClass,
    card_database: dict[str, Card],
    enemy_database: dict[str, EnemyDefinition],
    encounter_database: dict[str, EncounterDefinition],
    status_database: dict[str, StatusDefinition],
    rng: Random | None = None,
    act: int = 1,
    max_fights: int = 3,
) -> RunState:
    if rng is None:
        rng = Random()

    run_deck = build_deck(
        character_class.starting_deck,
        card_database,
    )

    return RunState(
        character_class=character_class,
        card_database=card_database,
        enemy_database=enemy_database,
        encounter_database=encounter_database,
        status_database=status_database,
        rng=rng,
        run_deck=run_deck,
        current_hp=character_class.max_hp,
        act=act,
        fight_number=1,
        max_fights=max_fights,
    )


def create_combat_state_for_next_encounter(
    run_state: RunState,
    *,
    difficulty: EncounterDifficulty = "normal",
) -> CombatState:
    if run_state.is_defeated():
        raise ValueError("Cannot start combat because the player has no HP.")

    if run_state.is_complete():
        raise ValueError("Cannot start combat because the run is already complete.")

    encounter = choose_random_encounter(
        run_state.encounter_database,
        run_state.rng,
        act=run_state.act,
        difficulty=difficulty,
    )

    enemies = create_enemies_for_encounter(
        encounter.id,
        run_state.encounter_database,
        run_state.enemy_database,
    )

    player = Combatant(
        id=run_state.character_class.id,
        name=run_state.character_class.name,
        max_hp=run_state.character_class.max_hp,
        hp=run_state.current_hp,
    )

    state = CombatState(
        player=player,
        enemies=enemies,
        max_energy=run_state.character_class.starting_energy,
        energy=run_state.character_class.starting_energy,
        draw_pile=list(run_state.run_deck),
        status_database=run_state.status_database,
    )
    state.log.append(f"Encounter chosen: {encounter.name}.")
    shuffle_draw_pile(state, run_state.rng)

    return state


def finish_victorious_combat(
    run_state: RunState,
    combat_state: CombatState,
) -> None:
    if not combat_state.is_victory():
        raise ValueError("Cannot finish combat as victory because enemies are still alive.")

    run_state.current_hp = combat_state.player.hp
    run_state.fight_number += 1