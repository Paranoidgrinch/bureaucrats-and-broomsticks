from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.content.data_loader import load_act_manifest
from bab.game_config import ACT_MANIFEST_FILES


def test_all_configured_act_manifests_load() -> None:
    manifests = [load_act_manifest(path) for path in ACT_MANIFEST_FILES]

    assert [manifest.act for manifest in manifests] == [1, 2, 3, 4, 5]
    assert len({manifest.id for manifest in manifests}) == 5


def test_all_configured_act_catalogs_load() -> None:
    for path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(path)

        assert catalog.act_manifest.id
        assert catalog.character_class.id == "bureaucrat"
        assert catalog.card_database
        assert catalog.enemy_database
        assert catalog.encounter_database
        assert catalog.status_database
        assert catalog.event_database
        assert catalog.relic_database


def test_each_act_catalog_contains_matching_act_encounters_and_events() -> None:
    for path in ACT_MANIFEST_FILES:
        catalog = load_content_catalog_from_act_manifest(path)
        act = catalog.act_manifest.act

        assert all(encounter.act == act for encounter in catalog.encounter_database.values())
        assert all(event.act == act for event in catalog.event_database.values())
