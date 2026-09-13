import os
import sqlite3
import shodan
import time
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# Set up Shodan API (Requires environment variable SHODAN_API_KEY)
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "../database.sqlite")

# Target OSINT queries for surveillance infrastructure
QUERIES = [
    "city:{city} port:554",
    "city:{city} product:Hikvision",
    "city:{city} product:Dahua",
    "city:{city} title:\"Network Camera\""
]

CITIES = ["Mumbai", "Delhi", "Bangalore"]

def init_shodan():
    if not SHODAN_API_KEY:
        print("WARNING: SHODAN_API_KEY not found in environment.")
        print("Running in dry-run mode (no API calls will be made).")
        return None
    return shodan.Shodan(SHODAN_API_KEY)

def fetch_devices_for_city(api: shodan.Shodan, city: str) -> List[Dict]:
    results = []
    for query_template in QUERIES:
        query = query_template.format(city=city)
        print(f"[*] Querying Shodan: {query}")
        try:
            # Note: We limit to 1 page (100 results) for hackathon demo purposes
            # to avoid exhausting API credits. In prod, we would paginate.
            result = api.search(query, page=1)
            for match in result.get('matches', []):
                results.append({
                    "ip": match.get('ip_str'),
                    "port": match.get('port'),
                    "org": match.get('org', 'Unknown'),
                    "isp": match.get('isp', 'Unknown'),
                    "lat": match.get('location', {}).get('latitude', 0.0),
                    "lon": match.get('location', {}).get('longitude', 0.0),
                    "product": match.get('product', 'Unknown'),
                    "data": match.get('data', ''),
                    "city": city
                })
            time.sleep(1)  # Respect API rate limits
        except shodan.APIError as e:
            print(f"[!] Shodan API Error: {e}")
    return results

def store_devices(devices: List[Dict]):
    """Insert or update devices in the SQLite database"""
    if not devices:
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists (matches init_db schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            city TEXT,
            lat REAL,
            lon REAL,
            ip TEXT,
            owner_org TEXT,
            owner_type TEXT,
            device_type TEXT,
            manufacturer TEXT,
            is_verified BOOLEAN DEFAULT FALSE,
            ports TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    count = 0
    for d in devices:
        device_id = f"{d['ip']}_{d['port']}"
        
        # Simple heuristic mapping
        owner_type = "corporate"
        if "gov" in d['org'].lower() or "police" in d['org'].lower():
            owner_type = "government"
        elif "telecom" in d['org'].lower() or "airtel" in d['org'].lower() or "jio" in d['org'].lower():
            owner_type = "telecom"
            
        device_type = "IP Camera"
        if "dvr" in str(d['product']).lower() or "nvr" in str(d['product']).lower():
            device_type = "DVR/NVR"
            
        cursor.execute("""
            INSERT INTO devices (id, city, lat, lon, ip, owner_org, owner_type, device_type, manufacturer, ports)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                last_seen = CURRENT_TIMESTAMP,
                owner_org = excluded.owner_org,
                manufacturer = excluded.manufacturer
        """, (
            device_id, d['city'], d['lat'], d['lon'], d['ip'], 
            d['org'], owner_type, device_type, d['product'], str(d['port'])
        ))
        count += 1
        
    conn.commit()
    conn.close()
    print(f"[+] Successfully stored {count} devices in database.")

def main():
    print("========================================")
    print(" SurveillanceWatch Shodan Ingestion Job")
    print("========================================")
    api = init_shodan()
    
    if api:
        for city in CITIES:
            print(f"\n[>] Processing city: {city}")
            devices = fetch_devices_for_city(api, city)
            print(f"[*] Found {len(devices)} unique surveillance assets.")
            store_devices(devices)
    else:
        print("\n[!] Dry run complete. To run live ingestion, set SHODAN_API_KEY.")

if __name__ == "__main__":
    main()
