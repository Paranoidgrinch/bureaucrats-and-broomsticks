from bab.content.catalog import load_content_catalog_from_act_manifest


ALLOWED_EVENT_EFFECT_TYPES = {
    "none",
    "gain_card_reward",
    "upgrade_card",
    "lose_percent_max_hp",
    "remove_card",
    "open_shop",
}


def test_act_2_has_large_archive_event_pool() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    act_2_events = [
        event
        for event in catalog.event_database.values()
        if event.act == 2
    ]

    assert len(act_2_events) >= 12

    event_ids = {event.id for event in act_2_events}
    assert "act_2_self_correcting_index" in event_ids
    assert "act_2_locked_reading_room" in event_ids
    assert "act_2_borrower_who_never_returned" in event_ids
    assert "act_2_shelf_that_shelves_back" in event_ids
    assert "act_2_margin_notes" in event_ids


def test_act_2_events_are_archive_themed() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for event in catalog.event_database.values():
        if event.act != 2:
            continue

        assert "archive" in event.tags
        assert "city" not in event.tags


def test_act_2_events_use_supported_console_effects() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for event in catalog.event_database.values():
        if event.act != 2:
            continue

        assert event.choices

        for choice in event.choices:
            for effect in choice.effects:
                assert effect.type in ALLOWED_EVENT_EFFECT_TYPES


def test_act_2_has_multiple_event_types() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    event_types = {
        event.event_type
        for event in catalog.event_database.values()
        if event.act == 2
    }

    assert "narrative" in event_types
    assert "risk_reward" in event_types
    assert "deck" in event_types


def test_act_2_has_shop_and_deck_events() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    has_shop_event = False
    has_remove_event = False
    has_upgrade_event = False

    for event in catalog.event_database.values():
        if event.act != 2:
            continue

        for choice in event.choices:
            for effect in choice.effects:
                if effect.type == "open_shop":
                    has_shop_event = True
                if effect.type == "remove_card":
                    has_remove_event = True
                if effect.type == "upgrade_card":
                    has_upgrade_event = True

    assert has_shop_event
    assert has_remove_event
    assert has_upgrade_event
