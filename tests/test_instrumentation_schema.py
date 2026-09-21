from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_flight_controller_emits_planning_timings_and_route_coordinates():
    source = (REPO / "src" / "flight_controller.py").read_text(encoding="utf-8")
    assert "last_plan_ms = round(" in source
    assert "plan_ms=last_plan_ms" in source
    assert "route_points_latlon=last_route_points_latlon" in source
    assert "control_loop_dt_ms" in source
    assert '"plan_ms": float(_plan_ms)' in source


def test_vision_system_emits_capture_inference_and_publish_timings():
    source = (REPO / "src" / "vision_system.py").read_text(encoding="utf-8")
    assert "capture_wall_ts = time.time()" in source
    assert "inference_end_ns = time.perf_counter_ns()" in source
    assert "inference_ms = round(" in source
    assert "publish_wall_ts = time.time()" in source
    assert '"capture_ts": float(capture_wall_ts)' in source
    assert '"vision_cycle_ms": round(' in source
