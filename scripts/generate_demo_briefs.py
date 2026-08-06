"""
Pre-generate risk briefs from real cluster data and store in SQLite cache.
Usage: python scripts/generate_demo_briefs.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
from services.claude_service import generate_brief
from database import init_db

DEMO_CLUSTERS = [
    {
        "cluster_id": "demo_cluster_dharavi",
        "city": "Mumbai",
        "device_count": 18,
        "device_types": ["IP Camera", "DVR/NVR", "RTSP Stream"],
        "manufacturers": ["Hikvision", "Dahua"],
        "owner_types": {"government": 8, "telecom": 7, "corporate": 2, "unknown": 1},
        "nearby_news_headlines": [
            "Mumbai Police to expand CCTV surveillance network across key localities",
            "1,500 new cameras planned for Dharavi redevelopment zone",
        ],
        "area_description": "Dharavi, Central Mumbai"
    },
    {
        "cluster_id": "demo_cluster_cst",
        "city": "Mumbai",
        "device_count": 31,
        "device_types": ["IP Camera", "Network Device", "RTSP Stream"],
        "manufacturers": ["Hikvision", "Samsung", "Axis"],
        "owner_types": {"government": 12, "telecom": 15, "corporate": 4, "unknown": 0},
        "nearby_news_headlines": [
            "Mumbai railway stations get AI-powered surveillance upgrade",
            "Face recognition cameras deployed at CST, Dadar stations",
        ],
        "area_description": "CST / Fort Area, South Mumbai"
    },
    {
        "cluster_id": "demo_cluster_bandra",
        "city": "Mumbai",
        "device_count": 14,
        "device_types": ["IP Camera", "DVR/NVR"],
        "manufacturers": ["Dahua", "Uniview", "Unknown"],
        "owner_types": {"government": 3, "telecom": 4, "corporate": 5, "unknown": 2},
        "nearby_news_headlines": [
            "Bandra-Kurla Complex surveillance expanded under Smart City project",
        ],
        "area_description": "Bandra West, Mumbai"
    },
    {
        "cluster_id": "demo_cluster_connaught",
        "city": "Delhi",
        "device_count": 22,
        "device_types": ["IP Camera", "DVR/NVR", "RTSP Stream", "Network Device"],
        "manufacturers": ["Hikvision", "Dahua", "Bosch"],
        "owner_types": {"government": 10, "telecom": 6, "corporate": 4, "unknown": 2},
        "nearby_news_headlines": [
            "Delhi gets 1.4 lakh CCTV cameras under Smart City project",
            "Facial recognition deployed at New Delhi railway station",
        ],
        "area_description": "Connaught Place, Central Delhi"
    },
    {
        "cluster_id": "demo_cluster_mgroad",
        "city": "Bangalore",
        "device_count": 16,
        "device_types": ["IP Camera", "DVR/NVR", "Network Device"],
        "manufacturers": ["Hikvision", "Axis", "Honeywell"],
        "owner_types": {"government": 6, "telecom": 4, "corporate": 5, "unknown": 1},
        "nearby_news_headlines": [
            "Bengaluru smart city project adds 7,000 AI surveillance cameras",
            "BBMP installs ANPR cameras on MG Road and Brigade Road",
        ],
        "area_description": "MG Road / Brigade Road, Central Bangalore"
    },
]


async def main():
    await init_db()
    print("=" * 60)
    print("Generating demo risk briefs...")
    print("=" * 60)

    success = 0
    for cluster in DEMO_CLUSTERS:
        print(f"\nGenerating brief for: {cluster['cluster_id']}")
        print(f"  Location: {cluster['area_description']}")
        try:
            result = await generate_brief(cluster)
            print(f"  Risk level: {result['risk_level']}")
            print(f"  Cached: {result.get('from_cache', False)}")
            print(f"  Preview: {result['brief_text'][:120]}...")
            success += 1
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Done. {success}/{len(DEMO_CLUSTERS)} briefs generated.")
    print("=" * 60)


asyncio.run(main())
