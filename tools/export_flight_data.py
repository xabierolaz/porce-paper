#!/usr/bin/env python3
"""Exporta el paquete de datos del contrato de vuelos fisicos desde los logs auditados.

Uso:
  python tools/export_flight_data.py <run_dir> [--out <dir>]

Entrada (la que ya escribe el runtime, dentro de <run_dir>):
  brain/events.jsonl      eventos de auditoria del Brain (decision_snapshot, evasion_*,
                          obstacle_ingest, setpoint_sent, failsafe_*)
  brain/trajectory.csv    muestreo de trayectoria (0.5 s por defecto)

Salida (por defecto <run_dir>/derived/):
  control.csv             una fila por muestra de trayectoria (§5.1 del contrato)
  planner_events.csv      una fila por ruta local generada (§5.2 del contrato)

Notas:
  - La cadencia de control.csv es la de trajectory.csv (0.5 s en la configuracion
    actual, AUDIT_BRAIN_TRAJ_EVERY_S). El bucle de control real corre a 10 Hz; si se
    necesita 10 Hz, bajar AUDIT_BRAIN_TRAJ_EVERY_S a 0.1 en la campana.
  - Los campos no disponibles quedan vacios; no se inventan valores.
  - `setpoint_sent` se registro a partir del 2026-09-20; en runs anteriores esas
    columnas salen vacias.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


CONTROL_HEADERS = [
    "seq", "ts", "iso_utc", "mode", "armed", "lat_deg", "lon_deg", "alt_msl_m", "rel_alt_m",
    "groundspeed_mps", "active_wp_idx", "mission_state", "nearest_track_id", "nearest_class",
    "obs_dist_est_m", "track_age_s", "track_static", "safety_radius_m", "d_react_m",
    "evasion_active", "route_point_idx", "route_points_n", "replan_requested", "replan_reason",
    "planner_runtime_ms", "failsafe_level", "failsafe_action",
    "setpoint_lat", "setpoint_lon", "setpoint_alt_rel_m",
]

PLANNER_HEADERS = [
    "event_id", "ts", "iso_utc", "reason", "vehicle_lat", "vehicle_lon", "goal_wp_idx",
    "obstacle_count", "obstacle_ids", "obstacle_classes", "nearest_distance_m", "nearest_type",
    "runtime_ms", "result", "path_points", "path_start_lat", "path_start_lon",
    "path_goal_lat", "path_goal_lon", "can_replan_now",
]


def _iso(ts: float) -> str:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(timespec="milliseconds")
    except Exception:
        return ""


def load_events(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            continue
    return events


def load_trajectory(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="ignore") as fh:
        return list(csv.DictReader(fh))


def _nearest(events: List[Dict[str, Any]], kind: str, ts: float) -> Optional[Dict[str, Any]]:
    best = None
    best_dt = None
    for e in events:
        if e.get("kind") != kind:
            continue
        try:
            dt = abs(float(e.get("ts", 0.0)) - float(ts))
        except Exception:
            continue
        if best_dt is None or dt < best_dt:
            best, best_dt = e, dt
    return best


def _previous(events: List[Dict[str, Any]], kind: str, ts: float) -> Optional[Dict[str, Any]]:
    best = None
    best_ts = None
    for e in events:
        if e.get("kind") != kind:
            continue
        try:
            ets = float(e.get("ts", 0.0))
        except Exception:
            continue
        if ets <= float(ts) and (best_ts is None or ets > best_ts):
            best, best_ts = e, ets
    return best


def _f(value: Any) -> str:
    try:
        if value in (None, ""):
            return ""
        return f"{float(value):.7g}"
    except Exception:
        return ""


def build_control_rows(events: List[Dict[str, Any]], traj: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, t in enumerate(traj):
        try:
            ts = float(t.get("ts", ""))
        except Exception:
            continue
        dec = _nearest(events, "decision_snapshot", ts) or {}
        plan = _nearest(events, "evasion_route_generated", ts) or {}
        spt = _previous(events, "setpoint_sent", ts) or {}
        obs = (dec.get("obs_sample") or [{}])[0] if isinstance(dec.get("obs_sample"), list) else {}
        rows.append({
            "seq": idx,
            "ts": _f(ts),
            "iso_utc": _iso(ts),
            "mode": t.get("mode", ""),
            "armed": t.get("armed", ""),
            "lat_deg": t.get("lat", ""),
            "lon_deg": t.get("lon", ""),
            "alt_msl_m": t.get("alt_msl", ""),
            "rel_alt_m": t.get("rel_alt", ""),
            "groundspeed_mps": _f(dec.get("speed_mps")),
            "active_wp_idx": t.get("wp_idx", ""),
            "mission_state": dec.get("mission_state", ""),
            "nearest_track_id": obs.get("track_id", dec.get("nearest_track_id", "")),
            "nearest_class": dec.get("nearest_type", t.get("nearest_type", "")),
            "obs_dist_est_m": t.get("nearest_obs_dist_m", _f(dec.get("nearest_distance_m"))),
            "track_age_s": _f(obs.get("track_age_s", dec.get("obs_age_s"))),
            "track_static": obs.get("static", ""),
            "safety_radius_m": _f(obs.get("safety_radius_m")),
            "d_react_m": _f(dec.get("reaction_distance_eval_m")),
            "evasion_active": t.get("evasion_active", ""),
            "route_point_idx": t.get("evasion_path_idx", ""),
            "route_points_n": plan.get("route_points", dec.get("decision_route_points", "")),
            "replan_requested": dec.get("decision_triggered", ""),
            "replan_reason": dec.get("decision_reason", ""),
            "planner_runtime_ms": _f(plan.get("plan_ms", dec.get("plan_ms"))),
            "failsafe_level": dec.get("failsafe_level", ""),
            "failsafe_action": dec.get("failsafe_action_active", ""),
            "setpoint_lat": _f(spt.get("lat")),
            "setpoint_lon": _f(spt.get("lon")),
            "setpoint_alt_rel_m": _f(spt.get("alt_rel_m")),
        })
    return rows


def build_planner_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seq = 0
    for e in events:
        if e.get("kind") != "evasion_route_generated":
            continue
        seq += 1
        pts = e.get("route_points_latlon") or []
        first = pts[0] if isinstance(pts, list) and pts else {}
        last = pts[-1] if isinstance(pts, list) and pts else {}
        ids = e.get("planner_obs_ids") or []
        try:
            ts = float(e.get("ts", 0.0))
        except Exception:
            ts = 0.0
        rows.append({
            "event_id": seq,
            "ts": _f(ts),
            "iso_utc": _iso(ts),
            "reason": "trigger",
            "vehicle_lat": _f(first.get("lat") if isinstance(first, dict) else None),
            "vehicle_lon": _f(first.get("lon") if isinstance(first, dict) else None),
            "goal_wp_idx": e.get("wp_idx", ""),
            "obstacle_count": e.get("planner_obs_count", ""),
            "obstacle_ids": "|".join(str(i) for i in ids),
            "obstacle_classes": (str(e.get("nearest_type", "")) if e.get("nearest_type") else ""),
            "nearest_distance_m": _f(e.get("nearest_distance_m")),
            "nearest_type": e.get("nearest_type", ""),
            "runtime_ms": _f(e.get("plan_ms")),
            "result": "valid",
            "path_points": e.get("route_points", ""),
            "path_start_lat": _f(first.get("lat") if isinstance(first, dict) else None),
            "path_start_lon": _f(first.get("lon") if isinstance(first, dict) else None),
            "path_goal_lat": _f(last.get("lat") if isinstance(last, dict) else None),
            "path_goal_lon": _f(last.get("lon") if isinstance(last, dict) else None),
            "can_replan_now": e.get("can_replan_now", ""),
        })
    return rows


def write_csv(path: Path, headers: List[str], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def export_run(run_dir: Path, out_dir: Optional[Path] = None) -> Dict[str, str]:
    brain = run_dir / "brain"
    events = load_events(brain / "events.jsonl")
    traj = load_trajectory(brain / "trajectory.csv")
    dest = out_dir if out_dir is not None else run_dir / "derived"
    control = build_control_rows(events, traj)
    planner = build_planner_rows(events)
    out_control = dest / "control.csv"
    out_planner = dest / "planner_events.csv"
    write_csv(out_control, CONTROL_HEADERS, control)
    write_csv(out_planner, PLANNER_HEADERS, planner)
    return {"control_csv": str(out_control), "planner_events_csv": str(out_planner),
            "control_rows": str(len(control)), "planner_rows": str(len(planner))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = export_run(args.run_dir, args.out)
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
