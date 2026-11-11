"""The seven typed tools. Every tool returns a source_id so verdicts can cite it."""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
from collections import Counter
from typing import Optional

from pydantic import BaseModel, Field

from .data import BATCHES, CENSUS, GI_DOCS, GI_REGISTRY, WEAVERS

DB_PATH = os.environ.get("LOOMTRACE_DB", os.path.join(os.path.dirname(__file__), "..", "loomtrace.db"))


# ------------------------------------------------------------------ schemas --
class LabelFields(BaseModel):
    product: Optional[str] = None
    region: Optional[str] = None
    state: Optional[str] = None
    weaver_id: Optional[str] = None
    batch_id: Optional[str] = None
    material: Optional[str] = None
    gi_claim: bool = True


class ToolResult(BaseModel):
    tool: str
    ok: bool
    data: dict | list | None = None
    source_id: Optional[str] = None
    note: str = ""
    ms: float = 0.0


class Passage(BaseModel):
    id: str
    product: str
    page: int
    text: str
    score: float = Field(ge=0)


# --------------------------------------------------------------- utilities --
def _db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS review_queue(
        id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, reason TEXT,
        claim TEXT, created REAL, status TEXT DEFAULT 'open')""")
    con.execute("""CREATE TABLE IF NOT EXISTS checkpoints(
        case_id TEXT, step INTEGER, node TEXT, state TEXT, created REAL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS cases(
        case_id TEXT PRIMARY KEY, label TEXT, verdict TEXT, grade REAL,
        loops INTEGER, citations TEXT, created REAL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS decisions(
        queue_id INTEGER PRIMARY KEY, case_id TEXT, decision TEXT, note TEXT, decided REAL)""")
    return con


# ------------------------------------------------- human-in-the-loop helpers --
def request_review(case_id: str, reason: str, claim: dict) -> int:
    """Customer-initiated escalation (e.g. they disagree with the automated verdict)."""
    return escalate_to_human(case_id, reason, claim).data["queue_id"]


def decide(queue_id: int, decision: str, note: str):
    """Reviewer decision. It becomes the case's final verdict."""
    con = _db()
    case_id = con.execute("SELECT case_id FROM review_queue WHERE id=?", (queue_id,)).fetchone()[0]
    con.execute("UPDATE review_queue SET status=? WHERE id=?",
                ("approved" if decision == "Supported" else "rejected", queue_id))
    con.execute("INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?)", (queue_id, case_id, decision, note, time.time()))
    con.commit()
    con.close()


def case_status(case_id: str) -> dict | None:
    con = _db()
    row = con.execute("SELECT case_id, label, verdict, grade, created FROM cases WHERE case_id=?",
                      (case_id.strip().upper(),)).fetchone()
    if not row:
        con.close()
        return None
    q = con.execute("SELECT id, reason, status, created FROM review_queue WHERE case_id=? ORDER BY id DESC",
                    (row[0],)).fetchone()
    d = con.execute("SELECT decision, note, decided FROM decisions WHERE case_id=? ORDER BY decided DESC",
                    (row[0],)).fetchone()
    con.close()
    return {"case_id": row[0], "label": row[1], "auto_verdict": row[2], "grade": row[3], "created": row[4],
            "queue": {"id": q[0], "reason": q[1], "status": q[2], "created": q[3]} if q else None,
            "decision": {"verdict": d[0], "note": d[1], "decided": d[2]} if d else None}


def _timed(fn):
    def wrap(*a, **k):
        t = time.perf_counter()
        r: ToolResult = fn(*a, **k)
        r.ms = round((time.perf_counter() - t) * 1000, 2)
        return r
    wrap.__name__ = fn.__name__
    return wrap


def canonical_product(name: Optional[str]) -> Optional[str]:
    """Map a free-text product name (or alias) to its GI-registered name."""
    if not name:
        return None
    n = name.lower().strip()
    for prod, info in GI_REGISTRY.items():
        if n == prod.lower():
            return prod
    best, best_len = None, 0
    for prod, info in GI_REGISTRY.items():
        for a in info["aliases"] + [prod.lower()]:
            if a in n and len(a) > best_len:
                best, best_len = prod, len(a)
    return best


# ------------------------------------------------------------- tool 1: OCR --
@_timed
def extract_label(label_text: str = "", image_bytes: bytes | None = None, llm=None) -> ToolResult:
    """Product image/label -> structured fields. EasyOCR if available, SLM if a key is set,
    otherwise a deterministic parser."""
    text = label_text or ""
    note = "parsed label text"
    if image_bytes:
        try:
            import easyocr  # optional heavy dependency
            reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            text = " \n".join(reader.readtext(image_bytes, detail=0)) + "\n" + text
            note = "EasyOCR + parser"
        except Exception:
            note = "EasyOCR not installed - used typed label text"

    fields = None
    if llm is not None:
        fields = llm.extract(text)
        if fields:
            note += " + SLM extraction"
    if fields is None:
        fields = _parse_label(text)
    return ToolResult(tool="extract_label", ok=True, data=fields.model_dump(),
                      source_id="LABEL#input", note=note)


def _grab(pattern, text):
    m = re.search(pattern, text, re.I | re.M)
    return m.group(1).strip() if m else None


def _parse_label(text: str) -> LabelFields:
    def field(*keys):
        for k in keys:
            v = _grab(rf"^\s*{k}\s*[:\-]\s*(.+)$", text)
            if v:
                return v
        return None

    product = field("product", "item", "saree", "name")
    region = field("region", "district", "origin", "place", "woven in", "made in")
    state = field("state")
    weaver = field("weaver id", "weaver", "artisan id") or _grab(r"\b(WV-[A-Z]{3}-\d{3})\b", text)
    batch = field("batch id", "batch", "lot") or _grab(r"\b(B-[A-Z]{3}-\d{4})\b", text)
    material = field("material", "yarn", "fabric")
    if weaver:
        weaver = (_grab(r"(WV-[A-Z]{3}-\d{3})", weaver.upper()) or weaver).upper()
    if batch:
        batch = (_grab(r"(B-[A-Z]{3}-\d{4})", batch.upper()) or batch).upper()
    if not product:
        for prod, info in GI_REGISTRY.items():
            if any(a in text.lower() for a in info["aliases"] + [prod.lower()]):
                product = prod
                break
    if region and "," in region and not state:
        region, state = [s.strip() for s in region.split(",", 1)]
    gi_claim = not re.search(r"\bno gi\b|\bnot gi\b", text, re.I)
    return LabelFields(product=product, region=region, state=state, weaver_id=weaver,
                       batch_id=batch, material=material, gi_claim=gi_claim)


# ---------------------------------------------------------- tool 2: registry --
@_timed
def gi_registry_lookup(product: str, resolve_aliases: bool = False) -> ToolResult:
    name = canonical_product(product) if resolve_aliases else (
        product if product in GI_REGISTRY else None)
    if not name:
        return ToolResult(tool="gi_registry_lookup", ok=False,
                          note=f"'{product}' not found in GI registration list"
                               + ("" if resolve_aliases else " (exact match)"))
    info = GI_REGISTRY[name]
    return ToolResult(tool="gi_registry_lookup", ok=True, source_id=info["source_id"],
                      data={"product": name, "gi_no": info["gi_no"], "state": info["state"],
                            "class": info["goods_class"], "districts": info["districts"],
                            "materials": info["materials"], "state_wide": info.get("state_wide", False)})


# ------------------------------------------------------ tool 3: RAG search --
_TOK = re.compile(r"[a-z]+")


def _tokens(s):
    return _TOK.findall(s.lower())


_DOC_TOKS = [_tokens(d["text"] + " " + d["product"]) for d in GI_DOCS]
_DF = Counter(t for toks in _DOC_TOKS for t in set(toks))
_AVG = sum(map(len, _DOC_TOKS)) / len(_DOC_TOKS)


def _bm25(query, idx, k1=1.5, b=0.75):
    toks, tf, n = _DOC_TOKS[idx], Counter(_DOC_TOKS[idx]), len(GI_DOCS)
    s = 0.0
    for q in set(_tokens(query)):
        if q not in tf:
            continue
        idf = math.log(1 + (n - _DF[q] + 0.5) / (_DF[q] + 0.5))
        s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(toks) / _AVG))
    return s


