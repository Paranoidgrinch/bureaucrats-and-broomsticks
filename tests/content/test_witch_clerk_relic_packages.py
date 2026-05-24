from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="witch_clerk",
            name="Witch Clerk",
            max_hp=64,
            hp=64,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_witch_clerk_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/witch_clerk_relics.json"])

    assert "minor_hex_stamp" in relics
    assert "carbon_copy_covenant" in relics
    assert "chief_witch_clerks_stamp" in relics
    assert all(relic.allowed_classes == ["witch_clerk"] for relic in relics.values())


def test_witch_clerk_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "minor_hex_stamp" in catalog.relic_database
    assert "enchanted_inbox_tray" in catalog.relic_database
    assert "desk_drawer_perch" in catalog.relic_database


def test_witch_clerk_relic_filtering_accepts_only_witch_clerk():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["minor_hex_stamp"]

    assert relic_is_allowed_for_character(relic, "witch_clerk")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "hedge_witch")
    assert not relic_is_allowed_for_character(relic, "mortuary_apprentice")


def test_witch_clerk_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_minor_hex_stamp_adds_hexed_stamp_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["minor_hex_stamp"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "hexed_stamp" in [card.id for card in state.hand]


def test_tea_stained_charm_tag_adds_tea_charm_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["tea_stained_charm_tag"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "tea_charm" in [card.id for card in state.hand]


def test_ink_stained_thimble_adds_ink_splatter_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["ink_stained_thimble"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "ink_splatter" in [card.id for card in state.hand]


def test_municipal_charm_string_grants_block_and_doubt():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["municipal_charm_string"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.player.block == 5
    assert state.enemies[0].statuses["doubt"].amount == 1


def test_after_hours_ledger_applies_paperwork_and_adds_stamp_to_draw():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["after_hours_ledger"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["paperwork"].amount == 1
    assert "hexed_stamp" in [card.id for card in state.draw_pile]


def test_carbon_copy_covenant_adds_energy_and_misfiled_hex():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["carbon_copy_covenant"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "misfiled_hex" in [card.id for card in state.discard_pile]


def test_chief_witch_clerks_stamp_applies_paperwork_and_doubt():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["chief_witch_clerks_stamp"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["paperwork"].amount == 1
    assert state.enemies[0].statuses["doubt"].amount == 1


def test_enchanted_inbox_tray_adds_stamp_and_tea_charm():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["enchanted_inbox_tray"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    hand_ids = [card.id for card in state.hand]
    assert "hexed_stamp" in hand_ids
    assert "tea_charm" in hand_ids


def test_wrong_class_does_not_roll_witch_clerk_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    witch_clerk_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["witch_clerk"]
    }

    try:
        choose_random_unowned_relic(
            witch_clerk_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no witch-clerk relic for bureaucrat.")
