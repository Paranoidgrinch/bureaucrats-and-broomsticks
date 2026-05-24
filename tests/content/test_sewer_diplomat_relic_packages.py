from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="sewer_diplomat",
            name="Sewer Diplomat",
            max_hp=68,
            hp=68,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_sewer_diplomat_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/sewer_diplomat_relics.json"])

    assert "cheese_envoy_badge" in relics
    assert "favours_ledger" in relics
    assert "unpleasant_diplomatic_pouch" in relics
    assert all(relic.allowed_classes == ["sewer_diplomat"] for relic in relics.values())


def test_sewer_diplomat_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "cheese_envoy_badge" in catalog.relic_database
    assert "rat_king_signature" in catalog.relic_database
    assert "official_manhole_cover" in catalog.relic_database


def test_sewer_diplomat_relic_filtering_accepts_only_sewer_diplomat():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["cheese_envoy_badge"]

    assert relic_is_allowed_for_character(relic, "sewer_diplomat")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "failed_wizard")
    assert not relic_is_allowed_for_character(relic, "night_watch_recruit")


def test_sewer_diplomat_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_cheese_envoy_badge_adds_cheese_favor_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["cheese_envoy_badge"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "cheese_favor" in [card.id for card in state.hand]


def test_rat_cousin_roster_adds_rat_cousin_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["rat_cousin_roster"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "rat_cousin" in [card.id for card in state.hand]


def test_gutter_seal_applies_paperwork_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["gutter_seal"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["paperwork"].amount == 1


def test_pocket_muck_sample_applies_poison_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["pocket_muck_sample"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["poison"].amount == 1


def test_underpipe_passage_key_grants_block_and_sewer_map():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["underpipe_passage_key"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.player.block == 6
    assert "sewer_map" in [card.id for card in state.hand]


def test_favours_ledger_adds_energy_and_spoiled_cheese_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["favours_ledger"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "spoiled_cheese" in [card.id for card in state.discard_pile]


def test_unpleasant_diplomatic_pouch_applies_poison_and_doubt():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["unpleasant_diplomatic_pouch"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["poison"].amount == 1
    assert state.enemies[0].statuses["doubt"].amount == 1


def test_wrong_class_does_not_roll_sewer_diplomat_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    sewer_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["sewer_diplomat"]
    }

    try:
        choose_random_unowned_relic(
            sewer_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no sewer-diplomat relic for bureaucrat.")
