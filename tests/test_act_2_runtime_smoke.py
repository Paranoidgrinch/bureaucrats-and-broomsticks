from random import Random

from bab.console.run_flow import create_run_state
from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.sim.auto_runner import SimConfig, simulate_runs
from bab.systems.rewards import build_card_reward_pool, choose_epic_card_rewards
from bab.systems.shop import choose_shop_card_offers, choose_shop_relic_offers


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


def test_act_2_can_create_run_state_for_every_character() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        run_state = create_run_state(
            character_id,
            catalog=catalog,
            rng=Random(100),
        )

        assert run_state.act == 2
        assert run_state.run_map.act == 2
        assert run_state.current_hp == run_state.character_class.max_hp
        assert run_state.character_class.id == character_id
        assert run_state.treasure_mimic_encounter_id == "archive_mimic_01"
        assert run_state.mimic_chance == 0.05


def test_act_2_direct_random_simulation_has_no_runtime_errors() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    summary = simulate_runs(
        SimConfig(
            runs=25,
            seed=2202,
            max_combat_turns=60,
            reward_skip_chance=0.15,
            card_play_stop_chance=0.08,
            shop_leave_chance=0.20,
        ),
        catalog=catalog,
        raise_errors=True,
    )

    assert summary.total_runs == 25
    assert summary.errors == 0
    assert all(result.error is None for result in summary.results)


def test_act_2_reward_and_shop_pools_do_not_offer_epic_transition_cards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    for character_id in CHARACTER_IDS:
        normal_reward_pool = build_card_reward_pool(
            catalog.card_database,
            card_class=character_id,
        )
        shop_card_offers = choose_shop_card_offers(
            catalog.card_database,
            Random(300),
            card_class=character_id,
            act=2,
            fight_number=4,
            count=5,
        )

        assert normal_reward_pool
        assert shop_card_offers

        assert all(card.rarity != "epic" for card in normal_reward_pool)
        assert all("epic" not in card.tags for card in normal_reward_pool)

        assert all(offer.card.rarity != "epic" for offer in shop_card_offers)
        assert all("epic" not in offer.card.tags for offer in shop_card_offers)


def test_epic_transition_pool_remains_character_specific() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")

    for character_id in CHARACTER_IDS:
        rewards = choose_epic_card_rewards(
            catalog.card_database,
            Random(400),
            count=3,
            card_class=character_id,
        )

        assert len(rewards) == 3
        assert all(card.rarity == "epic" for card in rewards)
        assert all(card.class_ == character_id for card in rewards)


def test_act_2_shop_relic_offers_are_valid_and_non_boss() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")
    run_state = create_run_state(
        "bureaucrat",
        catalog=catalog,
        rng=Random(500),
    )

    offers = choose_shop_relic_offers(
        catalog.relic_database,
        run_state.relics,
        Random(501),
        act=2,
        fight_number=4,
        count=3,
    )

    assert offers
    assert all(offer.relic.id in catalog.relic_database for offer in offers)
    assert all(offer.relic.rarity != "boss" for offer in offers)
