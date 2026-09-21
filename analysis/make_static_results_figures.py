# make_static_results_figures.py
# Figuras de resultados del paper estatico (MDPI), escenario cow_evasion_v2:
#   A) fig_static_mission_route.png   - ruta nominal vs volada + evasion + inset zoom
#   B) fig_static_evasion_sequence.png - multipanel 1A-1F con crops centrados en las vacas
#   C) fig_static_perception_closeups.png - 3 zooms de las detecciones YOLOE
#   D) fig_static_clearance_timeseries.png - distancia al obstaculo mas cercano vs tiempo
# Geometria identica a overlay_yoloe_cow_evasion_v2.py / build_cow_evasion_v2.py.
# NOTA (round-3 revision): las secciones A (mission route) y D (clearance) de este
# script derivan del re-render SCRIPTADO y ya NO se usan en el paper; las figuras 4-6
# se generan desde los logs reales con make_logged_campaign_figures.py. Este script
# solo se mantiene para el multipanel de percepcion (B, Figure 1) y los closeups (C).
import math
import os
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = os.environ.get(
    "PORCE_LEGACY_RENDER_ROOT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_data", "legacy_renders"),
)
ANN = os.path.join(ROOT, "cow_evasion_v2_annotated")
IMG = os.environ.get("PORCE_STATIC_FIG_OUT", os.path.join(ROOT, "static_results_figures"))
os.makedirs(IMG, exist_ok=True)

# --- geometria (cm) -------------------------------------------------------------
P1 = (-4920.8, -11834.2); P2 = (32820.4, 45204.0)
COWS = [(13941.7, 17366.4, -1166.4), (14844.0, 17342.7, -1154.6)]
CX = (COWS[0][0] + COWS[1][0]) / 2; CY = (COWS[0][1] + COWS[1][1]) / 2
CAM_Z_OFFSET = 5000.0
FPS = 20.0
SPEED_MPS = 10.0
HOLD_FRAMES = 400
N_FLIGHT = 513

dx, dy = P2[0] - P1[0], P2[1] - P1[1]
rl = math.hypot(dx, dy); ux, uy = dx / rl, dy / rl
t_cow = (CX - P1[0]) * ux + (CY - P1[1]) * uy
R, ZONE, LEAD, TAIL = 5000.0, 12000.0, 6000.0, 3500.0
px, py = -uy, ux
B = t_cow - ZONE / 2; D = t_cow + ZONE / 2
BX, BY = P1[0] + ux * B, P1[1] + uy * B
DX, DY = P1[0] + ux * D, P1[1] + uy * D
SX, SY = P1[0] + ux * (B - LEAD), P1[1] + uy * (B - LEAD)

def pp(q):
    if q <= LEAD:
        return SX + ux * q, SY + uy * q
    elif q <= LEAD + ZONE:
        z = q - LEAD
        rx, ry = BX + ux * z, BY + uy * z
        lat = R * math.sin(math.pi * z / ZONE)
        return rx + px * lat, ry + py * lat
    else:
        q3 = q - LEAD - ZONE
        return DX + ux * q3, DY + uy * q3

Q_MAX = LEAD + ZONE + TAIL
arc = [(0.0, 0.0)]
qx, qy = pp(0.0); acc = 0.0; q = 5.0
while q <= Q_MAX:
    nx, ny = pp(min(q, Q_MAX))
    acc += math.hypot(nx - qx, ny - qy)
    arc.append((min(q, Q_MAX), acc)); qx, qy = nx, ny; q += 5.0
TOTAL_LEN = acc

def q_at(s):
    if s <= 0: return 0.0
    if s >= TOTAL_LEN: return Q_MAX
    lo, hi = 0, len(arc) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if arc[mid][1] < s: lo = mid
        else: hi = mid
    q0, s0 = arc[lo]; q1, s1 = arc[hi]
    f = (s - s0) / (s1 - s0) if s1 > s0 else 0.0
    return q0 + (q1 - q0) * f

