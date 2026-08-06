"""
corroboration_service.py
========================
Phase 2 — Camera adjacency + recent-alert corroboration check.

Design decisions (documented for Phase 4 / report)
----------------------------------------------------
1. Adjacency is manually curated, stored in `camera_adjacency` (populated by
   `scripts/seed_camera_adjacency.py`). It is NOT auto-computed from lat/lon —
   manual curation avoids false positives from cameras on opposite sides of a
   wall sharing GPS coordinates.

2. Corroboration window: configurable via CORROBORATION_WINDOW_MINUTES (default
   15 minutes). An alert from a nearby camera within this window, for the SAME
   event_type, counts as corroboration. Rationale: different event types (e.g.
   "loitering" vs "perimeter_breach") should NOT corroborate each other because
   they represent distinct threat signals.

3. The function returns the list of camera_ids that corroborate, not just a
   count — so the `alerts.corroborated_by` JSON column stores the actual IDs
   for traceability/audit.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import aiosqlite
from config import DATABASE_PATH

# Default corroboration window — alert from adjacent camera within this window
# for the same event_type counts as corroboration.
CORROBORATION_WINDOW_MINUTES: int = 15


async def get_nearby_cameras(camera_id: str) -> list[str]:
    """
    Return a list of camera_id strings that are registered as adjacent to
    `camera_id` in the `camera_adjacency` table.

    Returns empty list if no adjacency rows exist (new cameras, unseeded data).
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT nearby_camera_id FROM camera_adjacency WHERE camera_id = ?",
            (camera_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def check_corroboration(
    camera_id: str,
    event_type: str,
    window_minutes: int = CORROBORATION_WINDOW_MINUTES,
) -> list[str]:
    """
    Check whether any cameras adjacent to `camera_id` have recently triggered
    an alert of the same `event_type`.

    Parameters
    ----------
    camera_id : str
        The device ID of the camera that just fired an event.
    event_type : str
        The event type to match (e.g. "loitering", "perimeter_breach").
        Only alerts with the SAME event_type count as corroboration.
    window_minutes : int
        How far back to look in the `alerts` table. Default: 15 minutes.

    Returns
    -------
    list[str]
        Camera IDs of adjacent cameras that have a recent matching alert.
        Empty list = no corroboration.
    """
    nearby = await get_nearby_cameras(camera_id)
    if not nearby:
        return []

    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    ).isoformat()

    # Build a parameterised IN clause for the nearby camera IDs
    placeholders = ",".join("?" * len(nearby))
    query = f"""
        SELECT DISTINCT camera_id
          FROM alerts
         WHERE camera_id IN ({placeholders})
           AND event_type = ?
           AND detected_at >= ?
    """
    params = (*nearby, event_type, cutoff)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    return [row[0] for row in rows]


async def add_adjacency(camera_id: str, nearby_camera_id: str) -> None:
    """
    Insert a bidirectional adjacency relationship between two cameras.
    Safe to call multiple times (INSERT OR IGNORE).

    Both directions are inserted so either camera can find the other via
    `get_nearby_cameras`.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO camera_adjacency (camera_id, nearby_camera_id) "
            "VALUES (?, ?)",
            (camera_id, nearby_camera_id),
        )
        await db.execute(
            "INSERT OR IGNORE INTO camera_adjacency (camera_id, nearby_camera_id) "
            "VALUES (?, ?)",
            (nearby_camera_id, camera_id),
        )
        await db.commit()
