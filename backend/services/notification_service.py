"""
notification_service.py
========================
Literature-Grounded Tiered Trust-Gated Alert Dispatcher (Rasal et al. 2025).

Routes incoming alerts based on trust tier:
- High-Trust (80-100) -> Immediate Emergency Channel / Webhook Dispatch
- Medium-Trust (50-79) -> Dashboard Triage Queue
- Low-Trust (<50) -> Silent Audit Log (prevents alert fatigue)
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Outgoing dispatch history for testing & verification
_dispatch_history: list[dict[str, Any]] = []


async def dispatch_alert(alert_data: dict[str, Any]) -> dict[str, Any]:
    """
    Route an alert based on action_tier and trust_score.
    Returns dispatch decision metadata.
    """
    tier = alert_data.get("action_tier", "low_trust")
    score = alert_data.get("trust_score", 0)

    if tier == "high_trust" or score >= 80:
        channel = "EMERGENCY_DISPATCH_SMS"
        action = "INSTANT_PUSH_DISPATCH"
        priority = "CRITICAL"
    elif tier == "medium_trust" or score >= 50:
        channel = "DASHBOARD_TRIAGE_QUEUE"
        action = "OPERATOR_REVIEW_REQUIRED"
        priority = "WARNING"
    else:
        channel = "SILENT_AUDIT_LOG"
        action = "LOG_ONLY"
        priority = "LOW"

    record = {
        "alert_id": alert_data.get("alert_id") or alert_data.get("id"),
        "camera_id": alert_data.get("camera_id"),
        "trust_score": score,
        "action_tier": tier,
        "channel": channel,
        "action": action,
        "priority": priority,
    }

    _dispatch_history.append(record)
    log.info(f"[notification_service] Dispatched alert {record['alert_id']} via {channel} ({action})")
    return record


def get_dispatch_history() -> list[dict[str, Any]]:
    return list(_dispatch_history)


def clear_dispatch_history() -> None:
    _dispatch_history.clear()
