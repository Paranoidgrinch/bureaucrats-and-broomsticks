from bab.sim.rl_env import Action, RoguelikeEnv


def test_observation_exposes_relic_ids_and_empty_noncombat_status_features() -> None:
    env = RoguelikeEnv(seed=101)
    observation = env.reset(seed=101, character_id="bureaucrat")

    assert observation.phase == "map"
    assert observation.relic_ids == ()
    assert observation.player_status_ids == ()
    assert observation.player_status_amounts == ()
    assert observation.enemy_status_ids == ()
    assert observation.enemy_status_amounts == ()
    assert observation.draw_pile_size == 0
    assert observation.discard_pile_size == 0
    assert observation.exhaust_pile_size == 0


def test_observation_exposes_combat_statuses_and_pile_sizes() -> None:
    env = RoguelikeEnv(seed=102)
    observation = env.reset(seed=102, character_id="bureaucrat")

    map_action = next(action for action in observation.legal_actions if action.kind == "choose_map_node")
    observation = env.step(map_action).observation

    assert observation.phase == "combat"
    assert env.combat_state is not None

    env.combat_state.player.apply_status("paperwork", 3)
    env.combat_state.enemies[0].apply_status("paperwork", 4)
    env.combat_state.discard_pile.extend(env.combat_state.hand[:1])

    observation = env.observation()

    assert "paperwork" in observation.player_status_ids
    player_index = observation.player_status_ids.index("paperwork")
    assert observation.player_status_amounts[player_index] == 3

    assert observation.enemy_status_ids
    assert "paperwork" in observation.enemy_status_ids[0]
    enemy_index = observation.enemy_status_ids[0].index("paperwork")
    assert observation.enemy_status_amounts[0][enemy_index] == 4

    assert observation.draw_pile_size >= 0
    assert observation.discard_pile_size >= 1
    assert observation.exhaust_pile_size >= 0
