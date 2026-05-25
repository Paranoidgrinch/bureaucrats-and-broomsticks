from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES


def test_each_act_with_events_has_shop_event() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        if not catalog.act_manifest.event_files:
            assert catalog.event_database == {}
            continue

        shop_events = [
            event
            for event in catalog.event_database.values()
            if "shop" in event.tags
        ]

        assert shop_events, f"{catalog.act_manifest.id} has no shop event."


def test_each_shop_event_can_open_shop() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        shop_events = [
            event
            for event in catalog.event_database.values()
            if "shop" in event.tags
        ]

        for event in shop_events:
            effect_types = {
                effect.type
                for choice in event.choices
                for effect in choice.effects
            }
            assert "open_shop" in effect_types
