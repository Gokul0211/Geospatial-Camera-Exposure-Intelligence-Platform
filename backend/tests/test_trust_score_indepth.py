"""
test_trust_score_indepth.py
============================
In-depth testing for trust_score_service.py:
- Complete 32-combination factor matrix for deterministic formula
- Exact boundary clamping [0, 100] and tier assignments
- In-depth verification of compute_probabilistic_trust_score (Bayes, CVSS)
- Robustness against missing fields, corrupt dates, and edge case inputs
"""

import os
import sys
import pytest
from itertools import product
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.trust_score_service import (
    compute_trust_score,
    compute_probabilistic_trust_score,
    _firmware_older_than_2_years,
)


class TestFirmwareDateParser:
    def test_null_date_treated_as_outdated(self):
        assert _firmware_older_than_2_years(None) is True

    def test_unparseable_date_treated_as_outdated(self):
        assert _firmware_older_than_2_years("invalid-date-string") is True
        assert _firmware_older_than_2_years(12345) is True

    def test_recent_date_not_outdated(self):
        recent_date = (date.today() - timedelta(days=100)).isoformat()
        assert _firmware_older_than_2_years(recent_date) is False

    def test_old_date_is_outdated(self):
        old_date = (date.today() - timedelta(days=800)).isoformat()
        assert _firmware_older_than_2_years(old_date) is True

    def test_exact_two_year_boundary(self):
        exact_two_years = (date.today() - timedelta(days=730)).isoformat()
        assert _firmware_older_than_2_years(exact_two_years) is True


class TestDeterministicTrustScoreMatrix:
    """Test all 2^5 = 32 factor combinations to ensure formula accuracy."""

    @pytest.mark.parametrize(
        "auth_required, cve_count, owner_type, patch_age_years, corroborating_count",
        list(product([True, False], [0, 1], ["government", "unknown"], [0.5, 3.0], [0, 2])),
    )
    def test_trust_score_matrix_permutation(
        self, auth_required, cve_count, owner_type, patch_age_years, corroborating_count
    ):
        patch_date = (
            (date.today() - timedelta(days=int(patch_age_years * 365))).isoformat()
            if patch_age_years is not None
            else None
        )
        device = {
            "auth_required": auth_required,
            "known_cve_count": cve_count,
            "owner_type": owner_type,
            "last_patch_date": patch_date,
        }
        corroborating = [f"cam_{i}" for i in range(corroborating_count)]

        result = compute_trust_score(device, corroborating)

        # Re-compute expected manually
        expected_score = 100
        expected_factors = []

        if not auth_required:
            expected_score -= 30
            expected_factors.append("unauthenticated_stream")

        if cve_count > 0:
            expected_score -= 25
            expected_factors.append("unpatched_cve")

        if owner_type == "unknown":
            expected_score -= 20
            expected_factors.append("unknown_owner")

        if patch_age_years > 2.0:
            expected_score -= 15
            expected_factors.append("outdated_firmware")

        if corroborating_count == 0:
            expected_score -= 10
            expected_factors.append("no_corroboration")
        elif corroborating_count >= 2:
            expected_score += 20
            expected_factors.append("corroborated")

        clamped_expected = max(0, min(100, expected_score))

        assert result["score"] == clamped_expected
        assert result["factors"] == expected_factors

        if clamped_expected >= 80:
            assert result["tier"] == "high_trust"
        elif clamped_expected >= 50:
            assert result["tier"] == "medium_trust"
        else:
            assert result["tier"] == "low_trust"

    def test_single_corroborating_camera_neutral(self):
        """1 corroborating camera is neutral: no penalty (-10) and no bonus (+20)."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": date.today().isoformat(),
        }
        result_1 = compute_trust_score(device, ["cam_1"])
        assert result_1["score"] == 100
        assert "no_corroboration" not in result_1["factors"]
        assert "corroborated" not in result_1["factors"]


class TestProbabilisticTrustScore:
    def test_perfect_device_probabilistic(self):
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": date.today().isoformat(),
        }
        result = compute_probabilistic_trust_score(device, ["cam_1", "cam_2"])
        assert result["score"] >= 95
        assert result["tier"] == "high_trust"
        assert result["posterior_probability"] > 0.95

    def test_worst_device_probabilistic(self):
        device = {
            "auth_required": False,
            "known_cve_count": 5,
            "owner_type": "unknown",
            "last_patch_date": "2018-01-01",
        }
        result = compute_probabilistic_trust_score(device, [], max_cvss=9.8)
        assert result["score"] <= 15
        assert result["tier"] == "low_trust"

    def test_cvss_scaling(self):
        device = {
            "auth_required": True,
            "known_cve_count": 1,
            "owner_type": "corporate",
            "last_patch_date": date.today().isoformat(),
        }
        low_cvss = compute_probabilistic_trust_score(device, ["c1", "c2"], max_cvss=2.0)
        high_cvss = compute_probabilistic_trust_score(device, ["c1", "c2"], max_cvss=10.0)

        assert low_cvss["score"] > high_cvss["score"]


class TestTrustScoreRobustness:
    def test_empty_device_dict_defaults(self):
        """compute_trust_score should handle empty dict safely without crashing."""
        result = compute_trust_score({}, [])
        # empty dict -> auth_required=False (-30), known_cve_count=0, owner_type=None, patch_date=None (-15), no_corr (-10)
        # 100 - 30 - 15 - 10 = 45 -> low_trust
        assert result["score"] == 45
        assert result["tier"] == "low_trust"

    def test_extreme_corroboration_list_size(self):
        """Very large corroborating camera list should clamp to 100."""
        device = {
            "auth_required": True,
            "known_cve_count": 0,
            "owner_type": "government",
            "last_patch_date": date.today().isoformat(),
        }
        many_cams = [f"cam_{i}" for i in range(1000)]
        result = compute_trust_score(device, many_cams)
        assert result["score"] == 100
