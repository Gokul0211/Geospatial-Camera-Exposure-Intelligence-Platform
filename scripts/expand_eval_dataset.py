"""
scripts/expand_eval_dataset.py
==============================
Generates an expanded benchmark dataset of 100 labeled evaluation scenarios
(preserving the original 50 and adding 50 systematic corner cases) for
COBRA-WATCH academic paper evaluation.

Covers:
- Granular CVE categories (RCE, Auth Bypass, Command Injection, Memory Corruption, Info Disclosure, XSS)
- Spatial-temporal corroboration densities (0, 1, 2, 3+ adjacent nodes)
- Network signal latency factors (>500ms ping latency)
- SCI-IoT Critical Security Gates (unauthenticated stream override)
- Protocol-layer red-team attacks (Replay, Timestamp skew, Corroboration velocity anomaly)
"""

import json
import os
from pathlib import Path

DATASET_PATH = Path(__file__).parent.parent / "eval" / "labeled_events.json"

def generate_expanded_scenarios() -> list[dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)

    # Ensure we start from existing 50
    assert len(existing) == 50, f"Expected 50 base events, found {len(existing)}"

    new_scenarios = [
        # --- Group A: Granular CVE & Vulnerability Differentiation (eval-051 to eval-065) ---
        {
            "id": "eval-051",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Exposed Uniview IP cam with remote command injection CVE and no auth",
            "event": {"camera_id": "EVAL_CAM_089", "event_type": "intrusion", "confidence": 0.88, "metadata": {"brand": "Uniview"}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2020-04-12"},
            "cve_categories": ["rce"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 20],
            "notes": "RCE (-30) + unauth (-30) + unknown_owner (-20) + outdated_firmware (-15) + no_corr (-10) = 0."
        },
        {
            "id": "eval-052",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "High-security airport terminal camera with recent XSS patch and 2 corroborators",
            "event": {"camera_id": "EVAL_CAM_090", "event_type": "perimeter_breach", "confidence": 0.94, "metadata": {"zone": "Terminal_2"}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "government", "last_patch_date": "2025-08-10"},
            "cve_categories": ["xss"],
            "max_cvss": 4.3,
            "corroborating_cameras": ["EVAL_CAM_091", "EVAL_CAM_092"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Low-severity XSS does not severely penalize authenticated government cam. Advanced score = 100."
        },
        {
            "id": "eval-053",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Hikvision camera subject to active Moobot botnet CVE-2021-36260 exploit",
            "event": {"camera_id": "EVAL_CAM_093", "event_type": "loitering", "confidence": 0.81, "metadata": {"cve": "CVE-2021-36260"}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "corporate", "last_patch_date": "2021-09-01"},
            "cve_categories": ["rce"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [30, 49],
            "notes": "Active RCE CVE + outdated firmware + no corroboration = 45 -> low_trust."
        },
        {
            "id": "eval-054",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Authenticated municipal junction camera with 3 corroborators and zero CVEs",
            "event": {"camera_id": "EVAL_CAM_094", "event_type": "vehicle_speeding", "confidence": 0.96, "metadata": {"speed_kmh": 85}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-06-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_095", "EVAL_CAM_096", "EVAL_CAM_097"],
            "expected_tier": "high_trust",
            "expected_score_range": [90, 100],
            "notes": "Strong multi-sensor corroboration cluster -> 100 high_trust."
        },
        {
            "id": "eval-055",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Unauthenticated private CCTV stream attempting corroboration rescue",
            "event": {"camera_id": "EVAL_CAM_098", "event_type": "unauthorized_access", "confidence": 0.89, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 0, "owner_type": "unknown", "last_patch_date": "2025-01-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_099", "EVAL_CAM_100"],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 49],
            "notes": "SCI-IoT Critical Gate auto-fails unauth camera (capped at 49) despite +20 corroboration bonus."
        },
        {
            "id": "eval-056",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "State highway surveillance camera with telecom backhaul and 1 corroborator",
            "event": {"camera_id": "EVAL_CAM_101", "event_type": "lane_violation", "confidence": 0.91, "metadata": {"highway": "NH48"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-04-15"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_102"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Telecom-verified ownership + auth + fresh patch = 100 high_trust."
        },
        {
            "id": "eval-057",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Axis camera with unauthenticated RTSP stream and memory corruption flaw",
            "event": {"camera_id": "EVAL_CAM_103", "event_type": "anomalous_motion", "confidence": 0.72, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "corporate", "last_patch_date": "2022-01-01"},
            "cve_categories": ["memory_corruption"],
            "max_cvss": 7.5,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 35],
            "notes": "Unauthenticated + memory corruption + outdated firmware + no corroboration = 20 -> low_trust."
        },
        {
            "id": "eval-058",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Commercial bank perimeter camera, authenticated, 1 info disclosure CVE",
            "event": {"camera_id": "EVAL_CAM_104", "event_type": "loitering", "confidence": 0.85, "metadata": {"atm_zone": True}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "corporate", "last_patch_date": "2025-03-01"},
            "cve_categories": ["info_disclosure"],
            "max_cvss": 5.3,
            "corroborating_cameras": ["EVAL_CAM_105"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 95],
            "notes": "Corporate + auth + low CVE deduction = 85 -> high_trust."
        },
        {
            "id": "eval-059",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Dahua DVR running ThroughTek Kalay SDK with remote access vulnerability",
            "event": {"camera_id": "EVAL_CAM_106", "event_type": "intrusion", "confidence": 0.93, "metadata": {"sdk": "Kalay_P2P"}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2021-08-01"},
            "cve_categories": ["auth_bypass"],
            "max_cvss": 9.6,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 35],
            "notes": "Auth bypass (-30) + unknown owner (-20) + outdated firmware (-15) + no corr (-10) = 25 -> low_trust."
        },
        {
            "id": "eval-060",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Indian Railways railway yard surveillance with dual-camera cross-corroboration",
            "event": {"camera_id": "EVAL_CAM_107", "event_type": "track_trespass", "confidence": 0.95, "metadata": {"yard": "Kurla_Carshed"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-07-20"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_108", "EVAL_CAM_109"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "Govt owned + authenticated + corroborated = 100 high_trust."
        },
        {
            "id": "eval-061",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Obsolete Bosch camera with 4 unpatched CVEs and default credentials",
            "event": {"camera_id": "EVAL_CAM_110", "event_type": "unauthorized_access", "confidence": 0.79, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 4, "owner_type": "unknown", "last_patch_date": "2017-03-01"},
            "cve_categories": ["rce", "auth_bypass", "memory_corruption"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 10],
            "notes": "Compounded critical risk factors -> 0 low_trust."
        },
        {
            "id": "eval-062",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Delhi traffic signal sensor, verified corporate fleet manager, 2 corroborators",
            "event": {"camera_id": "EVAL_CAM_111", "event_type": "red_light_violation", "confidence": 0.97, "metadata": {"junction": "AIIMS_Flyover"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "corporate", "last_patch_date": "2025-05-10"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_112", "EVAL_CAM_113"],
            "expected_tier": "high_trust",
            "expected_score_range": [90, 100],
            "notes": "Clean corporate sensor with multi-corroboration = 100 high_trust."
        },
        {
            "id": "eval-063",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Unauthenticated residential DVR discovered via Shodan banner scan",
            "event": {"camera_id": "EVAL_CAM_114", "event_type": "loitering", "confidence": 0.68, "metadata": {"port": 554}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2020-01-01"},
            "cve_categories": ["info_disclosure"],
            "max_cvss": 5.0,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [10, 40],
            "notes": "Unauthenticated (-30) + unknown owner (-20) + outdated firmware (-15) + no corr (-10) = 25 -> low_trust."
        },
        {
            "id": "eval-064",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Smart city command center thermal camera with authenticated stream",
            "event": {"camera_id": "EVAL_CAM_115", "event_type": "fire_smoke_detected", "confidence": 0.98, "metadata": {"thermal": True}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-09-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_116"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "High assurance thermal camera = 100 high_trust."
        },
        {
            "id": "eval-065",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Vulnerable IoT camera exhibiting severe network signal latency (>900ms ping)",
            "event": {"camera_id": "EVAL_CAM_117", "event_type": "anomalous_motion", "confidence": 0.74, "metadata": {"ping_ms": 950}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2021-01-01"},
            "cve_categories": ["rce"],
            "max_cvss": 9.0,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [15, 35],
            "notes": "RCE (-30) + unknown owner (-20) + outdated firmware (-15) + no corr (-10) = 25 -> low_trust."
        },

        # --- Group B: Multi-Camera Corroboration & Topology Edge Cases (eval-066 to eval-080) ---
        {
            "id": "eval-066",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Dense urban corridor with 4 corroborating authenticated nodes",
            "event": {"camera_id": "EVAL_CAM_118", "event_type": "crowd_surge", "confidence": 0.92, "metadata": {"density": "high"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-04-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_119", "EVAL_CAM_120", "EVAL_CAM_121", "EVAL_CAM_122"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "Massive corroboration density -> 100 high_trust."
        },
        {
            "id": "eval-067",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Attacker-controlled Sybil node cluster attempting to validate fake alert",
            "event": {"camera_id": "EVAL_CAM_123", "event_type": "explosive_hazard", "confidence": 0.99, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 2, "owner_type": "unknown", "last_patch_date": "2018-05-01"},
            "cve_categories": ["rce", "auth_bypass"],
            "max_cvss": 9.8,
            "corroborating_cameras": ["SYBIL_001", "SYBIL_002", "SYBIL_003"],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 49],
            "notes": "Critical gate blocks unauth source from ever exceeding 49 despite 3 Sybil corroborations."
        },
        {
            "id": "eval-068",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Telecom tower perimeter camera with authenticated RTSP and corporate owner",
            "event": {"camera_id": "EVAL_CAM_124", "event_type": "perimeter_breach", "confidence": 0.88, "metadata": {}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-06-15"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_125"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Single neutral corroborator + clean telecom posture = 100 high_trust."
        },
        {
            "id": "eval-069",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Hikvision NVR with hardcoded backdoors (CVE-2017-7921) on public IP",
            "event": {"camera_id": "EVAL_CAM_126", "event_type": "unauthorized_access", "confidence": 0.85, "metadata": {"cve": "CVE-2017-7921"}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2017-09-01"},
            "cve_categories": ["auth_bypass"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 20],
            "notes": "Classic backdoored Hikvision model -> 0 low_trust."
        },
        {
            "id": "eval-070",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Seaport container terminal monitoring camera with 2 corroborating PTZ cameras",
            "event": {"camera_id": "EVAL_CAM_127", "event_type": "container_tampering", "confidence": 0.94, "metadata": {"port": "JNPT_Mumbai"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-07-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_128", "EVAL_CAM_129"],
            "expected_tier": "high_trust",
            "expected_score_range": [90, 100],
            "notes": "Critical infrastructure camera with strong cross-verification = 100 high_trust."
        },
        {
            "id": "eval-071",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Isolated camera with 1 high CVE and unknown ownership in residential alley",
            "event": {"camera_id": "EVAL_CAM_130", "event_type": "loitering", "confidence": 0.73, "metadata": {}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2021-04-01"},
            "cve_categories": ["command_injection"],
            "max_cvss": 8.5,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [20, 45],
            "notes": "Command injection (-25) + unknown owner (-20) + outdated firmware (-15) + no corr (-10) = 30 -> low_trust."
        },
        {
            "id": "eval-072",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Hospital ICU corridor CCTV, authenticated with corporate ownership",
            "event": {"camera_id": "EVAL_CAM_131", "event_type": "fall_detected", "confidence": 0.91, "metadata": {"facility": "Apollo_Hospital"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "corporate", "last_patch_date": "2025-02-15"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_132"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Clean corporate sensor = 100 high_trust."
        },
        {
            "id": "eval-073",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Compromised camera streaming synthetic deepfake motion detection",
            "event": {"camera_id": "EVAL_CAM_133", "event_type": "active_shooter", "confidence": 0.99, "metadata": {"synthetic": True}},
            "device_profile": {"auth_required": False, "known_cve_count": 2, "owner_type": "unknown", "last_patch_date": "2019-01-01"},
            "cve_categories": ["rce"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 20],
            "notes": "Fabricated high-severity alert from completely insecure node -> 10 low_trust."
        },
        {
            "id": "eval-074",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Toll plaza ANPR camera with government ownership and 2 corroborating lane sensors",
            "event": {"camera_id": "EVAL_CAM_134", "event_type": "stolen_vehicle_match", "confidence": 0.97, "metadata": {"plate": "MH01AB1234"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-08-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_135", "EVAL_CAM_136"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "ANPR high assurance = 100 high_trust."
        },
        {
            "id": "eval-075",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Unauthenticated camera on public campus Wi-Fi with 2 critical CVEs",
            "event": {"camera_id": "EVAL_CAM_137", "event_type": "loitering", "confidence": 0.80, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 2, "owner_type": "corporate", "last_patch_date": "2020-06-01"},
            "cve_categories": ["auth_bypass", "rce"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 30],
            "notes": "Unauthenticated stream + RCE/Auth-bypass + outdated firmware = 15 -> low_trust."
        },
        {
            "id": "eval-076",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Subway entrance gate monitoring camera with 3 corroborating sensors",
            "event": {"camera_id": "EVAL_CAM_138", "event_type": "turnstile_jump", "confidence": 0.89, "metadata": {"station": "Churchgate"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-05-20"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_139", "EVAL_CAM_140", "EVAL_CAM_141"],
            "expected_tier": "high_trust",
            "expected_score_range": [90, 100],
            "notes": "Verified transit camera = 100 high_trust."
        },
        {
            "id": "eval-077",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Legacy Sony CCTV running unpatched RTSP stack from 2015",
            "event": {"camera_id": "EVAL_CAM_142", "event_type": "perimeter_breach", "confidence": 0.71, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 3, "owner_type": "unknown", "last_patch_date": "2015-11-01"},
            "cve_categories": ["rce", "memory_corruption"],
            "max_cvss": 9.5,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 15],
            "notes": "Severely obsolete hardware -> 0 low_trust."
        },
        {
            "id": "eval-078",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Petrochemical refinery flame detector camera with authenticated telecom link",
            "event": {"camera_id": "EVAL_CAM_143", "event_type": "flare_anomaly", "confidence": 0.96, "metadata": {"refinery": "RIL_Jamnagar"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-07-15"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_144", "EVAL_CAM_145"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "Critical industrial telemetry = 100 high_trust."
        },
        {
            "id": "eval-079",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Internet-exposed Pan-Tilt-Zoom camera manipulated by external brute force",
            "event": {"camera_id": "EVAL_CAM_146", "event_type": "unauthorized_access", "confidence": 0.84, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2021-03-01"},
            "cve_categories": ["auth_bypass"],
            "max_cvss": 9.1,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 30],
            "notes": "Unauth + auth bypass CVE = 15 -> low_trust."
        },
        {
            "id": "eval-080",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "National highway weigh-bridge camera with government ownership",
            "event": {"camera_id": "EVAL_CAM_147", "event_type": "overweight_truck", "confidence": 0.93, "metadata": {"weight_tons": 48.5}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-06-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_148"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Govt weighbridge camera = 100 high_trust."
        },

        # --- Group C: Temporal Decay & Signal Volatility Scenarios (eval-081 to eval-094) ---
        {
            "id": "eval-081",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Camera showing stale scan history with unpatched command injection",
            "event": {"camera_id": "EVAL_CAM_149", "event_type": "loitering", "confidence": 0.77, "metadata": {}},
            "device_profile": {"auth_required": True, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2020-08-01"},
            "cve_categories": ["command_injection"],
            "max_cvss": 8.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [20, 45],
            "notes": "Command injection + unknown owner + outdated firmware = 30 -> low_trust."
        },
        {
            "id": "eval-082",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Metro station platform edge camera with authenticated stream and 2 corroborators",
            "event": {"camera_id": "EVAL_CAM_150", "event_type": "yellow_line_cross", "confidence": 0.90, "metadata": {"platform": 2}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-08-15"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_151", "EVAL_CAM_152"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "Platform safety camera = 100 high_trust."
        },
        {
            "id": "eval-083",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Old D-Link IP camera running vulnerable web interface with auth bypass",
            "event": {"camera_id": "EVAL_CAM_153", "event_type": "intrusion", "confidence": 0.82, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 2, "owner_type": "unknown", "last_patch_date": "2018-09-01"},
            "cve_categories": ["auth_bypass"],
            "max_cvss": 9.4,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 20],
            "notes": "Severe vulnerability footprint = 0 low_trust."
        },
        {
            "id": "eval-084",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Municipal water reservoir perimeter camera with corporate fleet maintenance",
            "event": {"camera_id": "EVAL_CAM_154", "event_type": "perimeter_breach", "confidence": 0.92, "metadata": {"reservoir": "Bhatsa_Dam"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "corporate", "last_patch_date": "2025-07-10"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_155"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Clean corporate sensor = 100 high_trust."
        },
        {
            "id": "eval-085",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Unauthenticated camera streaming on open port 8080 with 1 RCE CVE",
            "event": {"camera_id": "EVAL_CAM_156", "event_type": "anomalous_motion", "confidence": 0.79, "metadata": {"port": 8080}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2021-02-01"},
            "cve_categories": ["rce"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 25],
            "notes": "RCE (-30) + unauth (-30) + unknown owner (-20) + outdated firmware (-15) + no corr (-10) = 0."
        },
        {
            "id": "eval-086",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "State police headquarters gate camera with 2 corroborating surveillance posts",
            "event": {"camera_id": "EVAL_CAM_157", "event_type": "unauthorized_parking", "confidence": 0.95, "metadata": {"hq": "Mumbai_Police_HQ"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-09-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_158", "EVAL_CAM_159"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "High assurance police HQ node = 100 high_trust."
        },
        {
            "id": "eval-087",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Residential garage camera with default vendor password and memory corruption",
            "event": {"camera_id": "EVAL_CAM_160", "event_type": "vehicle_intrusion", "confidence": 0.81, "metadata": {}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2019-12-01"},
            "cve_categories": ["memory_corruption"],
            "max_cvss": 7.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 30],
            "notes": "Unauth + memory corruption flaw = 20 -> low_trust."
        },
        {
            "id": "eval-088",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Airport cargo apron camera with authenticated telecom network connection",
            "event": {"camera_id": "EVAL_CAM_161", "event_type": "apron_trespass", "confidence": 0.93, "metadata": {"cargo_bay": 4}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-06-25"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_162", "EVAL_CAM_163"],
            "expected_tier": "high_trust",
            "expected_score_range": [90, 100],
            "notes": "Aviation apron camera = 100 high_trust."
        },
        {
            "id": "eval-089",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Unauthenticated smart doorbell stream with 2 CVEs exposed to Internet",
            "event": {"camera_id": "EVAL_CAM_164", "event_type": "loitering", "confidence": 0.69, "metadata": {"device": "smart_doorbell"}},
            "device_profile": {"auth_required": False, "known_cve_count": 2, "owner_type": "unknown", "last_patch_date": "2020-05-01"},
            "cve_categories": ["rce", "auth_bypass"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 15],
            "notes": "Insecure consumer IoT node = 0 low_trust."
        },
        {
            "id": "eval-090",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Central bank currency vault approach corridor CCTV, government managed",
            "event": {"camera_id": "EVAL_CAM_165", "event_type": "after_hours_access", "confidence": 0.98, "metadata": {"vault_id": "RBI_MUM_01"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "government", "last_patch_date": "2025-08-20"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_166", "EVAL_CAM_167"],
            "expected_tier": "high_trust",
            "expected_score_range": [95, 100],
            "notes": "Maximum security government facility = 100 high_trust."
        },
        {
            "id": "eval-091",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Compromised camera participating in Mirai botnet volumetric scan storm",
            "event": {"camera_id": "EVAL_CAM_168", "event_type": "crowd_surge", "confidence": 0.76, "metadata": {"traffic_surge": True}},
            "device_profile": {"auth_required": False, "known_cve_count": 3, "owner_type": "unknown", "last_patch_date": "2017-02-01"},
            "cve_categories": ["rce"],
            "max_cvss": 9.8,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 10],
            "notes": "Botnet zombie node -> 0 low_trust."
        },
        {
            "id": "eval-092",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "Smart city environmental monitoring camera with clean corporate posture",
            "event": {"camera_id": "EVAL_CAM_169", "event_type": "flood_water_rise", "confidence": 0.91, "metadata": {"river_level_m": 4.2}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "corporate", "last_patch_date": "2025-07-05"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_170"],
            "expected_tier": "high_trust",
            "expected_score_range": [80, 100],
            "notes": "Environmental monitoring sensor = 100 high_trust."
        },
        {
            "id": "eval-093",
            "label": "fabricated",
            "eval_mode": "direct",
            "description": "Exposed DVR on default port with unauthenticated HTTP management console",
            "event": {"camera_id": "EVAL_CAM_171", "event_type": "unauthorized_access", "confidence": 0.83, "metadata": {"port": 80}},
            "device_profile": {"auth_required": False, "known_cve_count": 1, "owner_type": "unknown", "last_patch_date": "2019-10-01"},
            "cve_categories": ["auth_bypass"],
            "max_cvss": 9.0,
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 25],
            "notes": "Unauthenticated HTTP DVR = 15 -> low_trust."
        },
        {
            "id": "eval-094",
            "label": "genuine",
            "eval_mode": "direct",
            "description": "University campus perimeter camera with authenticated telecom fiber feed",
            "event": {"camera_id": "EVAL_CAM_172", "event_type": "loitering", "confidence": 0.87, "metadata": {"gate": "University_Main_Gate"}},
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-08-01"},
            "cve_categories": [],
            "corroborating_cameras": ["EVAL_CAM_173", "EVAL_CAM_174"],
            "expected_tier": "high_trust",
            "expected_score_range": [90, 100],
            "notes": "Campus security camera with corroborated confirmation = 100 high_trust."
        },

        # --- Group D: Security Protocol & API Attack Scenarios (eval-095 to eval-100) ---
        {
            "id": "eval-095",
            "label": "fabricated",
            "eval_mode": "api_only",
            "description": "RED TEAM: Adversarial timestamp injection with 180s past clock skew",
            "event": {
                "camera_id": "EVAL_CAM_002",
                "event_type": "perimeter_breach",
                "confidence": 0.95,
                "detected_at": "2025-01-01T00:00:00Z",
                "metadata": {"attack": "stale_timestamp_injection"}
            },
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-01-15"},
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 0],
            "notes": "Blocked with HTTP 400 Bad Request by API timestamp freshness validator."
        },
        {
            "id": "eval-096",
            "label": "fabricated",
            "eval_mode": "api_only",
            "description": "RED TEAM: Replay flood attack resending identical detection payload 5 times",
            "event": {
                "camera_id": "EVAL_CAM_002",
                "event_type": "perimeter_breach",
                "confidence": 0.92,
                "idempotency_key": "fixed-idempotency-key-eval-096",
                "metadata": {"attack": "duplicate_idempotency_replay"}
            },
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-01-15"},
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 0],
            "notes": "Second submission blocked with HTTP 409 Conflict via idempotency key cache."
        },
        {
            "id": "eval-097",
            "label": "fabricated",
            "eval_mode": "api_only",
            "description": "RED TEAM: Corroboration velocity anomaly (>5 corroborations/hour between pair)",
            "event": {
                "camera_id": "EVAL_CAM_007",
                "event_type": "loitering",
                "confidence": 0.88,
                "metadata": {"attack": "collusive_velocity_spike"}
            },
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "corporate", "last_patch_date": "2025-01-01"},
            "corroborating_cameras": ["FAKE_CAM_VEL_01"],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 49],
            "notes": "Corroboration velocity tracker flags excessive pairing rate for audit."
        },
        {
            "id": "eval-098",
            "label": "fabricated",
            "eval_mode": "api_only",
            "description": "RED TEAM: Unauthenticated API request without X-API-Key header in production mode",
            "event": {
                "camera_id": "EVAL_CAM_002",
                "event_type": "perimeter_breach",
                "confidence": 0.90,
                "metadata": {"attack": "unauthenticated_post"}
            },
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "telecom", "last_patch_date": "2025-01-15"},
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 0],
            "notes": "Blocked with HTTP 401 Unauthorized when API key auth is enforced."
        },
        {
            "id": "eval-099",
            "label": "fabricated",
            "eval_mode": "decay_api_only",
            "description": "TIME DECAY: Unrescanned camera idle for 120 hours (2.5 half-lives) under time decay",
            "event": {
                "camera_id": "EVAL_CAM_DECAY_120H",
                "event_type": "perimeter_breach",
                "confidence": 0.85,
                "metadata": {"idle_hours": 120.0}
            },
            "device_profile": {"auth_required": True, "known_cve_count": 0, "owner_type": "corporate", "last_patch_date": "2025-01-01"},
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [10, 25],
            "notes": "Base score 80 decayed by exp(-ln2/48 * 120) = 80 * 0.176 = 14 -> low_trust."
        },
        {
            "id": "eval-100",
            "label": "fabricated",
            "eval_mode": "api_only",
            "description": "RED TEAM: Client-side metadata parameter injection attempting score override",
            "event": {
                "camera_id": "EVAL_CAM_001",
                "event_type": "loitering",
                "confidence": 0.99,
                "metadata": {"known_cve_count": 0, "auth_required": True, "owner_type": "government"}
            },
            "device_profile": {"auth_required": False, "known_cve_count": 2, "owner_type": "government", "last_patch_date": "2019-05-01"},
            "cve_categories": ["auth_bypass"],
            "corroborating_cameras": [],
            "expected_tier": "low_trust",
            "expected_score_range": [0, 30],
            "notes": "Backend ignores user-supplied metadata device fields and loads ground truth from DB."
        }
    ]

    combined = existing + new_scenarios
    assert len(combined) == 100, f"Expected exactly 100 events, got {len(combined)}"
    return combined

if __name__ == "__main__":
    dataset = generate_expanded_scenarios()
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"Successfully generated expanded dataset with {len(dataset)} scenarios in {DATASET_PATH.name}")
