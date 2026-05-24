from bab.sim.card_features import safe_load_default_card_feature_index
from bab.sim.q_learning import abstract_action_key, abstract_state_key, card_collection_profile
from bab.sim.rl_env import RoguelikeEnv


def test_observation_contains_deck_ids_and_combat_intent_fields() -> None:
    env = RoguelikeEnv(seed=1)
    observation = env.reset(character_id="hedge_witch")

    assert observation.deck_card_ids
    assert hasattr(observation, "incoming_damage")
    assert hasattr(observation, "enemy_intents")


def test_q_state_uses_deck_profile_without_crashing() -> None:
    env = RoguelikeEnv(seed=2)
    observation = env.reset(character_id="hedge_witch")
    features = safe_load_default_card_feature_index()

    state = abstract_state_key(observation, features)

    assert isinstance(state, tuple)
    assert card_collection_profile(observation.deck_card_ids, features)


def test_q_action_uses_card_quality_without_crashing() -> None:
    env = RoguelikeEnv(seed=3)
    observation = env.reset(character_id="hedge_witch")
    features = safe_load_default_card_feature_index()

    action = observation.legal_actions[0]
    action_key = abstract_action_key(observation, action, features)

    assert isinstance(action_key, tuple)
