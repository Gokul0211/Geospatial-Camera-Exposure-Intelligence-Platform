"""
test_cisa_kev_and_temporal.py — CISA KEV Catalog & CVSS Temporal Multiplier Tests
===================================================================================
Literature: Antonakakis et al. (USENIX Security, 2017), Bernot et al. (J. Cybersecurity, 2025)
"""

import os
import sys
import pytest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.vulnerability_service import (
    is_in_kev_catalog,
    get_kev_amplification_factor,
    compute_temporal_cvss_multiplier,
    _kev_cache,
)


class TestCisaKevAndTemporal:

    @pytest.mark.asyncio
    async def test_cisa_kev_lookup_known_exploited(self):
        from datetime import datetime, timezone
        # Inject known CVE into mock cache
        with patch.dict("services.vulnerability_service._kev_cache", {"CVE-2021-36260": True}):
            with patch("services.vulnerability_service._kev_cache_loaded_at", datetime.now(timezone.utc)):
                is_kev = await is_in_kev_catalog("CVE-2021-36260")
                assert is_kev is True

                factor = await get_kev_amplification_factor(["CVE-2021-36260"])
                assert factor == 1.4

    @pytest.mark.asyncio
    async def test_cisa_kev_lookup_unexploited(self):
        from datetime import datetime, timezone
        with patch.dict("services.vulnerability_service._kev_cache", {"CVE-2021-36260": True}):
            with patch("services.vulnerability_service._kev_cache_loaded_at", datetime.now(timezone.utc)):
                is_kev = await is_in_kev_catalog("CVE-9999-00001")
                assert is_kev is False

                factor = await get_kev_amplification_factor(["CVE-9999-00001"])
                assert factor == 1.0

    def test_cvss_temporal_multiplier_calculations(self):
        # High exploit maturity (H) + Official fix (O)
        mult_patched = compute_temporal_cvss_multiplier(exploit_maturity="H", remediation_level="O")
        assert mult_patched == round(1.15 * 0.70, 4)
        assert mult_patched < 1.0  # discount for patched CVE

        # High exploit maturity (H) + Unavailable fix (U - zero-day)
        mult_zeroday = compute_temporal_cvss_multiplier(exploit_maturity="H", remediation_level="U")
        assert mult_zeroday == round(1.15 * 1.0, 4)
        assert mult_zeroday > 1.0  # amplification for unpatched weaponised zero-day

        # Default undefined values
        mult_default = compute_temporal_cvss_multiplier()
        assert mult_default == 1.0
