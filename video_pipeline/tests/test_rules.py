"""
video_pipeline/tests/test_rules.py
====================================
Unit tests for rules.py — pure logic, no video, no model weights, no ML deps.

These tests pass without ultralytics, OpenCV, or torch installed.
Run with: pytest video_pipeline/tests/test_rules.py -v
"""

import sys
import os

# Add video_pipeline/ to path (so we can import rules and config directly)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rules import RuleEngine, _point_in_polygon, _sign_of_side, _mean_confidence


# ---------------------------------------------------------------------------
# Shared test config
# ---------------------------------------------------------------------------

CENTRE_ZONE = [
    [0.25, 0.25],
    [0.75, 0.25],
    [0.75, 0.75],
    [0.25, 0.75],
]

HORIZONTAL_LINE = [[0.0, 0.5], [1.0, 0.5]]

RULES_CFG = {
    "loitering_threshold_seconds": 5.0,
    "loitering_zone": CENTRE_ZONE,
    "perimeter_lines": [HORIZONTAL_LINE],
    "event_cooldown_seconds": 10.0,
}


def _make_history(cx_values: list[float], cy_values: list[float],
                  start_ts: float = 0.0, ts_step: float = 1.0,
                  confidence: float = 0.85) -> list[dict]:
    """Build a synthetic track history from lists of (cx, cy) values."""
    return [
        {
            "frame_idx": i + 1,
            "timestamp_s": start_ts + i * ts_step,
            "cx_norm": cx,
            "cy_norm": cy,
            "bbox_norm": [cx - 0.05, cy - 0.1, cx + 0.05, cy + 0.1],
            "confidence": confidence,
        }
        for i, (cx, cy) in enumerate(zip(cx_values, cy_values))
    ]


# ---------------------------------------------------------------------------
# Tests: geometry helpers (pure functions)
# ---------------------------------------------------------------------------

class TestPointInPolygon:
    def test_centre_inside_square_zone(self):
        """Dead centre (0.5, 0.5) should be inside the zone."""
        assert _point_in_polygon(0.5, 0.5, CENTRE_ZONE) is True

    def test_corner_inside(self):
        """Just inside a corner."""
        assert _point_in_polygon(0.3, 0.3, CENTRE_ZONE) is True

    def test_outside_left(self):
        """Point clearly outside to the left."""
        assert _point_in_polygon(0.1, 0.5, CENTRE_ZONE) is False

    def test_outside_top(self):
        assert _point_in_polygon(0.5, 0.1, CENTRE_ZONE) is False

    def test_outside_right(self):
        assert _point_in_polygon(0.9, 0.5, CENTRE_ZONE) is False

    def test_outside_bottom(self):
        assert _point_in_polygon(0.5, 0.9, CENTRE_ZONE) is False

    def test_degenerate_polygon_returns_false(self):
        """A polygon with fewer than 3 vertices always returns False."""
        assert _point_in_polygon(0.5, 0.5, [[0.0, 0.0], [1.0, 1.0]]) is False

    def test_empty_polygon(self):
        assert _point_in_polygon(0.5, 0.5, []) is False


class TestSignOfSide:
    def test_above_horizontal_line(self):
        """Point at y=0.3 is above (negative y = top of frame) the y=0.5 line."""
        # Line: (0,0.5) → (1,0.5); point at (0.5, 0.3)
        # Cross product: (1-0)*(0.3-0.5) - (0.5-0.5)*(0.5-0) = -0.2 → side = -1
        result = _sign_of_side(0.5, 0.3, 0.0, 0.5, 1.0, 0.5)
        assert result == -1

    def test_below_horizontal_line(self):
        """Point at y=0.7 is below the y=0.5 line."""
        result = _sign_of_side(0.5, 0.7, 0.0, 0.5, 1.0, 0.5)
        assert result == 1

    def test_on_line_returns_zero(self):
        """Point exactly on the line returns 0."""
        result = _sign_of_side(0.5, 0.5, 0.0, 0.5, 1.0, 0.5)
        assert result == 0


class TestMeanConfidence:
    def test_single_entry(self):
        h = [{"confidence": 0.85}]
        assert abs(_mean_confidence(h) - 0.85) < 1e-6

    def test_multiple_entries(self):
        h = [{"confidence": 0.8}, {"confidence": 0.9}, {"confidence": 0.7}]
        assert abs(_mean_confidence(h) - 0.8) < 1e-6

    def test_empty_history(self):
        assert _mean_confidence([]) == 0.0


# ---------------------------------------------------------------------------
# Tests: RuleEngine — loitering
# ---------------------------------------------------------------------------

