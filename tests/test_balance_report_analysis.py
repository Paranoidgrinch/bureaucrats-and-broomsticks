from bab.sim.balance_report import (
    BalanceReportThresholds,
    build_balance_report,
    format_balance_report_console,
    format_balance_report_markdown,
    write_balance_report_bundle,
)


def sample_payload():
    return {
        "schema_version": 1,
        "summary": [
            {
                "policy": "heuristic",
                "character_id": "__overall__",
                "runs": 2,
                "wins": 1,
                "win_rate": 0.5,
                "average_reward": 10.0,
            },
            {
                "policy": "heuristic",
                "character_id": "hard_character",
                "runs": 10,
                "wins": 0,
                "win_rate": 0.0,
                "average_reward": -5.0,
            },
            {
                "policy": "q_learning",
                "character_id": "hard_character",
                "runs": 10,
                "wins": 1,
                "win_rate": 0.1,
                "average_reward": -1.0,
            },
            {
                "policy": "random",
                "character_id": "hard_character",
                "runs": 10,
                "wins": 0,
                "win_rate": 0.0,
                "average_reward": -10.0,
            },
            {
                "policy": "heuristic",
                "character_id": "easy_character",
                "runs": 10,
                "wins": 9,
                "win_rate": 0.9,
                "average_reward": 100.0,
            },
            {
                "policy": "q_learning",
                "character_id": "easy_character",
                "runs": 10,
                "wins": 8,
                "win_rate": 0.8,
                "average_reward": 90.0,
            },
            {
                "policy": "random",
                "character_id": "easy_character",
                "runs": 10,
                "wins": 2,
                "win_rate": 0.2,
                "average_reward": 20.0,
            },
        ],
    }


def test_build_balance_report_flags_hard_and_easy_characters() -> None:
    report = build_balance_report(sample_payload())

    priority = report["priority"]

    assert "hard_character" in priority["too_hard"]
    assert "easy_character" in priority["too_easy"]
    assert "easy_character" in priority["random_too_successful"]


def test_format_balance_report_outputs_text() -> None:
    report = build_balance_report(sample_payload())

    console_text = format_balance_report_console(report)
    markdown_text = format_balance_report_markdown(report)

    assert "Balance Report" in console_text
    assert "hard_character" in console_text
    assert "# Agent Benchmark Balance Report" in markdown_text
    assert "easy_character" in markdown_text


def test_write_balance_report_bundle(tmp_path) -> None:
    report = build_balance_report(
        sample_payload(),
        thresholds=BalanceReportThresholds(),
    )

    json_path, markdown_path = write_balance_report_bundle(
        report,
        tmp_path,
        stem="report",
    )

    assert json_path.exists()
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8").startswith("# Agent Benchmark")
