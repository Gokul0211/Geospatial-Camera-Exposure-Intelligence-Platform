"""
audit_router.py
================
Module E (IIT-B BTP) — Audit Ledger REST API
Literature: BIoT Trust Assessment SLR (MDPI Applied Sciences, 2026)

Exposes the persistent Merkle hash-chain audit ledger over a REST API,
making every trust decision a queryable, forensically verifiable artifact.

Endpoints
---------
GET /api/audit/ledger          — paginated audit chain (newest first)
GET /api/audit/verify          — integrity verification report
GET /api/audit/ledger/{alert_id} — lookup entry by alert_id
GET /api/audit/stats           — chain statistics
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from services.audit_ledger import (
    get_ledger,
    get_ledger_entry_by_alert_id,
    get_ledger_stats,
    generate_chain_proof,
    verify_ledger_integrity,
    verify_ledger_integrity_report,
)

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


@router.get("/audit/ledger/{alert_id}")
async def get_audit_entry_for_alert(alert_id: str):
    """
    Lookup the Merkle chain entry for a specific alert_id.
    Returns the entry with its hash, previous_hash, and full payload.
    404 if alert_id not found in the chain (was processed before server restart
    and DB persistence wasn't loaded, or alert doesn't exist).
    """
    entry = get_ledger_entry_by_alert_id(alert_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Alert '{alert_id}' not found in audit ledger chain.",
        )
    return entry


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
async def get_chain_proof(alert_id: str = Query(..., description="Alert ID to generate cryptographic proof for")):
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

