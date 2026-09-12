"""
parsing.py
PDF -> raw text, and raw resume text -> best-effort section split.

Design notes:
- We never fail hard on a messy PDF. If a page has no extractable text
  (e.g. a scanned image resume) we skip it and keep going instead of
  raising, because the testing checklist explicitly requires surviving
  the messiest-formatted resume in the batch.
- Section splitting is heuristic: we look for common header keywords on
  their own line (case-insensitive) and slice the text between headers.
  If we can't find at least two headers, we fall back to treating the
  whole resume as a single "experience" blob so downstream skill
  extraction still has something to search over.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pdfplumber

# Canonical section -> header keywords that mark the start of that section.
SECTION_HEADERS: Dict[str, list] = {
    "skills": [
        r"skills?", r"technical skills?", r"tech(nical)? stack",
        r"core competenc(y|ies)", r"tools? (and|&) technolog(y|ies)",
    ],
    "experience": [
        r"experience", r"work experience", r"professional experience",
        r"employment( history)?", r"internships?",
    ],
    "projects": [
        r"projects?", r"personal projects?", r"academic projects?",
    ],
    "education": [
        r"education", r"academic (background|qualifications?)",
        r"qualifications?",
    ],
}

_HEADER_LINE_RE = re.compile(
    r"^\s*[#>*\-\u2022]*\s*(" +
    "|".join(
        pattern
        for patterns in SECTION_HEADERS.values()
        for pattern in patterns
    ) +
    r")\s*[:\-]?\s*$",
    re.IGNORECASE,
)


_PAGE_BREAK = "\n\f\n"  # form-feed marker: preserves page boundaries without
# polluting downstream tokenization (BM25/embedding tokenizers treat it as
# whitespace), so evidence can still be traced back to a page if needed.

# Some resume PDFs embed a bullet glyph (e.g. a Wingdings-style dot) whose
# font has no ToUnicode mapping; pdfplumber then emits the raw glyph id as
# literal text like "(cid:127)" instead of a character. At the start of a
# line that's always standing in for a bullet marker, so we normalize it to
# a real bullet; anywhere else (rare) we just drop it rather than leak the
# artifact into scores/explanations.
_CID_ARTIFACT_RE = re.compile(r"\(cid:\d+\)")


def _clean_cid_artifacts(text: str) -> str:
    def repl(match: re.Match) -> str:
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start:match.start()]
        return "•" if prefix.strip() == "" else ""

    cleaned = _CID_ARTIFACT_RE.sub(repl, text)
    return re.sub(r"[ \t]{2,}", " ", cleaned)


def extract_pages(pdf_path: str) -> List[str]:
    """Extract text per page. Skips pages that fail to extract (scanned/
    image-only pages) rather than raising, so one bad page doesn't sink
    the whole batch."""
    path = Path(pdf_path)
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(_clean_cid_artifacts(text) if text else text)
    return pages


def extract_text(pdf_path: str) -> str:
    """Extract all readable text from a PDF, joined page by page (page
    boundaries preserved via a form-feed marker so evidence could later be
    traced back to a page)."""
    pages = [p for p in extract_pages(pdf_path) if p.strip()]
    return _PAGE_BREAK.join(pages).strip()


def has_low_text_extraction(text: str) -> bool:
    """Basic extraction sanity check per the build spec: a PDF that yields
    almost no text is likely scanned/image-only. Callers should flag this
    (e.g. 'low_text_extraction') and continue rather than crash or silently
    produce a misleading ranking."""
    return len(text.strip()) < 100


def _canonical_section_for_header(line: str) -> str | None:
    line_clean = line.strip().lower()
    for section, patterns in SECTION_HEADERS.items():
        for pattern in patterns:
            if re.fullmatch(pattern, line_clean, flags=re.IGNORECASE):
                return section
    return None


def split_resume_sections(text: str) -> Dict[str, str]:
    """Best-effort split of resume text into skills/experience/projects/education.

    Falls back to putting everything under 'experience' if fewer than two
    recognizable headers are found (common with messy/plain-text resumes).
    """
    lines = text.splitlines()
    header_positions = []  # (line_index, section_name)

    for i, raw_line in enumerate(lines):
        candidate = raw_line.strip()
        if not candidate or len(candidate) > 60:
            continue
        section = _canonical_section_for_header(candidate)
        if section:
            header_positions.append((i, section))

    sections = {k: "" for k in SECTION_HEADERS}

    if len(header_positions) < 2:
        # Not enough structure detected -- treat the whole thing as one blob.
        sections["experience"] = text
        return sections

    for idx, (line_no, section_name) in enumerate(header_positions):
        start = line_no + 1
        end = (
            header_positions[idx + 1][0]
            if idx + 1 < len(header_positions)
            else len(lines)
        )
        body = "\n".join(lines[start:end]).strip()
        # If the same section header appears twice, append rather than overwrite.
        sections[section_name] = (sections[section_name] + "\n" + body).strip()

    return sections


def full_text_or_blob(sections: Dict[str, str]) -> str:
    """Convenience: reconstitute a single search-friendly blob from sections."""
    return "\n".join(v for v in sections.values() if v).strip()


_BULLET_LINE_RE = re.compile(r"^\s*[•‣◦⁃∙\-*>•▪●]\s*(.+)$")


def _bullets_from_block(block: str) -> List[str]:
    """Pull out bullet-marked lines from a text block. Returns [] if the
    block doesn't look bullet-formatted (caller should fall back)."""
    bullets = []
    for line in block.splitlines():
        m = _BULLET_LINE_RE.match(line)
        if m:
            bullets.append(m.group(1).strip())
    return bullets


def _sentence_fallback(text: str) -> List[str]:
    """Short text-block fallback when bullets can't be reliably detected:
    split on newlines/sentence punctuation."""
    raw_pieces = re.split(r"[\n\r]+|(?<=[.!?])\s+", text)
    return [p.strip(" \t-•*") for p in raw_pieces if len(p.strip()) >= 8]


def chunk_resume(text_or_sections) -> List[str]:
    """Lightweight chunking for semantic matching: prefer experience/project
    bullets as individual chunks (that's where the concrete evidence for a
    JD requirement usually lives); fall back to short sentence/line blocks
    when bullets can't be reliably detected.

    Accepts either the raw resume text (str) or the dict produced by
    split_resume_sections().
    """
    if isinstance(text_or_sections, dict):
        sections = text_or_sections
        priority_blocks = [sections.get("experience", ""), sections.get("projects", "")]
        secondary_blocks = [sections.get("skills", ""), sections.get("education", "")]
    else:
        priority_blocks = [text_or_sections]
        secondary_blocks = []

    chunks: List[str] = []
    for block in priority_blocks:
        if block:
            chunks.extend(_bullets_from_block(block))
    if not chunks:
        for block in priority_blocks:
            if block:
                chunks.extend(_sentence_fallback(block))
    for block in secondary_blocks:
        if block:
            chunks.extend(_sentence_fallback(block))

    # De-duplicate while preserving order.
    seen = set()
    unique = []
    for c in chunks:
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    return unique or [text_or_sections if isinstance(text_or_sections, str) else full_text_or_blob(text_or_sections)]
