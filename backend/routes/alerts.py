"""
alerts.py — Modules A, B, C, F, G (Major Project)
==================================================
Three endpoints:

  GET  /api/alerts                          — recent alerts, newest first
  GET  /api/devices/{camera_id}/trust-score — on-demand trust score
  POST /api/detection-event                 — real ingestion endpoint

Major Project Enhancements (Modules A, B, C, F, G):
----------------------------------------------------
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
  - `compute_advanced_trust_score()` runs in parallel for comparison.
  - Reads `cve_categories` and `max_cvss` from the device DB row.
  - Literature: Oliver (2025), Famera et al. (2025), Bernot et al. (2025).

Module F: Re-ID Feature Embedding Corroboration
  - `DetectionEvent` accepts an optional `feature_embedding` field.
  - `check_reid_corroboration()` replaces binary event-type match.
  - Literature: Nayak et al. (iSES, 2019).

Module G: IG-DCTF — Integrity-Gated Dual-Channel Trust Fusion (PRIMARY SCORER)
  - `compute_ig_dctf_trust_score()` is now the PRIMARY decision scorer.
  - Fuses Cyber Vulnerability Channel A with Signal/Feed Authenticity Channel B.
  - `record_device_drift_and_integrity()` is called on every detection event to
    compute fresh Tier-1 banner drift from stored Shodan raw_data, persisting
    the updated `signal_integrity_score`, `last_drift_score`, and
    `integrity_gate_tripped` back to the devices table.
  - Hard gate G(s): if signal_integrity < 0.50, trust is capped at <=30
    regardless of CVE profile — preventing spoofed/decoy cameras from
    achieving high_trust via a clean CVE score alone.
  - Literature: Yilmazer & Karakose (2025), ByteTrack (2022), BIoT SLR (2026).
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
    compute_ig_dctf_trust_score,
    apply_trust_decay,
)
from services.signal_integrity_service import record_device_drift_and_integrity
from services.corroboration_service import (
    check_corroboration,
    check_reid_corroboration,
    get_velocity_alerts,
)
from services.audit_ledger import record_audit_event, record_integrity_gate_trip
from services.notification_service import dispatch_alert
from services.vulnerability_service import get_max_epss_score, get_kev_active_fraction
from services.cold_start_service import is_cold_start_device, compute_stereotype_prior

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


async def _require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    import config
    active_key = getattr(config, "DETECTION_API_KEY", "") or globals().get("DETECTION_API_KEY", "")
    if not active_key:
        return
    import hmac
    if x_api_key is None or not hmac.compare_digest(x_api_key, active_key):
        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid or missing X-API-Key. "
                "Set X-API-Key: <your key> header when calling POST/write routes. "
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
    # Module G Tier-2: optional frame-level Visual Liveness Score L(t) in [0.0, 1.0],
    # computed by video_pipeline.liveness_detector.FrameLivenessTracker for cameras
    # already inside FOOTAGE_CAMERA_MAP. None means Tier-2 unavailable for this
    # camera/event — IG-DCTF falls back to Tier-1-only signal integrity.
    visual_liveness: float | None = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Optional Tier-2 frame-level liveness score from the video pipeline (freeze/blur/spec-mismatch fusion).",
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
    # Module G: IG-DCTF signal integrity gate (research novelty)
    signal_integrity_score: float | None = None
    drift_score: float | None = None
    integrity_gate_tripped: bool = False
    gate_status: str | None = None
    cyber_trust_score: int | None = None
    # Module G: Tiered notification routing (Rasal et al. 2025)
    notification_channel: str | None = None
    notification_priority: str | None = None
    operator_verdict: str | None = None
    # Security: velocity flag for suspicious corroboration pairs (red_team_findings.md v2)
    velocity_suspicious: bool = False


class OperatorVerdictRequest(BaseModel):
    verdict: str = Field(..., description="'verified' | 'false_alarm'")
    notes: str | None = Field(default=None, description="Optional operator investigation notes")


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
    notification_channel: str | None = None,
    notification_priority: str | None = None,
    signal_integrity_score: float | None = None,
    drift_score: float | None = None,
    integrity_gate_tripped: bool = False,
) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO alerts
              (id, camera_id, city, event_type, detected_at,
               trust_score, contributing_factors, corroborated_by, action_tier,
               probabilistic_score, decayed_score, max_cvss, feature_embedding,
               notification_channel, notification_priority,
               signal_integrity_score, drift_score, integrity_gate_tripped)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                notification_channel,
                notification_priority,
                signal_integrity_score,
                drift_score,
                1 if integrity_gate_tripped else 0,
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
    Real detection event ingestion — Major Project Enhanced Pipeline (Module G: IG-DCTF).

    Flow (IG-DCTF Primary)
    ----------------------
    0. Security: idempotency key, rate limit, timestamp freshness
    1. Load device from DB (404 if not found)
    2. [Module G Tier-1] Banner-fingerprint drift: record_device_drift_and_integrity()
       computes Drift(d,t) from stored raw_data vs previous scan fingerprint,
       updates devices table (banner_fingerprint, last_drift_score, signal_integrity_score,
       integrity_gate_tripped). Returns signal_integrity for pipeline.
    3. [Module F] Re-ID cosine similarity corroboration
    4. [Module G PRIMARY] IG-DCTF: compute_ig_dctf_trust_score() fuses
       Channel A (CVE trust) × Channel B (signal integrity) via multiplicative gate G(s).
    5. [Module C] compute_advanced_trust_score() runs in parallel (comparison / secondary).
    6. [Module B] Probabilistic scoring: compute_probabilistic_trust_score()
    7. [Module A] Time-decay: apply_trust_decay() using device.fetched_at
    8. Persist alert to DB with all scores (including signal_integrity, drift_score)
    9. Record to Merkle audit ledger with full multi-model result
    10. Tiered dispatch (Rasal 2025)
    11. Broadcast over WebSocket
    12. Return full enriched AlertResponse
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

    # 2. Module G Tier-1 — Passive banner fingerprint drift (IG-DCTF research novelty)
    # Fetches stored fingerprint, diffs against raw_data from latest Shodan scan,
    # persists updated signal_integrity_score to devices table. Zero new outbound connections.
    raw_data = device.get("raw_data")  # Shodan JSON stored at ingest time
    drift_integrity_result = await record_device_drift_and_integrity(
        device_id=event.camera_id,
        raw_shodan_data=raw_data or {},
        visual_liveness=event.visual_liveness,  # Tier-2: from video_pipeline.FrameLivenessTracker, if provided
    )
    live_signal_integrity: float = drift_integrity_result["signal_integrity"]
    live_drift_score: float = drift_integrity_result["drift_score"]
    live_gate_tripped: bool = drift_integrity_result["gate"]["gate_tripped"]
    live_gate_status: str = drift_integrity_result["gate"]["gate_status"]

    # 3. Module F — Re-ID corroboration
    reid_result = await check_reid_corroboration(
        camera_id=event.camera_id,
        event_type=event.event_type,
        query_embedding=event.feature_embedding,
    )
    corroborating = reid_result["corroborating_cameras"]
    corroboration_method = reid_result["method"]

    # 4. Parse CVE categories (shared between Module C and G)
    cve_categories: list[str] = []
    raw_cats = device.get("cve_categories")
    if raw_cats:
        try:
            cve_categories = json.loads(raw_cats)
        except (json.JSONDecodeError, TypeError):
            cve_categories = []

    # 5. Module G PRIMARY — IG-DCTF: Integrity-Gated Dual-Channel Trust Fusion
    # T_final(t) = T_cve(t) * G(SignalIntegrity(t))
    # This is the PRIMARY scoring function for COBRA-WATCH v2.0 (research contribution).
    ig_result = compute_ig_dctf_trust_score(
        device=device,
        corroborating_cameras=corroborating,
        drift_score=live_drift_score,
        visual_liveness=event.visual_liveness,  # Tier-2: from video_pipeline.FrameLivenessTracker, if provided
        cve_categories=cve_categories if cve_categories else None,
    )
    # ig_result shape: final_trust_score, cyber_trust_score, signal_integrity,
    #                  drift_score, gate_multiplier, gate_status, gate_tripped, factors, tier
    trust_result = {
        "score": ig_result["final_trust_score"],
        "tier": ig_result["tier"],
        "factors": ig_result["factors"],
    }

    # Module C — Advanced CVE-category-aware scoring (parallel comparison only)
    advanced_result = compute_advanced_trust_score(
        device=device,
        corroborating_cameras=corroborating,
        cve_categories=cve_categories if cve_categories else None,
        ping_latency_ms=None,  # Module D heartbeat integrated via heartbeat_router
        enforce_critical_gates=True,
    )

    # 6. Module B — Probabilistic Bayesian scoring (parallel dual-model)
    # §5.2 Cold-start bootstrapping: a camera with zero prior alerts has no
    # history of its own, so instead of always starting from the flat,
    # uninformative 0.50 prior, check whether a "digital twin" cluster of
    # already-scored devices (same manufacturer + port signature) exists and
    # bootstrap the prior from their historical scores. Devices with their
    # own history are unaffected — this only touches the true cold-start case.
    max_cvss_val = event.max_cvss or device.get("max_cvss")
    prior_probability = 0.50
    if await is_cold_start_device(event.camera_id):
        stereotype = await compute_stereotype_prior(device)
        prior_probability = stereotype["prior_probability"]
    prob_result = compute_probabilistic_trust_score(
        device=device,
        corroborating_cameras=corroborating,
        max_cvss=max_cvss_val,
        prior_probability=prior_probability,
    )
    probabilistic_score: int = prob_result["score"]

    # 7. Module A — Time-decay score erosion (Griffioen 2020)
    # §5.1 Threat-intel-adaptive half-life: pull this device's live EPSS
    # (exploit prediction) and CISA KEV (actively-exploited) signal so a
    # device under active campaign-style exploitation decays faster than the
    # fixed 48h half-life, relaxing back toward it once exploitation activity
    # subsides. Fails open to epss=0/kev=0 (i.e. the original fixed-rate
    # behaviour) on any lookup error — decay must never block the pipeline.
    fetched_at = device.get("fetched_at")
    device_cve_ids: list[str] = []
    raw_cve_ids = device.get("cve_ids")
    if raw_cve_ids:
        try:
            device_cve_ids = json.loads(raw_cve_ids)
        except (json.JSONDecodeError, TypeError):
            device_cve_ids = []
    live_epss_score = await get_max_epss_score(device_cve_ids) if device_cve_ids else 0.0
    live_kev_fraction = await get_kev_active_fraction(device_cve_ids) if device_cve_ids else 0.0
    decay_info = apply_trust_decay(
        base_score=trust_result["score"],
        last_scanned_at_iso=fetched_at,
        half_life_hours=48.0,
        epss_score=live_epss_score,
        kev_active_fraction=live_kev_fraction,
    )
    decayed_score: int = decay_info["decayed_score"]
    decay_factor: float = decay_info["decay_factor"]
    hours_since_scan: float = decay_info["hours_elapsed"]

    # 8. Pre-generate ID & timestamps
    alert_id = str(uuid.uuid4())
    detected_at = event.detected_at or datetime.now(timezone.utc).isoformat()
    city = device.get("city", "Unknown")

    # 10. Tiered notification dispatch (Rasal et al. 2025)
    dispatch_res = await dispatch_alert({
        "alert_id": alert_id,
        "camera_id": event.camera_id,
        "city": city,
        "event_type": event.event_type,
        "trust_score": trust_result["score"],
        "action_tier": trust_result["tier"],
        "contributing_factors": trust_result["factors"],
    })

    # 11. Persist to DB (with IG-DCTF columns)
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
        notification_channel=dispatch_res["channel"],
        notification_priority=dispatch_res["priority"],
        signal_integrity_score=live_signal_integrity,
        drift_score=live_drift_score,
        integrity_gate_tripped=live_gate_tripped,
    )

    # 12. Module E — Persistent Merkle audit ledger (BIoT SLR 2026)
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
    if live_gate_tripped:
        # Dedicated INTEGRITY_GATE_TRIP ledger entry (§4.6) — independently
        # queryable via GET /api/audit/integrity-trips, rather than only
        # existing as a factor string inside the TRUST_DECISION entry above.
        record_integrity_gate_trip(
            camera_id=event.camera_id,
            drift_score=live_drift_score,
            signal_integrity=live_signal_integrity,
            gate_status=live_gate_status,
            alert_id=alert_id,
        )

    # 13. Broadcast over WebSocket (with IG-DCTF integrity gate fields)
    # Check for suspicious corroboration velocity before broadcasting
    velocity_alerts = get_velocity_alerts()
    velocity_suspicious = any(
        event.camera_id in va["camera_pair"] or
        any(c in va["camera_pair"] for c in corroborating)
        for va in velocity_alerts
    )

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
            "notification_channel": dispatch_res["channel"],
            "notification_priority": dispatch_res["priority"],
            "velocity_suspicious": velocity_suspicious,
            # Module G: IG-DCTF integrity gate fields
            "signal_integrity_score": live_signal_integrity,
            "drift_score": live_drift_score,
            "integrity_gate_tripped": live_gate_tripped,
            "gate_status": live_gate_status,
            "cyber_trust_score": ig_result["cyber_trust_score"],
        }
        if live_gate_tripped:
            # Emit a dedicated integrity gate trip event in addition to the ALERT
            await _connection_manager.broadcast({
                "type": "INTEGRITY_GATE_TRIPPED",
                "camera_id": event.camera_id,
                "city": city,
                "drift_score": live_drift_score,
                "signal_integrity": live_signal_integrity,
                "gate_status": live_gate_status,
                "detected_at": detected_at,
                "action": "dispatch_technician_for_physical_inspection",
            })
        await _connection_manager.broadcast(ws_payload)

    # 14. Return enriched response
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
        signal_integrity_score=live_signal_integrity,
        drift_score=live_drift_score,
        integrity_gate_tripped=live_gate_tripped,
        gate_status=live_gate_status,
        cyber_trust_score=ig_result["cyber_trust_score"],
        notification_channel=dispatch_res["channel"],
        notification_priority=dispatch_res["priority"],
        velocity_suspicious=velocity_suspicious,
    )


@router.get("/alerts")
async def get_alerts(city: str | None = None, limit: int = 20, decayed: bool = False):
    """
    Recent alerts, newest first.
    If decayed=True, re-evaluates exponential decay dynamically relative to current server time.
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

        # Strip feature_embedding from list response (large data)
        d.pop("feature_embedding", None)

        if decayed and d.get("detected_at"):
            decay_calc = apply_trust_decay(
                base_score=d.get("trust_score", 100),
                last_scanned_at_iso=d.get("detected_at"),
                half_life_hours=48.0,
            )
            d["live_decayed_score"] = decay_calc["decayed_score"]
            d["live_decay_factor"] = decay_calc["decay_factor"]

        result.append(d)

    return {"alerts": result, "count": len(result)}


