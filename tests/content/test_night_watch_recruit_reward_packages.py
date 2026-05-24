from bab.content.data_loader import load_card_database
from bab.systems.rewards import build_card_reward_pool


CARD_FILES = [
    "data/cards/night_watch_recruit_starter.json",
    "data/cards/night_watch_recruit_rewards.json",
]


def test_night_watch_reward_packages_load_and_exclude_generated_cards():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="night_watch_recruit")
    reward_ids = {card.id for card in reward_pool}

    generated_ids = {
        "watch_whistle",
        "backup_constable",
        "incident_report",
        "loose_cobblestone",
        "unfiled_complaint",
    }

    assert generated_ids.issubset(card_database)
    assert generated_ids.isdisjoint(reward_ids)


def test_night_watch_reward_pool_contains_expected_packages():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="night_watch_recruit")
    tags_by_card = {card.id: set(card.tags) for card in reward_pool}

    assert any("patrol" in tags for tags in tags_by_card.values())
    assert any("riot_act" in tags for tags in tags_by_card.values())
    assert any("shield" in tags for tags in tags_by_card.values())
    assert any("cudgel" in tags for tags in tags_by_card.values())
    assert any("backup" in tags for tags in tags_by_card.values())


def test_night_watch_create_card_effects_reference_existing_cards():
    card_database = load_card_database(CARD_FILES)

    missing = []
    for card in card_database.values():
        for effect in card.effects:
            if effect.type == "create_card" and effect.card_id not in card_database:
                missing.append((card.id, effect.card_id))

    assert not missing


def test_night_watch_reward_cards_have_upgrades():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="night_watch_recruit")

    missing_upgrades = []
    for card in reward_pool:
        if card.rarity in {"common", "uncommon", "rare"}:
            if card.upgrades_to is None:
                missing_upgrades.append(card.id)
            elif card.upgrades_to not in card_database:
                missing_upgrades.append(card.id)

    assert not missing_upgrades


def test_night_watch_starter_cards_have_tags():
    card_database = load_card_database(CARD_FILES)

    for card_id in [
        "cudgel_warning",
        "raised_shield",
        "read_the_riot_act",
        "boots_on_cobblestones",
    ]:
        assert card_database[card_id].tags
