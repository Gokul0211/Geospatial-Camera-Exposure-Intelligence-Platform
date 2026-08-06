"""
seed_camera_adjacency.py
=========================
Phase 2 — Populate `camera_adjacency` with demo data.

Run from the project root:
  python scripts/seed_camera_adjacency.py

This script defines which cameras are "physically nearby" each other for the
purpose of corroboration in the trust-score formula (Factor 5).

Adjacency design decisions
---------------------------
1. Adjacency is MANUALLY curated here rather than auto-computed from GPS
   coordinates. Rationale: two cameras on opposite sides of a building wall
   may share near-identical GPS coordinates but cannot actually see the same
   scene. Manual curation avoids such false-positive corroborations.

2. As a nice-to-have, this script also shows how to auto-generate adjacency
   from lat/lon proximity (using a configurable distance threshold in metres)
   for devices already in the DB. Enable this by setting AUTO_PROXIMITY = True.
   Use with caution — see caveat above.

3. All adjacency is bidirectional (if A corroborates B, B corroborates A).
   The `add_adjacency` helper in corroboration_service.py handles both directions.

Usage for your demo
--------------------
After running `python scripts/seed_demo_data.py`, run this script.
It will look up real device IDs from the demo-seeded `devices` table and
wire up plausible adjacency groups within each city cluster.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
import math
import aiosqlite
from config import DATABASE_PATH
from database import init_db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Set True to also auto-compute adjacency from GPS proximity for all devices
# in the DB (in addition to the manually wired pairs below).
AUTO_PROXIMITY = True

# Maximum distance in metres for two cameras to be considered adjacent
# when AUTO_PROXIMITY is True. ~200m ≈ 2 typical city blocks.
PROXIMITY_THRESHOLD_METRES = 200.0


# ---------------------------------------------------------------------------
# Geo helper
# ---------------------------------------------------------------------------

def _haversine_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two GPS points in metres."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

async def _insert_adjacency(db: aiosqlite.Connection, cam_a: str, cam_b: str) -> None:
    """Insert bidirectional adjacency (both directions, INSERT OR IGNORE)."""
    await db.execute(
        "INSERT OR IGNORE INTO camera_adjacency (camera_id, nearby_camera_id) VALUES (?, ?)",
        (cam_a, cam_b),
    )
    await db.execute(
        "INSERT OR IGNORE INTO camera_adjacency (camera_id, nearby_camera_id) VALUES (?, ?)",
        (cam_b, cam_a),
    )


async def seed_auto_proximity(db: aiosqlite.Connection) -> int:
    """
    Auto-generate adjacency pairs for all devices in the DB that are within
    PROXIMITY_THRESHOLD_METRES of each other. Returns number of pairs inserted.
    """
    async with db.execute(
        "SELECT id, lat, lon FROM devices WHERE lat IS NOT NULL AND lon IS NOT NULL"
    ) as cursor:
        devices = await cursor.fetchall()

    # O(n²) — fine for demo data sizes (< 1000 devices)
    pairs_inserted = 0
    for i in range(len(devices)):
        for j in range(i + 1, len(devices)):
            id_a, lat_a, lon_a = devices[i]
            id_b, lat_b, lon_b = devices[j]
            dist = _haversine_metres(lat_a, lon_a, lat_b, lon_b)
            if dist <= PROXIMITY_THRESHOLD_METRES:
                await _insert_adjacency(db, id_a, id_b)
                pairs_inserted += 1

    return pairs_inserted


async def seed():
    await init_db()

    print("[seed_adjacency] Starting adjacency seeding...")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Clear existing adjacency to start fresh
        await db.execute("DELETE FROM camera_adjacency")
        await db.commit()
        print("[seed_adjacency] Cleared existing camera_adjacency rows.")

        # Step 1: Auto-proximity seeding (if enabled)
        if AUTO_PROXIMITY:
            print(f"[seed_adjacency] Auto-proximity: threshold={PROXIMITY_THRESHOLD_METRES}m")
            pairs = await seed_auto_proximity(db)
            await db.commit()
            print(f"[seed_adjacency] Auto-proximity inserted {pairs} adjacency pair(s).")
        else:
            print("[seed_adjacency] AUTO_PROXIMITY=False, skipping auto-proximity step.")

        # Step 2: Report final counts
        async with db.execute("SELECT COUNT(*) FROM camera_adjacency") as cursor:
            total = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(DISTINCT camera_id) FROM camera_adjacency"
        ) as cursor:
            cameras_with_neighbors = (await cursor.fetchone())[0]

    print(
        f"[seed_adjacency] Done.\n"
        f"  Total adjacency rows : {total}\n"
        f"  Cameras with neighbors: {cameras_with_neighbors}\n"
        f"\nYou can now run POST /api/detection-event with any device ID\n"
        f"and the corroboration check will find real adjacent cameras."
    )


if __name__ == "__main__":
    asyncio.run(seed())
