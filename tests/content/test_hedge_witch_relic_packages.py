from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="hedge_witch",
            name="Hedge Witch",
            max_hp=66,
            hp=60,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_hedge_witch_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/hedge_witch_relics.json"])

    assert "herb_pouch" in relics
    assert "chipped_teacup" in relics
    assert "blackened_kettle" in relics
    assert all(relic.allowed_classes == ["hedge_witch"] for relic in relics.values())


def test_hedge_witch_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "herb_pouch" in catalog.relic_database
    assert "simmering_kettle" in catalog.relic_database
    assert "familiar_perch" in catalog.relic_database


def test_hedge_witch_relic_filtering_accepts_only_hedge_witch():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["herb_pouch"]

    assert relic_is_allowed_for_character(relic, "hedge_witch")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "failed_wizard")
    assert not relic_is_allowed_for_character(relic, "night_watch_recruit")


def test_hedge_witch_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_herb_pouch_adds_warm_poultice_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["herb_pouch"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "warm_poultice" in [card.id for card in state.hand]


def test_crow_button_adds_crow_feather_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["crow_button"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "crow_feather" in [card.id for card in state.hand]


def test_knot_box_adds_spare_knot_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["knot_box"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "spare_knot" in [card.id for card in state.hand]


def test_chipped_teacup_applies_doubt_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["chipped_teacup"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["doubt"].amount == 1


def test_village_remedy_bag_heals_and_grants_block():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["village_remedy_bag"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.player.hp == 62
    assert state.player.block == 3


def test_thirteenth_spoon_adds_energy_and_soggy_tea_leaves_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["thirteenth_spoon"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "soggy_tea_leaves" in [card.id for card in state.discard_pile]


def test_blackened_kettle_applies_poison_and_adds_junk():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["blackened_kettle"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["poison"].amount == 2
    assert "soggy_tea_leaves" in [card.id for card in state.discard_pile]


def test_wrong_class_does_not_roll_hedge_witch_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    hedge_witch_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["hedge_witch"]
    }

    try:
        choose_random_unowned_relic(
            hedge_witch_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no hedge-witch relic for bureaucrat.")