def cam_xy(t_s):
    s = min(t_s * SPEED_MPS * 100.0, TOTAL_LEN)
    return pp(q_at(s))

def to_m(x, y):  # cm -> m centrado en el cruce de las vacas
    return (x - CX) / 100.0, (y - CY) / 100.0

# estilo comun (parecido a las figuras de datos del paper dinamico)
FG = "#1a2233"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "text.color": FG, "axes.edgecolor": "#5b6575",
    "axes.labelcolor": FG, "xtick.color": FG, "ytick.color": FG,
    "axes.titlesize": 13, "axes.titleweight": "bold", "font.size": 10,
})
C_NOM = "#3a7ca5"   # nominal
C_FLY = "#c96a2b"   # volada/evasion
C_OBS = "#a03030"

# =================================================================================
# A) fig_static_mission_route.png
# =================================================================================
ts = np.linspace(0, (N_FLIGHT - 1) / FPS, 400)
path = np.array([cam_xy(t) for t in ts])
nom = np.array([to_m(SX + ux * s, SY + uy * s) for s in np.linspace(0, Q_MAX, 200)])
fly = np.array([to_m(x, y) for x, y in path])
ev = np.array([to_m(*cam_xy(t)) for t in ts if (LEAD < q_at(min(t * SPEED_MPS * 100, TOTAL_LEN)) <= LEAD + ZONE)])

fig, ax = plt.subplots(figsize=(9.2, 6.4), dpi=200)
ax.plot(nom[:, 0], nom[:, 1], "--", color=C_NOM, lw=1.6, label="Nominal corridor (waypoints)")
ax.plot(fly[:, 0], fly[:, 1], "-", color="#666666", lw=1.4, label="Flown path")
if len(ev):
    ax.plot(ev[:, 0], ev[:, 1], "-", color=C_FLY, lw=3.2, label="Active evasion segment")
for i, (cx_, cy_, cz_) in enumerate(COWS):
    ax.add_patch(Circle((0, 0) if i == -1 else ((cx_ - CX) / 100.0, (cy_ - CY) / 100.0),
                        12, fill=True, alpha=0.18, color=C_OBS, zorder=3))
    ax.add_patch(Circle(((cx_ - CX) / 100.0, (cy_ - CY) / 100.0), 12, fill=False,
                        ls=":", lw=1.2, color=C_OBS, zorder=4))
    ax.plot((cx_ - CX) / 100.0, (cy_ - CY) / 100.0, "x", color=C_OBS, ms=9, mew=2.4, zorder=5)
ax.plot([], [], "x", color=C_OBS, ms=9, mew=2.4, label="Cattle (12 m protected radius)")
x0, y0 = fly[0]; x1, y1 = fly[-1]
ax.plot(x0, y0, "s", color="#222222", ms=7); ax.annotate("start", (x0, y0), textcoords="offset points", xytext=(8, -2), fontsize=9)
ax.plot(x1, y1, ">", color="#222222", ms=7); ax.annotate("end", (x1, y1), textcoords="offset points", xytext=(8, -2), fontsize=9)

# inset zoom sobre la evasion
axins = ax.inset_axes([0.58, 0.08, 0.38, 0.42])
axins.plot(nom[:, 0], nom[:, 1], "--", color=C_NOM, lw=1.4)
axins.plot(fly[:, 0], fly[:, 1], "-", color="#666666", lw=1.2)
if len(ev):
    axins.plot(ev[:, 0], ev[:, 1], "-", color=C_FLY, lw=3.0)
for (cx_, cy_, cz_) in COWS:
    axins.add_patch(Circle(((cx_ - CX) / 100.0, (cy_ - CY) / 100.0), 12, fill=True, alpha=0.18, color=C_OBS))
    axins.add_patch(Circle(((cx_ - CX) / 100.0, (cy_ - CY) / 100.0), 12, fill=False, ls=":", lw=1.1, color=C_OBS))
    axins.plot((cx_ - CX) / 100.0, (cy_ - CY) / 100.0, "x", color=C_OBS, ms=8, mew=2.2)
