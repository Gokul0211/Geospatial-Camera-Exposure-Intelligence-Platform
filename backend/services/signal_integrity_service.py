"""
signal_integrity_service.py
===========================
Module G / Research Novelty — Integrity-Gated Dual-Channel Trust Fusion (IG-DCTF)
Literature:
  - Yilmazer & Karakose (2025): Image-quality & tampering trust modelling
  - Zhang et al. ByteTrack (2022): Stream trustworthiness & cross-modal fusion
  - Swami et al. SCI-IoT (2025): Security gate auto-fail patterns
  - Griffioen & Doerr (2020), Antonakakis et al. (2017)

Architecture:
  Treats video signal authenticity and cyber-vulnerability trust as two
  independent, orthogonal channels fused via a multiplicative hard gate:
    SignalIntegrity(t) = f(Drift(d, t), L(t))
    T_final(t) = T_cve(t) * G(SignalIntegrity(t))

Tier 1 (Passive OSINT Banner Drift):
  Extracts fingerprint vector B_d(t) from Shodan/Censys metadata without any
  outbound connections to discovered cameras. Computes normalized drift.

Tier 2 (Frame-Level Visual Liveness):
  Ingests real-time frame freeze (pHash), quality drift (Laplacian blur/exposure),
  and spec-mismatch signals for authorized video streams.
"""

from __future__ import annotations

import json
import re
import math
import aiosqlite
from typing import Any
from config import DATABASE_PATH


# ---------------------------------------------------------------------------
# Default Weights & Thresholds
# ---------------------------------------------------------------------------

DEFAULT_DRIFT_WEIGHTS = {
    "resolution": 0.20,
    "firmware_version": 0.25,
    "http_server": 0.20,
    "open_ports": 0.20,
    "product_string": 0.10,
    "codec": 0.05,
}

THETA_HIGH = 0.85   # Nominal threshold (multiplier = 1.0)
THETA_LOW = 0.50    # Critical integrity threshold (hard gate cap <= 30)


# ---------------------------------------------------------------------------
# Tier 1 — Passive Banner-Fingerprint Extraction & Drift Scoring
# ---------------------------------------------------------------------------

