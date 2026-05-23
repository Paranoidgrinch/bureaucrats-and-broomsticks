from bab.content.catalog import load_default_content_catalog


EXPECTED_NEW_RELICS = {
    "stamped_lunchbox",
    "cracked_wax_seal",
    "municipal_umbrella",
    "certified_tea_mug",
    "moth_eaten_index",
    "queue_token",
    "gargoyle_chalk",
    "minor_healing_voucher",
    "red_ribbon_spool",
    "notary_candle",
    "archive_lantern",
    "sealed_healing_voucher",
    "extra_counter_ticket",
    "clerk_badge",
    "stone_counterweight",
    "bottomless_stamp_pad",
    "official_timepiece",
    "grand_ledger_chain",
    "charter_fragment",
    "deputy_signature",
}


def test_new_act_1_relics_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_NEW_RELICS <= set(catalog.relic_database)


def test_new_act_1_relics_have_valid_effects_and_text() -> None:
    catalog = load_default_content_catalog()

    for relic_id in EXPECTED_NEW_RELICS:
        relic = catalog.relic_database[relic_id]

        assert relic.name
        assert relic.description
        assert relic.effects
        assert relic.rarity in {"common", "uncommon", "rare", "boss"}


def test_act_1_has_large_relic_pool_for_shops_and_rewards() -> None:
    catalog = load_default_content_catalog()

    assert len(catalog.relic_database) >= 20


def test_act_1_relic_pool_has_rarity_variety() -> None:
    catalog = load_default_content_catalog()

    rarities = {
        relic.rarity
        for relic in catalog.relic_database.values()
    }

    assert {"common", "uncommon", "rare"} <= rarities
