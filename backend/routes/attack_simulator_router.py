"""
attack_simulator_router.py
============================
Module H — Live Attack Mode / Red-Team Simulator (frontend-facing demo feature).

Every defense this module exercises already exists in the live pipeline
(idempotency check, timestamp-skew guard, per-camera rate limit, corroboration
velocity tracker, graph-based collusion detector) — this router does not add
new security logic. It drives the REAL `receive_detection_event()` pipeline
function directly (in-process, no extra HTTP hop) so the frontend can trigger
each attack shape on demand and show the actual live response, instead of a
scripted/staged animation.

Design note: `receive_detection_event` is a normal async function under
FastAPI's dependency-injection decorator — calling it directly from Python
(rather than through a real HTTP request) bypasses the `Depends(_require_api_key)`
resolution, so callers here pass `_auth=None` explicitly. That's fine: attack
simulation is an internal, unauthenticated demo action by design (it exercises
the DETECTION pipeline's OWN defenses, it doesn't need its own separate auth).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import aiosqlite
from fastapi import APIRouter, HTTPException

from config import DATABASE_PATH
from routes.alerts import (
    DetectionEvent,
    receive_detection_event,
    _seen_idempotency_keys,
    _camera_request_timestamps,
    MAX_EVENTS_PER_MINUTE,
)
from services.corroboration_service import add_adjacency, get_velocity_alerts
from services.collusion_graph_service import detect_collusion_clusters, GRAPH_EDGE_MIN_COUNT

router = APIRouter()

# Dedicated demo camera IDs — created once, reused across every simulation run
# so repeated demo clicks don't pollute the devices table with junk rows.
_SIM_CAMERA_IDS = {
    "solo": "SIM_ATTACK_SOLO",
    "ring": ["SIM_RING_A", "SIM_RING_B", "SIM_RING_C", "SIM_RING_D"],
}


async def _ensure_sim_device(camera_id: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id FROM devices WHERE id = ?", (camera_id,)) as cur:
            row = await cur.fetchone()
        if row:
            return
        await db.execute(
            """INSERT INTO devices
               (id, city, ip, lat, lon, owner_type, auth_required,
                known_cve_count, manufacturer, device_type, ports)
               VALUES (?, 'Mumbai', '10.255.0.1', 19.07, 72.87, 'unknown', 0,
                       0, 'Simulated', 'IP Camera', '[554]')""",
            (camera_id,),
        )
        await db.commit()


def _http_exc_info(e: HTTPException) -> dict:
    return {"blocked": True, "status_code": e.status_code, "detail": e.detail}


@router.post("/simulate/replay-attack")
async def simulate_replay_attack():
    """
    Send the identical `idempotency_key` twice for the same camera.
    Expected defense: second attempt → HTTP 409 (see alerts.py Step 0).
    """
    camera_id = _SIM_CAMERA_IDS["solo"]
    await _ensure_sim_device(camera_id)
    idempotency_key = str(uuid.uuid4())
    event = DetectionEvent(camera_id=camera_id, event_type="loitering", confidence=0.91, idempotency_key=idempotency_key)

    first, first_err = None, None
    try:
        first = await receive_detection_event(event=event, _auth=None)
    except HTTPException as e:
        first_err = _http_exc_info(e)

    second, second_err = None, None
    try:
        second = await receive_detection_event(event=event, _auth=None)
    except HTTPException as e:
        second_err = _http_exc_info(e)

    defense_worked = second_err is not None and second_err["status_code"] == 409
    return {
        "attack": "replay_attack",
        "description": "Re-sends the exact same idempotency_key for a second detection event.",
        "first_attempt": first_err or {"blocked": False, "alert_id": first.alert_id, "trust_score": first.trust_score},
        "second_attempt": second_err or {"blocked": False, "alert_id": second.alert_id if second else None},
        "defense_triggered": defense_worked,
        "verdict": "DEFENSE WORKED — replay blocked with HTTP 409 (idempotency check)" if defense_worked else "DEFENSE FAILED — replay was NOT blocked",
    }


@router.post("/simulate/timestamp-skew")
async def simulate_timestamp_skew():
    """
    Send a detection event backdated well beyond MAX_TIMESTAMP_SKEW_SECONDS.
    Expected defense: HTTP 400 (see alerts.py Step 0).
    """
    camera_id = _SIM_CAMERA_IDS["solo"]
    await _ensure_sim_device(camera_id)
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    event = DetectionEvent(camera_id=camera_id, event_type="loitering", confidence=0.88, detected_at=stale_time)

    err = None
    result = None
    try:
        result = await receive_detection_event(event=event, _auth=None)
    except HTTPException as e:
        err = _http_exc_info(e)

    defense_worked = err is not None and err["status_code"] == 400
    return {
        "attack": "timestamp_skew",
        "description": "Sends detected_at backdated 10 minutes (limit is 60 seconds).",
        "attempt": err or {"blocked": False, "alert_id": result.alert_id if result else None},
        "defense_triggered": defense_worked,
        "verdict": "DEFENSE WORKED — stale timestamp rejected with HTTP 400" if defense_worked else "DEFENSE FAILED — stale timestamp was accepted",
    }


@router.post("/simulate/rate-flood")
async def simulate_rate_flood():
    """
    Fire MAX_EVENTS_PER_MINUTE + 3 detection events at the same camera back to back.
    Expected defense: requests beyond the per-minute cap → HTTP 429.
    """
    camera_id = _SIM_CAMERA_IDS["solo"]
    await _ensure_sim_device(camera_id)
    # Clear this camera's own request history so the flood starts from zero,
    # independent of whatever other simulations ran earlier in the session.
    _camera_request_timestamps.pop(camera_id, None)

    attempts = []
    total = MAX_EVENTS_PER_MINUTE + 3
    for i in range(total):
        event = DetectionEvent(camera_id=camera_id, event_type="anomalous_motion", confidence=0.7, idempotency_key=str(uuid.uuid4()))
        try:
            res = await receive_detection_event(event=event, _auth=None)
            attempts.append({"n": i + 1, "blocked": False, "alert_id": res.alert_id})
        except HTTPException as e:
            attempts.append({"n": i + 1, "blocked": True, "status_code": e.status_code})

    blocked_count = sum(1 for a in attempts if a["blocked"])
    defense_worked = blocked_count >= 3  # the 3 over-the-cap requests should all be blocked
    return {
        "attack": "rate_flood",
        "description": f"Fires {total} events at one camera in immediate succession (cap is {MAX_EVENTS_PER_MINUTE}/min).",
        "attempts": attempts,
        "blocked_count": blocked_count,
        "allowed_count": total - blocked_count,
        "defense_triggered": defense_worked,
        "verdict": f"DEFENSE WORKED — {blocked_count}/{total} requests rate-limited with HTTP 429" if defense_worked else "DEFENSE FAILED — flood was not rate-limited",
    }


@router.post("/simulate/collusion-ring")
async def simulate_collusion_ring():
    """
    Sets up 4 cameras in a corroboration RING (A-B-C-D-A) and drives real
    detection events around the ring twice — enough for every edge to cross
    GRAPH_EDGE_MIN_COUNT while each individual pairwise edge stays under the
    single-pair velocity threshold (5/60min) — exactly the distributed-collusion
    blind spot §5.3 was built to catch. Then runs the real graph detector.
    """
    cams = _SIM_CAMERA_IDS["ring"]
    for cid in cams:
        await _ensure_sim_device(cid)

    # Ring adjacency: A-B, B-C, C-D, D-A (bidirectional, via add_adjacency)
    ring_edges = list(zip(cams, cams[1:] + cams[:1]))
    for a, b in ring_edges:
        await add_adjacency(a, b)

    # Drive real detection events around the ring twice so every edge crosses
    # GRAPH_EDGE_MIN_COUNT (2) — each pass: firing on cam[i] lets check_corroboration
    # see cam[i-1]'s just-posted alert (they're adjacent), recording that pair.
    events_fired = 0
    for _ in range(GRAPH_EDGE_MIN_COUNT):
        for cid in cams:
            event = DetectionEvent(camera_id=cid, event_type="loitering", confidence=0.85, idempotency_key=str(uuid.uuid4()))
            try:
                await receive_detection_event(event=event, _auth=None)
                events_fired += 1
            except HTTPException:
                pass  # rate limit is per-camera; ring cameras rarely collide with it here

    clusters = detect_collusion_clusters()
    ring_detected = any(set(cams).issubset(set(c["camera_ids"])) or set(c["camera_ids"]) == set(cams) for c in clusters)
    velocity_alerts = get_velocity_alerts()
    ring_pairs_flagged_individually = [
        va for va in velocity_alerts if set(va["camera_pair"]).issubset(set(cams))
    ]

    return {
        "attack": "collusion_ring",
        "description": "4 cameras (A→B→C→D→A) manufacture corroboration in a ring; each pairwise edge stays under the single-pair velocity threshold.",
        "ring_cameras": cams,
        "events_fired": events_fired,
        "pairwise_velocity_tracker_flagged_any_edge": len(ring_pairs_flagged_individually) > 0,
        "graph_collusion_clusters": clusters,
        "defense_triggered": ring_detected,
        "verdict": (
            "DEFENSE WORKED — graph detector caught the ring even though no single pairwise edge tripped the velocity tracker"
            if ring_detected and not ring_pairs_flagged_individually
            else "DEFENSE WORKED — graph detector caught the ring" if ring_detected
            else "DEFENSE FAILED — ring was not detected"
        ),
    }


@router.post("/simulate/reset")
async def reset_simulation_state():
    """Clear simulator-created devices/adjacency/velocity state for a clean re-run."""
    from services.corroboration_service import reset_velocity_tracker

    all_sim_ids = [_SIM_CAMERA_IDS["solo"], *_SIM_CAMERA_IDS["ring"]]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        placeholders = ",".join("?" * len(all_sim_ids))
        await db.execute(f"DELETE FROM devices WHERE id IN ({placeholders})", all_sim_ids)
        await db.execute(f"DELETE FROM camera_adjacency WHERE camera_id IN ({placeholders}) OR nearby_camera_id IN ({placeholders})", all_sim_ids + all_sim_ids)
        await db.execute(f"DELETE FROM alerts WHERE camera_id IN ({placeholders})", all_sim_ids)
        await db.commit()
    reset_velocity_tracker()
    _seen_idempotency_keys.clear()
    for cid in all_sim_ids:
        _camera_request_timestamps.pop(cid, None)
    return {"status": "reset", "cleared_cameras": all_sim_ids}
