"""Full-mission map of the audited simulation run with the rejoin highlighted.

Equivalent of the original manuscript's "Middle Stages. Rejoining and new
detections" mission map (Figure 6 of the submitted paper), regenerated from the
logged audited run 20260731_061815_cow:

  * panel (a): whole mission (HOME + inspection waypoints + landing) with the
    logged flown path and the executed evasion segment;
  * panel (b): zoom of the rejoin detail centered on the obstacle estimate used
    at the first trigger (same content as the existing 12 m-reference figure).

Everything is logged telemetry/estimates: nothing is treated as independent
ground truth and no physical clearance is claimed.
"""

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "evidence" / "zero_trust_runs" / "20260731_061815_cow"
MISSION = ROOT / "missions" / "ejea_canonical_523m.waypoints"
OUT = ROOT / "paper" / "revision" / "Main" / "images"
OUT.mkdir(parents=True, exist_ok=True)

R_EARTH_M = 6_371_000.0
SAFETY_RADIUS_M = 12.0
FG = "#202b3c"
BLUE = "#2674a8"
ORANGE = "#dd6b20"
GREEN = "#2f855a"
RED = "#b43c3c"
PURPLE = "#7651a8"
GREY = "#8493a5"


def enu(lat, lon, lat0, lon0):
    east = math.radians(lon - lon0) * R_EARTH_M * math.cos(math.radians(lat0))
    north = math.radians(lat - lat0) * R_EARTH_M
    return east, north


def read_mission():
    points = []
    with MISSION.open(encoding="utf-8", errors="replace") as f:
        next(f)
        for line in f:
            cols = line.split()
            if len(cols) >= 12:
                points.append({"seq": int(cols[0]), "command": int(cols[3]),
                               "lat": float(cols[8]), "lon": float(cols[9])})
    home = next(p for p in points if p["seq"] == 0)
    wps = [p for p in points if p["command"] == 16 and p["seq"] > 0]
    return home, wps


with (RUN / "brain" / "trajectory.csv").open(encoding="utf-8", newline="") as f:
    trajectory = list(csv.DictReader(f))
with (RUN / "brain" / "events.jsonl").open(encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]
home, waypoints = read_mission()
t_origin = float(trajectory[0]["ts"])
LAT0, LON0 = home["lat"], home["lon"]

snapshots = [e for e in events if e.get("kind") == "decision_snapshot"
             and e.get("nearest_distance_m") is not None]
triggers = [e for e in events if e.get("kind") == "evasion_route_generated"]
completed = next(e for e in events if e.get("kind") == "evasion_completed")
start_event = next(e for e in events if e.get("kind") == "evasion_state_change"
                   and e.get("active") is True)
end_event = next(e for e in events if e.get("kind") == "evasion_state_change"
                 and e.get("active") is False)
first_trigger = triggers[0]
trigger_t = float(first_trigger["ts"])


def obstacle_fix(event):
    samples = event.get("obs_sample") or event.get("sample") or []
    if not samples:
        nearest = min(snapshots, key=lambda e: abs(e["ts"] - event["ts"]))
        samples = nearest.get("obs_sample") or []
    if not samples:
        raise SystemExit("No logged obstacle position for event %s" % event.get("kind"))
    return float(samples[0]["lat"]), float(samples[0]["lon"])


# Obstacle estimate used at the first trigger (the position that governed the
# evasion), consistent with the zoom figure already in the manuscript.
trigger_snap = min(snapshots, key=lambda e: abs(e["ts"] - trigger_t))
obs_lat, obs_lon = obstacle_fix(trigger_snap)

# --- flown path (logged telemetry, airborne) -------------------------------------
air = [r for r in trajectory if r["mode"] == "GUIDED" and float(r["rel_alt"]) > 5]
track_e = np.asarray([enu(float(r["lat"]), float(r["lon"]), LAT0, LON0)[0] for r in air])
track_n = np.asarray([enu(float(r["lat"]), float(r["lon"]), LAT0, LON0)[1] for r in air])
track_t = np.asarray([float(r["ts"]) for r in air]) - t_origin
track_active = np.asarray([r["evasion_active"] == "1" for r in air])

