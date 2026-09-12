import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.bias_check import check_bias


def test_does_not_false_positive_on_words_containing_he():
    # "the", "About the Role" etc. contain "he " as a raw substring; a naive
    # `in` check flags these as gendered language, which is wrong.
    jd = "About the Role\nWe are hiring a developer for the team."
    flags = check_bias(jd)
    assert not any("gendered" in f.lower() for f in flags)


def test_flags_actual_gendered_language():
    jd = "We need a rockstar ninja who can manage his own workload."
    flags = check_bias(jd)
    assert any("gendered" in f.lower() for f in flags)


def test_flags_excessive_years_for_internship():
    jd = "Junior Developer Intern position requiring 5+ years of experience."
    flags = check_bias(jd)
    assert any("internship" in f.lower() for f in flags)


def test_flags_narrow_tool_requirement_without_equivalent_language():
    jd = "Required: React experience."
    flags = check_bias(jd)
    assert any("react" in f.lower() and "equivalent" in f.lower() for f in flags)


def test_does_not_flag_narrow_tool_when_equivalent_language_present():
    jd = "Required: React or equivalent frontend framework."
    flags = check_bias(jd)
    assert not any("react" in f.lower() for f in flags)
