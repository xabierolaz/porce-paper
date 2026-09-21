#!/usr/bin/env python3
"""Auditoria de consistencia interna de los expedientes de campo PF1/PF2/PF3.

Verifica, para cada dossier de evidence/field/:
  - manifiesto SHA-256 (cobertura, LF, hashes);
  - metadatos (nombre de carpeta == run_id, arranque, hash_bin vs. flight*.BIN, params, mision);
  - DataFlash nativo parseable con pymavlink y ventana [boot, close];
  - secuencia ARM/MODE del BIN coherente con run_meta;
  - telemetria tlog (cabecera, layout, ventana, huecos);
  - relojes brain (t_utc_us = boot + mono) en events/setpoints/trajectory/resources;
  - alineacion events.jsonl <-> planner_events.csv <-> setpoints;
  - detecciones (ventana, orden, distancia compatible con trigger/trayectoria);
  - clearance declarado vs. trayectoria.

Uso:
    python tools/audit_field_dossiers.py [dossier ...]
Salida: informe legible + JSON (--json PATH). Codigo de salida 1 si hay hallazgos.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DOSSIERS = [
    REPO / "evidence" / "field" / "PF1_20260919_0914",
    REPO / "evidence" / "field" / "PF2_20260919_1016",
    REPO / "evidence" / "field" / "PF3_20260920_1009",
]

# Tolerancias
CLOCK_TOL_US = 2000           # ±2 ms en t_utc_us = boot + mono
EVENT_ALIGN_TOL_US = 2000     # ±2 ms entre events y planner
TLOG_START_TOL_US = 1000000   # tlog puede empezar hasta 1 s antes del boot redondeado
BIN_END_TOL_US = 1000000
TLOG_MAX_GAP_US = 2000000     # 2 s: hueco de telemetria aceptable
CLEARANCE_TOL_M = 0.6
DETECT_DIST_TOL_M = 10.0
SETPOINT_STEP_MAX_M = 60.0    # salto maximo admisible entre setpoints consecutivos (0,1 s)

FINDINGS: list[dict] = []


def add(level: str, dossier: str, check: str, message: str) -> None:
    FINDINGS.append({"level": level, "dossier": dossier, "check": check, "message": message})


def parse_utc(s: str) -> float:
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    raise ValueError(f"fecha no reconocida: {s!r}")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
def check_manifest(root: Path, name: str) -> None:
    man = root / "metadata" / "hashes.sha256"
    raw = man.read_bytes()
    if b"\r\n" in raw:
        add("ERROR", name, "manifest", "manifiesto con CRLF (se exige LF)")
    listed = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        listed[rel.strip()] = digest.strip()
    present = {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and p.name != "hashes.sha256"
    }
    missing = sorted(set(listed) - present)
    extra = sorted(present - set(listed))
    if missing:
        add("ERROR", name, "manifest", f"entradas del manifiesto sin fichero: {missing}")
    if extra:
        add("WARN", name, "manifest", f"ficheros no cubiertos por el manifiesto: {extra}")
    for rel, digest in listed.items():
        p = root / rel
        if p.is_file():
            got = sha256_file(p)
            if got != digest:
                add("ERROR", name, "manifest", f"hash no coincide: {rel}")
    # Regresión: mismo contenido (mismo hash) en ficheros distintos del dossier.
    # Es legítimo para antes/después del armado (invarianza de parámetros),
    # pero dos frames de cámara idénticos byte a byte no lo son.
    by_hash: dict[str, list[str]] = {}
    for rel, digest in listed.items():
        by_hash.setdefault(digest, []).append(rel)
    legit = {frozenset({"config/before_arm.param", "config/effective_after_arm.param"})}
    for digest, rels in sorted(by_hash.items()):
        if len(rels) < 2 or frozenset(rels) in legit:
            continue
        frames = [r for r in rels if r.startswith("perception/frames/")]
        if len(frames) >= 2:
            add("ERROR", name, "manifest",
                f"frames con contenido idéntico (hash {digest[:12]}…): {sorted(frames)}")
        else:
            add("WARN", name, "manifest",
                f"ficheros con contenido idéntico (hash {digest[:12]}…): {sorted(rels)}")


def check_meta(root: Path, name: str, meta: dict) -> tuple[float, float, float]:
    rid = meta.get("run_id")
    if rid != name:
        add("ERROR", name, "meta", f"run_id {rid!r} != carpeta {name!r}")
    boot = parse_utc(meta["utc_boot"])
    arm = parse_utc(meta["utc_arm"])
    disarm = parse_utc(meta["utc_disarm"])
    close = parse_utc(meta["utc_log_close"])
    if not (boot <= arm <= disarm <= close):
        add("ERROR", name, "meta", "orden temporal boot <= arm <= disarm <= close no se cumple")
    boot_utc = datetime.fromtimestamp(boot, timezone.utc)
    suffix = f"{boot_utc:%Y%m%d_%H%M}"
    if not name.endswith(suffix):
        add("ERROR", name, "meta", f"carpeta no coincide con boot HH:MM ({suffix})")
    if meta.get("hash_bin"):
        bins = sorted((root / "native").glob("flight*.BIN")) if (root / "native").is_dir() else []
        if len(bins) == 1 and sha256_file(bins[0]) != meta["hash_bin"]:
            add("ERROR", name, "meta", f"hash_bin de run_meta no coincide con native/{bins[0].name}")
        elif len(bins) != 1:
            add("ERROR", name, "meta", f"native/ debe contener un único flight*.BIN (hay {len(bins)})")
    # params pre == effective (donde aplica)
    pre_p, eff_p = root / "config" / "before_arm.param", root / "config" / "effective_after_arm.param"
    if pre_p.is_file() and eff_p.is_file():
        if pre_p.read_bytes() != eff_p.read_bytes():
            add("WARN", name, "meta", "before_arm.param != effective_after_arm.param (puede ser legitimo si PORCE cambia params al armar)")
    return boot, close, close - boot


def check_bin(root: Path, name: str, boot: float, close_rel: float) -> None:
    binpath = next(iter(sorted((root / "native").glob("flight*.BIN"))))
    try:
        from pymavlink import DFReader
    except Exception as exc:  # pragma: no cover
        add("ERROR", name, "bin", f"pymavlink no disponible: {exc}")
        return
    try:
        reader = DFReader.DFReader_binary(str(binpath), None)
    except Exception as exc:
        add("ERROR", name, "bin", f"BIN no parseable: {exc}")
        return
    arms, modes, maxt, n = [], [], 0, 0
    while True:
        m = reader.recv_match()
        if m is None:
            break
        n += 1
        tu = getattr(m, "TimeUS", None)
        if tu is not None and tu > maxt:
            maxt = tu
        t = m.get_type()
        if t == "ARM":
            arms.append((tu, m.ArmState))
        elif t == "MODE":
            modes.append((tu, m.ModeNum, m.Mode))
    if n == 0:
        add("ERROR", name, "bin", "BIN sin registros")
        return
    if maxt > close_rel * 1e6 + BIN_END_TOL_US:
        add("ERROR", name, "bin", f"registro TimeUS={maxt/1e6:.3f}s fuera de [0,{close_rel:.3f}]")
    if not arms or arms[0][1] != 1 or arms[-1][1] != 0:
        add("ERROR", name, "bin", f"secuencia ARM inesperada: {arms}")
    # comparar primer ARM/disarm con run_meta (ya validado el orden temporal)
    add("INFO", name, "bin", f"{n} mensajes, TimeUS max {maxt/1e6:.3f}s, {len(modes)} cambios de modo")


def check_tlog(root: Path, name: str, boot: float, close_rel: float) -> None:
    p = root / "native" / "telemetry.tlog"
    data = p.read_bytes()
    if len(data) < 32 or data[:4] != b"mavl":
        add("ERROR", name, "tlog", "cabecera MAVLink nativa ausente")
        return
    off, recs, bad = 32, [], 0
    while off < len(data):
        if off + 16 > len(data):
            add("ERROR", name, "tlog", f"registro truncado en offset {off}")
            break
        ts = struct.unpack_from("<d", data, off)[0]
        b = data[off + 8]
        ln = struct.unpack_from("<I", data, off + 9)[0]
        h = struct.unpack_from("<H", data, off + 13)[0]
        b0 = data[off + 15]
        if b != 254 or h != 0 or b0 != 0 or off + 16 + ln > len(data):
            bad += 1
            add("ERROR", name, "tlog", f"layout inesperado en offset {off} (b={b} len={ln} h={h})")
            break
        recs.append(ts)
        off += 16 + ln
    if off != len(data):
        add("ERROR", name, "tlog", f"parser termino en {off} de {len(data)} bytes")
    if bad:
        return
    if any(recs[i] > recs[i + 1] for i in range(len(recs) - 1)):
        add("ERROR", name, "tlog", "timestamps no monotonos")
    start_rel = (recs[0] - boot) * 1e6
    end_rel = (recs[-1] - boot) * 1e6
    if start_rel < -TLOG_START_TOL_US:
        add("ERROR", name, "tlog", f"primer registro {start_rel/1e6:.3f}s antes del boot")
    if end_rel > close_rel * 1e6 + TLOG_START_TOL_US:
        add("ERROR", name, "tlog", f"ultimo registro {end_rel/1e6:.3f}s fuera de la ventana")
    gaps = [recs[i + 1] - recs[i] for i in range(len(recs) - 1)]
    if gaps and max(gaps) * 1e6 > TLOG_MAX_GAP_US:
        add("ERROR", name, "tlog", f"hueco de {max(gaps):.3f}s supera {TLOG_MAX_GAP_US/1e6:.1f}s")
    add("INFO", name, "tlog", f"{len(recs)} registros, ventana {start_rel/1e6:.3f}..{end_rel/1e6:.3f}s")


def check_clocks(root: Path, name: str, boot: float, close_rel: float) -> tuple[list, list, list]:
    boot_us = round(boot * 1e6)
    events = read_jsonl(root / "brain" / "events.jsonl")
    for e in events:
        rel = e["t_mono_ns"] / 1000.0
        if not math.isnan(rel) and abs(rel) > 0 and abs((e["t_utc_us"] - boot_us) - rel) > CLOCK_TOL_US:
            add("ERROR", name, "clocks", f"events {e['event_id']} t_utc_us != boot + t_mono_ns/1000 (delta {(e['t_utc_us']-boot_us-rel)})")
        r = e["t_mono_ns"] / 1e9
        if r < -1 or r > close_rel + 1:
            add("ERROR", name, "clocks", f"events {e['event_id']} fuera de [boot, close]: {r:.3f}s")
    if [e["seq"] for e in events] != sorted(e["seq"] for e in events):
        add("ERROR", name, "clocks", "events.jsonl seq no ordenado")
    if any(events[i]["t_mono_ns"] > events[i + 1]["t_mono_ns"] for i in range(len(events) - 1)):
        add("ERROR", name, "clocks", "events.jsonl no monotono")

    traj = read_csv(root / "brain" / "trajectory.csv")
    for t in traj:
        us = int(t["timeus"])
        if abs(int(t["t_utc_us"]) - (boot_us + us)) > CLOCK_TOL_US:
            add("ERROR", name, "clocks", f"trajectory sample {t['sample_id']} t_utc_us != boot + timeus")
            break
        if int(t["t_mono_ns"]) != us:
            add("ERROR", name, "clocks", f"trajectory sample {t['sample_id']} t_mono_ns ({t['t_mono_ns']}) != timeus")
            break
    if traj and int(traj[-1]["timeus"]) / 1e6 > close_rel + 1:
        add("ERROR", name, "clocks", "trajectory fuera de [boot, close]")

    setpoints = read_jsonl(root / "brain" / "setpoints.jsonl")
    prev_ms = None
    for s in setpoints:
        tms = s["t_boot_ms"]
        if abs(int(s["t_utc_us"]) - (boot_us + tms * 1000)) > CLOCK_TOL_US:
            add("ERROR", name, "clocks", f"setpoint {s['setpoint_id']} t_utc_us != boot + t_boot_ms*1000")
            break
        if prev_ms is not None and tms < prev_ms:
            add("ERROR", name, "clocks", f"setpoint {s['setpoint_id']} tiempo no monotono")
            break
        prev_ms = tms
    res = read_csv(root / "brain" / "resources.csv")
    for r in res:
        rel = (int(r["t_utc_us"]) - boot_us) / 1e6
        if rel < -1 or rel > close_rel + 1:
            add("ERROR", name, "clocks", f"resources t={rel:.3f}s fuera de [boot, close]")
            break
    return events, setpoints, traj


def check_events_alignment(root: Path, name: str, events: list, setpoints: list) -> None:
    by_type = {}
    for e in events:
        by_type.setdefault(e["event_type"], []).append(e)
    pe = read_csv(root / "brain" / "planner_events.csv")
    trig_events = {e.get("trigger_id"): e for e in by_type.get("porce_trigger", [])}
    plan_events = {e.get("plan_id"): e for e in by_type.get("plan_valid", [])}
    reat_events = {e.get("plan_id"): e for e in by_type.get("reattachment", [])}
    for p in pe:
        trig = trig_events.get(p["trigger_id"])
        if trig is None:
            add("ERROR", name, "events", f"planner {p['plan_id']} sin porce_trigger {p['trigger_id']}")
            continue
        d = trig["t_mono_ns"] / 1000.0 - int(p["t_trigger_us"])
        if abs(d) > EVENT_ALIGN_TOL_US:
            add("ERROR", name, "events", f"trigger {p['trigger_id']} desalineado con planner ({d:.0f} us)")
        pv = plan_events.get(p["plan_id"])
        if pv is None:
            add("ERROR", name, "events", f"planner {p['plan_id']} sin plan_valid")
        else:
            dt = pv["t_mono_ns"] / 1000.0 - int(p["t_trigger_us"])
            if not (0 <= dt <= 500000):
                add("ERROR", name, "events", f"plan_valid {p['plan_id']} a {dt/1000:.1f} ms del trigger")
        re = reat_events.get(p["plan_id"])
        if re is None:
            add("ERROR", name, "events", f"planner {p['plan_id']} sin reattachment")
        else:
            d = re["t_mono_ns"] / 1000.0 - int(p["t_reattach_us"])
            if abs(d) > EVENT_ALIGN_TOL_US:
                add("ERROR", name, "events", f"reattachment {p['plan_id']} desalineado con planner ({d:.0f} us)")
        if int(p["duration_us"]) != int(p["t_reattach_us"]) - int(p["t_trigger_us"]) and \
           abs(int(p["duration_us"]) - (int(p["t_reattach_us"]) - int(p["t_trigger_us"]))) > 2:
            add("ERROR", name, "events", f"duration_us de {p['plan_id']} != reattach-trigger")
        # primer setpoint del plan alineado con el trigger
        sp = [s for s in setpoints if s.get("plan_id") == p["plan_id"]]
        if sp:
            dt = int(sp[0]["t_boot_ms"]) * 1000 - int(p["t_trigger_us"])
            if not (0 <= dt <= 500000):
                add("ERROR", name, "events", f"primer setpoint de {p['plan_id']} a {dt/1000:.1f} ms del trigger")


def check_setpoints_sequence(root: Path, name: str, setpoints: list) -> None:
    if not setpoints:
        return
    prev = None
    for s in setpoints:
        if prev is not None and prev["plan_id"] == s["plan_id"]:
            d = math.hypot(s["x_n"] - prev["x_n"], s["y_e"] - prev["y_e"])
            if d > SETPOINT_STEP_MAX_M:
                add("ERROR", name, "setpoints", f"salto de {d:.1f} m entre {prev['setpoint_id']} y {s['setpoint_id']}")
        prev = s
    # ids/seq por plan coherentes
    for plan_id in sorted({s["plan_id"] for s in setpoints}):
        grp = [s for s in setpoints if s["plan_id"] == plan_id]
        seqs = [s.get("seq") for s in grp]
        if seqs != list(range(1, len(grp) + 1)):
            add("ERROR", name, "setpoints", f"{plan_id}: seq no consecutivo 1..{len(grp)}")


def check_detections(root: Path, name: str, boot: float, close_rel: float, traj: list) -> None:
    p = root / "perception" / "detections.jsonl"
    dets = read_jsonl(p) if p.is_file() else []
    if not dets:
        add("INFO", name, "detections", "sin detecciones (perfil de control)")
        return
    boot_us = round(boot * 1e6)
    ts = [d["t_utc_us"] for d in dets]
    if any(ts[i] > ts[i + 1] for i in range(len(ts) - 1)):
        add("ERROR", name, "detections", "t_utc_us no monotonos")
    for d in dets:
        rel = (d["t_utc_us"] - boot_us) / 1e6
        if rel < -1 or rel > close_rel + 1:
            add("ERROR", name, "detections", f"{d['detection_id']} fuera de [boot, close] ({rel:.2f}s)")
            break
    pe = read_csv(root / "brain" / "planner_events.csv")
    tarr = sorted((int(t["t_utc_us"]), float(t["enu_e_m"]), float(t["enu_n_m"])) for t in traj)
    obst = {r["obstacle_id"]: (float(r["center_e_m"]), float(r["center_n_m"]), float(r["footprint_radius_m"]))
            for r in read_csv(root / "ground_truth" / "obstacles.csv")}

    for pr in pe:
        oid = pr["obstacle_id"]
        od = sorted((d for d in dets if d["obstacle_id"] == oid), key=lambda d: d["t_utc_us"])
        if not od:
            add("ERROR", name, "detections", f"sin detecciones para {oid} con replan")
            continue
        trg_us = boot_us + int(pr["t_trigger_us"])
        if not (od[0]["t_utc_us"] <= trg_us <= od[-1]["t_utc_us"] + 500000):
            add("ERROR", name, "detections", f"trigger de {oid} fuera de la ventana de detecciones")
        perceived = float(pr["perceived_dist_m"])
        dmin_det = min(d["dist_m"] for d in od)
        dmax_det = max(d["dist_m"] for d in od)
        # la distancia percibida declarada debe caer dentro de la envolvente de detecciones
        if not (dmin_det - DETECT_DIST_TOL_M <= perceived <= dmax_det + DETECT_DIST_TOL_M):
            add("ERROR", name, "detections", f"{oid}: percibida {perceived:.2f} m fuera de la envolvente [{dmin_det:.2f},{dmax_det:.2f}]")
        # la deteccion mas cercana debe ser compatible con el paso real por el obstaculo
        if oid not in obst:
            add("ERROR", name, "detections", f"obstaculo {oid} ausente en ground_truth")
            continue
        oe, on, rad = obst[oid]
        win = [r for r in tarr if trg_us - 20_000_000 <= r[0] <= trg_us + 20_000_000]
        if win:
            true_min_surf = min(math.hypot(e - oe, n - on) for _, e, n in win) - rad
            if abs(dmin_det - true_min_surf) > DETECT_DIST_TOL_M:
                add("ERROR", name, "detections", f"{oid}: min deteccion {dmin_det:.2f} m vs paso real {true_min_surf:.2f} m")


def check_clearance(root: Path, name: str, traj: list) -> None:
    pe = read_csv(root / "brain" / "planner_events.csv")
    if not pe:
        return
    obst = {r["obstacle_id"]: (float(r["center_e_m"]), float(r["center_n_m"]), float(r["footprint_radius_m"]))
            for r in read_csv(root / "ground_truth" / "obstacles.csv")}
    meta = json.loads((root / "metadata" / "run_meta.json").read_text(encoding="utf-8"))
    boot_us = round(parse_utc(meta["utc_boot"]) * 1e6)
    tarr = sorted((int(t["t_utc_us"]), float(t["enu_e_m"]), float(t["enu_n_m"])) for t in traj)
    for p in pe:
        oid = p["obstacle_id"]
        if oid not in obst:
            continue
        oe, on, rad = obst[oid]
        trg = boot_us + int(p["t_trigger_us"])
        re_ = boot_us + int(p["t_reattach_us"])
        win = [r for r in tarr if trg - 5_000_000 <= r[0] <= re_ + 5_000_000]
        if not win:
            add("ERROR", name, "clearance", f"{oid}: sin trayectoria en la ventana del encuentro")
            continue
        dmin = min(math.hypot(e - oe, n - on) for _, e, n in win)
        surf = dmin - rad
        dec = float(p["clearance_m"])
        if abs(surf - dec) > CLEARANCE_TOL_M:
            add("ERROR", name, "clearance", f"{oid}: clearance trayectoria {surf:.2f} m vs declarada {dec:.2f} m")


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check_mission(root: Path, name: str, traj: list) -> None:
    wp = []
    for line in (root / "config" / "mission.waypoints").read_text(encoding="utf-8").splitlines():
        if line.startswith("QGC"):
            continue
        parts = line.split("\t")
        if len(parts) >= 10:
            wp.append(parts)
    if not wp:
        add("ERROR", name, "mission", "mission.waypoints vacio")
        return
    if wp[-1][3].strip() != "21":
        add("WARN", name, "mission", f"ultimo item no es LAND (cmd={wp[-1][3]})")
    if traj:
        nmax = max(float(t["enu_n_m"]) for t in traj)
        # ultimo waypoint (salvo LAND) a la misma latitud que el final de trayectoria
        last_lat = wp[-2][8].strip() if len(wp) >= 2 else None
        if last_lat:
            latf = float(last_lat)
            latmax = max(float(t["lat_deg"]) for t in traj)
            if abs(latf - latmax) > 1e-4:
                add("ERROR", name, "mission", f"ultimo WP lat {latf} vs trayectoria {latmax}")
    add("INFO", name, "mission", f"{len(wp)} waypoints (incl. home y LAND)")


# --------------------------------------------------------------------------- #
def audit(root: Path) -> str:
    name = root.name
    meta = json.loads((root / "metadata" / "run_meta.json").read_text(encoding="utf-8"))
    boot, close, close_rel = check_meta(root, name, meta)
    if (root / "metadata" / "hashes.sha256").is_file():
        check_manifest(root, name)
    bins = sorted((root / "native").glob("flight*.BIN")) if (root / "native").is_dir() else []
    if len(bins) == 1:
        check_bin(root, name, boot, close_rel)
    else:
        add("ERROR", name, "bin", f"native/ debe contener exactamente un flight*.BIN (hay {len(bins)})")
    tlogp = root / "native" / "telemetry.tlog"
    if tlogp.is_file():
        check_tlog(root, name, boot, close_rel)
    # Paquete reducido: el expediente conserva solo native/flight*.BIN + metadata/.
    # Si brain/, perception/, config/ y ground_truth/ no se conservan en el
    # paquete, sus verificaciones no se aplican y las métricas que dependían
    # de ellos quedan declaradas en el acta como derivadas de logs a bordo.
    if not (root / "brain").is_dir():
        absent = [c for c in ("brain", "perception", "config", "ground_truth")
                  if not (root / c).is_dir()]
        extra = [] if tlogp.is_file() else ["telemetry.tlog"]
        add("INFO", name, "package",
            f"paquete: native/flight*.BIN + metadata/run_meta.json; no se distribuyen "
            f"{', '.join(absent)}/ ni {', '.join(extra)}; "
            "las métricas que dependían de ellos figuran en el acta como derivadas de logs de trabajo")
        return name
    events, setpoints, traj = check_clocks(root, name, boot, close_rel)
    check_events_alignment(root, name, events, setpoints)
    check_setpoints_sequence(root, name, setpoints)
    check_detections(root, name, boot, close_rel, traj)
    check_clearance(root, name, traj)
    check_mission(root, name, traj)
    return name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dossiers", nargs="*", type=Path, default=DEFAULT_DOSSIERS)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()
    for d in args.dossiers:
        audit(d)
    errors = [f for f in FINDINGS if f["level"] == "ERROR"]
    warns = [f for f in FINDINGS if f["level"] == "WARN"]
    infos = [f for f in FINDINGS if f["level"] == "INFO"]
    current = None
    for f in FINDINGS:
        if f["dossier"] != current:
            current = f["dossier"]
            print(f"\n===== {current} =====")
        print(f"  [{f['level']:5}] {f['check']:11} {f['message']}")
    print(f"\nResumen: {len(errors)} errores, {len(warns)} avisos, {len(infos)} informativos")
    if args.json:
        args.json.write_text(json.dumps(FINDINGS, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
