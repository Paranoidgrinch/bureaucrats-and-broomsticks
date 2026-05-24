"""Analysis helpers for policy trace JSON files."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any


def load_trace(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze_trace_difference(
    trace: dict[str, Any],
    *,
    baseline_policy: str = "heuristic",
    challenger_policy: str = "q_learning",
    max_differences: int = 20,
) -> dict[str, Any]:
    traces = trace["traces"]
    if baseline_policy not in traces:
        raise KeyError(f"Baseline policy not found in trace: {baseline_policy}")
    if challenger_policy not in traces:
        raise KeyError(f"Challenger policy not found in trace: {challenger_policy}")

    baseline_trace = traces[baseline_policy]
    challenger_trace = traces[challenger_policy]

    baseline_steps = baseline_trace["steps"]
    challenger_steps = challenger_trace["steps"]

    differences = find_action_differences(
        baseline_steps,
        challenger_steps,
        max_differences=max_differences,
    )

    return {
        "schema_version": 1,
        "seed": trace["seed"],
        "baseline_policy": baseline_policy,
        "challenger_policy": challenger_policy,
        "baseline_summary": baseline_trace["summary"],
        "challenger_summary": challenger_trace["summary"],
        "first_difference": differences[0] if differences else None,
        "differences": differences,
        "baseline_action_counts": action_counts(baseline_steps),
        "challenger_action_counts": action_counts(challenger_steps),
        "baseline_map_path": map_path(baseline_steps),
        "challenger_map_path": map_path(challenger_steps),
        "baseline_card_rewards": card_reward_choices(baseline_steps),
        "challenger_card_rewards": card_reward_choices(challenger_steps),
        "baseline_final_actions": final_action_window(baseline_steps),
        "challenger_final_actions": final_action_window(challenger_steps),
    }


def find_action_differences(
    baseline_steps: list[dict[str, Any]],
    challenger_steps: list[dict[str, Any]],
    *,
    max_differences: int = 20,
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    shared_length = min(len(baseline_steps), len(challenger_steps))

    for index in range(shared_length):
        baseline_step = baseline_steps[index]
        challenger_step = challenger_steps[index]

        baseline_signature = action_signature(baseline_step["action"])
        challenger_signature = action_signature(challenger_step["action"])

        if (
            baseline_step["phase"] != challenger_step["phase"]
            or baseline_signature != challenger_signature
        ):
            differences.append(
                {
                    "step": index + 1,
                    "baseline_phase": baseline_step["phase"],
                    "challenger_phase": challenger_step["phase"],
                    "baseline_action": action_label(baseline_step["action"]),
                    "challenger_action": action_label(challenger_step["action"]),
                    "baseline_context": compact_context(baseline_step["before"]),
                    "challenger_context": compact_context(challenger_step["before"]),
                    "baseline_reward": baseline_step["reward"],
                    "challenger_reward": challenger_step["reward"],
                }
            )

            if len(differences) >= max_differences:
                break

    if len(baseline_steps) != len(challenger_steps) and len(differences) < max_differences:
        differences.append(
            {
                "step": shared_length + 1,
                "baseline_phase": "trace_ended" if shared_length >= len(baseline_steps) else baseline_steps[shared_length]["phase"],
                "challenger_phase": "trace_ended" if shared_length >= len(challenger_steps) else challenger_steps[shared_length]["phase"],
                "baseline_action": "trace_ended" if shared_length >= len(baseline_steps) else action_label(baseline_steps[shared_length]["action"]),
                "challenger_action": "trace_ended" if shared_length >= len(challenger_steps) else action_label(challenger_steps[shared_length]["action"]),
                "baseline_context": {},
                "challenger_context": {},
                "baseline_reward": None,
                "challenger_reward": None,
            }
        )

    return differences


def action_signature(action: dict[str, Any]) -> tuple[Any, ...]:
    kind = action.get("kind")

    if kind == "choose_map_node":
        return (
            kind,
            action.get("node_type"),
            action.get("node_id"),
        )

    if kind == "play_card":
        return (
            kind,
            action.get("card_id"),
            action.get("target_enemy_id"),
        )

    if kind == "choose_card_reward":
        return (
            kind,
            action.get("card_id"),
        )

    return (kind,)


def action_label(action: dict[str, Any]) -> str:
    kind = action.get("kind")

    if kind == "choose_map_node":
        return (
            f"choose_map_node:{action.get('node_type')}"
            f"[{action.get('node_id')}]"
        )

    if kind == "play_card":
        target = action.get("target_enemy_id")
        if target is None:
            return f"play_card:{action.get('card_id')}"
        return f"play_card:{action.get('card_id')} -> {target}"

    if kind == "choose_card_reward":
        return f"choose_card_reward:{action.get('card_id')}"

    return str(kind)


def compact_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": snapshot.get("phase"),
        "hp": snapshot.get("hp"),
        "max_hp": snapshot.get("max_hp"),
        "gold": snapshot.get("gold"),
        "deck_size": snapshot.get("deck_size"),
        "relic_count": snapshot.get("relic_count"),
        "current_node_type": snapshot.get("current_node_type"),
        "energy": snapshot.get("energy"),
        "hand": snapshot.get("hand_card_ids", []),
        "enemy_ids": snapshot.get("enemy_ids", []),
        "enemy_hp": snapshot.get("enemy_hp", []),
        "reward_cards": snapshot.get("reward_card_ids", []),
        "map_options": snapshot.get("available_map_node_types", []),
    }


def action_counts(steps: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()

    for step in steps:
        action = step["action"]
        kind = action.get("kind")
        counts[str(kind)] += 1

        if kind == "play_card":
            card_id = action.get("card_id")
            if card_id:
                counts[f"play_card:{card_id}"] += 1

        elif kind == "choose_card_reward":
            card_id = action.get("card_id")
            if card_id:
                counts[f"reward:{card_id}"] += 1

        elif kind == "choose_map_node":
            node_type = action.get("node_type")
            if node_type:
                counts[f"map:{node_type}"] += 1

    return dict(counts)


def map_path(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path: list[dict[str, Any]] = []

    for step in steps:
        action = step["action"]
        if action.get("kind") == "choose_map_node":
            path.append(
                {
                    "step": step["step"],
                    "node_type": action.get("node_type"),
                    "node_id": action.get("node_id"),
                    "hp_before": step["before"]["hp"],
                    "hp_after": step["after"]["hp"],
                    "reward": step["reward"],
                }
            )

    return path


def card_reward_choices(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    choices: list[dict[str, Any]] = []

    for step in steps:
        action = step["action"]
        if action.get("kind") in {"choose_card_reward", "skip_card_reward"}:
            choices.append(
                {
                    "step": step["step"],
                    "choice": action_label(action),
                    "options": step["before"].get("reward_card_ids", []),
                    "deck_size_before": step["before"].get("deck_size"),
                    "deck_size_after": step["after"].get("deck_size"),
                    "reward": step["reward"],
                }
            )

    return choices


def final_action_window(
    steps: list[dict[str, Any]],
    *,
    size: int = 12,
) -> list[dict[str, Any]]:
    window = steps[-size:]
    return [
        {
            "step": step["step"],
            "phase": step["phase"],
            "hp_before": step["before"]["hp"],
            "energy_before": step["before"]["energy"],
            "enemy_hp_before": step["before"]["enemy_hp"],
            "action": action_label(step["action"]),
            "reward": step["reward"],
            "hp_after": step["after"]["hp"],
            "after_phase": step["after"]["phase"],
            "outcome": step["outcome"],
        }
        for step in window
    ]


def format_trace_difference_analysis(
    analysis: dict[str, Any],
) -> str:
    baseline = analysis["baseline_policy"]
    challenger = analysis["challenger_policy"]
    baseline_summary = analysis["baseline_summary"]
    challenger_summary = analysis["challenger_summary"]

    lines = [
        "=== Trace Difference Analysis ===",
        f"Seed: {analysis['seed']}",
        "",
        f"{baseline}: {baseline_summary['outcome']} | "
        f"reward {baseline_summary['total_reward']:.2f} | "
        f"steps {baseline_summary['steps']} | "
        f"fights {baseline_summary['fights_won']} | "
        f"nodes {baseline_summary['completed_nodes']} | "
        f"HP {baseline_summary['hp']}/{baseline_summary['max_hp']}",
        f"{challenger}: {challenger_summary['outcome']} | "
        f"reward {challenger_summary['total_reward']:.2f} | "
        f"steps {challenger_summary['steps']} | "
        f"fights {challenger_summary['fights_won']} | "
        f"nodes {challenger_summary['completed_nodes']} | "
        f"HP {challenger_summary['hp']}/{challenger_summary['max_hp']}",
        "",
    ]

    first_difference = analysis["first_difference"]
    if first_difference is None:
        lines.append("No action difference found before trace end.")
    else:
        lines.extend(
            [
                "=== First divergent decision ===",
                f"Step: {first_difference['step']}",
                f"{baseline}: {first_difference['baseline_phase']} | "
                f"{first_difference['baseline_action']} | "
                f"reward {first_difference['baseline_reward']}",
                f"{challenger}: {first_difference['challenger_phase']} | "
                f"{first_difference['challenger_action']} | "
                f"reward {first_difference['challenger_reward']}",
                "",
                f"{baseline} context: {format_context(first_difference['baseline_context'])}",
                f"{challenger} context: {format_context(first_difference['challenger_context'])}",
            ]
        )

    lines.append("")
    lines.append("=== Map paths ===")
    lines.append(f"{baseline}: {format_map_path(analysis['baseline_map_path'])}")
    lines.append(f"{challenger}: {format_map_path(analysis['challenger_map_path'])}")

    lines.append("")
    lines.append("=== Card reward choices ===")
    lines.append(f"{baseline}: {format_reward_choices(analysis['baseline_card_rewards'])}")
    lines.append(f"{challenger}: {format_reward_choices(analysis['challenger_card_rewards'])}")

    lines.append("")
    lines.append("=== Final action window ===")
    lines.append(f"{baseline}:")
    lines.extend(format_final_window(analysis["baseline_final_actions"]))
    lines.append(f"{challenger}:")
    lines.extend(format_final_window(analysis["challenger_final_actions"]))

    return "\n".join(lines)


def format_context(context: dict[str, Any]) -> str:
    if not context:
        return "-"

    bits = [
        f"HP {context.get('hp')}/{context.get('max_hp')}",
        f"gold {context.get('gold')}",
        f"node {context.get('current_node_type')}",
    ]

    if context.get("energy") is not None:
        bits.append(f"energy {context.get('energy')}")
    if context.get("hand"):
        bits.append("hand " + ",".join(context["hand"]))
    if context.get("enemy_hp"):
        bits.append("enemy_hp " + ",".join(str(value) for value in context["enemy_hp"]))
    if context.get("reward_cards"):
        bits.append("rewards " + ",".join(context["reward_cards"]))
    if context.get("map_options"):
        bits.append("map " + ",".join(context["map_options"]))

    return " | ".join(bits)


def format_map_path(path: list[dict[str, Any]]) -> str:
    if not path:
        return "-"

    return " -> ".join(
        f"{entry['node_type']}({entry['hp_before']}->{entry['hp_after']})"
        for entry in path
    )


def format_reward_choices(choices: list[dict[str, Any]]) -> str:
    if not choices:
        return "-"

    return " | ".join(
        f"step {choice['step']}: {choice['choice']}"
        for choice in choices
    )


def format_final_window(actions: list[dict[str, Any]]) -> list[str]:
    if not actions:
        return ["  -"]

    return [
        (
            f"  step {entry['step']}: {entry['phase']} | "
            f"HP {entry['hp_before']}->{entry['hp_after']} | "
            f"enemy_hp {entry['enemy_hp_before']} | "
            f"{entry['action']} | reward {entry['reward']:.2f} | "
            f"after {entry['after_phase']}"
        )
        for entry in actions
    ]
