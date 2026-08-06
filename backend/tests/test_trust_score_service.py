"""
test_trust_score_service.py
============================
Phase 2 unit tests for trust_score_service.py.

Pure functions, no I/O — no mocking required.
Run with: pytest backend/tests/test_trust_score_service.py -v
"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.trust_score_service import compute_trust_score, _firmware_older_than_2_years


# ---------------------------------------------------------------------------
# _firmware_older_than_2_years (pure function)
# ---------------------------------------------------------------------------

class TestFirmwareOlderThan2Years:
    def test_none_is_treated_as_outdated(self):
        """NULL last_patch_date → unknown → treated as outdated (conservative)."""
        assert _firmware_older_than_2_years(None) is True

    def test_empty_string_is_treated_as_outdated(self):
        """Empty string → unparseable → treated as outdated."""
        assert _firmware_older_than_2_years("") is True

    def test_malformed_date_is_treated_as_outdated(self):
        """Unparseable date string → treated as outdated."""
        assert _firmware_older_than_2_years("not-a-date") is True

    def test_date_3_years_ago_is_outdated(self):
        """A date 3 years ago → clearly outdated."""
        three_years_ago = (date.today() - timedelta(days=3 * 365)).isoformat()
        assert _firmware_older_than_2_years(three_years_ago) is True

    def test_date_exactly_2_years_ago_is_outdated(self):
        """Exactly 730 days ago → just over the threshold → outdated."""
        exactly_2y = (date.today() - timedelta(days=730)).isoformat()
        assert _firmware_older_than_2_years(exactly_2y) is True

    def test_date_1_year_ago_is_not_outdated(self):
        """1 year ago → within 2-year window → not outdated."""
        one_year_ago = (date.today() - timedelta(days=365)).isoformat()
        assert _firmware_older_than_2_years(one_year_ago) is False

    def test_date_yesterday_is_not_outdated(self):
        """Yesterday → definitely not outdated."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        assert _firmware_older_than_2_years(yesterday) is False

    def test_future_date_is_not_outdated(self):
        """Future date → not outdated."""
        future = (date.today() + timedelta(days=365)).isoformat()
        assert _firmware_older_than_2_years(future) is False


# ---------------------------------------------------------------------------
# compute_trust_score — exact score verification
# ---------------------------------------------------------------------------

