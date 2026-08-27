"""
Simulate live detection events for demo purposes.
Posts alerts directly to http://localhost:8000/api/detection-event.
"""
import httpx
import time
import random
import asyncio
import aiosqlite
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from config import DATABASE_PATH, DETECTION_API_KEY

EVENT_TYPES = ["loitering", "perimeter_breach", "unauthorized_access", "anomalous_motion"]

async def main():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id, city FROM devices LIMIT 100") as cursor:
            devices = await cursor.fetchall()

    if not devices:
        print("No devices found in DB. Run seed_demo_data.py first.")
        return

    print(f"Loaded {len(devices)} cameras. Sending live detection events to http://localhost:8000...")
    headers = {"X-API-Key": DETECTION_API_KEY} if DETECTION_API_KEY else {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            dev_id, city = random.choice(devices)
            event_type = random.choice(EVENT_TYPES)
            payload = {
                "camera_id": dev_id,
                "event_type": event_type,
                "confidence": round(random.uniform(0.75, 0.99), 2),
                "metadata": {"simulated": True}
            }
            try:
                res = await client.post("http://localhost:8000/api/detection-event", json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    print(f"  [ALERT SENT] {city} ({dev_id[:8]}) -> {event_type} | Trust Score: {data['trust_score']} ({data['action_tier']})")
                else:
                    print(f"  [HTTP {res.status_code}] {res.text}")
            except Exception as e:
                print(f"  [CONN ERROR] {e}")

            await asyncio.sleep(4)

if __name__ == "__main__":
    asyncio.run(main())
