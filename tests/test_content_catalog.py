from bab.content_catalog import load_default_content_catalog


def test_default_content_catalog_loads_all_content_groups() -> None:
    catalog = load_default_content_catalog()

    assert catalog.character_class.id == "bureaucrat"
    assert catalog.card_database
    assert catalog.enemy_database
    assert catalog.encounter_database
    assert catalog.status_database
    assert catalog.event_database
    assert catalog.relic_database


def test_default_content_catalog_contains_starting_deck_cards() -> None:
    catalog = load_default_content_catalog()

    for card_id in catalog.character_class.starting_deck:
        assert card_id in catalog.card_database
