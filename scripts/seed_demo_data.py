"""
Seed the database with realistic sample data.
Use this ONLY if Shodan API calls fail — this is your demo safety net.
Usage: python scripts/seed_demo_data.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
import aiosqlite
import json
import hashlib
import random
from datetime import datetime, timezone
from config import DATABASE_PATH
from database import init_db

SEED_DATA = {
    "Mumbai": {
        "center": (19.0760, 72.8777),
        "clusters": [
            {"area": "Dharavi", "center": (19.0390, 72.8519), "count": 15,
             "owner_mix": {"government": 6, "telecom": 5, "corporate": 2, "unknown": 2}},
            {"area": "CST/Fort", "center": (18.9400, 72.8350), "count": 22,
             "owner_mix": {"government": 10, "telecom": 8, "corporate": 3, "unknown": 1}},
            {"area": "Bandra West", "center": (19.0544, 72.8402), "count": 12,
             "owner_mix": {"government": 3, "telecom": 4, "corporate": 4, "unknown": 1}},
            {"area": "Andheri", "center": (19.1197, 72.8469), "count": 10,
             "owner_mix": {"government": 2, "telecom": 5, "corporate": 2, "unknown": 1}},
        ]
    },
    "Delhi": {
        "center": (28.6139, 77.2090),
        "clusters": [
            {"area": "Connaught Place", "center": (28.6315, 77.2167), "count": 18,
             "owner_mix": {"government": 9, "telecom": 5, "corporate": 3, "unknown": 1}},
            {"area": "Rohini", "center": (28.7380, 77.0938), "count": 12,
             "owner_mix": {"government": 4, "telecom": 4, "corporate": 2, "unknown": 2}},
            {"area": "Saket", "center": (28.5245, 77.2066), "count": 8,
             "owner_mix": {"government": 2, "telecom": 3, "corporate": 2, "unknown": 1}},
        ]
    },
    "Bangalore": {
        "center": (12.9716, 77.5946),
        "clusters": [
            {"area": "MG Road", "center": (12.9758, 77.6045), "count": 14,
             "owner_mix": {"government": 5, "telecom": 4, "corporate": 4, "unknown": 1}},
            {"area": "Electronic City", "center": (12.8399, 77.6770), "count": 10,
             "owner_mix": {"government": 2, "telecom": 3, "corporate": 4, "unknown": 1}},
        ]
    },
}

MANUFACTURERS = ["Hikvision", "Dahua", "Axis", "Bosch", "Samsung", "Uniview", "Honeywell"]
DEVICE_TYPES = ["IP Camera", "DVR/NVR", "RTSP Stream", "Network Device"]
ORGS = {
    "government": ["Mumbai Municipal Corp", "Delhi Police", "BSNL", "Smart City Mission", "MTNL"],
    "telecom": ["Airtel", "Reliance Jio", "Vodafone Idea", "Tata Communications", "Hathway"],
    "corporate": ["TCS Solutions Pvt Ltd", "Infosys Technologies", "Wipro Systems", "HCL Corp"],
    "unknown": ["Unknown", "APNIC Research", "Private Network"],
}

def is_in_mumbai_water(lat, lon):
    # Rough approximation of Mumbai's coastlines to prevent ocean-cameras
    if lon < 72.822 and lat < 18.98: return True # Back Bay / Arabian Sea (South)
    if lon < 72.830 and lat >= 18.98 and lat < 19.05: return True # Mahim Bay
    if lon < 72.810 and lat >= 19.05: return True # Arabian Sea (Juhu/Versova)
    if lon > 72.855 and lat < 18.96: return True # Eastern Harbor
    if lon > 72.870 and lat >= 18.96 and lat < 19.03: return True # Sewri mudflats
    return False

async def seed():
    await init_db()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for city, city_data in SEED_DATA.items():
            for cluster in city_data["clusters"]:
                for owner_type, count in cluster["owner_mix"].items():
                    for _ in range(count * 10):
                        # RCA Fix: Use Gaussian distribution instead of Uniform Square, and reject points in the ocean
                        for _ in range(15):
                            lat = cluster["center"][0] + random.gauss(0, 0.012)
                            lon = cluster["center"][1] + random.gauss(0, 0.012)
                            if city == "Mumbai" and is_in_mumbai_water(lat, lon):
                                continue
                            break
                        ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
                        did = hashlib.md5(f"{ip}:{city}".encode()).hexdigest()
                        mfr = random.choice(MANUFACTURERS)
                        dt = random.choice(DEVICE_TYPES)
                        org = random.choice(ORGS[owner_type])
                        ports = random.sample([554, 80, 443, 8080, 8443, 37777], k=random.randint(1, 3))

                        await db.execute("""
                            INSERT OR REPLACE INTO devices
                            (id, city, ip, lat, lon, device_type, manufacturer, ports,
                             owner_org, owner_type, ownership_confidence,
                             first_seen, last_seen, banner_snippet, raw_data, fetched_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            did, city, ip, lat, lon, dt, mfr, json.dumps(ports),
                            org, owner_type,
                            "high" if owner_type != "unknown" else "low",
                            "2024-03-01", "2025-05-10",
                            f"Server: {mfr}-WebServer/2.0",
                            json.dumps({"product": mfr, "org": org}),
                            datetime.now(timezone.utc).isoformat()
                        ))

            await db.execute("""
                INSERT OR REPLACE INTO cities (name, lat, lon, zoom_level, last_fetched)
                VALUES (?, ?, ?, ?, ?)
            """, (city, city_data["center"][0], city_data["center"][1], 12, datetime.now(timezone.utc).isoformat()))

        await db.commit()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT city, COUNT(*) FROM devices GROUP BY city") as c:
            rows = await c.fetchall()
            print("Seeded device counts:")
            for row in rows:
                print(f"  {row[0]}: {row[1]} devices")


asyncio.run(seed())
print("Done. Demo data seeded.")
