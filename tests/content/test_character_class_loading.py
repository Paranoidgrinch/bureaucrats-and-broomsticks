from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES


def test_act_manifests_load_character_class_collections() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        assert catalog.character_classes
        assert catalog.character_class.id == catalog.act_manifest.default_character_class_id


def test_all_loaded_character_classes_have_valid_starting_decks() -> None:
    for manifest_path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(manifest_path)

        for character_class in catalog.character_classes.values():
            assert character_class.starting_deck
            assert all(card_id in catalog.card_database for card_id in character_class.starting_deck)