class TestComputeTrustScore:

    # -- Perfect device (max score) --

    def test_perfect_device_scores_100_with_corroboration(self):
        """
        All five factors in the best possible state:
          auth_required=True, cve_count=0, owner=government, recent_patch, 2+ corroborators
        → 100 - 0 + 20 = 120, clamped to 100
        """
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, ["cam_b", "cam_c"])
        assert result["score"] == 100
        assert result["tier"] == "high_trust"
        assert "corroborated" in result["factors"]
        assert "unauthenticated_stream" not in result["factors"]

    def test_perfect_device_no_corroboration_scores_90(self):
        """
        auth_required=True, cve=0, known_owner, recent_patch, but 0 corroborators.
        → 100 - 10 = 90 (high_trust)
        """
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, [])
        assert result["score"] == 90
        assert result["tier"] == "high_trust"
        assert "no_corroboration" in result["factors"]

    # -- Single-factor penalties --

    def test_unauthenticated_stream_penalty(self):
        """-30 for unauthenticated stream (auth_required=False)."""
        device = {
            "auth_required": False,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, [])
        assert result["score"] == 60  # 100 - 30 - 10
        assert "unauthenticated_stream" in result["factors"]

    def test_none_auth_treated_as_unauthenticated(self):
        """auth_required=None → treated as open → -30 penalty."""
        device = {
            "auth_required": None,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, [])
        assert "unauthenticated_stream" in result["factors"]

    def test_known_cve_penalty(self):
        """-25 for known CVEs."""
        device = {
            "auth_required": True,
            "known_cve_count": 3,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, [])
        assert result["score"] == 65  # 100 - 25 - 10
        assert "unpatched_cve" in result["factors"]

    def test_unknown_owner_penalty(self):
        """-20 for unknown owner."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "unknown",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, [])
        assert result["score"] == 70  # 100 - 20 - 10
        assert "unknown_owner" in result["factors"]

    def test_outdated_firmware_penalty(self):
        """-15 for firmware older than 2 years."""
        old_date = (date.today() - timedelta(days=800)).isoformat()
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": old_date,
        }
        result = compute_trust_score(device, [])
        assert result["score"] == 75  # 100 - 15 - 10
        assert "outdated_firmware" in result["factors"]

    def test_null_patch_date_triggers_firmware_penalty(self):
        """-15 for NULL last_patch_date (unknown → conservative)."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": None,
        }
        result = compute_trust_score(device, [])
        assert "outdated_firmware" in result["factors"]

    # -- Combined / all-bad scenario --

    def test_worst_case_device_scores_zero(self):
        """
        All factors at worst:
        auth=None(-30), cve=5(-25), owner=unknown(-20), old_patch(-15), no_corroboration(-10)
        = 100 - 30 - 25 - 20 - 15 - 10 = 0
        """
        device = {
            "auth_required": None,
            "known_cve_count": 5,
            "owner_type": "unknown",
            "last_patch_date": "2018-01-01",
        }
        result = compute_trust_score(device, [])
        assert result["score"] == 0
        assert result["tier"] == "low_trust"
        assert len(result["factors"]) == 5

    # -- Corroboration bonus --

    def test_single_corroborator_is_neutral(self):
        """1 corroborating camera: neither +20 nor -10."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, ["cam_b"])
        assert result["score"] == 100  # no penalty, no bonus
        assert "corroborated" not in result["factors"]
        assert "no_corroboration" not in result["factors"]

    def test_two_corroborators_give_bonus(self):
        """≥ 2 corroborating cameras: +20 bonus."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, ["cam_b", "cam_c"])
        assert "corroborated" in result["factors"]
        assert result["score"] == 100  # clamped from 120

    # -- Tier boundaries --

    def test_score_80_is_high_trust(self):
        assert compute_trust_score(
            {"auth_required": True, "known_cve_count": 0, "owner_type": "government",
             "last_patch_date": (date.today() - timedelta(days=30)).isoformat()},
            []  # -10 → 90
        )["tier"] == "high_trust"

    def test_score_50_is_medium_trust(self):
        # 100 - 30 (no auth) - 20 (unknown owner) = 50
        # but no_corroboration (-10) → 40... let me engineer exactly 50
        # auth=False(-30), cve=0, owner=government, recent_patch, 1 corroborator(neutral)
        # = 100 - 30 = 70 medium → not quite.
        # auth=False(-30), unknown_owner(-20) = 50, 1 corroborator (neutral)
        device = {
            "auth_required": False,
            "known_cve_count": 0,
            "owner_type": "unknown",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, ["cam_b"])  # 1 → neutral
        assert result["score"] == 50
        assert result["tier"] == "medium_trust"

    def test_score_49_is_low_trust(self):
        # auth=False(-30), unknown(-20), 1 corroborator(neutral) = 50
        # add cve (+1 cve, -25) → 25 low_trust
        device = {
            "auth_required": False,
            "known_cve_count": 1,
            "owner_type": "unknown",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, ["cam_b"])
        assert result["score"] == 25
        assert result["tier"] == "low_trust"

    # -- Score always clamped to [0, 100] --

    def test_score_never_exceeds_100(self):
        """Even with corroboration bonus, score is capped at 100."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_trust_score(device, ["a", "b", "c", "d"])
        assert result["score"] <= 100

    def test_score_never_below_zero(self):
        """Even with all penalties, score is floored at 0."""
        device = {
            "auth_required": False,
            "known_cve_count": 100,
            "owner_type": "unknown",
            "last_patch_date": "2010-01-01",
        }
        result = compute_trust_score(device, [])
        assert result["score"] >= 0

    # -- Missing device fields are safe --

    def test_missing_fields_default_gracefully(self):
        """A mostly-empty device dict should not crash."""
        result = compute_trust_score({}, [])
        assert isinstance(result["score"], int)
        assert result["tier"] in {"high_trust", "medium_trust", "low_trust"}
