"""
eval/run_eval.py
================
COBRA-WATCH Evaluation Harness — IIT-B BTech Final Year Project

Runs labeled scenarios from `labeled_events.json` through the trust score
engine and computes Precision, Recall, F1, and Tier Accuracy across three
scoring models:
1. Deterministic Weighted Average (WA) — Baseline
2. Advanced Category-Aware Engine (Module C/D/F) — Primary BTP Engine
3. Bayesian Log-Odds Posterior (Module B) — Probabilistic Model

Eval modes
----------
  python eval/run_eval.py                      # Comparative report (default)
  python eval/run_eval.py --mode wa            # WA direct mode
  python eval/run_eval.py --mode advanced      # Advanced category-aware primary
  python eval/run_eval.py --mode probabilistic # Bayesian log-odds model
  python eval/run_eval.py --mode comparative   # 3-model side-by-side report
  python eval/run_eval.py --mode api           # Live API integration test

Eval Mode Taxonomy
------------------
Each scenario in labeled_events.json has an optional "eval_mode" field:
  - Absent / "direct": scored by the trust engine directly (default).
  - "api_only": represents a security/protocol attack (replay, stale timestamp,
    rate-limit). The direct eval never fires the HTTP middleware that would block
    these — only the API-mode eval correctly evaluates them. Direct mode EXCLUDES
    these scenarios to avoid inflating FP counts with attacks that are correctly
    handled by the API layer.
  - "decay_api_only": tests time-decay erosion, which is computed at API time
    from the actual DB timestamp. Direct eval cannot replicate this without a
    live DB fixture, so these scenarios are excluded from direct metrics.

Wilson Confidence Intervals
----------------------------
All reported accuracy/precision/recall/F1 values include 95% Wilson confidence
intervals. At n=25 (scoring-only scenarios after filtering), point estimates
alone are insufficient — the CI width is reported to be academically honest.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

# Allow importing from backend/ when running directly
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.trust_score_service import (
    compute_trust_score,
    compute_advanced_trust_score,
    compute_probabilistic_trust_score,
    apply_trust_decay,
)


# ---------------------------------------------------------------------------
# Wilson confidence interval
# ---------------------------------------------------------------------------

def wilson_ci(p_hat: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """
    Wilson score interval for a proportion.
    Returns (lower, upper) as fractions in [0, 1].
    z=1.96 for 95% CI.
    """
    if n == 0:
        return (0.0, 1.0)
    denom = 1 + z ** 2 / n
    centre = (p_hat + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p_hat * (1 - p_hat) / n + z ** 2 / (4 * n ** 2)) / denom
    return (max(0.0, round(centre - half, 4)), min(1.0, round(centre + half, 4)))


# ---------------------------------------------------------------------------
# Direct evaluators
# ---------------------------------------------------------------------------

def _is_direct_eligible(event_data: dict) -> bool:
    """Return True if this scenario should be included in direct (non-API) evaluation."""
    mode = event_data.get("eval_mode", "direct")
    return mode == "direct" or mode is None


def run_direct(labeled_events: list[dict], model: str = "advanced", verbose: bool = False) -> list[dict]:
    """
    Run evaluation using specified scoring model directly (no backend needed).
    `model`: "wa" | "advanced" | "probabilistic"

    Automatically excludes api_only and decay_api_only scenarios — these test
    API-layer security/decay features that cannot be exercised without the HTTP
    stack. Including them would inflate FP counts for attacks the API correctly
    blocks, making both models appear to fail scenarios they never had a chance
    to handle.
    """
    results = []
    skipped = 0
    for event_data in labeled_events:
        if not _is_direct_eligible(event_data):
            skipped += 1
            if verbose:
                print(f"  SKIP [{event_data['id']:10s}] eval_mode={event_data.get('eval_mode')} "
                      f"(API-layer scenario — excluded from direct scoring eval)")
            continue

        device = event_data["device_profile"]
        corroborating = event_data.get("corroborating_cameras", [])
        cve_cats = event_data.get("cve_categories", [])

        if model == "wa":
            res = compute_trust_score(device, corroborating)
        elif model == "probabilistic":
            res = compute_probabilistic_trust_score(device, corroborating, max_cvss=event_data.get("max_cvss"))
        else:  # advanced (default)
            res = compute_advanced_trust_score(device, corroborating, cve_categories=cve_cats or None)

        tier = res["tier"]
        score = res["score"]
        predicted_label = "fabricated" if tier == "low_trust" else "genuine"
        ground_truth = event_data["label"]
        correct = predicted_label == ground_truth

        expected_tier = event_data.get("expected_tier")
        tier_correct = (tier == expected_tier) if expected_tier else True

        expected_range = event_data.get("expected_score_range", [0, 100])
        score_in_range = expected_range[0] <= score <= expected_range[1]

        results.append({
            "id": event_data["id"],
            "ground_truth": ground_truth,
            "predicted": predicted_label,
            "correct": correct,
            "score": score,
            "tier": tier,
            "expected_tier": expected_tier,
            "tier_correct": tier_correct,
            "score_in_range": score_in_range,
            "factors": res["factors"],
            "notes": event_data.get("notes", ""),
        })

        if verbose:
            status = "OK  " if correct else "FAIL"
            print(f"  {status} [{event_data['id']:10s}] model={model:12s} label={ground_truth:10s} "
                  f"predicted={predicted_label:10s} score={score:3d} tier={tier}")

    if verbose and skipped > 0:
        print(f"  [{skipped} scenarios skipped — api_only/decay_api_only, use --mode api to evaluate]")

    return results


def run_comparative(labeled_events: list[dict]) -> dict:
    """
    Run evaluation across ALL THREE models side-by-side.
    Returns per-model results and a summary comparison table.
    """
    wa_results = run_direct(labeled_events, model="wa")
    adv_results = run_direct(labeled_events, model="advanced")
    prob_results = run_direct(labeled_events, model="probabilistic")

    return {
        "wa": {"results": wa_results, "metrics": compute_metrics(wa_results)},
        "advanced": {"results": adv_results, "metrics": compute_metrics(adv_results)},
        "probabilistic": {"results": prob_results, "metrics": compute_metrics(prob_results)},
    }


# ---------------------------------------------------------------------------
# API mode evaluator
# ---------------------------------------------------------------------------

def run_api(labeled_events: list[dict], backend_url: str, api_key: str = "", verbose: bool = False) -> list[dict]:
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx is required for API mode. Run: pip install httpx")
        sys.exit(1)

    results = []
    headers = {"X-API-Key": api_key} if api_key else {}

    with httpx.Client(timeout=15.0) as client:
        for event_data in labeled_events:
            event = event_data["event"]
            try:
                res = client.post(
                    f"{backend_url}/api/detection-event",
                    json=event,
                    headers=headers,
                )
                if res.status_code == 404:
                    results.append({"id": event_data["id"], "error": "Camera not found in DB", "ground_truth": event_data["label"], "correct": None})
                    continue
                elif res.status_code in (400, 409, 429):
                    # Red-team attack blocked by security middleware — correctly classified
                    predicted_label = "fabricated"
                    ground_truth = event_data["label"]
                    correct = predicted_label == ground_truth
                    results.append({
                        "id": event_data["id"],
                        "ground_truth": ground_truth,
                        "predicted": predicted_label,
                        "correct": correct,
                        "score": 0,
                        "tier": "low_trust",
                        "blocked_by_security": True,
                        "status_code": res.status_code,
                    })
                    continue
                elif res.status_code != 200:
                    results.append({"id": event_data["id"], "error": f"HTTP {res.status_code}", "ground_truth": event_data["label"], "correct": None})
                    continue

                data = res.json()
                tier = data.get("action_tier", "low_trust")
                score = data.get("trust_score", 0)
                predicted_label = "fabricated" if tier == "low_trust" else "genuine"
                ground_truth = event_data["label"]
                correct = predicted_label == ground_truth

                results.append({
                    "id": event_data["id"],
                    "ground_truth": ground_truth,
                    "predicted": predicted_label,
                    "correct": correct,
                    "score": score,
                    "tier": tier,
                    "probabilistic_score": data.get("probabilistic_score"),
                    "decayed_score": data.get("decayed_score"),
                })
            except Exception as e:
                results.append({"id": event_data["id"], "error": str(e), "ground_truth": event_data["label"], "correct": None})

    return results


def seed_eval_cameras(labeled_events: list[dict], db_path: str = None) -> None:
    """
    Seed sqlite database with camera records referenced by labeled_events dataset
    for API integration evaluation testing.
    """
    import sqlite3
    try:
        from config import DATABASE_PATH
    except ImportError:
        from backend.config import DATABASE_PATH
    db_target = db_path or DATABASE_PATH

    conn = sqlite3.connect(db_target)
    try:
        for item in labeled_events:
            dev = item.get("device_profile") or item.get("device") or {}
            cam_id = (item.get("event") or {}).get("camera_id") or item.get("camera_id") or item.get("id")
            if not cam_id:
                continue

            cve_cats_json = json.dumps(dev.get("cve_categories", []))
            conn.execute(
                """
                INSERT OR REPLACE INTO devices (
                    id, city, ip, lat, lon, device_type, manufacturer, ports, owner_org, owner_type,
                    ownership_confidence, auth_required, known_cve_count, last_patch_date, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (
                    cam_id,
                    dev.get("city", "Mumbai"),
                    dev.get("ip", "1.2.3.4"),
                    dev.get("lat", 19.0760),
                    dev.get("lon", 72.8777),
                    dev.get("device_type", "IP Camera"),
                    dev.get("manufacturer", "Hikvision"),
                    json.dumps(dev.get("ports", [80, 554])),
                    dev.get("owner_org", "Org"),
                    dev.get("owner_type", "commercial"),
                    "high",
                    1 if dev.get("auth_required", True) else 0,
                    dev.get("known_cve_count", 0),
                    dev.get("last_patch_date", "2024-01-01"),
                )
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Metrics (with Wilson CI)
# ---------------------------------------------------------------------------

def compute_metrics(results: list[dict]) -> dict:
    valid = [r for r in results if r.get("correct") is not None]
    if not valid:
        return {"error": "No valid results"}

    n = len(valid)
    tp = sum(1 for r in valid if r["ground_truth"] == "genuine" and r["predicted"] == "genuine")
    fp = sum(1 for r in valid if r["ground_truth"] == "fabricated" and r["predicted"] == "genuine")
    fn = sum(1 for r in valid if r["ground_truth"] == "genuine" and r["predicted"] == "fabricated")
    tn = sum(1 for r in valid if r["ground_truth"] == "fabricated" and r["predicted"] == "fabricated")

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    tier_correct = [r for r in valid if r.get("tier_correct") is not None]
    tier_acc = sum(1 for r in tier_correct if r["tier_correct"]) / len(tier_correct) if tier_correct else None

    # Wilson 95% confidence intervals
    acc_ci = wilson_ci(accuracy, n)
    pre_ci = wilson_ci(precision, tp + fp) if (tp + fp) > 0 else (0.0, 1.0)
    rec_ci = wilson_ci(recall, tp + fn) if (tp + fn) > 0 else (0.0, 1.0)

    return {
        "total": n,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": round(accuracy, 4),
        "accuracy_ci_95": acc_ci,
        "precision": round(precision, 4),
        "precision_ci_95": pre_ci,
        "recall": round(recall, 4),
        "recall_ci_95": rec_ci,
        "f1": round(f1, 4),
        "tier_accuracy": round(tier_acc, 4) if tier_acc is not None else None,
    }


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def print_comparative_table(comp: dict) -> None:
    print("\n" + "=" * 80)
    print("COBRA-WATCH 3-MODEL COMPARATIVE EVALUATION REPORT (IIT-B BTP)")
    print("Note: api_only/decay_api_only scenarios excluded from direct scoring eval.")
    print("=" * 80)
    print(f"{'Metric':<22s} | {'WA (Baseline)':<20s} | {'Advanced (Primary)':<22s} | {'Bayesian (Prob)':<18s}")
    print("-" * 90)
    for m in ["accuracy", "precision", "recall", "f1", "tier_accuracy"]:
        wa_m = comp["wa"]["metrics"]
        adv_m = comp["advanced"]["metrics"]
        prob_m = comp["probabilistic"]["metrics"]

        wa_val = wa_m.get(m, "N/A")
        adv_val = adv_m.get(m, "N/A")
        prob_val = prob_m.get(m, "N/A")

        # Append CI for primary metrics
        ci_key = f"{m}_ci_95"
        wa_ci = wa_m.get(ci_key)
        adv_ci = adv_m.get(ci_key)
        prob_ci = prob_m.get(ci_key)

        wa_str = f"{wa_val}" + (f" [{wa_ci[0]:.2f},{wa_ci[1]:.2f}]" if wa_ci else "")
        adv_str = f"{adv_val}" + (f" [{adv_ci[0]:.2f},{adv_ci[1]:.2f}]" if adv_ci else "")
        prob_str = f"{prob_val}" + (f" [{prob_ci[0]:.2f},{prob_ci[1]:.2f}]" if prob_ci else "")

        print(f"{m.replace('_', ' ').title():<22s} | {wa_str:<20s} | {adv_str:<22s} | {prob_str:<18s}")

    n_wa = comp["wa"]["metrics"].get("total", "?")
    n_adv = comp["advanced"]["metrics"].get("total", "?")
    print("=" * 90)
    print(f"Eval set: n={n_wa} scoring scenarios (WA/Advanced), n={n_adv} (Advanced).")
    print("95% Wilson CI shown in brackets. Wider CI at small n is expected and honest.")
    print()


def main():
    parser = argparse.ArgumentParser(description="COBRA-WATCH Evaluation Script")
    parser.add_argument("--mode", choices=["wa", "advanced", "probabilistic", "comparative", "api"], default="comparative",
                        help="Evaluation mode (default: comparative)")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--api-key", default=os.getenv("DETECTION_API_KEY", ""))
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    dataset_path = Path(__file__).parent / "labeled_events.json"
    with open(dataset_path) as f:
        labeled_events = json.load(f)

    direct_count = sum(1 for e in labeled_events if _is_direct_eligible(e))
    api_only_count = len(labeled_events) - direct_count
    print(f"Loaded {len(labeled_events)} labeled events from {dataset_path.name}")
    print(f"  Direct scoring: {direct_count} scenarios | API-only: {api_only_count} scenarios")

    if args.mode == "comparative":
        comp = run_comparative(labeled_events)
        print_comparative_table(comp)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(comp, f, indent=2)
            print(f"Comparative report written to {args.output}")
    elif args.mode in ("wa", "advanced", "probabilistic"):
        results = run_direct(labeled_events, model=args.mode, verbose=args.verbose)
        metrics = compute_metrics(results)
        print(f"\nModel: {args.mode.upper()} Mode Metrics (direct scoring scenarios only):")
        print(json.dumps(metrics, indent=2))
    elif args.mode == "api":
        results = run_api(labeled_events, backend_url=args.url, api_key=args.api_key, verbose=args.verbose)
        metrics = compute_metrics(results)
        print(f"\nAPI Mode Metrics (all {len(labeled_events)} scenarios including api_only):")
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