@router.post("/alerts/{alert_id}/verdict")
async def record_operator_verdict(
    alert_id: str,
    body: OperatorVerdictRequest,
    _auth: None = Depends(_require_api_key),
):
    """
    Operator Ground-Truth Labelling Endpoint (Luna et al. 2018, ByteTrack 2022).
    Allows security analysts to submit a ground-truth verdict ('verified' or 'false_alarm').

    Requires X-API-Key authentication — unprotected verdict labelling would allow
    adversaries to poison the live precision/recall metrics (GET /api/eval/live).
    """
    if body.verdict not in ("verified", "false_alarm"):
        raise HTTPException(
            status_code=400,
            detail="Verdict must be either 'verified' (True Positive) or 'false_alarm' (False Positive).",
        )

    now_iso = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id FROM alerts WHERE id = ?", (alert_id,)) as cursor:
            existing = await cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

        await db.execute(
            """
            UPDATE alerts
               SET operator_verdict = ?,
                   verdict_recorded_at = ?
             WHERE id = ?
            """,
            (body.verdict, now_iso, alert_id),
        )
        await db.commit()

    return {
        "alert_id": alert_id,
        "operator_verdict": body.verdict,
        "recorded_at": now_iso,
        "status": "success",
    }


@router.get("/eval/live")
async def get_live_evaluation_metrics():
    """
    Rolling Live Precision/Recall & Tier Efficacy Evaluation (Luna 2018).
    Computes performance metrics across all operator-labelled alerts in the system.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT trust_score, action_tier, operator_verdict FROM alerts WHERE operator_verdict IS NOT NULL"
        ) as cursor:
            rows = await cursor.fetchall()

    total_labelled = len(rows)
    if total_labelled == 0:
        return {
            "total_labelled": 0,
            "message": "No operator verdicts recorded yet. Label alerts using the dashboard to view live metrics.",
            "precision": None,
            "recall": None,
            "f1_score": None,
            "accuracy": None,
        }

    tp = sum(1 for r in rows if r["operator_verdict"] == "verified" and r["action_tier"] == "high_trust")
    fp = sum(1 for r in rows if r["operator_verdict"] == "false_alarm" and r["action_tier"] == "high_trust")
    fn = sum(1 for r in rows if r["operator_verdict"] == "verified" and r["action_tier"] != "high_trust")
    tn = sum(1 for r in rows if r["operator_verdict"] == "false_alarm" and r["action_tier"] != "high_trust")

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    accuracy = round((tp + tn) / total_labelled, 4) if total_labelled > 0 else 0.0

    return {
        "total_labelled": total_labelled,
        "confusion_matrix": {"true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn},
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "accuracy": accuracy,
        "high_trust_filter_efficiency": round((tp + tn) / total_labelled, 4),
    }


@router.get("/devices/{camera_id}/trust-score")
async def get_device_trust_score(camera_id: str):
    """
    On-demand full Major Project trust score for a specific device.
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

    # All four scoring models (Major Project contribution)
    wa_result = compute_trust_score(device, corroborating)
    prob_result = compute_probabilistic_trust_score(
        device, corroborating, max_cvss=device.get("max_cvss")
    )
    advanced_result = compute_advanced_trust_score(
        device, corroborating, cve_categories=cve_categories or None
    )
    # IG-DCTF: use stored signal_integrity_score from last banner drift computation
    stored_signal_integrity: float = device.get("signal_integrity_score") or 1.0
    stored_drift_score: float = device.get("last_drift_score") or 0.0
    ig_result = compute_ig_dctf_trust_score(
        device=device,
        corroborating_cameras=corroborating,
        drift_score=stored_drift_score,
        visual_liveness=None,
        cve_categories=cve_categories or None,
    )
    device_cve_ids: list[str] = []
    raw_cve_ids = device.get("cve_ids")
    if raw_cve_ids:
        try:
            device_cve_ids = json.loads(raw_cve_ids)
        except (json.JSONDecodeError, TypeError):
            device_cve_ids = []
    live_epss_score = await get_max_epss_score(device_cve_ids) if device_cve_ids else 0.0
    live_kev_fraction = await get_kev_active_fraction(device_cve_ids) if device_cve_ids else 0.0
    decay_info = apply_trust_decay(
        base_score=ig_result["final_trust_score"],
        last_scanned_at_iso=device.get("fetched_at"),
        half_life_hours=48.0,
        epss_score=live_epss_score,
        kev_active_fraction=live_kev_fraction,
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
        # All four scoring models (Major Project contribution)
        "trust_score_wa": wa_result["score"],
        "trust_score_advanced": advanced_result["score"],
        "trust_score_probabilistic": prob_result["score"],
        "trust_score_ig_dctf": ig_result["final_trust_score"],
        "trust_score_decayed": decay_info["decayed_score"],
        # IG-DCTF is PRIMARY decision scorer (Module G research contribution)
        "trust_score": ig_result["final_trust_score"],
        "cyber_trust_score": ig_result["cyber_trust_score"],
        "action_tier": ig_result["tier"],
        "contributing_factors": ig_result["factors"],
        "probabilistic_factors": prob_result["factors"],
        "decay_factor": decay_info["decay_factor"],
        "hours_since_scan": decay_info["hours_elapsed"],
        "corroborating_cameras": corroborating,
        # IG-DCTF signal integrity state
        "signal_integrity_score": stored_signal_integrity,
        "drift_score": stored_drift_score,
        "integrity_gate_tripped": bool(device.get("integrity_gate_tripped", 0)),
        "gate_status": ig_result["gate_status"],
        "gate_multiplier": ig_result["gate_multiplier"],
    }
