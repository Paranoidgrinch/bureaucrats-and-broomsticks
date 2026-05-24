from bab.sim.agents import HeuristicPolicy
from bab.sim.q_learning import (
    QLearningPolicy,
    abstract_action_key,
    abstract_state_key,
    pretrain_from_policy_demonstrations,
    train_q_learning_agent,
)
from bab.sim.rl_env import RoguelikeEnv


def test_q_learning_policy_returns_legal_action() -> None:
    env = RoguelikeEnv(seed=1)
    observation = env.reset()

    policy = QLearningPolicy(seed=1)
    action = policy.choose_action(observation)

    assert action in observation.legal_actions


def test_guided_q_learning_policy_returns_legal_action() -> None:
    env = RoguelikeEnv(seed=11)
    observation = env.reset()

    policy = QLearningPolicy(
        seed=11,
        fallback_policy=HeuristicPolicy(seed=11),
    )
    action = policy.choose_action(observation)

    assert action in observation.legal_actions


def test_q_learning_update_changes_q_value() -> None:
    env = RoguelikeEnv(seed=2)
    observation = env.reset()

    policy = QLearningPolicy(seed=2)
    action = policy.choose_action(observation)
    before = policy.q_value(observation, action)

    result = env.step(action)
    policy.update(
        observation,
        action,
        result.reward,
        result.observation,
        result.done,
    )

    after = policy.q_value(observation, action)
    assert after != before


def test_q_learning_imitation_update_changes_q_value() -> None:
    env = RoguelikeEnv(seed=12)
    observation = env.reset()

    policy = QLearningPolicy(seed=12)
    expert = HeuristicPolicy(seed=12)
    action = expert.choose_action(observation)

    before = policy.q_value(observation, action)
    policy.imitation_update(observation, action)
    after = policy.q_value(observation, action)

    assert after > before


def test_q_learning_training_smoke_test() -> None:
    result = train_q_learning_agent(
        episodes=2,
        imitation_episodes=1,
        seed=3,
        max_steps=80,
    )

    assert len(result.episode_results) == 2
    assert len(result.imitation_results) == 1
    assert result.policy.q_table
    assert all(episode.steps > 0 for episode in result.episode_results)


def test_q_learning_pretraining_smoke_test() -> None:
    learner = QLearningPolicy(
        seed=13,
        fallback_policy=HeuristicPolicy(seed=13),
    )
    teacher = HeuristicPolicy(seed=13)

    results = pretrain_from_policy_demonstrations(
        learner,
        teacher,
        episodes=1,
        seed=13,
        max_steps=80,
    )

    assert len(results) == 1
    assert learner.q_table
    assert results[0].steps > 0


def test_q_learning_save_load_roundtrip(tmp_path) -> None:
    training = train_q_learning_agent(
        episodes=2,
        imitation_episodes=1,
        seed=4,
        max_steps=80,
    )
    model_path = training.policy.save(tmp_path / "q_agent.json")

    loaded = QLearningPolicy.load(model_path, seed=4)

    assert loaded.q_table == training.policy.q_table
    assert loaded.config.alpha == training.policy.config.alpha
    assert loaded.fallback_policy is not None


def test_q_learning_can_load_without_guidance(tmp_path) -> None:
    training = train_q_learning_agent(
        episodes=2,
        imitation_episodes=1,
        seed=14,
        max_steps=80,
    )
    model_path = training.policy.save(tmp_path / "q_agent.json")

    loaded = QLearningPolicy.load(
        model_path,
        seed=14,
        use_heuristic_guidance=False,
    )

    assert loaded.q_table == training.policy.q_table
    assert loaded.fallback_policy is None


def test_state_and_action_abstractions_are_hashable_like() -> None:
    env = RoguelikeEnv(seed=5)
    observation = env.reset()
    action = observation.legal_actions[0]

    state_key = abstract_state_key(observation)
    action_key = abstract_action_key(observation, action)

    assert isinstance(state_key, tuple)
    assert isinstance(action_key, tuple)


def test_q_learning_risk_aware_fallback_margin_changes_with_hp() -> None:
    env = RoguelikeEnv(seed=21)
    observation = env.reset()

    policy = QLearningPolicy(
        seed=21,
        fallback_policy=HeuristicPolicy(seed=21),
    )

    high_hp_margin = policy._fallback_margin_for_observation(observation)

    observation.hp = max(1, int(observation.max_hp * 0.20))
    low_hp_margin = policy._fallback_margin_for_observation(observation)

    assert low_hp_margin > high_hp_margin
    assert low_hp_margin >= policy.config.low_hp_fallback_margin
