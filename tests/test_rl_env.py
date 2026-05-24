from bab.sim.rl_env import Action, RoguelikeEnv, rollout_random_policy


def test_rl_env_can_reset() -> None:
    env = RoguelikeEnv(seed=123)
    observation = env.reset()

    assert observation.phase in {"map", "terminal"}
    assert observation.character_id
    assert observation.hp > 0
    assert observation.max_hp >= observation.hp
    assert observation.legal_actions


def test_rl_env_can_step_multiple_times() -> None:
    env = RoguelikeEnv(seed=123)
    observation = env.reset()

    rewards = []
    for _ in range(40):
        if observation.done:
            break
        result = env.step(env.sample_action(observation))
        observation = result.observation
        rewards.append(result.reward)

    assert rewards
    assert all(isinstance(reward, float) for reward in rewards)


def test_rl_env_random_policy_rollout_does_not_crash() -> None:
    result = rollout_random_policy(seed=123, max_steps=300)

    assert result.steps > 0
    assert result.outcome in {"win", "defeat", "stalled", "truncated"}
    assert result.completed_nodes >= 0
    assert result.deck_size > 0


def test_rl_env_rewards_are_non_zero_during_rollout() -> None:
    env = RoguelikeEnv(seed=7)
    observation = env.reset()

    rewards = []
    for _ in range(120):
        if observation.done:
            break
        result = env.step(env.sample_action(observation))
        observation = result.observation
        rewards.append(result.reward)

    assert rewards
    assert any(reward != 0.0 for reward in rewards)


def test_rl_env_invalid_action_is_penalized_without_crashing() -> None:
    env = RoguelikeEnv(seed=123)
    observation = env.reset()

    result = env.step(Action("definitely_not_legal"))

    assert result.observation.phase == observation.phase
    assert result.reward < 0
    assert "invalid_action" in result.info