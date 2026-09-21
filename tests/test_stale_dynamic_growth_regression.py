import sys
import time
from pathlib import Path

import pytest

STAGING = Path(__file__).resolve().parents[1]
SRC = STAGING / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import flight_controller as brain  # noqa: E402


def test_stale_dynamic_track_growth_does_not_raise():
    """Regresion A03: un track dinamico stale no debe provocar NameError en
    _rebuild_active_obstacles_locked (la variable class_name usada por la burbuja
    de incertidumbre debe resolverse dentro del bucle)."""
    now = time.time()
    brain.state.clear()
    brain.state["obstacle_tracks"] = {
        7: {
            "id": 7,
            "entity_id": "vision:7",
            "source": "vision",
            "source_id": 7,
            "type": "biker",          # clase dinamica
            "confidence": 0.8,
            "distance": 30.0,
            "lat": 42.2, "lon": -1.23,
            "last_seen_ts": now - 2.0,    # stale (>1 s) pero vivo (<TTL dinamico 3 s)
            "source_timestamp_s": now - 2.0,
        }
    }
    active = brain._rebuild_active_obstacles_locked(now)
    assert isinstance(active, list) and len(active) == 1
    item = active[0]
    # el radio crecido debe existir (track dinamico stale)
    assert "stale_growth_radius_m" in item
    assert item["stale_growth_radius_m"] > 0.0
    assert item["stale"] is True
