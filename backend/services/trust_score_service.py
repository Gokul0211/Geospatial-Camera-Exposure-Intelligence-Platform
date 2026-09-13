"""
trust_score_service.py
======================
Phase 2 — The core trust score engine.

FIXED CONTRACT — do not change weights, thresholds, or factor name strings.
Phase 4's evaluation dataset and report reference these exact values.

Formula
-------
  Start at 100.
  - Unauthenticated stream   : −30  (auth_required is False or None)
  - Known unpatched CVE      : −25  (known_cve_count > 0)
  - Unknown owner            : −20  (owner_type == "unknown")
  - Outdated firmware        : −15  (last_patch_date > 2 years ago, or NULL)
  - No corroboration         : −10  (zero nearby cameras confirmed the event)
  - Corroborated (bonus)     : +20  (≥ 2 nearby cameras confirmed it)
  Clamped to [0, 100].

Tiers
-----
  high_trust   : score ≥ 80
  medium_trust : score ≥ 50
  low_trust    : score < 50

`_firmware_older_than_2_years` contract
-----------------------------------------
Phase 1 populates `last_patch_date` as:
  - An ISO date string "YYYY-MM-DD" (from NVD published date of newest CVE)
  - None / NULL when no CVE data was found

Decision documented here for Phase 2: NULL is treated as "unknown age",
which we assume is potentially outdated → the −15 penalty applies.
This is the conservative choice: better to over-flag than to miss a
genuinely vulnerable device whose patch history is unknown.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _firmware_older_than_2_years(last_patch_date: str | None) -> bool:
    """
    Return True if `last_patch_date` indicates the device's last known patch
    was more than 2 years ago, OR if the date is None/unknown.

    Parameters
    ----------
    last_patch_date : str | None
        ISO date string "YYYY-MM-DD" from `devices.last_patch_date`, or None.

    Returns
    -------
    bool
        True  → outdated firmware penalty should apply
        False → recent enough patch date found, no penalty
    """
    if last_patch_date is None:
        # Unknown patch date — treat conservatively as outdated.
        # Documented decision: see module docstring.
        return True

    try:
        patch_date = date.fromisoformat(str(last_patch_date)[:10])
        two_years_ago = date.today() - timedelta(days=730)
        return patch_date <= two_years_ago
    except (ValueError, TypeError):
        # Unparseable date → treat as unknown → outdated
        return True


# ---------------------------------------------------------------------------
# Public API — fixed formula, do not modify
# ---------------------------------------------------------------------------

def compute_trust_score(device: dict, corroborating_cameras: list) -> dict:
    """
    Compute the trust score for a detection event from a specific camera.

    Parameters
    ----------
    device : dict
        A device row from the `devices` table. Expected keys:
          auth_required     : bool | None  (from auth_detection.py)
          known_cve_count   : int          (from vulnerability_service.py)
          owner_type        : str          ("government"|"telecom"|"corporate"|"unknown")
          last_patch_date   : str | None   (ISO date, from vulnerability_service.py)
    corroborating_cameras : list
        List of camera_id strings that have recently confirmed the same
        event type (from corroboration_service.py). Length drives the
        corroboration factor.

    Returns
    -------
    dict with keys:
        score              : int   — final trust score [0, 100]
        factors            : list  — which factor strings fired
        tier               : str   — "high_trust" | "medium_trust" | "low_trust"
    """
    score = 100
    factors: list[str] = []

    # Factor 1: Unauthenticated stream  [−30]
    # auth_required=False means open. auth_required=None means unknown → also penalise.
    if not device.get("auth_required"):
        score -= 30
        factors.append("unauthenticated_stream")

    # Factor 2: Known unpatched CVE  [−25]
    if device.get("known_cve_count", 0) > 0:
        score -= 25
        factors.append("unpatched_cve")

    # Factor 3: Unknown owner  [−20]
    if device.get("owner_type") == "unknown":
        score -= 20
        factors.append("unknown_owner")

    # Factor 4: Outdated firmware  [−15]
    if _firmware_older_than_2_years(device.get("last_patch_date")):
        score -= 15
        factors.append("outdated_firmware")

    # Factor 5: Corroboration  [−10 / +20]
    n_corroborating = len(corroborating_cameras)
    if n_corroborating == 0:
        score -= 10
        factors.append("no_corroboration")
    elif n_corroborating >= 2:
        score += 20
        factors.append("corroborated")
    # 1 corroborating camera: neither penalty nor bonus — neutral

    # Clamp
    score = max(0, min(100, score))

    # Tier
    if score >= 80:
        tier = "high_trust"
    elif score >= 50:
        tier = "medium_trust"
    else:
        tier = "low_trust"

    return {"score": score, "factors": factors, "tier": tier}


# ---------------------------------------------------------------------------
# Advanced Academic API — Probabilistic Bayesian & CVSS-Weighted Model (Phase 4 / BTP)
# ---------------------------------------------------------------------------

def compute_probabilistic_trust_score(
    device: dict,
    corroborating_cameras: list,
    max_cvss: float | None = None,
    prior_probability: float = 0.50,
) -> dict:
    """
    Academic / BTP Advanced Probabilistic Trust Score Engine.
    Uses Bayesian log-odds likelihood fusion and CVSS severity scaling.

    Parameters
    ----------
    device : dict
        Device row from DB.
    corroborating_cameras : list
        List of corroborating adjacent camera IDs.
    max_cvss : float | None
        Maximum CVSS v3 score (0.0 to 10.0) associated with the device's CVEs.
    prior_probability : float
        Starting P(genuine) before any evidence is applied. Defaults to the
        flat, uninformative 0.50 prior (fixed contract — existing callers and
        the eval harness are unaffected). Callers doing cold-start bootstrapping
        (§5.2, `services.cold_start_service.compute_stereotype_prior`) may pass
        a device-cluster-informed prior instead of the flat default for
        brand-new cameras with no scoring history of their own.

    Returns
    -------
    dict
        Prior/posterior probability, log-odds score, CVSS penalty factor, and action tier.
    """
    import math

    # Baseline prior log-odds (Prior P = 0.50 -> Log-Odds = 0.0 unless overridden)
    prior_prob = max(0.01, min(0.99, prior_probability))
    log_odds = math.log(prior_prob / (1 - prior_prob))
    factors: list[str] = []
    if prior_prob != 0.50:
        factors.append(f"cold_start_stereotype_prior_{prior_prob:.2f}")

    # 1. Auth Evidence: LR(auth=True) = 2.5, LR(auth=False/None) = 0.20
    if device.get("auth_required"):
        log_odds += math.log(2.5)
        factors.append("authenticated_stream")
    else:
        log_odds += math.log(0.20)
        factors.append("unauthenticated_stream")

    # 2. CVE & CVSS Severity Evidence
    cve_count = device.get("known_cve_count", 0)
    if cve_count > 0:
        cvss_val = max_cvss if max_cvss is not None else 7.5  # default high if unstated
        # CVSS exponential penalty multiplier
        cve_lr = max(0.05, 1.0 - (cvss_val / 10.0) * 0.85)
        log_odds += math.log(cve_lr)
        factors.append(f"unpatched_cve_cvss_{cvss_val:.1f}")

    # 3. Ownership Verification Evidence
    owner_type = device.get("owner_type", "unknown")
    if owner_type in ("government", "telecom"):
        log_odds += math.log(2.0)
        factors.append(f"verified_{owner_type}_owner")
    elif owner_type == "corporate":
        log_odds += math.log(1.3)
        factors.append("corporate_owner")
    else:
        log_odds += math.log(0.40)
        factors.append("unknown_owner")

    # 4. Patch Currency Evidence
    if _firmware_older_than_2_years(device.get("last_patch_date")):
        log_odds += math.log(0.50)
        factors.append("outdated_firmware")

    # 5. Spatial-Temporal Corroboration Evidence
    n_corroborating = len(corroborating_cameras)
    if n_corroborating >= 2:
        log_odds += math.log(4.5)  # Strong positive corroboration
        factors.append("corroborated_spatial_cluster")
    elif n_corroborating == 0:
        log_odds += math.log(0.70)
        factors.append("no_corroboration")

    # Convert posterior log-odds back to posterior probability P(Genuine | Evidence)
    posterior_prob = 1.0 / (1.0 + math.exp(-log_odds))
    score = int(round(posterior_prob * 100))

    if score >= 80:
        tier = "high_trust"
    elif score >= 50:
        tier = "medium_trust"
    else:
        tier = "low_trust"

    return {
        "score": score,
        "posterior_probability": round(posterior_prob, 4),
        "prior_probability": round(prior_prob, 4),
        "factors": factors,
        "tier": tier,
    }


# ---------------------------------------------------------------------------
# Literature-Grounded v2/v3 Extensions (Griffioen 2020, Oliver 2025, Swami 2025)
# ---------------------------------------------------------------------------

def compute_adaptive_decay_rate(
    base_half_life_hours: float = 48.0,
    epss_score: float = 0.0,
    kev_active_fraction: float = 0.0,
    beta: float = 1.5,
    gamma: float = 1.0,
) -> float:
    """
    Threat-Intelligence-Adaptive Half-Life Decay Model (§5.1).
    Dynamically compresses half-life when live EPSS velocity or CISA KEV
    active exploitation indicates campaign-level attacks.

    lambda_eff = lambda_base * (1 + beta * EPSS + gamma * KEV_fraction)
    T_half_eff = T_half_base / (1 + beta * EPSS + gamma * KEV_fraction)
    """
    scaling = 1.0 + (beta * max(0.0, min(1.0, epss_score))) + (gamma * max(0.0, min(1.0, kev_active_fraction)))
    eff_half_life = max(6.0, base_half_life_hours / scaling)
    return round(eff_half_life, 2)


def apply_trust_decay(
    base_score: float,
    last_scanned_at_iso: str | None,
    half_life_hours: float = 48.0,
    epss_score: float = 0.0,
    kev_active_fraction: float = 0.0,
) -> dict:
    """
    Time-decay exponential volatility erosion model (Griffioen & Doerr 2020).
    A camera's trust score gradually erodes over time between scan refreshes.
    S(t) = S0 * exp(-lambda * delta_t) where lambda = ln(2) / T_half_life
    """
    import math

    if not last_scanned_at_iso:
        return {"decayed_score": int(base_score), "decay_factor": 1.0, "hours_elapsed": 0.0}

    try:
        scanned_dt = datetime.fromisoformat(last_scanned_at_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta_hours = max(0.0, (now - scanned_dt).total_seconds() / 3600.0)

        eff_half_life = compute_adaptive_decay_rate(
            base_half_life_hours=half_life_hours,
            epss_score=epss_score,
            kev_active_fraction=kev_active_fraction,
        )

        decay_rate = math.log(2) / eff_half_life
        decay_factor = math.exp(-decay_rate * delta_hours)
        decayed_score = max(0, min(100, int(round(base_score * decay_factor))))

        return {
            "decayed_score": decayed_score,
            "decay_factor": round(decay_factor, 4),
            "hours_elapsed": round(delta_hours, 1),
            "effective_half_life_hours": eff_half_life,
        }
    except (ValueError, TypeError):
        return {"decayed_score": int(base_score), "decay_factor": 1.0, "hours_elapsed": 0.0}


def compute_advanced_trust_score(
    device: dict,
    corroborating_cameras: list,
    cve_categories: list[str] | None = None,
    ping_latency_ms: float | None = None,
    enforce_critical_gates: bool = True,
    signal_integrity: float | None = None,
    enforce_integrity_gate: bool = False,
) -> dict:
    """
    Literature-grounded Advanced Trust Score Engine incorporating:
    - Vulnerability Category-Aware Weights (Oliver 2025, Famera 2025)
    - Signal Latency & Heartbeat Health (YOLO Review 2025)
    - SCI-IoT Critical Security Gate Auto-Fails (Swami 2025)
    - IG-DCTF Multiplicative Integrity Gate (Optional / Feature Flagged)
    """
    score = 100
    factors: list[str] = []

    # 1. Unauthenticated Stream (-30)
    auth_req = device.get("auth_required")
    if not auth_req:
        score -= 30
        factors.append("unauthenticated_stream")

    # 2. Category-Aware CVE Deductions (Oliver 2025 / Famera 2025)
    cve_count = device.get("known_cve_count", 0)
    if cve_count > 0:
        cats = [c.lower() for c in (cve_categories or [])]
        for cat in cats:
            if cat in ("auth_bypass", "rce", "remote_code_execution", "memory_corruption", "info_disclosure", "xss"):
                factors.append(f"cve_category:{cat}(-30)" if cat in ("auth_bypass", "rce") else f"cve_category:{cat}")
        if any(c in cats for c in ("auth_bypass", "rce", "remote_code_execution")):
            deduction = 30
            factors.append("critical_cve_auth_bypass_rce")
        elif any(c in cats for c in ("command_injection", "memory_corruption")) or cve_count >= 2:
            deduction = 25
            factors.append("high_cve_unpatched" if cve_count >= 2 else "high_cve_command_injection")
        else:
            deduction = 15
            factors.append("standard_cve_unpatched")
        score -= deduction

    # 3. Ownership (-20)
    if device.get("owner_type") == "unknown":
        score -= 20
        factors.append("unknown_owner")

    # 4. Outdated Firmware (-15)
    if _firmware_older_than_2_years(device.get("last_patch_date")):
        score -= 15
        factors.append("outdated_firmware")

    # 5. Signal Latency / Health (YOLO Review 2025)
    if ping_latency_ms is not None and ping_latency_ms > 500.0:
        score -= 10
        factors.append(f"high_signal_latency_{int(ping_latency_ms)}ms")

    # 6. Corroboration (-10 / +20)
    n_corroborating = len(corroborating_cameras)
    if n_corroborating == 0:
        score -= 10
        factors.append("no_corroboration")
    elif n_corroborating >= 2:
        score += 20
        factors.append("corroborated")

    # SCI-IoT Critical Security Gate Auto-Fail (Swami 2025)
    # Unauthenticated streams are hard-capped at low_trust (< 50) regardless of corroboration
    if enforce_critical_gates and not auth_req:
        score = min(49, score)
        factors.append("critical_gate_unauthenticated_cap")

    # IG-DCTF Multiplicative Signal Integrity Gate (§4.5)
    gate_multiplier = 1.0
    gate_status = "nominal"
    if enforce_integrity_gate and signal_integrity is not None:
        from services.signal_integrity_service import evaluate_integrity_gate
        gate_res = evaluate_integrity_gate(signal_integrity)
        gate_multiplier = gate_res["multiplier"]
        gate_status = gate_res["gate_status"]
        
        score = int(round(score * gate_multiplier))
        if gate_res["hard_cap"] is not None:
            score = min(gate_res["hard_cap"], score)
            factors.append(f"integrity_gate_tripped_cap_{gate_res['hard_cap']}")
        elif gate_status == "tapered":
            factors.append(f"integrity_gate_taper_{gate_multiplier:.2f}")

    score = max(0, min(100, score))

    if score >= 80:
        tier = "high_trust"
    elif score >= 50:
        tier = "medium_trust"
    else:
        tier = "low_trust"

    result = {
        "score": score,
        "factors": factors,
        "tier": tier,
    }
    if signal_integrity is not None:
        result["signal_integrity"] = signal_integrity
        result["gate_multiplier"] = gate_multiplier
        result["gate_status"] = gate_status
    return result


# ---------------------------------------------------------------------------
# IG-DCTF — Primary Novelty Dual-Channel Trust Fusion Pipeline
# ---------------------------------------------------------------------------

def compute_ig_dctf_trust_score(
    device: dict,
    corroborating_cameras: list,
    drift_score: float = 0.0,
    visual_liveness: float | None = None,
    cve_categories: list[str] | None = None,
    ping_latency_ms: float | None = None,
) -> dict:
    """
    Integrity-Gated Dual-Channel Trust Fusion (IG-DCTF) Core API.
    Fuses:
      Channel A: Cyber Vulnerability Posture (CVE, Auth, Owner, Firmware)
      Channel B: Signal / Feed Authenticity (Passive OSINT Drift + Frame Liveness)
      Gate: Multiplicative Hard Gate G(s) capping compromised/spoofed feeds <= 30.
    """
    from services.signal_integrity_service import (
        compute_composite_signal_integrity,
        evaluate_integrity_gate,
    )

    # 1. Evaluate Channel A (Cyber Vulnerability Baseline)
    cve_result = compute_advanced_trust_score(
        device=device,
        corroborating_cameras=corroborating_cameras,
        cve_categories=cve_categories,
        ping_latency_ms=ping_latency_ms,
        enforce_critical_gates=True,
        enforce_integrity_gate=False,
    )
    t_cve = cve_result["score"]
    factors = list(cve_result["factors"])

    # 2. Evaluate Channel B (Signal Integrity Vector)
    integrity_res = compute_composite_signal_integrity(
        drift_score=drift_score,
        visual_liveness=visual_liveness,
    )
    sig_integrity = integrity_res["signal_integrity"]

    # 3. Multiplicative Gate Fusion
    gate_res = evaluate_integrity_gate(sig_integrity)
    gate_mult = gate_res["multiplier"]
    hard_cap = gate_res["hard_cap"]
    gate_status = gate_res["gate_status"]

    final_score = int(round(t_cve * gate_mult))
    if hard_cap is not None:
        final_score = min(hard_cap, final_score)
        factors.append(f"ig_dctf_hard_gate_cap_{hard_cap}")
    elif gate_status == "tapered":
        factors.append(f"ig_dctf_taper_multiplier_{gate_mult:.2f}")

    final_score = max(0, min(100, final_score))

    if final_score >= 80:
        tier = "high_trust"
    elif final_score >= 50:
        tier = "medium_trust"
    else:
        tier = "low_trust"

    return {
        "final_trust_score": final_score,
        "cyber_trust_score": t_cve,
        "signal_integrity": sig_integrity,
        "drift_score": drift_score,
        "visual_liveness": visual_liveness,
        "gate_multiplier": gate_mult,
        "gate_status": gate_status,
        "gate_tripped": gate_res["gate_tripped"],
        "factors": factors,
        "tier": tier,
    }


