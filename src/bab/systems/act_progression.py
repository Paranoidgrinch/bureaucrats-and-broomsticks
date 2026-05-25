from __future__ import annotations

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.content.data_loader import load_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.run.map import generate_act_map
from bab.run.state import RunState


MAX_IMPLEMENTED_ACT = 5


def next_act_manifest_file(current_act: int) -> str | None:
    target_act = current_act + 1
    if target_act > MAX_IMPLEMENTED_ACT:
        return None

    for manifest_file in ACT_MANIFEST_FILES:
        manifest = load_act_manifest(manifest_file)
        if manifest.act == target_act:
            return manifest_file

    return None


def has_next_act(run_state: RunState) -> bool:
    return next_act_manifest_file(run_state.act) is not None


def advance_to_next_act(run_state: RunState) -> bool:
    manifest_file = next_act_manifest_file(run_state.act)
    if manifest_file is None:
        return False

    next_catalog = load_content_catalog_from_act_manifest(manifest_file)
    character_id = run_state.character_class.id

    if character_id not in next_catalog.character_classes:
        raise ValueError(
            f"Character class {character_id!r} is not available in "
            f"{next_catalog.act_manifest.id!r}."
        )

    next_character_class = next_catalog.character_classes[character_id]
    preserved_max_hp = max(run_state.character_class.max_hp, next_character_class.max_hp)
    if next_character_class.max_hp != preserved_max_hp:
        next_character_class = next_character_class.model_copy(
            update={"max_hp": preserved_max_hp}
        )

    run_state.character_class = next_character_class
    run_state.card_database = next_catalog.card_database
    run_state.enemy_database = next_catalog.enemy_database
    run_state.encounter_database = next_catalog.encounter_database
    run_state.status_database = next_catalog.status_database
    run_state.event_database = next_catalog.event_database
    run_state.relic_database = next_catalog.relic_database

    run_state.act = next_catalog.act_manifest.act
    run_state.run_map = generate_act_map(
        run_state.rng,
        act=next_catalog.act_manifest.act,
        steps_before_boss=next_catalog.act_manifest.map.steps_before_boss,
        width=next_catalog.act_manifest.map.width,
        first_elite_depth=next_catalog.act_manifest.map.first_elite_depth,
        elite_weight_multiplier=next_catalog.act_manifest.map.elite_weight_multiplier,
    )
    run_state.current_node_id = None
    run_state.current_hp = run_state.character_class.max_hp
    run_state.mimic_chance = next_catalog.act_manifest.treasure.mimic_chance
    run_state.treasure_mimic_encounter_id = (
        next_catalog.act_manifest.treasure.mimic_encounter_id
    )
    run_state.waiting_room_heal_percent = (
        next_catalog.act_manifest.waiting_room.heal_percent
    )

    return True
