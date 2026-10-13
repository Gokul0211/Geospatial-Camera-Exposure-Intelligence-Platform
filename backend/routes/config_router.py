"""
config_router.py
================
Read-only public configuration, so a client never hard-codes thresholds that live in the
scoring code. Values are imported from the scoring modules, not duplicated here.
"""
from fastapi import APIRouter

from services.signal_integrity_service import THETA_HIGH, THETA_LOW

router = APIRouter()

# Tier cut-offs are fixed in trust_score_service (high >= 80, medium >= 50, low < 50).
_TIER_HIGH_MIN = 80
_TIER_MEDIUM_MIN = 50
_GATE_FLOOR_MULTIPLIER = 0.3
_GATE_HARD_CAP = 30


@router.get("/config/thresholds")
async def get_thresholds():
    return {
        "tiers": {"high_min": _TIER_HIGH_MIN, "medium_min": _TIER_MEDIUM_MIN},
        "gate": {
            "theta_low": THETA_LOW,
            "theta_high": THETA_HIGH,
            "floor_multiplier": _GATE_FLOOR_MULTIPLIER,
            "hard_cap": _GATE_HARD_CAP,
        },
    }
