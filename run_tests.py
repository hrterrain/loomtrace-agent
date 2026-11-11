"""Demo test cases for LoomTrace. Run: .venv/bin/python run_tests.py  (writes TEST_RESULTS.md)"""
import time

from loomtrace.agent import build_graph, new_case

S, C, I = "Supported", "Conflicting evidence", "Insufficient evidence"

# (id, what it tests, product, region, state, material, weaver, batch, expected)
CASES = [
    ("T01", "Authentic Kancheepuram silk, full details", "Kancheepuram Silk", "Kancheepuram", "Tamil Nadu", "mulberry silk", "WV-KAN-002", "B-KAN-0020", S),
    ("T02", "Local name 'Kanjivaram' (agent re-plans to resolve alias)", "Kanjivaram Silk Saree", "Thiruvallur", "Tamil Nadu", "mulberry silk", "WV-KAN-001", "B-KAN-0010", S),
    ("T03", "Authentic Pochampalli ikat", "Pochampally Ikat Saree", "Nalgonda", "Telangana", "cotton", "WV-POC-003", "B-POC-0030", S),
    ("T04", "Authentic Banarasi saree", "Banarasi Silk Saree", "Varanasi", "Uttar Pradesh", "silk", "WV-BAN-006", "B-BAN-0060", S),
    ("T05", "New product: Sambalpuri ikat (Odisha)", "Sambalpuri Ikat Saree", "Bargarh", "Odisha", "", "WV-SAM-002", "B-SAM-0020", S),
    ("T06", "New product: Muga silk (state-wide GI, Assam)", "Muga Silk Mekhela", "Sualkuchi", "Assam", "muga silk", "WV-MUG-001", "B-MUG-0010", S),
    ("T07", "New product: Kota Doria (Rajasthan)", "Kota Doria Saree", "Kaithoon", "Rajasthan", "cotton", "WV-KTD-004", "B-KTD-0040", S),
    ("T08", "Fake: Banarasi claimed from Surat, Gujarat", "Banarasi Silk Saree", "Surat", "Gujarat", "silk", "WV-BAN-002", "B-BAN-0020", C),
    ("T09", "Fake: Kancheepuram sold with an Ikat weaver's ID", "Kancheepuram Silk", "Kancheepuram", "Tamil Nadu", "silk", "WV-POC-004", "B-POC-0040", C),
    ("T10", "Fake: batch woven by a different weaver", "Pochampalli Ikat", "Nalgonda", "Telangana", "cotton", "WV-POC-001", "B-POC-0050", C),
    ("T11", "Fake: Kancheepuram 'silk' made of polyester", "Kancheepuram Silk", "Kancheepuram", "Tamil Nadu", "polyester", "WV-KAN-002", "B-KAN-0020", C),
    ("T12", "Fake: Chanderi claimed from Varanasi", "Chanderi Saree", "Varanasi", "Uttar Pradesh", "silk", "WV-CHA-001", "B-CHA-0010", C),
    ("T13", "Missing weaver and batch details", "Banaras Brocades and Sarees", "Varanasi", "Uttar Pradesh", "silk", "", "", I),
    ("T14", "Weaver ID not in any registry", "Kota Doria", "Kota", "Rajasthan", "cotton", "WV-XXX-999", "B-KTD-0010", I),
    ("T15", "Batch ID not on record", "Kullu Shawl", "Kullu", "Himachal Pradesh", "wool", "WV-KUL-003", "B-KUL-9999", I),
]


def label(p, r, s, m, w, b):
    rows = [("Product", p), ("Region", r), ("State", s), ("Material", m), ("Weaver ID", w), ("Batch ID", b)]
    return "\n".join(f"{k}: {v}" for k, v in rows if v) + "\nGI Tagged"


if __name__ == "__main__":
    g = build_graph()
    out, ok = [], 0
    for cid, desc, p, r, s, m, w, b, exp in CASES:
        t = time.perf_counter()
        res = g.invoke(new_case(label(p, r, s, m, w, b), case_id=f"TEST-{cid}"), {"recursion_limit": 40})
        ms = (time.perf_counter() - t) * 1000
        failed = [k for k, v in res["checks"].items() if v["status"] == "fail"]
        unknown = [k for k, v in res["checks"].items() if v["status"] == "unknown"]
        why = ("failed: " + ", ".join(failed)) if failed else ("missing: " + ", ".join(unknown)) if unknown else "all checks passed"
        passed = res["verdict"] == exp
        ok += passed
        out.append(f"| {cid} | {desc} | {p} · {r}, {s} · {w or '—'} / {b or '—'} | {exp} | {res['verdict']} | "
                   f"{res.get('iteration', 0)} | {why} | {'✅' if passed else '❌'} |")
        print(f"{cid} {'PASS' if passed else 'FAIL'}  expected={exp:22s} got={res['verdict']:22s} {ms:5.0f} ms  {why}")
    md = ["# LoomTrace – Test Results", "", f"Run on {time.strftime('%d %b %Y, %H:%M')} · **{ok}/{len(CASES)} passed**", "",
          "| ID | What it tests | Input (product · place · weaver / batch) | Expected | Got | Re-plans | Reason | Result |",
          "|---|---|---|---|---|---|---|---|", *out]
    open("TEST_RESULTS.md", "w").write("\n".join(md) + "\n")
    print(f"\n{ok}/{len(CASES)} passed → TEST_RESULTS.md")
