"""45-case golden set (3 products x 3 verdicts x 5) and the A/B evaluation."""
from __future__ import annotations

import time

from .agent import build_graph, new_case, run_baseline
from .data import BATCHES, GI_REGISTRY, WEAVERS

ALIAS = {"Kancheepuram Silk": "Kanjivaram Silk Saree", "Pochampalli Ikat": "Pochampally Ikat Saree",
         "Banaras Brocades and Sarees": "Banarasi Silk Saree"}
OTHER = {"Kancheepuram Silk": "Pochampalli Ikat", "Pochampalli Ikat": "Banaras Brocades and Sarees",
         "Banaras Brocades and Sarees": "Kancheepuram Silk"}


def _label(product, region, state, weaver=None, batch=None, material=None):
    lines = [f"Product: {product}", f"Region: {region}", f"State: {state}"]
    if material:
        lines.append(f"Material: {material}")
    if weaver:
        lines.append(f"Weaver ID: {weaver}")
    if batch:
        lines.append(f"Batch ID: {batch}")
    lines.append("GI Tagged - Authentic Handloom")
    return "\n".join(lines)


def golden_set():
    cases = []
    for product in ALIAS:  # golden set covers the 3 products in the design document
        info = GI_REGISTRY[product]
        ws = [w for w in WEAVERS.values() if w["product"] == product]
        other_ws = [w for w in WEAVERS.values() if w["product"] == OTHER[product]]
        st = info["state"]
        # --- Supported (5): valid weaver + own batch; some use aliases to force a re-plan
        for i in range(5):
            w = ws[i]
            b = next(x for x in BATCHES.values() if x["weaver_id"] == w["weaver_id"])
            name = ALIAS[product] if i % 2 else product
            cases.append((product, "Supported", _label(name, w["district"], st, w["weaver_id"], b["batch_id"], b["yarn"])))
        # --- Conflicting (5)
        w, w2 = ws[5], ws[6]
        b = next(x for x in BATCHES.values() if x["weaver_id"] == w["weaver_id"])
        b2 = next(x for x in BATCHES.values() if x["weaver_id"] == w2["weaver_id"])
        ow = other_ws[0]
        ob = next(x for x in BATCHES.values() if x["weaver_id"] == ow["weaver_id"])
        wrong_region = {"Tamil Nadu": "Surat", "Telangana": "Bhagalpur", "Uttar Pradesh": "Murshidabad"}[st]
        cases += [
            (product, "Conflicting evidence", _label(product, wrong_region, st, w["weaver_id"], b["batch_id"])),
            (product, "Conflicting evidence", _label(product, w["district"], st, ow["weaver_id"], ob["batch_id"])),
            (product, "Conflicting evidence", _label(product, w["district"], st, w["weaver_id"], b2["batch_id"])),
            (product, "Conflicting evidence", _label("Mysore Silk Saree", w["district"], st, w["weaver_id"], b["batch_id"])),
            (product, "Conflicting evidence", _label(product, w["district"], st, w["weaver_id"], b["batch_id"], "polyester")),
        ]
        # --- Insufficient (5): missing / unknown weaver or batch details
        w = ws[7]
        b = next(x for x in BATCHES.values() if x["weaver_id"] == w["weaver_id"])
        cases += [
            (product, "Insufficient evidence", _label(product, w["district"], st, None, b["batch_id"])),
            (product, "Insufficient evidence", _label(product, w["district"], st, w["weaver_id"], None)),
            (product, "Insufficient evidence", _label(product, w["district"], st)),
            (product, "Insufficient evidence", _label(product, w["district"], st, "WV-XXX-999", b["batch_id"])),
            (product, "Insufficient evidence", _label(product, w["district"], st, w["weaver_id"], "B-XXX-0000")),
        ]
    return cases


def _macro_f1(pairs):
    f1s = []
    for c in ("Supported", "Conflicting evidence", "Insufficient evidence"):
        tp = sum(p == c and g == c for g, p in pairs)
        fp = sum(p == c and g != c for g, p in pairs)
        fn = sum(p != c and g == c for g, p in pairs)
        prec = tp / (tp + fp) if tp + fp else 0
        rec = tp / (tp + fn) if tp + fn else 0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0)
    return sum(f1s) / 3


def evaluate(progress=None, llm=None):
    graph = build_graph(llm)
    rows = []
    cases = golden_set()
    for i, (product, gold, label) in enumerate(cases):
        t = time.perf_counter()
        out = graph.invoke(new_case(label, case_id=f"EVAL-{i+1:02d}"), {"recursion_limit": 40})
        dt = time.perf_counter() - t
        tool_calls = sum(1 for e in out["evidence"] if e.get("tool"))
        docs = next((e for e in reversed(out["evidence"]) if e.get("tool") == "gi_doc_search"), None)
        recall = any(d["product"] == product for d in (docs["data"] or [])) if docs and docs["ok"] else False
        rows.append({"case": f"EVAL-{i+1:02d}", "product": product, "gold": gold, "agent": out["verdict"],
                     "baseline": run_baseline(label), "loops": out.get("iteration", 0),
                     "tool_calls": tool_calls, "latency_s": round(dt, 3), "recall@5": recall,
                     "cited": bool(out["citations"]), "label": label})
        if progress:
            progress((i + 1) / len(cases))
    n = len(rows)
    unclear = [r for r in rows if r["gold"] == "Insufficient evidence"]
    def summary(key):
        return {
            "accuracy": sum(r[key] == r["gold"] for r in rows) / n,
            "macro_f1": _macro_f1([(r["gold"], r[key]) for r in rows]),
            "abstention": sum(r[key] == "Insufficient evidence" for r in unclear) / len(unclear),
        }
    metrics = {"agent": summary("agent") | {
                   "recall@5": sum(r["recall@5"] for r in rows) / n,
                   "citation_rate": sum(r["cited"] for r in rows if r["agent"] != "Insufficient evidence")
                                    / max(1, sum(r["agent"] != "Insufficient evidence" for r in rows)),
                   "latency_s": sum(r["latency_s"] for r in rows) / n,
                   "tool_calls": sum(r["tool_calls"] for r in rows) / n},
               "baseline": summary("baseline")}
    return rows, metrics


if __name__ == "__main__":
    rows, m = evaluate()
    for r in rows:
        if r["agent"] != r["gold"]:
            print("MISS", r["case"], r["gold"], "->", r["agent"], r["label"].replace("\n", " | "))
    print(m)
