"""Step-by-step rollout tracing for policy diagnostics."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from bab.sim.agents import Policy
from bab.sim.rl_env import Action, Observation, RoguelikeEnv


def trace_policy_rollout(
    policy: Policy,
    *,
    policy_name: str | None = None,
    seed: int = 1,
    max_steps: int = 800,
    character_id: str | None = None,
) -> dict[str, Any]:
    name = policy_name or getattr(policy, "name", policy.__class__.__name__)
    env = RoguelikeEnv(seed=seed)
    observation = env.reset(seed=seed, character_id=character_id)
    steps: list[dict[str, Any]] = []
    total_reward = 0.0

    for step_index in range(max_steps):
        if observation.done:
            break
        action = policy.choose_action(observation)
        before = observation_snapshot(observation)
        action_info = action_summary(observation, action)
        result = env.step(action)
        after = observation_snapshot(result.observation)
        total_reward += result.reward
        steps.append(
            {
                "step": step_index + 1,
                "phase": observation.phase,
                "before": before,
                "action": action_info,
                "reward": result.reward,
                "damage_dealt_delta": damage_delta(before, after),
                "hp_lost_delta": max(0, before["hp"] - after["hp"]),
                "after": after,
                "done": result.done,
                "outcome": result.observation.outcome,
            }
        )
        observation = result.observation

    if not observation.done:
        env.done = True
        env.outcome = "truncated"
        env.phase = "terminal"
        observation = env.observation()

    assert env.run_state is not None
    return {
        "schema_version": 1,
        "policy": name,
        "seed": seed,
        "steps": steps,
        "summary": {
            "outcome": observation.outcome or "unknown",
            "steps": len(steps),
            "total_reward": total_reward,
            "completed_nodes": len(env.run_state.completed_node_ids),
            "fights_won": max(0, env.run_state.fight_number - 1),
            "gold": getattr(env.run_state, "gold", 0),
            "deck_size": len(env.run_state.run_deck),
            "relic_count": len(env.run_state.relics),
            "hp": observation.hp,
            "max_hp": observation.max_hp,
            "damage_dealt": getattr(env, "damage_dealt", 0),
            "damage_taken": getattr(env, "damage_taken", 0),
            "first_combat_damage_dealt": getattr(env, "first_combat_damage_dealt", 0),
            "first_combat_damage_taken": getattr(env, "first_combat_damage_taken", 0),
            "first_combat_turns": getattr(env, "first_combat_turns", 0),
            "first_combat_zero_damage": bool(
                getattr(env, "first_combat_zero_damage", False)
            ),
        },
    }


def trace_policies_for_seed(
    policies: dict[str, Policy],
    *,
    seed: int,
    max_steps: int = 800,
    character_id: str | None = None,
) -> dict[str, Any]:
    traces = {
        policy_name: trace_policy_rollout(
            policy,
            policy_name=policy_name,
            seed=seed,
            max_steps=max_steps,
            character_id=character_id,
        )
        for policy_name, policy in policies.items()
    }
    return {
        "schema_version": 1,
        "seed": seed,
        "traces": traces,
        "summary": {
            policy_name: trace["summary"] for policy_name, trace in traces.items()
        },
    }


def observation_snapshot(observation: Observation) -> dict[str, Any]:
    return {
        "phase": observation.phase,
        "hp": observation.hp,
        "max_hp": observation.max_hp,
        "gold": observation.gold,
        "deck_size": observation.deck_size,
        "relic_count": observation.relic_count,
        "completed_nodes": observation.completed_nodes,
        "current_node_id": observation.current_node_id,
        "current_node_type": observation.current_node_type,
        "available_map_node_ids": list(observation.available_map_node_ids),
        "available_map_node_types": list(observation.available_map_node_types),
        "combat_turn": observation.combat_turn,
        "energy": observation.energy,
        "hand_card_ids": list(observation.hand_card_ids),
        "hand_card_costs": list(observation.hand_card_costs),
        "enemy_ids": list(observation.enemy_ids),
        "enemy_hp": list(observation.enemy_hp),
        "enemy_block": list(observation.enemy_block),
        "enemy_intents": list(observation.enemy_intents),
        "incoming_damage": observation.incoming_damage,
        "reward_card_ids": list(observation.reward_card_ids),
        "done": observation.done,
        "outcome": observation.outcome,
    }


def action_summary(
    observation: Observation,
    action: Action,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "kind": action.kind,
        "index": action.index,
        "target_index": action.target_index,
    }
    if action.kind == "choose_map_node" and action.index is not None:
        if action.index < len(observation.available_map_node_ids):
            summary["node_id"] = observation.available_map_node_ids[action.index]
        if action.index < len(observation.available_map_node_types):
            summary["node_type"] = observation.available_map_node_types[action.index]
    elif action.kind == "play_card" and action.index is not None:
        if action.index < len(observation.hand_card_ids):
            summary["card_id"] = observation.hand_card_ids[action.index]
        if action.index < len(observation.hand_card_costs):
            summary["card_cost"] = observation.hand_card_costs[action.index]
        if (
            action.target_index is not None
            and action.target_index < len(observation.enemy_ids)
        ):
            summary["target_enemy_id"] = observation.enemy_ids[action.target_index]
            summary["target_enemy_hp"] = observation.enemy_hp[action.target_index]
            summary["target_enemy_block"] = observation.enemy_block[action.target_index]
    elif action.kind == "choose_card_reward" and action.index is not None:
        if action.index < len(observation.reward_card_ids):
            summary["card_id"] = observation.reward_card_ids[action.index]
    return summary


def damage_delta(before: dict[str, Any], after: dict[str, Any]) -> int:
    before_hp = sum(int(value) for value in before.get("enemy_hp", []))
    after_hp = sum(int(value) for value in after.get("enemy_hp", []))
    return max(0, before_hp - after_hp)


def write_trace_json(
    trace: dict[str, Any],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(trace, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def write_trace_csv(
    trace: dict[str, Any],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = flatten_trace_rows(trace)
    fieldnames = collect_fieldnames(rows)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def write_trace_bundle(
    trace: dict[str, Any],
    output_dir: str | Path,
    *,
    stem: str,
) -> tuple[Path, Path]:
    output_directory = Path(output_dir)
    return (
        write_trace_json(trace, output_directory / f"{stem}.json"),
        write_trace_csv(trace, output_directory / f"{stem}.csv"),
    )


def flatten_trace_rows(trace: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seed = trace["seed"]
    for policy_name, policy_trace in trace["traces"].items():
        summary = policy_trace["summary"]
        for step in policy_trace["steps"]:
            before = step["before"]
            after = step["after"]
            action = step["action"]
            rows.append(
                {
                    "seed": seed,
                    "policy": policy_name,
                    "step": step["step"],
                    "phase": step["phase"],
                    "before_hp": before["hp"],
                    "before_gold": before["gold"],
                    "before_deck_size": before["deck_size"],
                    "before_relic_count": before["relic_count"],
                    "before_current_node_type": before["current_node_type"],
                    "before_energy": before["energy"],
                    "before_incoming_damage": before["incoming_damage"],
                    "before_hand": "|".join(before["hand_card_ids"]),
                    "before_enemy_ids": "|".join(before["enemy_ids"]),
                    "before_enemy_hp": "|".join(str(value) for value in before["enemy_hp"]),
                    "before_enemy_intents": "|".join(before["enemy_intents"]),
                    "before_reward_cards": "|".join(before["reward_card_ids"]),
                    "before_map_node_types": "|".join(before["available_map_node_types"]),
                    "action_kind": action.get("kind"),
                    "action_index": action.get("index"),
                    "action_target_index": action.get("target_index"),
                    "action_card_id": action.get("card_id"),
                    "action_card_cost": action.get("card_cost"),
                    "action_node_type": action.get("node_type"),
                    "action_node_id": action.get("node_id"),
                    "action_target_enemy_id": action.get("target_enemy_id"),
                    "reward": step["reward"],
                    "damage_dealt_delta": step.get("damage_dealt_delta", 0),
                    "hp_lost_delta": step.get("hp_lost_delta", 0),
                    "after_phase": after["phase"],
                    "after_hp": after["hp"],
                    "after_gold": after["gold"],
                    "after_energy": after["energy"],
                    "done": step["done"],
                    "step_outcome": step["outcome"],
                    "final_outcome": summary["outcome"],
                    "final_total_reward": summary["total_reward"],
                    "final_completed_nodes": summary["completed_nodes"],
                    "final_fights_won": summary["fights_won"],
                    "final_damage_dealt": summary.get("damage_dealt", 0),
                    "final_damage_taken": summary.get("damage_taken", 0),
                    "final_first_combat_damage_dealt": summary.get("first_combat_damage_dealt", 0),
                    "final_first_combat_damage_taken": summary.get("first_combat_damage_taken", 0),
                    "final_first_combat_turns": summary.get("first_combat_turns", 0),
                    "final_first_combat_zero_damage": summary.get("first_combat_zero_damage", False),
                }
            )
    return rows


def collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["seed", "policy"]
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def format_trace_summary(trace: dict[str, Any]) -> str:
    lines = [
        "=== Trace Summary ===",
        f"Seed: {trace['seed']}",
    ]
    for policy_name, summary in trace["summary"].items():
        lines.append("")
        lines.append(f"Policy: {policy_name}")
        lines.append(f"Outcome: {summary['outcome']}")
        lines.append(f"Steps: {summary['steps']}")
        lines.append(f"Total reward: {summary['total_reward']:.2f}")
        lines.append(f"Completed nodes: {summary['completed_nodes']}")
        lines.append(f"Fights won: {summary['fights_won']}")
        lines.append(f"Final HP: {summary['hp']}/{summary['max_hp']}")
        lines.append(f"Gold: {summary['gold']}")
        lines.append(f"Deck size: {summary['deck_size']}")
        lines.append(f"Relics: {summary['relic_count']}")
        lines.append(f"Damage dealt: {summary.get('damage_dealt', 0)}")
        lines.append(f"Damage taken: {summary.get('damage_taken', 0)}")
        lines.append(
            "First combat: "
            f"damage_dealt={summary.get('first_combat_damage_dealt', 0)}, "
            f"damage_taken={summary.get('first_combat_damage_taken', 0)}, "
            f"turns={summary.get('first_combat_turns', 0)}, "
            f"zero_damage={summary.get('first_combat_zero_damage', False)}"
        )
    return "\n".join(lines)
