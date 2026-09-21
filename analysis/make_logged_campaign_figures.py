# make_logged_campaign_figures.py
# Figuras de resultados del paper estatico (MDPI) a partir de los LOGS REALES de la
# campanya (run auditado 20260731_061815_cow, runs/zero_trust en runtime;
# copia historica consolidada en local_data/evidence/pipeline_logs/zero_trust):
#   A) fig_static_mission_route.png      - corredor nominal vs trayectoria volada +
#                                          segmento de evasion ejecutado (A* real) + inset
#   B) fig_static_clearance_timeseries.png - nearest_obs_dist_m logueado vs tiempo
#   C) transcurso_mision_nuevo_obs.png   - vista de depuracion (estilo viz_recorder)
#                                          en el instante de reenganche, offline desde logs
# Estas figuras sustituyen a las derivadas del re-render cow_evasion_v2
# (make_static_results_figures.py), que ahora solo se usa para el multipanel de
# percepcion (Figure 1) y los closeups.
import csv
import json
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root (staging)
RUN = os.path.join(ROOT, "evidence", "zero_trust_runs", "20260731_061815_cow")
MISSION = os.path.join(ROOT, "missions", "cow_evasion_545m.waypoints")
IMG = os.path.join(ROOT, "analysis", "regen_output")
os.makedirs(IMG, exist_ok=True)

R_EARTH = 6371000.0


def latlon_to_m(lat, lon, lat0, lon0):
    return (math.radians(lon - lon0) * R_EARTH * math.cos(math.radians(lat0)),
            math.radians(lat - lat0) * R_EARTH)


# --- mission file (QGC WPL 110): item 0 home, 1 takeoff, 2-8 inspection WPs, 9 RTL ----
wps = []
with open(MISSION) as f:
    next(f)
    for line in f:
        p = line.split()
        if len(p) >= 12:
            wps.append((int(p[0]), int(p[3]), float(p[8]), float(p[9])))
HOME = next((la, lo) for i, c, la, lo in wps if i == 0)
INSPECTION_WPS = [(la, lo) for i, c, la, lo in wps if c == 16 and i > 0]

# --- logged trajectory ---------------------------------------------------------------
rows = list(csv.DictReader(open(os.path.join(RUN, "brain", "trajectory.csv"),
                               encoding="utf-8", errors="replace")))
t0 = float(rows[0]["ts"])
air = [r for r in rows if r["mode"] == "GUIDED" and float(r["rel_alt"]) > 5]
fly = [(float(r["lat"]), float(r["lon"]), float(r["ts"]), r["evasion_active"] == "1")
       for r in air]

# --- logged perceived obstacle positions (decision snapshots + ingests) --------------
obs_pts = []
snapshots = []
for line in open(os.path.join(RUN, "brain", "events.jsonl"), encoding="utf-8", errors="replace"):
    try:
        j = json.loads(line)
    except Exception:
        continue
    k = j.get("kind")
    if k == "decision_snapshot":
        snapshots.append(j)
        for s in (j.get("obs_sample") or []):
            obs_pts.append((s["lat"], s["lon"]))
    elif k == "obstacle_ingest":
        for s in (j.get("sample") or []):
            obs_pts.append((s["lat"], s["lon"]))
obs_lat = float(np.mean([p[0] for p in obs_pts]))
obs_lon = float(np.mean([p[1] for p in obs_pts]))
print("perceived obstacle: %.7f, %.7f  (n=%d logged fixes)" % (obs_lat, obs_lon, len(obs_pts)))

# trigger info
trig = next(j for j in snapshots if j.get("decision_triggered"))
print("first trigger at %.1f m, t=%.1f s" % (trig["nearest_distance_m"], trig["ts"] - t0))

# estilo comun
FG = "#1a2233"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "text.color": FG, "axes.edgecolor": "#5b6575",
    "axes.labelcolor": FG, "xtick.color": FG, "ytick.color": FG,
    "axes.titlesize": 13, "axes.titleweight": "bold", "font.size": 10,
})
C_NOM = "#3a7ca5"
C_FLY = "#c96a2b"
C_OBS = "#a03030"

