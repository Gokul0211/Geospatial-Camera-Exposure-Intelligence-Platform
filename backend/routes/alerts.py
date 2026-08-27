"""
alerts.py — Modules A, B, C, F (IIT-B BTP)
=============================================
Three endpoints:

  GET  /api/alerts                          — recent alerts, newest first
  GET  /api/devices/{camera_id}/trust-score — on-demand trust score
  POST /api/detection-event                 — real ingestion endpoint

IIT-B BTP Enhancements (Modules A, B, C, F):
---------------------------------------------
Module A: Time-Decay Trust Volatility
  - Every alert now includes `decayed_score` and `decay_factor` in the response.
  - `apply_trust_decay()` is wired into the live pipeline using `devices.fetched_at`.
  - Literature: Griffioen & Doerr (ACM CCS, 2020).

Module B: Dual Probabilistic + WA Scoring
  - Every alert runs BOTH `compute_trust_score()` (Weighted Average / deterministic)
    AND `compute_probabilistic_trust_score()` (Bayesian log-odds posterior).
  - Both scores returned in response for academic dual-model comparison.
  - Literature: Swami et al. (SCI-IoT 2025), Ferraris et al. (2024).

Module C: CVE Category-Aware Advanced Scoring
  - `compute_advanced_trust_score()` is now the PRIMARY decision scorer.
  - Reads `cve_categories` and `max_cvss` from the device DB row.
  - Literature: Oliver (2025), Famera et al. (2025), Bernot et al. (2025).

Module F: Re-ID Feature Embedding Corroboration
  - `DetectionEvent` accepts an optional `feature_embedding` field.
  - `check_reid_corroboration()` replaces binary event-type match.
  - Literature: Nayak et al. (iSES, 2019).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from config import DATABASE_PATH, DETECTION_API_KEY
from services.trust_score_service import (
    compute_trust_score,
    compute_probabilistic_trust_score,
    compute_advanced_trust_score,
    apply_trust_decay,
)
from services.corroboration_service import check_corroboration, check_reid_corroboration
from services.audit_ledger import record_audit_event
from services.notification_service import dispatch_alert

import time

router = APIRouter()

# ---------------------------------------------------------------------------
# Connection manager reference — injected by main.py at startup
# ---------------------------------------------------------------------------
_connection_manager = None


def set_connection_manager(manager) -> None:
    """Called from main.py once the ConnectionManager is created."""
    global _connection_manager
    _connection_manager = manager


# ---------------------------------------------------------------------------
# API key dependency
# ---------------------------------------------------------------------------

async def _require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not DETECTION_API_KEY:
        return
    import hmac
    if x_api_key is None or not hmac.compare_digest(x_api_key, DETECTION_API_KEY):
        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid or missing X-API-Key. "
                "Set X-API-Key: <your key> header when calling POST /api/detection-event. "
                "GET routes do not require authentication."
            ),
        )


# ---------------------------------------------------------------------------
# Replay protection & Rate limiting
# ---------------------------------------------------------------------------
_seen_idempotency_keys: dict[str, float] = {}
_camera_request_timestamps: dict[str, list[float]] = {}
MAX_TIMESTAMP_SKEW_SECONDS = 60.0
MAX_EVENTS_PER_MINUTE = 10


def _clean_replay_cache(now: float) -> None:
    expired_keys = [k for k, t in _seen_idempotency_keys.items() if now - t > 300]
    for k in expired_keys:
        del _seen_idempotency_keys[k]
    for cam_id in list(_camera_request_timestamps.keys()):
        _camera_request_timestamps[cam_id] = [
            t for t in _camera_request_timestamps[cam_id] if now - t <= 60
        ]
        if not _camera_request_timestamps[cam_id]:
            del _camera_request_timestamps[cam_id]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class DetectionEvent(BaseModel):
    """
    Fixed contract — Phase 3 (video AI pipeline) POSTs this exact shape.
    Extended for BTP Module F with optional feature_embedding field.
    """
    camera_id: str = Field(..., description="Must match an existing devices.id")
    event_type: str = Field(
        ...,
        description="loitering | perimeter_breach | unauthorized_access | anomalous_motion",
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    detected_at: str | None = Field(
        default=None,
        description="ISO8601 timestamp. Defaults to server time if omitted.",
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional unique client nonce/UUID to prevent replay attacks.",
    )
    # Module B: optional CVSS score from caller for richer probabilistic scoring
    max_cvss: float | None = Field(
        default=None,
        description="Optional max CVSS v3 score (0.0-10.0) for probabilistic scoring.",
    )
    # Module F: optional feature embedding for Re-ID corroboration
    feature_embedding: list[float] | None = Field(
        default=None,
        description="Optional 64-dim feature embedding for Re-ID cosine similarity corroboration.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertResponse(BaseModel):
    alert_id: str
    camera_id: str
    city: str
    event_type: str
    # Module C: primary scorer is compute_advanced_trust_score
    trust_score: int
    action_tier: str
    contributing_factors: list[str]
    corroborated_by: list[str]
    detected_at: str
    # Module B: probabilistic Bayesian posterior score
    probabilistic_score: int | None = None
    # Module A: time-decay eroded score
    decayed_score: int | None = None
    decay_factor: float | None = None
    hours_since_scan: float | None = None
    # Module F: Re-ID corroboration method used
    corroboration_method: str | None = None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _get_device(camera_id: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM devices WHERE id = ?", (camera_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def _save_alert(
    alert_id: str,
    camera_id: str,
    city: str,
    event_type: str,
    trust_result: dict,
    corroborating: list[str],
    detected_at: str,
    probabilistic_score: int | None = None,
    decayed_score: int | None = None,
    max_cvss: float | None = None,
    feature_embedding: list[float] | None = None,
) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO alerts
              (id, camera_id, city, event_type, detected_at,
               trust_score, contributing_factors, corroborated_by, action_tier,
               probabilistic_score, decayed_score, max_cvss, feature_embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                camera_id,
                city,
                event_type,
                detected_at,
                trust_result["score"],
                json.dumps(trust_result["factors"]),
                json.dumps(corroborating),
                trust_result["tier"],
                probabilistic_score,
                decayed_score,
                max_cvss,
                json.dumps(feature_embedding) if feature_embedding else None,
            ),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/detection-event", response_model=AlertResponse)
async def receive_detection_event(
    event: DetectionEvent,
    _auth: None = Depends(_require_api_key),
):
    """
    Real detection event ingestion — BTP Enhanced Pipeline.

    Flow (IIT-B BTP)
    ----------------
    0. Security: idempotency key, rate limit, timestamp freshness
    1. Load device from DB (404 if not found)
    2. [Module F] Re-ID cosine similarity corroboration
    3. [Module C] Primary scoring: compute_advanced_trust_score() with CVE categories
    4. [Module B] Probabilistic scoring: compute_probabilistic_trust_score()
    5. [Module A] Time-decay: apply_trust_decay() using device.fetched_at
    6. Persist alert to DB with all scores
    7. Record to Merkle audit ledger with full dual-model result
    8. Tiered dispatch (Rasal 2025)
    9. Broadcast over WebSocket
    10. Return full enriched AlertResponse
    """
    # 0. Security hardening
    now_ts = time.time()
    _clean_replay_cache(now_ts)

    if event.idempotency_key:
        if event.idempotency_key in _seen_idempotency_keys:
            raise HTTPException(
                status_code=409,
                detail=f"Replay attack blocked: Idempotency key '{event.idempotency_key}' has already been processed.",
            )
        _seen_idempotency_keys[event.idempotency_key] = now_ts

    recent_requests = _camera_request_timestamps.setdefault(event.camera_id, [])
    if len(recent_requests) >= MAX_EVENTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for camera '{event.camera_id}'. Maximum {MAX_EVENTS_PER_MINUTE} events per minute.",
        )
    recent_requests.append(now_ts)

    if event.detected_at:
        try:
            dt = datetime.fromisoformat(event.detected_at.replace("Z", "+00:00"))
            skew = abs((datetime.now(timezone.utc) - dt).total_seconds())
            if skew > MAX_TIMESTAMP_SKEW_SECONDS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stale or invalid timestamp. Clock skew of {skew:.1f}s exceeds max allowed threshold of {MAX_TIMESTAMP_SKEW_SECONDS}s.",
                )
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid ISO8601 timestamp format for detected_at.")

    # 1. Load device
    device = await _get_device(event.camera_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{event.camera_id}' not found in devices table. "
                   "Run shodan_service or seed_demo_data.py first.",
        )

    # 2. Module F — Re-ID corroboration
    reid_result = await check_reid_corroboration(
        camera_id=event.camera_id,
        event_type=event.event_type,
        query_embedding=event.feature_embedding,
    )
    corroborating = reid_result["corroborating_cameras"]
    corroboration_method = reid_result["method"]

    # 3. Module C — Advanced CVE-category-aware scoring (primary)
    cve_categories: list[str] = []
    raw_cats = device.get("cve_categories")
    if raw_cats:
        try:
            cve_categories = json.loads(raw_cats)
        except (json.JSONDecodeError, TypeError):
            cve_categories = []

    trust_result = compute_advanced_trust_score(
        device=device,
        corroborating_cameras=corroborating,
        cve_categories=cve_categories if cve_categories else None,
        ping_latency_ms=None,  # Module D heartbeat integrated via heartbeat_router
        enforce_critical_gates=True,
    )

    # 4. Module B — Probabilistic Bayesian scoring (parallel dual-model)
    max_cvss_val = event.max_cvss or device.get("max_cvss")
    prob_result = compute_probabilistic_trust_score(
        device=device,
        corroborating_cameras=corroborating,
        max_cvss=max_cvss_val,
    )
    probabilistic_score: int = prob_result["score"]

    # 5. Module A — Time-decay score erosion (Griffioen 2020)
    fetched_at = device.get("fetched_at")
    decay_info = apply_trust_decay(
        base_score=trust_result["score"],
        last_scanned_at_iso=fetched_at,
        half_life_hours=48.0,
    )
    decayed_score: int = decay_info["decayed_score"]
    decay_factor: float = decay_info["decay_factor"]
    hours_since_scan: float = decay_info["hours_elapsed"]

    # 6. Persist
    alert_id = str(uuid.uuid4())
    detected_at = event.detected_at or datetime.now(timezone.utc).isoformat()
    city = device.get("city", "Unknown")

    await _save_alert(
        alert_id=alert_id,
        camera_id=event.camera_id,
        city=city,
        event_type=event.event_type,
        trust_result=trust_result,
        corroborating=corroborating,
        detected_at=detected_at,
        probabilistic_score=probabilistic_score,
        decayed_score=decayed_score,
        max_cvss=max_cvss_val,
        feature_embedding=event.feature_embedding,
    )

    # 7. Module E — Persistent Merkle audit ledger (BIoT SLR 2026)
    record_audit_event(
        alert_id=alert_id,
        camera_id=event.camera_id,
        trust_score=trust_result["score"],
        action_tier=trust_result["tier"],
        factors=trust_result["factors"],
        probabilistic_score=probabilistic_score,
        decayed_score=decayed_score,
        max_cvss=max_cvss_val,
    )

    # 8. Tiered dispatch (Rasal 2025)
    await dispatch_alert({
        "alert_id": alert_id,
        "camera_id": event.camera_id,
        "trust_score": trust_result["score"],
        "action_tier": trust_result["tier"],
    })

    # 9. Broadcast over WebSocket
    if _connection_manager is not None:
        ws_payload = {
            "type": "ALERT",
            "id": alert_id,
            "camera_id": event.camera_id,
            "city": city,
            "event_type": event.event_type,
            "trust_score": trust_result["score"],
            "action_tier": trust_result["tier"],
            "contributing_factors": trust_result["factors"],
            "corroborated_by": corroborating,
            "detected_at": detected_at,
            "probabilistic_score": probabilistic_score,
            "decayed_score": decayed_score,
            "decay_factor": decay_factor,
            "corroboration_method": corroboration_method,
        }
        await _connection_manager.broadcast(ws_payload)

    # 10. Return enriched response
    return AlertResponse(
        alert_id=alert_id,
        camera_id=event.camera_id,
        city=city,
        event_type=event.event_type,
        trust_score=trust_result["score"],
        action_tier=trust_result["tier"],
        contributing_factors=trust_result["factors"],
        corroborated_by=corroborating,
        detected_at=detected_at,
        probabilistic_score=probabilistic_score,
        decayed_score=decayed_score,
        decay_factor=decay_factor,
        hours_since_scan=hours_since_scan,
        corroboration_method=corroboration_method,
    )


@router.get("/alerts")
async def get_alerts(city: str | None = None, limit: int = 20):
    """
    Recent alerts, newest first.
    Now includes probabilistic_score and decayed_score columns.
    """
    limit = max(1, min(limit, 200))

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if city:
            query = """
                SELECT * FROM alerts
                 WHERE city = ?
                 ORDER BY detected_at DESC
                 LIMIT ?
            """
            params = (city, limit)
        else:
            query = """
                SELECT * FROM alerts
                 ORDER BY detected_at DESC
                 LIMIT ?
            """
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["contributing_factors"] = json.loads(d.get("contributing_factors") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["contributing_factors"] = []
        try:
            d["corroborated_by"] = json.loads(d.get("corroborated_by") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["corroborated_by"] = []
        # Strip feature_embedding from list response (large data, available on individual alert)
        d.pop("feature_embedding", None)
        result.append(d)

    return {"alerts": result, "count": len(result)}


@router.get("/devices/{camera_id}/trust-score")
async def get_device_trust_score(camera_id: str):
    """
    On-demand full BTP trust score for a specific device.
    Returns WA, probabilistic, and decayed scores alongside all factor breakdowns.
    """
    device = await _get_device(camera_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found.",
        )

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT event_type FROM alerts WHERE camera_id = ? ORDER BY detected_at DESC LIMIT 1",
            (camera_id,),
        ) as cursor:
            last_alert = await cursor.fetchone()

    event_type = last_alert[0] if last_alert else "loitering"
    corroborating = await check_corroboration(camera_id, event_type)

    # Parse CVE categories
    cve_categories: list[str] = []
    raw_cats = device.get("cve_categories")
    if raw_cats:
        try:
            cve_categories = json.loads(raw_cats)
        except (json.JSONDecodeError, TypeError):
            pass

    # All three scoring models
    wa_result = compute_trust_score(device, corroborating)
    prob_result = compute_probabilistic_trust_score(
        device, corroborating, max_cvss=device.get("max_cvss")
    )
    advanced_result = compute_advanced_trust_score(
        device, corroborating, cve_categories=cve_categories or None
    )
    decay_info = apply_trust_decay(
        base_score=advanced_result["score"],
        last_scanned_at_iso=device.get("fetched_at"),
        half_life_hours=48.0,
    )

    return {
        "camera_id": camera_id,
        "city": device.get("city"),
        "manufacturer": device.get("manufacturer"),
        "owner_type": device.get("owner_type"),
        "auth_required": device.get("auth_required"),
        "known_cve_count": device.get("known_cve_count", 0),
        "cve_categories": cve_categories,
        "max_cvss": device.get("max_cvss"),
        "last_patch_date": device.get("last_patch_date"),
        # All three scoring models (BTP dual-model contribution)
        "trust_score_wa": wa_result["score"],
        "trust_score_advanced": advanced_result["score"],
        "trust_score_probabilistic": prob_result["score"],
        "trust_score_decayed": decay_info["decayed_score"],
        # Primary decision
        "trust_score": advanced_result["score"],
        "action_tier": advanced_result["tier"],
        "contributing_factors": advanced_result["factors"],
        "probabilistic_factors": prob_result["factors"],
        "decay_factor": decay_info["decay_factor"],
        "hours_since_scan": decay_info["hours_elapsed"],
        "corroborating_cameras": corroborating,
    }