# --- reattachment instant ---------------------------------------------------------
reattach_t = float(end_event["ts"]) - t_origin
completed_t = float(completed["ts"]) - t_origin
trigger_rel = trigger_t - t_origin

# rejoin marker: first logged airborne point after the evasion flag is cleared
i_rejoin = int(np.argmax(track_t >= reattach_t))

# --- verification prints ----------------------------------------------------------
wp_e = np.asarray([enu(p["lat"], p["lon"], LAT0, LON0)[0] for p in waypoints])
wp_n = np.asarray([enu(p["lat"], p["lon"], LAT0, LON0)[1] for p in waypoints])
# distance of each mission waypoint to the flown path
dmin = []
for xe, xn in zip(wp_e, wp_n):
    dmin.append(float(np.min(np.hypot(track_e - xe, track_n - xn))))
print("mission=%s: %d waypoints; max WP-to-flown-path distance %.1f m" %
      (MISSION.name, len(waypoints), max(dmin)))
print("evasion window [%.1f, %.1f] s; trigger %.2f m; first post-rejoin row t=%.1f s"
      % (float(air[0]["ts"]) - t_origin, reattach_t, float(first_trigger["nearest_distance_m"]),
         track_t[i_rejoin]))

# --- capture metadata (status box at the reattachment instant) ---------------------
cap = air[min(i_rejoin, len(air) - 1)]
i_a, i_b = max(0, i_rejoin - 3), min(len(air) - 1, i_rejoin + 3)
dxh = track_e[i_b] - track_e[i_a]
dyh = track_n[i_b] - track_n[i_a]
hdg = (90.0 - math.degrees(math.atan2(dyh, dxh))) % 360.0

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.0,
    "axes.titlesize": 9.2, "axes.titleweight": "bold",
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7.2,
    "axes.spines.top": False, "axes.spines.right": False,
})

fig, (ax, az) = plt.subplots(1, 2, figsize=(10.6, 5.6), dpi=300,
                             gridspec_kw={"width_ratios": [1.0, 1.0]})

# ============================ panel (a): full mission ==============================
wp_xy = np.column_stack([wp_e, wp_n])
ax.plot(wp_xy[:, 0], wp_xy[:, 1], "--", color=BLUE, lw=1.3,
        marker=".", ms=3.0, label="Nominal corridor (%d inspection waypoints)" % len(waypoints))
for i, (xe, xn) in enumerate(zip(wp_e, wp_n), start=1):
    ax.annotate("WP%d" % i, (xe, xn), textcoords="offset points", xytext=(7, 4),
                fontsize=6.6, color="#3b5a7a")
pre = track_t < (float(start_event["ts"]) - t_origin)
ev_mask = (track_t >= (float(start_event["ts"]) - t_origin)) & (track_t <= reattach_t)
post = track_t > reattach_t
ax.plot(track_e[pre], track_n[pre], color="#5a6472", lw=1.15, label="Flown path (logged)")
ax.plot(track_e[ev_mask], track_n[ev_mask], color=ORANGE, lw=3.4,
        label="Executed evasion segment")
ax.plot(track_e[post], track_n[post], color="#5a6472", lw=1.15)
# rejoin marker
ax.plot(track_e[i_rejoin], track_n[i_rejoin], marker="D", ms=6.0, color=GREEN,
        mec="white", mew=0.7, zorder=6)
ax.annotate("route\nreattachment", (track_e[i_rejoin], track_n[i_rejoin]),
            xytext=(380.0, -480.0), fontsize=7.2, color=GREEN, fontweight="bold",
            ha="left", arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.0})
# obstacle estimate + configured radius
oe, on = enu(obs_lat, obs_lon, LAT0, LON0)
ax.add_patch(Circle((oe, on), SAFETY_RADIUS_M, facecolor=RED, edgecolor=RED,
                    alpha=0.14, lw=1.1, ls="--", zorder=2,
                    label="Configured 12 m radius"))
ax.plot(oe, on, marker="x", color=RED, ms=7.5, mew=1.8,
        label="Obstacle estimate at first trigger")
