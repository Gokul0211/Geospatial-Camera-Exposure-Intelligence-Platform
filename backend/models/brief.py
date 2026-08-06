from pydantic import BaseModel
from typing import List, Dict, Optional


class BriefRequest(BaseModel):
    cluster_id: str
    city: str
    device_count: int
    device_types: List[str]
    manufacturers: List[str]
    owner_types: Dict[str, int]
    nearby_news_headlines: List[str] = []
    area_description: str


class BriefResponse(BaseModel):
    cluster_id: str
    brief_text: str
    risk_level: str   # LOW | MEDIUM | HIGH | CRITICAL
