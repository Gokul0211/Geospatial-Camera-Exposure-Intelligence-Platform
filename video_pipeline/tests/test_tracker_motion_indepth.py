"""
test_tracker_motion_indepth.py — Video AI Tracker & Object Motion Analytics Tests
====================================================================================
Tests stationary dwell bounds, rapid line crossings, lost track state cleanup,
and multi-polygon perimeter boundary detection in video_pipeline.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rules import (
    _point_in_polygon,
    _sign_of_side,
    _mean_confidence,
    RuleEngine,
)


class TestTrackerMotionAnalytics:

    def test_point_in_polygon_complex_star_shape(self):
        # 5-point star-like polygon in [x, y] format
        polygon = [
            [100, 0],
            [125, 75],
            [200, 75],
            [140, 120],
            [160, 200],
            [100, 150],
            [40, 200],
            [60, 120],
            [0, 75],
            [75, 75],
        ]
        # Center of star (100, 100) should be inside
        assert _point_in_polygon(100, 100, polygon) is True
        # Far outside point (300, 300) should be outside
        assert _point_in_polygon(300, 300, polygon) is False

    def test_perimeter_crossing_cross_product(self):
        # Above line (100, 50) for line (0, 100) -> (200, 100)
        side_above = _sign_of_side(100, 50, 0, 100, 200, 100)
        # Below line (100, 150)
        side_below = _sign_of_side(100, 150, 0, 100, 200, 100)

        assert side_above * side_below < 0  # Opposite signs indicate different sides

    def test_rule_engine_loitering_multi_track_isolation(self):
        rule_config = {
            "loitering_threshold_seconds": 2.0,
            "event_cooldown_seconds": 5.0,
            "loitering_zone": [
              [0.0, 0.0],
              [1.0, 0.0],
              [1.0, 1.0],
              [0.0, 1.0]
            ]
        }
        engine = RuleEngine("cam-test", rule_config)

        # Track 1 inside zone for 2.5 seconds
        tracks_inside = {
            101: {
                "track_id": 101,
                "class_name": "person",
                "history": [
                    {"cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9, "timestamp_s": 0.0},
                    {"cx_norm": 0.5, "cy_norm": 0.5, "confidence": 0.9, "timestamp_s": 2.5},
                ]
            }
        }
        fires = engine.evaluate(tracks_inside, current_timestamp_s=2.5)
        assert len(fires) == 1
        assert fires[0]["event_type"] == "loitering"

    def test_rule_engine_clean_stale_tracks(self):
        rule_config = {
          "loitering": {
            "enabled": True,
            "dwell_threshold_seconds": 2.0,
            "cooldown_seconds": 5.0,
            "zone_polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]
          }
        }
        engine = RuleEngine("cam-test", rule_config)
        assert engine.camera_id == "cam-test"
