import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "verify-team-package.sh"


def run_gate(fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(GATE), str(ROOT / "tests" / "fixtures" / fixture)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_team_fixture_passes() -> None:
    completed = run_gate("team-valid")
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "PASS(team)" in completed.stdout


def test_degenerate_team_fixture_fails() -> None:
    completed = run_gate("team-degenerate")
    assert completed.returncode != 0
    assert "degenerate team" in completed.stdout
