"""
video_pipeline/tests/test_main_tier2_wiring.py
=================================================
Unit tests for main.py's Tier-2 wiring: `_post_detection_event` must forward
a `visual_liveness` score into the POST payload when one is available, and
`_fetch_declared_resolution` must parse the backend's integrity endpoint
response to bridge Tier-1's declared resolution into the FrameLivenessTracker
(so its spec-mismatch sub-signal has a real baseline instead of always being
disabled).

Both are pure request/response-shape tests — no real HTTP, no video decode.
"""

import sys
import os
import importlib.util
from unittest.mock import MagicMock

_VP_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _VP_DIR)


def _load_video_pipeline_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_VP_DIR, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# NOTE: both backend/config.py + backend/main.py and video_pipeline/config.py +
# video_pipeline/main.py share the bare module names "config"/"main". Several
# backend tests (test_api.py etc.) already `import main` (which itself does
# `from config import CORS_ORIGINS`), caching BACKEND's versions in
# sys.modules under those bare names — a plain `import main` here would
# silently resolve to the wrong module (and `main.py`'s own
# `from config import BACKEND_URL` would then fail against backend's config,
# which has no such name) when the full suite runs together
# (`pytest backend/tests/ video_pipeline/tests/`).
#
# Fix: temporarily swap sys.modules["config"]/["main"] to video_pipeline's own
# versions only for the duration of this load, then restore whatever backend
# had cached there — this must not leak into any other test file's imports.
_saved_modules = {name: sys.modules.pop(name, None) for name in ("config", "main")}
try:
    sys.modules["config"] = _load_video_pipeline_module("config", "config.py")
    _video_pipeline_main = _load_video_pipeline_module("main", "main.py")
finally:
    for name, mod in _saved_modules.items():
        if mod is not None:
            sys.modules[name] = mod
        else:
            sys.modules.pop(name, None)

_post_detection_event = _video_pipeline_main._post_detection_event
_fetch_declared_resolution = _video_pipeline_main._fetch_declared_resolution


class TestPostDetectionEventVisualLiveness:
    def test_visual_liveness_included_when_provided(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"alert_id": "a1", "trust_score": 20, "action_tier": "low_trust"}
        client.post.return_value = response

        success = _post_detection_event(
            client=client, camera_id="CAM1", event_type="loitering",
            confidence=0.9, metadata={}, visual_liveness=0.37,
        )

        assert success is True
        _, kwargs = client.post.call_args
        assert kwargs["json"]["visual_liveness"] == 0.37

    def test_visual_liveness_omitted_when_none(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"alert_id": "a1", "trust_score": 90, "action_tier": "high_trust"}
        client.post.return_value = response

        _post_detection_event(
            client=client, camera_id="CAM1", event_type="loitering",
            confidence=0.9, metadata={}, visual_liveness=None,
        )

        _, kwargs = client.post.call_args
        assert "visual_liveness" not in kwargs["json"]

    def test_visual_liveness_rounded_to_4dp(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"alert_id": "a1", "trust_score": 50, "action_tier": "medium_trust"}
        client.post.return_value = response

        _post_detection_event(
            client=client, camera_id="CAM1", event_type="loitering",
            confidence=0.9, metadata={}, visual_liveness=0.123456789,
        )

        _, kwargs = client.post.call_args
        assert kwargs["json"]["visual_liveness"] == 0.1235


class TestFetchDeclaredResolution:
    def test_extracts_resolution_from_integrity_endpoint(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"banner_fingerprint": {"resolution": "1080p"}}
        client.get.return_value = response

        resolution = _fetch_declared_resolution(client, "CAM1")
        assert resolution == "1080p"

    def test_returns_none_when_resolution_unknown(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"banner_fingerprint": {"resolution": "unknown"}}
        client.get.return_value = response

        assert _fetch_declared_resolution(client, "CAM1") is None

    def test_returns_none_on_404(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 404
        client.get.return_value = response

        assert _fetch_declared_resolution(client, "CAM1") is None

    def test_returns_none_on_network_error(self):
        client = MagicMock()
        client.get.side_effect = Exception("connection refused")

        assert _fetch_declared_resolution(client, "CAM1") is None

    def test_returns_none_when_fingerprint_missing(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {}
        client.get.return_value = response

        assert _fetch_declared_resolution(client, "CAM1") is None
