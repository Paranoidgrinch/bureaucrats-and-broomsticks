from bab.content.catalog import load_default_content_catalog
from bab.sim.card_features import (
    build_card_feature_index,
    feature_from_card,
    keyword_card_role,
    safe_load_default_card_feature_index,
)


def test_default_card_feature_index_loads() -> None:
    index = safe_load_default_card_feature_index()

    assert index.features_by_id


def test_card_feature_index_contains_default_cards() -> None:
    catalog = load_default_content_catalog()
    index = build_card_feature_index(catalog.card_database)

    assert set(catalog.card_database).issubset(set(index.features_by_id))


def test_feature_from_card_assigns_known_role() -> None:
    catalog = load_default_content_catalog()
    card = next(iter(catalog.card_database.values()))

    feature = feature_from_card(card)

    assert feature.card_id == card.id
    assert feature.role in {
        "bad",
        "attack_block",
        "attack_debuff",
        "attack",
        "block_utility",
        "block",
        "scaling",
        "debuff",
        "energy",
        "draw",
        "other",
    }


def test_keyword_card_role_fallback() -> None:
    assert keyword_card_role("basic_strike") == "attack"
    assert keyword_card_role("careful_block") == "block"
    assert keyword_card_role("mysterious_unknown_card") == "other"
