"""Render simulation encounter figures from the archived native run logs.

Inputs are the telemetry and controller event records for run
20260731_061815_cow. The figures show logged GPS positions and logged
perceived-obstacle positions; they do not treat either as independent ground
truth or claim a physical clearance measurement.
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
# Mission of the audited run: ejea_canonical_523m matches the logged trajectory
# (home 42.229695/-1.235085 and terminal WP coincide with the track bounds;
# max waypoint-to-flown-path distance ~5.9 m). cow_evasion_545m.waypoints is an
# older mission excerpt and does not match the audited run.
MISSION = ROOT / "missions" / "ejea_canonical_523m.waypoints"
OUT = ROOT / "paper" / "revision" / "Main" / "images"
OUT.mkdir(parents=True, exist_ok=True)

R_EARTH_M = 6_371_000.0
SAFETY_RADIUS_M = 12.0
REACTION_BASE_M = 45.0
REACTION_SPEED_GAIN_S = 2.0


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

snapshots = [e for e in events if e.get("kind") == "decision_snapshot"
             and e.get("nearest_distance_m") is not None]
triggers = [e for e in events if e.get("kind") == "evasion_route_generated"]
completed = next(e for e in events if e.get("kind") == "evasion_completed")
start_event = next(e for e in events if e.get("kind") == "evasion_state_change"
                   and e.get("active") is True)
end_event = next(e for e in events if e.get("kind") == "evasion_state_change"
                 and e.get("active") is False)
first_detection = snapshots[0]
first_trigger = triggers[0]
active_snapshots = [e for e in snapshots if start_event["ts"] <= e["ts"] <= completed["ts"]]
min_snapshot = min(active_snapshots, key=lambda e: e["nearest_distance_m"])
last_active = active_snapshots[-1]
end_snapshot = min(snapshots, key=lambda e: abs(e["ts"] - end_event["ts"]))


def obstacle_fix(event):
    samples = event.get("obs_sample") or event.get("sample") or []
    if not samples:
        # The state transition can be timestamped between decision snapshots.
        nearest = min(snapshots, key=lambda e: abs(e["ts"] - event["ts"]))
        samples = nearest.get("obs_sample") or []
    if not samples:
        raise SystemExit("No logged obstacle position for event %s" % event.get("kind"))
    return float(samples[0]["lat"]), float(samples[0]["lon"])

reaction_horizon = float(first_detection["reaction_distance_eval_m"])
first_detection_distance = float(first_detection["nearest_distance_m"])
first_trigger_distance = float(first_trigger["nearest_distance_m"])
minimum_logged_distance = float(min_snapshot["nearest_distance_m"])
print("run=20260731_061815_cow; trajectory_rows=%d; obstacle_fixes=%d" %
      (len(trajectory), sum(len(e.get("sample") or e.get("obs_sample") or []) for e in events)))
print("first logged detection %.2f m; trigger %.2f m; min logged perceived distance %.2f m; "
      "evasion complete %.2f s after trajectory start" %
      (first_detection_distance, first_trigger_distance, minimum_logged_distance,
       completed["ts"] - t_origin))


gps_ll = [(float(r["lat"]), float(r["lon"])) for r in trajectory]
track_t = np.asarray([float(r["ts"]) - t_origin for r in trajectory])

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.0,
    "axes.titlesize": 9.2, "axes.titleweight": "bold",
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7.2,
    "axes.spines.top": False, "axes.spines.right": False,
})
FG = "#202b3c"
BLUE = "#2674a8"
ORANGE = "#dd6b20"
GREEN = "#2f855a"
RED = "#b43c3c"
PURPLE = "#7651a8"


def closest_track_row(ts):
    return min(range(len(trajectory)), key=lambda i: abs(float(trajectory[i]["ts"]) - ts))


def active_at(ts):
    return start_event["ts"] <= ts < end_event["ts"]


def draw_snapshot(ax, ts, title, badge, *, final=False):
    # Draw only measured track points available at this logged instant.
    snap = min(snapshots, key=lambda e: abs(e["ts"] - ts))
    obs_lat, obs_lon = obstacle_fix(snap)
    track = np.asarray([enu(lat, lon, obs_lat, obs_lon) for lat, lon in gps_ll])
    wp_xy = np.asarray([enu(p["lat"], p["lon"], obs_lat, obs_lon) for p in waypoints])
    idx = closest_track_row(ts)
    points = track[:idx + 1]
    times = track_t[:idx + 1]
    act = np.asarray([active_at(t_origin + t) for t in times])
    ax.plot(points[~act, 0], points[~act, 1], color=BLUE, lw=1.5,
            label="Logged GPS, normal guidance")
    ax.plot(points[act, 0], points[act, 1], color=ORANGE, lw=2.2,
            label="Logged GPS, evasion active")
    if len(wp_xy):
        ax.plot(wp_xy[:, 0], wp_xy[:, 1], "--", color="#8493a5", lw=0.9,
                marker=".", ms=2.5, label="Mission waypoints")
    ax.add_patch(Circle((0, 0), SAFETY_RADIUS_M, facecolor=RED, edgecolor=RED,
                        alpha=0.13, lw=1.2, ls="--", zorder=2))
    ax.plot(0, 0, marker="x", color=RED, ms=6.5, mew=1.6,
            label="Obstacle estimate at this logged state")
    ax.plot(points[-1, 0], points[-1, 1], marker="o", ms=4.8,
            color=GREEN if final else (ORANGE if active_at(ts) else BLUE),
            mec="white", mew=0.55, zorder=5)
    ax.set_title(title, loc="left", color=FG, pad=5)
    ax.text(0.98, 0.98, badge, transform=ax.transAxes, ha="right", va="top",
            color=FG, fontsize=7.3, fontweight="bold",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white",
                  "edgecolor": "#c4ccd5", "alpha": 0.94})
    ax.set_xlim(-85, 85)
    ax.set_ylim(-85, 85)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.23, ls=":", lw=0.55)


first_detection_t = float(first_detection["ts"])
trigger_t = float(first_trigger["ts"])
minimum_t = float(min_snapshot["ts"])
last_active_t = float(last_active["ts"])
completion_t = float(completed["ts"])
reattach_t = float(end_event["ts"])
panels = [
    (max(t_origin, first_detection_t - 1.0), "(a) Before obstacle report", "Nominal"),
    (first_detection_t, "(b) Obstacle reported; no replan", "%.1f m; horizon %.1f m" %
     (first_detection_distance, reaction_horizon)),
    (trigger_t, "(c) First logged replan", "%.1f m" % first_trigger_distance),
    (minimum_t, "(d) Evasion active", "t = %.1f s" % (minimum_t - t_origin)),
    (last_active_t, "(e) Evasion near completion", "t = %.1f s" %
     (last_active_t - t_origin)),
    (reattach_t, "(f) Reattachment after evasion", "%.1f s" %
     (reattach_t - t_origin)),
]

fig, axes = plt.subplots(3, 2, figsize=(9.6, 10.4), dpi=240)
for ax, (ts, title, badge) in zip(axes.flat, panels):
    draw_snapshot(ax, ts, title, badge, final=(ts >= reattach_t))
handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False,
           bbox_to_anchor=(0.5, 0.047), columnspacing=1.8, handlelength=2.0)
fig.suptitle("Logged simulation encounter and route reattachment (20260731_061815)",
             fontsize=12, fontweight="bold", color=FG, y=0.985)
fig.supxlabel("East from logged obstacle estimate (m)", fontsize=8.5, y=0.09)
fig.supylabel("North from logged obstacle estimate (m)", fontsize=8.5, x=0.018)
fig.text(0.5, 0.012,
         "Each panel is centered on its contemporaneous obstacle estimate; the 12 m disk is configured, not surveyed clearance.",
         ha="center", va="bottom", fontsize=7.2, color="#424b59")
fig.tight_layout(rect=(0.055, 0.115, 0.99, 0.95), h_pad=1.15, w_pad=1.0)
fig.savefig(OUT / "Imagenes_resultados_main.jpg", dpi=240,
            pil_kwargs={"quality": 94, "optimize": True})
plt.close(fig)

# Figure 13: local detail centered on the obstacle estimate used at the first
# trigger, with phase boundaries taken from state-change/completion events.
trigger_obs_lat, trigger_obs_lon = obstacle_fix(min(snapshots, key=lambda e: abs(e["ts"] - trigger_t)))
track = np.asarray([enu(lat, lon, trigger_obs_lat, trigger_obs_lon) for lat, lon in gps_ll])
wp_xy = np.asarray([enu(p["lat"], p["lon"], trigger_obs_lat, trigger_obs_lon) for p in waypoints])
fig, ax = plt.subplots(figsize=(6.6, 5.3), dpi=300)
pre = track_t < (start_event["ts"] - t_origin)
ev_mask = (track_t >= (start_event["ts"] - t_origin)) & (track_t <= (end_event["ts"] - t_origin))
post = track_t > (end_event["ts"] - t_origin)
ax.plot(track[pre, 0], track[pre, 1], color=BLUE, lw=1.55,
        label="Logged GPS before evasion")
ax.plot(track[ev_mask, 0], track[ev_mask, 1], color=ORANGE, lw=2.35,
        label="Logged GPS while evasion active")
ax.plot(track[post, 0], track[post, 1], color=GREEN, lw=1.55,
        label="Logged GPS after evasion")
ax.plot(wp_xy[:, 0], wp_xy[:, 1], "--", color="#8493a5", lw=0.9,
        marker=".", ms=2.5, label="Mission waypoint corridor")
ax.add_patch(Circle((0, 0), SAFETY_RADIUS_M, facecolor=RED, edgecolor=RED,
                    alpha=0.13, lw=1.4, ls="--", zorder=2,
                    label="Configured 12 m radius"))
ax.plot(0, 0, marker="x", color=RED, ms=8, mew=1.8,
        label="Obstacle estimate at first trigger")
for ts, label, color, marker in [
        (trigger_t, "First replan", PURPLE, "s"),
        (completion_t, "Evasion completed", GREEN, "D"),
        (reattach_t, "Evasion flag cleared", GREEN, "o")]:
    p = track[closest_track_row(ts)]
    ax.scatter(p[0], p[1], s=28, marker=marker, color=color,
               edgecolor="white", linewidth=0.6, zorder=6, label=label)
    offset = {"First replan": (7, 7), "Evasion completed": (8, -17),
              "Evasion flag cleared": (8, 9)}[label]
    ax.annotate(label, p, xytext=offset,
                textcoords="offset points", fontsize=7.4, color=FG)
ax.set_xlim(-75, 75)
ax.set_ylim(-75, 75)
ax.set_aspect("equal", adjustable="box")
ax.set_xlabel("East from obstacle estimate at first trigger (m)")
ax.set_ylabel("North from obstacle estimate at first trigger (m)")
ax.set_title("Logged route reattachment (run 20260731_061815)", pad=10,
             fontweight="bold", color=FG)
ax.grid(alpha=0.24, ls=":", lw=0.6)
ax.legend(loc="lower left", fontsize=7.1, framealpha=0.93, ncol=1)
fig.text(0.5, 0.012,
         "Telemetry and obstacle locations are logged estimates; circle denotes configured planner radius, not ground-truth separation.",
         ha="center", va="bottom", fontsize=7.1, color="#424b59")
fig.tight_layout(rect=(0.02, 0.045, 0.98, 0.98))
fig.savefig(OUT / "transcurso_de_mision_(nuevo_obs_detectado)_12m_reference.png",
            dpi=300, bbox_inches="tight")
plt.close(fig)

print("Wrote logged figures:", OUT / "Imagenes_resultados_main.jpg")
print("Wrote logged figures:", OUT / "transcurso_de_mision_(nuevo_obs_detectado)_12m_reference.png")
