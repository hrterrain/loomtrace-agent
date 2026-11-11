"""Reproduce the report numbers: evaluation (Ch. 7) and the A/B experiment (Ch. 8).

Run:  .venv/bin/python -m loomtrace.experiments   -> writes results/experiments.json
"""
from __future__ import annotations

import json
import os
import statistics as stats
import time

from . import agent as A
from .evaluate import _macro_f1, golden_set

CLASSES = ("Supported", "Conflicting evidence", "Insufficient evidence")
REPS = 3


def _run(max_loops: int, tag: str, rep: int):
    A.MAX_LOOPS = max_loops
    g = A.build_graph()
    rows = []
    for i, (product, gold, label) in enumerate(golden_set()):
        t = time.perf_counter()
        out = g.invoke(A.new_case(label, case_id=f"{tag}-R{rep}-{i+1:02d}"), {"recursion_limit": 40})
        dt = (time.perf_counter() - t) * 1000
        docs = next((e for e in reversed(out["evidence"]) if e.get("tool") == "gi_doc_search"), None)
        rows.append({
            "case": i + 1, "product": product, "gold": gold, "pred": out["verdict"],
            "baseline": A.run_baseline(label), "loops": out.get("iteration", 0),
            "tool_calls": sum(1 for e in out["evidence"] if e.get("tool")),
            "nodes": len(out["trace"]), "ms": dt, "grade": out["grade"],
            "recall5": bool(docs and docs["ok"] and any(d["product"] == product for d in docs["data"])),
            "cited": bool(out["citations"]), "n_cites": len(out["citations"]),
            "escalated": bool(out.get("escalated")), "label": label,
        })
    A.MAX_LOOPS = 3
    return rows


def _prf(rows, key):
    res = {}
    for c in CLASSES:
        tp = sum(r[key] == c and r["gold"] == c for r in rows)
        fp = sum(r[key] == c and r["gold"] != c for r in rows)
        fn = sum(r[key] != c and r["gold"] == c for r in rows)
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        res[c] = {"precision": p, "recall": rc, "f1": 2 * p * rc / (p + rc) if p + rc else 0.0, "tp": tp, "fp": fp, "fn": fn}
    return res


def _summary(rows, key="pred"):
    n = len(rows)
    unclear = [r for r in rows if r["gold"] == "Insufficient evidence"]
    decided = [r for r in rows if r[key] != "Insufficient evidence"]
    false_support = sum(r[key] == "Supported" and r["gold"] != "Supported" for r in rows)
    out = {
        "n": n,
        "accuracy": sum(r[key] == r["gold"] for r in rows) / n,
        "macro_f1": _macro_f1([(r["gold"], r[key]) for r in rows]),
        "abstention": sum(r[key] == "Insufficient evidence" for r in unclear) / len(unclear),
        "false_supported": false_support,
        "per_class": _prf(rows, key),
        "confusion": {g: {p: sum(r["gold"] == g and r[key] == p for r in rows) for p in CLASSES} for g in CLASSES},
        "per_product_acc": {p: sum(r[key] == r["gold"] for r in rows if r["product"] == p) /
                            sum(1 for r in rows if r["product"] == p) for p in sorted({r["product"] for r in rows})},
    }
    if key == "pred":
        ms = [r["ms"] for r in rows]
        out |= {
            "recall5": sum(r["recall5"] for r in rows) / n,
            "citation_rate": sum(r["cited"] for r in decided) / max(1, len(decided)),
            "mean_cites": stats.mean(r["n_cites"] for r in rows),
            "lat_mean_ms": stats.mean(ms), "lat_sd_ms": stats.pstdev(ms), "lat_max_ms": max(ms),
            "lat_p95_ms": sorted(ms)[int(0.95 * (n - 1))],
            "tool_calls_mean": stats.mean(r["tool_calls"] for r in rows),
            "tool_calls_max": max(r["tool_calls"] for r in rows),
            "nodes_mean": stats.mean(r["nodes"] for r in rows),
            "replanned_cases": sum(r["loops"] > 0 for r in rows),
            "escalated": sum(r["escalated"] for r in rows),
        }
    return out


def main():
    os.makedirs("results", exist_ok=True)
    result = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "reps": REPS, "variant_B": [], "variant_A": []}
    for rep in range(REPS):
        result["variant_B"].append(_summary(rows_b := _run(3, "EXPB", rep)))
        result["variant_A"].append(_summary(rows_a := _run(1, "EXPA", rep)))
    result["baseline"] = _summary(rows_b, key="baseline")
    result["errors_A"] = [{k: r[k] for k in ("case", "product", "gold", "pred", "label")} for r in rows_a if r["pred"] != r["gold"]]
    result["errors_baseline"] = [{k: r[k] for k in ("case", "product", "gold", "baseline")} for r in rows_b if r["baseline"] != r["gold"]]
    result["rows_B"] = [{k: v for k, v in r.items() if k != "label"} for r in rows_b]
    for v in ("variant_A", "variant_B"):
        lat = [s["lat_mean_ms"] for s in result[v]]
        result[v + "_agg"] = {"acc_mean": stats.mean(s["accuracy"] for s in result[v]),
                              "acc_sd": stats.pstdev([s["accuracy"] for s in result[v]]),
                              "lat_mean_ms": stats.mean(lat), "lat_sd_ms": stats.pstdev(lat),
                              "tool_calls_mean": stats.mean(s["tool_calls_mean"] for s in result[v])}
    json.dump(result, open("results/experiments.json", "w"), indent=1, default=str)
    for v in ("variant_A", "variant_B"):
        s = result[v][-1]
        print(v, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in s.items()
                  if k not in ("per_class", "confusion", "per_product_acc")}, result[v + "_agg"])
    print("baseline", round(result["baseline"]["accuracy"], 4), round(result["baseline"]["macro_f1"], 4),
          result["baseline"]["confusion"])
    print("A errors:", [(e["case"], e["gold"], e["pred"]) for e in result["errors_A"]])


if __name__ == "__main__":
    main()
