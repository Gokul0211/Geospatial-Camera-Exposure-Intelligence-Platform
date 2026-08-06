"""
alerts.py — Phase 2
====================
Three endpoints:

  GET  /api/alerts                          — recent alerts, newest first
  GET  /api/devices/{camera_id}/trust-score — on-demand trust score
  POST /api/detection-event                 — real ingestion endpoint
                                              (fixed contract — Phase 3 depends on this)

WebSocket broadcast is done via the `broadcast` helper imported from main.py's
connection manager. The manager is passed into this module at startup via
`set_connection_manager()` — this keeps the router importable standalone (for
testing) without needing a live FastAPI app.

API-key auth note (Phase 4 ready)
----------------------------------
The `POST /api/detection-event` handler accepts an optional `api_key` header
dependency via FastAPI `Depends`. Currently it's a no-op placeholder so adding
real auth in Phase 4 is a one-line swap.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Header, Security
from pydantic import BaseModel, Field

from config import DATABASE_PATH, DETECTION_API_KEY
from services.trust_score_service import compute_trust_score
from services.corroboration_service import check_corroboration

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
# API key dependency — applied to POST /api/detection-event
# ---------------------------------------------------------------------------
# Open/closed split (deliberate, documented in report):
#   PROTECTED:  POST /api/detection-event  — prevents fabricated alert injection
#   OPEN:       all GET routes             — public surveillance transparency
#
# If DETECTION_API_KEY is empty (local dev default), auth is disabled.
# Phase 2 designed this endpoint with Depends() so this is a one-line swap.

async def _require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Enforce X-API-Key header on write endpoints.
    - If DETECTION_API_KEY is empty: auth disabled (local dev convenience).
    - If set: header must match exactly (constant-time comparison avoids timing attacks).
    """
    if not DETECTION_API_KEY:
        return  # auth disabled in local dev / when no key configured
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
# Request / Response models
# ---------------------------------------------------------------------------

class DetectionEvent(BaseModel):
    """
    Fixed contract — Phase 3 (video AI pipeline) POSTs this exact shape.
    Do NOT change field names or types.
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
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertResponse(BaseModel):
    alert_id: str
    camera_id: str
    city: str
    event_type: str
    trust_score: int
    action_tier: str
    contributing_factors: list[str]
    corroborated_by: list[str]
    detected_at: str


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _get_device(camera_id: str) -> dict | None:
    """Load a single device row from the DB by id."""
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
) -> None:
    """Persist a processed alert to the `alerts` table."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO alerts
              (id, camera_id, city, event_type, detected_at,
               trust_score, contributing_factors, corroborated_by, action_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    Real detection event ingestion.

    Flow
    ----
    1. Load device from DB (404 if not found)
    2. Run corroboration check (adjacent cameras with same event in last 15 min)
    3. Compute trust score
    4. Persist alert to DB
    5. Broadcast real-data alert over WebSocket
    6. Return trust score result + alert id

    This replaces the fake `random.choice()` WebSocket loop that was in main.py.
    Phase 3's video AI pipeline calls this endpoint when a detection rule fires.
    """
    # 1. Load device
    device = await _get_device(event.camera_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{event.camera_id}' not found in devices table. "
                   "Run shodan_service or seed_demo_data.py first.",
        )

    # 2. Corroboration check
    corroborating = await check_corroboration(event.camera_id, event.event_type)

    # 3. Compute trust score
    trust_result = compute_trust_score(device, corroborating)

    # 4. Persist
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
    )

    # 5. Broadcast over WebSocket — real message shape (replaces fake LIVE_ALERT)
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
        }
        await _connection_manager.broadcast(ws_payload)

    # 6. Return
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
    )


@router.get("/alerts")
async def get_alerts(city: str | None = None, limit: int = 20):
    """
    Recent alerts, newest first.

    Query params
    ------------
    city  : optional filter by city name
    limit : max number of alerts to return (default 20)

    Note on city derivation: we denormalize `city` onto the `alerts` table
    (simpler queries, no join needed at read time). The value is copied from
    `devices.city` at the time the detection event is ingested.
    """
    limit = max(1, min(limit, 200))  # guard against absurd values

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
        # Deserialise JSON columns
        try:
            d["contributing_factors"] = json.loads(d.get("contributing_factors") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["contributing_factors"] = []
        try:
            d["corroborated_by"] = json.loads(d.get("corroborated_by") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["corroborated_by"] = []
        result.append(d)

    return {"alerts": result, "count": len(result)}


@router.get("/devices/{camera_id}/trust-score")
async def get_device_trust_score(camera_id: str):
    """
    On-demand trust score for a specific device using its current stored
    corroboration state (recent alerts from adjacent cameras).

    Uses the same `check_corroboration` logic as `POST /api/detection-event`,
    but does NOT create an alert or broadcast. Useful for the frontend's
    DetailPanel to show a live trust indicator when a device is clicked.
    """
    device = await _get_device(camera_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_id}' not found.",
        )

    # Use a generic event_type for the on-demand check — we query across all
    # event types from adjacent cameras to give the broadest corroboration view.
    # For the on-demand score we check all event types (pass empty to get any).
    # Simpler: check the last alert's event_type from this camera if available.
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT event_type FROM alerts WHERE camera_id = ? ORDER BY detected_at DESC LIMIT 1",
            (camera_id,),
        ) as cursor:
            last_alert = await cursor.fetchone()

    event_type = last_alert[0] if last_alert else "loitering"
    corroborating = await check_corroboration(camera_id, event_type)
    trust_result = compute_trust_score(device, corroborating)

    return {
        "camera_id": camera_id,
        "city": device.get("city"),
        "manufacturer": device.get("manufacturer"),
        "owner_type": device.get("owner_type"),
        "auth_required": device.get("auth_required"),
        "known_cve_count": device.get("known_cve_count", 0),
        "last_patch_date": device.get("last_patch_date"),
        "trust_score": trust_result["score"],
        "action_tier": trust_result["tier"],
        "contributing_factors": trust_result["factors"],
        "corroborating_cameras": corroborating,
    }
