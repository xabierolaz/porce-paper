import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"


def _stage_for(count: int) -> str:
    env = dict(os.environ)
    env.update(
        {
            "PORCE_EVASION_FAILSAFE_STAGE1_FAILS": "3",
            "PORCE_EVASION_FAILSAFE_STAGE2_FAILS": "5",
            "PORCE_EVASION_FAILSAFE_STAGE3_FAILS": "6",
            "PORCE_EVASION_FAILSAFE_ESCALATE_ACTION": "LAND",
        }
    )
    code = (
        "import sys;"
        f"sys.path.insert(0, r'{SRC}');"
        "import flight_controller as fc;"
        f"print(fc._failsafe_stage_for_fail_count({int(count)}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    return lines[-1].strip() if lines else ""


def test_failsafe_escalation_map_matches_documented_behaviour():
    assert _stage_for(2) == ""
    assert _stage_for(3) == "HOLD"
    assert _stage_for(5) == "REPLAN_LATERAL"
    assert _stage_for(6) == "LAND"
