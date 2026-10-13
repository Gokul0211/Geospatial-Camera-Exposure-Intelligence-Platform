"""
scenarios_router.py
===================
POST /api/scenarios/run starts a short, clearly-labelled demo scenario: a handful of synthetic
detection events fired at random stored cameras through the REAL `receive_detection_event()`
pipeline (scoring, ledger, WebSocket broadcast), in the style of scripts/simulate_live_alerts.py.

Every alert it produces carries `"demo": true` (see routes.alerts.DEMO_MODE), so a client can
label it as synthetic. It is not part of the evaluation and is never mixed into results.md.
"""
from __future__ import annotations

import asyncio
import random
import uuid

import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import DATABASE_PATH
from routes.alerts import DEMO_MODE, DetectionEvent, receive_detection_event

router = APIRouter()

EVENT_TYPES = ["loitering", "perimeter_breach", "unauthorized_access", "anomalous_motion"]
SCENARIO_EVENTS = 12
EVENT_INTERVAL_S = 2.0
_task: asyncio.Task | None = None


class ScenarioRequest(BaseModel):
    scenario: str = "default"


async def _run(camera_ids: list[str]) -> None:
    DEMO_MODE.set(True)  # task-local: only this scenario's alerts are flagged
    for _ in range(SCENARIO_EVENTS):
        event = DetectionEvent(
            camera_id=random.choice(camera_ids),
            event_type=random.choice(EVENT_TYPES),
            confidence=round(random.uniform(0.75, 0.99), 2),
            idempotency_key=str(uuid.uuid4()),
        )
        try:
            await receive_detection_event(event=event, _auth=None)
        except HTTPException:
            pass  # e.g. the per-camera rate limit: skip that event
        await asyncio.sleep(EVENT_INTERVAL_S)


@router.post("/scenarios/run")
async def run_scenario(req: ScenarioRequest):
    global _task
    if req.scenario != "default":
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{req.scenario}'. Available: ['default'].")
    if _task is not None and not _task.done():
        raise HTTPException(status_code=409, detail="A scenario is already running.")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id FROM devices WHERE id NOT LIKE 'SIM_%' LIMIT 100") as cur:
            camera_ids = [row[0] for row in await cur.fetchall()]
    if not camera_ids:
        raise HTTPException(status_code=409, detail="No devices in the database yet. Load a city first.")

    _task = asyncio.create_task(_run(camera_ids))
    return {
        "scenario": req.scenario,
        "events": SCENARIO_EVENTS,
        "interval_seconds": EVENT_INTERVAL_S,
        "demo": True,
        "message": "Synthetic demo events started; alerts arrive over the WebSocket and are flagged demo.",
    }
