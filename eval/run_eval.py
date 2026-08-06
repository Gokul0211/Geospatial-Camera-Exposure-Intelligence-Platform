"""
eval/run_eval.py
================
COBRA-WATCH Evaluation Script — Phase 4

Runs each labeled event in `labeled_events.json` through the real trust score
pipeline and computes precision/recall/F1 for the system's ability to correctly
classify genuine vs. fabricated detection events.

Two evaluation modes
---------------------
1. DIRECT (default, no backend needed)
   Calls `compute_trust_score()` directly with the device_profile and
   corroborating_cameras from the JSON file. Fast, reproducible, no DB needed.
   Use this for CI and report generation.

2. API mode (--mode api)
   POSTs each event to a running backend via /api/detection-event.
   Tests the full pipeline including DB, corroboration lookup, and auth.
   Requires: backend running + DETECTION_API_KEY set if auth is enabled.

Classification task
--------------------
Ground truth label: "genuine" vs "fabricated"
Predicted class: based on action_tier — "low_trust" → predicted fabricated,
                 "high_trust" | "medium_trust" → predicted genuine.

Rationale: low_trust events have enough bad device signals that they are likely
from devices an attacker would prefer to use (unauthenticated, unknown owner,
unpatched CVEs) — or they're fabricated events that couldn't survive scrutiny.

Usage
-----
  # From the project root
  python eval/run_eval.py                  # direct mode (recommended)
  python eval/run_eval.py --mode api       # API mode
  python eval/run_eval.py --mode api --url http://localhost:8000
  python eval/run_eval.py --verbose        # show per-event details
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow importing from backend/ when running directly
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ---------------------------------------------------------------------------
# Core evaluation logic (direct mode)
# ---------------------------------------------------------------------------

def run_direct(labeled_events: list[dict], verbose: bool = False) -> dict:
    """
    Run evaluation by calling compute_trust_score() directly.
    No backend, no DB, no network. 100% reproducible.
    """
    from services.trust_score_service import compute_trust_score

    results = []
    for event_data in labeled_events:
        device = event_data["device_profile"]
        corroborating = event_data.get("corroborating_cameras", [])
        trust_result = compute_trust_score(device, corroborating)

        predicted_label = (
            "fabricated" if trust_result["tier"] == "low_trust" else "genuine"
        )
        ground_truth = event_data["label"]
        correct = predicted_label == ground_truth

        # Score range validation
        score = trust_result["score"]
        expected_range = event_data.get("expected_score_range", [0, 100])
        score_in_range = expected_range[0] <= score <= expected_range[1]

        results.append({
            "id": event_data["id"],
            "ground_truth": ground_truth,
            "predicted": predicted_label,
            "correct": correct,
            "score": score,
            "tier": trust_result["tier"],
            "factors": trust_result["factors"],
            "expected_tier": event_data.get("expected_tier"),
            "tier_correct": trust_result["tier"] == event_data.get("expected_tier"),
            "score_in_range": score_in_range,
            "expected_score_range": expected_range,
            "notes": event_data.get("notes", ""),
        })

        if verbose:
            status = "OK" if correct else "FAIL"
            print(f"  {status} [{event_data['id']}] label={ground_truth} "
                  f"predicted={predicted_label} score={score} tier={trust_result['tier']}")
            if not correct:
                print(f"    MISMATCH: {event_data.get('notes', '')}")

    return results


# ---------------------------------------------------------------------------
# API mode evaluation
# ---------------------------------------------------------------------------

def run_api(labeled_events: list[dict], backend_url: str, api_key: str = "",
            verbose: bool = False) -> list[dict]:
    """
    Run evaluation by POSTing to the real backend API.
    Requires backend to be running.
    """
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx is not installed. Run: pip install httpx")
        sys.exit(1)

    results = []
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

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
                    # camera_id not in DB — skip and note
                    results.append({
                        "id": event_data["id"],
                        "error": f"camera_id '{event['camera_id']}' not found in DB "
                                 "(seed the eval cameras first)",
                        "ground_truth": event_data["label"],
                        "correct": None,
                    })
                    if verbose:
                        print(f"  SKIP [{event_data['id']}] — camera not in DB")
                    continue
                elif res.status_code != 200:
                    results.append({
                        "id": event_data["id"],
                        "error": f"HTTP {res.status_code}: {res.text[:100]}",
                        "ground_truth": event_data["label"],
                        "correct": None,
                    })
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
                    "alert_id": data.get("alert_id"),
                    "notes": event_data.get("notes", ""),
                })

                if verbose:
                    status = "OK" if correct else "FAIL"
                    print(f"  {status} [{event_data['id']}] label={ground_truth} "
                          f"predicted={predicted_label} score={score} tier={tier}")

            except Exception as e:
                results.append({
                    "id": event_data["id"],
                    "error": str(e),
                    "ground_truth": event_data["label"],
                    "correct": None,
                })

    return results


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_metrics(results: list[dict]) -> dict:
    """
    Compute precision, recall, F1 for the genuine/fabricated classification task.
    Positive class = 'genuine' (we care most about not missing real events).
    Negative class = 'fabricated'.
    """
    valid = [r for r in results if r.get("correct") is not None]
    if not valid:
        return {"error": "No valid results to compute metrics"}

    tp = sum(1 for r in valid if r["ground_truth"] == "genuine" and r["predicted"] == "genuine")
    fp = sum(1 for r in valid if r["ground_truth"] == "fabricated" and r["predicted"] == "genuine")
    fn = sum(1 for r in valid if r["ground_truth"] == "genuine" and r["predicted"] == "fabricated")
    tn = sum(1 for r in valid if r["ground_truth"] == "fabricated" and r["predicted"] == "fabricated")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(valid)

    # Tier accuracy (for direct mode only, where we have expected_tier)
    tier_correct = [r for r in valid if r.get("tier_correct") is not None]
    tier_accuracy = sum(1 for r in tier_correct if r["tier_correct"]) / len(tier_correct) if tier_correct else None

    return {
        "total": len(valid),
        "skipped": len(results) - len(valid),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tier_accuracy": round(tier_accuracy, 4) if tier_accuracy is not None else None,
    }


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def print_report(results: list[dict], metrics: dict, mode: str) -> None:
    print("\n" + "=" * 65)
    print("COBRA-WATCH Trust Score Evaluation Report")
    print(f"Mode: {mode.upper()}")
    print("=" * 65)

    print("\nPer-event results:")
    for r in results:
        if r.get("error"):
            print(f"  WARN [{r['id']}] ERROR: {r['error']}")
            continue
        status = "OK  " if r["correct"] else "FAIL"
        tier_ok = "OK" if r.get("tier_correct", True) else "!!"
        score_ok = "OK" if r.get("score_in_range", True) else "!!"
        print(
            f"  {status} [{r['id']:10s}] "
            f"label={r['ground_truth']:10s} "
            f"predicted={r['predicted']:10s} "
            f"score={r.get('score', '?'):3}  "
            f"tier={r.get('tier', '?'):12s} "
            f"tier{tier_ok} score_range{score_ok}"
        )
        if not r["correct"]:
            print(f"       NOTE: {r.get('notes', '')}")

    print("\nClassification Metrics (genuine vs. fabricated):")
    print(f"  Accuracy  : {metrics.get('accuracy', 'N/A')}")
    print(f"  Precision : {metrics.get('precision', 'N/A')}  (TP={metrics.get('tp')} FP={metrics.get('fp')})")
    print(f"  Recall    : {metrics.get('recall', 'N/A')}  (FN={metrics.get('fn')} TN={metrics.get('tn')})")
    print(f"  F1 Score  : {metrics.get('f1', 'N/A')}")
    if metrics.get("tier_accuracy") is not None:
        print(f"  Tier Match: {metrics['tier_accuracy']}  (exact action_tier correctness)")
    if metrics.get("skipped", 0) > 0:
        print(f"  Skipped   : {metrics['skipped']} events (camera not in DB)")
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="COBRA-WATCH Evaluation Script")
    parser.add_argument("--mode", choices=["direct", "api"], default="direct",
                        help="Evaluation mode: direct (no backend) or api (live backend)")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Backend URL for API mode")
    parser.add_argument("--api-key", default=os.getenv("DETECTION_API_KEY", ""),
                        help="API key for POST /api/detection-event (API mode only)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-event details during evaluation")
    parser.add_argument("--output", "-o", default=None,
                        help="Write results JSON to this file")
    args = parser.parse_args()

    dataset_path = Path(__file__).parent / "labeled_events.json"
    with open(dataset_path) as f:
        labeled_events = json.load(f)

    print(f"Loaded {len(labeled_events)} labeled events from {dataset_path}")

    if args.mode == "direct":
        print("Running in DIRECT mode (calling compute_trust_score() directly)...")
        results = run_direct(labeled_events, verbose=args.verbose)
    else:
        print(f"Running in API mode against {args.url}...")
        results = run_api(labeled_events, backend_url=args.url,
                          api_key=args.api_key, verbose=args.verbose)

    metrics = compute_metrics(results)
    print_report(results, metrics, args.mode)

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"metrics": metrics, "results": results}, f, indent=2)
        print(f"Results written to {args.output}")

    # Exit non-zero if any events were misclassified
    misclassified = sum(1 for r in results if r.get("correct") is False)
    sys.exit(misclassified)


if __name__ == "__main__":
    main()
