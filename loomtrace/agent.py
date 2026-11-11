"""LoomTrace agent: a LangGraph state graph with six nodes and a re-plan loop (max 3)."""
from __future__ import annotations

import json
import operator
import os
import time
import uuid
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from . import tools as T
from .data import GI_REGISTRY

MAX_LOOPS = 3
GRADE_THRESHOLD = 0.6
VERDICTS = ("Supported", "Conflicting evidence", "Insufficient evidence")


# ----------------------------------------------------------------- the SLM --
class GroqSLM:
    """Llama 3.1 8B on Groq. Used only for narrow tasks: extraction + verdict rationale."""
    model = "llama-3.1-8b-instant"

    def __init__(self, api_key: str):
        from groq import Groq
        self.client = Groq(api_key=api_key)

    def _json(self, system, user):
        r = self.client.chat.completions.create(
            model=self.model, temperature=0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return json.loads(r.choices[0].message.content)

    def extract(self, text: str) -> Optional[T.LabelFields]:
        try:
            d = self._json("Extract handloom label fields. Return JSON with keys: product, region "
                           "(district), state, weaver_id, batch_id, material, gi_claim (bool). Use null if absent. "
                           "Copy IDs exactly.", text)
            return T.LabelFields(**{k: d.get(k) for k in T.LabelFields.model_fields if d.get(k) is not None})
        except Exception:
            return None

    def rationale(self, verdict: str, checks: dict, evidence: list) -> Optional[str]:
        try:
            ev = [{"source": e["source_id"], "note": e.get("note", "")} for e in evidence if e.get("source_id")][:12]
            d = self._json("You explain a GI verification verdict in 2-3 sentences. Only use the given checks "
                           "and cite sources in [brackets]. Return JSON {\"rationale\": str}.",
                           json.dumps({"verdict": verdict, "checks": checks, "evidence": ev}))
            return d.get("rationale")
        except Exception:
            return None


def get_llm():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        return GroqSLM(key)
    except Exception:
        return None


# --------------------------------------------------------------- CaseState --
class CaseState(TypedDict, total=False):
    case_id: str
    label_text: str
    image: Optional[bytes]
    fields: dict
    plan: list
    query: str
    resolve_aliases: bool
    canonical: Optional[str]
    evidence: Annotated[list, operator.add]
    checks: dict
    grade: float
    grade_detail: dict
    iteration: int
    verdict: str
    confidence: float
    citations: list
    rationale: str
    escalated: Optional[dict]
    trace: Annotated[list, operator.add]


def _log(node, msg, **extra):
    return [{"node": node, "msg": msg, "t": time.time(), **extra}]


def _checkpoint(case_id, node, state):
    con = T._db()
    step = con.execute("SELECT COUNT(*) FROM checkpoints WHERE case_id=?", (case_id,)).fetchone()[0]
    safe = {k: v for k, v in state.items() if k != "image"}
    con.execute("INSERT INTO checkpoints VALUES (?,?,?,?,?)",
                (case_id, step, node, json.dumps(safe, default=str), time.time()))
    con.commit()
    con.close()


def checkpointed(name, fn):
    def run(state: CaseState):
        out = fn(state)
        _checkpoint(state["case_id"], name, {**state, **out,
                                             "evidence": state.get("evidence", []) + out.get("evidence", []),
                                             "trace": state.get("trace", []) + out.get("trace", [])})
        return out
    run.__name__ = name
    return run


# ------------------------------------------------------------------- nodes --
def make_nodes(llm):
    def extract(state: CaseState):
        r = T.extract_label(state.get("label_text", ""), state.get("image"), llm=llm)
        f = r.data
        found = ", ".join(f"{k}={v}" for k, v in f.items() if v not in (None, True, False))
        return {"fields": f, "iteration": 0, "evidence": [r.model_dump()],
                "trace": _log("Extract", f"{r.note}: {found or 'no fields found'}", tool=r.model_dump())}

    def planner(state: CaseState):
        f, it = state["fields"], state.get("iteration", 0)
        checks = ["product_registered", "gi_document_support", "census_plausible"]
        if f.get("region"):
            checks.append("region_in_gi_area")
        if f.get("state"):
            checks.append("state_matches")
        if f.get("material"):
            checks.append("material_consistent")
        checks += ["weaver_registered", "weaver_cluster", "batch_found", "batch_weaver_match"]
        if it == 0:
            query = f"{f.get('product') or ''} {f.get('region') or ''}".strip() or state.get("label_text", "")[:80]
            resolve, msg = False, "Initial plan: exact registry match, unfiltered document search"
        else:
            canon = T.canonical_product(f.get("product")) or state.get("canonical")
            info = GI_REGISTRY.get(canon, {})
            query = " ".join(filter(None, [canon, f.get("region"), info.get("state"),
                                           "geographical area weavers woven", *info.get("materials", [])]))
            resolve, msg = True, f"Re-plan #{it}: resolve aliases → '{canon}', sharper query filtered by product"
        return {"plan": checks, "query": query, "resolve_aliases": resolve,
                "trace": _log("Planner", msg, plan=checks, query=query)}

    def retriever(state: CaseState):
        f = state["fields"]
        results = []
        reg = T.gi_registry_lookup(f.get("product") or "", resolve_aliases=state.get("resolve_aliases", False))
        results.append(reg)
        canon = reg.data["product"] if reg.ok else None
        results.append(T.gi_doc_search(state["query"], product=canon if state.get("resolve_aliases") else None))
        st = f.get("state") or (reg.data["state"] if reg.ok else None)
        if st:
            results.append(T.census_lookup(st))
        if f.get("weaver_id"):
            results.append(T.weaver_lookup(f["weaver_id"]))
        if f.get("batch_id"):
            results.append(T.provenance_lookup(f["batch_id"]))
        it = state.get("iteration", 0)
        ev = [r.model_dump() | {"iteration": it} for r in results]
        summary = " · ".join(f"{r.tool}{'✓' if r.ok else '✗'}" for r in results)
        return {"evidence": ev, "canonical": canon,
                "trace": _log("Retriever", summary, tools=ev)}

    def verifier(state: CaseState):
        f, it = state["fields"], state.get("iteration", 0)
        ev = {e["tool"]: e for e in state["evidence"] if e.get("iteration") == it}
        c: dict[str, dict] = {}

        def put(name, status, why, src=None):
            c[name] = {"status": status, "why": why, "source": src}

        reg = ev.get("gi_registry_lookup")
        info = reg["data"] if reg and reg["ok"] else None
        if info:
            gi_txt = f"GI No. {info['gi_no']}" if info["gi_no"] else "a registered GI"
            put("product_registered", "pass", f"'{info['product']}' is {gi_txt} ({info['state']})", reg["source_id"])
        elif it == 0:
            put("product_registered", "unknown", f"'{f.get('product')}' has no exact registry match - may be an alias")
        else:
            put("product_registered", "fail", f"'{f.get('product')}' does not match any GI registration in scope")

        docs = ev.get("gi_doc_search")
        relevant = [d for d in (docs["data"] or [])] if docs and docs["ok"] else []
        if info:
            relevant = [d for d in relevant if d["product"] == info["product"]]
        if relevant and (relevant[0]["score"] >= 2.0 or info):
            put("gi_document_support", "pass", f"{len(relevant)} matching passages in the official GI application (best match on page {relevant[0]['page']})",
                ",".join(d["id"] for d in relevant[:3]))
        else:
            put("gi_document_support", "unknown", "Retrieved GI passages are weak or off-product")

        if f.get("region"):
            if info and info.get("state_wide"):
                st_ = (f.get("state") or "").lower()
                ok = st_ == info["state"].lower() or info["state"].lower() in f["region"].lower() or any(
                    d.lower() in f["region"].lower() for d in info["districts"])
                put("region_in_gi_area", "pass" if ok else "fail",
                    f"Region '{f['region']}' {'is' if ok else 'is NOT'} within the GI area ({info['state']})", reg["source_id"])
            elif info:
                ok = any(d.lower() in f["region"].lower() or f["region"].lower() in d.lower() for d in info["districts"])
                put("region_in_gi_area", "pass" if ok else "fail",
                    f"Region '{f['region']}' {'is' if ok else 'is NOT'} in GI area ({', '.join(info['districts'])})",
                    reg["source_id"])
            else:
                put("region_in_gi_area", "unknown", "No registry entry to compare region against")
        if f.get("state"):
            if info:
                ok = f["state"].lower() == info["state"].lower()
                put("state_matches", "pass" if ok else "fail", f"State '{f['state']}' vs registered '{info['state']}'", reg["source_id"])
            else:
                put("state_matches", "unknown", "No registry entry")
        if f.get("material"):
            if info and not info["materials"]:
                put("material_consistent", "pass", "GI record does not restrict materials", reg["source_id"])
            elif info:
                ok = any(m in f["material"].lower() or f["material"].lower() in m for m in info["materials"])
                put("material_consistent", "pass" if ok else "fail",
                    f"Material '{f['material']}' {'matches' if ok else 'not in'} GI description ({', '.join(info['materials'])})",
                    reg["source_id"])
            else:
                put("material_consistent", "unknown", "No registry entry")

        cen = ev.get("census_lookup")
        if cen and cen["ok"]:
            put("census_plausible", "pass", f"{cen['data']['weavers']:,} handloom weavers in {cen['data']['state']}", cen["source_id"])
        else:
            put("census_plausible", "unknown", "No census data for state")

        w = ev.get("weaver_lookup")
        if not f.get("weaver_id"):
            put("weaver_registered", "unknown", "No weaver ID on label")
            put("weaver_cluster", "unknown", "No weaver ID on label")
        elif not w["ok"]:
            put("weaver_registered", "unknown", f"Weaver '{f['weaver_id']}' not found in registry")
            put("weaver_cluster", "unknown", "Weaver record unavailable")
        else:
            wd = w["data"]
            put("weaver_registered", "pass", f"{wd['name']} ({wd['weaver_id']}), {wd['cluster']} cluster", w["source_id"])
            if info:
                ok = wd["product"] == info["product"] and wd["district"] in info["districts"]
                put("weaver_cluster", "pass" if ok else "fail",
                    f"Weaver belongs to {wd['product']} cluster in {wd['district']}" + ("" if ok else f" - not {info['product']}"),
                    w["source_id"])
            else:
                put("weaver_cluster", "unknown", "No registry entry")

        b = ev.get("provenance_lookup")
        if not f.get("batch_id"):
            put("batch_found", "unknown", "No batch ID on label")
            put("batch_weaver_match", "unknown", "No batch ID on label")
        elif not b["ok"]:
            put("batch_found", "unknown", f"Batch '{f['batch_id']}' not found")
            put("batch_weaver_match", "unknown", "Batch record unavailable")
        else:
            bd = b["data"]
            put("batch_found", "pass", f"Loom {bd['loom']}, {bd['yarn']} yarn, {bd['started']} → {bd['finished']}", b["source_id"])
            if f.get("weaver_id") and not (w and w["ok"]):
                put("batch_weaver_match", "unknown", "Claimed weaver is unverified - cannot match batch")
            elif f.get("weaver_id"):
                ok = bd["weaver_id"] == f["weaver_id"].upper() and (not info or bd["product"] == info["product"])
                put("batch_weaver_match", "pass" if ok else "fail",
                    f"Batch woven by {bd['weaver_id']} ({bd['product']})" + ("" if ok else " - mismatch with claim"), b["source_id"])
            else:
                put("batch_weaver_match", "unknown", "No weaver ID to match batch against")

        fails = [k for k, v in c.items() if v["status"] == "fail"]
        msg = f"{sum(v['status']=='pass' for v in c.values())} pass · {len(fails)} fail · " \
              f"{sum(v['status']=='unknown' for v in c.values())} unknown"
        return {"checks": c, "trace": _log("Verifier", msg, checks=c)}

    def grader(state: CaseState):
        c = state["checks"]
        n = len(c)
        determinate = sum(v["status"] != "unknown" for v in c.values())
        fails = sum(v["status"] == "fail" for v in c.values())
        completeness = determinate / n
        consistency = 1.0 if fails == 0 else 0.0
        cited = sum(1 for v in c.values() if v["status"] != "unknown" and v["source"]) / max(determinate, 1)
        if fails:
            grade = round(0.5 + 0.5 * cited, 2)  # a cited conflict is strong evidence
        else:
            grade = round(0.7 * completeness + 0.3 * cited, 2)
        fixable = c["product_registered"]["status"] == "unknown" or c["gi_document_support"]["status"] == "unknown"
        it = state.get("iteration", 0)
        loop = fixable and it + 1 < MAX_LOOPS and state.get("fields", {}).get("product")
        detail = {"completeness": round(completeness, 2), "consistency": consistency, "cited": round(cited, 2),
                  "decision": "re-plan" if loop else "finish"}
        return {"grade": grade, "grade_detail": detail, "iteration": it + 1 if loop else it,
                "trace": _log("Grader", f"grade={grade} (completeness {detail['completeness']}, "
                                        f"consistency {consistency}) → {detail['decision']}", grade=detail)}

    def guardrail(state: CaseState):
        c = state["checks"]
        statuses = [v["status"] for v in c.values()]
        if "fail" in statuses:
            verdict = "Conflicting evidence"
        elif "unknown" in statuses:
            verdict = "Insufficient evidence"
        else:
            verdict = "Supported"
        citations = sorted({s for v in c.values() if v["status"] != "unknown" and v["source"]
                            for s in v["source"].split(",")})
        reasons = []
        if verdict != "Insufficient evidence" and not citations:
            reasons.append("verdict has no citation")
        if verdict != "Insufficient evidence" and state["grade"] < GRADE_THRESHOLD:
            reasons.append(f"low confidence ({state['grade']})")
        if reasons:
            verdict = "Insufficient evidence"
        if verdict == "Insufficient evidence":
            missing = [k for k, v in c.items() if v["status"] == "unknown"]
            reasons.append("missing: " + ", ".join(missing) if missing else "")
        escalated = None
        out_ev = []
        if verdict == "Insufficient evidence":
            r = T.escalate_to_human(state["case_id"], "; ".join(filter(None, reasons)), state["fields"])
            escalated = r.data
            out_ev.append(r.model_dump())
        fails = [v["why"] for v in c.values() if v["status"] == "fail"]
        if verdict == "Supported":
            rationale = "All checks passed against official GI registry, GI documents and census data; weaver and batch records are consistent."
        elif verdict == "Conflicting evidence":
            rationale = "Conflict found: " + "; ".join(fails) + "."
        else:
            rationale = "Not enough evidence to decide - sent to human review (" + "; ".join(filter(None, reasons)) + ")."
        if llm is not None:
            rationale = llm.rationale(verdict, {k: v["status"] for k, v in c.items()}, state["evidence"]) or rationale
        _save_case(state, verdict, citations)
        return {"verdict": verdict, "confidence": state["grade"], "citations": citations, "rationale": rationale,
                "escalated": escalated, "evidence": out_ev,
                "trace": _log("Guardrail", f"{verdict}" + (f" → escalated to human (queue #{escalated['queue_id']})" if escalated else "")
                              , verdict=verdict)}

    return {"extract": extract, "planner": planner, "retriever": retriever,
            "verifier": verifier, "grader": grader, "guardrail": guardrail}


def _save_case(state, verdict, citations):
    con = T._db()
    con.execute("INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?)",
                (state["case_id"], state.get("label_text", ""), verdict, state["grade"],
                 state.get("iteration", 0), json.dumps(citations), time.time()))
    con.commit()
    con.close()


def build_graph(llm=None):
    nodes = make_nodes(llm)
    g = StateGraph(CaseState)
    for name, fn in nodes.items():
        g.add_node(name, checkpointed(name, fn))
    g.add_edge(START, "extract")
    g.add_edge("extract", "planner")
    g.add_edge("planner", "retriever")
    g.add_edge("retriever", "verifier")
    g.add_edge("verifier", "grader")
    g.add_conditional_edges("grader", lambda s: s["grade_detail"]["decision"],
                            {"re-plan": "planner", "finish": "guardrail"})
    g.add_edge("guardrail", END)
    return g.compile()


def new_case(label_text: str, image: bytes | None = None, case_id: str | None = None) -> CaseState:
    return {"case_id": case_id or f"CASE-{uuid.uuid4().hex[:8].upper()}", "label_text": label_text,
            "image": image, "evidence": [], "trace": []}


def run_case(label_text: str, image: bytes | None = None, llm=None, graph=None) -> dict:
    graph = graph or build_graph(llm)
    return graph.invoke(new_case(label_text, image), {"recursion_limit": 40})


# ------------------------------------------------------------- baseline ----
def run_baseline(label_text: str) -> str:
    """A/B baseline: one document lookup + one decision, no planning, loop or guardrail."""
    r = T.gi_doc_search(label_text)
    return "Supported" if r.ok and r.data[0]["score"] > 2 else "Insufficient evidence"
