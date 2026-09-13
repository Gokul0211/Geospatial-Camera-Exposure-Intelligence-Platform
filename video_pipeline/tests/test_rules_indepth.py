"""
test_rules_indepth.py
======================
In-depth geometry and state engine tests for video_pipeline/rules.py:
- Point-in-polygon ray casting algorithms (convex, concave, degenerate, vertex-coincident)
- Line crossing cross-product side determination
- RuleEngine state machine: dwell thresholds, cooldown windows, lost track cleanup
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rules import _point_in_polygon, _sign_of_side, _mean_confidence, RuleEngine


class TestGeometryHelpers:
    def test_point_in_polygon_square(self):
        square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
        assert _point_in_polygon(0.5, 0.5, square) is True
        assert _point_in_polygon(1.5, 0.5, square) is False
        assert _point_in_polygon(-0.1, 0.5, square) is False

    def test_point_in_polygon_concave_l_shape(self):
        # L-shaped polygon
        l_shape = [
            [0.0, 0.0], [0.5, 0.0], [0.5, 0.5],
            [1.0, 0.5], [1.0, 1.0], [0.0, 1.0]
        ]
        # Inside the bottom-left of L
        assert _point_in_polygon(0.2, 0.2, l_shape) is True
        # Inside top-right of L
        assert _point_in_polygon(0.8, 0.8, l_shape) is True
        # In the cut-out section (outside)
        assert _point_in_polygon(0.8, 0.2, l_shape) is False

    def test_degenerate_polygon_less_than_3_points(self):
        line_poly = [[0.0, 0.0], [1.0, 1.0]]
        assert _point_in_polygon(0.5, 0.5, line_poly) is False
        assert _point_in_polygon(0.0, 0.0, []) is False

    def test_sign_of_side_line_crossing(self):
        # Line from (0,0) to (1,1)
        lx1, ly1, lx2, ly2 = 0.0, 0.0, 1.0, 1.0

        # Point (0.2, 0.8) is to the left of the vector (0,0)->(1,1)
        assert _sign_of_side(0.2, 0.8, lx1, ly1, lx2, ly2) == 1

        # Point (0.8, 0.2) is to the right
        assert _sign_of_side(0.8, 0.2, lx1, ly1, lx2, ly2) == -1

        # Point (0.5, 0.5) is on the line
        assert _sign_of_side(0.5, 0.5, lx1, ly1, lx2, ly2) == 0

    def test_mean_confidence(self):
        assert _mean_confidence([]) == 0.0
        hist = [{"confidence": 0.8}, {"confidence": 0.9}, {"confidence": 1.0}]
        assert pytest.approx(_mean_confidence(hist)) == 0.9


class TestRuleEngineInDepth:
    def test_loitering_dwell_threshold_boundary(self):
        cfg = {
            "loitering_zone": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            "loitering_threshold_seconds": 10.0,
            "event_cooldown_seconds": 30.0,
        }
        engine = RuleEngine("cam_01", cfg)

        # Track enters at t=0s
        history = [
            {"frame_idx": 0, "timestamp_s": 0.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9},
        ]
        track_data = {"class_name": "person", "history": history}

        fires_t0 = engine.evaluate({1: track_data}, 0.0)
        assert fires_t0 == []

        # Frame at t=9.9s (under threshold -> no fire)
        history.append({"frame_idx": 99, "timestamp_s": 9.9, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9})
        fires_t9 = engine.evaluate({1: track_data}, 9.9)
        assert fires_t9 == []

        # Frame at t=10.0s (meets threshold -> FIRES)
        history.append({"frame_idx": 100, "timestamp_s": 10.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9})
        fires_t10 = engine.evaluate({1: track_data}, 10.0)

        assert len(fires_t10) == 1
        assert fires_t10[0]["event_type"] == "loitering"
        assert fires_t10[0]["track_id"] == 1
        assert fires_t10[0]["metadata"]["dwell_seconds"] == 10.0

    def test_cooldown_suppression(self):
        cfg = {
            "loitering_zone": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            "loitering_threshold_seconds": 5.0,
            "event_cooldown_seconds": 20.0,
        }
        engine = RuleEngine("cam_01", cfg)

        history = [
            {"frame_idx": 0, "timestamp_s": 0.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9},
            {"frame_idx": 50, "timestamp_s": 5.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9},
        ]
        track_data = {"class_name": "person", "history": history}

        # Fire 1 at t=5.0s
        fires1 = engine.evaluate({1: track_data}, 5.0)
        assert len(fires1) == 1

        # Frame at t=15.0s (dwell 15s > threshold 5s, but cooldown 20s not passed)
        history.append({"frame_idx": 150, "timestamp_s": 15.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9})
        fires2 = engine.evaluate({1: track_data}, 15.0)
        assert fires2 == []

        # Frame at t=26.0s (cooldown 20s passed -> FIRES AGAIN)
        history.append({"frame_idx": 260, "timestamp_s": 26.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9})
        fires3 = engine.evaluate({1: track_data}, 26.0)
        assert len(fires3) == 1

    def test_cleanup_lost_tracks(self):
        cfg = {
            "loitering_zone": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            "loitering_threshold_seconds": 5.0,
        }
        engine = RuleEngine("cam_01", cfg)

        history = [{"frame_idx": 0, "timestamp_s": 0.0, "cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9}]
        engine.evaluate({10: {"class_name": "person", "history": history}}, 0.0)

        assert 10 in engine._track_zone_entry

        # Track 10 leaves scene -> cleanup
        engine.cleanup_lost_tracks(active_track_ids=set())
        assert 10 not in engine._track_zone_entry
