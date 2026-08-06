from fastapi import APIRouter, HTTPException
from services.shodan_service import fetch_and_cache_city
from config import CITIES

router = APIRouter()

CITY_AREAS = {
    "Mumbai": 603,
    "Delhi": 1484,
    "Bangalore": 741,
}


def _calculate_surveillance_score(devices: list, city: str) -> dict | None:
    """Calculate Surveillance Density Index for a city."""
    if not devices:
        return None

    area = CITY_AREAS.get(city, 500)
    total = len(devices)

    owner_counts = {"government": 0, "corporate": 0, "telecom": 0, "unknown": 0}
    for d in devices:
        ot = d.get("owner_type") or "unknown"
        owner_counts[ot] = owner_counts.get(ot, 0) + 1

    devices_per_sq_km = round(total / area, 2)
    govt_pct = round((owner_counts["government"] / total) * 100, 1) if total else 0
    unknown_pct = round((owner_counts["unknown"] / total) * 100, 1) if total else 0

    return {
        "devices_per_sq_km": devices_per_sq_km,
        "govt_percentage": govt_pct,
        "unknown_percentage": unknown_pct,
        "total_area_sq_km": area,
        "label": f"{devices_per_sq_km} devices/km² · {govt_pct}% government · {unknown_pct}% unattributed",
    }


@router.get("/stats")
async def get_stats(city: str = "Mumbai"):
    if city not in CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' not supported. Available: {list(CITIES.keys())}"
        )
    devices = await fetch_and_cache_city(city)

    type_counts = {}
    owner_counts = {"government": 0, "corporate": 0, "telecom": 0, "unknown": 0}
    manufacturer_counts = {}

    for d in devices:
        dt = d.get("device_type") or "Unknown"
        type_counts[dt] = type_counts.get(dt, 0) + 1
        ot = d.get("owner_type") or "unknown"
        owner_counts[ot] = owner_counts.get(ot, 0) + 1
        mfr = d.get("manufacturer") or "Unknown"
        manufacturer_counts[mfr] = manufacturer_counts.get(mfr, 0) + 1

    top_manufacturer = max(manufacturer_counts, key=manufacturer_counts.get, default="Unknown")

    return {
        "city": city,
        "total_devices": len(devices),
        "by_type": type_counts,
        "by_owner": owner_counts,
        "top_manufacturer": top_manufacturer,
        "manufacturer_breakdown": manufacturer_counts,
        "surveillance_score": _calculate_surveillance_score(devices, city),
    }
