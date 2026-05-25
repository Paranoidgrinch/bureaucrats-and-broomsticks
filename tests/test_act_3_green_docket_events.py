from collections import Counter

from bab.content.catalog import load_content_catalog_from_act_manifest


ACT_3_MANIFEST = "data/acts/act_3_green_docket.json"


def _act_3_events():
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)
    return [
        event
        for event in catalog.event_database.values()
        if event.act == 3
    ]


def test_act_3_has_substantial_green_docket_event_pool() -> None:
    events = _act_3_events()

    assert len(events) >= 18

    counts = Counter(event.event_type for event in events)
    assert counts["narrative"] >= 5
    assert counts["deck"] >= 5
    assert counts["risk_reward"] >= 6


def test_act_3_events_include_restorative_nature_moments() -> None:
    events = _act_3_events()
    event_ids = {event.id for event in events}

    assert {
        "green_docket_nap_in_the_sun",
        "green_docket_stargazing",
        "green_docket_clear_stream",
        "green_docket_quiet_meadow",
        "green_docket_rain_under_one_tree",
    }.issubset(event_ids)

    restorative_events = [
        event
        for event in events
        if {"rest", "healing", "nature"}.intersection(set(event.tags))
    ]

    assert len(restorative_events) >= 8


def test_act_3_events_include_absurd_bureaucratic_road_events() -> None:
    events = _act_3_events()
    event_ids = {event.id for event in events}

    assert {
        "green_docket_toll_bridge_without_bridge",
        "green_docket_hedge_requires_notice",
        "green_docket_rangers_form",
        "green_docket_public_footpath_dispute",
        "green_docket_foresters_notice_board",
    }.issubset(event_ids)


def test_act_3_events_are_not_city_or_archive_placeholders() -> None:
    events = _act_3_events()

    forbidden_tags = {"city", "archive", "tribunal"}
    forbidden_ids = {
        "act_3_misfiled_prophecy",
        "act_3_haunted_suggestion_box",
        "act_3_unionized_broom_closet",
        "act_3_lost_and_found_desk",
    }

    assert forbidden_ids.isdisjoint({event.id for event in events})

    for event in events:
        assert "green_docket" in event.tags
        assert forbidden_tags.isdisjoint(set(event.tags))
        assert "Procedural Tribunal" not in event.name


def test_act_3_events_use_supported_existing_effect_types() -> None:
    events = _act_3_events()
    supported_effect_types = {
        "none",
        "gain_card_reward",
        "upgrade_card",
        "lose_percent_max_hp",
        "gain_max_hp",
        "remove_card",
        "open_shop",
    }

    seen_effect_types = set()

    for event in events:
        assert event.choices
        for choice in event.choices:
            for effect in choice.effects:
                seen_effect_types.add(effect.type)
                assert effect.type in supported_effect_types

    assert {
        "gain_card_reward",
        "upgrade_card",
        "remove_card",
        "gain_max_hp",
        "open_shop",
    }.issubset(seen_effect_types)
