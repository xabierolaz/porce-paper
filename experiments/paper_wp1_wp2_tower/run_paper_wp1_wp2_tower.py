"""Run a deterministic Paper Figure 1 scenario on the real PORCE Brain.

This harness does not draw a mock figure. It starts ``src/flight_controller.py``
with mock MAVLink, injects one static tower obstacle through the same
``/api/obstacles`` endpoint used by vision, and validates that the resulting
audit logs prove the WP1->WP2 paper sequence:

nominal flight -> detection/no action -> A* planning -> evasion active ->
evasion complete/rejoin before WP2.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
DEFAULTS_ENV = SRC_DIR / "configs" / "porce_defaults.env"
WAYPOINTS = REPO_ROOT / "missions" / "ejea_canonical_523m.waypoints"
VENV_PY = Path(os.environ.get("PORCE_PYTHON", str(REPO_ROOT.parent / "venv" / "Scripts" / "python.exe")))
OUT_ROOT = REPO_ROOT / "runs" / "paper_wp1_wp2_tower"

EARTH_RADIUS_M = 6_371_000.0
INJECT_SOURCE = "vision"
INJECT_CONFIDENCE = 0.99


def log(message: str) -> None:
    print(f"[paper_wp1_wp2] {message}", flush=True)


def load_defaults_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not DEFAULTS_ENV.exists():
        return env
    for raw in DEFAULTS_ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().replace("%PROJECT_ROOT%", str(REPO_ROOT))
    return env


def load_waypoints() -> list[dict]:
    rows = WAYPOINTS.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: list[dict] = []
    for line in rows[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        out.append({"idx": int(parts[0]), "lat": float(parts[8]), "lon": float(parts[9]), "alt": float(parts[10])})
    return out


def latlon_to_enu(lat_ref: float, lon_ref: float, lat: float, lon: float) -> tuple[float, float]:
    north = math.radians(lat - lat_ref) * EARTH_RADIUS_M
    east = math.radians(lon - lon_ref) * EARTH_RADIUS_M * max(math.cos(math.radians(lat_ref)), 1e-6)
    return east, north


def offset_latlon(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    dlat = math.degrees(north_m / EARTH_RADIUS_M)
    dlon = math.degrees(east_m / (EARTH_RADIUS_M * max(math.cos(math.radians(lat)), 1e-6)))
    return lat + dlat, lon + dlon


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    north = math.radians(lat2 - lat1) * EARTH_RADIUS_M
    east = math.radians(lon2 - lon1) * EARTH_RADIUS_M * max(math.cos(math.radians(lat1)), 1e-6)
    return math.hypot(north, east)


def waypoint_obstacle(progress: float, lateral_m: float, leg: int = 1) -> dict:
    mission = load_waypoints()
    wp1 = mission[leg]
    wp2 = mission[leg + 1]
    east2, north2 = latlon_to_enu(wp1["lat"], wp1["lon"], wp2["lat"], wp2["lon"])
    length = math.hypot(east2, north2)
    if length <= 1e-6:
        raise RuntimeError("WP1->WP2 segment has zero length")
    f_east = east2 / length
    f_north = north2 / length
    l_east = -f_north
    l_north = f_east
    east = east2 * progress + l_east * lateral_m
    north = north2 * progress + l_north * lateral_m
    lat, lon = offset_latlon(wp1["lat"], wp1["lon"], north, east)
    return {
        "lat": lat,
        "lon": lon,
        "east_m": east,
        "north_m": north,
        "progress": progress,
        "lateral_m": lateral_m,
        "segment_length_m": length,
    }


def find_free_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found")


def http_json(url: str, *, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def http_post_json(url: str, payload: dict, headers: dict[str, str], *, timeout: float = 2.0) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return -1


def parse_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]


def load_traj(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    header = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        parts = line.split(",")
        if header is None:
            header = parts
            continue
        rows.append({key: value for key, value in zip(header, parts)})
    return rows


def nearest_traj(rows: list[dict], ts: float) -> dict | None:
    if not rows:
        return None
    return min(rows, key=lambda row: abs(float(row["ts"]) - ts))


def projection_to_wp2(row: dict) -> float:
    mission = load_waypoints()
    wp1 = mission[1]
    wp2 = mission[2]
    east2, north2 = latlon_to_enu(wp1["lat"], wp1["lon"], wp2["lat"], wp2["lon"])
    east, north = latlon_to_enu(wp1["lat"], wp1["lon"], float(row["lat"]), float(row["lon"]))
    seg2 = east2 * east2 + north2 * north2
    return ((east * east2) + (north * north2)) / seg2


ACCEPTED_TYPE_KEYS = {"tower": ("tower",), "person": ("person", "bike")}


def validate_run(run_dir: Path, obstacle_type: str) -> dict:
    accepted_keys = set(ACCEPTED_TYPE_KEYS.get(obstacle_type, (obstacle_type,)))
    events = parse_jsonl(run_dir / "brain" / "events.jsonl")
    traj = load_traj(run_dir / "brain" / "trajectory.csv")
    accepted_types = set()
    for event in events:
        if event.get("kind") != "obstacle_ingest":
            continue
        for obs in event.get("accepted", []) or event.get("sample", []) or event.get("obs_sample", []) or []:
            obs_type = str(obs.get("type") or obs.get("object_type") or "").lower()
            if obs_type:
                accepted_types.add(obs_type)

    detections = []
    plans = []
    completions = []
    failures = []
    for event in events:
        kind = event.get("kind")
        if kind == "decision_snapshot" and event.get("nearest_type") in accepted_keys:
            row = nearest_traj(traj, float(event["ts"]))
            detections.append({"event": event, "row": row, "progress": projection_to_wp2(row) if row else None})
        elif kind == "evasion_route_generated" and event.get("nearest_type") in accepted_keys:
            row = nearest_traj(traj, float(event["ts"]))
            plans.append({"event": event, "row": row, "progress": projection_to_wp2(row) if row else None})
        elif kind == "evasion_completed":
            row = nearest_traj(traj, float(event["ts"]))
            completions.append({"event": event, "row": row, "progress": projection_to_wp2(row) if row else None})
        elif kind in {"evasion_route_failed_hold", "failsafe_escalation_triggered"}:
            failures.append(event)

    clean_detection = [
        item for item in detections
        if item["event"].get("decision_reason") == "distance_above_reaction"
        and item["row"] is not None
        and int(float(item["row"].get("evasion_active", "0"))) == 0
        and 0.0 <= float(item["progress"]) < 1.0
    ]
    valid_plans = [
        item for item in plans
        if item["row"] is not None
        and int(float(item["event"].get("route_points", 0) or 0)) >= 2
        and int(float(item["event"].get("planner_obs_count", 0) or 0)) == 1
        and 0.0 <= float(item["progress"]) < 1.0
    ]
    valid_completions = [
        item for item in completions
        if item["row"] is not None
        and 0.0 <= float(item["progress"]) < 1.0
        and int(float(item["row"].get("wp_idx", "0"))) <= 2
    ]

    active_rows = [row for row in traj if int(float(row.get("evasion_active", "0"))) == 1]
    active_start_progress = projection_to_wp2(active_rows[0]) if active_rows else None
    active_end_progress = projection_to_wp2(active_rows[-1]) if active_rows else None

    ok = (
        bool(clean_detection)
        and bool(valid_plans)
        and bool(valid_completions)
        and accepted_types.issubset(accepted_keys)
        and not failures
        and active_end_progress is not None
        and active_end_progress < 1.0
    )
    return {
        "ok": ok,
        "accepted_types": sorted(accepted_types),
        "clean_detection_count": len(clean_detection),
        "valid_plan_count": len(valid_plans),
        "valid_completion_count": len(valid_completions),
        "failure_count": len(failures),
        "active_start_progress": active_start_progress,
        "active_end_progress": active_end_progress,
        "selected_detection_ts": clean_detection[0]["event"]["ts"] if clean_detection else None,
        "selected_plan_ts": valid_plans[0]["event"]["ts"] if valid_plans else None,
        "selected_completion_ts": valid_completions[0]["event"]["ts"] if valid_completions else None,
    }


def run_candidate(progress: float, lateral_m: float, base_port: int, timeout_s: float, obstacle_type: str) -> dict:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUT_ROOT / f"paper_wp1_wp2_{obstacle_type}_p{progress:.2f}_l{lateral_m:+.1f}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)
    port = find_free_port(base_port)
    base_url = f"http://127.0.0.1:{port}"
    obstacle = waypoint_obstacle(progress, lateral_m)

    env = dict(os.environ)
    env.update(load_defaults_env())
    env.update(
        {
            "PORCE_SYSTEM_MODE": "SIMULATION",
            "PORCE_MOCK_MAVLINK": "1",
            "PORCE_FORCE_ARM": "1",
            "PORCE_ENABLE_EVASION": "1",
            "PORCE_BRAIN_HTTP_PORT": str(port),
            "PORCE_BRAIN_HTTP_HOST": "127.0.0.1",
            "PORCE_BRAIN_APP_BIND_HOST": "127.0.0.1",
            "PORCE_OBSTACLE_TOKEN": token,
            "PORCE_OBSTACLE_TOKEN_REQUIRED": "1",
            "PORCE_OBS_SOURCE_FILTER_ENABLE": "1",
            "PORCE_OBS_ALLOWED_SOURCES": INJECT_SOURCE,
            "PORCE_OBS_STATIC_CLASS_NAMES": obstacle_type,
            "PORCE_VISION_TARGET_CLASS_NAMES": obstacle_type,
            "PORCE_EVASION_ALLOW_REPLAN_WHEN_ACTIVE": "0",
            "PORCE_EVASION_FAILSAFE_ESCALATE_ENABLE": "0",
            "PORCE_AUDIT_ENABLE": "1",
            "PORCE_AUDIT_ROOT": str(run_dir),
            "PORCE_CONFIG_BANNER": "0",
        }
    )

    python_exe = VENV_PY if VENV_PY.exists() else Path(sys.executable)
    stdout_path = run_dir / "brain_stdout.log"
    proc = subprocess.Popen(
        [str(python_exe), "-u", "flight_controller.py"],
        cwd=str(SRC_DIR),
        env=env,
        stdout=stdout_path.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )

    meta = {
        "run_dir": str(run_dir),
        "port": port,
        "obstacle": obstacle,
        "ok": False,
        "error": None,
    }
    try:
        deadline = time.time() + 45.0
        while time.time() < deadline:
            status = http_json(f"{base_url}/api/status")
            if status:
                break
            if proc.poll() is not None:
                raise RuntimeError("Brain exited during startup")
            time.sleep(0.25)
        else:
            raise RuntimeError("Brain HTTP did not become ready")

        deadline = time.time() + 120.0
        while time.time() < deadline:
            status = http_json(f"{base_url}/api/status") or {}
            if int(status.get("wp_idx", 0) or 0) >= 2:
                break
            if proc.poll() is not None:
                raise RuntimeError("Brain exited before WP2")
            time.sleep(0.5)
        else:
            raise RuntimeError("Timeout waiting for WP2")

        headers = {"X-PORCE-Token": token}
        post_count = 0
        post_ok = 0
        deadline = time.time() + timeout_s
        reached_wp3 = False
        while time.time() < deadline:
            ui = http_json(f"{base_url}/api/ui/data", timeout=0.5) or {}
            telemetry = ui.get("telemetry") or {}
            cur_lat = float(telemetry.get("lat", obstacle["lat"]))
            cur_lon = float(telemetry.get("lon", obstacle["lon"]))
            payload = {
                "obstacles": [
                    {
                        "source": INJECT_SOURCE,
                        "source_id": 101,
                        "type": obstacle_type,
                        "confidence": INJECT_CONFIDENCE,
                        "lat": obstacle["lat"],
                        "lon": obstacle["lon"],
                        "distance": distance_m(cur_lat, cur_lon, obstacle["lat"], obstacle["lon"]),
                    }
                ]
            }
            code = http_post_json(f"{base_url}/api/obstacles", payload, headers, timeout=0.5)
            post_count += 1
            post_ok += int(code == 200)
            status = http_json(f"{base_url}/api/status", timeout=0.5) or {}
            if int(status.get("wp_idx", 0) or 0) >= 3:
                reached_wp3 = True
                time.sleep(2.0)
                break
            if proc.poll() is not None:
                raise RuntimeError("Brain exited during scenario")
            time.sleep(1.0 / 4.0)
        meta["post_count"] = post_count
        meta["post_ok"] = post_ok
        meta["reached_wp3"] = reached_wp3
    except Exception as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()

    validation = validate_run(run_dir, obstacle_type)
    meta["validation"] = validation
    meta["ok"] = bool(validation["ok"])
    (run_dir / "paper_wp1_wp2_tower_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta

# ---------------------------------------------------------------------------
# Protocolo F1/F2/F3 (contrato de vuelos fisicos) sobre la mision canonica.
#   F2/F3: tres encuentros sucesivos torre -> persona -> torre con la MISMA
#          geometria (progreso 0.50 del tramo, lateral 0) en los tramos 1, 3 y 5
#          (un tramo vacio entre encuentros para rejoin holgado).
#   F1   : mismos objetos, misma ruta y misma velocidad, pero a 70 m laterales:
#          se detectan (rango de deteccion 80 m) sin entrar en el horizonte de
#          reaccion (reaccion = 45 + 2*v = 61 m a 8 m/s) => cero replans
#          (dormancia). OJO: ocultar solo a la persona no basta; si las torres
#          quedan en el corredor dispararian igualmente.
PROTOCOLS = {
    "f1": [("tower", 1, 0.50, 70.0), ("person", 3, 0.50, 70.0), ("tower", 5, 0.50, 70.0)],
    "f2": [("tower", 1, 0.50, 0.0), ("person", 3, 0.50, 0.0), ("tower", 5, 0.50, 0.0)],
    "f3": [("tower", 1, 0.50, 0.0), ("person", 3, 0.50, 0.0), ("tower", 5, 0.50, 0.0)],
}


def validate_protocol(run_dir: Path, specs: list, expect_evasion: bool) -> dict:
    events = parse_jsonl(run_dir / "brain" / "events.jsonl")
    accepted = set()
    plans, completions, failures, clean = [], [], [], 0
    for event in events:
        kind = event.get("kind")
        if kind == "obstacle_ingest":
            for obs in event.get("accepted", []) or event.get("sample", []) or []:
                t = str(obs.get("type") or "").lower()
                if t:
                    accepted.add(t)
        elif kind == "decision_snapshot" and event.get("decision_reason") == "distance_above_reaction":
            clean += 1
        elif kind == "evasion_route_generated":
            plans.append(event)
        elif kind == "evasion_completed":
            completions.append(event)
        elif kind in {"evasion_route_failed_hold", "failsafe_escalation_triggered"}:
            failures.append(event)
    if expect_evasion:
        ok = (len(plans) >= len(specs) and len(completions) >= len(specs)
              and not failures and clean >= len(specs)
              and accepted.issubset({"tower", "bike"}))
    else:
        ok = (len(plans) == 0 and len(completions) == 0 and not failures
              and clean >= len(specs))
    return {"ok": ok, "accepted_types": sorted(accepted), "clean_detections": clean,
            "plans": len(plans), "completions": len(completions), "failures": len(failures)}


def run_protocol(name: str, base_port: int, timeout_s: float) -> dict:
    specs = PROTOCOLS[name]
    expect_evasion = name in ("f2", "f3")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUT_ROOT / f"paper_protocol_{name}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)
    port = find_free_port(base_port)
    base_url = f"http://127.0.0.1:{port}"

    obstacles = []
    for i, (obs_type, leg, progress, lateral) in enumerate(specs):
        o = waypoint_obstacle(progress, lateral, leg=leg)
        o["type"] = obs_type
        o["source_id"] = 101 + i
        obstacles.append(o)
    last_leg = max(s[1] for s in specs)

    env = dict(os.environ)
    env.update(load_defaults_env())
    env.update({
        "PORCE_SYSTEM_MODE": "SIMULATION",
        "PORCE_MOCK_MAVLINK": "1",
        "PORCE_FORCE_ARM": "1",
        "PORCE_ENABLE_EVASION": "1",
        "PORCE_BRAIN_HTTP_PORT": str(port),
        "PORCE_BRAIN_HTTP_HOST": "127.0.0.1",
        "PORCE_BRAIN_APP_BIND_HOST": "127.0.0.1",
        "PORCE_OBSTACLE_TOKEN": token,
        "PORCE_OBSTACLE_TOKEN_REQUIRED": "1",
        "PORCE_OBS_SOURCE_FILTER_ENABLE": "1",
        "PORCE_OBS_ALLOWED_SOURCES": INJECT_SOURCE,
        "PORCE_OBS_STATIC_CLASS_NAMES": "tower,person",
        "PORCE_VISION_TARGET_CLASS_NAMES": "tower,person",
        "PORCE_EVASION_ALLOW_REPLAN_WHEN_ACTIVE": "0",
        "PORCE_EVASION_FAILSAFE_ESCALATE_ENABLE": "0",
        "PORCE_AUDIT_ENABLE": "1",
        "PORCE_AUDIT_ROOT": str(run_dir),
        "PORCE_CONFIG_BANNER": "0",
    })
    python_exe = VENV_PY if VENV_PY.exists() else Path(sys.executable)
    proc = subprocess.Popen([str(python_exe), "-u", "flight_controller.py"], cwd=str(SRC_DIR), env=env,
                            stdout=(run_dir / "brain_stdout.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    meta = {"run_dir": str(run_dir), "port": port, "obstacles": obstacles, "ok": False, "error": None}
    try:
        deadline = time.time() + 45.0
        while time.time() < deadline:
            if http_json(f"{base_url}/api/status"):
                break
            if proc.poll() is not None:
                raise RuntimeError("Brain exited during startup")
            time.sleep(0.25)
        else:
            raise RuntimeError("Brain HTTP did not become ready")

        headers = {"X-PORCE-Token": token}
        deadline = time.time() + timeout_s
        posts = 0
        while time.time() < deadline:
            ui = http_json(f"{base_url}/api/ui/data", timeout=0.5) or {}
            telemetry = ui.get("telemetry") or {}
            cur_lat = float(telemetry.get("lat", obstacles[0]["lat"]))
            cur_lon = float(telemetry.get("lon", obstacles[0]["lon"]))
            payload = {"obstacles": [
                {"source": INJECT_SOURCE, "source_id": o["source_id"], "type": o["type"],
                 "confidence": INJECT_CONFIDENCE, "lat": o["lat"], "lon": o["lon"],
                 "distance": distance_m(cur_lat, cur_lon, o["lat"], o["lon"])}
                for o in obstacles]}
            http_post_json(f"{base_url}/api/obstacles", payload, headers, timeout=0.5)
            posts += 1
            status = http_json(f"{base_url}/api/status", timeout=0.5) or {}
            if int(status.get("wp_idx", 0) or 0) > last_leg + 1:
                break
            if proc.poll() is not None:
                raise RuntimeError("Brain exited during protocol")
            time.sleep(0.25)
        meta["posts"] = posts
    except Exception as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()

    validation = validate_protocol(run_dir, specs, expect_evasion)
    meta["validation"] = validation
    meta["ok"] = bool(validation["ok"])
    (run_dir / f"paper_protocol_{name}_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def clarity_score(result: dict) -> float:
    validation = result.get("validation") or {}
    if not result.get("ok"):
        return -1.0
    start = validation.get("active_start_progress")
    end = validation.get("active_end_progress")
    if start is None or end is None:
        return -1.0
    start_f = float(start)
    end_f = float(end)
    duration = max(0.0, end_f - start_f)
    rejoin_margin = max(0.0, 1.0 - end_f)
    centered = 1.0 - min(1.0, abs(((start_f + end_f) / 2.0) - 0.58) / 0.58)
    margin = min(1.0, rejoin_margin / 0.18)
    useful_duration = min(1.0, duration / 0.55)
    return 0.45 * margin + 0.35 * centered + 0.20 * useful_duration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-port", type=int, default=18120)
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--type", choices=["tower", "person"], default="tower",
                        help="clase del obstaculo estatico inyectado (tower|person)")
    parser.add_argument("--protocol", choices=sorted(PROTOCOLS), default=None,
                        help="protocolo F1/F2/F3 de tres encuentros sobre la mision canonica")
    parser.add_argument("--candidates", nargs="*", default=["0.38:0", "0.44:0", "0.50:0", "0.56:0", "0.44:8", "0.50:8", "0.56:8", "0.44:-8", "0.50:-8", "0.56:-8"])
    parser.add_argument("--stop-at-first", action="store_true")
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    if args.protocol:
        log(f"protocolo {args.protocol.upper()} (torre/persona/torre sobre la mision canonica)")
        result = run_protocol(args.protocol, args.base_port, max(args.timeout_s, 300.0))
        v = result["validation"]
        log("  ok=%s clean=%s plans=%s completions=%s failures=%s accepted=%s err=%s run=%s"
            % (result["ok"], v["clean_detections"], v["plans"], v["completions"],
               v["failures"], v["accepted_types"], result["error"], result["run_dir"]))
        (OUT_ROOT / f"latest_protocol_{args.protocol}_meta.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")
        return 0 if result["ok"] else 1

    results = []
    for spec in args.candidates:
        progress_s, lateral_s = spec.split(":", 1)
        progress = float(progress_s)
        lateral = float(lateral_s)
        log(f"candidate progress={progress:.2f} lateral={lateral:+.1f}m")
        result = run_candidate(progress, lateral, args.base_port, args.timeout_s, args.type)
        results.append(result)
        v = result["validation"]
        log(
            "  ok=%s score=%.3f clean_det=%s plans=%s completions=%s active=%.3f->%.3f err=%s run=%s"
            % (
                result["ok"],
                clarity_score(result),
                v["clean_detection_count"],
                v["valid_plan_count"],
                v["valid_completion_count"],
                float(v["active_start_progress"]) if v["active_start_progress"] is not None else -1.0,
                float(v["active_end_progress"]) if v["active_end_progress"] is not None else -1.0,
                result["error"],
                result["run_dir"],
            )
        )
        if result["ok"] and args.stop_at_first:
            break

    ranked = sorted((item for item in results if item["ok"]), key=clarity_score, reverse=True)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results": results,
        "best": ranked[0] if ranked else None,
    }
    out = OUT_ROOT / "latest_paper_wp1_wp2_tower_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["best"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