to_m = lambda la, lo: latlon_to_m(la, lo, obs_lat, obs_lon)

# =================================================================================
# A) fig_static_mission_route.png (logged audited run)
# =================================================================================
nom = np.array([to_m(la, lo) for la, lo in INSPECTION_WPS])
path = np.array([to_m(la, lo) for la, lo, ts, e in fly])
ev = np.array([to_m(la, lo) for la, lo, ts, e in fly if e])
home_xy = np.array(to_m(*HOME))

fig, ax = plt.subplots(figsize=(9.2, 6.4), dpi=200)
ax.plot(nom[:, 0], nom[:, 1], "--", color=C_NOM, lw=1.6,
        label="Nominal corridor (7 inspection waypoints)")
ax.plot(nom[:, 0], nom[:, 1], "o", color=C_NOM, ms=4)
ax.plot(path[:, 0], path[:, 1], "-", color="#666666", lw=1.4, label="Flown path (logged telemetry)")
ax.plot(ev[:, 0], ev[:, 1], "-", color=C_FLY, lw=3.2,
        label="Executed evasion segment (23 logged A* replans)")
ax.add_patch(Circle((0, 0), 12, fill=True, alpha=0.18, color=C_OBS, zorder=3))
ax.add_patch(Circle((0, 0), 12, fill=False, ls=":", lw=1.2, color=C_OBS, zorder=4))
ax.plot(0, 0, "x", color=C_OBS, ms=9, mew=2.4, zorder=5,
        label="Perceived cattle position (12 m safety radius)")
ax.annotate("WP1", nom[0], textcoords="offset points", xytext=(8, -2), fontsize=9)
ax.annotate("WP7", nom[-1], textcoords="offset points", xytext=(8, -2), fontsize=9)
# encuadre en el corredor de inspeccion + segmento de evasion (la vuelta a casa fuera)
pad = 70.0
xs = np.concatenate([nom[:, 0], ev[:, 0]])
ys = np.concatenate([nom[:, 1], ev[:, 1]])
ax.set_xlim(xs.min() - pad, xs.max() + pad)
ax.set_ylim(ys.min() - pad, ys.max() + pad)

axins = ax.inset_axes([0.05, 0.05, 0.40, 0.44])
axins.plot(nom[:, 0], nom[:, 1], "--", color=C_NOM, lw=1.4)
axins.plot(path[:, 0], path[:, 1], "-", color="#666666", lw=1.2)
axins.plot(ev[:, 0], ev[:, 1], "-", color=C_FLY, lw=3.0)
axins.add_patch(Circle((0, 0), 12, fill=True, alpha=0.18, color=C_OBS))
axins.add_patch(Circle((0, 0), 12, fill=False, ls=":", lw=1.1, color=C_OBS))
axins.plot(0, 0, "x", color=C_OBS, ms=8, mew=2.2)
axins.set_xlim(-70, 70)
axins.set_ylim(-55, 55)
axins.set_title("evasion window", fontsize=9)
axins.grid(alpha=0.3, ls=":")
ax.indicate_inset_zoom(axins, edgecolor="#888888")

ax.set_xlabel("East from perceived obstacle (m)")
ax.set_ylabel("North from perceived obstacle (m)")
ax.set_title("Mission route and static-obstacle evasion (logged run 20260731_061815)")
ax.grid(alpha=0.3, ls=":")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.95)
ax.set_aspect("equal", adjustable="box")
fig.tight_layout()
fig.savefig(os.path.join(IMG, "fig_static_mission_route.png"))
plt.close(fig)
print("OK fig_static_mission_route.png  evasion pts=%d" % len(ev))

# =================================================================================
# B) fig_static_clearance_timeseries.png (logged audited run)
# =================================================================================
obs_rows = [r for r in rows if r["obs_count"] != "0" and r["nearest_obs_dist_m"]]
t_first = float(obs_rows[0]["ts"])
tt = np.array([float(r["ts"]) - t_first for r in obs_rows])
dd = np.array([float(r["nearest_obs_dist_m"]) for r in obs_rows])
ev_rows = [r for r in rows if r["evasion_active"] == "1"]
t_ev0 = float(ev_rows[0]["ts"]) - t_first
t_ev1 = float(ev_rows[-1]["ts"]) - t_first
dmin = dd.min()
tmin = tt[int(dd.argmin())]
t_trig = trig["ts"] - t_first
d_trig = trig["nearest_distance_m"]

