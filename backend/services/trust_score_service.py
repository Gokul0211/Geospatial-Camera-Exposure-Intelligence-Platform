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

    Returns
    -------
    dict
        Prior/posterior probability, log-odds score, CVSS penalty factor, and action tier.
    """
    import math

    # Baseline prior log-odds for a random OSINT camera event (Prior P = 0.50 -> Log-Odds = 0.0)
    prior_prob = 0.50
    log_odds = math.log(prior_prob / (1 - prior_prob))
    factors: list[str] = []

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
        "factors": factors,
        "tier": tier,
    }


# ---------------------------------------------------------------------------
# Literature-Grounded v2/v3 Extensions (Griffioen 2020, Oliver 2025, Swami 2025)
# ---------------------------------------------------------------------------

def apply_trust_decay(
    base_score: float,
    last_scanned_at_iso: str | None,
    half_life_hours: float = 48.0,
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

        decay_rate = math.log(2) / half_life_hours
        decay_factor = math.exp(-decay_rate * delta_hours)
        decayed_score = max(0, min(100, int(round(base_score * decay_factor))))

        return {
            "decayed_score": decayed_score,
            "decay_factor": round(decay_factor, 4),
            "hours_elapsed": round(delta_hours, 1),
        }
    except (ValueError, TypeError):
        return {"decayed_score": int(base_score), "decay_factor": 1.0, "hours_elapsed": 0.0}


def compute_advanced_trust_score(
    device: dict,
    corroborating_cameras: list,
    cve_categories: list[str] | None = None,
    ping_latency_ms: float | None = None,
    enforce_critical_gates: bool = True,
) -> dict:
    """
    Literature-grounded Advanced Trust Score Engine incorporating:
    - Vulnerability Category-Aware Weights (Oliver 2025, Famera 2025)
    - Signal Latency & Heartbeat Health (YOLO Review 2025)
    - SCI-IoT Critical Security Gate Auto-Fails (Swami 2025)
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

    score = max(0, min(100, score))

    if score >= 80:
        tier = "high_trust"
    elif score >= 50:
        tier = "medium_trust"
    else:
        tier = "low_trust"

    return {"score": score, "factors": factors, "tier": tier}


