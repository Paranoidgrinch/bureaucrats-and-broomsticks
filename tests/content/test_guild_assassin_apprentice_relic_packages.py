from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="guild_assassin_apprentice",
            name="Guild Assassin Apprentice",
            max_hp=58,
            hp=58,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_guild_assassin_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/guild_assassin_apprentice_relics.json"])

    assert "calling_card_case" in relics
    assert "polished_stiletto" in relics
    assert "sealed_black_contract" in relics
    assert all(
        relic.allowed_classes == ["guild_assassin_apprentice"]
        for relic in relics.values()
    )


def test_guild_assassin_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "calling_card_case" in catalog.relic_database
    assert "contract_ledger" in catalog.relic_database
    assert "tasteful_vial_collection" in catalog.relic_database


def test_guild_assassin_relic_filtering_accepts_only_guild_assassin():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["calling_card_case"]

    assert relic_is_allowed_for_character(relic, "guild_assassin_apprentice")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "failed_wizard")


def test_guild_assassin_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_calling_card_case_adds_calling_card_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["calling_card_case"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "calling_card" in [card.id for card in state.hand]


def test_vial_ring_adds_poisoned_pin_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["vial_ring"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "poisoned_pin" in [card.id for card in state.hand]


def test_discreet_exit_route_adds_energy_and_false_alibi_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["discreet_exit_route"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "false_alibi" in [card.id for card in state.discard_pile]


def test_contract_ledger_applies_doubt_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["contract_ledger"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["doubt"].amount == 2


def test_wrong_class_does_not_roll_guild_assassin_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    guild_assassin_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["guild_assassin_apprentice"]
    }

    try:
        choose_random_unowned_relic(
            guild_assassin_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no guild-assassin relic for bureaucrat.")
