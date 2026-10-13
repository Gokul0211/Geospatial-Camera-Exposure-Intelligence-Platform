import json

from fastapi import APIRouter, HTTPException
from services.shodan_service import fetch_and_cache_city, devices_to_geojson
from services.trust_score_service import compute_ig_dctf_trust_score
from config import CITIES

router = APIRouter()


def _json_list(value) -> list:
    """Parse a JSON-encoded list column; tolerate NULL, lists and malformed text."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _enrich_with_posture(devices: list, geojson: dict) -> dict:
    """
    Attach a static-posture IG-DCTF score to every GeoJSON feature so a map can colour
    devices without one request per camera.

    The score uses only data already stored for the device (authentication, CVEs, owner,
    patch age, last stored banner drift) and assumes no corroboration, because corroboration
    depends on live alerts. `trust_score_basis` says so; the per-device endpoint
    `/api/devices/{id}/trust-score` remains the authoritative on-demand score.
    """
    by_id = {d.get("id"): d for d in devices}
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        device = by_id.get(props.get("id"))
        if device is None:
            continue
        cve_ids = _json_list(device.get("cve_ids"))
        try:
            result = compute_ig_dctf_trust_score(
                device=device,
                corroborating_cameras=[],
                drift_score=float(device.get("last_drift_score") or 0.0),
                cve_categories=_json_list(device.get("cve_categories")) or None,
            )
            props["trust_score"] = result["final_trust_score"]
            props["action_tier"] = result["tier"]
            props["integrity_gate_tripped"] = bool(result["gate_tripped"])
            props["trust_score_basis"] = "static_posture_no_corroboration"
        except Exception:
            # A malformed row must not take the whole device list down.
            pass
        props["city"] = device.get("city")
        props["cves"] = cve_ids
        props["firmware_version"] = device.get("firmware_version")
    return geojson


@router.get("/devices")
async def get_devices(city: str = "Mumbai"):
    if city not in CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' not supported. Available: {list(CITIES.keys())}"
        )
    devices = await fetch_and_cache_city(city)
    return _enrich_with_posture(devices, devices_to_geojson(devices))