def extract_banner_fingerprint(raw_data: dict | str | None) -> dict[str, Any]:
    """
    Extract a structured fingerprint vector B_d(t) from raw Shodan/Censys/banner metadata.
    Operates strictly passively with zero outbound network traffic.

    Parameters
    ----------
    raw_data : dict | str | None
        Raw dictionary from Shodan search or string representation of banner snippet.

    Returns
    -------
    dict
        Structured fingerprint vector containing resolution, codec, firmware,
        http_server, open_ports, and product_string.
    """
    if raw_data is None:
        return {
            "resolution": "unknown",
            "codec": "unknown",
            "firmware_version": "unknown",
            "http_server": "unknown",
            "open_ports": [],
            "product_string": "unknown",
        }

    if isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, dict):
                raw_data = parsed
            else:
                raw_data = {"data": raw_data}
        except Exception:
            raw_data = {"data": raw_data}

    # 1. Product string
    product = (raw_data.get("product") or "").strip()
    if not product and "data" in raw_data:
        banner = raw_data.get("data", "")
        # Basic heuristic fallback
        for m in ["Hikvision", "Dahua", "Axis", "Bosch", "Uniview", "Vivotek", "Hanwha"]:
            if m.lower() in banner.lower():
                product = m
                break
    product_string = product.lower() if product else "unknown"

    # 2. HTTP Server header
    http_block = raw_data.get("http") or {}
    server_header = http_block.get("server") or ""
    if not server_header and "data" in raw_data:
        banner = raw_data.get("data", "")
        match = re.search(r"Server:\s*([^\r\n]+)", banner, re.IGNORECASE)
        if match:
            server_header = match.group(1).strip()
    http_server = server_header.lower() if server_header else "unknown"

    # 3. Firmware version string
    firmware = raw_data.get("firmware_version") or raw_data.get("version") or ""
    if not firmware and "data" in raw_data:
        banner = raw_data.get("data", "")
        match = re.search(r"(?:firmware|version|ver|v)[\s/:]*([vV]?\d+(?:\.\d+)+[_\w-]*)", banner, re.IGNORECASE)
        if match:
            firmware = match.group(1).strip()
    firmware_version = firmware.lower() if firmware else "unknown"

    # 4. Open ports
    ports: list[int] = []
    if "port" in raw_data and isinstance(raw_data["port"], (int, str)):
        try:
            ports.append(int(raw_data["port"]))
        except ValueError:
            pass
    if "ports" in raw_data and isinstance(raw_data["ports"], list):
        for p in raw_data["ports"]:
            try:
                ports.append(int(p))
            except ValueError:
                pass
    open_ports = sorted(list(set(ports)))

    # 5. Claimed Resolution & Codec
    resolution = "unknown"
    codec = "unknown"
    banner_text = (raw_data.get("data") or "") + " " + (http_block.get("title") or "")
    
    # Resolution pattern match (e.g. 1920x1080, 1080p, 4K, 720p, 3840x2160)
    res_match = re.search(r"\b(1920\s*[xX*]\s*1080|1280\s*[xX*]\s*720|3840\s*[xX*]\s*2160|2560\s*[xX*]\s*1440|704\s*[xX*]\s*576|640\s*[xX*]\s*480|1080[pP]|720[pP]|4[kK])\b", banner_text)
    if res_match:
        res_raw = res_match.group(1).lower().replace(" ", "")
        if "1080" in res_raw:
            resolution = "1080p"
        elif "720" in res_raw:
            resolution = "720p"
        elif "2160" in res_raw or "4k" in res_raw:
            resolution = "4k"
        elif "1440" in res_raw:
            resolution = "1440p"
        elif "480" in res_raw or "576" in res_raw:
            resolution = "480p"
        else:
            resolution = res_raw

    # Codec pattern match
    codec_match = re.search(r"\b(h\.?264|h\.?265|hevc|mjpeg|av1|mpeg4)\b", banner_text, re.IGNORECASE)
    if codec_match:
        c_raw = codec_match.group(1).lower().replace(".", "")
        if "264" in c_raw:
            codec = "h264"
        elif "265" in c_raw or "hevc" in c_raw:
            codec = "h265"
        elif "mjpeg" in c_raw:
            codec = "mjpeg"
        else:
            codec = c_raw

    return {
        "resolution": resolution,
        "codec": codec,
        "firmware_version": firmware_version,
        "http_server": http_server,
        "open_ports": open_ports,
        "product_string": product_string,
    }


