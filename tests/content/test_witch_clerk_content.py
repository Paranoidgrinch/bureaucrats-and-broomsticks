from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES


def test_witch_clerk_is_available_in_all_acts() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        assert "witch_clerk" in catalog.character_classes
        assert catalog.character_classes["witch_clerk"].name == "Witch Clerk"


def test_witch_clerk_starting_deck_cards_exist() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        witch_clerk = catalog.character_classes["witch_clerk"]

        missing = sorted(set(witch_clerk.starting_deck) - set(catalog.card_database))
        assert not missing


def test_witch_clerk_cards_are_class_tagged() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        witch_card_ids = {
            "ritual_memo",
            "ritual_memo_plus",
            "broom_shield",
            "broom_shield_plus",
            "suspicious_charm",
            "suspicious_charm_plus",
            "stamped_incantation",
            "stamped_incantation_plus",
            "archive_breeze",
            "familiar_errand",
            "cauldron_stamp",
            "hexed_post_it",
            "broom_audit",
            "emergency_ward",
        }

        for card_id in witch_card_ids:
            assert catalog.card_database[card_id].class_ == "witch_clerk"
