from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import (
    build_card_reward_pool,
    card_progression_weight,
    choose_card_rewards,
)
from bab.systems.shop import (
    choose_shop_card_offers,
    choose_shop_relic_offers,
    eligible_shop_cards,
    eligible_shop_relics,
    shop_progression_weight,
)


ACT_3_MANIFEST = "data/acts/act_3_green_docket.json"


def _copy_model_with_tags(model, *, new_id: str, tags: list[str]):
    if hasattr(model, "model_copy"):
        return model.model_copy(update={"id": new_id, "tags": tags})
    return model.copy(update={"id": new_id, "tags": tags})


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


def test_act_3_card_progression_weights_prefer_act_3_then_act_2_then_older() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    older_card = next(
        card
        for card in catalog.card_database.values()
        if card.class_ == "bureaucrat"
        and card.rarity in {"common", "uncommon", "rare"}
        and "act_2" not in card.tags
        and "epic" not in card.tags
        and "upgraded" not in card.tags
    )
    act_2_card = next(
        card
        for card in catalog.card_database.values()
        if card.class_ == "bureaucrat"
        and card.rarity in {"common", "uncommon", "rare"}
        and "act_2" in card.tags
        and "epic" not in card.tags
        and "upgraded" not in card.tags
    )
    synthetic_act_3_card = _copy_model_with_tags(
        older_card,
        new_id="synthetic_act_3_reward_probe",
        tags=[tag for tag in older_card.tags if tag != "act_2"] + ["act_3"],
    )

    assert card_progression_weight(synthetic_act_3_card, act=3) == 6
    assert card_progression_weight(act_2_card, act=3) == 2
    assert card_progression_weight(older_card, act=3) == 1


def test_act_3_shop_progression_weights_prefer_act_3_then_act_2_then_older() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    older_relic = next(
        relic
        for relic in catalog.relic_database.values()
        if relic.rarity != "boss" and "act_2" not in relic.tags
    )
    act_2_relic = next(
        relic
        for relic in catalog.relic_database.values()
        if relic.rarity != "boss" and "act_2" in relic.tags
    )
    synthetic_act_3_relic = _copy_model_with_tags(
        older_relic,
        new_id="synthetic_act_3_relic_probe",
        tags=[tag for tag in older_relic.tags if tag != "act_2"] + ["act_3"],
    )

    assert shop_progression_weight(synthetic_act_3_relic, act=3) == 6
    assert shop_progression_weight(act_2_relic, act=3) == 2
    assert shop_progression_weight(older_relic, act=3) == 1


def test_act_3_normal_card_rewards_still_exclude_epics() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        rewards = choose_card_rewards(
            catalog.card_database,
            Random(1234),
            count=3,
            card_class=character_id,
            act=3,
        )

        assert reward_pool
        assert rewards
        assert all(card.rarity != "epic" for card in reward_pool)
        assert all(card.rarity != "epic" for card in rewards)
        assert all("transition_reward" not in card.tags for card in rewards)


def test_act_3_shop_cards_and_relics_use_weighted_progression_without_epics() -> None:
    catalog = load_content_catalog_from_act_manifest(ACT_3_MANIFEST)

    for character_id in CHARACTER_IDS:
        shop_cards = eligible_shop_cards(
            catalog.card_database,
            card_class=character_id,
            act=3,
            fight_number=7,
        )
        card_offers = choose_shop_card_offers(
            catalog.card_database,
            Random(5678),
            card_class=character_id,
            act=3,
            fight_number=7,
            count=5,
        )

        assert shop_cards
        assert card_offers
        assert all(card.rarity != "epic" for card in shop_cards)
        assert all(offer.card.rarity != "epic" for offer in card_offers)

    shop_relics = eligible_shop_relics(
        catalog.relic_database,
        owned_relics=[],
        act=3,
        fight_number=7,
        card_class="bureaucrat",
    )
    relic_offers = choose_shop_relic_offers(
        catalog.relic_database,
        owned_relics=[],
        rng=Random(9012),
        act=3,
        fight_number=7,
        card_class="bureaucrat",
        count=3,
    )

    assert shop_relics
    assert relic_offers
    assert all(relic.rarity != "boss" for relic in shop_relics)
    assert all(offer.relic.rarity != "boss" for offer in relic_offers)
