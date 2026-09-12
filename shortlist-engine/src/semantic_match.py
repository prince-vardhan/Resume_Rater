"""
semantic_match.py
Local embedding-based semantic similarity between JD requirements and
resume chunks, using sentence-transformers' all-MiniLM-L6-v2 (CPU, no
external API calls -- weights are downloaded once at setup time, then
everything runs offline).

The model is loaded once at module level (not per call / per candidate) --
see build spec's efficiency section.

Primary design (per build spec): JD requirement <-> resume bullet/chunk,
NOT whole-JD-embedding <-> whole-resume-embedding. Long resumes can exceed
the model's effective input window and lose signal to truncation/averaging,
and a single whole-document embedding gives no traceable evidence. Instead:

    for each JD requirement:
        embed(requirement)
        cosine similarity against every resume chunk
        best (max) similarity = evidence for that requirement

    semantic_score = mean(best similarity per requirement)

The best-matching chunk per requirement is kept as evidence so explain.py
can quote real resume text rather than inventing anything.
"""

from __future__ import annotations

import re
from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"
MODEL = SentenceTransformer(_MODEL_NAME)

_BULLET_LINE_RE = re.compile(r"^\s*[•‣◦⁃∙\-*>●▪]\s*(.+)$")
# Lines that are just a section header ("Requirements:", "Responsibilities")
# rather than an actual requirement statement -- skip these as "requirements".
_HEADER_ONLY_RE = re.compile(
    r"^(requirements?|responsibilities|qualifications?|preferred|nice[- ]to[- ]have|"
    r"must[- ]have|bonus|about (the )?(role|us|company)|overview|summary)\s*:?\s*$",
    re.IGNORECASE,
)


def extract_jd_requirements(jd_text: str) -> List[str]:
    """Best-effort split of the JD into requirement-like statements: bullet
    lines if present, otherwise sentence-ish lines. Section headers and
    very short fragments are dropped since they carry no comparable
    semantic content of their own."""
    bullets = [
        m.group(1).strip()
        for line in jd_text.splitlines()
        if (m := _BULLET_LINE_RE.match(line))
    ]
    candidates = bullets if bullets else re.split(r"[\n\r]+|(?<=[.!?])\s+", jd_text)

    requirements = []
    for c in candidates:
        c = c.strip(" \t-•*\f")
        if len(c) < 8 or _HEADER_ONLY_RE.match(c):
            continue
        requirements.append(c)
    return requirements


def _cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
    return a_norm @ b_norm.T


def semantic_match_resume(
    requirements: List[str],
    requirement_embeddings: np.ndarray,
    resume_chunks: List[str],
) -> Dict:
    """Match one resume's chunks against pre-embedded JD requirements.

    Returns:
      {
        "semantic_score": float,               # mean of per-requirement max similarity
        "requirement_evidence": [
          {"requirement": str, "best_chunk": str, "similarity": float},
          ...
        ]
      }
    """
    chunks = resume_chunks or ["(no extractable resume text)"]
    chunk_embeddings = MODEL.encode(chunks, convert_to_numpy=True)

    sim_matrix = _cosine_sim_matrix(requirement_embeddings, chunk_embeddings)
    best_chunk_idx = sim_matrix.argmax(axis=1)
    best_sims = sim_matrix.max(axis=1)

    evidence = [
        {
            "requirement": requirements[i],
            "best_chunk": chunks[best_chunk_idx[i]],
            "similarity": float(best_sims[i]),
        }
        for i in range(len(requirements))
    ]

    return {
        "semantic_score": float(best_sims.mean()) if len(best_sims) else 0.0,
        "requirement_evidence": evidence,
    }


def semantic_score_batch(jd_text: str, resume_chunk_lists: List[List[str]]) -> List[Dict]:
    """Batch entry point used by pipeline.py: one JD against many resumes'
    pre-chunked text. Requirements are extracted and embedded exactly once
    and reused for every resume.

    Falls back to treating the whole JD as a single "requirement" if
    requirement extraction produces nothing useful (e.g. an unstructured
    one-paragraph JD).
    """
    requirements = extract_jd_requirements(jd_text)
    if not requirements:
        requirements = [jd_text.strip()] if jd_text.strip() else ["(empty job description)"]

    requirement_embeddings = MODEL.encode(requirements, convert_to_numpy=True)

    return [
        semantic_match_resume(requirements, requirement_embeddings, chunks)
        for chunks in resume_chunk_lists
    ]
