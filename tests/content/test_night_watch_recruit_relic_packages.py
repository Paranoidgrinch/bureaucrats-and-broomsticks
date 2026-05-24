from random import Random

from bab.combat.state import CombatState, Combatant
from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.rules.relic_effect_handlers import resolve_combat_start_relic_effect
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def make_state(card_database):
    return CombatState(
        player=Combatant(
            id="night_watch_recruit",
            name="Night Watch Recruit",
            max_hp=78,
            hp=78,
        ),
        enemies=[Combatant(id="dummy", name="Dummy", max_hp=20, hp=20)],
        card_database=card_database,
    )


def test_night_watch_relic_file_loads_and_is_class_specific():
    relics = load_relic_database(["data/relics/night_watch_recruit_relics.json"])

    assert "tin_watch_badge" in relics
    assert "watch_whistle_cord" in relics
    assert "very_official_truncheon" in relics
    assert all(
        relic.allowed_classes == ["night_watch_recruit"]
        for relic in relics.values()
    )


def test_night_watch_relics_are_loaded_by_default_catalog():
    catalog = load_default_content_catalog()

    assert "tin_watch_badge" in catalog.relic_database
    assert "riot_helmet" in catalog.relic_database
    assert "emergency_backup_roster" in catalog.relic_database


def test_night_watch_relic_filtering_accepts_only_night_watch():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["watch_whistle_cord"]

    assert relic_is_allowed_for_character(relic, "night_watch_recruit")
    assert not relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "failed_wizard")
    assert not relic_is_allowed_for_character(relic, "guild_assassin_apprentice")


def test_night_watch_relic_create_card_references_exist():
    catalog = load_default_content_catalog()

    missing = []
    for relic in catalog.relic_database.values():
        for effect in relic.effects:
            if effect.type == "create_card_at_combat_start":
                if effect.card_id not in catalog.card_database:
                    missing.append((relic.id, effect.card_id))

    assert not missing


def test_watch_whistle_cord_adds_watch_whistle_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["watch_whistle_cord"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "watch_whistle" in [card.id for card in state.hand]


def test_patched_shield_strap_adds_backup_constable_to_hand():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["patched_shield_strap"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert "backup_constable" in [card.id for card in state.hand]


def test_beat_map_adds_energy_and_incident_report_to_discard():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["beat_map"]
    state = make_state(catalog.card_database)
    state.energy = 3

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.energy == 4
    assert "incident_report" in [card.id for card in state.discard_pile]


def test_bell_tower_token_applies_doubt_to_all_enemies():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["bell_tower_token"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.enemies[0].statuses["doubt"].amount == 2


def test_very_official_truncheon_adds_strength_and_loose_cobblestone():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["very_official_truncheon"]
    state = make_state(catalog.card_database)

    for effect in relic.effects:
        resolve_combat_start_relic_effect(effect, relic, state)

    assert state.player.statuses["strength"].amount == 1
    assert "loose_cobblestone" in [card.id for card in state.hand]


def test_wrong_class_does_not_roll_night_watch_relics_from_class_specific_pool():
    catalog = load_default_content_catalog()
    night_watch_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes == ["night_watch_recruit"]
    }

    try:
        choose_random_unowned_relic(
            night_watch_only,
            owned_relics=[],
            rng=Random(1),
            character_id="bureaucrat",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no night-watch relic for bureaucrat.")
