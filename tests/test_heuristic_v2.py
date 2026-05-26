from bab.sim.heuristic_v2 import HeuristicV2Policy
from bab.sim.rl_env import RoguelikeEnv


def test_heuristic_v2_returns_legal_actions_over_steps() -> None:
    env = RoguelikeEnv(seed=22)
    observation = env.reset(seed=22, character_id="bureaucrat")
    policy = HeuristicV2Policy(seed=22)

    for _ in range(80):
        if observation.done:
            break
        action = policy.choose_action(observation)
        assert action in observation.legal_actions
        observation = env.step(action).observation


def test_heuristic_v2_rollout_reaches_valid_terminal_or_progress_state() -> None:
    env = RoguelikeEnv(seed=23)
    observation = env.reset(seed=23, character_id="hedge_witch")
    policy = HeuristicV2Policy(seed=23)

    for _ in range(250):
        if observation.done:
            break
        action = policy.choose_action(observation)
        assert action in observation.legal_actions
        observation = env.step(action).observation

    assert observation.act >= 1
    assert observation.deck_size > 0
    assert observation.outcome in {None, "win", "defeat", "stalled", "truncated"}
