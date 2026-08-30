"""
audit_router.py
================
Module E (IIT-B BTP) — Audit Ledger REST API
Literature: BIoT Trust Assessment SLR (MDPI Applied Sciences, 2026)

Exposes the persistent Merkle hash-chain audit ledger over a REST API,
making every trust decision a queryable, forensically verifiable artifact.

Endpoints
---------
GET /api/audit/ledger            — paginated audit chain (newest first)
GET /api/audit/verify            — integrity verification report
GET /api/audit/ledger/{alert_id} — lookup entry by alert_id
GET /api/audit/stats             — chain statistics
GET /api/audit/chain-proof       — immutable chain proof for a specific alert
GET /api/audit/anchor            — current head hash for external anchoring
GET /api/audit/velocity          — suspicious corroboration velocity alerts
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from services.audit_ledger import (
    get_ledger,
    get_ledger_entry_by_alert_id,
    get_ledger_stats,
    generate_chain_proof,
    verify_ledger_integrity_report,
)
from services.corroboration_service import get_velocity_alerts

router = APIRouter()


@router.get("/audit/ledger")
async def get_audit_ledger(
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Return the audit ledger chain (newest first, paginated).

    Each entry contains:
    - sequence_id: monotonic ledger index
    - previous_hash: SHA-256 of the prior entry
    - hash: SHA-256 of this entry
    - payload: {alert_id, camera_id, trust_score, action_tier, factors,
                probabilistic_score, decayed_score, max_cvss, timestamp}

    Used by the frontend AnalyticsPanel "Audit Chain" tab.
    """
    entries = get_ledger(limit=limit, offset=offset)
    stats = get_ledger_stats()
    return {
        "entries": entries,
        "count": len(entries),
        "chain_length": stats["chain_length"],
        "head_hash": stats["head_hash"],
    }


@router.get("/audit/verify")
async def verify_audit_integrity():
    """
    Run cryptographic integrity verification over the full hash chain.
    """
    result = verify_ledger_integrity_report()
    return result


@router.get("/audit/stats")
async def get_audit_stats():
    """
    Return audit chain summary statistics for the dashboard.
    """
    stats = get_ledger_stats()
    report = verify_ledger_integrity_report()
    return {
        **stats,
        "chain_valid": report["valid"],
        "integrity_message": report["message"],
    }


@router.get("/audit/chain-proof")
async def get_chain_proof(
    alert_id: str = Query(..., description="Alert ID to generate cryptographic proof for")
):
    """
    Generate an immutable cryptographic chain proof for an alert (BIoT SLR 2026).
    """
    proof = generate_chain_proof(alert_id)
    if proof is None:
        raise HTTPException(
            status_code=404,
            detail=f"Alert '{alert_id}' not found in audit ledger chain.",
        )
    return proof


@router.get("/audit/anchor")
async def get_audit_anchor():
    """
    External Anchoring Endpoint — head hash for cross-operator tamper detection.

    Returns the current audit chain head hash with a timestamp. Publishing this
    value to any external channel (GitHub Gist, public Slack, pastebin, etc.)
    creates a cross-operator witness: an adversary who rewrites the SQLite DB
    cannot retroactively change the published hash without detection.

    Security model:
      - Without external anchoring: tamper-evident against external parties, but
        NOT against the system operator who controls the DB.
      - With external anchoring: tamper-evident against ALL parties including
        the operator, because the pre-rewrite hash is publicly on record.

    Recommended anchoring workflow (no blockchain needed):
      1. Call GET /api/audit/anchor to get the current head_hash.
      2. POST it to a public GitHub Gist or append to a public log.
      3. Any future integrity challenge can compare against the published record.

    This upgrades the ledger from "operator-witnessed" to "externally-anchored"
    tamper detection, as recommended by Zhang et al. (IoT Botnet Forensics, 2020).
    """
    stats = get_ledger_stats()
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "head_hash": stats["head_hash"],
        "chain_length": stats["chain_length"],
        "anchored_at": now_iso,
        "anchor_instructions": (
            "Publish head_hash + anchored_at to any public channel to create "
            "a cross-operator tamper-evident record. "
            "Suggested: GitHub Gist, public Slack webhook, or append to a public log."
        ),
        "security_model": (
            "Without publication: tamper-evident against external parties only. "
            "With publication: tamper-evident against all parties including the operator."
        ),
    }


@router.get("/audit/velocity")
async def get_corroboration_velocity():
    """
    Corroboration Velocity Alerts — suspicious camera pair detection.

    Returns all camera pairs that have corroborated each other more than
    VELOCITY_THRESHOLD times in the rolling VELOCITY_WINDOW_MINUTES window.

    This implements the Red Team v2 residual risk mitigation documented in
    red_team_findings.md (Attack 1: Spoofed Corroboration):
      - If an attacker seeds fake camera_adjacency rows and spams detection events
        from those cameras, the pair counter spikes above VELOCITY_THRESHOLD.
      - Operators can review flagged pairs and inspect their adjacency records.

    An empty list means no suspicious velocity patterns are currently active.
    """
    alerts = get_velocity_alerts()
    return {
        "velocity_alerts": alerts,
        "flagged_pairs": len(alerts),
        "status": "suspicious_activity_detected" if alerts else "clean",
    }


@router.get("/audit/ledger/{alert_id}")
async def get_audit_entry_for_alert(alert_id: str):
    """
    Lookup the Merkle chain entry for a specific alert_id.
    Returns the entry with its hash, previous_hash, and full payload.
    404 if alert_id not found in the chain.
    """
    entry = get_ledger_entry_by_alert_id(alert_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Alert '{alert_id}' not found in audit ledger chain.",
        )
    return entry
