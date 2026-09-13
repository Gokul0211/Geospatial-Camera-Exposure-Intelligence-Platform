"""
Run this BEFORE the hackathon starts to warm the SQLite cache.
Usage: python scripts/prefetch_bangalore.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
from services.shodan_service import fetch_and_cache_city
from services.news_service import fetch_and_cache_news

async def main():
    print("=" * 50)
    print("Prefetching Bangalore data...")
    print("=" * 50)
    devices = await fetch_and_cache_city("Bangalore")
    print(f"  → {len(devices)} devices cached")
    print("Fetching Bangalore news...")
    news = await fetch_and_cache_news("Bangalore")
    print(f"  → {len(news)} articles cached")
    print("Done. Bangalore data cached.")

asyncio.run(main())