def compute_banner_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Compute normalized weighted drift between a baseline fingerprint B_d(t-1) and
    the current fingerprint B_d(t).

    Drift(d, t) = sum_i (w_i * mismatch(B_d(t)[i], B_d(t-1)[i])) in [0, 1]

    Parameters
    ----------
    baseline : dict
        Previous scan fingerprint vector.
    current : dict
        Current scan fingerprint vector.
    weights : dict | None
        Optional custom weights dict.

    Returns
    -------
    dict:
        drift_score: float in [0.0, 1.0]
        drift_factors: list[str] explaining specific mismatches
        component_distances: dict[str, float]
    """
    w = weights or DEFAULT_DRIFT_WEIGHTS
    drift_factors: list[str] = []
    component_distances: dict[str, float] = {}

    total_weight = sum(w.values())
    accumulated_drift = 0.0

    # 1. Categorical / string exact matches
    for field in ["product_string", "http_server", "firmware_version", "codec"]:
        b_val = str(baseline.get(field, "unknown")).lower()
        c_val = str(current.get(field, "unknown")).lower()

        # If both are unknown, no drift penalty
        if b_val == "unknown" and c_val == "unknown":
            dist = 0.0
        elif b_val != "unknown" and c_val != "unknown" and b_val != c_val:
            dist = 1.0
            drift_factors.append(f"drift:{field}_changed_{b_val}_to_{c_val}")
        elif (b_val == "unknown") != (c_val == "unknown"):
            # One gained or lost a field — partial anomaly
            dist = 0.5
            drift_factors.append(f"drift:{field}_presence_anomaly")
        else:
            dist = 0.0

        component_distances[field] = dist
        accumulated_drift += w.get(field, 0.0) * dist

    # 2. Resolution distance
    b_res = str(baseline.get("resolution", "unknown")).lower()
    c_res = str(current.get("resolution", "unknown")).lower()
    if b_res != "unknown" and c_res != "unknown" and b_res != c_res:
        # Check if resolution dropped (e.g. 1080p -> 480p indicates physical swap/downgrade)
        res_rank = {"480p": 1, "720p": 2, "1080p": 3, "1440p": 4, "4k": 5}
        b_rank = res_rank.get(b_res, 3)
        c_rank = res_rank.get(c_res, 3)
        if c_rank < b_rank:
            res_dist = 1.0
            drift_factors.append(f"drift:resolution_downgraded_{b_res}_to_{c_res}")
        else:
            res_dist = 0.6
            drift_factors.append(f"drift:resolution_shifted_{b_res}_to_{c_res}")
    else:
        res_dist = 0.0
    component_distances["resolution"] = res_dist
    accumulated_drift += w.get("resolution", 0.0) * res_dist

    # 3. Open Ports Jaccard Distance
    b_ports = set(baseline.get("open_ports") or [])
    c_ports = set(current.get("open_ports") or [])
    if b_ports or c_ports:
        intersection = len(b_ports.intersection(c_ports))
        union = len(b_ports.union(c_ports))
        jaccard_dist = 1.0 - (intersection / union if union > 0 else 1.0)
        if jaccard_dist > 0.0:
            drift_factors.append(f"drift:port_set_jaccard_{jaccard_dist:.2f}")
    else:
        jaccard_dist = 0.0
    component_distances["open_ports"] = jaccard_dist
    accumulated_drift += w.get("open_ports", 0.0) * jaccard_dist

    normalized_drift = min(1.0, max(0.0, accumulated_drift / total_weight if total_weight > 0 else 0.0))

    return {
        "drift_score": round(normalized_drift, 4),
        "drift_factors": drift_factors,
        "component_distances": component_distances,
    }


# ---------------------------------------------------------------------------
# Tier 2 — Frame-Level Visual Liveness & Tamper Signal
# ---------------------------------------------------------------------------

def compute_visual_liveness(
    freeze_flag: bool = False,
    quality_drift: float = 0.0,
    spec_mismatch_flag: bool = False,
    weights: tuple[float, float, float] = (1.00, 0.60, 0.50),
) -> dict[str, Any]:
    """
    Compute Visual Liveness Score L(t) for authorized cameras in FOOTAGE_CAMERA_MAP.

    L(t) = 1 - max(w1 * Freeze, w2 * QualityDrift, w3 * SpecMismatch) in [0, 1]

    Parameters
    ----------
    freeze_flag : bool
        True if pHash distance across rolling window indicates a frozen or looped feed.
    quality_drift : float in [0.0, 1.0]
        Degree of blur/exposure deviation from per-camera learned EWMA baseline.
    spec_mismatch_flag : bool
        True if live frame resolution/spec violates Shodan declared spec.
    weights : tuple
        (w_freeze, w_quality, w_spec)

    Returns
    -------
    dict
        liveness_score: float in [0.0, 1.0]
        liveness_factors: list[str]
    """
    w1, w2, w3 = weights
    liveness_factors: list[str] = []

    f_term = (1.0 if freeze_flag else 0.0) * w1
    q_term = min(1.0, max(0.0, quality_drift)) * w2
    s_term = (1.0 if spec_mismatch_flag else 0.0) * w3

    if freeze_flag:
        liveness_factors.append("visual_tamper:freeze_or_loop_detected")
    if quality_drift > 0.40:
        liveness_factors.append(f"visual_tamper:quality_drift_{quality_drift:.2f}")
    if spec_mismatch_flag:
        liveness_factors.append("visual_tamper:declared_spec_mismatch")

    penalty = max(f_term, q_term, s_term)
    liveness = max(0.0, min(1.0, 1.0 - penalty))

    return {
        "liveness_score": round(liveness, 4),
        "liveness_factors": liveness_factors,
    }


# ---------------------------------------------------------------------------
# Dual-Channel Composite Signal Integrity & Multiplicative Gate
# ---------------------------------------------------------------------------

def compute_composite_signal_integrity(
    drift_score: float = 0.0,
    visual_liveness: float | None = None,
) -> dict[str, Any]:
    """
    Fuse Tier 1 (passive banner drift) and Tier 2 (frame liveness) into a single
    SignalIntegrity(t) metric in [0.0, 1.0].

    SignalIntegrity(t) =
        (1 - Drift(d, t)) * L(t)   if Tier 2 is available
        1 - Drift(d, t)            otherwise
    """
    tier1_integrity = max(0.0, min(1.0, 1.0 - drift_score))

    if visual_liveness is not None:
        composite = tier1_integrity * max(0.0, min(1.0, visual_liveness))
        tier2_used = True
    else:
        composite = tier1_integrity
        tier2_used = False

    return {
        "signal_integrity": round(composite, 4),
        "tier1_integrity": round(tier1_integrity, 4),
        "tier2_liveness": visual_liveness,
        "tier2_used": tier2_used,
    }


def evaluate_integrity_gate(
    signal_integrity: float,
    theta_high: float = THETA_HIGH,
    theta_low: float = THETA_LOW,
) -> dict[str, Any]:
    """
    Multiplicative Hard Gate G(s) gating the live trust score.

    G(s) =
        1.0                                      if s >= theta_high (0.85)
        0.3 + 0.7 * (s - theta_low)/(theta_high - theta_low)   if theta_low <= s < theta_high
        0.3 (hard capped at score <= 30)          if s < theta_low (0.50)

    Returns
    -------
    dict:
        multiplier: float in [0.3, 1.0]
        hard_cap: int | None (30 if s < theta_low, else None)
        gate_tripped: bool (True if s < theta_low)
        gate_status: "nominal" | "tapered" | "hard_gated"
    """
    s = max(0.0, min(1.0, signal_integrity))

    if s >= theta_high:
        return {
            "multiplier": 1.0,
            "hard_cap": None,
            "gate_tripped": False,
            "gate_status": "nominal",
        }
    elif s >= theta_low:
        # Linear taper from 1.0 down to 0.3
        slope = (1.0 - 0.3) / (theta_high - theta_low)
        multiplier = 0.3 + slope * (s - theta_low)
        return {
            "multiplier": round(multiplier, 4),
            "hard_cap": None,
            "gate_tripped": False,
            "gate_status": "tapered",
        }
    else:
        # Critical failure: feed spoofed/substituted/frozen
        return {
            "multiplier": 0.30,
            "hard_cap": 30,
            "gate_tripped": True,
            "gate_status": "hard_gated",
        }


# ---------------------------------------------------------------------------
# Database Persistence Integration
# ---------------------------------------------------------------------------

async def record_device_drift_and_integrity(
    device_id: str,
    raw_shodan_data: dict | str,
    visual_liveness: float | None = None,
) -> dict[str, Any]:
    """
    Fetch baseline fingerprint from SQLite, compute drift vs new scan,
    and persist updated fingerprint and signal integrity metrics.
    """
    current_fp = extract_banner_fingerprint(raw_shodan_data)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT banner_fingerprint FROM devices WHERE id = ?", (device_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row and row["banner_fingerprint"]:
            try:
                baseline_fp = json.loads(row["banner_fingerprint"])
            except Exception:
                baseline_fp = current_fp
        else:
            baseline_fp = current_fp

        drift_result = compute_banner_drift(baseline_fp, current_fp)
        drift_score = drift_result["drift_score"]

        integrity_res = compute_composite_signal_integrity(drift_score, visual_liveness)
        sig_integrity = integrity_res["signal_integrity"]

        gate_res = evaluate_integrity_gate(sig_integrity)
        is_tripped = 1 if gate_res["gate_tripped"] else 0

        # Update devices table
        await db.execute("""
            UPDATE devices
            SET banner_fingerprint = ?,
                last_drift_score = ?,
                signal_integrity_score = ?,
                integrity_gate_tripped = ?
            WHERE id = ?
        """, (
            json.dumps(current_fp),
            drift_score,
            sig_integrity,
            is_tripped,
            device_id,
        ))
        await db.commit()

        return {
            "device_id": device_id,
            "fingerprint": current_fp,
            "drift_score": drift_score,
            "drift_factors": drift_result["drift_factors"],
            "signal_integrity": sig_integrity,
            "gate": gate_res,
        }
