"""
explain.py
For the top 3 ranked candidates only: take structured evidence that has
ALREADY been computed by fusion.py / keyword_match.py / semantic_match.py
(matched/missing required skills, keyword_norm, semantic_norm, final
score, and per-requirement semantic evidence) and turn it into a short,
template-based natural-language explanation.

Hard constraint (build spec v2): no LLM/API call anywhere in this
pipeline, including here. This module is pure string templating over
already-computed evidence -- it never decides ranking, and it never
invents a skill, fact, or resume quote that isn't already in the
evidence it was handed.
"""

from __future__ import annotations

from typing import Dict, List


def _best_evidence(evidence: Dict) -> Dict | None:
    """Pick the single strongest requirement<->resume-chunk match to quote
    as 'best evidence'. Returns None if no requirement evidence is present."""
    reqs = evidence.get("requirement_evidence") or []
    if not reqs:
        return None
    return max(reqs, key=lambda r: r["similarity"])


def _template_explanation(evidence: Dict) -> str:
    matched = evidence["matched_skills"]
    missing = evidence["missing_skills"]
    preferred = evidence.get("matched_preferred", [])
    n_required = len(matched) + len(missing)

    lines = []
    if n_required:
        lines.append(
            f"Ranked #{evidence['rank']} with a score of {evidence['score']:.2f}. "
            f"Matched {len(matched)}/{n_required} required skills directly "
            f"({', '.join(matched) if matched else 'none'})."
        )
    else:
        lines.append(
            f"Ranked #{evidence['rank']} with a score of {evidence['score']:.2f}. "
            "No explicit required-skill list was detected in the JD for direct comparison."
        )

    lines.append(
        "Semantic matching found supporting evidence against the JD requirements, "
        f"with a normalized semantic score of {evidence['semantic_norm']:.2f} and a "
        f"normalized keyword score of {evidence['keyword_norm']:.2f}."
    )

    lines.append(f"Missing: {', '.join(missing) if missing else 'none'}.")

    if preferred:
        lines.append(f"Also shows preferred skills: {', '.join(preferred)}.")

    summary = " ".join(lines)

    best = _best_evidence(evidence)
    if best:
        summary += (
            f'\n\nBest evidence for "{best["requirement"]}" '
            f"(similarity {best['similarity']:.2f}):\n"
            f'"{best["best_chunk"]}"'
        )

    return summary


def explain_top_n(ranked_candidates: List[Dict], n: int = 3) -> List[Dict]:
    """Attaches an 'explanation' field to the top n ranked candidates
    (mutates and returns them). Purely template-based -- see module
    docstring for why no LLM is used here."""
    for candidate in ranked_candidates[:n]:
        candidate["explanation"] = _template_explanation(candidate)
    return ranked_candidates
