"""
bias_check.py (bonus feature)
Pure heuristic checks on the JD text for:
  - unrealistic years-of-experience asks for an intern/junior role
  - gendered or exclusionary phrasing
  - overly narrow tool requirements that exclude known equivalents
Returns a short list of flags (strings), never a blocking judgment -- this
never changes the ranking, only surfaces observations for a human.

Hard constraint (build spec v2): no LLM/API call anywhere in this
pipeline, including here -- these are regex/heuristic checks only.
"""

from __future__ import annotations

import re
from typing import List

from src.skill_vocab import EQUIVALENT_TOOL_GROUPS, SKILL_VOCAB

_GENDERED_TERMS = [
    "he", "his", "himself", "salesman", "manpower", "chairman",
    "guys", "rockstar", "ninja", "he/she", "young and energetic",
]

_EXCLUSIONARY_BUZZWORDS = [
    "work hard play hard", "digital native", "fast-paced environment",
    "wear many hats",
]


def _word_boundary_hits(terms: List[str], text_low: str) -> List[str]:
    """Case-insensitive, word-boundary-aware substring search -- plain `in`
    checks would false-positive on e.g. 'he' inside 'the' or 'cache'."""
    hits = []
    for term in terms:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(term) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_low):
            hits.append(term)
    return hits

_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*years?", re.IGNORECASE)
_INTERN_RE = re.compile(r"intern(ship)?", re.IGNORECASE)
_EQUIVALENCE_QUALIFIER_RE = re.compile(r"(or equivalent|similar (framework|technology|tool)|comparable)", re.IGNORECASE)


def _years_of_experience_flags(jd_text: str) -> List[str]:
    is_intern_role = bool(_INTERN_RE.search(jd_text))
    years_mentions = [int(m.group(1)) for m in _YEARS_RE.finditer(jd_text)]
    if is_intern_role and any(y >= 2 for y in years_mentions):
        return [
            f"JD is for an internship but asks for {max(years_mentions)}+ years of "
            "experience -- this may unfairly exclude qualified students/new grads."
        ]
    return []


def _gendered_or_exclusionary_flags(jd_text: str) -> List[str]:
    text_low = jd_text.lower()
    flags = []

    hits = sorted(set(_word_boundary_hits(_GENDERED_TERMS, text_low)))
    if hits:
        flags.append(f"Potentially gendered or exclusionary phrasing found: {', '.join(hits)}.")

    buzz_hits = _word_boundary_hits(_EXCLUSIONARY_BUZZWORDS, text_low)
    if buzz_hits:
        flags.append(
            "Culture-fit buzzwords that may discourage otherwise-qualified "
            f"applicants: {', '.join(buzz_hits)}."
        )
    return flags


def _narrow_tool_flags(jd_text: str) -> List[str]:
    """A required tool is flagged as 'narrow' when: (a) the vocabulary
    knows of interchangeable equivalents for it, (b) none of those
    equivalents are also mentioned in the JD, and (c) the JD doesn't
    already hedge with language like 'or equivalent' near the mention."""
    text_low = jd_text.lower()
    flags = []

    for group in EQUIVALENT_TOOL_GROUPS:
        if len(group) < 2:
            continue
        mentioned = [tool for tool in group if any(
            re.search(rf"(?<![a-zA-Z0-9]){re.escape(alias)}(?![a-zA-Z0-9])", text_low)
            for alias in SKILL_VOCAB.get(tool, [tool])
        )]
        if len(mentioned) != 1:
            continue  # none mentioned, or multiple/equivalents already accepted

        tool = mentioned[0]
        alias_hit = next(
            (a for a in SKILL_VOCAB.get(tool, [tool]) if a in text_low), tool
        )
        idx = text_low.find(alias_hit)
        window = text_low[max(idx - 40, 0): idx + 40]
        if not _EQUIVALENCE_QUALIFIER_RE.search(window):
            alternatives = sorted(group - {tool})
            flags.append(
                f"'{tool}' is named as a specific requirement with no 'or equivalent' "
                f"qualifier, though comparable tools exist ({', '.join(alternatives)}) -- "
                "consider whether candidates with comparable tools should also qualify."
            )
    return flags


def check_bias(jd_text: str) -> List[str]:
    flags = []
    flags.extend(_years_of_experience_flags(jd_text))
    flags.extend(_gendered_or_exclusionary_flags(jd_text))
    flags.extend(_narrow_tool_flags(jd_text))

    seen = set()
    unique = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique
