"""
ui/app.py (bonus feature)
Streamlit recruiter demo:
  - Upload JD + resumes
  - Run the pipeline, show ranked table + top-3 explanation cards
  - Bonus comparison: "Why is Candidate X ranked above Candidate Y?" --
    re-uses the same structured evidence already computed by the pipeline
    (never re-reads raw resume text, never calls an LLM, never changes
    the ranking).

Run with:
  streamlit run ui/app.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.pipeline import run_pipeline  # noqa: E402

st.set_page_config(page_title="Smart Shortlisting Engine", layout="wide")
st.title("Smart Shortlisting Engine")
st.caption(
    "Ranks resumes against a job description using BM25 keyword matching "
    "+ local sentence-embedding semantic matching (all-MiniLM-L6-v2). "
    "No external APIs are called at any point -- explanations and bias "
    "flags are template/rule-based over already-computed evidence."
)

with st.sidebar:
    st.header("1. Upload")
    jd_file = st.file_uploader("Job description (PDF)", type=["pdf"])
    resume_files = st.file_uploader(
        "Resumes (PDF, multiple)", type=["pdf"], accept_multiple_files=True
    )
    run_clicked = st.button("Run ranking", type="primary", disabled=not (jd_file and resume_files))

if "result" not in st.session_state:
    st.session_state.result = None

if run_clicked:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        jd_path = tmp / jd_file.name
        jd_path.write_bytes(jd_file.getvalue())

        resume_paths = []
        for rf in resume_files:
            rp = tmp / rf.name
            rp.write_bytes(rf.getvalue())
            resume_paths.append(str(rp))

        with st.spinner("Parsing resumes, scoring, and ranking..."):
            st.session_state.result = run_pipeline(str(jd_path), resume_paths)

result = st.session_state.result

if result:
    st.subheader("Required skills detected in JD")
    req = result["jd_required_skills"]
    col1, col2 = st.columns(2)
    col1.write("**Required:** " + (", ".join(req["required"]) or "none detected"))
    col2.write("**Preferred:** " + (", ".join(req["preferred"]) or "none detected"))

    if result["parsing_warnings"]:
        with st.expander("⚠️ Parsing warnings", expanded=False):
            for w in result["parsing_warnings"]:
                st.write(f"- **{w['file']}**: {w['detail']}")

    if result["bias_flags"]:
        with st.expander("⚠️ JD phrasing flags (bonus feature)", expanded=False):
            for flag in result["bias_flags"]:
                st.write(f"- {flag}")

    st.subheader("Ranked candidates")
    table_rows = [
        {
            "Rank": c["rank"],
            "Candidate": c["resume_id"],
            "Score": round(c["score"], 3),
            "Keyword": round(c["keyword_norm"], 3),
            "Semantic": round(c["semantic_norm"], 3),
            "Required coverage": round(c["required_skill_coverage"], 2),
            "Missing required": ", ".join(c["missing_skills"]) or "-",
        }
        for c in result["ranking"]
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.subheader("Top 3 explanations")
    for c in result["ranking"][:3]:
        with st.container(border=True):
            st.markdown(f"**#{c['rank']} — {c['resume_id']}** (score {c['score']:.3f})")
            st.text(c.get("explanation", ""))

    st.subheader("Ask: \"Why is X ranked above Y?\" (bonus comparison)")
    ids = [c["resume_id"] for c in result["ranking"]]
    colx, coly = st.columns(2)
    cand_x = colx.selectbox("Candidate X", ids, index=0)
    cand_y = coly.selectbox("Candidate Y", ids, index=min(1, len(ids) - 1))

    if st.button("Explain comparison"):
        by_id = {c["resume_id"]: c for c in result["ranking"]}
        x, y = by_id[cand_x], by_id[cand_y]

        st.write(
            f"**{cand_x}** is ranked #{x['rank']} vs **{cand_y}** at #{y['rank']} "
            f"(score {x['score']:.3f} vs {y['score']:.3f})."
        )
        st.write(
            f"Keyword match: {x['keyword_norm']:.3f} vs {y['keyword_norm']:.3f}. "
            f"Semantic match: {x['semantic_norm']:.3f} vs {y['semantic_norm']:.3f}. "
            f"Required-skill coverage: {x['required_skill_coverage']:.2f} vs "
            f"{y['required_skill_coverage']:.2f}."
        )
        only_x = sorted(set(x["matched_skills"]) - set(y["matched_skills"]))
        only_y = sorted(set(y["matched_skills"]) - set(x["matched_skills"]))
        if only_x:
            st.write(f"Required skills only {cand_x} has: {', '.join(only_x)}")
        if only_y:
            st.write(f"Required skills only {cand_y} has: {', '.join(only_y)}")
        if not only_x and not only_y:
            st.write(
                "Both matched the same required skills -- the difference comes "
                "from semantic/keyword score strength, not distinct skills."
            )
else:
    st.info("Upload a JD and resumes in the sidebar, then click Run ranking.")
