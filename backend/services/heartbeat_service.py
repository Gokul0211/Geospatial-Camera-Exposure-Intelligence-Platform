"""
heartbeat_service.py
=====================
Module D (IIT-B BTP) — Camera Heartbeat & Signal Integrity Trust Factor
Literature: YOLO in Suspicious Activity Review (ResearchGate, 2025)
           Rasal et al. (Springer LNNS, 2025)

Provides async ping-based camera health monitoring. Integrates network
reachability and latency as trust score deduction factors.

The YOLO Review (2025) explicitly identifies camera offline/damaged states
as a hard failure that makes surveillance systems "non-functional". COBRA-WATCH
converts this failure mode into a scored trust factor — the key academic
contribution of this module.

Deduction schedule (from compute_advanced_trust_score):
  Unreachable (timeout):   −15 pts + flag: camera_offline
  High latency (>500ms):   −10 pts + flag: high_signal_latency_{N}ms
  Elevated latency (>150ms): −5 pts + flag: elevated_signal_latency_{N}ms
  Healthy (<150ms):          0 pts
"""

from __future__ import annotations

import asyncio
import socket
import time
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Core ping implementation (async TCP ping — works on Windows without root)
# ---------------------------------------------------------------------------

async def tcp_ping(host: str, port: int = 80, timeout: float = 3.0) -> dict:
    """
    Async TCP connect-based ping to a host:port.
    Returns latency_ms and reachable flag.

    Uses TCP SYN (connect) rather than ICMP so it works without root privileges
    on Windows and Linux alike. Falls back through common camera ports:
    80 (HTTP), 554 (RTSP), 8080 (HTTP-alt).

    Parameters
    ----------
    host : str
        IP address or hostname to ping.
    port : int
        TCP port to connect to (default 80).
    timeout : float
        Connection timeout in seconds (default 3.0).

    Returns
    -------
    dict with keys: reachable (bool), latency_ms (float | None)
    """
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency_ms = (time.monotonic() - start) * 1000.0
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return {"reachable": True, "latency_ms": round(latency_ms, 1)}
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return {"reachable": False, "latency_ms": None}
    except Exception:
        return {"reachable": False, "latency_ms": None}


async def ping_camera(ip: str, timeout: float = 3.0) -> dict:
    """
    Try common camera ports in order: 80, 554, 8080.
    Returns the first successful result, or unreachable if all fail.

    Parameters
    ----------
    ip : str
        Camera IP address.
    timeout : float
        Per-port connection timeout in seconds.

    Returns
    -------
    dict: {reachable, latency_ms, port_used, checked_at}
    """
    ports_to_try = [80, 554, 8080]
    last_result = {"reachable": False, "latency_ms": None}

    for port in ports_to_try:
        result = await tcp_ping(ip, port=port, timeout=timeout)
        if result["reachable"]:
            return {
                "reachable": True,
                "latency_ms": result["latency_ms"],
                "port_used": port,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        last_result = result

    return {
        "reachable": False,
        "latency_ms": None,
        "port_used": None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Trust factor derivation
# ---------------------------------------------------------------------------

def get_heartbeat_trust_factor(ping_result: dict) -> dict:
    """
    Derive a trust score deduction and factor string from a ping result.

    Parameters
    ----------
    ping_result : dict
        Output of `ping_camera()`.

    Returns
    -------
    dict: {deduction, factor, status}
      deduction : int   — points to subtract from trust score (0, 5, 10, or 15)
      factor    : str   — factor string for contributing_factors list, or None
      status    : str   — "healthy" | "elevated" | "degraded" | "offline"
    """
    if not ping_result.get("reachable"):
        return {
            "deduction": 15,
            "factor": "camera_offline",
            "status": "offline",
        }

    latency_ms = ping_result.get("latency_ms") or 0.0

    if latency_ms > 500.0:
        return {
            "deduction": 10,
            "factor": f"high_signal_latency_{int(latency_ms)}ms",
            "status": "degraded",
        }
    elif latency_ms > 150.0:
        return {
            "deduction": 5,
            "factor": f"elevated_signal_latency_{int(latency_ms)}ms",
            "status": "elevated",
        }
    else:
        return {
            "deduction": 0,
            "factor": None,
            "status": "healthy",
        }


async def get_heartbeat_factor(ip: str, timeout: float = 3.0) -> dict:
    """
    Full pipeline: ping camera → derive trust factor.
    Convenience function for use in alert pipeline.

    Returns
    -------
    dict: {ping, factor} where ping is the raw ping result and
          factor is the trust deduction dict.
    """
    ping = await ping_camera(ip, timeout=timeout)
    factor = get_heartbeat_trust_factor(ping)
    return {"ping": ping, "factor": factor}