axins.set_xlim(-90, 90); axins.set_ylim(-70, 70)
axins.set_title("evasion window", fontsize=9)
axins.grid(alpha=0.3, ls=":")
ax.indicate_inset_zoom(axins, edgecolor="#888888")

ax.set_xlabel("East from cattle centroid (m)")
ax.set_ylabel("North from cattle centroid (m)")
ax.set_title("Mission route and static-obstacle evasion (digital-twin scenario)")
ax.grid(alpha=0.3, ls=":")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.95)
ax.set_aspect("equal", adjustable="datalim")
fig.tight_layout()
fig.savefig(os.path.join(IMG, "fig_static_mission_route.png"))
plt.close(fig)
print("OK fig_static_mission_route.png")

# =================================================================================
# D) fig_static_clearance_timeseries.png
# =================================================================================
tt = np.linspace(0, (N_FLIGHT - 1) / FPS, 500)
d1, d2, state = [], [], []
for t in tt:
    x, y = cam_xy(t)
    d1.append(math.dist((x, y, CAM_Z_OFFSET + COWS[0][2]), COWS[0]) / 100.0)
    d2.append(math.dist((x, y, CAM_Z_OFFSET + COWS[0][2]), COWS[1]) / 100.0)
    q = q_at(min(t * SPEED_MPS * 100.0, TOTAL_LEN))
    state.append(LEAD < q <= LEAD + ZONE)
dmin = np.minimum(d1, d2)
t_ev = [t for t, s in zip(tt, state) if s]
t0e, t1e = (min(t_ev), max(t_ev)) if t_ev else (None, None)

fig, ax = plt.subplots(figsize=(9.2, 4.4), dpi=200)
if t0e is not None:
    ax.axvspan(t0e, t1e, color="#f3e2c7", alpha=0.8, label="Active evasion window")
ax.plot(tt, d1, "-", color=C_FLY, lw=2.0, label="Distance to cow #1")
ax.plot(tt, d2, "-", color="#7a4a8a", lw=2.0, label="Distance to cow #2")
ax.axhline(12, color=C_OBS, ls="--", lw=1.4, label="Hard safety radius (12 m)")
imin = int(np.argmin(dmin))
ax.plot(tt[imin], dmin[imin], "o", color=C_OBS, ms=6)
ax.annotate("min %.1f m" % dmin[imin], (tt[imin], dmin[imin]),
            textcoords="offset points", xytext=(10, 6), fontsize=9, color=C_OBS)
ax.set_xlabel("Time from corridor entry (s)")
ax.set_ylabel("3D distance (m)")
ax.set_title("Clearance to the nearest static obstacle during the mission")
ax.grid(alpha=0.3, ls=":")
ax.legend(loc="upper right", fontsize=8.5, framealpha=0.95)
ax.set_ylim(0, max(d1 + d2) * 1.05)
fig.tight_layout()
fig.savefig(os.path.join(IMG, "fig_static_clearance_timeseries.png"))
plt.close(fig)
print("OK fig_static_clearance_timeseries.png  min=%.1f m  evasion=[%.1f,%.1f] s" % (dmin[imin], t0e, t1e))

# =================================================================================
# util: localizar cajas verdes del overlay en un frame anotado
# =================================================================================
def green_bbox(img):
    b, g, r = cv2.split(img.astype(np.int16))
    mask = ((g > 140) & (g > r + 40) & (g > b + 40)).astype(np.uint8) * 255
    # ignorar las barras de texto superior/inferior
    mask[:36, :] = 0; mask[-36:, :] = 0
    ys, xs = np.nonzero(mask)
    if len(xs) < 10:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max()

