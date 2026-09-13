"""
cold_start_service.py
======================
Module §5.2 (Secondary Contribution) — Cold-Start Trust Bootstrapping via
Device-Fingerprint Stereotyping.

Literature: general SIoT trust-bootstrapping / "stereotyping" survey work
(arXiv 2202.03624, arXiv 2504.15301) applied here to the camera-OSINT domain
via CVE/firmware-fingerprint clustering — an honest "known technique, new
domain" secondary contribution (see research_work.md §5.2), not a new
mechanism.

Problem
-------
`compute_probabilistic_trust_score()` always starts from a flat, uninformative
prior P(genuine) = 0.50 for every device, including a camera that has never
been scored before and has zero heartbeat/corroboration history. That is the
"cold-start problem" named in the BIoT Trust Assessment SLR (2026) as an
unsolved gap (G3) shared by essentially every fixed-weight IoT trust model.

Approach
--------
Instead of always defaulting to 0.50, look at whether *other* already-scored
devices sharing this device's manufacturer + open-port signature ("digital
twin" cluster) exist. If they do, bootstrap the new device's prior from the
empirical distribution of those devices' historical alert trust scores
instead of a flat neutral guess. If no comparable devices exist either
(true cold start with no stereotype available), fall back to 0.50 — this
function never fabricates confidence it doesn't have.
"""

from __future__ import annotations

import json

import aiosqlite
from config import DATABASE_PATH

# Minimum number of historical alerts from clustered "digital twin" devices
# required before trusting the stereotype over the flat neutral default.
# Below this, the sample is too small to be more informative than 0.50.
MIN_CLUSTER_SAMPLE_SIZE = 3

# Clamp the stereotype prior away from the extremes — a cluster of devices
# that were all high_trust doesn't mean a *brand-new, unverified* device
# should start at 0.95; it should start informed-but-cautious.
PRIOR_FLOOR = 0.20
PRIOR_CEILING = 0.80


async def is_cold_start_device(camera_id: str) -> bool:
    """
    A device is "cold start" if it has never produced a prior alert — this is
    the very first detection event the trust engine has ever seen for it, so
    there is no history of its own to lean on.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM alerts WHERE camera_id = ?", (camera_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return (row[0] if row else 0) == 0


async def _find_stereotype_cluster(device: dict) -> list[dict]:
    """
    Find already-scored "digital twin" devices sharing this device's
    manufacturer and open-port signature, returning their most recent
    trust_score + probabilistic_score from the alerts table.

    Clustering key: manufacturer (exact match) + open port set (Jaccard
    similarity >= 0.5 against the candidate's `ports` JSON column). Port set
    is a reasonable proxy for "same firmware family" per research_work.md
    §4.3's own reasoning (open-port set changes are a fingerprinting signal).
    """
    manufacturer = (device.get("manufacturer") or "").strip()
    if not manufacturer or manufacturer.lower() == "unknown":
        return []

    own_ports: set[int] = set()
    try:
        own_ports = set(json.loads(device.get("ports") or "[]"))
    except (json.JSONDecodeError, TypeError):
        pass

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, ports FROM devices
             WHERE manufacturer = ? AND id != ?
            """,
            (manufacturer, device.get("id", "")),
        ) as cursor:
            candidates = await cursor.fetchall()

    twin_ids: list[str] = []
    for row in candidates:
        try:
            cand_ports = set(json.loads(row["ports"] or "[]"))
        except (json.JSONDecodeError, TypeError):
            cand_ports = set()

        if not own_ports and not cand_ports:
            # Neither side has port data — fall back to manufacturer-only match
            twin_ids.append(row["id"])
            continue
        union = own_ports | cand_ports
        if not union:
            continue
        jaccard = len(own_ports & cand_ports) / len(union)
        if jaccard >= 0.5:
            twin_ids.append(row["id"])

    if not twin_ids:
        return []

    placeholders = ",".join("?" * len(twin_ids))
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""
            SELECT trust_score, probabilistic_score FROM alerts
             WHERE camera_id IN ({placeholders})
             ORDER BY detected_at DESC
             LIMIT 50
            """,
            tuple(twin_ids),
        ) as cursor:
            rows = await cursor.fetchall()

    return [dict(r) for r in rows]


async def compute_stereotype_prior(device: dict) -> dict:
    """
    Compute a cold-start prior P(genuine) for `device` from its digital-twin
    cluster's historical scoring, or fall back to the flat 0.50 default when
    no sufficiently-sized cluster exists.

    Returns
    -------
    dict:
        prior_probability : float  — in [PRIOR_FLOOR, PRIOR_CEILING] if
                                      stereotyped, else exactly 0.50
        method             : "stereotype" | "flat_default"
        cluster_size       : int — number of historical alerts the stereotype
                                    was derived from (0 for flat_default)
    """
    history = await _find_stereotype_cluster(device)

    if len(history) < MIN_CLUSTER_SAMPLE_SIZE:
        return {
            "prior_probability": 0.50,
            "method": "flat_default",
            "cluster_size": len(history),
        }

    # Prefer probabilistic_score (already a 0-100 posterior estimate) where
    # present; fall back to the deterministic trust_score otherwise.
    samples = [
        (h.get("probabilistic_score") if h.get("probabilistic_score") is not None else h["trust_score"])
        for h in history
    ]
    avg_score = sum(samples) / len(samples)
    raw_prior = avg_score / 100.0
    clamped_prior = max(PRIOR_FLOOR, min(PRIOR_CEILING, raw_prior))

    return {
        "prior_probability": round(clamped_prior, 4),
        "method": "stereotype",
        "cluster_size": len(history),
    }
