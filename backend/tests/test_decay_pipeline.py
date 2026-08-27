"""
test_decay_pipeline.py
=======================
Module A (IIT-B BTP) — Tests for time-decay trust volatility wired into the alert pipeline.
Literature: Griffioen & Doerr (ACM CCS, 2020)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.trust_score_service import apply_trust_decay, compute_trust_score


class TestApplyTrustDecay:
    def test_no_decay_when_no_scan_date(self):
        result = apply_trust_decay(80, last_scanned_at_iso=None)
        assert result["decayed_score"] == 80
        assert result["decay_factor"] == 1.0
        assert result["hours_elapsed"] == 0.0

    def test_score_decays_at_48h_to_half(self):
        """At T_half = 48h, score should decay to exactly half."""
        from datetime import datetime, timezone, timedelta
        scanned = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        result = apply_trust_decay(100, last_scanned_at_iso=scanned, half_life_hours=48.0)
        # S(48) = 100 * exp(-ln2) = 50
        assert result["decayed_score"] == 50
        assert abs(result["decay_factor"] - 0.5) < 0.01
        assert abs(result["hours_elapsed"] - 48.0) < 1.0

    def test_score_decays_exponentially(self):
        """Score at 96h should be ~25 (two half-lives from 100)."""
        from datetime import datetime, timezone, timedelta
        scanned = (datetime.now(timezone.utc) - timedelta(hours=96)).isoformat()
        result = apply_trust_decay(100, last_scanned_at_iso=scanned, half_life_hours=48.0)
        assert result["decayed_score"] == 25
        assert abs(result["decay_factor"] - 0.25) < 0.01

    def test_clamped_at_zero(self):
        """Score should never go below 0."""
        from datetime import datetime, timezone, timedelta
        scanned = (datetime.now(timezone.utc) - timedelta(hours=9999)).isoformat()
        result = apply_trust_decay(10, last_scanned_at_iso=scanned, half_life_hours=48.0)
        assert result["decayed_score"] == 0

    def test_recent_scan_minimal_decay(self):
        """Score scanned 1 minute ago should be essentially unchanged."""
        from datetime import datetime, timezone, timedelta
        scanned = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        result = apply_trust_decay(80, last_scanned_at_iso=scanned, half_life_hours=48.0)
        assert result["decayed_score"] >= 79
        assert result["decay_factor"] > 0.99

    def test_invalid_date_returns_base_score(self):
        result = apply_trust_decay(75, last_scanned_at_iso="not-a-date")
        assert result["decayed_score"] == 75
        assert result["decay_factor"] == 1.0

    def test_custom_half_life(self):
        """Half-life of 24h: at 24h elapsed, score should be ~50% of base."""
        from datetime import datetime, timezone, timedelta
        scanned = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        result = apply_trust_decay(100, last_scanned_at_iso=scanned, half_life_hours=24.0)
        assert result["decayed_score"] == 50

    def test_zero_base_score_stays_zero(self):
        from datetime import datetime, timezone, timedelta
        scanned = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        result = apply_trust_decay(0, last_scanned_at_iso=scanned, half_life_hours=48.0)
        assert result["decayed_score"] == 0
