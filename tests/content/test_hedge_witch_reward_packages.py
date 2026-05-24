from bab.content.data_loader import load_card_database
from bab.systems.rewards import build_card_reward_pool


CARD_FILES = [
    "data/cards/hedge_witch_starter.json",
    "data/cards/hedge_witch_rewards.json",
]


def test_hedge_witch_reward_packages_load_and_exclude_generated_cards():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="hedge_witch")
    reward_ids = {card.id for card in reward_pool}

    generated_ids = {
        "warm_poultice",
        "bitter_draught",
        "crow_feather",
        "spare_knot",
        "soggy_tea_leaves",
    }

    assert generated_ids.issubset(card_database)
    assert generated_ids.isdisjoint(reward_ids)


def test_hedge_witch_reward_pool_contains_expected_packages():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="hedge_witch")
    tags_by_card = {card.id: set(card.tags) for card in reward_pool}

    assert any("herb" in tags or "poultice" in tags for tags in tags_by_card.values())
    assert any("curse" in tags for tags in tags_by_card.values())
    assert any("charm" in tags or "ward" in tags for tags in tags_by_card.values())
    assert any("brew" in tags for tags in tags_by_card.values())
    assert any("familiar" in tags for tags in tags_by_card.values())


def test_hedge_witch_create_card_effects_reference_existing_cards():
    card_database = load_card_database(CARD_FILES)

    missing = []
    for card in card_database.values():
        for effect in card.effects:
            if effect.type == "create_card" and effect.card_id not in card_database:
                missing.append((card.id, effect.card_id))

    assert not missing


def test_hedge_witch_reward_cards_have_upgrades():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="hedge_witch")

    missing_upgrades = []
    for card in reward_pool:
        if card.rarity in {"common", "uncommon", "rare"}:
            if card.upgrades_to is None:
                missing_upgrades.append(card.id)
            elif card.upgrades_to not in card_database:
                missing_upgrades.append(card.id)

    assert not missing_upgrades


def test_hedge_witch_starter_cards_have_tags():
    card_database = load_card_database(CARD_FILES)

    for card_id in [
        "prickly_hex",
        "borrowed_shawl",
        "bad_luck_knot",
        "tea_and_threats",
        "crooked_pin",
    ]:
        assert card_database[card_id].tags