fig, ax = plt.subplots(figsize=(9.2, 4.4), dpi=200)
ax.axvspan(t_ev0, t_ev1, color="#f3e2c7", alpha=0.8, label="Active evasion window (logged)")
ax.plot(tt, dd, "-", color=C_FLY, lw=2.0, label="Logged distance to nearest perceived obstacle")
ax.axhline(12, color=C_OBS, ls="--", lw=1.4, label="Hard safety radius (12 m)")
ax.axhline(61, color="#3a7ca5", ls=":", lw=1.4, label="Reaction horizon at cruise (61 m)")
ax.plot(tmin, dmin, "o", color=C_OBS, ms=6)
ax.annotate("min %.1f m" % dmin, (tmin, dmin), textcoords="offset points",
            xytext=(10, -14), fontsize=9, color=C_OBS)
ax.plot(t_trig, d_trig, "s", color="#3a7ca5", ms=6)
ax.annotate("first replan trigger (%.1f m)" % d_trig, (t_trig, d_trig),
            textcoords="offset points", xytext=(10, 6), fontsize=9, color="#3a7ca5")
ax.set_xlabel("Time from first obstacle publication (s)")
ax.set_ylabel("Horizontal distance (m)")
ax.set_title("Clearance to the nearest perceived obstacle (logged run 20260731_061815)")
ax.grid(alpha=0.3, ls=":")
ax.legend(loc="upper right", fontsize=8.5, framealpha=0.95)
ax.set_ylim(0, max(dd) * 1.15)
fig.tight_layout()
fig.savefig(os.path.join(IMG, "fig_static_clearance_timeseries.png"))
plt.close(fig)
print("OK fig_static_clearance_timeseries.png  min=%.1f m at t=%.1f s  evasion=[%.1f,%.1f] s"
      % (dmin, tmin, t_ev0, t_ev1))

# =================================================================================
# C) transcurso_mision_nuevo_obs.png (offline debug view at reattachment, viz style)
# =================================================================================
T_CAP = 57.5  # s from log start: just after evasion_completed (56.0), obstacle still tracked
cap_row = min(rows, key=lambda r: abs(float(r["ts"]) - (t0 + T_CAP)))
t_cap = float(cap_row["ts"])
# obstacle position at capture: last logged perceived fix before capture
obs_before = None
for line in open(os.path.join(RUN, "brain", "events.jsonl"), encoding="utf-8", errors="replace"):
    try:
        j = json.loads(line)
    except Exception:
        continue
    if j.get("ts", 0) > t_cap:
        break
    if j.get("kind") in ("decision_snapshot", "obstacle_ingest"):
        for s in (j.get("obs_sample") or j.get("sample") or []):
            obs_before = (s["lat"], s["lon"])
# drone heading from trajectory deltas around capture
i_cap = rows.index(cap_row)
r_a = rows[max(0, i_cap - 4)]
r_b = rows[min(len(rows) - 1, i_cap + 4)]
dx_h, dy_h = latlon_to_m(float(r_b["lat"]), float(r_b["lon"]),
                         float(r_a["lat"]), float(r_a["lon"]))
hdg = (90 - math.degrees(math.atan2(dy_h, dx_h))) % 360

hlat, hlon = HOME
hist = [(float(r["lat"]), float(r["lon"])) for r in rows
        if float(r["ts"]) <= t_cap and r["mode"] == "GUIDED" and float(r["rel_alt"]) > 5]
ev_done = [(float(r["lat"]), float(r["lon"])) for r in rows
           if float(r["ts"]) <= t_cap and r["evasion_active"] == "1"]
