"""
pipeline.py
Orchestrates every stage end to end. Both the API and any local test/
demo script should call run_pipeline() rather than wiring the stages
together themselves.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from src.bias_check import check_bias
from src.explain import explain_top_n
from src.extraction import extract_required_skills
from src.fusion import fuse_scores, rank
from src.keyword_match import keyword_score, skill_overlap
from src.parsing import (
    chunk_resume,
    extract_text,
    full_text_or_blob,
    has_low_text_extraction,
    split_resume_sections,
)
from src.semantic_match import semantic_score_batch
from src.skill_vocab import SKILL_VOCAB


def _resume_id_from_path(path: str) -> str:
    return Path(path).stem


def run_pipeline(jd_path: str, resume_paths: List[str]) -> Dict:
    # 1. Parse JD.
    jd_text = extract_text(jd_path)
    parsing_warnings = []
    if has_low_text_extraction(jd_text):
        parsing_warnings.append({
            "file": Path(jd_path).name,
            "flag": "low_text_extraction",
            "detail": "Job description PDF yielded very little extractable text "
                      "(possibly scanned/image-only). Results may be unreliable.",
        })

    # 2. Parse + section + chunk every resume.
    resume_ids = [_resume_id_from_path(p) for p in resume_paths]
    resume_texts = []
    resume_chunk_lists = []
    for path, resume_id in zip(resume_paths, resume_ids):
        raw = extract_text(path)
        if has_low_text_extraction(raw):
            parsing_warnings.append({
                "file": Path(path).name,
                "resume_id": resume_id,
                "flag": "low_text_extraction",
                "detail": "Resume PDF yielded very little extractable text "
                          "(possibly scanned/image-only). Ranked on limited evidence.",
            })
        sections = split_resume_sections(raw)
        resume_texts.append(full_text_or_blob(sections) or raw)
        resume_chunk_lists.append(chunk_resume(sections) if raw.strip() else [])

    # 3. Keyword (BM25) scores + explicit skill overlap / required-skill coverage.
    kw_scores = keyword_score(jd_text, resume_texts)
    overlaps = skill_overlap(jd_text, resume_texts, SKILL_VOCAB)
    required_skill_coverage = [o["required_skill_coverage"] for o in overlaps]

    # 4. Semantic (requirement <-> resume-chunk) scores + evidence.
    semantic_results = semantic_score_batch(jd_text, resume_chunk_lists)
    sem_scores = [r["semantic_score"] for r in semantic_results]

    # 5. Fuse.
    fused = fuse_scores(kw_scores, sem_scores, required_skill_coverage)

    # 6. Assemble per-candidate records.
    candidates = []
    for i, resume_id in enumerate(resume_ids):
        candidates.append({
            "resume_id": resume_id,
            "score": fused["final_score"][i],
            "keyword_norm": fused["keyword_norm"][i],
            "semantic_norm": fused["semantic_norm"][i],
            "required_skill_coverage": required_skill_coverage[i],
            "matched_skills": overlaps[i]["matched_required"],
            "missing_skills": overlaps[i]["missing_required"],
            "matched_preferred": overlaps[i]["matched_preferred"],
            "requirement_evidence": semantic_results[i]["requirement_evidence"],
        })

    ranked = rank(candidates)

    # 7. Explanations for the top 3 only (template-based, no LLM).
    ranked = explain_top_n(ranked, n=3)

    # Drop the bulky per-requirement evidence from the general payload once
    # explanations have consumed it, to keep the API response lean -- but
    # keep it on the top 3 so a UI can show more than one quote if desired.
    for c in ranked[3:]:
        c.pop("requirement_evidence", None)

    # 8. Bonus: JD bias/narrow-phrasing flags (heuristic only).
    bias_flags = check_bias(jd_text)

    return {
        "jd_required_skills": extract_required_skills(jd_text, SKILL_VOCAB),
        "ranking": ranked,
        "parsing_warnings": parsing_warnings,
        "bias_flags": bias_flags,
    }