def crop_around(img, bbox, target_ar=4 / 3, margin=1.9):
    h, w = img.shape[:2]
    if bbox is None:
        return img
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    bw, bh = (x2 - x1) * margin, (y2 - y1) * margin
    W = max(bw, bh * target_ar, 320)
    H = W / target_ar
    X1 = int(np.clip(cx - W / 2, 0, w - W)); Y1 = int(np.clip(cy - H / 2, 0, h - H))
    return img[Y1:Y1 + int(H), X1:X1 + int(W)]

# =================================================================================
# B) fig_static_evasion_sequence.png (multipanel con crops)
# =================================================================================
PANELS = [
    ("ann_0000.png", "(a)", "Nominal waypoint following", False),
    ("ann_0060.png", "(b)", "Detected, outside reaction distance", True),
    ("ann_0150.png", "(c)", "Obstacle enters reaction range", False),
    ("ann_0256.png", "(d)", "Active evasion maneuver", True),
    ("ann_0350.png", "(e)", "Bypass with tracked obstacles", True),
    ("ann_0450.png", "(f)", "Route rejoined, nominal resumed", False),
]
CELL_W, CELL_H, LABEL_BAR, PAD = 640, 480, 34, 6
FONT = cv2.FONT_HERSHEY_SIMPLEX
cells = []
for fname, tag, desc, do_crop in PANELS:
    img = cv2.imread(os.path.join(ANN, fname))
    if img is None:
        raise SystemExit("falta " + fname)
    if do_crop:
        img = crop_around(img, green_bbox(img), margin=2.6)
    img = cv2.resize(img, (CELL_W, CELL_H), interpolation=cv2.INTER_AREA)
    canvas = np.full((CELL_H + LABEL_BAR, CELL_W, 3), (255, 255, 255), np.uint8)
    canvas[LABEL_BAR:, :] = img
    cv2.putText(canvas, "%s  %s" % (tag, desc), (10, 24), FONT, 0.62, (20, 20, 20), 2, cv2.LINE_AA)
    cells.append(canvas)
rows = []
for r in range(3):
    rows.append(np.hstack([cells[r * 2], np.full((CELL_H + LABEL_BAR, PAD, 3), 255, np.uint8), cells[r * 2 + 1]]))
grid = rows[0]
for r in range(1, 3):
    grid = np.vstack([grid, np.full((PAD, grid.shape[1], 3), 255, np.uint8), rows[r]])
cv2.imwrite(os.path.join(IMG, "fig_static_evasion_sequence.png"), grid, [cv2.IMWRITE_PNG_COMPRESSION, 3])
print("OK fig_static_evasion_sequence.png")

# =================================================================================
# C) fig_static_perception_closeups.png (3 zooms horizontales)
# =================================================================================
CLOSE = [("ann_0060.png", "2A  first detection (~101 m)"),
         ("ann_0150.png", "2B  reaction horizon entry (~70 m)"),
         ("ann_0256.png", "2C  closest approach (~67 m)")]
CW, CH, LB = 560, 420, 32
tiles = []
for fname, label in CLOSE:
    img = cv2.imread(os.path.join(ANN, fname))
    c = crop_around(img, green_bbox(img), margin=1.7)
    c = cv2.resize(c, (CW, CH), interpolation=cv2.INTER_AREA)
    canvas = np.full((CH + LB, CW, 3), 255, np.uint8)
    canvas[LB:, :] = c
    cv2.putText(canvas, label, (10, 22), FONT, 0.58, (20, 20, 20), 2, cv2.LINE_AA)
    tiles.append(canvas)
strip = tiles[0]
for t in tiles[1:]:
    strip = np.hstack([strip, np.full((CH + LB, PAD, 3), 255, np.uint8), t])
cv2.imwrite(os.path.join(IMG, "fig_static_perception_closeups.png"), strip, [cv2.IMWRITE_PNG_COMPRESSION, 3])
print("OK fig_static_perception_closeups.png")
