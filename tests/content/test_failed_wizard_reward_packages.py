from bab.content.data_loader import load_card_database
from bab.systems.rewards import build_card_reward_pool


CARD_FILES = [
    "data/cards/failed_wizard_starter.json",
    "data/cards/failed_wizard_rewards.json",
]


def test_failed_wizard_reward_packages_load_and_exclude_generated_cards():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="failed_wizard")
    reward_ids = {card.id for card in reward_pool}

    generated_ids = {
        "loose_spark",
        "escaped_syllable",
        "half_remembered_spell",
        "smoking_rune",
        "bad_incantation",
    }

    assert generated_ids.issubset(card_database)
    assert generated_ids.isdisjoint(reward_ids)


def test_failed_wizard_reward_pool_contains_expected_packages():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="failed_wizard")
    tags_by_card = {card.id: set(card.tags) for card in reward_pool}

    assert any("misfire" in tags for tags in tags_by_card.values())
    assert any("panic" in tags for tags in tags_by_card.values())
    assert any("borrowed_thaum" in tags for tags in tags_by_card.values())
    assert any("spell_fragment" in tags for tags in tags_by_card.values())
    assert any("unstable" in tags for tags in tags_by_card.values())


def test_failed_wizard_create_card_effects_reference_existing_cards():
    card_database = load_card_database(CARD_FILES)

    missing = []
    for card in card_database.values():
        for effect in card.effects:
            if effect.type == "create_card" and effect.card_id not in card_database:
                missing.append((card.id, effect.card_id))

    assert not missing


def test_failed_wizard_reward_cards_have_upgrades():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="failed_wizard")

    missing_upgrades = []
    for card in reward_pool:
        if card.rarity in {"common", "uncommon", "rare"}:
            if card.upgrades_to is None:
                missing_upgrades.append(card.id)
            elif card.upgrades_to not in card_database:
                missing_upgrades.append(card.id)

    assert not missing_upgrades


def test_failed_wizard_starter_cards_have_tags():
    card_database = load_card_database(CARD_FILES)

    for card_id in [
        "sparks_probably",
        "robe_flap",
        "borrowed_thaum",
        "luggage_burst",
    ]:
        assert card_database[card_id].tags
