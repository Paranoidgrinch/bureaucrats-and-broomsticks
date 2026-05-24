from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="shroomancer",
            name="Mike Cellium",
            max_hp=76,
            hp=76,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_shroomancer_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/shroomancer_relics.json"])

    assert "spore_satchel" in relics
    assert "compost_pocket" in relics
    assert "spore_print_ledger" in relics
    assert all(relic.allowed_classes == ["shroomancer"] for relic in relics.values())


def test_shroomancer_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "spore_satchel" in catalog.relic_database
    assert "old_growth_ring" in catalog.relic_database
    assert "whispering_mycelium" in catalog.relic_database


def test_shroomancer_relic_filtering_accepts_only_shroomancer():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["spore_satchel"]

    assert relic_is_allowed_for_character(relic, "shroomancer")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "failed_wizard")
    assert not relic_is_allowed_for_character(relic, "sewer_diplomat")


def test_shroomancer_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_spore_satchel_adds_loose_spore_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["spore_satchel"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "loose_spore" in [card.id for card in state.hand]


def test_soft_cap_brooch_adds_soft_cap_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["soft_cap_brooch"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "soft_cap" in [card.id for card in state.hand]


def test_corked_spore_vial_applies_poison_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["corked_spore_vial"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["poison"].amount == 1


def test_damp_log_grants_block_and_adds_loose_spore_to_draw_pile():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["damp_log"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.player.block == 5
    assert "loose_spore" in [card.id for card in state.draw_pile]


def test_compost_pocket_adds_energy_and_soggy_compost_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["compost_pocket"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "soggy_compost" in [card.id for card in state.discard_pile]


def test_whispering_mycelium_adds_thread_and_soft_cap_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["whispering_mycelium"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    hand_ids = [card.id for card in state.hand]
    assert "mycelium_thread" in hand_ids
    assert "soft_cap" in hand_ids


def test_spore_print_ledger_applies_poison_and_doubt():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["spore_print_ledger"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["poison"].amount == 1
    assert state.enemies[0].statuses["doubt"].amount == 1


def test_wrong_class_does_not_roll_shroomancer_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    shroomancer_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["shroomancer"]
    }

    try:
        choose_random_unowned_relic(
            shroomancer_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no shroomancer relic for bureaucrat.")
