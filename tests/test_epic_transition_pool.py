from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool, choose_epic_card_rewards
from bab.systems.shop import eligible_shop_cards


CHARACTER_IDS = {
    "bureaucrat",
    "failed_wizard",
    "guild_assassin_apprentice",
    "hedge_witch",
    "mortuary_apprentice",
    "night_watch_recruit",
    "sewer_diplomat",
    "shroomancer",
    "witch_clerk",
}


def epic_cards_for(catalog, character_id: str):
    return [
        card
        for card in catalog.card_database.values()
        if card.class_ == character_id and card.rarity == "epic"
    ]


def test_each_character_has_nine_epic_transition_cards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")

    for character_id in CHARACTER_IDS:
        epics = epic_cards_for(catalog, character_id)

        assert len(epics) >= 9
        assert all("epic" in card.tags for card in epics)
        assert all("transition_reward" in card.tags for card in epics)
        assert all("build_defining" in card.tags for card in epics)


def test_epic_transition_rewards_are_character_specific() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")

    for character_id in CHARACTER_IDS:
        rewards = choose_epic_card_rewards(
            catalog.card_database,
            Random(1000),
            count=3,
            card_class=character_id,
        )

        assert len(rewards) == 3
        assert all(card.class_ == character_id for card in rewards)
        assert all(card.rarity == "epic" for card in rewards)


def test_epic_cards_stay_out_of_normal_rewards_and_shops() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        shop_pool = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=2,
            fight_number=4,
        )

        assert all(card.rarity != "epic" for card in reward_pool)
        assert all(card.rarity != "epic" for card in shop_pool)
