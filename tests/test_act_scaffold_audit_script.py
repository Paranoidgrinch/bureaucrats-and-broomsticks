import subprocess
import sys


def test_act_scaffold_audit_script_runs_for_late_acts() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_act_scaffold.py",
            "--seeds",
            "5",
            "--acts",
            "3",
            "4",
            "5",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Act scaffold audit" in result.stdout
    assert "Act 3:" in result.stdout
    assert "Act 4:" in result.stdout
    assert "Act 5:" in result.stdout
