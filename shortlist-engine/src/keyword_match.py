"""
keyword_match.py
BM25 keyword scoring of resumes against a JD, plus explicit vocab-based
skill overlap (matched / missing required skills) that feeds explain.py.
"""

from __future__ import annotations

import re
from typing import Dict, List

from rank_bm25 import BM25Okapi

from src.extraction import extract_required_skills, extract_resume_skills

_TOKEN_RE = re.compile(r"[a-zA-Z0-9+#.-]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def keyword_score(jd_text: str, resume_texts: List[str]) -> List[float]:
    """BM25 score of the JD (as a query) against each resume (as a document).

    Returns raw BM25 scores (not yet normalized -- normalization happens
    once, batch-wide, in fusion.py).
    """
    tokenized_corpus = [_tokenize(text) for text in resume_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = _tokenize(jd_text)
    scores = bm25.get_scores(query_tokens)
    return [float(s) for s in scores]


def skill_overlap(jd_text: str, resume_texts: List[str], vocab: dict) -> List[Dict]:
    """Per-resume matched/missing required skills, matched preferred skills,
    and required-skill coverage (fraction of required skills matched).

    required_skill_coverage feeds fusion.py's keyword component so a
    resume can't paper over hard-missing required skills purely on
    semantic vibes -- see build spec's fusion enhancement.
    """
    jd_skills = extract_required_skills(jd_text, vocab)
    required = set(jd_skills["required"])
    preferred = set(jd_skills["preferred"])

    results = []
    for text in resume_texts:
        resume_skills = set(extract_resume_skills(text, vocab))
        matched_required = sorted(required & resume_skills)
        missing_required = sorted(required - resume_skills)
        matched_preferred = sorted(preferred & resume_skills)
        coverage = (len(matched_required) / len(required)) if required else 1.0
        results.append({
            "matched_required": matched_required,
            "missing_required": missing_required,
            "matched_preferred": matched_preferred,
            "resume_skills": sorted(resume_skills),
            "required_skill_coverage": coverage,
        })
    return results
