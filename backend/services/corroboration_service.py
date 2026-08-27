"""
corroboration_service.py
========================
Phase 2 — Camera adjacency + recent-alert corroboration check.
Module F (IIT-B BTP) — Feature Embedding Re-ID Upgrade.
Literature: Nayak et al. (iSES, 2019), Liu et al. (arXiv 2503.11088, 2025)

Phase 2 Design decisions (unchanged)
--------------------------------------
1. Adjacency is manually curated in camera_adjacency table.
2. Corroboration window: 15 minutes (configurable via CORROBORATION_WINDOW_MINUTES).
3. Same event_type required for corroboration.
4. Returns camera_id list (not just count) for audit traceability.

Module F BTP Extension
-----------------------
- `check_reid_corroboration()`: if feature embeddings are provided, requires
  cosine similarity >= REID_SIMILARITY_THRESHOLD (0.80) between embeddings.
  Falls back to binary event-type match if no embeddings given.
  This upgrades corroboration from "same event type nearby" to
  "same-person/same-object confirmed by visual appearance matching",
  directly instantiating Nayak et al.'s Re-ID cross-camera identity.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

import aiosqlite
from config import DATABASE_PATH

# Default corroboration window — alert from adjacent camera within this window
# for the same event_type counts as corroboration.
CORROBORATION_WINDOW_MINUTES: int = 15

# Re-ID similarity threshold (Module F / Nayak 2019)
# Cosine similarity must be >= this value for embedding-based corroboration.
REID_SIMILARITY_THRESHOLD: float = 0.80


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


# ---------------------------------------------------------------------------
# Module F — Re-ID Cosine Similarity Corroboration (Nayak et al. 2019)
# ---------------------------------------------------------------------------

def compute_cosine_similarity(
    embedding_a: list[float],
    embedding_b: list[float],
) -> float:
    """
    Compute cosine similarity between two feature embedding vectors.

    cosine_sim(a, b) = dot(a, b) / (||a|| * ||b||)

    Returns a value in [-1.0, 1.0] where 1.0 = identical, 0.0 = orthogonal.
    For visual Re-ID, values >= 0.80 indicate high-confidence same-entity match
    (REID_SIMILARITY_THRESHOLD).

    Parameters
    ----------
    embedding_a, embedding_b : list[float]
        Feature embedding vectors (must be same dimension).

    Returns
    -------
    float : cosine similarity, or 0.0 if vectors are invalid/mismatched.
    """
    if not embedding_a or not embedding_b:
        return 0.0
    if len(embedding_a) != len(embedding_b):
        return 0.0

    dot = sum(a * b for a, b in zip(embedding_a, embedding_b))
    norm_a = math.sqrt(sum(a * a for a in embedding_a))
    norm_b = math.sqrt(sum(b * b for b in embedding_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


async def check_reid_corroboration(
    camera_id: str,
    event_type: str,
    query_embedding: list[float] | None = None,
    window_minutes: int = CORROBORATION_WINDOW_MINUTES,
    similarity_threshold: float = REID_SIMILARITY_THRESHOLD,
) -> dict:
    """
    Module F — Feature Embedding Re-ID corroboration check.

    If query_embedding is provided: requires both event_type match AND
    cosine_similarity >= similarity_threshold between embeddings to count
    as corroboration (same-entity identity confirmation per Nayak 2019).

    If query_embedding is None: falls back to the original binary event-type
    match (check_corroboration) for backward compatibility.

    Parameters
    ----------
    camera_id : str
        Camera that just fired the event.
    event_type : str
        Event type to match in adjacent cameras.
    query_embedding : list[float] | None
        64- or 128-dimensional feature embedding from the detection event.
        None triggers fallback to binary event-type matching.
    window_minutes : int
        How far back to look (default 15 minutes).
    similarity_threshold : float
        Minimum cosine similarity to count as Re-ID corroboration (default 0.80).

    Returns
    -------
    dict: {
        corroborating_cameras: list[str],
        method: "reid_cosine" | "event_type_match",
        best_similarity: float | None,
    }
    """
    if query_embedding is None:
        # Fallback — original binary check
        cameras = await check_corroboration(camera_id, event_type, window_minutes)
        return {
            "corroborating_cameras": cameras,
            "method": "event_type_match",
            "best_similarity": None,
        }

    nearby = await get_nearby_cameras(camera_id)
    if not nearby:
        return {
            "corroborating_cameras": [],
            "method": "reid_cosine",
            "best_similarity": None,
        }

    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    ).isoformat()

    placeholders = ",".join("?" * len(nearby))
    query = f"""
        SELECT camera_id, feature_embedding
          FROM alerts
         WHERE camera_id IN ({placeholders})
           AND event_type = ?
           AND detected_at >= ?
           AND feature_embedding IS NOT NULL
    """
    params = (*nearby, event_type, cutoff)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    confirmed: list[str] = []
    best_sim: float = 0.0

    for row in rows:
        try:
            stored_embedding = json.loads(row["feature_embedding"])
            sim = compute_cosine_similarity(query_embedding, stored_embedding)
            if sim > best_sim:
                best_sim = sim
            if sim >= similarity_threshold:
                cam_id = row["camera_id"]
                if cam_id not in confirmed:
                    confirmed.append(cam_id)
        except (json.JSONDecodeError, TypeError):
            continue

    # If no Re-ID matches found, fall back to binary event-type check
    if not confirmed:
        fallback = await check_corroboration(camera_id, event_type, window_minutes)
        return {
            "corroborating_cameras": fallback,
            "method": "event_type_match_fallback",
            "best_similarity": round(best_sim, 4) if best_sim > 0 else None,
        }

    return {
        "corroborating_cameras": confirmed,
        "method": "reid_cosine",
        "best_similarity": round(best_sim, 4),
    }
