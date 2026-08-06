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

from datetime import date, datetime, timedelta


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
