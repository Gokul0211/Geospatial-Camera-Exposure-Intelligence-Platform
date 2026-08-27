"""
heartbeat_router.py
====================
Module D (IIT-B BTP) — Camera Heartbeat & Signal Integrity REST API
Literature: YOLO in Suspicious Activity Review (ResearchGate, 2025)

Exposes camera ping/heartbeat monitoring over REST, and allows the frontend
AnalyticsPanel to display live camera health status.

Endpoints
---------
GET /api/devices/{camera_id}/heartbeat  — on-demand ping + trust impact for one camera
GET /api/heartbeat/status               — bulk heartbeat status for all cameras in a city
"""

from __future__ import annotations

import asyncio

import aiosqlite
from fastapi import APIRouter, HTTPException, Query

from config import DATABASE_PATH
from services.heartbeat_service import ping_camera, get_heartbeat_trust_factor

router = APIRouter()

# Timeout for individual ping during bulk status check (shorter to avoid blocking)
BULK_PING_TIMEOUT: float = 2.0
# Max cameras to ping in bulk (prevent runaway async tasks)
BULK_PING_LIMIT: int = 50


@router.get("/devices/{camera_id}/heartbeat")
async def get_camera_heartbeat(camera_id: str):
    """
    On-demand heartbeat check for a single camera.

    Returns:
    - ping result: {reachable, latency_ms, port_used, checked_at}
    - trust_factor: {deduction, factor, status}
    - trust_impact: description of how heartbeat affects trust score

    Academic note: this endpoint instantiates the YOLO Review (2025) finding
    that camera failure/damage makes surveillance systems "non-functional" —
    COBRA-WATCH converts that failure into a scored trust penalty instead.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, ip, manufacturer, city FROM devices WHERE id = ?", (camera_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found.")

    device = dict(row)
    ip = device.get("ip")

    if not ip:
        raise HTTPException(status_code=422, detail=f"Camera '{camera_id}' has no IP address stored.")

    ping = await ping_camera(ip, timeout=3.0)
    factor = get_heartbeat_trust_factor(ping)

    status_descriptions = {
        "healthy": "Camera is reachable with normal latency. No trust deduction applied.",
        "elevated": f"Camera has elevated network latency ({ping.get('latency_ms', '?')}ms). Minor trust deduction applied.",
        "degraded": f"Camera has high network latency ({ping.get('latency_ms', '?')}ms > 500ms). Significant trust deduction applied.",
        "offline": "Camera is unreachable on all tested ports (80, 554, 8080). Maximum trust deduction applied.",
    }

    return {
        "camera_id": camera_id,
        "ip": ip,
        "manufacturer": device.get("manufacturer"),
        "city": device.get("city"),
        "ping": ping,
        "trust_factor": factor,
        "trust_impact": status_descriptions.get(factor["status"], "Unknown status."),
        "deduction_applied": factor["deduction"],
        "literature_source": "YOLO in Suspicious Activity Review (ResearchGate, 2025)",
    }


@router.get("/heartbeat/status")
async def get_bulk_heartbeat_status(
    city: str = Query(..., description="City name to check"),
    limit: int = Query(20, ge=1, le=BULK_PING_LIMIT, description=f"Max cameras to ping (max {BULK_PING_LIMIT})"),
):
    """
    Bulk heartbeat status for up to `limit` cameras in a city.
    Pings all cameras concurrently with asyncio.gather for speed.

    Returns a list of heartbeat results with trust factor for each,
    plus a summary of online/offline/degraded counts.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, ip, manufacturer FROM devices WHERE city = ? AND ip IS NOT NULL LIMIT ?",
            (city, limit),
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No devices found for city='{city}'.")

    devices = [dict(row) for row in rows]

    async def _check(device: dict) -> dict:
        ping = await ping_camera(device["ip"], timeout=BULK_PING_TIMEOUT)
        factor = get_heartbeat_trust_factor(ping)
        return {
            "camera_id": device["id"],
            "manufacturer": device.get("manufacturer"),
            "ping": ping,
            "trust_factor": factor,
        }

    results = await asyncio.gather(*[_check(d) for d in devices])

    # Summary counts
    summary = {"online": 0, "elevated": 0, "degraded": 0, "offline": 0}
    for r in results:
        status = r["trust_factor"]["status"]
        if status == "healthy":
            summary["online"] += 1
        elif status in summary:
            summary[status] += 1

    return {
        "city": city,
        "total_checked": len(results),
        "summary": summary,
        "results": results,
    }
