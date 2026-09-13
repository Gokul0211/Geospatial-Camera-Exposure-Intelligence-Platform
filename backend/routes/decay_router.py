"""
decay_router.py
================
Module A (Major Project) — Trust Decay Curve REST Endpoint
Literature: Griffioen & Doerr (ACM CCS, 2020)

Exposes the time-decay model as a queryable API for the frontend
AnalyticsPanel "Decay Curve" tab, which plots S(t) = S0 * exp(-λt).

Endpoints
---------
GET /api/decay-curve?camera_id={id}     — decay curve for a camera's current score
GET /api/decay-preview?base_score={n}&hours={n} — preview decay for arbitrary inputs
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, HTTPException, Query

from config import DATABASE_PATH
from services.trust_score_service import apply_trust_decay, compute_trust_score
from services.corroboration_service import check_corroboration
from services.vulnerability_service import get_max_epss_score, get_kev_active_fraction

router = APIRouter()

# Trust score half-life in hours (empirically grounded in Griffioen 2020:
# IoT devices are re-compromised in hours to days; 48h is a conservative midpoint)
DECAY_HALF_LIFE_HOURS: float = 48.0


def _generate_decay_series(
    base_score: float,
    half_life_hours: float = DECAY_HALF_LIFE_HOURS,
    points: int = 25,
    max_hours: float = 168.0,  # 7 days
) -> list[dict]:
    """
    Generate a time-series of decayed trust scores for charting.

    Returns `points` data points evenly spaced across [0, max_hours].
    Each point: {hour: float, score: int, decay_factor: float}
    """
    decay_rate = math.log(2) / half_life_hours
    step = max_hours / (points - 1)
    series = []
    for i in range(points):
        hour = step * i
        decay_factor = math.exp(-decay_rate * hour)
        score = max(0, min(100, int(round(base_score * decay_factor))))
        series.append({
            "hour": round(hour, 1),
            "score": score,
            "decay_factor": round(decay_factor, 4),
        })
    return series


@router.get("/decay-curve")
async def get_decay_curve(
    camera_id: str = Query(..., description="Camera device ID"),
    half_life_hours: float = Query(
        DECAY_HALF_LIFE_HOURS,
        ge=1.0, le=720.0,
        description="Trust score half-life in hours (default: 48h from Griffioen 2020)",
    ),
):
    """
    Return a 7-day trust score decay curve for a specific camera.

    Fetches the camera's current trust score and scan age from the DB,
    then generates a 25-point decay series for the AnalyticsPanel chart.

    The decay model: S(t) = S0 * exp(-ln(2)/T_half * t)
    where T_half = 48 hours (Griffioen & Doerr 2020 empirical finding).
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM devices WHERE id = ?", (camera_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")

    device = dict(row)

    # Compute current base trust score
    corroborating = await check_corroboration(camera_id, "loitering")
    trust_result = compute_trust_score(device, corroborating)
    base_score = trust_result["score"]

    # §5.1 threat-intel-adaptive decay: pull this device's live EPSS/KEV
    # signal so the curve reflects a compressed half-life during active
    # exploitation, rather than always the fixed 48h rate.
    device_cve_ids: list[str] = []
    raw_cve_ids = device.get("cve_ids")
    if raw_cve_ids:
        try:
            device_cve_ids = json.loads(raw_cve_ids)
        except (json.JSONDecodeError, TypeError):
            device_cve_ids = []
    live_epss_score = await get_max_epss_score(device_cve_ids) if device_cve_ids else 0.0
    live_kev_fraction = await get_kev_active_fraction(device_cve_ids) if device_cve_ids else 0.0

    # Current decay state (how much has already eroded)
    current_decay = apply_trust_decay(
        base_score=base_score,
        last_scanned_at_iso=device.get("fetched_at"),
        half_life_hours=half_life_hours,
        epss_score=live_epss_score,
        kev_active_fraction=live_kev_fraction,
    )

    effective_half_life = current_decay.get("effective_half_life_hours", half_life_hours)

    # Forward-looking decay series from current state, using the adaptive
    # half-life if EPSS/KEV compressed it.
    series = _generate_decay_series(
        base_score=base_score,
        half_life_hours=effective_half_life,
    )

    return {
        "camera_id": camera_id,
        "base_score": base_score,
        "current_decayed_score": current_decay["decayed_score"],
        "hours_since_scan": current_decay["hours_elapsed"],
        "current_decay_factor": current_decay["decay_factor"],
        "half_life_hours": half_life_hours,
        "effective_half_life_hours": effective_half_life,
        "epss_score": live_epss_score,
        "kev_active_fraction": live_kev_fraction,
        "decay_model": "S(t) = S0 * exp(-ln(2)/T_half * t)",
        "literature_source": "Griffioen & Doerr (ACM CCS, 2020): IoT device reinfection half-life",
        "decay_series": series,
    }


@router.get("/decay-preview")
async def preview_decay(
    base_score: float = Query(..., ge=0, le=100, description="Trust score to decay from"),
    half_life_hours: float = Query(DECAY_HALF_LIFE_HOURS, ge=1.0, le=720.0),
    max_hours: float = Query(168.0, ge=1.0, le=720.0, description="Time horizon in hours"),
):
    """
    Preview the decay curve for an arbitrary base_score without referencing a specific camera.
    Useful for the AnalyticsPanel slider UI.
    """
    series = _generate_decay_series(
        base_score=base_score,
        half_life_hours=half_life_hours,
        max_hours=max_hours,
    )
    return {
        "base_score": base_score,
        "half_life_hours": half_life_hours,
        "max_hours": max_hours,
        "decay_series": series,
    }