ax.plot([0], [0], marker="^", ms=7, color=BLUE, mec="white", mew=0.5,
        zorder=5, label="HOME / takeoff")

ax.set_aspect("equal", adjustable="box")
ax.grid(alpha=0.23, ls=":", lw=0.55)
ax.set_xlabel("East (m)")
ax.set_ylabel("North (m)")
ax.set_title("(a) Full logged mission with rejoin (run 20260731_061815)",
             loc="left", color=FG, pad=5)
ax.legend(loc="upper right", fontsize=6.4, framealpha=0.95)

# ============================ panel (b): rejoin detail =============================
te = np.asarray([enu(float(r["lat"]), float(r["lon"]), obs_lat, obs_lon)[0] for r in air])
tn = np.asarray([enu(float(r["lat"]), float(r["lon"]), obs_lat, obs_lon)[1] for r in air])
wze = np.asarray([enu(p["lat"], p["lon"], obs_lat, obs_lon)[0] for p in waypoints])
wzn = np.asarray([enu(p["lat"], p["lon"], obs_lat, obs_lon)[1] for p in waypoints])
az.plot(te[pre], tn[pre], color=BLUE, lw=1.55, label="Logged GPS before evasion")
az.plot(te[ev_mask], tn[ev_mask], color=ORANGE, lw=2.35,
        label="Logged GPS while evasion active")
az.plot(te[post], tn[post], color=GREEN, lw=1.55, label="Logged GPS after evasion")
az.plot(wze, wzn, "--", color=GREY, lw=0.9, marker=".", ms=2.5,
        label="Mission waypoint corridor")
az.add_patch(Circle((0, 0), SAFETY_RADIUS_M, facecolor=RED, edgecolor=RED,
                    alpha=0.13, lw=1.4, ls="--", zorder=2,
                    label="Configured 12 m radius"))
az.plot(0, 0, marker="x", color=RED, ms=8, mew=1.8,
        label="Obstacle estimate at first trigger")
min_active = min((e for e in snapshots if start_event["ts"] <= e["ts"] <= completed["ts"]),
                 key=lambda e: e["nearest_distance_m"])
min_t = float(min_active["ts"])
for ts, label, color, marker in [
        (trigger_t, "First replan", PURPLE, "s"),
        (float(completed["ts"]), "Evasion completed", GREEN, "D"),
        (float(end_event["ts"]), "Evasion flag cleared", GREEN, "o")]:
    k = int(np.argmin(np.abs(track_t - (ts - t_origin))))
    p = (te[k], tn[k])
    az.scatter(p[0], p[1], s=28, marker=marker, color=color,
               edgecolor="white", linewidth=0.6, zorder=6, label=label)
    offset = {"First replan": (7, 7), "Evasion completed": (8, -17),
              "Evasion flag cleared": (8, 9)}[label]
    az.annotate(label, p, xytext=offset, textcoords="offset points",
                fontsize=7.4, color=FG)
az.set_xlim(-75, 75)
az.set_ylim(-75, 75)
az.set_aspect("equal", adjustable="box")
az.set_xlabel("East from obstacle estimate at first trigger (m)")
az.set_ylabel("North from obstacle estimate at first trigger (m)")
az.set_title("(b) Rejoin detail", loc="left", color=FG, pad=5)
az.grid(alpha=0.24, ls=":", lw=0.6)
az.legend(loc="lower left", fontsize=6.4, framealpha=0.93)

fig.suptitle("Logged simulation mission: evasion and route reattachment (audited run 20260731_061815)",
             fontsize=10.5, fontweight="bold", color=FG, y=0.995)
fig.text(0.5, 0.008,
         "Telemetry and obstacle location are logged estimates; the circle is the configured planner radius, not ground-truth separation.",
         ha="center", va="bottom", fontsize=6.8, color="#424b59")
fig.tight_layout(rect=(0.0, 0.03, 1.0, 0.94))
out_path = OUT / "sim_mission_map_rejoin_20260731_061815.png"
fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("Wrote", out_path)
