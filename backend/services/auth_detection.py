"""
auth_detection.py
=================
Phase 1 — Server-side banner-based authentication status inference.

This is a server-side port and improvement of the `isConfirmedOpen(device)`
heuristic that already exists in `frontend/src/components/DetailPanel.jsx`
(lines ~12-20). Moving it server-side lets us persist `auth_required` into
the `devices` table where Phase 2's trust score formula can read it.

IMPORTANT — Ethical/legal boundary
------------------------------------
This module ONLY inspects banner strings already collected by Shodan and
stored in the `banner_snippet` / `raw_data` columns of the `devices` table.
It NEVER makes an outbound connection to a discovered device, attempts a
login, or probes credentials. Passive banner inspection of already-collected
data is what keeps this on the right side of unauthorized-access laws.

`auth_required` column semantics
----------------------------------
  True  — banner clearly signals authentication is required
  False — banner clearly signals the stream/interface is open/unauthenticated
  None  — insufficient signal; Phase 2 should treat this conservatively
          (i.e., assume open, apply the −30 penalty)
"""

from __future__ import annotations

import json
import re
import asyncio
import aiosqlite
from datetime import datetime, timezone
from config import DATABASE_PATH


# ---------------------------------------------------------------------------
# Keyword lists — tunable without touching the function signature
# ---------------------------------------------------------------------------

# Signals that authentication IS required
_AUTH_SIGNALS: list[str] = [
    "401 unauthorized",
    "403 forbidden",
    "www-authenticate",
    "authentication required",
    "login required",
    "please log in",
    "please login",
    "password",
    "username",
    "sign in",
    "access denied",
    "unauthorized",
    "digest realm",
    "basic realm",
    "ntlm",
    "negotiate",
    # RTSP-specific auth indicators
    "rtsp/1.0 401",
    "rtsp/2.0 401",
]

# Signals that the stream/interface is OPEN (no auth)
_OPEN_SIGNALS: list[str] = [
    "200 ok",
    "mjpeg",
    "video web server",
    "netcam",
    "ip camera",
    "network camera",
    "ipcam",
    "live view",
    "liveview",
    "videostream",
    "video_stream",
    "rtsp server ready",
    "rtsp/1.0 200 ok",
    "rtsp/2.0 200 ok",
    # Common open-access DVR/NVR web UIs
    "dvr login",          # paradoxically: banner saying "dvr login" shows it has a login
    "camera web server",  # generic open header used by many cheap cams
    "h264dvr",            # Hikvision/clone open RTSP banner
    "server: yawcam",     # Yawcam — typically open by default
    "server: webcam 7",   # Webcam 7 — typically open
]

# These manufacturer/product strings are known to default to open access
# and are weighted as additional open evidence when seen in the banner.
_KNOWN_OPEN_DEFAULTS: list[str] = [
    "hikvision",   # CVE-2021-36260 involves default/no auth
    "dahua",
    "avtech",
    "foscam",
    "vstarcam",
    "uniview",
]


# ---------------------------------------------------------------------------
# Core inference function
# ---------------------------------------------------------------------------

