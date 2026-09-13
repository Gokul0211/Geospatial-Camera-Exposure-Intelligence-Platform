from fastapi import APIRouter, HTTPException
from services.news_service import fetch_and_cache_news
from config import CITIES

router = APIRouter()


@router.get("/news")
async def get_news(city: str = "Mumbai"):
    if city not in CITIES:
        raise HTTPException(
            status_code=400,
            detail=f"City '{city}' not supported. Available: {list(CITIES.keys())}"
        )
    articles = await fetch_and_cache_news(city)
    return {"articles": articles, "total": len(articles)}
