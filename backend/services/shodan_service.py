import shodan
import asyncio
import aiosqlite
import json
import hashlib
from datetime import datetime, timedelta, timezone
from config import SHODAN_API_KEY, SHODAN_QUERIES, DATABASE_PATH, CACHE_TTL_HOURS
from services.ownership_service import enrich_ownership


def _device_id(ip: str, city: str) -> str:
    """Deterministic ID so the same IP+city always maps to the same device row."""
    return hashlib.md5(f"{ip}:{city}".encode()).hexdigest()


def _classify_device_type(data: dict) -> str:
    """Classify a Shodan result into a human-readable device type."""
    product = (data.get("product") or "").lower()
    title = ((data.get("http") or {}).get("title") or "").lower()
    banner = (data.get("data") or "").lower()
    port = data.get("port", 0)

    if any(k in product for k in ["camera", "webcam", "ipcam"]):
        return "IP Camera"
    if any(k in product for k in ["hikvision", "dahua", "axis", "bosch", "vivotek", "uniview"]):
        return "IP Camera"
    if any(k in title for k in ["dvr", "nvr", "cctv", "video recorder"]):
        return "DVR/NVR"
    if port == 554 or "rtsp" in banner:
        return "RTSP Stream"
    if any(k in product for k in ["zte", "huawei", "nokia"]) and port not in [80, 443]:
        return "Telecom Equipment"
    if any(k in banner for k in ["netcam", "ip camera", "network camera"]):
        return "IP Camera"
    if any(k in title for k in ["router", "gateway", "modem"]):
        return "Network Device"
    return "Network Device"


def _extract_manufacturer(data: dict) -> str:
    """Extract manufacturer name from Shodan result."""
    product = data.get("product") or ""
    org = data.get("org") or ""
    known = ["Hikvision", "Dahua", "Axis", "Bosch", "Samsung", "Sony",
             "Panasonic", "Hanwha", "Vivotek", "Uniview", "ZTE", "Huawei",
             "TP-Link", "D-Link", "Honeywell", "Pelco", "Avigilon"]
    for m in known:
        if m.lower() in product.lower() or m.lower() in org.lower():
            return m
    if product:
        first_word = product.split()[0]
        if len(first_word) > 2:
            return first_word.title()
    return "Unknown"


