import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.keyword_match import keyword_score, skill_overlap
from src.skill_vocab import SKILL_VOCAB


def test_keyword_score_ranks_more_relevant_resume_higher():
    jd = "We need a React and Node.js developer with MongoDB experience."
    resumes = [
        "I built full stack apps using React, Node.js, Express, and MongoDB.",
        "I have experience baking bread and managing a coffee shop.",
    ]
    scores = keyword_score(jd, resumes)
    assert scores[0] > scores[1]


def test_skill_overlap_flags_missing_required_skills():
    jd = "Required: React, MongoDB, Docker. Preferred: GraphQL."
    resumes = ["Built apps with React and MongoDB."]
    overlaps = skill_overlap(jd, resumes, SKILL_VOCAB)
    result = overlaps[0]
    assert "react" in result["matched_required"]
    assert "mongodb" in result["matched_required"]
    assert "docker" in result["missing_required"]


def test_skill_overlap_alias_matching():
    jd = "Required: Node.js, Express.js"
    resumes = ["Experienced with express and nodejs backend development."]
    overlaps = skill_overlap(jd, resumes, SKILL_VOCAB)
    assert "nodejs" in overlaps[0]["matched_required"]
    assert "express" in overlaps[0]["matched_required"]
