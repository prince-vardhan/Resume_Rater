import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.parsing import _clean_cid_artifacts, chunk_resume, split_resume_sections


def test_cid_artifact_at_line_start_becomes_a_bullet():
    text = "(cid:127) Built REST APIs with Express and MongoDB"
    cleaned = _clean_cid_artifacts(text)
    assert cleaned == "• Built REST APIs with Express and MongoDB"


def test_cid_artifact_mid_line_is_dropped_not_leaked():
    text = "Salary: 10 (cid:8) 12 LPA"
    cleaned = _clean_cid_artifacts(text)
    assert "cid:" not in cleaned
    assert "Salary: 10 12 LPA" == cleaned


def test_bullets_from_cid_cleaned_text_are_detected_as_chunks():
    # Real PDFs are cleaned inside extract_text()/extract_pages() before
    # anything else sees them -- simulate that same order here rather than
    # handing raw "(cid:N)" text straight to split_resume_sections().
    raw = (
        "Experience\n"
        "(cid:127) Built 4 new React components integrated with REST APIs\n"
        "(cid:127) Developed Node.js/Express backend endpoints\n"
    )
    text = _clean_cid_artifacts(raw)
    sections = split_resume_sections(text)
    chunks = chunk_resume(sections)
    assert "Built 4 new React components integrated with REST APIs" in chunks
    assert "Developed Node.js/Express backend endpoints" in chunks
    assert not any("cid:" in c for c in chunks)
