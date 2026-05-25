from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.game_config import ACT_MANIFEST_FILES
from bab.run.state import create_new_run
from bab.systems.act_progression import advance_to_next_act, has_next_act
from bab.systems.rewards import build_card_reward_pool, choose_card_rewards
from bab.systems.shop import (
    choose_shop_card_offers,
    choose_shop_relic_offers,
)


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


def _make_run():
    catalog = load_content_catalog_from_act_manifest(ACT_MANIFEST_FILES[0])
    character_class = catalog.character_classes["bureaucrat"]
    return create_new_run(
        character_class=character_class,
        card_database=catalog.card_database,
        enemy_database=catalog.enemy_database,
        encounter_database=catalog.encounter_database,
        status_database=catalog.status_database,
        event_database=catalog.event_database,
        relic_database=catalog.relic_database,
        rng=Random(12345),
        act=catalog.act_manifest.act,
        map_steps_before_boss=catalog.act_manifest.map.steps_before_boss,
        map_width=catalog.act_manifest.map.width,
        map_first_elite_depth=catalog.act_manifest.map.first_elite_depth,
        map_elite_weight_multiplier=catalog.act_manifest.map.elite_weight_multiplier,
        mimic_chance=catalog.act_manifest.treasure.mimic_chance,
        treasure_mimic_encounter_id=catalog.act_manifest.treasure.mimic_encounter_id,
        waiting_room_heal_percent=catalog.act_manifest.waiting_room.heal_percent,
    )


def test_run_can_advance_through_all_five_implemented_acts() -> None:
    run_state = _make_run()

    for expected_next_act in [2, 3, 4, 5]:
        assert has_next_act(run_state)

        run_state.current_hp = 1
        run_state.completed_node_ids.append(run_state.run_map.boss_node_id)

        assert run_state.is_complete()
        assert advance_to_next_act(run_state)

        manifest = load_content_catalog_from_act_manifest(
            ACT_MANIFEST_FILES[expected_next_act - 1]
        ).act_manifest

        assert run_state.act == expected_next_act
        assert run_state.run_map.act == expected_next_act
        boss_node = run_state.run_map.get_node(run_state.run_map.boss_node_id)
        if manifest.map.layout == "boss_gauntlet":
            assert boss_node.depth == manifest.map.boss_count
            assert len(run_state.run_map.nodes) == manifest.map.boss_count
            assert {node.node_type for node in run_state.run_map.nodes.values()} == {"boss"}
        else:
            assert boss_node.depth == manifest.map.steps_before_boss + 1
        assert run_state.current_hp == run_state.character_class.max_hp
        assert run_state.card_reward_choices == manifest.rewards.card_choices
        assert run_state.current_node_id is None
        assert not run_state.is_complete()

    assert not has_next_act(run_state)

    run_state.completed_node_ids.append(run_state.run_map.boss_node_id)
    assert run_state.is_complete()
    assert not advance_to_next_act(run_state)


def test_late_act_catalogs_load_and_have_runtime_offer_sources() -> None:
    for manifest_path in [
        "data/acts/act_4_licensing_labyrinth.json",
        "data/acts/act_5_divine_ledger.json",
    ]:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        manifest = catalog.act_manifest
        assert manifest.act in {4, 5}
        assert catalog.card_database
        assert catalog.relic_database
        assert catalog.enemy_database
        assert catalog.encounter_database

        if manifest.id == "act_5_divine_ledger":
            assert manifest.map.layout == "boss_gauntlet"
            assert manifest.map.boss_count == 3
            assert len(manifest.map.boss_encounter_ids) >= manifest.map.boss_count
            assert manifest.event_files == []
            assert catalog.event_database == {}
            assert manifest.treasure.mimic_chance == 0
            assert manifest.treasure.mimic_encounter_id is None
            assert all(
                catalog.encounter_database[encounter_id].difficulty == "boss"
                for encounter_id in manifest.map.boss_encounter_ids
            )
            continue

        assert manifest.map.layout == "standard"
        assert manifest.map.steps_before_boss >= 17
        assert manifest.map.width >= 5
        assert manifest.map.first_elite_depth <= 3
        assert manifest.map.elite_weight_multiplier > 1
        assert catalog.event_database



def test_late_act_card_rewards_and_shops_are_available_for_each_class() -> None:
    for manifest_path in [
        "data/acts/act_4_licensing_labyrinth.json",
    ]:
        catalog = load_content_catalog_from_act_manifest(manifest_path)
        act = catalog.act_manifest.act

        for index, character_id in enumerate(sorted(CHARACTER_IDS)):
            reward_pool = build_card_reward_pool(
                catalog.card_database,
                card_class=character_id,
            )
            rewards = choose_card_rewards(
                catalog.card_database,
                Random(40_000 + act * 100 + index),
                count=3,
                card_class=character_id,
                act=act,
            )
            shop_cards = choose_shop_card_offers(
                catalog.card_database,
                Random(50_000 + act * 100 + index),
                card_class=character_id,
                act=act,
                fight_number=10,
                count=5,
            )
            shop_relics = choose_shop_relic_offers(
                catalog.relic_database,
                owned_relics=[],
                rng=Random(60_000 + act * 100 + index),
                act=act,
                fight_number=10,
                card_class=character_id,
                count=3,
            )

            assert reward_pool
            assert rewards
            assert shop_cards
            assert shop_relics

            assert all(card.class_ == character_id for card in rewards)
            assert all(card.rarity != "epic" for card in rewards)
            assert all("transition_reward" not in card.tags for card in rewards)

            assert all(offer.card.class_ == character_id for offer in shop_cards)
            assert all(offer.card.rarity != "epic" for offer in shop_cards)

            for offer in shop_relics:
                relic = offer.relic
                assert relic.rarity != "boss"
                assert not relic.allowed_classes or character_id in relic.allowed_classes
