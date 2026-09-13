"""
test_auth_detection.py
======================
Phase 1 unit tests for auth_detection.py.

`infer_auth_required` is a pure function (no I/O, no network) so every test
here is a plain synchronous call — no mocking needed.
Run with: pytest backend/tests/test_auth_detection.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.auth_detection import infer_auth_required


# ---------------------------------------------------------------------------
# Clear auth-required cases
# ---------------------------------------------------------------------------

class TestAuthRequired:
    def test_401_unauthorized_banner(self):
        """A plain '401 Unauthorized' in the banner → auth required."""
        result = infer_auth_required("HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm=\"Camera\"")
        assert result is True

    def test_www_authenticate_header(self):
        """WWW-Authenticate header presence → auth required."""
        result = infer_auth_required("HTTP/1.0 401\r\nWWW-Authenticate: Digest realm=\"IPCamera\"")
        assert result is True

    def test_password_keyword_in_banner(self):
        """'password' keyword in banner → auth required."""
        result = infer_auth_required("Please enter your username and password to access this device.")
        assert result is True

    def test_authentication_required_banner(self):
        """'Authentication required' string → auth required."""
        result = infer_auth_required("Authentication required. Please log in.")
        assert result is True

    def test_basic_realm_in_banner(self):
        """'Basic realm' in banner → auth required."""
        result = infer_auth_required('WWW-Authenticate: Basic realm="DVR"')
        assert result is True

    def test_rtsp_401_banner(self):
        """RTSP 401 response → auth required."""
        result = infer_auth_required("RTSP/1.0 401 Unauthorized\r\nWWW-Authenticate: Digest realm=\"RTSP Server\"")
        assert result is True

    def test_403_forbidden(self):
        """403 Forbidden → auth-like signal (access denied)."""
        result = infer_auth_required("HTTP/1.1 403 Forbidden\r\nContent-Type: text/html")
        assert result is True

    def test_http_401_regex(self):
        """Explicit HTTP/1.1 401 status line should be caught by regex."""
        result = infer_auth_required("HTTP/1.1 401 Unauthorized")
        assert result is True


# ---------------------------------------------------------------------------
# Clear open (unauthenticated) cases
# ---------------------------------------------------------------------------

class TestOpenAccess:
    def test_200_ok_with_mjpeg(self):
        """200 OK + MJPEG content → open access."""
        result = infer_auth_required(
            "HTTP/1.0 200 OK\r\nContent-Type: multipart/x-mixed-replace;boundary=mjpeg\r\n"
        )
        assert result is False

    def test_rtsp_200_ok(self):
        """RTSP 200 OK → open access."""
        result = infer_auth_required("RTSP/1.0 200 OK\r\nCSeq: 1\r\n")
        assert result is False

    def test_video_web_server_banner(self):
        """'video web server' in banner → open access."""
        result = infer_auth_required("Server: Video Web Server 1.0\r\nContent-Type: text/html")
        assert result is False

    def test_netcam_banner(self):
        """'netcam' in banner → open access."""
        result = infer_auth_required("NetCam/2.0 streaming server ready")
        assert result is False

    def test_ip_camera_banner_no_auth(self):
        """'IP Camera' product with 200 OK → open."""
        result = infer_auth_required("HTTP/1.1 200 OK\r\nServer: IP Camera HTTP Server")
        assert result is False

    def test_h264dvr_open_banner(self):
        """H264DVR (common Hikvision clone) without auth → open."""
        result = infer_auth_required("Server: H264DVR\r\nContent-Type: text/html")
        assert result is False

    def test_http_200_regex(self):
        """Explicit HTTP/1.1 200 status line should be caught by regex."""
        result = infer_auth_required("HTTP/1.1 200 OK")
        assert result is False


# ---------------------------------------------------------------------------
# Ambiguous / no-signal cases → None
# ---------------------------------------------------------------------------

class TestAmbiguous:
    def test_empty_banner(self):
        """Completely empty banner → None."""
        result = infer_auth_required("")
        assert result is None

    def test_none_banner(self):
        """None input → None (not a crash)."""
        result = infer_auth_required(None)
        assert result is None

    def test_generic_http_server_header_only(self):
        """A bare 'Server: Apache' with no auth or open signals → None."""
        result = infer_auth_required("Server: Apache/2.4.51")
        assert result is None

    def test_unrelated_banner(self):
        """Completely unrelated banner content → None."""
        result = infer_auth_required("SSH-2.0-OpenSSH_8.9p1 Ubuntu")
        assert result is None


# ---------------------------------------------------------------------------
# raw_data integration
# ---------------------------------------------------------------------------

class TestRawDataIntegration:
    def test_open_inferred_from_raw_product(self):
        """
        If banner is minimal but raw_data product reveals a known open-default
        manufacturer + banner has an open signal, should resolve to open.
        """
        import json
        raw = json.dumps({"product": "Hikvision Network Camera", "org": "Test Org", "os": None})
        result = infer_auth_required(
            banner_snippet="HTTP/1.1 200 OK\r\nServer: Hikvision-Webs",
            raw_data=raw,
        )
        assert result is False

    def test_raw_data_as_dict(self):
        """raw_data can be passed as a pre-parsed dict (not just a JSON string)."""
        raw = {"product": "Dahua IPC", "org": "", "os": None}
        result = infer_auth_required(
            banner_snippet="RTSP/1.0 200 OK",
            raw_data=raw,
        )
        assert result is False

    def test_raw_data_malformed_json_does_not_raise(self):
        """Malformed raw_data JSON string should not crash — treated as empty."""
        result = infer_auth_required(
            banner_snippet="HTTP/1.1 401 Unauthorized",
            raw_data="this is not json {{{",
        )
        # Auth signal from banner still wins
        assert result is True


# ---------------------------------------------------------------------------
# Auth overrides open when both signals present
# ---------------------------------------------------------------------------

class TestConflictResolution:
    def test_strong_auth_overrides_soft_open(self):
        """
        A banner that has both 'mjpeg' (open signal) AND '401 unauthorized'
        (auth signal) should favour auth when auth score is higher.
        """
        # '401 Unauthorized' + 'WWW-Authenticate' = auth_score 2
        # 'mjpeg' = open_score 1
        result = infer_auth_required(
            "HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm=\"cam\"\r\n"
            "Content-Type: multipart/x-mixed-replace;boundary=mjpeg"
        )
        assert result is True

    def test_strong_open_overrides_soft_auth_keyword(self):
        """
        'username' alone (weak, 1 point) in an otherwise clear open banner
        should not flip to auth if open signals dominate.
        """
        # 'username' in a 200 OK / mjpeg / video web server banner
        # open_score: 200 ok (regex +2) + mjpeg (+1) = 3
        # auth_score: username (+1) = 1
        result = infer_auth_required(
            "HTTP/1.1 200 OK\r\nServer: Video Web Server\r\n"
            "Content-Type: multipart/x-mixed-replace;boundary=mjpeg\r\n"
            "X-Username: admin"  # 'username' substring present
        )
        assert result is False
