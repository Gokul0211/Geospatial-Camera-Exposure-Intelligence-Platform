"""
test_epss_adaptive_decay_live.py
==================================
Tests for §5.1 — wiring live EPSS + CISA KEV signal into the
threat-intel-adaptive decay rate (`compute_adaptive_decay_rate`), rather than
that function only ever being called with defaulted epss_score=0.0 /
kev_active_fraction=0.0 (which was the actual state of the codebase before
this change — the adaptive math existed but no live caller ever fed it real
data).

Covers:
  1. `get_epss_scores` / `get_max_epss_score` — batched fetch + 24h cache,
     network-mocked (never hits the real FIRST.org API in tests).
  2. `get_kev_active_fraction` — fraction of a device's CVE list in KEV.
  3. End-to-end: `apply_trust_decay(epss_score=..., kev_active_fraction=...)`
     actually compresses the half-life relative to the flat-rate baseline.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.vulnerability_service import (
    get_epss_scores,
    get_max_epss_score,
    get_kev_active_fraction,
)
from services.trust_score_service import apply_trust_decay


def _mock_epss_response(pairs: dict[str, float]) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "data": [{"cve": cve, "epss": str(score)} for cve, score in pairs.items()]
    }
    return response


class TestEpssLiveFetch:
    @pytest.mark.asyncio
    async def test_empty_cve_list_returns_empty(self):
        assert await get_epss_scores([]) == {}
        assert await get_max_epss_score([]) == 0.0

    @pytest.mark.asyncio
    async def test_fetches_and_caches_epss_scores(self):
        with patch.dict("services.vulnerability_service._epss_cache", {}, clear=True):
            mock_get = AsyncMock(return_value=_mock_epss_response({"CVE-2021-36260": 0.94}))
            with patch("httpx.AsyncClient.get", mock_get):
                scores = await get_epss_scores(["CVE-2021-36260"])
            assert scores == {"CVE-2021-36260": 0.94}
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_score_does_not_trigger_second_network_call(self):
        now = datetime.now(timezone.utc)
        with patch.dict(
            "services.vulnerability_service._epss_cache",
            {"CVE-2021-36260": (0.5, now)},
            clear=True,
        ):
            mock_get = AsyncMock(return_value=_mock_epss_response({}))
            with patch("httpx.AsyncClient.get", mock_get):
                scores = await get_epss_scores(["CVE-2021-36260"])
            assert scores == {"CVE-2021-36260": 0.5}
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_epss_score_takes_worst_case_cve(self):
        with patch.dict("services.vulnerability_service._epss_cache", {}, clear=True):
            mock_get = AsyncMock(
                return_value=_mock_epss_response({"CVE-LOW": 0.02, "CVE-HIGH": 0.91})
            )
            with patch("httpx.AsyncClient.get", mock_get):
                max_score = await get_max_epss_score(["CVE-LOW", "CVE-HIGH"])
            assert max_score == 0.91

    @pytest.mark.asyncio
    async def test_network_failure_fails_open_to_cached_or_empty(self):
        with patch.dict("services.vulnerability_service._epss_cache", {}, clear=True):
            with patch("httpx.AsyncClient.get", AsyncMock(side_effect=Exception("network down"))):
                scores = await get_epss_scores(["CVE-2021-36260"])
                assert scores == {}
                assert await get_max_epss_score(["CVE-2021-36260"]) == 0.0


class TestKevActiveFraction:
    @pytest.mark.asyncio
    async def test_no_cves_returns_zero(self):
        assert await get_kev_active_fraction([]) == 0.0

    @pytest.mark.asyncio
    async def test_partial_kev_membership_returns_fraction(self):
        with patch.dict(
            "services.vulnerability_service._kev_cache",
            {"CVE-A": True}, clear=True,
        ):
            with patch("services.vulnerability_service._kev_cache_loaded_at", datetime.now(timezone.utc)):
                fraction = await get_kev_active_fraction(["CVE-A", "CVE-B"])
        assert fraction == 0.5

    @pytest.mark.asyncio
    async def test_full_kev_membership_returns_one(self):
        with patch.dict(
            "services.vulnerability_service._kev_cache",
            {"CVE-A": True, "CVE-B": True}, clear=True,
        ):
            with patch("services.vulnerability_service._kev_cache_loaded_at", datetime.now(timezone.utc)):
                fraction = await get_kev_active_fraction(["CVE-A", "CVE-B"])
        assert fraction == 1.0


class TestAdaptiveDecayEndToEnd:
    def test_live_epss_kev_signal_compresses_half_life_vs_flat_rate(self):
        """
        Same base score and elapsed time, but a device under active
        exploitation (high EPSS + KEV-active) should decay to a LOWER score
        than the flat 48h-rate baseline within the same elapsed window.
        """
        scanned = "2026-08-28T00:00:00+00:00"  # ~fixed reference in the past
        baseline = apply_trust_decay(
            base_score=100.0, last_scanned_at_iso=scanned, half_life_hours=48.0,
        )
        under_exploitation = apply_trust_decay(
            base_score=100.0, last_scanned_at_iso=scanned, half_life_hours=48.0,
            epss_score=0.9, kev_active_fraction=1.0,
        )
        assert under_exploitation["effective_half_life_hours"] < baseline["effective_half_life_hours"]
        assert under_exploitation["decayed_score"] <= baseline["decayed_score"]

    def test_zero_epss_zero_kev_matches_flat_rate_exactly(self):
        """Explicit epss=0/kev=0 (the pre-fix default) must reproduce the original fixed-rate behaviour exactly — no silent regression for existing callers."""
        scanned = "2026-09-01T00:00:00+00:00"
        explicit_zero = apply_trust_decay(
            base_score=80.0, last_scanned_at_iso=scanned, half_life_hours=48.0,
            epss_score=0.0, kev_active_fraction=0.0,
        )
        implicit_default = apply_trust_decay(
            base_score=80.0, last_scanned_at_iso=scanned, half_life_hours=48.0,
        )
        assert explicit_zero["decayed_score"] == implicit_default["decayed_score"]
        assert explicit_zero["effective_half_life_hours"] == 48.0
