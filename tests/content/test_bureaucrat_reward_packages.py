from bab.content.data_loader import load_card_database
from bab.systems.rewards import build_card_reward_pool


CARD_FILES = [
    "data/cards/bureaucrat_starter.json",
    "data/cards/bureaucrat_rewards.json",
]


def test_bureaucrat_reward_packages_load_and_exclude_generated_junk_from_rewards():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="bureaucrat")
    reward_ids = {card.id for card in reward_pool}

    assert "red_tape" in card_database
    assert "duplicate_copy" in card_database
    assert "misfiled_paper" in card_database
    assert "unsigned_form" in card_database

    assert "red_tape" not in reward_ids
    assert "duplicate_copy" not in reward_ids
    assert "misfiled_paper" not in reward_ids
    assert "unsigned_form" not in reward_ids


def test_bureaucrat_reward_pool_has_no_generic_spell_placeholders():
    card_database = load_card_database(CARD_FILES)

    removed_ids = {
        "fireball",
        "frostbolt",
        "lightning_bolt",
        "unauthorized_wand",
        "witchs_annotation",
        "lightning_audit",
    }

    assert removed_ids.isdisjoint(card_database)


def test_bureaucrat_reward_pool_contains_expected_archetype_packages():
    card_database = load_card_database(CARD_FILES)
    reward_pool = build_card_reward_pool(card_database, card_class="bureaucrat")
    tags_by_card = {card.id: set(card.tags) for card in reward_pool}

    assert any("paperwork" in tags and "payoff" in tags for tags in tags_by_card.values())
    assert any("zero_cost" in tags for tags in tags_by_card.values())
    assert any("junk" in tags for tags in tags_by_card.values())
    assert any("queue" in tags for tags in tags_by_card.values())
    assert any("stamp" in tags for tags in tags_by_card.values())


def test_bureaucrat_create_card_effects_reference_existing_cards():
    card_database = load_card_database(CARD_FILES)

    missing = []
    for card in card_database.values():
        for effect in card.effects:
            if effect.type == "create_card" and effect.card_id not in card_database:
                missing.append((card.id, effect.card_id))

    assert not missing
