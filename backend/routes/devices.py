from fastapi import APIRouter, HTTPException
from services.shodan_service import fetch_and_cache_city, devices_to_geojson
from config import CITIES

router = APIRouter()


@router.get("/devices")
async def get_devices(city: str = "Mumbai"):
    if city not in CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' not supported. Available: {list(CITIES.keys())}"
        )
    devices = await fetch_and_cache_city(city)
    return devices_to_geojson(devices)
