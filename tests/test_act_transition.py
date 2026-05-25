from random import Random

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.run.state import create_new_run
from bab.systems.act_progression import advance_to_next_act, has_next_act
from bab.systems.rewards import (
    build_card_reward_pool,
    choose_epic_card_rewards,
)


def make_act_1_run():
    catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")
    character_class = catalog.character_classes["bureaucrat"]
    return create_new_run(
        character_class=character_class,
        card_database=catalog.card_database,
        enemy_database=catalog.enemy_database,
        encounter_database=catalog.encounter_database,
        status_database=catalog.status_database,
        event_database=catalog.event_database,
        relic_database=catalog.relic_database,
        rng=Random(1),
        act=catalog.act_manifest.act,
        max_fights=99,
        map_steps_before_boss=catalog.act_manifest.map.steps_before_boss,
        map_width=catalog.act_manifest.map.width,
        mimic_chance=catalog.act_manifest.treasure.mimic_chance,
        treasure_mimic_encounter_id=catalog.act_manifest.treasure.mimic_encounter_id,
        waiting_room_heal_percent=catalog.act_manifest.waiting_room.heal_percent,
    )


def test_epic_cards_are_loaded_but_excluded_from_normal_rewards() -> None:
    catalog = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")

    normal_rewards = build_card_reward_pool(
        catalog.card_database,
        card_class="bureaucrat",
    )
    assert normal_rewards
    assert all(card.rarity != "epic" for card in normal_rewards)

    epic_rewards = choose_epic_card_rewards(
        catalog.card_database,
        Random(1),
        count=3,
        card_class="bureaucrat",
    )
    assert len(epic_rewards) == 3
    assert all(card.rarity == "epic" for card in epic_rewards)
    assert all(card.class_ == "bureaucrat" for card in epic_rewards)


def test_advance_to_act_2_preserves_deck_and_fully_heals() -> None:
    run_state = make_act_1_run()
    run_state.current_hp = 1

    epic_reward = choose_epic_card_rewards(
        run_state.card_database,
        run_state.rng,
        count=3,
        card_class=run_state.character_class.id,
    )[0]
    run_state.run_deck.append(epic_reward)

    run_state.completed_node_ids.append(run_state.run_map.boss_node_id)
    assert run_state.is_complete()
    assert has_next_act(run_state)

    advanced = advance_to_next_act(run_state)

    assert advanced
    assert run_state.act == 2
    assert run_state.run_map.act == 2
    assert run_state.run_map.boss_node_id == "act_2_boss"
    assert run_state.current_node_id is None
    assert run_state.current_hp == run_state.character_class.max_hp
    assert not run_state.is_complete()
    assert epic_reward.id in [card.id for card in run_state.run_deck]
    assert epic_reward.id in run_state.card_database
    assert run_state.treasure_mimic_encounter_id == "archive_mimic_01"
    assert run_state.mimic_chance == 0.05


def test_advance_to_act_3_uses_green_docket_runtime_config() -> None:
    run_state = make_act_1_run()

    assert advance_to_next_act(run_state)
    assert run_state.act == 2
    assert has_next_act(run_state)

    run_state.current_hp = 1
    epic_reward = choose_epic_card_rewards(
        run_state.card_database,
        run_state.rng,
        count=3,
        card_class=run_state.character_class.id,
    )[0]
    run_state.run_deck.append(epic_reward)
    run_state.completed_node_ids.append(run_state.run_map.boss_node_id)

    assert run_state.is_complete()

    advanced = advance_to_next_act(run_state)

    assert advanced
    assert run_state.act == 3
    assert run_state.run_map.act == 3
    assert run_state.run_map.boss_node_id == "act_3_boss"
    assert run_state.run_map.get_node("act_3_boss").depth == 18
    assert run_state.current_node_id is None
    assert run_state.current_hp == run_state.character_class.max_hp
    assert not run_state.is_complete()
    assert epic_reward.id in [card.id for card in run_state.run_deck]
    assert run_state.treasure_mimic_encounter_id == "act_3_elite_02"
    assert run_state.mimic_chance == 0.10
