"""Regenerate the physical-flight figures from the V1--V3 dossiers."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.patches import Rectangle
import numpy as np
from pymavlink import DFReader


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "VUELOS_REALES_3"
OUT = Path(__file__).resolve().parent / "regen_output"
OUT.mkdir(parents=True, exist_ok=True)

RUNS = [
    ("V1", "V1_20260919_092511", "2 towers, 8 persons"),
    ("V2", "V2_20260919_120908", "3 towers, 2 persons"),
    ("V3", "V3_20260919_162344", "3 towers, 2 persons (V2 replica)"),
]
RADIUS_M = 12.0
CELL_M = 4.0
COLORS = {"V1": "#2369a1", "V2": "#d16b25", "V3": "#32805a"}
CLASS_COLORS = {"tower": "#a44a32", "person": "#7955a5"}
EARTH_M = 6_371_000.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def read_native_track(path: Path, origin_lat: float, origin_lon: float) -> list[dict[str, float]]:
    """Read armed-interval valid GPS points into the campaign E/N frame."""
    reader = DFReader.DFReader_binary(str(path), None)
    gps_samples = []
    arms = []
    while (message := reader.recv_match()) is not None:
        kind = message.get_type()
        if kind == "ARM":
            arms.append((int(message.TimeUS), int(message.ArmState)))
            continue
        if kind != "GPS" or getattr(message, "I", 0) != 0 or getattr(message, "Status", 0) < 3:
            continue
        lat, lon = float(message.Lat), float(message.Lng)
        east = math.radians(lon - origin_lon) * EARTH_M * math.cos(math.radians(origin_lat))
        north = math.radians(lat - origin_lat) * EARTH_M
        gps_samples.append({"time_us": int(message.TimeUS), "E_m": east, "N_m": north})
    arm_on = next((t for t, state in arms if state == 1), None)
    arm_off = next((t for t, state in arms if state == 0 and arm_on is not None and t > arm_on), None)
    if arm_on is None or arm_off is None:
        raise ValueError(f"{path}: missing an ARM/DISARM interval")
    samples = [r for r in gps_samples if arm_on <= r["time_us"] <= arm_off]
    samples.sort(key=lambda row: row["time_us"])
    # Keep the complete native GPS stream; no resampling or smoothing, so the
    # minimum-distance audit uses every valid receiver sample.
    return samples


def read_derived_track(path: Path) -> list[dict[str, float]]:
    """Read the exporter's derived 1 Hz track (campaign E/N frame).

    The derived trajectory is the dossier's exported product and reproduces the
    committed figure basis; the raw flight.BIN additionally interleaves
    obstacle-estimate samples during the return leg, which are not aircraft
    positions and must not be drawn as flown track.
    """
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({
                "time_us": int(float(row["time_us"])),
                "E_m": float(row["E_m"]),
                "N_m": float(row["N_m"]),
            })
    rows.sort(key=lambda r: r["time_us"])
    return rows


def detour_windows(track, enter_m=4.0, exit_m=2.5, min_s=1.5):
    """Contiguous detour excursions of the track, found geometrically.

    A detour window opens when the cross-track offset |E_m| exceeds enter_m
    (one 4 m grid cell) and closes when it returns below exit_m; windows shorter
    than min_s are discarded. Only the outbound leg is scanned: everything from
    the first sample that enters the return lane (E_m < -60 m, the planned
    return-lane offset) onwards is excluded, so the turn at the north edge and
    the return lane itself are never flagged as detours.
    """
    outbound_end = len(track)
    for i, row in enumerate(track):
        if row["E_m"] < -60.0:
            outbound_end = i
            break
    # The turn into the return lane happens at the north edge, within a few
    # tens of metres of the outbound leg end; samples in that corner band are
    # excluded so the turn itself is never flagged as a detour.
    north_band_m = 60.0
    n_limit = track[outbound_end - 1]["N_m"] - north_band_m if outbound_end else 0.0
    windows = []
    on = False
    start_i = end_i = None
    for i in range(outbound_end):
        row = track[i]
        e, n = row["E_m"], row["N_m"]
        in_region = -60.0 < e < 100.0 and 20.0 < n < n_limit
        dev = abs(e) if in_region else 0.0
        if in_region and dev > enter_m and not on:
            on, start_i = True, i
        elif on and (not in_region or dev < exit_m):
            on = False
            end_i = i
            duration = (track[end_i]["time_us"] - track[start_i]["time_us"]) / 1e6
            if duration >= min_s:
                windows.append((start_i, end_i))
    if on:
        end_i = outbound_end - 1
        duration = (track[end_i]["time_us"] - track[start_i]["time_us"]) / 1e6
        if duration >= min_s:
            windows.append((start_i, end_i))
    # Merge windows separated by short nominal gaps (bypass wiggle inside one
    # detour): the gap between successive detours of one encounter sequence is
    # far longer than any within-bypass wobble, so a 3 s merge window keeps
    # each executed bypass as a single excursion.
    merged = []
    for w0, w1 in windows:
        if merged and (track[w0]["time_us"] - track[merged[-1][1]]["time_us"]) / 1e6 < 3.0:
            merged[-1] = (merged[-1][0], w1)
        else:
            merged.append((w0, w1))
    return merged


def load_runs():
    out = []
    for label, folder, description in RUNS:
        base = DATA / folder
        meta = json.loads((base / "derived" / "metrics.json").read_text(encoding="utf-8"))
        if float(meta["grid_resolution_m"]) != CELL_M or float(meta["safety_radius_m"]) != RADIUS_M:
            raise ValueError(f"{label} config differs from the figure contract")
        frame = json.loads((base / "config" / "campaign_frame.json").read_text(encoding="utf-8"))
        if float(frame.get("outbound_bearing_deg", -1)) != 0.0:
            raise ValueError(f"{label} campaign frame is not aligned to northing")
        track = read_derived_track(base / "derived" / "trajectory.csv")
        obstacles = read_csv(base / "ground_truth" / "obstacles.csv")
        encounters = read_csv(base / "derived" / "encounters.csv")
        out.append((
            label,
            description,
            read_native_track(base / "native" / "flight.BIN",
                              float(frame["origin"]["lat"]), float(frame["origin"]["lon"])),
            track,
            obstacles,
            encounters,
            frame,
        ))
    return out


def make_tracks(runs) -> Path:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 16,
        "axes.titlesize": 17, "axes.titleweight": "bold",
        "axes.labelsize": 16,
    })
    fig = plt.figure(figsize=(14.0, 9.0))
    layout = fig.add_gridspec(2, 6, height_ratios=(1.0, 0.92), hspace=0.48, wspace=0.42)
    overview_axes = [
        fig.add_subplot(layout[0, 0:2]),
        fig.add_subplot(layout[0, 2:4]),
        fig.add_subplot(layout[0, 4:6]),
    ]
    for ax, (label, description, _, trajectory, obstacles, encounters, _) in zip(overview_axes, runs):
        # Route coordinate is northing in the campaign frame; S_m in the
        # trajectory CSV is cumulative flown distance and must not be overlaid
        # on the obstacle layout's fixed route-coordinate S_m.
        s = np.asarray([float(r["N_m"]) for r in trajectory])
        x = np.asarray([float(r["E_m"]) for r in trajectory])
        windows = detour_windows(trajectory)
        print(f"{label}: detour excursions found={len(windows)}; "
              f"logged encounters={len(encounters)}")
        ax.plot(s, x, color=COLORS[label], lw=1.45, label=f"{label} flown track")
        for w0, w1 in windows:
            ax.plot(s[w0:w1 + 1], x[w0:w1 + 1], color="#d97706", lw=2.6, zorder=3)
            ax.plot([s[w1]], [x[w1]], marker="D", ms=7, color="#15803d",
                    mec="white", mew=0.6, zorder=5, linestyle="None")
        ax.scatter([s[0]], [x[0]], marker="o", s=26, color=COLORS[label], zorder=4, label="start")
        ax.scatter([s[-1]], [x[-1]], marker="x", s=36, color="#222222", zorder=4, label="end")
        for obj in obstacles:
            os_, ox = float(obj["S_m"]), float(obj["X_m"])
            color = CLASS_COLORS[obj["class"]]
            ax.scatter([os_], [ox], marker="s" if obj["class"] == "tower" else "o",
                       s=38, color=color, edgecolor="white", linewidth=0.6, zorder=5)
        ax.axhline(0, color="#a5a5a5", lw=0.7, ls="--", zorder=0)
        ax.axhline(-80, color="#777777", lw=0.8, ls=(0, (4, 3)), zorder=0)
        ax.set_xlim(-35, max(s) + 35)
        ax.set_ylim(-108, 88)
        short_desc = {"V1": "2 towers, 8 persons", "V2": "3 towers, 2 persons",
                      "V3": "3 towers, 2 persons; V2 replica"}[label]
        ax.set_title(f"{label} — {short_desc}")
        ax.set_xlabel("Route coordinate S (m)")
        if label == "V1":
            ax.set_ylabel("Cross-track offset X (m)")
        ax.grid(alpha=0.22, ls=":")

    # Zoom the five surveyed people that form the V1 cluster at S=680--730 m.
    people_ax = fig.add_subplot(layout[1, 0:3])
    v1 = runs[0]
    cluster = [o for o in v1[4] if o["class"] == "person" and 665 <= float(o["S_m"]) <= 745]
    turn_idx = max(range(len(v1[3])), key=lambda i: float(v1[3][i]["N_m"]))
    outbound_track = v1[3][:turn_idx + 1]
    local_track = [r for r in outbound_track if 660 <= float(r["N_m"]) <= 750]
    people_ax.plot([float(r["N_m"]) for r in local_track],
                   [float(r["E_m"]) for r in local_track],
                   color=COLORS["V1"], lw=1.2, label="V1 flown track")
    offsets = {"P-1": (-2, -17), "P-2": (-8, 14), "P-3": (8, -16),
               "P-4": (-7, 15), "P-5": (7, 14)}
    for obj in cluster:
        sx, xx = float(obj["S_m"]), float(obj["X_m"])
        people_ax.scatter([sx], [xx], marker="o", s=38, color=CLASS_COLORS["person"],
                          edgecolor="white", linewidth=0.6, zorder=4)
        dx, dy = offsets[obj["object_id"]]
        people_ax.annotate(obj["object_id"], (sx, xx), xytext=(dx, dy),
                           textcoords="offset points", fontsize=10, ha="center",
                           bbox={"boxstyle": "round,pad=0.16", "fc": "white", "ec": "none", "alpha": 0.9},
                           arrowprops={"arrowstyle": "-", "color": "#555555", "lw": 0.6})
    people_ax.set_xlim(660, 750)
    people_ax.set_ylim(-5, 88)
    people_ax.set_xlabel("Route coordinate S (m)")
    people_ax.set_ylabel("Cross-track offset X (m)")
    people_ax.set_title("V1 second cluster: 5 of 8 surveyed people")
    people_ax.grid(alpha=0.25, ls=":")

    # Schematic of the implemented cell-vs-disk intersection mask. The grid is
    # re-anchored at the UAS start point for every planning call, but the phase
    # is absent from these flight logs. Show a clearly offset illustrative
    # phase rather than centring a cell on the obstacle and implying symmetry.
    raster_ax = fig.add_subplot(layout[1, 3:6])
    grid_e_origin, grid_n_origin = -1.25, 0.80
    e_extents = np.arange(-5, 6) * CELL_M + grid_e_origin
    n_extents = np.arange(-5, 6) * CELL_M + grid_n_origin
    furthest = 0.0
    for ix in range(len(e_extents) - 1):
        x0, x1 = e_extents[ix], e_extents[ix + 1]
        gx = x0 if x0 > 0 else (-x1 if x1 < 0 else 0.0)
        for iy in range(len(n_extents) - 1):
            y0, y1 = n_extents[iy], n_extents[iy + 1]
            gy = y0 if y0 > 0 else (-y1 if y1 < 0 else 0.0)
            if np.hypot(gx, gy) <= RADIUS_M:
                raster_ax.add_patch(Rectangle((x0, y0), CELL_M, CELL_M,
                                              facecolor="#e98f82", edgecolor="#bd5b4e",
                                              linewidth=0.7, alpha=0.38, zorder=1))
                furthest = max(furthest, *(np.hypot(x, y) for x in (x0, x1) for y in (y0, y1)))
    raster_ax.add_patch(Circle((0, 0), RADIUS_M, fill=False, edgecolor="#a83232",
                               lw=1.7, ls="--", label="Configured 12 m disk", zorder=3))
    raster_ax.scatter([0], [0], marker="x", s=60, linewidth=2, color="#222222",
                      label="Obstacle centre", zorder=4)
    raster_ax.set_xlim(-18, 18)
    raster_ax.set_ylim(-18, 18)
    raster_ax.set_aspect("equal", adjustable="box")
    raster_ax.set_xticks(np.arange(-16, 17, 8))
    raster_ax.set_yticks(np.arange(-16, 17, 8))
    raster_ax.grid(color="#778899", alpha=0.55, lw=0.6, zorder=0)
    raster_ax.set_xlabel("East offset from obstacle (m)")
    raster_ax.set_ylabel("North offset from obstacle (m)")
    raster_ax.set_title(
        f"Configured 12 m disk + 4 m cells\nOffset phase is illustrative; raster corner {furthest:.1f} m",
        fontsize=14.5,
    )
    handles = [
        plt.Line2D([], [], color=COLORS["V1"], lw=1.8, label="V1–V3 flown tracks"),
        plt.Line2D([], [], color="#d97706", lw=2.6, label="Detour excursion"),
        plt.Line2D([], [], marker="D", color="w", markerfacecolor="#15803d",
                   label="Route reattachment", markersize=7),
        plt.Line2D([], [], marker="s", color="w", markerfacecolor=CLASS_COLORS["tower"],
                   label="Tower", markersize=7),
        plt.Line2D([], [], marker="o", color="w", markerfacecolor=CLASS_COLORS["person"],
                   label="Person", markersize=7),
        plt.Line2D([], [], marker="x", color="#222222", lw=0, label="Obstacle centre", markersize=7),
    ]
    handles.extend([
        plt.Line2D([], [], color="#777777", lw=0.8, ls=(0, (4, 3)), label="Planned return lane: X = -80 m"),
        plt.Rectangle((0, 0), 1, 1, facecolor="#e98f82", edgecolor="#bd5b4e", alpha=0.38,
                      label="Blocked raster cells"),
    ])
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 0.015), fontsize=11.5)
    fig.suptitle("V1–V3 native GPS tracks, RTK surveys, and the 4 m raster mask", y=0.99,
                 fontsize=17, weight="bold")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.20,
                        hspace=0.52, wspace=0.42)
    path = OUT / "real_flight_tracks_v1_v3.png"
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def make_clearance(runs) -> Path:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 15.5,
        "axes.titlesize": 17.5, "axes.titleweight": "bold",
        "axes.labelsize": 15.5,
    })
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.0), sharey=True)
    for ax, (label, description, track, _, obstacles, encounters, frame) in zip(axes, runs):
        color = COLORS[label]
        encounters_by_id = {row["object_id"]: row for row in encounters}
        lat0, lon0 = float(frame["origin"]["lat"]), float(frame["origin"]["lon"])
        track_en = np.asarray([
            [r["E_m"], r["N_m"]] for r in track
        ], dtype=float)
        names = [row["object_id"].replace("P-", "P") for row in obstacles]
        xs = np.arange(len(obstacles))
        ax.axhline(RADIUS_M, color="#a83232", ls="--", lw=1.5,
                   label="Configured centre radius: 12 m")
        for i, obstacle in enumerate(obstacles):
            east = math.radians(float(obstacle["lon_deg"]) - lon0) * EARTH_M * math.cos(math.radians(lat0))
            north = math.radians(float(obstacle["lat_deg"]) - lat0) * EARTH_M
            raw_min = float(np.min(np.hypot(track_en[:, 0] - east, track_en[:, 1] - north)))
            c = CLASS_COLORS[obstacle["class"]]
            ax.scatter(xs[i] - 0.12, raw_min, marker="o", s=35, color=c,
                       edgecolor="white", linewidth=0.5, zorder=4)
            encounter = encounters_by_id[obstacle["object_id"]]
            reported = float(encounter["min_ground_truth_clearance_m"])
            err = float(encounter["ground_truth_uncertainty_m"])
            ax.errorbar(xs[i] + 0.12, reported, yerr=err, fmt="s", ms=5,
                        color=c, ecolor=c, capsize=2, elinewidth=1, zorder=4)
        ax.set_xticks(xs, names, rotation=45, ha="right")
        ax.tick_params(axis="both", labelsize=13)
        ax.set_title(f"{label} · n={len(encounters)}")
        ax.set_xlabel("Encounter")
        ax.grid(axis="y", alpha=0.25, ls=":")
        ax.set_ylim(0, 60)
    axes[0].set_ylabel("Minimum distance to surveyed obstacle centre (m)")
    legend = [
        plt.Line2D([], [], marker="o", color="#444444", lw=0,
                   label="Native valid-GPS min distance to survey centre"),
        plt.Line2D([], [], marker="s", color="#444444", lw=0,
                   label="Dossier encounter clearance; whisker = reported uncertainty"),
        plt.Line2D([], [], color="#a83232", ls="--", lw=1.5, label="Configured centre radius: 12 m"),
        plt.Line2D([], [], marker="s", color=CLASS_COLORS["tower"], lw=0, label="Tower"),
        plt.Line2D([], [], marker="s", color=CLASS_COLORS["person"], lw=0, label="Person"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.005), fontsize=12)
    fig.suptitle("Audit: native GPS minima do not reconcile with dossier clearances", y=1.015,
                 fontsize=17, weight="bold")
    fig.tight_layout(rect=(0, 0.09, 1, 0.96))
    path = OUT / "native_vs_summary_clearance_audit_v1_v3.png"
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    runs = load_runs()
    for path in (make_tracks(runs), make_clearance(runs)):
        print(path)


if __name__ == "__main__":
    main()
