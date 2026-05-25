import json
from collections import Counter
from pathlib import Path

from bab.content.catalog import load_content_catalog_from_act_manifest


ACT_4_MANIFEST = "data/acts/act_4_licensing_labyrinth.json"
ACT_4_EVENT_FILE = Path("data/events/act_4_licensing_labyrinth_events.json")

POSITIVE_EFFECT_TYPES = {
    "gain_card_reward",
    "upgrade_card",
    "remove_card",
    "gain_max_hp",
    "open_shop",
}

EXPECTED_POSITIVE_EVENT_IDS = {
    "act_4_shop",
    "act_4_red_linen_thread",
    "act_4_fountain_of_recorded_water",
    "act_4_cartouche_repair_bench",
    "act_4_weighing_room_mercy",
}


def _events():
    return json.loads(ACT_4_EVENT_FILE.read_text(encoding="utf-8"))


def _has_positive_option(event: dict) -> bool:
    return any(
        effect["type"] in POSITIVE_EFFECT_TYPES
        for choice in event["choices"]
        for effect in choice["effects"]
    )


def test_act_4_events_are_pyramid_labyrinth_hazard_package() -> None:
    events = _events()

    assert len(events) == 15
    assert len({event["id"] for event in events}) == 15
    assert Counter(event["event_type"] for event in events) == {
        "risk_reward": 11,
        "deck": 2,
        "narrative": 2,
    }

    for event in events:
        assert event["act"] == 4
        assert "act_4" in event["tags"]
        assert "pyramid" in event["tags"]
        assert "licensing_labyrinth" in event["tags"]
        assert "city" not in event["tags"]
        assert event["choices"]


def test_act_4_events_have_only_five_positive_opportunities() -> None:
    events = _events()

    positive_event_ids = {
        event["id"]
        for event in events
        if _has_positive_option(event)
    }

    assert positive_event_ids == EXPECTED_POSITIVE_EVENT_IDS
    assert len(positive_event_ids) == 5


def test_act_4_negative_events_apply_losses_or_no_reward_only() -> None:
    events = _events()

    for event in events:
        if event["id"] in EXPECTED_POSITIVE_EVENT_IDS:
            continue

        for choice in event["choices"]:
            effect_types = {effect["type"] for effect in choice["effects"]}
            assert effect_types <= {"lose_percent_max_hp", "none"}


def test_act_4_has_exactly_one_shop_event_and_catalog_loads_it() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_4_MANIFEST)
    events = _events()

    shop_events = [event for event in events if event["id"] == "act_4_shop"]
    assert len(shop_events) == 1
    assert any(
        effect["type"] == "open_shop"
        for choice in shop_events[0]["choices"]
        for effect in choice["effects"]
    )
    assert "act_4_shop" in catalog.event_database
