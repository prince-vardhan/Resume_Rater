"""
fusion.py
Normalize keyword and semantic scores independently within the current
batch, combine them with fixed, citable weights, and produce the final
ranked list.

Weights live here as constants specifically so they're easy to find,
tune, and explain to judges.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

# --- Fusion weights (tune here) ---
KEYWORD_WEIGHT = 0.40
SEMANTIC_WEIGHT = 0.60

# Within the keyword side, blend raw BM25 signal with explicit required-
# skill coverage so semantic similarity alone can't paper over a resume
# that's missing hard-required skills (see build spec's fusion enhancement).
KEYWORD_BM25_WEIGHT = 0.70
KEYWORD_COVERAGE_WEIGHT = 0.30


def minmax(scores: List[float]) -> List[float]:
    """Safe min-max normalization. All-identical batches (degenerate --
    e.g. one resume, or every BM25 score tied) get a neutral 0.5 for
    everyone instead of dividing by zero."""
    arr = np.array(scores, dtype=float)
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-9:
        return [0.5 for _ in scores]
    return list((arr - lo) / (hi - lo))


def fuse_scores(
    keyword_scores: List[float],
    semantic_scores: List[float],
    required_skill_coverage: List[float],
) -> Dict[str, List[float]]:
    keyword_norm = minmax(keyword_scores)
    semantic_norm = minmax(semantic_scores)

    keyword_component = [
        KEYWORD_BM25_WEIGHT * k + KEYWORD_COVERAGE_WEIGHT * cov
        for k, cov in zip(keyword_norm, required_skill_coverage)
    ]
    final = [
        KEYWORD_WEIGHT * kc + SEMANTIC_WEIGHT * s
        for kc, s in zip(keyword_component, semantic_norm)
    ]
    return {
        "keyword_norm": keyword_norm,
        "semantic_norm": semantic_norm,
        "keyword_component": keyword_component,
        "final_score": final,
    }


def rank(candidates: List[Dict]) -> List[Dict]:
    """candidates: list of dicts each already carrying 'score' and other
    per-candidate fields (resume id, matched/missing skills, etc).
    Returns the same dicts, sorted descending by score, with a 1-indexed
    'rank' field added. Ties broken by resume_id ascending for
    determinism."""
    ordered = sorted(
        candidates,
        key=lambda c: (-c["score"], c.get("resume_id", "")),
    )
    for i, c in enumerate(ordered, start=1):
        c["rank"] = i
    return ordered
