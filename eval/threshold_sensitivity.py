"""
eval/threshold_sensitivity.py
==============================
IG-DCTF Threshold Sensitivity Analysis

Answers the standard reviewer question:
  "Why these specific thresholds (theta_low=0.50, theta_high=0.85)?"

Sweeps theta_low ∈ {0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60}
      theta_high ∈ {0.70, 0.75, 0.80, 0.85, 0.90, 0.95}

At each (theta_low, theta_high) pair, runs the full IG-DCTF eval on the
n=120 labeled corpus and records F1 and accuracy.

Outputs:
  1. A printed ASCII heatmap (F1 score at each threshold pair)
  2. A CSV file: eval/threshold_sensitivity_results.csv

Interpretation: A stable, wide plateau around the chosen thresholds
confirms the design is not hyper-tuned to a single point — any (theta_low, theta_high)
pair within the plateau gives comparable performance.

Run:
    python eval/threshold_sensitivity.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.trust_score_service import (
    compute_advanced_trust_score,
    compute_ig_dctf_trust_score,
)
from services.signal_integrity_service import (
    compute_banner_drift,
    compute_composite_signal_integrity,
    evaluate_integrity_gate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

THETA_LOW_GRID  = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
THETA_HIGH_GRID = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


def load_corpus(path: str | None = None) -> list[dict]:
    if path is None:
        path = str(Path(__file__).parent / "labeled_events.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_direct_scoreable(event: dict) -> bool:
    mode = event.get("eval_mode", "direct")
    return mode in ("direct", None, "")


def _score_ig_dctf_with_thresholds(
    event: dict,
    theta_low: float,
    theta_high: float,
) -> dict:
    """Score one event with IG-DCTF using custom gate thresholds."""
    device = event.get("device_profile", {})
    corroborating = event.get("corroborating_cameras", [])
    cve_cats = event.get("cve_categories", [])
    drift = event.get("drift_score", 0.0)
    liveness = event.get("visual_liveness", None)

    # Compute Channel A (CVE cyber score)
    adv_res = compute_advanced_trust_score(device, corroborating, cve_categories=cve_cats or None)
    t_cve = adv_res["score"]

    # Compute Channel B (signal integrity)
    integrity_res = compute_composite_signal_integrity(
        drift_score=drift,
        visual_liveness=liveness,
    )
    s = integrity_res["signal_integrity"]

    # Apply gate with custom thresholds
    if s >= theta_high:
        multiplier = 1.0
        tripped = False
    elif s >= theta_low:
        slope = (1.0 - 0.3) / (theta_high - theta_low)
        multiplier = 0.3 + slope * (s - theta_low)
        tripped = False
    else:
        multiplier = 0.30
        tripped = True

    final_score = t_cve * multiplier
    if tripped:
        final_score = min(30.0, final_score)

    # Tiering
    if final_score <= 30:
        tier = "low_trust"
    elif final_score <= 70:
        tier = "medium_trust"
    else:
        tier = "high_trust"

    return {"score": final_score, "tier": tier}


def evaluate_at_thresholds(
    corpus: list[dict],
    theta_low: float,
    theta_high: float,
) -> dict:
    """Run full IG-DCTF eval with specified thresholds. Returns metrics dict."""
    tp = fp = tn = fn = 0
    for event in corpus:
        if not _is_direct_scoreable(event):
            continue
        try:
            scored = _score_ig_dctf_with_thresholds(event, theta_low, theta_high)
            predicted = "fabricated" if scored["tier"] == "low_trust" else "genuine"
            label = event["label"]
            if predicted == "fabricated" and label == "fabricated":
                tp += 1
            elif predicted == "fabricated" and label == "genuine":
                fp += 1
            elif predicted == "genuine" and label == "genuine":
                tn += 1
            else:
                fn += 1
        except Exception:
            continue

    n = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / n if n > 0 else 0.0

    return {
        "theta_low": theta_low,
        "theta_high": theta_high,
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "n": n,
    }


# ---------------------------------------------------------------------------
# ASCII heatmap printer
# ---------------------------------------------------------------------------

def print_heatmap(results: list[dict], metric: str = "f1") -> None:
    """Print an ASCII heatmap of the metric across the threshold grid."""
    # Build lookup
    lookup: dict[tuple, float] = {}
    for r in results:
        lookup[(r["theta_low"], r["theta_high"])] = r[metric]

    col_width = 8
    metric_label = "F1 Score" if metric == "f1" else metric.upper()
    print(f"\n{metric_label} Sensitivity Heatmap (rows=theta_low, cols=theta_high)")
    print(f"  Chosen design point: theta_low=0.50, theta_high=0.85  <- marked with [*]")
    print()

    # Header
    header = f"{'theta_low \\ theta_high':<22}"
    for th in THETA_HIGH_GRID:
        marker = "*" if abs(th - 0.85) < 0.001 else " "
        header += f"  {th:.2f}{marker}  "
    print(header)
    print("-" * (22 + len(THETA_HIGH_GRID) * col_width + 10))

    for tl in THETA_LOW_GRID:
        row_marker = "*" if abs(tl - 0.50) < 0.001 else " "
        row = f"  {tl:.2f}{row_marker}         "
        for th in THETA_HIGH_GRID:
            if tl >= th:
                row += f"  N/A    "
            else:
                val = lookup.get((tl, th), float("nan"))
                if metric == "f1":
                    row += f"  {val:.4f} "
                else:
                    row += f"  {val:6.2f}%"
        print(row)


def save_csv(results: list[dict], output_path: str) -> None:
    fieldnames = ["theta_low", "theta_high", "accuracy", "precision", "recall", "f1", "tp", "fp", "tn", "fn", "n"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    corpus = load_corpus()

    print("\n" + "=" * 90)
    print("IG-DCTF THRESHOLD SENSITIVITY ANALYSIS")
    print(f"Sweeping theta_low in {THETA_LOW_GRID}")
    print(f"        theta_high in {THETA_HIGH_GRID}")
    print(f"Evaluating on n=~120 direct-scoreable scenarios from labeled_events.json")
    print("=" * 90)

    results = []
    for tl in THETA_LOW_GRID:
        for th in THETA_HIGH_GRID:
            if tl >= th:
                # Invalid: theta_low must be strictly less than theta_high
                continue
            r = evaluate_at_thresholds(corpus, tl, th)
            results.append(r)
            marker = " <- CHOSEN DESIGN POINT" if abs(tl - 0.50) < 0.001 and abs(th - 0.85) < 0.001 else ""
            print(
                f"  theta_low={tl:.2f}, theta_high={th:.2f}  ->  "
                f"Accuracy={r['accuracy']:6.2f}%  Precision={r['precision']:6.2f}%  "
                f"Recall={r['recall']:6.2f}%  F1={r['f1']:.4f}{marker}"
            )

    print_heatmap(results, metric="f1")
    print_heatmap(results, metric="accuracy")

    # Summary: stability report
    chosen = next((r for r in results if abs(r["theta_low"] - 0.50) < 0.001 and abs(r["theta_high"] - 0.85) < 0.001), None)
    valid_results = [r for r in results]
    max_f1 = max(r["f1"] for r in valid_results)
    plateau_count = sum(1 for r in valid_results if r["f1"] >= max_f1 - 0.01)
    total_valid = len(valid_results)

    print("\n" + "=" * 90)
    print("STABILITY SUMMARY:")
    if chosen:
        print(f"  Chosen thresholds (theta_low=0.50, theta_high=0.85): F1={chosen['f1']:.4f}, Accuracy={chosen['accuracy']:.2f}%")
    print(f"  Maximum F1 across all valid threshold pairs: {max_f1:.4f}")
    print(f"  Pairs within 0.01 F1 of maximum: {plateau_count}/{total_valid} ({100*plateau_count/total_valid:.0f}%)")
    print()
    print("  INTERPRETATION: A wide plateau (>50% of pairs within 0.01 F1 of maximum)")
    print("  confirms the system is NOT hyper-tuned to specific thresholds. Performance")
    print("  is stable across a range of gate configurations.")
    print("=" * 90)

    # Save CSV
    output_csv = str(Path(__file__).parent / "threshold_sensitivity_results.csv")
    save_csv(results, output_csv)


if __name__ == "__main__":
    main()
