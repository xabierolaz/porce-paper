import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_exporter():
    spec = importlib.util.spec_from_file_location("export_flight_data", REPO / "tools" / "export_flight_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_flight_data_from_archived_run(tmp_path):
    run = REPO / "evidence" / "zero_trust_runs" / "20260731_061815_cow"
    assert (run / "brain" / "events.jsonl").is_file(), "falta el run auditado de referencia"
    exporter = _load_exporter()
    result = exporter.export_run(run, tmp_path)
    control = tmp_path / "control.csv"
    planner = tmp_path / "planner_events.csv"
    assert control.is_file() and planner.is_file()
    header = control.read_text(encoding="utf-8").splitlines()[0]
    for column in ("lat_deg", "evasion_active", "replan_reason", "d_react_m", "setpoint_lat"):
        assert column in header
    planner_lines = [l for l in planner.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(planner_lines) - 1 == 23, "el run auditado tiene 23 replans"
    control_lines = [l for l in control.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(control_lines) > 1000