hx = [latlon_to_m(la, lo, hlat, hlon)[0] for la, lo in hist]
hy = [latlon_to_m(la, lo, hlat, hlon)[1] for la, lo in hist]
ex = [latlon_to_m(la, lo, hlat, hlon)[0] for la, lo in ev_done]
ey = [latlon_to_m(la, lo, hlat, hlon)[1] for la, lo in ev_done]
dx, dy = latlon_to_m(float(cap_row["lat"]), float(cap_row["lon"]), hlat, hlon)
ox, oy = latlon_to_m(obs_before[0], obs_before[1], hlat, hlon)
mx = [0.0] + [latlon_to_m(la, lo, hlat, hlon)[0] for la, lo in INSPECTION_WPS]
my = [0.0] + [latlon_to_m(la, lo, hlat, hlon)[1] for la, lo in INSPECTION_WPS]

plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(8, 8))
ax.text(0, 0, "HOME", fontsize=10, fontweight="bold", color="#4C72B0")
for i, (la, lo) in enumerate(INSPECTION_WPS, start=1):
    wx, wy = latlon_to_m(la, lo, hlat, hlon)
    ax.text(wx + 5, wy + 5, "WP%d" % i, fontsize=10, color="#4C72B0")
ax.plot(mx, my, "--", color="#4C72B0", linewidth=1.5, zorder=1)
ax.add_patch(Circle((ox, oy), 12, color="#C44E52", alpha=0.3))
ax.plot(ox, oy, "x", color="#C44E52")
if ex:
    ax.plot(ex, ey, "-", color="#E67E22", linewidth=2.5, zorder=5)
ax.plot(hx, hy, "-", color="#555555", linewidth=1.5, alpha=0.7, zorder=3)
ang = math.radians(90 - hdg)
MS = 8.0
p1 = (dx + MS * math.cos(ang), dy + MS * math.sin(ang))
p2 = (dx + MS * 0.7 * math.cos(ang + 2.5), dy + MS * 0.7 * math.sin(ang + 2.5))
p3 = (dx + MS * 0.7 * math.cos(ang - 2.5), dy + MS * 0.7 * math.sin(ang - 2.5))
ax.fill([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]], color="black", zorder=10)

status = "OBSTACLE DETECTED"
info = ("STATUS: %s\nGPS: %.5f, %.5f\nALT: %.1fm MSL | HDG: %d deg\nOBS: 1"
        % (status, float(cap_row["lat"]), float(cap_row["lon"]),
           float(cap_row["alt_msl"]), int(round(hdg))))
ax.text(0.5, 0.03, info, transform=ax.transAxes, fontsize=9, ha="center", va="bottom",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="#333333"),
        fontfamily="monospace")
legend_elements = [
    Line2D([0], [0], color="#4C72B0", lw=1.5, ls="--", label="Global Mission"),
    Line2D([0], [0], color="#555555", lw=1.5, label="Flown Path"),
    Line2D([0], [0], color="#E67E22", lw=2.5, label="Evasion Path (executed)"),
    Line2D([0], [0], marker="^", color="w", markerfacecolor="black", markersize=8, label="Drone"),
    Line2D([0], [0], marker="x", color="#C44E52", label="Obstacle (tracked)", linestyle="None"),
]
ax.legend(handles=legend_elements, loc="upper right", fontsize=9, framealpha=0.9)
cx = (min(mx) + max(mx)) * 0.5
cy = (min(my) + max(my)) * 0.5
half = max(max(mx) - min(mx), max(my) - min(my)) * 0.5 + 30
ax.set_xlim(cx - half, cx + half)
ax.set_ylim(cy - half, cy + half)
try:
    ax.set_box_aspect(1)
except Exception:
    pass
ax.grid(True, linestyle=":", alpha=0.6)
ax.set_xlabel("East (m)", fontsize=11, fontweight="bold")
ax.set_ylabel("North (m)", fontsize=11, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(IMG, "transcurso_mision_nuevo_obs.png"), dpi=150)
plt.close(fig)
print("OK transcurso_mision_nuevo_obs.png  capture at t=%.1f s, wp_idx=%s, hdg=%d"
      % (t_cap - t0, cap_row["wp_idx"], int(round(hdg))))

