"""
test_signal_integrity_gate.py
==============================
Tests for IG-DCTF Multiplicative Hard Gate G(s) and Dual-Channel Fusion (§4.5).
Verifies:
  1. Decoy / Spoofed devices with clean CVEs are gated <= 30.
  2. Nominal feeds (signal integrity >= 0.85) retain 1.0x full trust.
  3. Intermediate drift (0.50 <= s < 0.85) linearly tapers multiplier (0.3x -> 1.0x).
  4. Integration with compute_advanced_trust_score and compute_ig_dctf_trust_score.
  5. Threat-intelligence-adaptive decay rate (§5.1).
"""

import pytest
from services.signal_integrity_service import (
    compute_composite_signal_integrity,
    evaluate_integrity_gate,
    compute_visual_liveness,
    THETA_HIGH,
    THETA_LOW,
)
from services.trust_score_service import (
    compute_advanced_trust_score,
    compute_ig_dctf_trust_score,
    compute_adaptive_decay_rate,
    apply_trust_decay,
)


def test_integrity_gate_mathematical_contract():
    """Verify piecewise formulation of G(s)."""
    # 1. Nominal regime: s >= 0.85 -> multiplier 1.0, no cap, gate not tripped
    res_nom = evaluate_integrity_gate(0.95)
    assert res_nom["multiplier"] == 1.0
    assert res_nom["hard_cap"] is None
    assert res_nom["gate_tripped"] is False
    assert res_nom["gate_status"] == "nominal"

    # Boundary at theta_high
    res_high = evaluate_integrity_gate(THETA_HIGH)
    assert res_high["multiplier"] == 1.0
    assert res_high["gate_status"] == "nominal"

    # 2. Linear taper regime: 0.50 <= s < 0.85
    res_mid = evaluate_integrity_gate(0.675)
    assert 0.3 < res_mid["multiplier"] < 1.0
    assert res_mid["hard_cap"] is None
    assert res_mid["gate_tripped"] is False
    assert res_mid["gate_status"] == "tapered"

    # 3. Critical failure regime: s < 0.50 -> multiplier 0.3, hard_cap 30, gate tripped
    res_crit = evaluate_integrity_gate(0.30)
    assert res_crit["multiplier"] == 0.30
    assert res_crit["hard_cap"] == 30
    assert res_crit["gate_tripped"] is True
    assert res_crit["gate_status"] == "hard_gated"


def test_decoy_camera_with_clean_cve_profile_gated_to_low_trust():
    """
    Core Research Thesis Demonstration (§4.1):
    A device with a pristine CVE profile (authenticated, 0 CVEs, verified government owner,
    recent patch, 2 corroborators) would score 100 on naive CVE engines.
    Under IG-DCTF, if it is a swapped decoy with drift_score = 0.80 (signal_integrity = 0.20),
    it is hard-capped at <= 30 low_trust.
    """
    clean_device = {
        "auth_required": True,
        "known_cve_count": 0,
        "owner_type": "government",
        "last_patch_date": "2025-06-01",
    }
    corroborators = ["CAM_02", "CAM_03"]

    # 1. Baseline CVE-only score (without integrity gate)
    base_res = compute_advanced_trust_score(
        device=clean_device,
        corroborating_cameras=corroborators,
        enforce_critical_gates=True,
        enforce_integrity_gate=False,
    )
    assert base_res["score"] == 100
    assert base_res["tier"] == "high_trust"

    # 2. Dual-channel IG-DCTF evaluation with high drift (decoy swap)
    drift_score = 0.80  # Significant banner/resolution/header anomaly
    ig_res = compute_ig_dctf_trust_score(
        device=clean_device,
        corroborating_cameras=corroborators,
        drift_score=drift_score,
        visual_liveness=None,
    )
    assert ig_res["cyber_trust_score"] == 100
    assert ig_res["signal_integrity"] == 0.20
    assert ig_res["gate_tripped"] is True
    assert ig_res["final_trust_score"] <= 30
    assert ig_res["tier"] == "low_trust"
    assert any("ig_dctf_hard_gate_cap_30" in f for f in ig_res["factors"])


def test_tier2_frame_freeze_gates_active_stream():
    """Verify that a live video feed freeze (Tier 2) trips the integrity gate."""
    clean_device = {
        "auth_required": True,
        "known_cve_count": 0,
        "owner_type": "telecom",
        "last_patch_date": "2025-01-01",
    }
    corroborators = ["CAM_02", "CAM_03"]

    # Live frame freeze detected by pHash tracker -> liveness_score = 0.50 * (1 - 0.5) = 0.50
    # Combined with small drift -> s < 0.50
    drift_score = 0.20
    liveness_score = 0.40  # Frozen / severely blurred stream

    ig_res = compute_ig_dctf_trust_score(
        device=clean_device,
        corroborating_cameras=corroborators,
        drift_score=drift_score,
        visual_liveness=liveness_score,
    )
    # signal_integrity = (1 - 0.20) * 0.40 = 0.32 < 0.50
    assert ig_res["signal_integrity"] == 0.32
    assert ig_res["final_trust_score"] <= 30
    assert ig_res["tier"] == "low_trust"


def test_threat_intel_adaptive_decay_rate():
    """Verify adaptive half-life decay scaling by EPSS and KEV (§5.1)."""
    # 1. Base rate: 48h half-life when EPSS=0, KEV=0
    base_hl = compute_adaptive_decay_rate(base_half_life_hours=48.0, epss_score=0.0, kev_active_fraction=0.0)
    assert base_hl == 48.0

    # 2. High exploitability: EPSS=0.85, KEV active=1.0 -> compressed half life
    active_hl = compute_adaptive_decay_rate(base_half_life_hours=48.0, epss_score=0.85, kev_active_fraction=1.0)
    # scaling = 1 + 1.5*0.85 + 1.0*1.0 = 3.275 -> 48 / 3.275 ~= 14.66 hours
    assert 12.0 <= active_hl <= 16.0

    # 3. Test decay application
    decay_res = apply_trust_decay(
        base_score=100.0,
        last_scanned_at_iso="2026-08-28T00:00:00+00:00",
        half_life_hours=48.0,
        epss_score=0.85,
        kev_active_fraction=1.0,
    )
    assert decay_res["effective_half_life_hours"] == active_hl
    assert decay_res["decayed_score"] < 50  # After ~70 hours with ~14.6h half-life, eroded significantly
