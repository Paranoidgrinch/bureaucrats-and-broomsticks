"""Balance-oriented analysis of agent benchmark results.

This module does not change balance. It turns benchmark outputs into a concise
diagnostic report so later patches can be based on evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BalanceReportThresholds:
    hard_competent_win_rate: float = 0.10
    easy_competent_win_rate: float = 0.75
    random_warning_win_rate: float = 0.10
    agent_disagreement_win_rate: float = 0.10


def load_benchmark_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_balance_report(
    benchmark_payload: dict[str, Any],
    *,
    thresholds: BalanceReportThresholds | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or BalanceReportThresholds()
    summaries = benchmark_payload.get("summary", [])

    character_summaries = collect_character_summaries(summaries)
    overall_summaries = collect_overall_summaries(summaries)

    character_reports = [
        analyze_character(character_id, policy_summaries, thresholds)
        for character_id, policy_summaries in sorted(character_summaries.items())
    ]

    return {
        "schema_version": 1,
        "thresholds": asdict(thresholds),
        "overall": overall_summaries,
        "characters": character_reports,
        "priority": build_priority_lists(character_reports),
    }


def collect_character_summaries(
    summaries: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}

    for summary in summaries:
        character_id = summary.get("character_id")
        policy = summary.get("policy")
        if not character_id or not policy:
            continue
        if character_id == "__overall__":
            continue

        grouped.setdefault(character_id, {})[policy] = summary

    return grouped


def collect_overall_summaries(
    summaries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    overall: dict[str, dict[str, Any]] = {}

    for summary in summaries:
        if summary.get("character_id") != "__overall__":
            continue
        policy = summary.get("policy")
        if policy:
            overall[policy] = summary

    return overall


LEARNED_POLICY_ORDER = ("linear_q", "q_learning", "checkpoint_q", "good_player")


def learned_policy_summary(
    policy_summaries: dict[str, dict[str, Any]],
) -> tuple[str | None, dict[str, Any] | None]:
    for policy_name in LEARNED_POLICY_ORDER:
        summary = policy_summaries.get(policy_name)
        if summary is not None:
            return policy_name, summary
    return None, None


def analyze_character(
    character_id: str,
    policy_summaries: dict[str, dict[str, Any]],
    thresholds: BalanceReportThresholds,
) -> dict[str, Any]:
    heuristic = policy_summaries.get("heuristic")
    learned_policy_name, q_learning = learned_policy_summary(policy_summaries)
    random = policy_summaries.get("random")

    competent_win_rates = [
        float(summary.get("win_rate", 0.0))
        for summary in (heuristic, q_learning)
        if summary is not None
    ]
    competent_win_rate = (
        sum(competent_win_rates) / len(competent_win_rates)
        if competent_win_rates
        else 0.0
    )

    random_win_rate = float(random.get("win_rate", 0.0)) if random else 0.0
    heuristic_win_rate = float(heuristic.get("win_rate", 0.0)) if heuristic else None
    q_learning_win_rate = float(q_learning.get("win_rate", 0.0)) if q_learning else None

    flags: list[str] = []

    if competent_win_rate <= thresholds.hard_competent_win_rate:
        flags.append("too_hard_for_competent_agents")

    if competent_win_rate >= thresholds.easy_competent_win_rate:
        flags.append("too_easy_for_competent_agents")

    if random_win_rate >= thresholds.random_warning_win_rate:
        flags.append("random_policy_wins_too_often")

    if heuristic_win_rate is not None and q_learning_win_rate is not None:
        disagreement = abs(q_learning_win_rate - heuristic_win_rate)
        if disagreement >= thresholds.agent_disagreement_win_rate:
            flags.append("agent_disagreement")

    severity = classify_severity(flags)

    return {
        "character_id": character_id,
        "severity": severity,
        "flags": flags,
        "competent_win_rate": competent_win_rate,
        "heuristic_win_rate": heuristic_win_rate,
        "learned_policy_name": learned_policy_name,
        "q_learning_win_rate": q_learning_win_rate,
        "random_win_rate": random_win_rate,
        "q_minus_heuristic_win_rate": (
            None
            if heuristic_win_rate is None or q_learning_win_rate is None
            else q_learning_win_rate - heuristic_win_rate
        ),
        "policies": policy_summaries,
        "recommendation": recommendation_for_flags(flags),
    }


def classify_severity(flags: list[str]) -> str:
    if "too_hard_for_competent_agents" in flags:
        return "critical"
    if "too_easy_for_competent_agents" in flags:
        return "high"
    if "random_policy_wins_too_often" in flags:
        return "medium"
    if "agent_disagreement" in flags:
        return "inspect"
    return "ok"


def recommendation_for_flags(flags: list[str]) -> str:
    if "too_hard_for_competent_agents" in flags:
        return (
            "Inspect starter deck, starting relic, early combat matchups, and "
            "boss scaling. Do not nerf enemies globally before checking whether "
            "this character lacks damage, block, or scaling."
        )

    if "too_easy_for_competent_agents" in flags:
        return (
            "Inspect starter deck/relic synergies and runaway scaling. This "
            "character may need weaker starting tools, harder matchups, or less "
            "reliable sustain."
        )

    if "random_policy_wins_too_often" in flags:
        return (
            "Random policy wins unusually often. Check whether this character "
            "has passive power, excessive sustain, or auto-winning relic/card loops."
        )

    if "agent_disagreement" in flags:
        return (
            "Heuristic and Q-learning disagree substantially. Trace differing "
            "seeds before changing balance; this may indicate a real strategic branch."
        )

    return "No immediate balance concern from this benchmark size."


def build_priority_lists(
    character_reports: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return {
        "too_hard": [
            report["character_id"]
            for report in character_reports
            if "too_hard_for_competent_agents" in report["flags"]
        ],
        "too_easy": [
            report["character_id"]
            for report in character_reports
            if "too_easy_for_competent_agents" in report["flags"]
        ],
        "random_too_successful": [
            report["character_id"]
            for report in character_reports
            if "random_policy_wins_too_often" in report["flags"]
        ],
        "agent_disagreement": [
            report["character_id"]
            for report in character_reports
            if "agent_disagreement" in report["flags"]
        ],
        "ok": [
            report["character_id"]
            for report in character_reports
            if not report["flags"]
        ],
    }


def write_balance_report_json(
    report: dict[str, Any],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def write_balance_report_markdown(
    report: dict[str, Any],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_balance_report_markdown(report), encoding="utf-8")
    return output_path


def write_balance_report_bundle(
    report: dict[str, Any],
    output_dir: str | Path,
    *,
    stem: str = "balance_report",
) -> tuple[Path, Path]:
    output_directory = Path(output_dir)
    return (
        write_balance_report_json(report, output_directory / f"{stem}.json"),
        write_balance_report_markdown(report, output_directory / f"{stem}.md"),
    )


def format_balance_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Benchmark Balance Report",
        "",
        "## Priority",
    ]

    priority = report.get("priority", {})
    for key in ["too_hard", "too_easy", "random_too_successful", "agent_disagreement", "ok"]:
        values = priority.get(key, [])
        lines.append(f"- **{key}**: {', '.join(values) if values else '-'}")

    lines.append("")
    lines.append("## Characters")
    lines.append("")

    for character in report.get("characters", []):
        lines.append(f"### {character['character_id']}")
        lines.append("")
        lines.append(f"- Severity: **{character['severity']}**")
        lines.append(f"- Flags: {', '.join(character['flags']) if character['flags'] else '-'}")
        lines.append(f"- Competent win rate: {character['competent_win_rate']:.1%}")
        lines.append(f"- Heuristic win rate: {format_optional_rate(character['heuristic_win_rate'])}")
        learned_label = character.get("learned_policy_name") or "q_learning"
        lines.append(f"- {learned_label} win rate: {format_optional_rate(character['q_learning_win_rate'])}")
        lines.append(f"- Random win rate: {character['random_win_rate']:.1%}")

        delta = character["q_minus_heuristic_win_rate"]
        if delta is not None:
            lines.append(f"- Q minus heuristic: {delta:+.1%}")

        lines.append(f"- Recommendation: {character['recommendation']}")
        lines.append("")

    return "\n".join(lines)


def format_balance_report_console(report: dict[str, Any]) -> str:
    lines = ["=== Balance Report ==="]

    priority = report.get("priority", {})
    lines.append("")
    lines.append("Priority:")
    for key in ["too_hard", "too_easy", "random_too_successful", "agent_disagreement", "ok"]:
        values = priority.get(key, [])
        lines.append(f"  {key}: {', '.join(values) if values else '-'}")

    lines.append("")
    lines.append("Characters:")
    for character in report.get("characters", []):
        flags = ", ".join(character["flags"]) if character["flags"] else "-"
        lines.append(
            f"  {character['character_id']}: "
            f"{character['severity']} | "
            f"competent {character['competent_win_rate']:.1%} | "
            f"H {format_optional_rate(character['heuristic_win_rate'])} | "
            f"L[{character.get('learned_policy_name') or 'none'}] {format_optional_rate(character['q_learning_win_rate'])} | "
            f"R {character['random_win_rate']:.1%} | "
            f"flags {flags}"
        )

    return "\n".join(lines)


def format_optional_rate(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1%}"
