import csv, json, math, os, sys, glob

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "evidence", "zero_trust_runs")

def hav(lat1, lon1, lat2, lon2):
    R = 6371008.8
    p = math.pi / 180
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))

def analyze(run_dir):
    out = {"run": os.path.basename(run_dir)}
    traj = os.path.join(run_dir, "brain", "trajectory.csv")
    ev = os.path.join(run_dir, "brain", "events.jsonl")
    if not os.path.exists(traj):
        out["error"] = "no trajectory.csv"
        return out
    rows = []
    with open(traj, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        out["error"] = "empty trajectory"
        return out
    ts0 = float(rows[0]["ts"]); ts1 = float(rows[-1]["ts"])
    out["duration_s"] = round(ts1 - ts0, 1)
    path = 0.0
    prev = None
    for r in rows:
        if r["lat"] in ("", None) or r["lon"] in ("", None):
            continue
        cur = (float(r["lat"]), float(r["lon"]))
        if prev is not None:
            path += hav(prev[0], prev[1], cur[0], cur[1])
        prev = cur
    out["path_m"] = round(path, 1)
    # min nearest perceived obstacle distance while obstacle present
    mind = None
    for r in rows:
        v = r.get("nearest_obs_dist_m")
        if v not in ("", None):
            try:
                d = float(v)
                if mind is None or d < mind:
                    mind = d
            except ValueError:
                pass
    out["min_nearest_obs_m"] = None if mind is None else round(mind, 1)
    # evasion seconds from trajectory sampling
    ev_rows = sum(1 for r in rows if r.get("evasion_active") in ("1", "True", "true"))
    out["evasion_active_rows_x0.5s"] = round(ev_rows * 0.5, 1)
    # events
    if os.path.exists(ev):
        n_routes = 0; first_trigger = None; ev_start = None; ev_end = None
        cfg = None
        wps = None
        with open(ev, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                k = o.get("kind")
                if k == "brain_config":
                    cfg = {kk: o.get(kk) for kk in (
                        "safety_distance_m", "evasion_reaction_base_m", "evasion_reaction_speed_gain_s",
                        "evasion_reaction_min_m", "evasion_reaction_max_m", "control_loop_period_s",
                        "evasion_replan_min_interval_s", "evasion_route_point_reached_m",
                        "obs_track_ttl_static_s", "obs_track_ttl_dynamic_s", "evasion_failsafe_min_dist_m",
                        "evasion_planner_obs_max_distance_m", "evasion_planner_obs_max_count",
                        "planner_grid_radius_cells", "workflow", "control_mode")}
                elif k == "evasion_route_generated":
                    n_routes += 1
                    d = o.get("nearest_distance_m")
                    if first_trigger is None and d is not None:
                        first_trigger = round(d, 1)
                elif k == "evasion_state_change" and o.get("active"):
                    ev_start = o.get("ts")
                elif k == "evasion_completed":
                    ev_end = o.get("ts")
                elif k == "mission_loaded":
                    wps = o
        out["n_replans"] = n_routes
        out["first_trigger_m"] = first_trigger
        out["evasion_s"] = None if (ev_start is None or ev_end is None) else round(ev_end - ev_start, 1)
        if cfg:
            out["config"] = cfg
    return out

def main():
    runs = sorted(glob.glob(os.path.join(ROOT, "2026073*_c*")))
    results = [analyze(r) for r in runs]
    print(json.dumps(results, indent=1))
    out_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "analysis", "sim_campaign_recomputed.csv")
    cols = ["run", "duration_s", "path_m", "min_nearest_obs_m", "evasion_s",
            "evasion_active_rows_x0.5s", "n_replans", "first_trigger_m", "error"]
    with open(out_csv, "w", newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    print("WROTE", out_csv)

if __name__ == "__main__":
    main()
