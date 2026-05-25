from bab.sim.rl_env import RoguelikeEnv


def test_rl_env_completed_act_advances_campaign_until_act_5_win() -> None:
    env = RoguelikeEnv(seed=123)
    observation = env.reset(character_id="bureaucrat")

    assert observation.act == 1
    assert not observation.done

    for expected_next_act in [2, 3, 4, 5]:
        assert env.run_state is not None
        env.run_state.completed_node_ids.append(env.run_state.run_map.boss_node_id)
        env._sync_terminal_state()

        observation = env.observation()
        assert not observation.done
        assert observation.act == expected_next_act
        assert env.max_act_seen == expected_next_act

    assert env.run_state is not None
    env.run_state.completed_node_ids.append(env.run_state.run_map.boss_node_id)
    env._sync_terminal_state()

    observation = env.observation()
    assert observation.done
    assert observation.outcome == "win"
    assert observation.act == 5
    assert env.max_act_seen == 5
