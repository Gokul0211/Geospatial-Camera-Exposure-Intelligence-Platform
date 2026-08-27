"""
analytics_router.py
====================
Module G (IIT-B BTP) — Analytics Dashboard REST API
Literature: All 5 research clusters synthesized

Powers the new AnalyticsPanel frontend component with:
- Trust score distribution across recent alerts
- Hourly alert frequency timeline (last 24h)
- Scoring model comparison (WA vs Probabilistic vs Decayed)
- System health summary

Endpoints
---------
GET /api/analytics/trust-distribution   — trust tier bucket counts
GET /api/analytics/alert-timeline       — hourly alert counts for last 24h
GET /api/analytics/score-comparison     — average WA vs Probabilistic vs Decayed
GET /api/analytics/summary              — system overview for dashboard banner
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiosqlite
from fastapi import APIRouter, Query

from config import DATABASE_PATH

router = APIRouter()


@router.get("/analytics/trust-distribution")
async def get_trust_distribution(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (default 24h)"),
    city: str | None = Query(None, description="Filter by city"),
):
    """
    Trust score distribution across recent alerts.

    Returns bucket counts for trust tiers (for histogram visualization):
    - critical_low  (0–20): highest risk
    - low           (21–49): low trust
    - medium        (50–79): medium trust
    - high          (80–100): high trust (verified genuine)

    Also returns the distribution of action_tiers and average trust scores.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        if city:
            query = """
                SELECT trust_score, action_tier, probabilistic_score, decayed_score
                  FROM alerts
                 WHERE detected_at >= ? AND city = ?
            """
            params = (cutoff, city)
        else:
            query = """
                SELECT trust_score, action_tier, probabilistic_score, decayed_score
                  FROM alerts
                 WHERE detected_at >= ?
            """
            params = (cutoff,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        return {
            "total_alerts": 0,
            "hours_window": hours,
            "buckets": {"critical_low": 0, "low": 0, "medium": 0, "high": 0},
            "tiers": {"high_trust": 0, "medium_trust": 0, "low_trust": 0},
            "averages": {"wa": None, "probabilistic": None, "decayed": None},
        }

    buckets = {"critical_low": 0, "low": 0, "medium": 0, "high": 0}
    tiers = {"high_trust": 0, "medium_trust": 0, "low_trust": 0}
    wa_scores, prob_scores, decayed_scores = [], [], []

    for row in rows:
        score = row["trust_score"] or 0
        if score <= 20:
            buckets["critical_low"] += 1
        elif score <= 49:
            buckets["low"] += 1
        elif score <= 79:
            buckets["medium"] += 1
        else:
            buckets["high"] += 1

        tier = row["action_tier"] or "low_trust"
        if tier in tiers:
            tiers[tier] += 1

        wa_scores.append(score)
        if row["probabilistic_score"] is not None:
            prob_scores.append(row["probabilistic_score"])
        if row["decayed_score"] is not None:
            decayed_scores.append(row["decayed_score"])

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    return {
        "total_alerts": len(rows),
        "hours_window": hours,
        "city": city,
        "buckets": buckets,
        "tiers": tiers,
        "averages": {
            "wa": avg(wa_scores),
            "probabilistic": avg(prob_scores),
            "decayed": avg(decayed_scores),
        },
    }


@router.get("/analytics/alert-timeline")
async def get_alert_timeline(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    city: str | None = Query(None),
):
    """
    Hourly alert frequency timeline for the last N hours.

    Returns a list of {hour, count, high_trust, medium_trust, low_trust} buckets
    for the AnalyticsPanel "Threats" tab time-series chart.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        if city:
            query = """
                SELECT detected_at, action_tier
                  FROM alerts
                 WHERE detected_at >= ? AND city = ?
                 ORDER BY detected_at ASC
            """
            params = (cutoff.isoformat(), city)
        else:
            query = """
                SELECT detected_at, action_tier
                  FROM alerts
                 WHERE detected_at >= ?
                 ORDER BY detected_at ASC
            """
            params = (cutoff.isoformat(),)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    # Build hourly buckets
    timeline: dict[str, dict] = {}
    for i in range(hours):
        bucket_time = cutoff + timedelta(hours=i)
        bucket_label = bucket_time.strftime("%H:%M")
        timeline[bucket_label] = {
            "hour": bucket_label,
            "count": 0,
            "high_trust": 0,
            "medium_trust": 0,
            "low_trust": 0,
        }

    for row in rows:
        try:
            detected = datetime.fromisoformat(
                str(row["detected_at"]).replace("Z", "+00:00")
            )
            if detected.tzinfo is None:
                detected = detected.replace(tzinfo=timezone.utc)
            # Round down to the nearest hour
            bucket_dt = detected.replace(minute=0, second=0, microsecond=0)
            # Find offset from cutoff
            delta_hours = int((bucket_dt - cutoff.replace(minute=0, second=0, microsecond=0)).total_seconds() / 3600)
            if 0 <= delta_hours < hours:
                bucket_label = (cutoff + timedelta(hours=delta_hours)).strftime("%H:%M")
                if bucket_label in timeline:
                    timeline[bucket_label]["count"] += 1
                    tier = row["action_tier"] or "low_trust"
                    if tier in ("high_trust", "medium_trust", "low_trust"):
                        timeline[bucket_label][tier] += 1
        except (ValueError, TypeError, AttributeError):
            continue

    return {
        "hours_window": hours,
        "city": city,
        "total_alerts": len(rows),
        "timeline": list(timeline.values()),
    }


@router.get("/analytics/score-comparison")
async def get_score_comparison(
    city: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Per-alert comparison of WA, Probabilistic, and Decayed trust scores.
    Returns the last `limit` alerts with all three score columns side-by-side.
    Enables the academic dual-model analysis described in the BTP report.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        if city:
            query = """
                SELECT id, camera_id, event_type, detected_at, action_tier,
                       trust_score, probabilistic_score, decayed_score
                  FROM alerts
                 WHERE city = ?
                 ORDER BY detected_at DESC
                 LIMIT ?
            """
            params = (city, limit)
        else:
            query = """
                SELECT id, camera_id, event_type, detected_at, action_tier,
                       trust_score, probabilistic_score, decayed_score
                  FROM alerts
                 ORDER BY detected_at DESC
                 LIMIT ?
            """
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    alerts = []
    for row in rows:
        d = dict(row)
        d["wa_vs_prob_delta"] = (
            (d["probabilistic_score"] or 0) - d["trust_score"]
            if d["probabilistic_score"] is not None else None
        )
        d["wa_vs_decayed_delta"] = (
            (d["decayed_score"] or 0) - d["trust_score"]
            if d["decayed_score"] is not None else None
        )
        alerts.append(d)

    return {
        "city": city,
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/analytics/summary")
async def get_analytics_summary(city: str | None = Query(None)):
    """
    High-level system overview for the AnalyticsPanel dashboard banner.
    Returns total devices, total alerts (24h), tier distribution, and integrity status.
    """
    from services.audit_ledger import get_ledger_stats, verify_ledger_integrity_report

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Device count
        if city:
            async with db.execute("SELECT COUNT(*) FROM devices WHERE city = ?", (city,)) as cur:
                device_count = (await cur.fetchone())[0]
            async with db.execute(
                "SELECT action_tier, COUNT(*) as n FROM alerts WHERE detected_at >= ? AND city = ? GROUP BY action_tier",
                (cutoff, city),
            ) as cur:
                tier_rows = await cur.fetchall()
        else:
            async with db.execute("SELECT COUNT(*) FROM devices") as cur:
                device_count = (await cur.fetchone())[0]
            async with db.execute(
                "SELECT action_tier, COUNT(*) as n FROM alerts WHERE detected_at >= ? GROUP BY action_tier",
                (cutoff,),
            ) as cur:
                tier_rows = await cur.fetchall()

    tiers = {"high_trust": 0, "medium_trust": 0, "low_trust": 0}
    for row in tier_rows:
        t = row["action_tier"]
        if t in tiers:
            tiers[t] = row["n"]

    total_alerts_24h = sum(tiers.values())

    ledger_stats = get_ledger_stats()
    integrity = verify_ledger_integrity_report()

    return {
        "city": city or "All",
        "device_count": device_count,
        "total_alerts_24h": total_alerts_24h,
        "alert_tiers_24h": tiers,
        "audit_chain_length": ledger_stats["chain_length"],
        "audit_chain_valid": integrity["valid"],
        "head_hash_preview": ledger_stats["head_hash"][:16] + "..." if ledger_stats["head_hash"] != "0" * 64 else "genesis",
    }