def infer_auth_required(
    banner_snippet: str | None,
    raw_data: str | dict | None = None,
) -> bool | None:
    """
    Infer whether a device requires authentication based on passive banner
    inspection of Shodan-collected data.

    Parameters
    ----------
    banner_snippet : str | None
        First ~200 chars of the Shodan `data` field, stored in `devices.banner_snippet`.
    raw_data : str | dict | None, optional
        JSON string or already-parsed dict from `devices.raw_data`.
        Used to extract additional product/org context.

    Returns
    -------
    bool | None
        True  — auth clearly required
        False — clearly open / unauthenticated
        None  — not enough signal to decide

    Notes
    -----
    The function counts weighted positive signals on each side and picks the
    winner only when there's a meaningful signal surplus. If both sides score
    equally, or neither has any signal, returns None (ambiguous).

    Passive inspection only — no network calls, no I/O.
    """
    # Normalise inputs to lowercase strings for matching
    banner = (banner_snippet or "").lower()

    raw: dict = {}
    if isinstance(raw_data, str):
        try:
            raw = json.loads(raw_data)
        except (json.JSONDecodeError, TypeError):
            raw = {}
    elif isinstance(raw_data, dict):
        raw = raw_data

    # Build a combined context string from banner + raw_data fields
    extra = " ".join(filter(None, [
        str(raw.get("product") or ""),
        str(raw.get("org") or ""),
        str(raw.get("os") or ""),
    ])).lower()
    context = f"{banner} {extra}".strip()

    if not context:
        return None  # nothing to inspect

    auth_score = 0
    open_score = 0

    # Count auth signals (each hit = +1 to auth_score)
    for signal in _AUTH_SIGNALS:
        if signal in context:
            auth_score += 1

    # Count open signals (each hit = +1 to open_score)
    for signal in _OPEN_SIGNALS:
        if signal in context:
            open_score += 1

    # Known-open-default manufacturers add a soft weight to the open side
    # (they are not conclusive on their own — only tip the balance)
    for mfr in _KNOWN_OPEN_DEFAULTS:
        if mfr in context:
            open_score += 0.5  # half-weight: manufacturer alone isn't conclusive

    # HTTP status code pattern — explicit 200/401 in the banner is strong evidence
    if re.search(r"\bHTTP/1\.[01]\s+200\b", banner_snippet or "", re.IGNORECASE):
        open_score += 2   # strong open signal
    if re.search(r"\bHTTP/1\.[01]\s+401\b", banner_snippet or "", re.IGNORECASE):
        auth_score += 2   # strong auth signal

    # Decision: need a meaningful surplus on one side (> 0.5 difference)
    # to avoid flipping on noise. If both are 0, return None.
    if auth_score == 0 and open_score == 0:
        return None
    if auth_score > open_score:
        return True   # auth required
    if open_score > auth_score:
        return False  # open access (no auth)
    # Tie — not enough signal
    return None


# ---------------------------------------------------------------------------
# Batch persistence pass
# ---------------------------------------------------------------------------

async def run_auth_detection_for_city(city: str) -> dict:
    """
    Walk every device row for `city`, run `infer_auth_required`, and persist
    the result into `devices.auth_required`. This is a batch pass over the
    existing DB data — no Shodan queries, no network calls.

    Safe to run multiple times (idempotent — just overwrites with the same
    inferred value if the banner hasn't changed).

    Parameters
    ----------
    city : str
        City name matching the `devices.city` column.

    Returns
    -------
    dict with summary stats:
        total    : int  — total devices scanned
        auth     : int  — devices inferred as requiring auth
        open     : int  — devices inferred as open
        unknown  : int  — devices with insufficient signal
    """
    stats = {"total": 0, "auth": 0, "open": 0, "unknown": 0}

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, banner_snippet, raw_data FROM devices WHERE city = ?",
            (city,),
        ) as cursor:
            devices = await cursor.fetchall()

    if not devices:
        print(f"[auth_detection] No devices found for city='{city}'")
        return stats

    print(f"[auth_detection] Running auth inference on {len(devices)} devices in {city}")

    updates: list[tuple] = []
    for device in devices:
        stats["total"] += 1
        result = infer_auth_required(
            banner_snippet=device["banner_snippet"],
            raw_data=device["raw_data"],
        )
        if result is True:
            stats["auth"] += 1
        elif result is False:
            stats["open"] += 1
        else:
            stats["unknown"] += 1

        # SQLite stores BOOLEAN as integer: 1 / 0 / NULL
        db_value = 1 if result is True else (0 if result is False else None)
        updates.append((db_value, device["id"]))

    # Batch-write all updates in a single transaction
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executemany(
            "UPDATE devices SET auth_required = ? WHERE id = ?",
            updates,
        )
        await db.commit()

    print(
        f"[auth_detection] Done. "
        f"auth={stats['auth']} open={stats['open']} unknown={stats['unknown']}"
    )
    return stats


async def run_auth_detection_all_cities() -> dict:
    """
    Convenience wrapper: run auth detection for all cities currently in the DB.
    """
    import aiosqlite as _aiosqlite
    async with _aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT name FROM cities") as cursor:
            cities = [row[0] for row in await cursor.fetchall()]

    combined = {"total": 0, "auth": 0, "open": 0, "unknown": 0}
    for city in cities:
        result = await run_auth_detection_for_city(city)
        for k in combined:
            combined[k] += result.get(k, 0)
    return combined
