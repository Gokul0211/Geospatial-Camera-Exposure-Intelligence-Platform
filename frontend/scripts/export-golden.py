"""
Run the Python implementation on random vectors plus the threshold edges and write
tests/fixtures/gate_golden.json. The Vitest parity test asserts the TypeScript port matches.

    python frontend/scripts/export-golden.py

Reads only backend code; touches no network and no database.
"""
import json
import os
import random
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))

from services.signal_integrity_service import (  # noqa: E402
    compute_composite_signal_integrity,
    compute_visual_liveness,
    evaluate_integrity_gate,
    compute_banner_drift,
)

random.seed(20261014)
cases = []


def add(t_cve, drift, freeze, quality, spec):
    live = None
    if freeze is not None:
        live = compute_visual_liveness(freeze, quality, spec)["liveness_score"]
    s = compute_composite_signal_integrity(drift, live)["signal_integrity"]
    g = evaluate_integrity_gate(s)
    final = int(round(t_cve * g["multiplier"]))
    if g["hard_cap"] is not None:
        final = min(g["hard_cap"], final)
    final = max(0, min(100, final))
    cases.append({
        "t_cve": t_cve, "drift": drift, "freeze": freeze, "quality": quality, "spec": spec,
        "liveness": live, "s": s, "multiplier": g["multiplier"], "status": g["gate_status"],
        "tripped": g["gate_tripped"], "hard_cap": g["hard_cap"], "t_final": final,
    })


for _ in range(200):
    add(
        random.randint(0, 100),
        round(random.random(), 4),
        random.choice([None, True, False]),
        round(random.random(), 4),
        random.choice([True, False]),
    )

# threshold edges: s exactly at 0.5, 0.85 and neighbours, via drift with Tier 2 unavailable
for d in (0.0, 0.15, 0.1500, 0.4999, 0.5, 0.5001, 1.0):
    for t in (0, 1, 50, 99, 100):
        add(t, d, None, 0.0, False)

# .5 rounding ties for int(round(T * G))
for t in (5, 15, 25, 35, 45, 55, 65, 75, 85, 95):
    for d in (0.35, 0.4, 0.45):
        add(t, d, None, 0.0, False)

banner = []
base = {"resolution": "1080p", "codec": "h264", "firmware_version": "5.4.1", "http_server": "dnvrs-webs", "product_string": "hikvision", "open_ports": [80, 554, 8000]}
variants = [
    {}, {"resolution": "480p"}, {"resolution": "4k"}, {"http_server": "nginx"}, {"firmware_version": "5.3.0"},
    {"open_ports": [80, 554]}, {"open_ports": [22, 23]}, {"codec": "h265"}, {"product_string": "unknown"},
    {"resolution": "480p", "http_server": "nginx", "firmware_version": "1.0", "open_ports": [22], "codec": "mjpeg", "product_string": "dahua"},
]
for v in variants:
    cur = {**base, **v}
    r = compute_banner_drift(base, cur)
    banner.append({"baseline": base, "current": cur, "drift": r["drift_score"], "distances": r["component_distances"]})

out = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "gate_golden.json")
with open(out, "w") as f:
    json.dump({"cases": cases, "banner": banner}, f, indent=1)
print(f"wrote {len(cases)} gate cases and {len(banner)} banner cases to {os.path.relpath(out)}")
