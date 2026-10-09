"""
paper/scripts/compute_results.py
================================
Single source of truth for every number quoted in the paper.

Convention (used everywhere in the paper):
  * Positive class  = "fabricated"  (alert from an untrustworthy device/feed)
  * Predicted positive <=> final tier == "low_trust"  (score < 50)
  * Precision = TP/(TP+FP), Recall = TP/(TP+FN), 95% Wilson intervals.

Run from the repository root:
    python paper/scripts/compute_results.py

Writes paper/data/results.json and prints a summary.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.trust_score_service import (  # noqa: E402
    compute_advanced_trust_score,
    compute_ig_dctf_trust_score,
    compute_probabilistic_trust_score,
    compute_trust_score,
)
from services.signal_integrity_service import (  # noqa: E402
    compute_composite_signal_integrity,
    evaluate_integrity_gate,
)

CORPUS = ROOT / "eval" / "labeled_events.json"
OUT = ROOT / "paper" / "data" / "results.json"
OUT_MD = ROOT / "paper" / "results.md"
sys.path.insert(0, str(ROOT))


def _load_module(name: str, path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- stats
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value (b, c = discordant counts)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def metrics(rows: list[dict]) -> dict:
    tp = sum(r["y"] == 1 and r["p"] == 1 for r in rows)
    fp = sum(r["y"] == 0 and r["p"] == 1 for r in rows)
    tn = sum(r["y"] == 0 and r["p"] == 0 for r in rows)
    fn = sum(r["y"] == 1 and r["p"] == 0 for r in rows)
    n = len(rows)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / n if n else 0.0
    return {
        "n": n, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "accuracy": acc, "accuracy_ci": wilson(tp + tn, n),
        "precision": prec, "precision_ci": wilson(tp, tp + fp),
        "recall": rec, "recall_ci": wilson(tp, tp + fn),
        "specificity": spec, "specificity_ci": wilson(tn, tn + fp),
        "f1": f1,
    }


# --------------------------------------------------------------------------- scorers
def tier_of(score: float) -> str:
    return "high_trust" if score >= 80 else "medium_trust" if score >= 50 else "low_trust"


def score_wa(e):
    return compute_trust_score(e["device_profile"], e.get("corroborating_cameras", []))["score"]


def score_adv(e):
    return compute_advanced_trust_score(
        e["device_profile"], e.get("corroborating_cameras", []),
        cve_categories=e.get("cve_categories") or None)["score"]


def score_bayes(e):
    return compute_probabilistic_trust_score(
        e["device_profile"], e.get("corroborating_cameras", []),
        max_cvss=e.get("max_cvss"))["score"]


def score_ig(e):
    return compute_ig_dctf_trust_score(
        e["device_profile"], e.get("corroborating_cameras", []),
        drift_score=e.get("drift_score", 0.0),
        visual_liveness=e.get("visual_liveness"),
        cve_categories=e.get("cve_categories") or None)["final_trust_score"]


def score_channel_b_only(e):
    s = compute_composite_signal_integrity(e.get("drift_score", 0.0), e.get("visual_liveness"))
    g = evaluate_integrity_gate(s["signal_integrity"])
    return int(round(100 * g["multiplier"]))


def score_additive(e, penalty: float = 70.0):
    """Additive fusion control: T = T_cve - P*(1 - SignalIntegrity).

    P = 70 gives the same worst-case end point as the multiplicative gate
    (a perfect device with a fully failed Channel B lands on 30), so the two
    fusion rules differ only in how Channel A can compensate for Channel B.
    """
    s = compute_composite_signal_integrity(e.get("drift_score", 0.0), e.get("visual_liveness"))
    return max(0, int(round(score_adv(e) - penalty * (1 - s["signal_integrity"]))))


def score_ig_thresholds(e, th_low: float, th_high: float):
    """IG-DCTF with custom gate thresholds; identical arithmetic to the deployed scorer."""
    t_cve = score_adv(e)
    s = compute_composite_signal_integrity(e.get("drift_score", 0.0), e.get("visual_liveness"))["signal_integrity"]
    if s >= th_high:
        g = 1.0
    elif s >= th_low:
        g = 0.3 + 0.7 * (s - th_low) / (th_high - th_low)
    else:
        g = 0.3
    return min(30, int(round(t_cve * g))) if s < th_low else int(round(t_cve * g))


def run(corpus, scorer):
    rows = []
    for e in corpus:
        sc = scorer(e)
        rows.append({
            "id": e["id"], "y": int(e["label"] == "fabricated"),
            "p": int(tier_of(sc) == "low_trust"), "score": sc,
            "has_signal": bool(e.get("drift_score", 0.0) > 0 or e.get("visual_liveness") is not None),
        })
    return rows


def tier1_benchmark() -> dict:
    """Re-run the 100-case Tier-1 synthetic mutation corpus (threshold 0.15) and keep the raw counts."""
    from services.signal_integrity_service import compute_banner_drift
    mod = _load_module("t1", ROOT / "backend" / "tests" / "test_banner_drift_benchmark.py")
    corpus = mod._generate_synthetic_benchmark_corpus()
    cats: dict[str, dict] = {}
    rows = []
    t0 = time.perf_counter()
    for c in corpus:
        d = compute_banner_drift(c["baseline"], c["current"])["drift_score"]
        rows.append({"y": int(c["expected_anomalous"]), "p": int(d >= 0.15)})
        k = cats.setdefault(c["category"], {"n": 0, "drift": d, "detected": 0})
        k["n"] += 1
        k["detected"] += int(d >= 0.15)
    ms = (time.perf_counter() - t0) * 1000 / len(corpus)
    m = metrics(rows)
    m["ms_per_device"] = ms
    m["categories"] = cats
    m["distinct_cases"] = len({json.dumps([c["baseline"], c["current"]], sort_keys=True) for c in corpus})
    return m


def tier2_benchmark() -> dict:
    """Re-run the 80-scenario Tier-2 corpus; also push the final liveness through the gate end-to-end."""
    from video_pipeline.liveness_detector import FrameLivenessTracker
    mod = _load_module("t2", ROOT / "backend" / "tests" / "test_liveness_freeze_benchmark.py")
    corpus = mod._build_scenario_corpus()
    rows, per_cat, lat = [], {}, []
    for sc in corpus:
        tr = FrameLivenessTracker(sc["id"], window_size=30, freeze_dist_threshold=1,
                                  consecutive_freeze_frames=25,
                                  declared_resolution=sc.get("declared_resolution"))
        det, det_frame, min_l = False, None, 1.0
        for i, fr in enumerate(sc["frames"]):
            r = tr.process_frame(fr, i, float(i))
            min_l = min(min_l, r["liveness_score"])
            if r["liveness_score"] < 0.70 or (i >= 10 and r.get("quality_drift", 0) > 0.70) or r.get("spec_mismatch"):
                det = True
                det_frame = i if det_frame is None else det_frame
        rows.append({"y": int(sc["expected_anomaly"]), "p": int(det)})
        if sc["expected_anomaly"] and det and det_frame is not None:
            lat.append(max(0, det_frame - sc.get("attack_start_frame", 0)))
        # end-to-end: perfect Channel A (T_cve = 100), zero banner drift, Tier-2 liveness = min over the run
        g = evaluate_integrity_gate(compute_composite_signal_integrity(0.0, min_l)["signal_integrity"])
        t_final = min(30, int(round(100 * g["multiplier"]))) if g["gate_tripped"] else int(round(100 * g["multiplier"]))
        c = per_cat.setdefault(sc["category"], {"n": 0, "flagged": 0, "low_trust": 0, "min_L": [], "t_final": []})
        c["n"] += 1
        c["flagged"] += int(det)
        c["low_trust"] += int(t_final < 50)
        c["min_L"].append(min_l)
        c["t_final"].append(t_final)
    m = metrics(rows)
    m["mean_latency_frames"] = sum(lat) / len(lat) if lat else 0.0
    for c in per_cat.values():
        c["mean_min_L"] = sum(c.pop("min_L")) / c["n"]
        c["mean_t_final"] = sum(c.pop("t_final")) / c["n"]
    m["categories"] = per_cat
    return m


def single_factor_table() -> list[dict]:
    """Effect of a single Tier-2 failure (Drift = 0, T_cve = 100) with weights (.5, .3, .2)."""
    from services.signal_integrity_service import compute_visual_liveness
    out = []
    for name, kw in [("freeze", dict(freeze_flag=True)),
                     ("severe blur (q=1)", dict(quality_drift=1.0)),
                     ("spec mismatch", dict(spec_mismatch_flag=True)),
                     ("all three", dict(freeze_flag=True, quality_drift=1.0, spec_mismatch_flag=True))]:
        L = compute_visual_liveness(**kw)["liveness_score"]
        g = evaluate_integrity_gate(L)
        out.append({"failure": name, "L": L, "G": g["multiplier"],
                    "T_final": int(round(100 * g["multiplier"])), "status": g["gate_status"]})
    return out


def write_markdown(r: dict) -> None:
    f = lambda x: f"{x:.4f}"
    ci = lambda t: f"[{t[0]:.3f}, {t[1]:.3f}]"
    L = ["# COBRA-WATCH / IG-DCTF: verified results", "",
         "_Generated by `paper/scripts/compute_results.py`. Do not edit by hand; re-run the script to refresh "
         "this file and `data/results.json`._", "",
         "**Convention (used everywhere in the paper).** Positive class = `fabricated` (alert from an untrustworthy "
         "device or feed). A scenario is predicted positive iff the final tier is `low_trust` (score < 50). "
         "Intervals are 95% Wilson.", "",
         f"**Corpus.** {r['n_direct']} directly scoreable scenarios from `eval/labeled_events.json` "
         f"({r['n_fabricated']} fabricated, {r['n_genuine']} genuine); only {r['n_with_signal_fields']} carry "
         "Channel-B fields (drift and/or liveness). The 10 API-only scenarios are excluded.", "",
         "## 1. Four-model comparison", "",
         "| Model | Acc. | Prec. | Recall | Spec. | F1 | TP | FP | TN | FN |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, m in r["comparison"].items():
        L.append(f"| {k} | {f(m['accuracy'])} {ci(m['accuracy_ci'])} | {f(m['precision'])} | "
                 f"{f(m['recall'])} {ci(m['recall_ci'])} | {f(m['specificity'])} | {f(m['f1'])} | "
                 f"{m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} |")
    mc = r["mcnemar_ig_vs_adv"]
    L += ["", f"Exact McNemar, IG-DCTF vs. Advanced (CVE-only): IG-DCTF-only correct = {mc['ig_only_correct']}, "
          f"Advanced-only correct = {mc['adv_only_correct']}, p = {mc['p_value']:.2e}.",
          f"IG-DCTF errors: {', '.join(r['ig_errors'])}. Advanced errors: {len(r['adv_errors'])} scenarios.", "",
          "### Stratified by presence of Channel-B fields", "",
          "| Model | with Channel B (n=30): Acc. / F1 | without (n=90): Acc. / F1 |", "|---|---|---|"]
    for k, s in r["stratified"].items():
        w, wo = s["with_signal"], s["without_signal"]
        L.append(f"| {k} | {w['accuracy']:.3f} / {w['f1']:.3f} | {wo['accuracy']:.3f} / {wo['f1']:.3f} |")
    L += ["", "## 2. Ablation and fusion-rule control", "",
          "| Variant | Acc. | Recall | F1 | TP | FP | TN | FN |", "|---|---|---|---|---|---|---|---|"]
    for k, m in r["ablation"].items():
        L.append(f"| {k} | {f(m['accuracy'])} | {f(m['recall'])} | {f(m['f1'])} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} |")
    L += ["", "Additive control: `T = T_cve - 70 (1 - s)`, chosen so a perfect device with a fully failed Channel B "
          "also lands on 30 (same end point as the multiplicative gate).", "",
          "## 3. Gate-threshold sweep (same tier cut-offs as Section 1)", "",
          f"Best F1 = {f(r['sweep_summary']['best_f1'])}; chosen (0.50, 0.85) F1 = {f(r['sweep_summary']['chosen_f1'])}; "
          f"{r['sweep_summary']['within_0.01_of_best']}/{r['sweep_summary']['total']} grid points within 0.01 of the best. "
          "The surface is flat because every labelled scenario sits far from both thresholds "
          "(genuine s >= 0.686, fabricated s <= 0.38); the corpus therefore cannot *select* the thresholds.", ""]
    t1 = r["tier1"]
    L += ["## 4. Tier-1 synthetic benchmark (banner drift, threshold 0.15)", "",
          f"n = {t1['n']} (TP {t1['tp']}, FP {t1['fp']}, TN {t1['tn']}, FN {t1['fn']}); precision {f(t1['precision'])}, "
          f"recall {f(t1['recall'])}, {t1['ms_per_device']:.4f} ms/device. "
          f"**Distinct (baseline, current) pairs: {t1['distinct_cases']}** (cases are replicated 10x or 50x).", "",
          "| Category | n | drift | detected |", "|---|---|---|---|"]
    for k, c in t1["categories"].items():
        L.append(f"| {k} | {c['n']} | {c['drift']:.2f} | {c['detected']} |")
    t2 = r["tier2"]
    L += ["", "## 5. Tier-2 synthetic benchmark (frame liveness)", "",
          f"n = {t2['n']} (TP {t2['tp']}, FP {t2['fp']}, TN {t2['tn']}, FN {t2['fn']}); precision {f(t2['precision'])}, "
          f"recall {f(t2['recall'])}; mean detection latency {t2['mean_latency_frames']:.1f} frames after attack onset.", "",
          "End-to-end consequence (T_cve = 100, banner drift = 0, liveness = minimum over the run):", "",
          "| Category | n | flagged by detector | reaches `low_trust` | mean min L | mean T_final |", "|---|---|---|---|---|---|"]
    for k, c in t2["categories"].items():
        L.append(f"| {k} | {c['n']} | {c['flagged']} | {c['low_trust']} | {c['mean_min_L']:.3f} | {c['mean_t_final']:.1f} |")
    L += ["", "### Single-factor reachability of L(t) with w = (1.0, 0.6, 0.5)", "",
          "| Failure | L | G(L) | T_final (T_cve=100) | gate status |", "|---|---|---|---|---|"]
    for row in r["single_factor"]:
        L.append(f"| {row['failure']} | {row['L']:.2f} | {row['G']:.2f} | {row['T_final']} | {row['status']} |")
    L += ["", "Weights were changed from (0.5, 0.3, 0.2) to (1.0, 0.6, 0.5) on 2026-10-09: with the old weights "
          "L(t) >= 0.5 always, so only freezes could reach low trust and the corpus's liveness values "
          "(down to 0.25) were unreachable. With the new weights L(t) spans [0, 1].", "",
          "## 6. Overhead", "",
          f"Channel A only: {r['latency_us']['advanced']:.2f} us/call; full IG-DCTF: {r['latency_us']['ig_dctf']:.2f} us/call "
          "(pure Python, in-process, excludes I/O).", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    corpus = [e for e in data if e.get("eval_mode", "direct") in ("direct", None)]
    out: dict = {"n_direct": len(corpus)}
    out["n_fabricated"] = sum(e["label"] == "fabricated" for e in corpus)
    out["n_genuine"] = sum(e["label"] == "genuine" for e in corpus)
    out["n_with_signal_fields"] = sum(
        (e.get("drift_score", 0.0) > 0 or e.get("visual_liveness") is not None) for e in corpus)

    # ---- main comparison
    models = {"WA": score_wa, "Advanced": score_adv, "Bayesian": score_bayes, "IG-DCTF": score_ig}
    runs = {k: run(corpus, f) for k, f in models.items()}
    out["comparison"] = {k: metrics(v) for k, v in runs.items()}

    # ---- paired significance IG-DCTF vs Advanced (exact McNemar on correctness)
    a, g = runs["Advanced"], runs["IG-DCTF"]
    b = sum((x["y"] == x["p"]) and (y["y"] != y["p"]) for x, y in zip(a, g))   # adv right, ig wrong
    c = sum((x["y"] != x["p"]) and (y["y"] == y["p"]) for x, y in zip(a, g))   # adv wrong, ig right
    out["mcnemar_ig_vs_adv"] = {"adv_only_correct": b, "ig_only_correct": c, "p_value": mcnemar_exact(b, c)}

    # ---- where does the gain come from? stratify by presence of channel-B fields
    strat = {}
    for k, v in runs.items():
        strat[k] = {
            "with_signal": metrics([r for r in v if r["has_signal"]]),
            "without_signal": metrics([r for r in v if not r["has_signal"]]),
        }
    out["stratified"] = strat

    # ---- ablation (+ additive-fusion control)
    abl = {
        "Channel A only": score_adv,
        "Channel B only": score_channel_b_only,
        "Additive fusion": score_additive,
        "IG-DCTF (multiplicative)": score_ig,
    }
    out["ablation"] = {k: metrics(run(corpus, f)) for k, f in abl.items()}

    # ---- threshold sensitivity (same tier cut-offs as main evaluation)
    lows = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
    highs = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    sweep = []
    for lo in lows:
        for hi in highs:
            m = metrics(run(corpus, lambda e, lo=lo, hi=hi: score_ig_thresholds(e, lo, hi)))
            sweep.append({"theta_low": lo, "theta_high": hi, "f1": m["f1"],
                          "accuracy": m["accuracy"], "precision": m["precision"],
                          "recall": m["recall"], "fp": m["fp"], "fn": m["fn"]})
    out["sweep"] = sweep
    best = max(s["f1"] for s in sweep)
    out["sweep_summary"] = {
        "best_f1": best,
        "chosen_f1": next(s["f1"] for s in sweep if s["theta_low"] == 0.50 and s["theta_high"] == 0.85),
        "within_0.01_of_best": sum(s["f1"] >= best - 0.01 for s in sweep),
        "total": len(sweep),
    }

    # ---- misclassifications of the deployed scorer
    out["ig_errors"] = [r["id"] for r in runs["IG-DCTF"] if r["y"] != r["p"]]
    out["adv_errors"] = [r["id"] for r in runs["Advanced"] if r["y"] != r["p"]]

    # ---- latency: per-call cost of Channel A vs full IG-DCTF
    sample = corpus[:60]
    reps = 200
    t0 = time.perf_counter()
    for _ in range(reps):
        for e in sample:
            score_adv(e)
    t_adv = (time.perf_counter() - t0) / (reps * len(sample)) * 1e6
    t0 = time.perf_counter()
    for _ in range(reps):
        for e in sample:
            score_ig(e)
    t_ig = (time.perf_counter() - t0) / (reps * len(sample)) * 1e6
    out["latency_us"] = {"advanced": t_adv, "ig_dctf": t_ig}

    out["tier1"] = tier1_benchmark()
    out["tier2"] = tier2_benchmark()
    out["single_factor"] = single_factor_table()

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    write_markdown(out)

    # ---- console summary
    print(f"direct scenarios: {out['n_direct']}  fabricated={out['n_fabricated']} genuine={out['n_genuine']}"
          f"  with channel-B fields={out['n_with_signal_fields']}")
    hdr = f"{'model':<26}{'Acc':>8}{'Prec':>8}{'Rec':>8}{'Spec':>8}{'F1':>8}   TP FP TN FN"
    print(hdr)
    for k, m in out["comparison"].items():
        print(f"{k:<26}{m['accuracy']:8.4f}{m['precision']:8.4f}{m['recall']:8.4f}{m['specificity']:8.4f}{m['f1']:8.4f}   "
              f"{m['tp']:2d} {m['fp']:2d} {m['tn']:2d} {m['fn']:2d}")
    print("\nablation")
    for k, m in out["ablation"].items():
        print(f"{k:<26}{m['accuracy']:8.4f}{m['precision']:8.4f}{m['recall']:8.4f}{m['specificity']:8.4f}{m['f1']:8.4f}   "
              f"{m['tp']:2d} {m['fp']:2d} {m['tn']:2d} {m['fn']:2d}")
    print("\nstratified (with / without channel-B fields)")
    for k, s in strat.items():
        w, wo = s["with_signal"], s["without_signal"]
        print(f"{k:<12} with: n={w['n']} acc={w['accuracy']:.3f} f1={w['f1']:.3f} | without: n={wo['n']} acc={wo['accuracy']:.3f} f1={wo['f1']:.3f}")
    print("\nMcNemar IG vs Adv:", out["mcnemar_ig_vs_adv"])
    print("sweep:", out["sweep_summary"])
    print("IG errors:", out["ig_errors"])
    print("Adv errors:", out["adv_errors"])
    print("latency us/call:", out["latency_us"])


if __name__ == "__main__":
    main()
