# LoomTrace — GI-tag verification agent

Agentic AI (26CD7PEAAI) mini-project · B.E. CSE (Data Science), BMSCE · **Team 10**
Sudeeksha (1BM23CD027) · Khushi Vernekar (1BM23CD026) · Trishul J (1BM23CD066) · Geetha R (1BM24CD400)
Course lead: Dr. Kalyan Nagaraj

📄 Final report: [`LoomTrace_Report_Team10.pdf`](LoomTrace_Report_Team10.pdf) (LaTeX source in [`report/`](report/))

Checks whether a handloom product's GI-tag claim is backed by official evidence and returns an advisory verdict:
**Supported**, **Conflicting evidence**, or **Insufficient evidence (human review)**.
Scope: 15 registered handloom GIs — Kancheepuram Silk (GI 15), Pochampalli Ikat (GI 4), Banaras Brocades & Sarees (GI 99), plus 12 from the Govt. of India GI catalogue (PIB/TRIFED, 2021). Census data: 4th All India Handloom Census 2019-20 (PIB release 2202869). Weaver and batch records are **simulated**.

## Run
```bash
git clone https://github.com/hrterrain/loomtrace-agent.git && cd loomtrace-agent
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export GROQ_API_KEY=...        # optional: enables Llama 3.1 8B (llama-3.1-8b-instant)
.venv/bin/streamlit run app.py
.venv/bin/python -m loomtrace.evaluate      # 45-case evaluation vs baseline
.venv/bin/python -m loomtrace.experiments   # report numbers: 3 reps + A/B (re-plan loop on/off) -> results/
.venv/bin/python run_tests.py               # 15 demo cases -> TEST_RESULTS.md
```

## Structure
- `loomtrace/agent.py`: LangGraph state graph: Extract → Planner → Retriever agent → Verifier agent → Grader → (re-plan ≤3 | Guardrail). CaseState is checkpointed to SQLite after every node.
- `loomtrace/tools.py`: 7 typed (Pydantic) tools: extract_label, gi_registry_lookup, gi_doc_search, census_lookup, weaver_lookup, provenance_lookup, escalate_to_human. Each returns a source_id for citations.
- `loomtrace/data.py`: official GI registry + Handloom Census 2019-20 figures, GI document passages, simulated weaver/batch records (labelled).
- `loomtrace/evaluate.py`: 45-case golden set (3×3×5), metrics, baseline.
- `loomtrace/experiments.py`: repeated evaluation and A/B experiment used in the report.
- `run_tests.py`: 15 hand-written demo cases.
- `report/`: LaTeX source of the final report (compile `main.tex` with logo.png alongside).
- `app.py`: Streamlit UI: verify (live trace + cited verdict), agent graph, human review queue, evaluation dashboard, data & tools.

Without a Groq key the agent runs in deterministic rule mode (all reported results use this mode). EasyOCR is optional (`pip install easyocr`) for image labels.
Document search uses BM25 here; swap in Chroma + bge-small for production.
