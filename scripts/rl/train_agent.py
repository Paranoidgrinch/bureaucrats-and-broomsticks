from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bab.sim.agents import (  # noqa: E402
    HeuristicPolicy,
    RandomPolicy,
    compare_policies,
    summarize_policy_results,
)
from bab.sim.metrics import write_results_bundle  # noqa: E402
from bab.sim.q_learning import (  # noqa: E402
    QLearningConfig,
    train_q_learning_agent,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate a dependency-free Q-learning agent."
    )
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--imitation-episodes", type=int, default=250)
    parser.add_argument("--eval-runs", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--character-id", type=str, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "rl_training",
    )
    parser.add_argument("--alpha", type=float, default=0.15)
    parser.add_argument("--gamma", type=float, default=0.96)
    parser.add_argument("--epsilon-start", type=float, default=0.45)
    parser.add_argument("--epsilon-end", type=float, default=0.04)
    parser.add_argument("--epsilon-decay-episodes", type=int, default=350)
    parser.add_argument("--heuristic-explore-probability", type=float, default=0.75)
    parser.add_argument("--heuristic-tiebreak-margin", type=float, default=0.10)
    parser.add_argument("--imitation-bonus", type=float, default=5.0)
    parser.add_argument("--imitation-margin", type=float, default=1.0)
    parser.add_argument(
        "--disable-risk-aware-fallback",
        action="store_true",
        help="Disable HP-aware conservative fallback during greedy evaluation.",
    )
    parser.add_argument("--low-hp-fallback-ratio", type=float, default=0.35)
    parser.add_argument("--medium-hp-fallback-ratio", type=float, default=0.55)
    parser.add_argument("--low-hp-fallback-margin", type=float, default=6.0)
    parser.add_argument("--medium-hp-fallback-margin", type=float, default=2.0)
    parser.add_argument("--card-reward-fallback-margin", type=float, default=0.75)
    parser.add_argument("--map-fallback-margin", type=float, default=0.50)
    parser.add_argument(
        "--no-heuristic-guidance",
        action="store_true",
        help="Disable heuristic-guided exploration and tie-breaking.",
    )
    args = parser.parse_args()

    config = QLearningConfig(
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
        heuristic_explore_probability=args.heuristic_explore_probability,
        heuristic_tiebreak_margin=args.heuristic_tiebreak_margin,
        imitation_bonus=args.imitation_bonus,
        imitation_margin=args.imitation_margin,
        risk_aware_fallback=not args.disable_risk_aware_fallback,
        low_hp_fallback_ratio=args.low_hp_fallback_ratio,
        medium_hp_fallback_ratio=args.medium_hp_fallback_ratio,
        low_hp_fallback_margin=args.low_hp_fallback_margin,
        medium_hp_fallback_margin=args.medium_hp_fallback_margin,
        card_reward_fallback_margin=args.card_reward_fallback_margin,
        map_fallback_margin=args.map_fallback_margin,
    )

    training = train_q_learning_agent(
        episodes=args.episodes,
        imitation_episodes=args.imitation_episodes,
        seed=args.seed,
        max_steps=args.max_steps,
        character_id=args.character_id,
        config=config,
        use_heuristic_guidance=not args.no_heuristic_guidance,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    model_path = training.policy.save(args.out_dir / "q_learning_agent.json")
    train_results = {}
    if training.imitation_results:
        train_results["q_learning_imitation"] = training.imitation_results
    train_results["q_learning_train"] = training.episode_results

    train_json, train_csv = write_results_bundle(
        train_results,
        args.out_dir,
        stem="q_learning_training",
    )

    policies = [
        RandomPolicy(seed=args.seed),
        HeuristicPolicy(seed=args.seed),
        training.policy,
    ]
    evaluation = compare_policies(
        policies,
        runs=args.eval_runs,
        seed=args.seed + 10_000,
        max_steps=args.max_steps,
        character_id=args.character_id,
    )
    eval_json, eval_csv = write_results_bundle(
        evaluation,
        args.out_dir,
        stem="q_learning_evaluation",
    )

    print("=== Q-Learning Training Complete ===")
    print(f"Imitation episodes: {args.imitation_episodes}")
    print(f"RL episodes: {args.episodes}")
    print(f"Heuristic guidance: {not args.no_heuristic_guidance}")
    print(f"Risk-aware fallback: {not args.disable_risk_aware_fallback}")
    print(f"Q-table entries: {len(training.policy.q_table)}")
    print(f"Model: {model_path}")
    print(f"Training JSON: {train_json}")
    print(f"Training CSV:  {train_csv}")
    print("")
    print(summarize_policy_results(evaluation))
    print("")
    print("Saved evaluation exports:")
    print(f"  JSON: {eval_json}")
    print(f"  CSV:  {eval_csv}")


if __name__ == "__main__":
    main()