@_timed
def gi_doc_search(query: str, product: Optional[str] = None, k: int = 5) -> ToolResult:
    """Top-k GI application passages (BM25; swap for Chroma + bge-small in production)."""
    scored = []
    for i, d in enumerate(GI_DOCS):
        if product and d["product"] != product:
            continue
        sc = _bm25(query, i)
        if sc > 0:
            scored.append(Passage(**d, score=round(sc, 3)))
    scored.sort(key=lambda p: -p.score)
    top = scored[:k]
    return ToolResult(tool="gi_doc_search", ok=bool(top), data=[p.model_dump() for p in top],
                      source_id=",".join(p.id for p in top) or None,
                      note=f"{len(top)} passages" + (f" filtered to {product}" if product else " (unfiltered)"))


# ------------------------------------------------------------ tool 4: census --
@_timed
def census_lookup(state: str) -> ToolResult:
    row = next((v | {"state": k} for k, v in CENSUS.items() if k.lower() == (state or "").lower()), None)
    if not row:
        return ToolResult(tool="census_lookup", ok=False, note=f"No census row for '{state}'")
    return ToolResult(tool="census_lookup", ok=True, data=row, source_id=row["source_id"],
                      note="PIB annexure, Release ID 2202869 (Handloom Census 2019-20)")


