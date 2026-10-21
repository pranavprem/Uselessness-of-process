import json
from pathlib import Path

import pytest

from uselessness.cli import main, prompt_scores
from uselessness.evaluate import (
    KEEP_THRESHOLD,
    QUESTIONS,
    SCALE_MAX,
    VERDICT_DROP,
    VERDICT_KEEP,
    ScoreError,
    evaluate,
)

ROOT = Path(__file__).parents[1]
EXAMPLE = (0, 4, 0, 0, 8, 0, 0, 4, 0)


def test_scale_and_question_count():
    assert len(QUESTIONS) == 9
    assert SCALE_MAX == 8
    assert KEEP_THRESHOLD == 30
    assert [question.number for question in QUESTIONS] == list(range(1, 10))
    assert [question.polarity for question in QUESTIONS] == [
        "high",
        "high",
        "high",
        "low",
        "low",
        "low",
        "high",
        "high",
        "high",
    ]


def test_all_no_can_be_removed_with_the_low_side_caveats():
    result = evaluate([0] * 9)
    assert result.total == 0
    assert result.eliminable
    assert result.verdict == VERDICT_DROP
    assert result.considerations == tuple(
        question.consideration for question in QUESTIONS if question.polarity == "low"
    )


def test_all_yes_is_kept_and_yes_counts_as_eight():
    # Column O ("Yes") was never read by the original macro.
    result = evaluate([8] * 9)
    assert result.total == 72
    assert result.maximum == 72
    assert not result.eliminable
    assert result.verdict == VERDICT_KEEP
    assert result.considerations == ()
    assert result.message == VERDICT_KEEP


def test_to_some_extent_on_every_question_is_kept():
    result = evaluate([4] * 9)
    assert result.total == 36
    assert not result.eliminable
    assert result.considerations == ()


def test_just_under_the_middle_can_be_removed():
    result = evaluate([3] * 9)
    assert result.total == 27
    assert result.eliminable
    assert result.considerations == tuple(
        QUESTIONS[index].consideration for index in (3, 4, 5)
    )


def test_total_of_thirty_can_be_removed_and_thirty_one_is_kept():
    at_threshold = evaluate([5, 5, 5, 5, 5, 5, 0, 0, 0])
    above = evaluate([5, 5, 5, 5, 5, 6, 0, 0, 0])
    assert at_threshold.total == 30
    assert at_threshold.eliminable
    assert above.total == 31
    assert not above.eliminable


def test_boundary_of_five_does_not_add_a_consideration():
    high_side = [5, 0, 0, 5, 5, 5, 0, 0, 0]
    result = evaluate(high_side)
    assert result.eliminable
    assert result.considerations == ()

    flagged = [6, 0, 0, 4, 5, 5, 0, 0, 0]
    result = evaluate(flagged)
    assert QUESTIONS[0].consideration in result.considerations
    assert QUESTIONS[3].consideration in result.considerations
    assert QUESTIONS[4].consideration not in result.considerations


def test_considerations_are_withheld_when_the_step_is_kept():
    # Low scores on questions 4-6 would be caveats, but the total stays.
    result = evaluate([8, 8, 8, 0, 0, 0, 8, 8, 8])
    assert result.total == 48
    assert not result.eliminable
    assert result.considerations == ()


def test_worked_example_matches_the_workbook_sentence():
    result = evaluate(EXAMPLE)
    assert result.total == 16
    assert result.eliminable
    assert result.considerations == (
        QUESTIONS[3].consideration,
        QUESTIONS[5].consideration,
    )
    assert result.message == (
        "The Process can be eliminated! "
        "With consideration for removing redundant tasks "
        "With consideration for breaking this step down to further steps"
    )


def test_rejects_bad_answers():
    with pytest.raises(ScoreError):
        evaluate([0] * 8)
    with pytest.raises(ScoreError):
        evaluate([0] * 9 + [0])
    with pytest.raises(ScoreError):
        evaluate([0, 0, 0, 0, 0, 0, 0, 0, 9])
    with pytest.raises(ScoreError):
        evaluate([0, 0, 0, 0, 0, 0, 0, 0, True])
    with pytest.raises(ScoreError):
        evaluate([0, 0, 0, 0, 0, 0, 0, 0, "0"])  # type: ignore[list-item]


def test_prompt_and_cli_text():
    answers = iter(["0", "nope", "4", "0", "0", "8", "0", "0", "4", "0"])
    prompted: list[str] = []
    scores = prompt_scores(
        input_fn=lambda _prompt: next(answers), output_fn=prompted.append
    )
    assert scores == list(EXAMPLE)
    assert any("whole number" in line for line in prompted)

    printed: list[str] = []
    code = main([str(score) for score in EXAMPLE], output_fn=printed.append)
    assert code == 0
    assert printed == [
        "The Process can be eliminated!\n"
        "Total: 16 / 72 (kept when the total is above 30)\n"
        "\n"
        "With consideration for removing redundant tasks\n"
        "With consideration for breaking this step down to further steps"
    ]


def test_cli_json_and_errors():
    printed: list[str] = []
    code = main(
        ["--json", *[str(score) for score in EXAMPLE]], output_fn=printed.append
    )
    payload = json.loads(printed[0])
    assert code == 0
    assert payload["total"] == 16
    assert payload["eliminable"] is True

    errors: list[str] = []
    code = main(["1", "2", "3"], output_fn=printed.append, error_fn=errors.append)
    assert code == 2
    assert "Expected 9" in errors[0]

    code = main(["0", "--serve"], error_fn=errors.append)
    assert code == 2
    assert "not both" in errors[-1]


def test_corrected_macro_keeps_the_same_phrases():
    source = (ROOT / "workbook" / "Module1.bas").read_text(encoding="utf-8")
    assert VERDICT_KEEP in source
    assert VERDICT_DROP in source
    assert "total > 30" in source
    for question in QUESTIONS:
        assert question.consideration in source
    assert "column - 7" in source
    assert "question + 4" in source
