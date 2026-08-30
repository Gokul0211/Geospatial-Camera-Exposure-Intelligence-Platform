"""
notification_service.py
========================
Literature-Grounded Tiered Trust-Gated Alert Dispatcher (Rasal et al. 2025).

Three-tier routing based on trust score / action_tier:
  HIGH-Trust (80–100)   → EMERGENCY_DISPATCH  (instant SMS/webhook + dashboard RED)
  MEDIUM-Trust (50–79)  → TRIAGE_QUEUE        (dashboard AMBER + operator review)
  LOW-Trust  (<50)      → SILENT_AUDIT        (log only — prevents alert fatigue)

Research advantage over Rasal et al.:
  Rasal et al. send SMS on every detection (false-alarm prone).
  COBRA-WATCH gates physical dispatch on trust score.
  This reduces false-alarm dispatch rate — measurable in your evaluation.

Webhook Integration:
  Set COBRA_WATCH_WEBHOOK_URL and COBRA_WATCH_WEBHOOK_SECRET in .env to activate
  real outbound POST dispatch on HIGH-trust alerts.
  Without credentials: logs a stub dispatch record (safe for demo/testing).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

# Outgoing dispatch history — in-memory for testing & runtime inspection
_dispatch_history: list[dict[str, Any]] = []

# Optional webhook integration (configure via environment / .env)
_WEBHOOK_URL: str | None = os.getenv("COBRA_WATCH_WEBHOOK_URL")
_WEBHOOK_SECRET: str | None = os.getenv("COBRA_WATCH_WEBHOOK_SECRET")


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

_TIER_CONFIG: dict[str, dict] = {
    "high_trust": {
        "channel": "EMERGENCY_DISPATCH_SMS",
        "action": "INSTANT_PUSH_DISPATCH",
        "priority": "CRITICAL",
        "color": "#ef4444",       # red
        "rationale": "Trust score ≥ 80. Verified alert. Physical dispatch authorised.",
        "literature": "Rasal et al. (2025) — High-trust alerts trigger immediate field response.",
    },
    "medium_trust": {
        "channel": "DASHBOARD_TRIAGE_QUEUE",
        "action": "OPERATOR_REVIEW_REQUIRED",
        "priority": "WARNING",
        "color": "#f59e0b",       # amber
        "rationale": "Trust score 50–79. Alert requires operator verification before dispatch.",
        "literature": "Swami et al. SCI-IoT (2025) — Grade B threshold for human-in-the-loop.",
    },
    "low_trust": {
        "channel": "SILENT_AUDIT_LOG",
        "action": "LOG_ONLY",
        "priority": "LOW",
        "color": "#64748b",       # muted
        "rationale": "Trust score < 50. High false-alarm risk. Logged for audit only.",
        "literature": "BIoT SLR (2026) — low-trust events preserved for forensic analysis.",
    },
}


# ---------------------------------------------------------------------------
# Webhook delivery (pluggable — stub when no URL configured)
# ---------------------------------------------------------------------------

async def _send_webhook(record: dict[str, Any]) -> bool:
    """
    POST the dispatch record to the configured webhook URL.
    Returns True on success, False on failure or when not configured.
    This stub enables production SMS/push integrations (Twilio, PagerDuty, etc.).
    """
    if not _WEBHOOK_URL:
        log.debug("[notification_service] No webhook URL configured — stub dispatch logged.")
        return False

    try:
        import httpx
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if _WEBHOOK_SECRET:
            headers["X-COBRA-WATCH-Secret"] = _WEBHOOK_SECRET

        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(_WEBHOOK_URL, json=record, headers=headers)
            if res.status_code < 300:
                log.info(f"[notification_service] Webhook delivered → {_WEBHOOK_URL} ({res.status_code})")
                return True
            log.warning(f"[notification_service] Webhook returned {res.status_code}")
            return False
    except Exception as e:
        log.warning(f"[notification_service] Webhook delivery failed (non-fatal): {e}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def dispatch_alert(alert_data: dict[str, Any]) -> dict[str, Any]:
    """
    Route an alert based on action_tier and trust_score.

    Parameters
    ----------
    alert_data : dict
        Must contain at minimum: alert_id, camera_id, trust_score, action_tier.
        Optional: event_type, city, contributing_factors.

    Returns
    -------
    dict — dispatch decision metadata including channel, action, rationale.
    """
    score: int = int(alert_data.get("trust_score", 0))
    tier: str = alert_data.get("action_tier", "")

    # Normalise tier — derive from score if not explicitly set or invalid
    if tier not in _TIER_CONFIG:
        if score >= 80:
            tier = "high_trust"
        elif score >= 50:
            tier = "medium_trust"
        else:
            tier = "low_trust"

    cfg = _TIER_CONFIG[tier]
    timestamp = datetime.now(timezone.utc).isoformat()

    record: dict[str, Any] = {
        "dispatched_at": timestamp,
        "alert_id": alert_data.get("alert_id") or alert_data.get("id"),
        "camera_id": alert_data.get("camera_id"),
        "city": alert_data.get("city"),
        "event_type": alert_data.get("event_type"),
        "trust_score": score,
        "action_tier": tier,
        "channel": cfg["channel"],
        "action": cfg["action"],
        "priority": cfg["priority"],
        "color": cfg["color"],
        "rationale": cfg["rationale"],
        "literature_basis": cfg["literature"],
        "contributing_factors": alert_data.get("contributing_factors", []),
        "webhook_delivered": False,
    }

    # Fire webhook for HIGH-trust alerts only (Rasal et al. 2025 SMS channel)
    if tier == "high_trust":
        record["webhook_delivered"] = await _send_webhook(record)

    _dispatch_history.append(record)
    log.info(
        f"[notification_service] {cfg['action']} → alert={record['alert_id']} "
        f"score={score} tier={tier} channel={cfg['channel']}"
    )
    return record


def get_dispatch_history() -> list[dict[str, Any]]:
    """Return all dispatch records (newest last)."""
    return list(_dispatch_history)


def get_dispatch_stats() -> dict[str, Any]:
    """
    Summary statistics for evaluation — used in false-alarm reduction analysis.
    Computes dispatch rate per tier, which is the primary deployment metric
    distinguishing COBRA-WATCH from Rasal et al. (2025).
    """
    total = len(_dispatch_history)
    by_tier: dict[str, int] = {"high_trust": 0, "medium_trust": 0, "low_trust": 0}
    webhooks_fired = 0

    for r in _dispatch_history:
        t = r.get("action_tier", "low_trust")
        by_tier[t] = by_tier.get(t, 0) + 1
        if r.get("webhook_delivered"):
            webhooks_fired += 1

    return {
        "total_dispatched": total,
        "by_tier": by_tier,
        "webhooks_fired": webhooks_fired,
        "high_trust_rate": round(by_tier["high_trust"] / total, 4) if total else 0.0,
        "false_alarm_suppression_rate": round(
            (by_tier["medium_trust"] + by_tier["low_trust"]) / total, 4
        ) if total else 0.0,
    }


def clear_dispatch_history() -> None:
    """Reset dispatch history (for tests only)."""
    _dispatch_history.clear()

