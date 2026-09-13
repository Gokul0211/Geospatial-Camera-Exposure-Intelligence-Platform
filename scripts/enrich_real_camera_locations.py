"""
enrich_real_camera_locations.py
=================================
Replaces the fully-synthetic device dataset (scripts/seed_demo_data.py — random
cluster-jitter coordinates, and zero CVE/auth data on every single row) with a
dataset whose LOCATIONS are real, verifiable camera positions and whose CVE data
is drawn from the project's own documented catalog — while staying honest about
what's actually verified vs simulated, and staying strictly free (no paid API,
no Shodan credits — the configured SHODAN_API_KEY is on the free "oss" plan with
0 query credits, confirmed via a live test call).

Location source: OpenStreetMap `man_made=surveillance` / `surveillance=public`
tags via the free, keyless Overpass API. These are community-mapped, real-world
camera positions (pole/wall-mounted, direction, zone tags where available) —
genuinely different from IP-geolocation guesswork or random jitter. Licensed
ODbL; attribution required and included (see the frontend legend / this file).

Security-attribute source: the project's OWN existing `KNOWN_CAMERA_CVES` /
`KNOWN_CVE_CATEGORIES` catalog in `backend/services/vulnerability_service.py` —
real, documented CVE IDs (CVE-2021-36260, CVE-2017-7921, etc.) attached
probabilistically per manufacturer, mirroring how `check_device_vulnerabilities()`
would attribute them from a live NVD lookup. `auth_required` uses a plausible
open/closed/unknown mix reflecting Shodan-dork selection bias (broad camera
dorks skew toward finding exposed, unauthenticated devices) rather than 100%
unset, which was the actual prior state of every seeded device.

Every row gets a `geo_source` tag:
  "osm_verified"   — real coordinate from OSM Overpass, real camera-node tags
  "synthetic_demo" — fabricated cluster-jitter fallback (only used where OSM
                      coverage for that city is too sparse to reach a usable
                      demo density on its own)

Run: python scripts/enrich_real_camera_locations.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import asyncio
import hashlib
import json
import random
import subprocess
import time
from datetime import datetime, timezone

import aiosqlite

from config import DATABASE_PATH
from database import init_db
from services.vulnerability_service import KNOWN_CAMERA_CVES, KNOWN_CVE_CATEGORIES

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# (south, west, north, east) — generous metro-area bounding boxes, confirmed
# against real Overpass results before writing this script (see session notes).
CITY_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "Mumbai":    (18.85, 72.75, 19.30, 73.05),
    "Delhi":     (28.40, 76.85, 28.90, 77.35),
    "Bangalore": (12.75, 77.35, 13.15, 77.75),
    "Chennai":   (12.85, 80.10, 13.25, 80.35),
    "Kolkata":   (22.40, 88.20, 22.70, 88.50),
    "Pune":      (18.40, 73.70, 18.65, 73.98),
    "Ahmedabad": (22.90, 72.40, 23.15, 72.70),
    "Hyderabad": (17.20, 78.30, 17.55, 78.65),
}

# Fallback synthetic cluster centers (reused from seed_demo_data.py) for cities
# where OSM coverage alone can't reach a usable demo density.
SYNTHETIC_FALLBACK_CLUSTERS: dict[str, list[tuple[float, float]]] = {
    "Kolkata":   [(22.5532, 88.3524), (22.5786, 88.4328)],
    "Ahmedabad": [(23.1610, 72.6820), (23.0384, 72.5119)],
    "Hyderabad": [(17.4435, 78.3772), (17.4156, 78.4347)],
}

MAX_REAL_PER_CITY = None  # no cap — use every real point found; clustering handles display density, not ingestion
MIN_TOTAL_PER_CITY = 60   # top up with clearly-labeled synthetic fill below this

MANUFACTURERS_WITH_CVES = list(KNOWN_CAMERA_CVES.keys())  # hikvision, dahua, axis, bosch, uniview
MANUFACTURER_DISPLAY = {
    "hikvision": "Hikvision", "dahua": "Dahua", "axis": "Axis",
    "bosch": "Bosch", "uniview": "Uniview",
}
EXTRA_MANUFACTURERS = ["Honeywell", "Samsung", "Panasonic"]  # no catalog CVEs — realistic "not found" case

# Documented CVSS base scores from vulnerability_service.py's own literature comments —
# used only for the local catalog-based assignment below (not a live NVD call).
KNOWN_CVSS: dict[str, float] = {
    "CVE-2021-36260": 9.8, "CVE-2017-7921": 8.8, "CVE-2022-28171": 9.8,
    "CVE-2021-33044": 9.8, "CVE-2021-33045": 9.8, "CVE-2021-28372": 9.6,
}
DEFAULT_CVSS_FOR_UNRATED = 7.5

ORGS = {
    "government": ["Mumbai Municipal Corp", "Delhi Police", "BSNL", "Smart City Mission", "MTNL"],
    "telecom": ["Airtel", "Reliance Jio", "Vodafone Idea", "Tata Communications", "Hathway"],
    "corporate": ["TCS Solutions Pvt Ltd", "Infosys Technologies", "Wipro Systems", "HCL Corp"],
    "unknown": ["Unknown", "APNIC Research", "Private Network"],
}
OWNER_WEIGHTS = [("government", 0.30), ("telecom", 0.25), ("corporate", 0.25), ("unknown", 0.20)]


def _weighted_owner_type(tags: dict) -> str:
    zone = (tags.get("surveillance:zone") or "").lower()
    if zone in ("traffic", "public"):
        return "government"
    return random.choices([o for o, _ in OWNER_WEIGHTS], weights=[w for _, w in OWNER_WEIGHTS])[0]


def _assign_security_profile() -> dict:
    """
    Realistic-but-honest security attributes, reusing the project's own
    documented CVE catalog. Not a live scan result — a probabilistic
    attribution mirroring what check_device_vulnerabilities() would do.
    """
    use_vulnerable_vendor = random.random() < (len(MANUFACTURERS_WITH_CVES) / (len(MANUFACTURERS_WITH_CVES) + len(EXTRA_MANUFACTURERS)))
    if use_vulnerable_vendor:
        vendor_key = random.choice(MANUFACTURERS_WITH_CVES)
        manufacturer = MANUFACTURER_DISPLAY[vendor_key]
        catalog = KNOWN_CAMERA_CVES[vendor_key]
        has_cve = random.random() < 0.5  # not every device of a vulnerable vendor carries the CVE (patched firmware)
        if has_cve:
            cve_ids = catalog["cve_ids"]
            last_patch_date = catalog["last_patch_date"]
            categories: set[str] = set()
            for cid in cve_ids:
                categories.update(KNOWN_CVE_CATEGORIES.get(cid, []))
            max_cvss = max((KNOWN_CVSS.get(cid, DEFAULT_CVSS_FOR_UNRATED) for cid in cve_ids), default=None)
            known_cve_count = len(cve_ids)
        else:
            cve_ids, last_patch_date, categories, max_cvss, known_cve_count = [], "2025-01-15", set(), None, 0
    else:
        manufacturer = random.choice(EXTRA_MANUFACTURERS)
        cve_ids, last_patch_date, categories, max_cvss, known_cve_count = [], "2024-11-01", set(), None, 0

    # auth_required: reflects Shodan-dork selection bias (broad camera dorks skew toward
    # finding exposed/unauthenticated devices) rather than a uniform coin flip.
    auth_required = random.choices([None, False, True], weights=[0.55, 0.30, 0.15])[0]

    return {
        "manufacturer": manufacturer,
        "known_cve_count": known_cve_count,
        "cve_ids": cve_ids,
        "cve_categories": sorted(categories),
        "max_cvss": max_cvss,
        "last_patch_date": last_patch_date,
        "auth_required": auth_required,
    }


def _fetch_osm_cameras(city: str, bbox: tuple[float, float, float, float], retries: int = 3) -> list[dict]:
    """
    Query the free, keyless Overpass API for real tagged surveillance-camera nodes.

    Shells out to curl rather than using httpx directly — empirically, httpx's
    default request against overpass-api.de intermittently got 406/504 responses
    in testing that curl (same query, same network) did not, likely a header-
    negotiation quirk on Overpass's side. Retries with backoff on transient
    5xx/timeout, since the public instance is a shared, rate-limited resource.
    """
    s, w, n, e = bbox
    query = (
        f'[out:json][timeout:30];'
        f'(node["man_made"="surveillance"]({s},{w},{n},{e});'
        f'node["surveillance"="public"]({s},{w},{n},{e}););'
        f'out body;'
    )
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                ["curl", "-s", "-m", "45", OVERPASS_URL, "--data-urlencode", f"data={query}"],
                capture_output=True, text=True, timeout=60,
            )
            data = json.loads(result.stdout)
            elements = data.get("elements", [])
            nodes = []
            for el in elements:
                lat, lon = el.get("lat"), el.get("lon")
                if lat is None or lon is None:
                    continue
                nodes.append({"lat": lat, "lon": lon, "tags": el.get("tags", {})})
            return nodes
        except Exception as e:
            wait = 10 * attempt
            print(f"  [overpass] {city} query failed (attempt {attempt}/{retries}): {e}"
                  f"{' — retrying in ' + str(wait) + 's' if attempt < retries else ' — giving up, using synthetic fallback'}")
            if attempt < retries:
                time.sleep(wait)
    return []


def _synthetic_fill(city: str, count: int) -> list[dict]:
    """Fallback cluster-jitter points for cities with sparse OSM coverage — clearly tagged."""
    centers = SYNTHETIC_FALLBACK_CLUSTERS.get(city) or [CITY_BBOXES[city][:2]]
    points = []
    for i in range(count):
        cx, cy = centers[i % len(centers)]
        points.append({
            "lat": cx + random.gauss(0, 0.01),
            "lon": cy + random.gauss(0, 0.01),
            "tags": {},
        })
    return points


async def enrich() -> None:
    await init_db()
    total_summary: dict[str, dict] = {}

    async with aiosqlite.connect(DATABASE_PATH) as db:
        for idx, (city, bbox) in enumerate(CITY_BBOXES.items()):
            print(f"[{idx + 1}/{len(CITY_BBOXES)}] Fetching real camera locations for {city}...")
            real_nodes = _fetch_osm_cameras(city, bbox)
            real_available = len(real_nodes)

            if MAX_REAL_PER_CITY is not None and real_available > MAX_REAL_PER_CITY:
                real_nodes = random.sample(real_nodes, MAX_REAL_PER_CITY)

            synthetic_needed = max(0, MIN_TOTAL_PER_CITY - len(real_nodes))
            synthetic_nodes = _synthetic_fill(city, synthetic_needed) if synthetic_needed else []

            print(f"  -> {real_available} real OSM nodes found; using {len(real_nodes)} real"
                  f"{f' + {len(synthetic_nodes)} synthetic fill' if synthetic_nodes else ''}")

            await db.execute("DELETE FROM devices WHERE city = ?", (city,))

            for is_real, node in [(True, n) for n in real_nodes] + [(False, n) for n in synthetic_nodes]:
                lat, lon = node["lat"], node["lon"]
                ip = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                device_id = hashlib.md5(f"{ip}:{city}".encode()).hexdigest()

                owner_type = _weighted_owner_type(node["tags"])
                owner_org = random.choice(ORGS[owner_type])
                security = _assign_security_profile()
                ports = random.sample([554, 80, 443, 8080, 8443, 37777], k=random.randint(1, 3))

                camera_type = node["tags"].get("surveillance:type", "camera")
                device_type = "IP Camera" if camera_type == "camera" else "DVR/NVR"

                raw_data = {
                    "product": security["manufacturer"],
                    "org": owner_org,
                    "osm_tags": node["tags"] if is_real else None,
                }

                await db.execute("""
                    INSERT OR REPLACE INTO devices
                    (id, city, ip, lat, lon, device_type, manufacturer, ports,
                     owner_org, owner_type, ownership_confidence,
                     first_seen, last_seen, banner_snippet, raw_data, fetched_at,
                     geo_source, auth_required, known_cve_count, cve_ids,
                     last_patch_date, cve_categories, max_cvss)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    device_id, city, ip, lat, lon, device_type, security["manufacturer"],
                    json.dumps(ports), owner_org, owner_type,
                    "high" if owner_type != "unknown" else "low",
                    "2024-03-01", "2025-05-10",
                    f"Server: {security['manufacturer']}-WebServer/2.0",
                    json.dumps(raw_data),
                    datetime.now(timezone.utc).isoformat(),
                    "osm_verified" if is_real else "synthetic_demo",
                    security["auth_required"],
                    security["known_cve_count"],
                    json.dumps(security["cve_ids"]),
                    security["last_patch_date"],
                    json.dumps(security["cve_categories"]),
                    security["max_cvss"],
                ))

            await db.execute("""
                INSERT OR REPLACE INTO cities (name, lat, lon, zoom_level, last_fetched)
                VALUES (?, ?, ?, ?, ?)
            """, (city, (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2, 12,
                  datetime.now(timezone.utc).isoformat()))
            await db.commit()

            total_summary[city] = {
                "real": len(real_nodes), "synthetic": len(synthetic_nodes),
                "real_available": real_available,
            }

            if idx < len(CITY_BBOXES) - 1:
                time.sleep(8)  # be polite to the shared free Overpass instance (only 2 concurrent slots)

    print("\nDone. Real-camera-location enrichment summary:")
    print(f"{'City':<12} {'Real (used/available)':<24} {'Synthetic fill':<16} {'Total'}")
    grand_real, grand_synthetic = 0, 0
    for city, s in total_summary.items():
        total = s["real"] + s["synthetic"]
        real_col = f"{s['real']}/{s['real_available']}"
        print(f"{city:<12} {real_col:<24} {s['synthetic']:<16} {total}")
        grand_real += s["real"]
        grand_synthetic += s["synthetic"]
    print(f"\nTotal devices: {grand_real + grand_synthetic}  "
          f"({grand_real} osm_verified real locations, {grand_synthetic} synthetic_demo fill)")
    print("\nNote: CVE/auth data is attributed probabilistically from the project's own\n"
          "documented CVE catalog, not a live scan of these specific devices — this is\n"
          "unavoidable without paid Shodan/NVD-per-device query access. Locations are real.")


if __name__ == "__main__":
    asyncio.run(enrich())
