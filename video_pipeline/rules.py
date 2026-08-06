"""
video_pipeline/rules.py
========================
Rule engine — pure logic, zero video/ML dependencies.

This file has no imports from ultralytics, opencv, or any ML library.
It only takes track history dicts (from tracker.py) and returns rule fires.
This is intentional: it makes the rules fast to unit test without any model
weights, GPU, or video files.

Rules implemented
------------------
1. Loitering
   A track's centre point has stayed inside a defined zone polygon for longer
   than `loitering_threshold_seconds`. Fires once per track, then respects
   the per-camera `event_cooldown_seconds` before firing again.

2. Perimeter breach
   A track's centre point crosses a defined line segment between consecutive
   history entries. Fires once per crossing event (not continuously).

Zone / line coordinate system
-------------------------------
All coordinates are NORMALISED (0.0–1.0 relative to frame dimensions).
This means the rule config works correctly regardless of video resolution.

RuleFire schema
----------------
Each rule fire is a dict:
  {
    "event_type"  : "loitering" | "perimeter_breach",
    "track_id"    : int,
    "class_name"  : str,
    "camera_id"   : str,
    "confidence"  : float,    # mean confidence of the track's history points
    "timestamp_s" : float,    # video time when the rule fired
    "metadata"    : {
        "dwell_seconds" : float,   # (loitering only) how long in zone
        "zone"          : [...],   # zone polygon
        -- or --
        "line"          : [...],   # perimeter line that was crossed
        "from_side"     : int,     # +1 or -1
    }
  }
"""

from __future__ import annotations

import math
import logging
from typing import Sequence

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geometry helpers (pure functions — easy to test)
# ---------------------------------------------------------------------------

def _point_in_polygon(px: float, py: float, polygon: list[list[float]]) -> bool:
    """
    Ray-casting algorithm for point-in-polygon test.
    `polygon` is a list of [x, y] vertices (normalised coords).
    Returns True if (px, py) is inside the polygon.
    """
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _sign_of_side(
    px: float, py: float, lx1: float, ly1: float, lx2: float, ly2: float
) -> int:
    """
    Returns +1 or -1 depending on which side of line (lx1,ly1)→(lx2,ly2)
    the point (px, py) is on. Returns 0 if exactly on the line.
    Based on the cross product of the line vector with the point vector.
    """
    cross = (lx2 - lx1) * (py - ly1) - (ly2 - ly1) * (px - lx1)
    if cross > 0:
        return 1
    if cross < 0:
        return -1
    return 0


def _mean_confidence(history: list[dict]) -> float:
    """Mean confidence score of a track's history entries."""
    if not history:
        return 0.0
    return sum(e["confidence"] for e in history) / len(history)


# ---------------------------------------------------------------------------
# Stateful rule engine
# ---------------------------------------------------------------------------