class TestLoiteringRule:
    def _make_engine(self, threshold=5.0, cooldown=10.0):
        cfg = {
            "loitering_threshold_seconds": threshold,
            "loitering_zone": CENTRE_ZONE,
            "perimeter_lines": [],
            "event_cooldown_seconds": cooldown,
        }
        return RuleEngine(camera_id="TEST_CAM", rules_config=cfg)

    def _make_in_zone_history(self, dwell_seconds: float, ts_step: float = 1.0):
        """Make a track that has been in the centre zone for `dwell_seconds`."""
        n = int(dwell_seconds / ts_step) + 1
        cxs = [0.5] * n
        cys = [0.5] * n
        return _make_history(cxs, cys, ts_step=ts_step)

    def test_no_fire_before_threshold(self):
        """Track in zone for 3s should NOT fire when threshold is 5s."""
        engine = self._make_engine(threshold=5.0)
        history = self._make_in_zone_history(3.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=3.0)
        assert fires == []

    def test_fires_at_threshold(self):
        """Track in zone for >= 5s should fire when threshold is 5s."""
        engine = self._make_engine(threshold=5.0)
        history = self._make_in_zone_history(6.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=6.0)
        loitering_fires = [f for f in fires if f["event_type"] == "loitering"]
        assert len(loitering_fires) == 1
        assert loitering_fires[0]["camera_id"] == "TEST_CAM"
        assert loitering_fires[0]["metadata"]["dwell_seconds"] >= 5.0

    def test_no_fire_when_outside_zone(self):
        """Track outside the zone should never fire loitering."""
        engine = self._make_engine(threshold=5.0)
        # Track at (0.1, 0.1) — outside CENTRE_ZONE
        history = _make_history([0.1] * 10, [0.1] * 10, ts_step=1.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=10.0)
        assert fires == []

    def test_cooldown_suppresses_repeat_fire(self):
        """After firing, the same track should not fire again within cooldown."""
        engine = self._make_engine(threshold=2.0, cooldown=30.0)
        history = self._make_in_zone_history(10.0)
        histories = {1: {"class_name": "person", "history": history}}

        # First evaluate — should fire
        fires1 = engine.evaluate(histories, current_timestamp_s=10.0)
        loitering1 = [f for f in fires1 if f["event_type"] == "loitering"]
        assert len(loitering1) == 1

        # Second evaluate immediately after — should NOT fire (in cooldown)
        fires2 = engine.evaluate(histories, current_timestamp_s=11.0)
        loitering2 = [f for f in fires2 if f["event_type"] == "loitering"]
        assert loitering2 == []

    def test_zone_exit_resets_dwell_timer(self):
        """If track leaves zone and re-enters, dwell timer resets."""
        engine = self._make_engine(threshold=5.0, cooldown=5.0)

        # Track enters zone at t=0, stays until t=3, leaves, re-enters at t=4
        # At t=6 it has been back in zone for 2 seconds — below threshold
        history = _make_history(
            [0.5, 0.5, 0.5, 0.5,   0.1,   0.5, 0.5, 0.5],
            [0.5, 0.5, 0.5, 0.5,   0.1,   0.5, 0.5, 0.5],
            ts_step=1.0
        )
        # Process frame by frame to let zone-exit-reset logic trigger
        for i, entry in enumerate(history):
            partial_history = history[:i+1]
            histories = {1: {"class_name": "person", "history": partial_history}}
            fires = engine.evaluate(histories, current_timestamp_s=entry["timestamp_s"])

        # At the end (2s since re-entry), should NOT have fired yet
        loitering = [f for f in fires if f["event_type"] == "loitering"]
        assert loitering == []

    def test_empty_zone_config_no_loitering(self):
        """If loitering_zone is empty, no loitering rule runs."""
        cfg = {
            "loitering_threshold_seconds": 5.0,
            "loitering_zone": [],
            "perimeter_lines": [],
            "event_cooldown_seconds": 10.0,
        }
        engine = RuleEngine(camera_id="TEST_CAM", rules_config=cfg)
        history = _make_history([0.5] * 10, [0.5] * 10, ts_step=1.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=10.0)
        assert fires == []


# ---------------------------------------------------------------------------
# Tests: RuleEngine — perimeter breach
# ---------------------------------------------------------------------------

