from fastapi import APIRouter, HTTPException
from services.shodan_service import fetch_and_cache_city
from config import CITIES

router = APIRouter()


@router.get("/heatmap")
async def get_heatmap(city: str = "Mumbai"):
    if city not in CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' not supported. Available: {list(CITIES.keys())}"
        )
    devices = await fetch_and_cache_city(city)
    points = []
    for d in devices:
        lat = d.get("lat")
        lon = d.get("lon")
        if lat and lon:
            device_type = d.get("device_type", "")
            intensity = 1.0
            if device_type in ("IP Camera", "DVR/NVR"):
                intensity = 1.5
            elif device_type == "RTSP Stream":
                intensity = 1.2
            points.append([lat, lon, intensity])
    return {"points": points, "total": len(points)}
