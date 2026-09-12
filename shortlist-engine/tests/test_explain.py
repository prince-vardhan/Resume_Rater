import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.explain import explain_top_n


def _candidate(rank, matched, missing, similarity_text="Built REST APIs with Express and MongoDB."):
    return {
        "rank": rank,
        "score": 0.75,
        "keyword_norm": 0.6,
        "semantic_norm": 0.8,
        "matched_skills": matched,
        "missing_skills": missing,
        "matched_preferred": [],
        "requirement_evidence": [
            {"requirement": "Build REST APIs using Express.js", "best_chunk": similarity_text, "similarity": 0.84},
            {"requirement": "Familiarity with Docker", "best_chunk": "Used Git for version control.", "similarity": 0.21},
        ],
    }


def test_explanation_lists_matched_and_missing_skills():
    candidates = [_candidate(1, ["react", "nodejs"], ["docker"])]
    explained = explain_top_n(candidates, n=3)
    text = explained[0]["explanation"]
    assert "react" in text
    assert "nodejs" in text
    assert "docker" in text
    assert "2/3" in text  # 2 matched + 1 missing = 3 required


def test_explanation_quotes_the_highest_similarity_resume_chunk_only():
    candidates = [_candidate(1, ["react"], [])]
    explained = explain_top_n(candidates, n=3)
    text = explained[0]["explanation"]
    assert "Built REST APIs with Express and MongoDB." in text
    assert "Used Git for version control." not in text  # lower-similarity evidence not quoted


def test_explain_only_touches_top_n():
    candidates = [_candidate(i, [], ["docker"]) for i in range(1, 6)]
    explained = explain_top_n(candidates, n=3)
    assert all("explanation" in c for c in explained[:3])
    assert all("explanation" not in c for c in explained[3:])


def test_explanation_never_invents_a_missing_evidence_field():
    candidate = _candidate(1, ["react"], [])
    candidate["requirement_evidence"] = []  # simulate no semantic evidence available
    explained = explain_top_n([candidate], n=1)
    # Should not crash and should not fabricate a quote.
    assert "Best evidence" not in explained[0]["explanation"]
