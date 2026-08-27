"""
test_detector_security_boundary.py
====================================
Tests for video_pipeline/detector.py:
- Verification of ethical/legal source authorization boundary (_assert_source_is_authorized)
- Rejection of unauthorized RTSP streams and non-whitelisted paths
- Verification of allowed sample footage paths
- Detector initialization and configuration loading
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

video_pipeline_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if video_pipeline_dir not in sys.path:
    sys.path.insert(0, video_pipeline_dir)

old_config = sys.modules.get("config")
sys.modules.pop("config", None)

from detector import _assert_source_is_authorized, _ALLOWED_PATHS
from config import FOOTAGE_CAMERA_MAP

if old_config is not None:
    sys.modules["config"] = old_config


class TestDetectorSecurityBoundary:
    def test_reject_unauthorized_rtsp(self):
        unauthorized_rtsp = "rtsp://192.168.1.100:554/live.sdp"
        with pytest.raises(ValueError) as exc_info:
            _assert_source_is_authorized(unauthorized_rtsp)
        assert "NOT whitelisted" in str(exc_info.value)
        assert "unauthorized access" in str(exc_info.value)

    def test_reject_unregistered_local_file(self):
        unregistered_file = "C:/random_folder/unregistered_surveillance.mp4"
        with pytest.raises(ValueError) as exc_info:
            _assert_source_is_authorized(unregistered_file)
        assert "not registered in config.FOOTAGE_CAMERA_MAP" in str(exc_info.value)

    def test_accept_whitelisted_source(self):
        if FOOTAGE_CAMERA_MAP:
            valid_path = FOOTAGE_CAMERA_MAP[0]["path"]
            # Should not raise any exception
            _assert_source_is_authorized(valid_path)

    def test_allowed_paths_populated(self):
        assert isinstance(_ALLOWED_PATHS, set)
        assert len(_ALLOWED_PATHS) == len(FOOTAGE_CAMERA_MAP)
