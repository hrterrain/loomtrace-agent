"""LoomTrace website - verify the GI tag of a handloom product."""
import json
import time

import pandas as pd
import streamlit as st

from loomtrace import tools as T
from loomtrace.agent import build_graph, get_llm, new_case
from loomtrace.data import CENSUS, GI_REGISTRY, WEAVERS
from loomtrace.evaluate import evaluate

st.set_page_config(page_title="LoomTrace · Verify GI-tagged handloom", page_icon="🧵", layout="wide",
                   initial_sidebar_state="collapsed")

PAGE = st.query_params.get("page", "home")

# ------------------------------------------------------------------ styles --
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#1d1a2e;--indigo:#2b2a6b;--madder:#a3322a;--zari:#c79a2b;--paper:#faf6ee;--muted:#6b6577;--line:#e8e0cf;
--ok:#1f7a4d;--warn:#b7791f;--bad:#b42318;}
header[data-testid="stHeader"],#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stSidebarCollapsedControl"]{display:none!important;}
html,body,.stApp,[class*="css"]{font-family:'Inter',sans-serif;color:var(--ink);}
.stApp{background:var(--paper);}
.block-container{padding-top:0!important;max-width:1180px;}
h1,h2,h3{font-family:'Fraunces',serif!important;letter-spacing:-.015em;color:var(--ink);}
a{text-decoration:none!important;}
/* nav */
.nav{display:flex;align-items:center;justify-content:space-between;padding:18px 0;border-bottom:1px solid var(--line);margin-bottom:8px;}
.brand{font-family:'Fraunces',serif;font-weight:700;font-size:1.45rem;color:var(--ink)!important;display:flex;gap:10px;align-items:center;}
.logo{width:34px;height:34px;border-radius:9px;background:
 repeating-linear-gradient(90deg,var(--zari) 0 3px,var(--indigo) 3px 7px);box-shadow:inset 0 0 0 2px rgba(255,255,255,.25);}
