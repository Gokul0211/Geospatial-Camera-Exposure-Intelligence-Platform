"""
Public demo mode.

When PUBLIC_DEMO=1, the API is safe to put on the open internet:
  - identifying device fields (IP, hostnames, ports, org/ISP/ASN) are stripped from every JSON response
  - coordinates are snapped to a coarse grid (~1.1 km at 0.01 deg) so no single camera can be located
  - heartbeat routes are disabled (they send packets to real camera IPs)
  - all write methods are rejected (no alert injection, no LLM-cost endpoints)

This is defense in depth. The primary control is serving a scrubbed database built by
scripts/make_public_snapshot.py, so the public server never holds real IPs at all
(device IDs are md5(ip:city) and can be brute-forced back to IPs).

Local development is unaffected when PUBLIC_DEMO is unset.
"""

import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_DEMO = os.getenv("PUBLIC_DEMO", "").lower() in ("1", "true", "yes")

REDACT_KEYS = {
    "ip", "ip_str", "hostname", "hostnames", "port", "ports", "open_ports",
    "org", "owner_org", "isp", "asn", "os", "banner_snippet", "raw_data",
}
COORD_KEYS = {"lat", "lon", "latitude", "longitude"}
GRID = float(os.getenv("PUBLIC_DEMO_GRID_DEG", "0.01"))

BLOCKED_PREFIXES = ("/api/heartbeat",)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _snap(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(round(v / GRID) * GRID, 4)
    return v


def _snap_coords(v):
    if isinstance(v, list):
        return [_snap_coords(x) for x in v]
    return _snap(v)


def scrub(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in REDACT_KEYS:
                continue
            if k in COORD_KEYS:
                out[k] = _snap(v)
            elif k == "coordinates":  # GeoJSON [lon, lat] (or nested rings)
                out[k] = _snap_coords(v)
            else:
                out[k] = scrub(v)
        return out
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    return obj


class PublicDemoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith(BLOCKED_PREFIXES):
            return JSONResponse({"detail": "Disabled in public demo mode."}, status_code=403)
        if request.method not in SAFE_METHODS and path.startswith("/api"):
            return JSONResponse({"detail": "Read-only in public demo mode."}, status_code=403)

        response = await call_next(request)

        if "application/json" not in response.headers.get("content-type", ""):
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            data = scrub(json.loads(body))
        except ValueError:
            return Response(body, status_code=response.status_code, media_type="application/json")

        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return JSONResponse(data, status_code=response.status_code, headers=headers)


def install(app: FastAPI) -> None:
    if PUBLIC_DEMO:
        app.add_middleware(PublicDemoMiddleware)
