from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="mortuary_apprentice",
            name="Mortuary Apprentice",
            max_hp=72,
            hp=72,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_mortuary_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/mortuary_apprentice_relics.json"])

    assert "undertakers_stamp" in relics
    assert "death_certificate_pad" in relics
    assert "coffin_nail_collection" in relics
    assert all(
        relic.allowed_classes == ["mortuary_apprentice"]
        for relic in relics.values()
    )


def test_mortuary_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "undertakers_stamp" in catalog.relic_database
    assert "silver_funeral_bell" in catalog.relic_database
    assert "borrowed_spirit_lantern" in catalog.relic_database


def test_mortuary_relic_filtering_accepts_only_mortuary():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["undertakers_stamp"]

    assert relic_is_allowed_for_character(relic, "mortuary_apprentice")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "hedge_witch")
    assert not relic_is_allowed_for_character(relic, "night_watch_recruit")


def test_mortuary_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_black_ribbon_spool_adds_black_ribbon_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["black_ribbon_spool"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "black_ribbon" in [card.id for card in state.hand]


def test_death_certificate_pad_adds_death_certificate_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["death_certificate_pad"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "death_certificate" in [card.id for card in state.hand]


def test_undertakers_stamp_applies_paperwork_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["undertakers_stamp"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["paperwork"].amount == 1


def test_quiet_hearse_key_adds_energy_and_unfinished_obituary_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["quiet_hearse_key"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "unfinished_obituary" in [card.id for card in state.discard_pile]


def test_silver_funeral_bell_adds_echo_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["silver_funeral_bell"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "paperwork" not in state.enemies[0].statuses
    assert "small_bell_echo" in [card.id for card in state.hand]


def test_coffin_nail_collection_adds_strength_and_bone_splinter():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["coffin_nail_collection"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.player.statuses["strength"].amount == 1
    assert "bone_splinter" in [card.id for card in state.hand]


def test_wrong_class_does_not_roll_mortuary_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    mortuary_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["mortuary_apprentice"]
    }

    try:
        choose_random_unowned_relic(
            mortuary_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no mortuary relic for bureaucrat.")
