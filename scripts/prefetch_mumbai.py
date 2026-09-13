"""
Run this BEFORE the hackathon starts to warm the SQLite cache.
Usage: python scripts/prefetch_mumbai.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
from services.shodan_service import fetch_and_cache_city
from services.news_service import fetch_and_cache_news

async def main():
    print("=" * 50)
    print("Prefetching Mumbai data...")
    print("=" * 50)
    devices = await fetch_and_cache_city("Mumbai")
    print(f"  → {len(devices)} devices cached")
    print("Fetching Mumbai news...")
    news = await fetch_and_cache_news("Mumbai")
    print(f"  → {len(news)} articles cached")
    print("Done. Mumbai data cached.")

asyncio.run(main())