class TestPerimeterBreachRule:
    def _make_engine(self, cooldown=10.0):
        cfg = {
            "loitering_threshold_seconds": 999.0,  # high to not interfere
            "loitering_zone": [],
            "perimeter_lines": [HORIZONTAL_LINE],
            "event_cooldown_seconds": cooldown,
        }
        return RuleEngine(camera_id="TEST_CAM", rules_config=cfg)

    def test_crossing_fires_breach(self):
        """Track moving from y=0.3 → y=0.7 crosses the y=0.5 line."""
        engine = self._make_engine()
        # prev: above line (y=0.3), curr: below line (y=0.7)
        history = _make_history([0.5, 0.5], [0.3, 0.7], ts_step=1.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=1.0)
        breach_fires = [f for f in fires if f["event_type"] == "perimeter_breach"]
        assert len(breach_fires) == 1
        assert breach_fires[0]["camera_id"] == "TEST_CAM"

    def test_no_breach_staying_on_same_side(self):
        """Track staying above the line should NOT fire perimeter breach."""
        engine = self._make_engine()
        history = _make_history([0.5, 0.5], [0.3, 0.35], ts_step=1.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=1.0)
        breach_fires = [f for f in fires if f["event_type"] == "perimeter_breach"]
        assert breach_fires == []

    def test_crossing_in_both_directions_fires_twice(self):
        """Track crossing up then crossing down = two breach events (with gap)."""
        cfg = {
            "loitering_threshold_seconds": 999.0,
            "loitering_zone": [],
            "perimeter_lines": [HORIZONTAL_LINE],
            "event_cooldown_seconds": 0.1,  # very short cooldown
        }
        engine = RuleEngine(camera_id="TEST_CAM", rules_config=cfg)

        # down crossing at t=1, up crossing at t=2
        cy_values = [0.3, 0.7, 0.3]
        history = _make_history([0.5, 0.5, 0.5], cy_values, ts_step=1.0)
        fires_total = []
        for i in range(2, len(history) + 1):
            partial = history[:i]
            histories = {1: {"class_name": "person", "history": partial}}
            fires = engine.evaluate(histories, current_timestamp_s=partial[-1]["timestamp_s"])
            fires_total.extend([f for f in fires if f["event_type"] == "perimeter_breach"])

        assert len(fires_total) == 2

    def test_no_breach_with_single_history_point(self):
        """Single history point (no previous point to compare) → no breach."""
        engine = self._make_engine()
        history = _make_history([0.5], [0.3], ts_step=1.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=0.0)
        assert fires == []

    def test_no_breach_when_no_perimeter_lines(self):
        """If perimeter_lines is empty, no breach rule runs."""
        cfg = {
            "loitering_threshold_seconds": 999.0,
            "loitering_zone": [],
            "perimeter_lines": [],
            "event_cooldown_seconds": 10.0,
        }
        engine = RuleEngine(camera_id="TEST_CAM", rules_config=cfg)
        history = _make_history([0.5, 0.5], [0.3, 0.7], ts_step=1.0)
        histories = {1: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=1.0)
        assert fires == []

    def test_breach_cooldown_suppresses_repeat(self):
        """Two rapid crossings within cooldown → only one event fires."""
        engine = self._make_engine(cooldown=60.0)  # 60s cooldown
        # Crosses twice in quick succession: 0.3→0.7 at t=1, stays below at t=2
        history = _make_history([0.5, 0.5], [0.3, 0.7], ts_step=0.5)
        histories = {1: {"class_name": "person", "history": history}}
        fires1 = engine.evaluate(histories, current_timestamp_s=0.5)

        # Immediately again
        history2 = _make_history([0.5, 0.5, 0.5], [0.3, 0.7, 0.3], ts_step=0.5)
        histories2 = {1: {"class_name": "person", "history": history2}}
        fires2 = engine.evaluate(histories2, current_timestamp_s=1.0)

        breach_fires = (
            [f for f in fires1 if f["event_type"] == "perimeter_breach"] +
            [f for f in fires2 if f["event_type"] == "perimeter_breach"]
        )
        assert len(breach_fires) == 1  # cooldown suppressed the second


# ---------------------------------------------------------------------------
# Tests: RuleEngine — metadata correctness
# ---------------------------------------------------------------------------

class TestRuleFireMetadata:
    def test_loitering_metadata_has_dwell_and_zone(self):
        cfg = {
            "loitering_threshold_seconds": 2.0,
            "loitering_zone": CENTRE_ZONE,
            "perimeter_lines": [],
            "event_cooldown_seconds": 100.0,
        }
        engine = RuleEngine(camera_id="CAM_X", rules_config=cfg)
        history = _make_history([0.5] * 5, [0.5] * 5, ts_step=1.0)
        histories = {42: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=4.0)
        loitering = [f for f in fires if f["event_type"] == "loitering"]
        assert len(loitering) == 1
        assert "dwell_seconds" in loitering[0]["metadata"]
        assert "zone" in loitering[0]["metadata"]
        assert loitering[0]["track_id"] == 42
        assert loitering[0]["class_name"] == "person"

    def test_perimeter_metadata_has_line(self):
        cfg = {
            "loitering_threshold_seconds": 999.0,
            "loitering_zone": [],
            "perimeter_lines": [HORIZONTAL_LINE],
            "event_cooldown_seconds": 0.0,
        }
        engine = RuleEngine(camera_id="CAM_Y", rules_config=cfg)
        history = _make_history([0.5, 0.5], [0.3, 0.7], ts_step=1.0)
        histories = {7: {"class_name": "person", "history": history}}
        fires = engine.evaluate(histories, current_timestamp_s=1.0)
        breach = [f for f in fires if f["event_type"] == "perimeter_breach"]
        assert len(breach) == 1
        assert "line" in breach[0]["metadata"]
        assert "from_side" in breach[0]["metadata"]
        assert breach[0]["track_id"] == 7