class RuleEngine:
    """
    Stateful rule evaluator for a single camera.

    Usage — call `evaluate()` once per frame with the current track histories.
    It returns a (possibly empty) list of RuleFire dicts.

    State maintained
    -----------------
    - `_track_zone_entry`: dict mapping track_id → timestamp_s when the track
      first entered the current zone. Reset when track leaves.
    - `_last_crossing_side`: dict mapping (track_id, line_idx) → last known side.
    - `_cooldown_state`: dict mapping (track_id, event_type) → timestamp_s of
      last fire, used to suppress repeated events.

    Parameters
    ----------
    camera_id : str
        Used for metadata in rule fires.
    rules_config : dict
        Per-camera rule config from config.CAMERA_RULES (or DEFAULT_RULES).
    """

    def __init__(self, camera_id: str, rules_config: dict) -> None:
        self.camera_id = camera_id
        self.cfg = rules_config

        self._track_zone_entry: dict[int, float] = {}
        self._last_crossing_side: dict[tuple[int, int], int] = {}
        self._cooldown_state: dict[tuple[int, str], float] = {}

    def _is_in_cooldown(
        self, track_id: int, event_type: str, current_ts: float
    ) -> bool:
        key = (track_id, event_type)
        last = self._cooldown_state.get(key)
        if last is None:
            return False
        return (current_ts - last) < self.cfg.get("event_cooldown_seconds", 30.0)

    def _set_cooldown(self, track_id: int, event_type: str, ts: float) -> None:
        self._cooldown_state[(track_id, event_type)] = ts

    def evaluate(
        self, track_histories: dict[int, dict], current_timestamp_s: float
    ) -> list[dict]:
        """
        Evaluate all rules against the current set of track histories.

        Parameters
        ----------
        track_histories : dict[int, dict]
            Full track history as returned by `Tracker.get_histories()`.
        current_timestamp_s : float
            The timestamp of the current video frame.

        Returns
        -------
        list[dict]
            RuleFire dicts for any rules that fired this frame. Empty if none.
        """
        fires: list[dict] = []
        zone = self.cfg.get("loitering_zone", [])
        threshold = self.cfg.get("loitering_threshold_seconds", 10.0)
        perimeter_lines = self.cfg.get("perimeter_lines", [])

        for track_id, track_data in track_histories.items():
            history = track_data.get("history", [])
            if not history:
                continue

            latest = history[-1]
            cx = latest["cx_norm"]
            cy = latest["cy_norm"]
            ts = latest["timestamp_s"]
            class_name = track_data.get("class_name", "unknown")

            # ── Rule 1: Loitering ──────────────────────────────────────────
            if zone and len(zone) >= 3:
                in_zone = _point_in_polygon(cx, cy, zone)

                if in_zone:
                    if track_id not in self._track_zone_entry:
                        # First time we see this track in the zone this session.
                        # Also scan backwards through history to find the earliest
                        # contiguous in-zone point (handles full-batch evaluate calls).
                        earliest_in_zone_ts = ts
                        for past in reversed(history[:-1]):
                            if _point_in_polygon(past["cx_norm"], past["cy_norm"], zone):
                                earliest_in_zone_ts = past["timestamp_s"]
                            else:
                                break  # contiguous run ended
                        self._track_zone_entry[track_id] = earliest_in_zone_ts

                    dwell = ts - self._track_zone_entry[track_id]

                    if (
                        dwell >= threshold
                        and not self._is_in_cooldown(track_id, "loitering", ts)
                    ):
                        fires.append({
                            "event_type": "loitering",
                            "track_id": track_id,
                            "class_name": class_name,
                            "camera_id": self.camera_id,
                            "confidence": _mean_confidence(history),
                            "timestamp_s": ts,
                            "metadata": {
                                "dwell_seconds": round(dwell, 2),
                                "zone": zone,
                            },
                        })
                        self._set_cooldown(track_id, "loitering", ts)
                        log.info(
                            f"[rules] LOITERING: track={track_id} "
                            f"dwell={dwell:.1f}s camera={self.camera_id}"
                        )
                else:
                    # Track left zone — reset entry time
                    self._track_zone_entry.pop(track_id, None)

            # ── Rule 2: Perimeter breach ───────────────────────────────────
            if len(history) >= 2:
                prev = history[-2]
                px, py = prev["cx_norm"], prev["cy_norm"]

                for line_idx, line in enumerate(perimeter_lines):
                    if len(line) < 2:
                        continue
                    lx1, ly1 = line[0]
                    lx2, ly2 = line[1]

                    prev_side = _sign_of_side(px, py, lx1, ly1, lx2, ly2)
                    curr_side = _sign_of_side(cx, cy, lx1, ly1, lx2, ly2)

                    key = (track_id, line_idx)
                    last_known = self._last_crossing_side.get(key)

                    if (
                        prev_side != 0
                        and curr_side != 0
                        and prev_side != curr_side
                        and not self._is_in_cooldown(track_id, "perimeter_breach", ts)
                    ):
                        fires.append({
                            "event_type": "perimeter_breach",
                            "track_id": track_id,
                            "class_name": class_name,
                            "camera_id": self.camera_id,
                            "confidence": _mean_confidence(history),
                            "timestamp_s": ts,
                            "metadata": {
                                "line": line,
                                "from_side": prev_side,
                                "line_idx": line_idx,
                            },
                        })
                        self._set_cooldown(track_id, "perimeter_breach", ts)
                        log.info(
                            f"[rules] PERIMETER BREACH: track={track_id} "
                            f"line={line_idx} camera={self.camera_id}"
                        )

                    self._last_crossing_side[key] = curr_side

        return fires

    def cleanup_lost_tracks(self, active_track_ids: set[int]) -> None:
        """
        Remove state for tracks that have left the scene entirely.
        Call this after each frame with the set of currently-visible track_ids.
        """
        lost = set(self._track_zone_entry.keys()) - active_track_ids
        for tid in lost:
            self._track_zone_entry.pop(tid, None)
