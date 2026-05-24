from bab.sim.agents import HeuristicPolicy
from bab.sim.linear_q import (
    LinearQPolicy,
    checkpoint_train_linear_class_runner,
    linear_features,
    train_linear_policy_chunk,
)
from bab.sim.rl_env import RoguelikeEnv


def test_linear_q_policy_returns_legal_action() -> None:
    env = RoguelikeEnv(seed=1)
    observation = env.reset(character_id="hedge_witch")

    policy = LinearQPolicy(seed=1, fallback_policy=HeuristicPolicy(seed=1))
    action = policy.choose_action(observation)

    assert action in observation.legal_actions


def test_linear_q_update_changes_weights() -> None:
    env = RoguelikeEnv(seed=2)
    observation = env.reset(character_id="hedge_witch")

    policy = LinearQPolicy(seed=2, fallback_policy=HeuristicPolicy(seed=2))
    action = policy.choose_action(observation)
    result = env.step(action)

    before = dict(policy.weights)
    policy.update(observation, action, result.reward, result.observation, result.done)

    assert policy.weights != before


def test_linear_features_are_non_empty() -> None:
    env = RoguelikeEnv(seed=3)
    observation = env.reset(character_id="hedge_witch")
    action = observation.legal_actions[0]

    features = linear_features(observation, action)

    assert features
    assert "bias" in features


def test_train_linear_policy_chunk_smoke() -> None:
    policy = LinearQPolicy(seed=4, fallback_policy=HeuristicPolicy(seed=4))
    results = train_linear_policy_chunk(
        policy,
        character_id="hedge_witch",
        seed=4,
        start_episode=0,
        episodes=1,
        max_steps=60,
    )

    assert len(results) == 1
    assert policy.weights


def test_linear_save_load_roundtrip(tmp_path) -> None:
    policy = LinearQPolicy(seed=5, fallback_policy=HeuristicPolicy(seed=5))
    env = RoguelikeEnv(seed=5)
    observation = env.reset(character_id="hedge_witch")
    action = policy.choose_action(observation)
    result = env.step(action)
    policy.update(observation, action, result.reward, result.observation, result.done)

    path = policy.save(tmp_path / "linear.json")
    loaded = LinearQPolicy.load(path, seed=5)

    assert loaded.weights == policy.weights
    assert loaded.config.alpha == policy.config.alpha


def test_checkpoint_train_linear_class_runner_smoke(tmp_path) -> None:
    result = checkpoint_train_linear_class_runner(
        character_id="hedge_witch",
        output_dir=tmp_path,
        seed=6,
        episodes=1,
        minutes=None,
        checkpoint_interval=1,
        eval_runs=1,
        max_steps=60,
        imitation_episodes=1,
    )

    assert result["character_id"] == "hedge_witch"
    assert result["weight_count"] > 0
    assert (tmp_path / "hedge_witch" / "best_linear_q_agent.json").exists()
