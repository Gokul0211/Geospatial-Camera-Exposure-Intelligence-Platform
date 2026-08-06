from pydantic import BaseModel
from typing import Optional


class NewsArticle(BaseModel):
    id: str
    city: str
    title: str
    source: Optional[str] = None
    published_at: Optional[str] = None
    url: str
    description: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    geo_confidence: Optional[str] = None  # city-level | keyword-matched | manually_verified
