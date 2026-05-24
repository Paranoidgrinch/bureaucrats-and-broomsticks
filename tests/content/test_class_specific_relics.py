from random import Random

from bab.content.catalog import load_default_content_catalog
from bab.content.data_loader import load_relic_database
from bab.systems.relics import choose_random_unowned_relic, relic_is_allowed_for_character


def test_bureaucrat_relics_declare_allowed_classes():
    relics = load_relic_database(["data/relics/bureaucrat_relics.json"])

    assert relics
    assert all(relic.allowed_classes == ["bureaucrat"] for relic in relics.values())


def test_general_relics_are_allowed_for_every_character():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["certified_tea_mug"]

    assert relic.allowed_classes == []
    assert relic_is_allowed_for_character(relic, "bureaucrat")
    assert relic_is_allowed_for_character(relic, "failed_wizard")


def test_class_specific_relic_filter_accepts_matching_character():
    catalog = load_default_content_catalog()
    relic = catalog.relic_database["brass_filing_tray"]

    assert relic_is_allowed_for_character(relic, "bureaucrat")
    assert not relic_is_allowed_for_character(relic, "failed_wizard")


def test_choose_random_unowned_relic_does_not_offer_wrong_class_specific_relics():
    catalog = load_default_content_catalog()
    character_id = "hedge_witch"

    for seed in range(50):
        relic = choose_random_unowned_relic(
            catalog.relic_database,
            owned_relics=[],
            rng=Random(seed),
            character_id=character_id,
        )

        assert relic.allowed_classes == [] or character_id in relic.allowed_classes


def test_choose_random_unowned_relic_can_offer_matching_class_specific_relics_when_general_pool_removed():
    catalog = load_default_content_catalog()
    class_specific_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes
    }

    relic = choose_random_unowned_relic(
        class_specific_only,
        owned_relics=[],
        rng=Random(1),
        character_id="bureaucrat",
    )

    assert relic.allowed_classes == ["bureaucrat"]


def test_choose_random_unowned_relic_raises_if_only_wrong_class_relics_available():
    catalog = load_default_content_catalog()
    class_specific_only = {
        relic_id: relic
        for relic_id, relic in catalog.relic_database.items()
        if relic.allowed_classes
    }

    try:
        choose_random_unowned_relic(
            class_specific_only,
            owned_relics=[],
            rng=Random(1),
            character_id="definitely_not_a_real_class",
        )
    except ValueError as exc:
        assert "No unowned relics available" in str(exc)
    else:
        raise AssertionError("Expected no available relics for an unmatched character id.")