async def _is_cache_fresh(city: str) -> bool:
    """Check if cached data is less than CACHE_TTL_HOURS old."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT last_fetched FROM cities WHERE name = ?", (city,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return False
            try:
                last = datetime.fromisoformat(row[0])
                return datetime.now(timezone.utc) - last < timedelta(hours=CACHE_TTL_HOURS)
            except (ValueError, TypeError):
                return False


async def _load_from_cache(city: str) -> list:
    """Load cached devices from SQLite."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM devices WHERE city = ?", (city,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def _save_devices(city: str, devices: list):
    """Save devices to SQLite cache."""
    from config import CITIES
    city_data = CITIES.get(city, {})
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Delete old entries for this city to avoid stale data
        await db.execute("DELETE FROM devices WHERE city = ?", (city,))

        for d in devices:
            await db.execute("""
                INSERT OR REPLACE INTO devices
                (id, city, ip, lat, lon, device_type, manufacturer, ports,
                 owner_org, owner_type, ownership_confidence,
                 first_seen, last_seen, banner_snippet, raw_data, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                d["id"], city, d["ip"],
                d.get("lat"), d.get("lon"),
                d.get("device_type"), d.get("manufacturer"),
                json.dumps(d.get("ports", [])),
                d.get("owner_org"), d.get("owner_type"),
                d.get("ownership_confidence"),
                d.get("first_seen"), d.get("last_seen"),
                d.get("banner_snippet"),
                json.dumps(d.get("raw", {})),
                datetime.now(timezone.utc).isoformat()
            ))

        await db.execute("""
            INSERT OR REPLACE INTO cities (name, lat, lon, zoom_level, last_fetched)
            VALUES (?, ?, ?, ?, ?)
        """, (
            city,
            city_data.get("lat", 0),
            city_data.get("lon", 0),
            city_data.get("zoom", 12),
            datetime.now(timezone.utc).isoformat()
        ))
        await db.commit()


def _run_shodan_queries(city: str) -> list:
    """Synchronous Shodan queries — run in executor to avoid blocking the event loop."""
    if not SHODAN_API_KEY:
        print(f"[warn] No SHODAN_API_KEY set, returning empty results for {city}")
        return []

    api = shodan.Shodan(SHODAN_API_KEY)
    results = []
    seen_ips = set()

    for query_template in SHODAN_QUERIES:
        query = query_template.format(city=city)
        try:
            print(f"  [shodan] Running query: {query}")
            res = api.search(query, limit=100)
            count = 0
            for match in res.get("matches", []):
                ip = match.get("ip_str", "")
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)

                location = match.get("location", {})
                lat = location.get("latitude")
                lon = location.get("longitude")
                if not lat or not lon:
                    continue

                ports = match.get("ports", [])
                if not ports and match.get("port"):
                    ports = [match["port"]]
                ports = [p for p in ports if p]

                results.append({
                    "id": _device_id(ip, city),
                    "ip": ip,
                    "lat": lat,
                    "lon": lon,
                    "device_type": _classify_device_type(match),
                    "manufacturer": _extract_manufacturer(match),
                    "ports": ports,
                    "first_seen": (match.get("timestamp") or "")[:10],
                    "last_seen": (match.get("timestamp") or "")[:10],
                    "banner_snippet": (match.get("data") or "")[:200],
                    "raw": {k: match.get(k) for k in ["product", "org", "isp", "os", "hostnames"]},
                })
                count += 1
            print(f"    → {count} new devices from this query")
        except shodan.APIError as e:
            print(f"  [shodan error] Query '{query}': {e}")
            continue
        except Exception as e:
            print(f"  [shodan exception] Query '{query}': {e}")
            continue

    print(f"  [shodan] Total unique devices for {city}: {len(results)}")
    return results


async def fetch_and_cache_city(city: str) -> list:
    """Fetch devices for a city. Returns from cache if fresh."""
    if await _is_cache_fresh(city):
        print(f"[cache hit] {city}")
        return await _load_from_cache(city)

    print(f"[shodan fetch] {city}")
    loop = asyncio.get_event_loop()
    raw_devices = await loop.run_in_executor(None, _run_shodan_queries, city)

    if not raw_devices:
        stale = await _load_from_cache(city)
        if stale:
            print(f"[warn] No fresh data for {city}, returning {len(stale)} stale cached devices")
            return stale
        print(f"[warn] No data at all for {city}")
        return []

    # Enrich with ownership — run in small batches to avoid WHOIS rate limiting
    from config import WHOIS_BATCH_SIZE, WHOIS_DELAY_SECONDS
    enriched = []
    for i in range(0, len(raw_devices), WHOIS_BATCH_SIZE):
        batch = raw_devices[i:i + WHOIS_BATCH_SIZE]
        tasks = [enrich_ownership(d) for d in batch]
        enriched.extend(await asyncio.gather(*tasks))
        if i + WHOIS_BATCH_SIZE < len(raw_devices):
            await asyncio.sleep(WHOIS_DELAY_SECONDS)

    await _save_devices(city, enriched)
    return enriched


def devices_to_geojson(devices: list) -> dict:
    """Convert device list to GeoJSON FeatureCollection for Leaflet."""
    features = []
    for d in devices:
        if not d.get("lat") or not d.get("lon"):
            continue
        ports = d.get("ports")
        if isinstance(ports, str):
            try:
                ports = json.loads(ports)
            except Exception:
                ports = []
        # Parse raw_data for extra fields (stored as JSON string in DB)
        raw = d.get("raw_data") or d.get("raw") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [d["lon"], d["lat"]]
            },
            "properties": {
                "id": d["id"],
                "ip": d["ip"],
                # Include coordinates directly in properties so frontend can access them
                "lat": d["lat"],
                "lon": d["lon"],
                "device_type": d.get("device_type"),
                "manufacturer": d.get("manufacturer"),
                "ports": ports,
                "owner_org": d.get("owner_org"),
                "org": d.get("owner_org") or raw.get("org"),
                "owner_type": d.get("owner_type", "unknown"),
                "ownership_confidence": d.get("ownership_confidence", "low"),
                "first_seen": d.get("first_seen"),
                "last_seen": d.get("last_seen"),
                "last_update": d.get("last_seen") or d.get("fetched_at", ""),
                "banner_snippet": d.get("banner_snippet"),
                "os": raw.get("os"),
                "isp": raw.get("isp"),
            }
        })
    return {"type": "FeatureCollection", "features": features}
