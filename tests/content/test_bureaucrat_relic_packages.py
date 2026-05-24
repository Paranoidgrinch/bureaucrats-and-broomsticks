from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.models import RelicEffect
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect


def make_state(card_database):
    return CombatState(
        player=Combatant(id="bureaucrat", name="Bureaucrat", max_hp=70, hp=70),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_bureaucrat_relic_file_loads():
    relics = load_relic_database(["data/relics/bureaucrat_relics.json"])

    assert "brass_filing_tray" in relics
    assert "deputy_seal" in relics
    assert "red_tape_dispenser" in relics
    assert "bottomless_inbox_tray" in relics


def test_bureaucrat_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "brass_filing_tray" in catalog.relic_database
    assert "permit_cabinet" in catalog.relic_database


def test_create_card_at_combat_start_adds_card_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["brass_filing_tray"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    hand_ids = [card.id for card in state.hand]
    assert "temporary_authorization" in hand_ids


def test_create_card_at_combat_start_can_add_junk_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["carbon_copy_pad"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    hand_ids = [card.id for card in state.hand]
    discard_ids = [card.id for card in state.discard_pile]

    assert "counter_signature" in hand_ids
    assert "duplicate_copy" in discard_ids


def test_bureaucrat_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing
