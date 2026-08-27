"""
test_cve_categories.py
=======================
Module C (IIT-B BTP) — Tests for CVE category extraction from NVD CWE tags.
Literature: Oliver (2025), Famera et al. (2025), Bernot et al. (2025)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.vulnerability_service import (
    _extract_cve_categories,
    _extract_max_cvss,
    _CWE_TO_CATEGORY,
    KNOWN_CVE_CATEGORIES,
)


def _make_vuln(cwe_ids: list[str], cvss_score: float | None = None) -> dict:
    """Helper: construct a minimal NVD vulnerability entry."""
    entry = {
        "cve": {
            "id": "CVE-XXXX-XXXX",
            "weaknesses": [
                {
                    "description": [{"value": cwe_id, "lang": "en"} for cwe_id in cwe_ids]
                }
            ],
            "metrics": {},
        }
    }
    if cvss_score is not None:
        entry["cve"]["metrics"]["cvssMetricV31"] = [{
            "cvssData": {"baseScore": cvss_score}
        }]
    return entry


class TestCVECategoryExtraction:
    def test_rce_cwe_78(self):
        vuln = _make_vuln(["CWE-78"])
        cats = _extract_cve_categories([vuln], [])
        assert "rce" in cats

    def test_auth_bypass_cwe_287(self):
        vuln = _make_vuln(["CWE-287"])
        cats = _extract_cve_categories([vuln], [])
        assert "auth_bypass" in cats

    def test_memory_corruption_cwe_787(self):
        vuln = _make_vuln(["CWE-787"])
        cats = _extract_cve_categories([vuln], [])
        assert "memory_corruption" in cats

    def test_info_disclosure_cwe_200(self):
        vuln = _make_vuln(["CWE-200"])
        cats = _extract_cve_categories([vuln], [])
        assert "info_disclosure" in cats

    def test_xss_cwe_79(self):
        vuln = _make_vuln(["CWE-79"])
        cats = _extract_cve_categories([vuln], [])
        assert "xss" in cats

    def test_multiple_cwe_combined(self):
        vuln = _make_vuln(["CWE-78", "CWE-287"])
        cats = _extract_cve_categories([vuln], [])
        assert "rce" in cats
        assert "auth_bypass" in cats

    def test_unknown_cwe_ignored(self):
        vuln = _make_vuln(["CWE-9999"])
        cats = _extract_cve_categories([vuln], [])
        assert cats == []

    def test_empty_inputs(self):
        cats = _extract_cve_categories([], [])
        assert cats == []

    def test_known_cve_catalog_fallback(self):
        """If NVD returns no CWE tags, known CVE catalog should supply categories."""
        cats = _extract_cve_categories([], ["CVE-2021-36260"])
        assert "rce" in cats  # Hikvision command injection

    def test_hikvision_auth_bypass(self):
        cats = _extract_cve_categories([], ["CVE-2017-7921"])
        assert "auth_bypass" in cats

    def test_dahua_auth_bypass(self):
        cats = _extract_cve_categories([], ["CVE-2021-33044", "CVE-2021-33045"])
        assert "auth_bypass" in cats

    def test_throughtek_combined_rce_auth_bypass(self):
        cats = _extract_cve_categories([], ["CVE-2021-28372"])
        assert "rce" in cats
        assert "auth_bypass" in cats

    def test_no_duplicates_in_output(self):
        """Multiple CVEs with same category should not duplicate."""
        cats = _extract_cve_categories([], ["CVE-2021-33044", "CVE-2021-33045"])
        assert cats.count("auth_bypass") == 1

    def test_priority_order_rce_before_auth_bypass(self):
        """rce should appear before auth_bypass in priority order."""
        vuln = _make_vuln(["CWE-78", "CWE-287"])
        cats = _extract_cve_categories([vuln], [])
        rce_idx = cats.index("rce")
        auth_idx = cats.index("auth_bypass")
        assert rce_idx < auth_idx

    def test_cwe_mapping_coverage(self):
        """All CWEs in _CWE_TO_CATEGORY should map to valid categories."""
        valid_cats = {"rce", "auth_bypass", "memory_corruption", "info_disclosure", "xss"}
        for cwe, cat in _CWE_TO_CATEGORY.items():
            assert cat in valid_cats, f"{cwe} maps to invalid category '{cat}'"


class TestMaxCVSSExtraction:
    def test_extracts_v31_score(self):
        vuln = _make_vuln([], cvss_score=9.8)
        score = _extract_max_cvss([vuln])
        assert score == pytest.approx(9.8)

    def test_returns_max_across_multiple(self):
        v1 = _make_vuln([], cvss_score=7.5)
        v2 = _make_vuln([], cvss_score=9.8)
        v3 = _make_vuln([], cvss_score=4.0)
        score = _extract_max_cvss([v1, v2, v3])
        assert score == pytest.approx(9.8)

    def test_empty_list_returns_none(self):
        assert _extract_max_cvss([]) is None

    def test_no_cvss_data_returns_none(self):
        vuln = _make_vuln([])  # no cvss_score
        score = _extract_max_cvss([vuln])
        assert score is None

    def test_v30_fallback(self):
        vuln = {
            "cve": {
                "metrics": {
                    "cvssMetricV30": [{"cvssData": {"baseScore": 8.5}}]
                }
            }
        }
        score = _extract_max_cvss([vuln])
        assert score == pytest.approx(8.5)

    def test_score_clamped_to_10(self):
        """NVD CVSS scores should never exceed 10.0."""
        vuln = _make_vuln([], cvss_score=9.8)
        score = _extract_max_cvss([vuln])
        assert score <= 10.0
