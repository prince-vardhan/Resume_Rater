"""
extraction.py
Turn free text (JD or resume) into a structured skill list using the
alias vocab in skill_vocab.py, and split a JD's requirements into
"required" vs "preferred" buckets when it distinguishes them.
"""

from __future__ import annotations

import re
from typing import Dict, List

REQUIRED_SECTION_HEADERS = [
    r"required", r"requirements", r"must[- ]have", r"minimum qualifications",
]
PREFERRED_SECTION_HEADERS = [
    r"preferred", r"nice[- ]to[- ]have", r"bonus", r"good to have", r"plus",
]


def _build_alias_pattern(alias: str) -> re.Pattern:
    escaped = re.escape(alias)
    # word-boundary match, tolerant of punctuation like "Node.js"
    return re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)


def _match_vocab(text: str, vocab: dict) -> List[str]:
    text_low = text.lower()
    found = []
    for canonical, aliases in vocab.items():
        for alias in aliases:
            if _build_alias_pattern(alias).search(text_low):
                found.append(canonical)
                break
    return found


def extract_resume_skills(resume_text: str, vocab: dict) -> List[str]:
    """Skills mentioned anywhere in the resume."""
    return _match_vocab(resume_text, vocab)


def _split_required_preferred(jd_text: str) -> Dict[str, str]:
    """Best-effort split of JD text into a 'required' blob and a 'preferred'
    blob, based on section header keywords. Works whether a header sits on
    its own line ("Required:\\n  React...") or inline with its content
    ("Required: React, MongoDB..."), by matching the keyword's character
    offset in the full text rather than requiring it to occupy a whole line.
    Falls back to treating the whole JD as 'required' if no distinguishing
    headers are found (safer default -- we'd rather over-count required
    skills than under-count them)."""
    header_re = re.compile(
        r"(" + "|".join(REQUIRED_SECTION_HEADERS + PREFERRED_SECTION_HEADERS) + r")\s*:?",
        re.IGNORECASE,
    )

    markers = []  # (content_start_offset, next_header_start_offset, "required"|"preferred")
    matches = list(header_re.finditer(jd_text))
    for i, m in enumerate(matches):
        label = m.group(1).lower()
        bucket = "preferred" if any(
            re.fullmatch(p, label, re.IGNORECASE) for p in PREFERRED_SECTION_HEADERS
        ) else "required"
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(jd_text)
        markers.append((content_start, content_end, bucket))

    if not markers:
        return {"required": jd_text, "preferred": ""}

    buckets = {"required": "", "preferred": ""}
    for content_start, content_end, bucket in markers:
        buckets[bucket] += "\n" + jd_text[content_start:content_end]

    # Anything before the first header is ambiguous JD preamble -- treat as required
    # context too (role summary often repeats core skills).
    preamble = jd_text[: matches[0].start()]
    buckets["required"] = preamble + "\n" + buckets["required"]

    return buckets


def extract_required_skills(jd_text: str, vocab: dict) -> Dict[str, List[str]]:
    """Returns {'required': [...], 'preferred': [...]} canonical skill names.

    A skill mentioned in both buckets is kept only under 'required' (the
    stricter classification), since it genuinely matters to the role.
    """
    buckets = _split_required_preferred(jd_text)
    required = set(_match_vocab(buckets["required"], vocab))
    preferred = set(_match_vocab(buckets["preferred"], vocab)) - required
    return {"required": sorted(required), "preferred": sorted(preferred)}