.links a{color:var(--ink)!important;margin-left:26px;font-weight:500;font-size:.95rem;opacity:.75;}
.links a.on{opacity:1;border-bottom:2px solid var(--madder);padding-bottom:4px;}
.links a.cta{background:var(--madder);color:#fff!important;padding:9px 18px;border-radius:99px;opacity:1;}
/* hero */
.hero{display:grid;grid-template-columns:1.2fr 1fr;gap:40px;align-items:center;padding:56px 0 40px;}
.eyebrow{color:var(--madder);font-weight:600;font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;}
.hero h1{font-size:3.4rem;line-height:1.05;margin:.6rem 0 1rem;}
.hero p{font-size:1.12rem;color:#4b4458;line-height:1.6;max-width:540px;}
.btn{display:inline-block;padding:13px 24px;border-radius:99px;font-weight:600;margin:18px 10px 0 0;}
.btn-p{background:var(--madder);color:#fff!important;}
.btn-s{border:1.5px solid var(--ink);color:var(--ink)!important;}
.weave{height:340px;border-radius:28px;position:relative;overflow:hidden;box-shadow:0 30px 60px -30px rgba(43,42,107,.6);
 background:linear-gradient(135deg,#2b2a6b,#5a1f3d);}
.weave:before{content:"";position:absolute;inset:0;opacity:.35;background:
 repeating-linear-gradient(90deg,#c79a2b 0 3px,transparent 3px 16px),repeating-linear-gradient(0deg,#fff 0 1px,transparent 1px 12px);}
.weave .tag{position:absolute;left:28px;bottom:28px;right:28px;background:#fff;border-radius:18px;padding:18px 20px;}
.weave .tag b{font-family:'Fraunces',serif;font-size:1.15rem;}
.pill{display:inline-block;font-size:.72rem;font-weight:600;padding:4px 10px;border-radius:99px;}
.p-ok{background:#e3f4ea;color:var(--ok)}.p-bad{background:#fde7e5;color:var(--bad)}.p-warn{background:#fdf1dc;color:var(--warn)}
.p-n{background:#f1ecdf;color:#4b4458}
/* sections */
.sec{padding:44px 0 10px;}
.sec h2{font-size:2.1rem;margin-bottom:.3rem;}
.lead{color:var(--muted);font-size:1.02rem;margin-bottom:24px;}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:22px;}
.num{width:36px;height:36px;border-radius:50%;background:var(--indigo);color:#fff;display:flex;align-items:center;
 justify-content:center;font-weight:700;margin-bottom:12px;}
.card h4{margin:.2rem 0 .4rem;font-size:1.05rem;}
.card p{color:var(--muted);font-size:.92rem;margin:0;line-height:1.55;}
.prod{overflow:hidden;padding:0;}
.prod .sw{height:110px;}
.prod .bd{padding:18px 20px;}
.big{font-family:'Fraunces',serif;font-size:1.9rem;font-weight:700;}
/* verify */
.panel{background:#fff;border:1px solid var(--line);border-radius:22px;padding:26px 28px;}
.report{background:#fff;border:1px solid var(--line);border-radius:22px;overflow:hidden;}
.rhead{padding:26px 28px;color:#fff;}
.r-Supported{background:linear-gradient(135deg,#1f7a4d,#2f9e66);}
.r-Conflicting{background:linear-gradient(135deg,#8f1d17,#c2412d);}
.r-Insufficient{background:linear-gradient(135deg,#8a5a12,#c58a1c);}
.rhead .v{font-family:'Fraunces',serif;font-size:2rem;font-weight:700;}
.rhead .s{opacity:.92;margin-top:4px;}
.rbody{padding:22px 28px;}
.kv{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;padding-bottom:18px;border-bottom:1px solid var(--line);}
.kv .k{color:var(--muted);font-size:.74rem;text-transform:uppercase;letter-spacing:.06em;}
.kv .val{font-weight:600;margin-top:3px;}
.row{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid #f3eee2;}
.ic{flex:0 0 26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.8rem;}
.ic-pass{background:#e3f4ea;color:var(--ok)}.ic-fail{background:#fde7e5;color:var(--bad)}.ic-unknown{background:#fdf1dc;color:var(--warn)}
.row .t{font-weight:600;font-size:.93rem}.row .d{color:var(--muted);font-size:.86rem}
.srcs span{display:inline-block;background:#f6f1e5;border-radius:8px;padding:5px 10px;margin:4px 6px 0 0;font-size:.8rem;}
.empty{text-align:center;padding:70px 20px;color:var(--muted);}
.stButton>button{border-radius:99px;font-weight:600;padding:.6rem 1rem;}
.stButton>button[kind="primary"]{background:var(--madder);border-color:var(--madder);}
.foot{margin-top:60px;padding:28px 0;border-top:1px solid var(--line);display:flex;justify-content:space-between;
 color:var(--muted);font-size:.84rem;}
@media(max-width:800px){.hero,.grid3,.grid4,.kv{grid-template-columns:1fr}.hero h1{font-size:2.4rem}.links a:not(.cta){display:none}}
</style>""", unsafe_allow_html=True)


def nav():
    def a(p, label, cls=""):
        on = " on" if PAGE == p and not cls else ""
        return f'<a class="{cls}{on}" href="?page={p}" target="_self">{label}</a>'
    st.markdown(f"""<div class="nav"><a class="brand" href="?page=home" target="_self"><span class="logo"></span>LoomTrace</a>
    <div class="links">{a('home','Home')}{a('products','GI Products')}{a('about','How it works')}{a('track','Track report')}{a('admin','Admin')}
    {a('verify','Verify a product','cta')}</div></div>""", unsafe_allow_html=True)


def footer():
    st.markdown("""<div class="foot"><div><b>LoomTrace</b> · Protecting India's handloom heritage<br>
    Advisory verification only — not a legal certification.</div>
    <div style="text-align:right">Data: IP India GI Registry · Handloom Census 2019-20 (Ministry of Textiles)<br>
    BMSCE · B.E. CSE (Data Science)</div></div>""", unsafe_allow_html=True)


SWATCH = {"Kancheepuram Silk": "linear-gradient(135deg,#7a1424,#c79a2b)",
          "Pochampalli Ikat": "repeating-linear-gradient(45deg,#1f3a6b 0 14px,#d9472b 14px 28px,#f3e2c0 28px 34px)",
          "Banaras Brocades and Sarees": "radial-gradient(circle at 30% 40%,#e6c46a 0 6px,transparent 7px) 0 0/26px 26px,linear-gradient(135deg,#3d1050,#8a1e4a)"}
BLURB = {"Kancheepuram Silk": "Pure mulberry silk with gold zari, body and border interlocked by the korvai technique.",
         "Pochampalli Ikat": "Tie-and-dye resist patterns dyed into the yarn before it reaches the loom.",
         "Banaras Brocades and Sarees": "Silk brocade with gold and silver zari, Mughal-inspired buti and bel motifs."}

SOURCE_NAMES = {"IPINDIA-GI-REG": "IP India GI Registry", "PIB-GI-2021": "Govt. of India GI catalogue (PIB / TRIFED, 2021)", "HLCENSUS-2019-20": "Handloom Census 2019-20",
                "SIM-WEAVER": "Weaver registry", "SIM-PROV": "Production records", "GI15": "GI application No. 15",
                "GI4": "GI application No. 4", "GI99": "GI application No. 99"}
CHECK_NAMES = {"product_registered": "Product is GI-registered", "gi_document_support": "Matches the official GI description",
               "census_plausible": "Active handloom weaving in the state", "region_in_gi_area": "Made inside the GI region",
               "state_matches": "State matches the GI registration", "material_consistent": "Material matches the GI specification",
               "weaver_registered": "Weaver is registered", "weaver_cluster": "Weaver belongs to this product's cluster",
               "batch_found": "Production batch on record", "batch_weaver_match": "Batch was woven by this weaver"}


WEAVERS_COVERED = sum(CENSUS[s]["weavers"] for s in {i["state"] for i in GI_REGISTRY.values()})


def gi_label(info):
    return f"GI No. {info['gi_no']}" if info.get("gi_no") else "Registered GI"


def swatch(p):
    h = sum(map(ord, p)) % 360
    return (f"repeating-linear-gradient(90deg,hsl({h},55%,32%) 0 10px,hsl({(h+40)%360},60%,45%) 10px 16px,"
            f"#c79a2b 16px 18px)")


def friendly_source(sid):
    key = sid.split("#")[0].split("-p")[0]
    name = SOURCE_NAMES.get(key, sid)
    page = f", page {sid.split('-p')[1]}" if sid.startswith("GI") and "-p" in sid else ""
    return name + page


@st.cache_resource
def graph():
    return build_graph(get_llm())


nav()

# ==================================================================== HOME ==
if PAGE == "home":
    st.markdown("""<div class="hero"><div>
      <div class="eyebrow">GI-tag verification for handloom</div>
      <h1>Is your handloom saree the real thing?</h1>
      <p>Enter the details on the product label. LoomTrace checks them against official government records and
      gives you a clear answer with the sources it used.</p>
      <a class="btn btn-p" href="?page=verify" target="_self">Verify a product →</a>
      <a class="btn btn-s" href="?page=about" target="_self">How it works</a></div>
      <div class="weave"><div class="tag"><span class="pill p-ok">✓ Supported</span><br>
      <b>Kancheepuram Silk · GI No. 15</b><div style="color:#6b6577;font-size:.88rem;margin-top:4px">
      Woven in Kancheepuram, Tamil Nadu · 10 of 10 checks passed · 6 official sources</div></div></div></div>""",
                unsafe_allow_html=True)
    st.markdown(f"""<div class="grid4">
      <div class="card"><div class="big">{len(GI_REGISTRY)}</div><p>GI-tagged handloom products covered</p></div>
      <div class="card"><div class="big">10</div><p>independent checks on every product</p></div>
      <div class="card"><div class="big">{WEAVERS_COVERED / 1e5:.1f} L</div><p>handloom weavers in covered states (Census 2019-20)</p></div>
      <div class="card"><div class="big">100%</div><p>verdicts backed by a cited source</p></div></div>""",
                unsafe_allow_html=True)
    st.markdown("""<div class="sec"><h2>Three steps, one clear answer</h2>
      <div class="lead">No account needed. Results in seconds.</div><div class="grid3">
      <div class="card"><div class="num">1</div><h4>Share the label</h4><p>Type the label details or upload a photo of the product tag.</p></div>
      <div class="card"><div class="num">2</div><h4>We check the records</h4><p>The GI registry, official GI documents, the national handloom census, and weaver and batch records.</p></div>
      <div class="card"><div class="num">3</div><h4>Get a cited verdict</h4><p>Supported, Conflicting, or sent to an expert for review when the evidence isn't enough.</p></div>
      </div></div>""", unsafe_allow_html=True)
    st.markdown("""<div class="sec"><div class="card" style="background:var(--indigo);color:#fff;border:none;padding:34px;
      display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap">
      <div><h2 style="color:#fff;margin:0">Buying a GI saree online?</h2>
      <div style="opacity:.85;margin-top:6px">Check the seller's claim before you pay.</div></div>
      <a class="btn btn-p" style="margin:0;background:var(--zari);color:#1d1a2e!important" href="?page=verify" target="_self">Verify now →</a></div></div>""",
                unsafe_allow_html=True)

# ================================================================ PRODUCTS ==
elif PAGE == "products":
    st.markdown('<div class="sec"><div class="eyebrow">Covered products</div><h2>GI-tagged handloom we verify</h2>'
                '<div class="lead">Each product is protected by a Geographical Indication registered with IP India.</div></div>',
                unsafe_allow_html=True)
    cards = ""
    for p, info in GI_REGISTRY.items():
        cards += f"""<div class="card prod"><div class="sw" style="background:{SWATCH.get(p) or swatch(p)}"></div><div class="bd">
        <span class="pill p-n">{gi_label(info)}</span><h3 style="margin:.6rem 0 .2rem">{p}</h3>
        <p>{BLURB.get(p) or info.get('summary', '')[:150].rsplit(' ', 1)[0] + '…'}</p><p style="margin-top:12px"><b style="color:#1d1a2e">GI region:</b> {', '.join(info['districts'])}, {info['state']}</p>
        <p style="margin-top:6px"><b style="color:#1d1a2e">Materials:</b> {', '.join(info['materials']) or 'not specified in GI record'}</p>
        <p style="margin-top:6px"><b style="color:#1d1a2e">{CENSUS[info['state']]['weavers']:,}</b> handloom weavers in {info['state']}</p>
        <p style="margin-top:6px;font-size:.78rem">Source: {friendly_source(info['source_id'])}</p>
        </div></div>"""
    st.markdown(f'<div class="grid3">{cards}</div>', unsafe_allow_html=True)

# =================================================================== ABOUT ==
elif PAGE == "about":
    st.markdown('<div class="sec"><div class="eyebrow">How it works</div><h2>Evidence, not guesswork</h2>'
                '<div class="lead">Every answer is built from official records, and every answer shows its sources.</div></div>',
                unsafe_allow_html=True)
    st.markdown("""<div class="grid3">
    <div class="card"><h4>📄 Reads the label</h4><p>Picks out the product name, region, weaver ID and batch number, even when the seller uses a local name like "Kanjivaram".</p></div>
    <div class="card"><h4>🏛️ Checks official records</h4><p>Compares the claim with the IP India GI Registry, the GI application documents and the 4th All India Handloom Census.</p></div>
    <div class="card"><h4>🧵 Traces the maker</h4><p>Confirms the weaver belongs to the right cluster and the production batch was woven on their loom.</p></div>
    <div class="card"><h4>🔁 Looks again if unsure</h4><p>If the first search is weak, it refines the search and checks again, up to three times.</p></div>
    <div class="card"><h4>📌 Cites every answer</h4><p>Each verdict lists the exact records and document pages it relied on.</p></div>
    <div class="card"><h4>🧑‍⚖️ Asks a human when needed</h4><p>Missing details are never guessed. The case goes to an expert reviewer instead.</p></div>
    </div>""", unsafe_allow_html=True)
    st.markdown("""<div class="sec"><h2>What the verdicts mean</h2><div class="grid3">
    <div class="card"><span class="pill p-ok">✓ Supported</span><p style="margin-top:10px">Every check passed and the evidence agrees with the claim.</p></div>
    <div class="card"><span class="pill p-bad">✕ Conflicting evidence</span><p style="margin-top:10px">Something doesn't match: wrong region, a weaver from another cluster, or a different product.</p></div>
    <div class="card"><span class="pill p-warn">? Needs review</span><p style="margin-top:10px">Key details are missing or unverifiable, so an expert will review it.</p></div>
    </div><p style="color:#6b6577;margin-top:18px;font-size:.88rem">LoomTrace gives an advisory verdict and does not legally certify a product.
    Individual weaver and batch records shown are demonstration data.</p></div>""", unsafe_allow_html=True)

# ================================================================== VERIFY ==
elif PAGE == "verify":
    st.markdown('<div class="sec" style="padding-top:28px"><div class="eyebrow">Verify a product</div>'
                '<h2>Check a GI-tag claim</h2><div class="lead">Fill in what\'s printed on the label or tag.</div></div>',
                unsafe_allow_html=True)
    EX = {"Try an example…": None,
          "Kanjivaram silk saree": ("Kanjivaram Silk Saree", "Thiruvallur", "Tamil Nadu", "mulberry silk", "WV-KAN-001", "B-KAN-0010"),
          "Pochampalli ikat saree": ("Pochampalli Ikat", "Nalgonda", "Telangana", "cotton", "WV-POC-003", "B-POC-0030"),
          "Sambalpuri ikat saree (Odisha)": ("Sambalpuri Ikat Saree", "Bargarh", "Odisha", "", "WV-SAM-002", "B-SAM-0020"),
          "Muga silk mekhela (Assam)": ("Muga Silk Mekhela", "Sualkuchi", "Assam", "muga silk", "WV-MUG-001", "B-MUG-0010"),
          "Chanderi saree claimed from Varanasi": ("Chanderi Saree", "Varanasi", "Uttar Pradesh", "silk", "WV-CHA-001", "B-CHA-0010"),
          "Banarasi saree from Surat": ("Banarasi Silk Saree", "Surat", "Gujarat", "silk", "WV-BAN-002", "B-BAN-0020"),
          "Banarasi with no maker details": ("Banaras Brocades and Sarees", "Varanasi", "Uttar Pradesh", "silk", "", "")}
    left, right = st.columns([5, 7], gap="large")
    with left:
        with st.container(border=True):
            ex = st.selectbox("Example", list(EX.keys()), label_visibility="collapsed")
            d = EX[ex] or ("", "", "", "", "", "")
            k = ex
            product = st.text_input("Product name", d[0], placeholder="e.g. Kanjivaram Silk Saree", key=f"p{k}")
            c1, c2 = st.columns(2)
            region = c1.text_input("Region / district", d[1], placeholder="e.g. Kancheepuram", key=f"r{k}")
            state = c2.text_input("State", d[2], placeholder="e.g. Tamil Nadu", key=f"s{k}")
            material = st.text_input("Material", d[3], placeholder="e.g. mulberry silk", key=f"m{k}")
            c3, c4 = st.columns(2)
            weaver = c3.text_input("Weaver ID", d[4], placeholder="WV-KAN-001", key=f"w{k}")
            batch = c4.text_input("Batch ID", d[5], placeholder="B-KAN-0010", key=f"b{k}")
            img = st.file_uploader("Or upload a photo of the tag (optional)", type=["png", "jpg", "jpeg"])
            go = st.button("Verify product", type="primary", use_container_width=True)

    with right:
        if go:
            if not product.strip() and not img:
                st.warning("Please enter at least the product name.")
                go = False
            elif product.strip() and not T.canonical_product(product):
                go = False
                st.session_state.pop("res", None)
                st.session_state["uncovered"] = {"product": product, "region": region, "state": state,
                                                 "material": material, "weaver_id": weaver, "batch_id": batch}
        unc = st.session_state.get("uncovered")
        if unc and not go:
            names = "".join(f"<li>{p} ({i['state']})</li>" for p, i in GI_REGISTRY.items())
            st.markdown(f"""<div class="report"><div class="rhead" style="background:linear-gradient(135deg,#2b2a6b,#4a3f8f)">
              <div class="v">Not covered yet</div><div class="s">“{unc['product']}” isn't one of the GI products we can verify automatically.</div></div>
              <div class="rbody"><b>We currently verify:</b><ul style="color:#4b4458">{names}</ul>
              <p style="color:#6b6577;font-size:.9rem">You can still send this claim to one of our reviewers, who will check it manually.</p></div></div>""",
                        unsafe_allow_html=True)
            if st.button("Send to an expert reviewer", type="primary"):
                cid = new_case("")["case_id"]
                con = T._db()
                con.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?)",
                            (cid, json.dumps(unc), "Not covered", 0.0, 0, "[]", time.time()))
                con.commit(); con.close()
                qid = T.request_review(cid, "Product not covered by automated verification", unc)
                st.session_state.pop("uncovered")
                st.success(f"Sent for expert review. Your reference is **{cid}** (queue #{qid}). "
                           f"Check its status any time on the Track report page.")
        if go:
            st.session_state.pop("uncovered", None)
            label = "\n".join(f"{k}: {v}" for k, v in [("Product", product), ("Region", region), ("State", state),
                              ("Material", material), ("Weaver ID", weaver), ("Batch ID", batch)] if v.strip())
            label += "\nGI Tagged"
            msgs = {"extract": "Reading the label…", "planner": "Planning the checks…", "retriever": "Searching official records…",
                    "verifier": "Verifying weaver and batch…", "grader": "Weighing the evidence…", "guardrail": "Preparing your report…"}
            box = st.empty()
            final = new_case(label, img.getvalue() if img else None)
            for i, upd in enumerate(graph().stream(dict(final), {"recursion_limit": 40}, stream_mode="updates")):
                for node, out in upd.items():
                    for kk, v in out.items():
                        final[kk] = final.get(kk, []) + v if kk in ("evidence", "trace") else v
                    box.markdown(f'<div class="panel empty"><div style="font-size:2rem">🧵</div><b>{msgs[node]}</b>'
                                 f'<div style="margin-top:14px;height:6px;background:#f1ecdf;border-radius:9px;overflow:hidden">'
                                 f'<div style="width:{min(95, 12 + i * 11)}%;height:100%;background:var(--madder)"></div></div></div>',
                                 unsafe_allow_html=True)
                    time.sleep(0.3)
            box.empty()
            st.session_state["res"] = final

        res = st.session_state.get("res")
        if res:
            cls = res["verdict"].split()[0]
            head = {"Supported": ("✓ GI claim supported", "The details on this label match official records."),
                    "Conflicting": ("✕ Conflicting evidence", "Some details on this label don't match official records."),
                    "Insufficient": ("? Needs expert review", "We couldn't confirm this claim, so it has been sent to a reviewer.")}[cls]
            f, c = res["fields"], res["checks"]
            reg = next((e["data"] for e in res["evidence"] if e.get("tool") == "gi_registry_lookup" and e["ok"]), None)
            wv = WEAVERS.get((f.get("weaver_id") or "").upper())
            passed = sum(v["status"] == "pass" for v in c.values())
            kv = [("Product", reg["product"] if reg else (f.get("product") or "—")),
                  ("GI status", gi_label(reg) if reg else "Not found"),
                  ("Made in", ", ".join(filter(None, [f.get("region"), f.get("state")])) or "—"),
                  ("Weaver", wv["name"] if wv else (f.get("weaver_id") or "Not provided"))]
            rows = "".join(f'<div class="row"><div class="ic ic-{v["status"]}">{"✓" if v["status"]=="pass" else "✕" if v["status"]=="fail" else "?"}</div>'
                           f'<div><div class="t">{CHECK_NAMES.get(k, k)}</div><div class="d">{v["why"]}</div></div></div>'
                           for k, v in sorted(c.items(), key=lambda x: {"fail": 0, "unknown": 1, "pass": 2}[x[1]["status"]]))
            srcs = "".join(f"<span>📄 {n}</span>" for n in dict.fromkeys(friendly_source(s) for s in res["citations"])) or "<span>None</span>"
            ref = f" · Reference #{res['escalated']['queue_id']}" if res.get("escalated") else ""
            st.markdown(f"""<div class="report"><div class="rhead r-{cls}"><div class="v">{head[0]}</div>
              <div class="s">{head[1]}</div><div class="s" style="font-size:.85rem;margin-top:10px">
              {passed} of {len(c)} checks passed · Report {res['case_id']}{ref}</div></div>
              <div class="rbody"><div class="kv">{''.join(f'<div><div class="k">{a}</div><div class="val">{b}</div></div>' for a, b in kv)}</div>
              <h4 style="margin:18px 0 4px">What we checked</h4>{rows}
              <h4 style="margin:20px 0 4px">Sources</h4><div class="srcs">{srcs}</div>
              <p style="color:#6b6577;font-size:.8rem;margin-top:18px">Advisory result based on available records — not a legal certification.</p>
              </div></div>""", unsafe_allow_html=True)
            st.markdown("")
            if res.get("escalated"):
                st.info(f"🧑‍⚖️ An expert reviewer will look at this case. Save your reference **{res['case_id']}** "
                        f"and check it on the **Track report** page.")
            else:
                with st.container(border=True):
                    st.markdown("**Disagree with this result?** Send it to an expert reviewer for a manual check.")
                    why = st.text_input("Tell the reviewer why (optional)", key="why",
                                        placeholder="e.g. I have the original purchase invoice from the cooperative")
                    if st.button("Request expert review"):
                        qid = T.request_review(res["case_id"], "Customer requested review" + (f": {why}" if why else ""),
                                               res["fields"])
                        res["escalated"] = {"queue_id": qid}
                        st.rerun()
        elif not go and not st.session_state.get("uncovered"):
            st.markdown('<div class="panel empty"><div style="font-size:2.6rem">🧵</div>'
                        '<h3 style="margin:.4rem 0">Your report will appear here</h3>'
                        'Enter the label details, or pick an example, and press <b>Verify product</b>.</div>',
                        unsafe_allow_html=True)

# =================================================================== TRACK ==
elif PAGE == "track":
    st.markdown('<div class="sec" style="padding-top:28px"><div class="eyebrow">Track a report</div>'
                '<h2>Check your review status</h2><div class="lead">Enter the reference shown on your report, e.g. CASE-1A2B3C4D.</div></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    ref = c1.text_input("Reference", st.query_params.get("ref", ""), label_visibility="collapsed", placeholder="CASE-…")
    c2.button("Check status", type="primary", use_container_width=True)
    if ref.strip():
        s = T.case_status(ref)
        if not s:
            st.warning("We couldn't find a report with that reference.")
        else:
            d, qd = s["decision"], s["queue"]
            if d:
                cls = d["verdict"].split()[0]
                title = {"Supported": "✓ Confirmed authentic by reviewer", "Conflicting": "✕ Not authentic — reviewer decision",
                         "Insufficient": "? Reviewer could not confirm"}[cls]
                when = time.strftime("%d %b %Y, %H:%M", time.localtime(d["decided"]))
                body = f"Reviewer note: {d['note']}" if d["note"] else "No note added."
                head = f'<div class="rhead r-{cls}"><div class="v">{title}</div><div class="s">Decided {when}</div></div>'
            elif qd:
                head = ('<div class="rhead" style="background:linear-gradient(135deg,#2b2a6b,#4a3f8f)"><div class="v">⏳ Under expert review</div>'
                        f'<div class="s">Queue #{qd["id"]} · reason: {qd["reason"]}</div></div>')
                body = "A reviewer will check the official records and the weaving cluster. Check back here for the decision."
            else:
                cls = s["auto_verdict"].split()[0]
                head = f'<div class="rhead r-{cls}"><div class="v">{s["auto_verdict"]}</div><div class="s">Automated result · no review requested</div></div>'
                body = "This result was not sent for expert review."
            steps = [("Submitted", True), ("Automated check", s["auto_verdict"] != "Not covered"),
                     ("Expert review", bool(qd)), ("Final decision", bool(d))]
            tl = "".join(f'<div class="row"><div class="ic {"ic-pass" if ok else "ic-unknown"}">{"✓" if ok else "·"}</div>'
                         f'<div class="t">{n}</div></div>' for n, ok in steps)
            st.markdown(f'<div class="report">{head}<div class="rbody"><p>{body}</p>'
                        f'<p style="color:#6b6577;font-size:.85rem">Automated verdict: {s["auto_verdict"]} · Reference {s["case_id"]}</p>'
                        f'{tl}</div></div>', unsafe_allow_html=True)

# =================================================================== ADMIN ==
elif PAGE == "admin":
    st.markdown('<div class="sec" style="padding-top:28px"><div class="eyebrow">Reviewer dashboard</div>'
                '<h2>Cases & review queue</h2></div>', unsafe_allow_html=True)
    con = T._db()
    hist = pd.read_sql("SELECT case_id, verdict, grade, created FROM cases WHERE case_id LIKE 'CASE-%' ORDER BY created DESC", con)
    q = pd.read_sql("SELECT id, case_id, reason, claim, status FROM review_queue WHERE case_id LIKE 'CASE-%' ORDER BY id DESC", con)
    vc = hist["verdict"].value_counts()
    st.markdown(f"""<div class="grid4">
      <div class="card"><div class="big">{len(hist)}</div><p>Products checked</p></div>
      <div class="card"><div class="big" style="color:var(--ok)">{vc.get('Supported', 0)}</div><p>Supported</p></div>
      <div class="card"><div class="big" style="color:var(--bad)">{vc.get('Conflicting evidence', 0)}</div><p>Conflicting</p></div>
      <div class="card"><div class="big" style="color:var(--warn)">{(q['status'] == 'open').sum()}</div><p>Awaiting review</p></div>
      </div>""", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Review queue", "Recent checks", "Accuracy report"])
    with t1:
        if q.empty:
            st.info("Nothing to review right now.")
        decs = pd.read_sql("SELECT queue_id, decision, note FROM decisions", con).set_index("queue_id")
        for _, r in q.head(25).iterrows():
            claim = json.loads(r["claim"])
            qid = int(r["id"])
            with st.container(border=True):
                details = " · ".join(f"{k.replace('_', ' ')}: **{v}**" for k, v in claim.items()
                                     if v not in (None, "", True, False))
                st.markdown(f"**#{qid} · {r['case_id']}**  \n{details}  \n"
                            f"<span style='color:#b7791f;font-size:.88rem'>⚠ {r['reason']}</span>", unsafe_allow_html=True)
                if r["status"] == "open":
                    note = st.text_input("Reviewer note (shown to the customer)", key=f"n{qid}",
                                         placeholder="e.g. Confirmed with the weavers' cooperative society")
                    b1, b2, b3 = st.columns(3)
                    if b1.button("✓ Confirm authentic", key=f"a{qid}", use_container_width=True):
                        T.decide(qid, "Supported", note); st.rerun()
                    if b2.button("✕ Not authentic", key=f"r{qid}", use_container_width=True):
                        T.decide(qid, "Conflicting evidence", note); st.rerun()
                    if b3.button("? Cannot confirm", key=f"i{qid}", use_container_width=True):
                        T.decide(qid, "Insufficient evidence", note); st.rerun()
                elif qid in decs.index:
                    d = decs.loc[qid]
                    pill = {"Supported": "p-ok", "Conflicting evidence": "p-bad"}.get(d["decision"], "p-warn")
                    st.markdown(f"<span class='pill {pill}'>Reviewer: {d['decision']}</span> "
                                f"<span style='color:#6b6577;font-size:.86rem'>{d['note'] or ''}</span>",
                                unsafe_allow_html=True)
    with t2:
        if hist.empty:
            st.info("No checks yet.")
        else:
            hist["created"] = pd.to_datetime(hist["created"], unit="s").dt.strftime("%d %b, %H:%M")
            st.dataframe(hist.rename(columns={"case_id": "Report", "verdict": "Verdict", "grade": "Confidence",
                                              "created": "Checked at"}), use_container_width=True, hide_index=True)
    with t3:
        st.caption("45 labelled test cases (3 products × 3 verdicts × 5), compared against a simple one-lookup baseline.")
        if st.button("Run accuracy report", type="primary"):
            with st.spinner("Running 45 test cases…"):
                st.session_state["eval"] = evaluate()
        if "eval" in st.session_state:
            rows, m = st.session_state["eval"]
            a_, b_ = m["agent"], m["baseline"]
            st.markdown(f"""<div class="grid4">
              <div class="card"><div class="big">{a_['accuracy']:.0%}</div><p>Accuracy (baseline {b_['accuracy']:.0%})</p></div>
              <div class="card"><div class="big">{a_['abstention']:.0%}</div><p>Unclear cases sent to review (baseline {b_['abstention']:.0%})</p></div>
              <div class="card"><div class="big">{a_['citation_rate']:.0%}</div><p>Verdicts with citations</p></div>
              <div class="card"><div class="big">{a_['macro_f1']:.2f}</div><p>Macro-F1 (baseline {b_['macro_f1']:.2f})</p></div></div>""",
                        unsafe_allow_html=True)
            df = pd.DataFrame(rows)
            per = df.groupby("gold").apply(lambda g: pd.Series({"LoomTrace": (g.agent == g.gold).mean(),
                                                                 "Baseline": (g.baseline == g.gold).mean()}), include_groups=False)
            st.bar_chart(per, color=["#2b2a6b", "#c79a2b"], stack=False)
    con.close()

footer()
