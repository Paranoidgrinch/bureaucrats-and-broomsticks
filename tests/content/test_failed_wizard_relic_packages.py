from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(id="failed_wizard", name="Failed Wizard", max_hp=62, hp=62),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_failed_wizard_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/failed_wizard_relics.json"])

    assert "cracked_wizard_hat" in relics
    assert "borrowed_spellbook" in relics
    assert "overfull_thaumic_pocket" in relics
    assert all(relic.allowed_classes == ["failed_wizard"] for relic in relics.values())


def test_failed_wizard_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "cracked_wizard_hat" in catalog.relic_database
    assert "luggage_splinter" in catalog.relic_database
    assert "academy_rejection_letter" in catalog.relic_database


def test_failed_wizard_relic_filtering_accepts_only_failed_wizard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["cracked_wizard_hat"]

    assert relic_is_allowed_for_character(relic, "failed_wizard")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")


def test_failed_wizard_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_cracked_wizard_hat_adds_loose_spark_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["cracked_wizard_hat"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "loose_spark" in [card.id for card in state.hand]


def test_borrowed_spellbook_adds_bad_incantation_to_discard_and_energy():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["borrowed_spellbook"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "bad_incantation" in [card.id for card in state.discard_pile]


def test_luggage_splinter_adds_two_spell_fragments_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["luggage_splinter"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    hand_ids = [card.id for card in state.hand]
    assert "escaped_syllable" in hand_ids
    assert "loose_spark" in hand_ids


def test_wrong_class_does_not_roll_failed_wizard_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    failed_wizard_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["failed_wizard"]
    }

    try:
        choose_random_unowned_relic(
            failed_wizard_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no failed-wizard relic for bureaucrat.")