# ------------------------------------------------------- tool 5/6: records --
@_timed
def weaver_lookup(weaver_id: str) -> ToolResult:
    w = WEAVERS.get((weaver_id or "").upper())
    if not w:
        return ToolResult(tool="weaver_lookup", ok=False, note=f"Weaver '{weaver_id}' not in registry")
    return ToolResult(tool="weaver_lookup", ok=True, data=w, source_id=w["source_id"], note="SIMULATED record")


@_timed
def provenance_lookup(batch_id: str) -> ToolResult:
    b = BATCHES.get((batch_id or "").upper())
    if not b:
        return ToolResult(tool="provenance_lookup", ok=False, note=f"Batch '{batch_id}' not found")
    return ToolResult(tool="provenance_lookup", ok=True, data=b, source_id=b["source_id"], note="SIMULATED record")


# ------------------------------------------------------------ tool 7: HITL --
@_timed
def escalate_to_human(case_id: str, reason: str, claim: dict) -> ToolResult:
    con = _db()
    cur = con.execute("INSERT INTO review_queue(case_id, reason, claim, created) VALUES (?,?,?,?)",
                      (case_id, reason, json.dumps(claim), time.time()))
    con.commit()
    qid = cur.lastrowid
    con.close()
    return ToolResult(tool="escalate_to_human", ok=True, data={"queue_id": qid, "reason": reason},
                      source_id=f"REVIEWQ#{qid}", note="added to human review queue")


TOOL_CATALOG = [
    ("extract_label", "Product image → text fields", "EasyOCR + SLM", "Extract"),
    ("gi_registry_lookup", "Product name → GI no., state, class", "IP India registration list", "Retriever"),
    ("gi_doc_search", "Query + product → top-5 passages + page", "GI documents (vector index)", "Retriever"),
    ("census_lookup", "State → weaver counts", "Handloom Census 2019-20", "Retriever"),
    ("weaver_lookup", "Weaver ID → name, cluster, district", "Simulated registry", "Retriever"),
    ("provenance_lookup", "Batch ID → loom, yarn, dates, weaver", "Simulated records", "Retriever"),
    ("escalate_to_human", "Case + reason → review-queue entry", "SQLite review queue", "Guardrail"),
]
