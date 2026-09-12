import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.fusion import fuse_scores, minmax, rank


def test_min_max_normalize_and_weights():
    kw = [1.0, 2.0, 3.0]
    sem = [0.1, 0.5, 0.9]
    # coverage tracks kw_norm exactly here (0, 0.5, 1) so keyword_component
    # collapses to kw_norm and the final formula reduces to the plain
    # 0.4*kw_norm + 0.6*sem_norm case, easy to hand-verify.
    coverage = [0.0, 0.5, 1.0]
    fused = fuse_scores(kw, sem, coverage)
    assert fused["keyword_norm"] == [0.0, 0.5, 1.0]
    assert fused["semantic_norm"][0] == 0.0
    assert fused["semantic_norm"][2] == 1.0
    assert abs(fused["final_score"][2] - 1.0) < 1e-9
    assert abs(fused["final_score"][0] - 0.0) < 1e-9


def test_required_skill_coverage_affects_keyword_component():
    kw = [1.0, 1.0]
    sem = [0.5, 0.5]
    coverage = [1.0, 0.0]  # identical bm25/semantic, but candidate 1 is missing every required skill
    fused = fuse_scores(kw, sem, coverage)
    assert fused["keyword_component"][0] > fused["keyword_component"][1]
    assert fused["final_score"][0] > fused["final_score"][1]


def test_fuse_scores_degenerate_batch_all_equal():
    kw = [5.0, 5.0, 5.0]
    sem = [0.3, 0.3, 0.3]
    coverage = [1.0, 1.0, 1.0]
    fused = fuse_scores(kw, sem, coverage)
    assert all(v == 0.5 for v in fused["keyword_norm"])
    assert all(v == 0.5 for v in fused["semantic_norm"])


def test_minmax_handles_identical_scores_without_division_by_zero():
    assert minmax([2.0, 2.0, 2.0]) == [0.5, 0.5, 0.5]


def test_rank_sorts_descending_and_assigns_rank():
    candidates = [
        {"resume_id": "b", "score": 0.2},
        {"resume_id": "a", "score": 0.9},
        {"resume_id": "c", "score": 0.5},
    ]
    ranked = rank(candidates)
    assert [c["resume_id"] for c in ranked] == ["a", "c", "b"]
    assert [c["rank"] for c in ranked] == [1, 2, 3]


def test_rank_ties_broken_by_resume_id_ascending():
    candidates = [
        {"resume_id": "CAND_0000002", "score": 0.5},
        {"resume_id": "CAND_0000001", "score": 0.5},
    ]
    ranked = rank(candidates)
    assert [c["resume_id"] for c in ranked] == ["CAND_0000001", "CAND_0000002"]
