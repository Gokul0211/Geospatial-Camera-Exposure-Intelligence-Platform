from pydantic import BaseModel
from typing import Optional, List


class Device(BaseModel):
    id: str
    city: str
    ip: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    device_type: Optional[str] = None
    manufacturer: Optional[str] = None
    ports: Optional[List[int]] = None
    owner_org: Optional[str] = None
    owner_type: Optional[str] = None       # government | corporate | telecom | unknown
    ownership_confidence: Optional[str] = None  # high | medium | low
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    banner_snippet: Optional[str] = None
