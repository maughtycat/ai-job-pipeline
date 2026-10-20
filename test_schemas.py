#!/usr/bin/env python3
"""Tests for the Pydantic LLM-output boundaries: garbage in, garbage stopped."""
from pydantic import ValidationError

from models import FitResult, ParsedPosting


def _rejects(**kw):
    try:
        FitResult.model_validate(kw)
    except ValidationError:
        return True
    return False


def test_parse_defaults_and_coercion():
    empty = ParsedPosting.model_validate({})
    assert empty.company == "Unknown" and empty.required_skills == []
    coerced = ParsedPosting.model_validate(
        {"company": "Acme", "role": "Eng", "required_skills": "Python"}
    )
    assert coerced.required_skills == ["Python"]  # bare string became one item
    extra = ParsedPosting.model_validate({"company": "Acme", "hallucinated": 1})
    assert extra.company == "Acme"                # unknown keys ignored, not fatal


def test_fit_rejects_garbage():
    assert _rejects(score="high")    # non-numeric score
    assert _rejects(score=150)       # out of range
    assert _rejects()                # missing score
    ok = FitResult.model_validate({"score": "85", "red_flags": "long posting",
                                   "reasoning": "solid overlap"})
    assert ok.score == 85 and ok.red_flags == ["long posting"]


if __name__ == "__main__":
    test_parse_defaults_and_coercion()
    test_fit_rejects_garbage()
    print("OK: 2 tests, 8 assertions passed")
