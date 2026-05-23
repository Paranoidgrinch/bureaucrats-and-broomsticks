from bab.content.catalog import load_default_content_catalog


EXPECTED_GOLD_SHOP_RELICS = {
    "petty_cash_purse",
    "municipal_tax_stamp",
    "counterfeit_coupon",
    "toll_exemption_badge",
    "vendor_license",
    "bottom_drawer_coins",
}


def test_gold_and_shop_relics_are_available() -> None:
    catalog = load_default_content_catalog()

    assert EXPECTED_GOLD_SHOP_RELICS <= set(catalog.relic_database)


def test_relic_content_uses_gold_and_shop_effects() -> None:
    catalog = load_default_content_catalog()

    used_effect_types = {
        effect.type
        for relic in catalog.relic_database.values()
        for effect in relic.effects
    }

    assert "gain_gold_on_pickup" in used_effect_types
    assert "increase_gold_rewards" in used_effect_types
    assert "shop_price_discount" in used_effect_types
