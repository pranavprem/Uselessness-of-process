"""Scoring rules taken from the 2017 workbook, with the macro's bugs corrected.

Each question is answered on a nine-point scale. Column G of the questionnaire
was "No" (0) and column O was "Yes" (8); column K, "To some extent", is 4.
Yes always points toward keeping the step. The step is kept only when the
total is above 30.

The shipped macro never implemented that scale. It mapped two different
scores onto column G, never read column O, and scanned rows 1–10 while the
questions sit on rows 5–13. This module scores the nine written questions
on the scale the sheet actually labels.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

SCALE_MAX = 8
NOTE_BOUNDARY = 5
KEEP_THRESHOLD = 30

VERDICT_KEEP = "The Process can not be eliminated"
VERDICT_DROP = "The Process can be eliminated!"

Polarity = Literal["high", "low"]


class ScoreError(ValueError):
    """The answers cannot be scored."""


@dataclass(frozen=True)
class Question:
    number: int
    text: str
    consideration: str
    # "high": a score above NOTE_BOUNDARY is called out when the step is removed.
    # "low": a score below NOTE_BOUNDARY is called out. Questions 4–6 are worded
    # so that No means the step is redundant, automatable, or splittable.
    polarity: Polarity


# Wording follows the macro workbook. Two copy errors are corrected here:
# question 7 no longer says "serve to service", and question 9 spells
# "maintenance". The consideration sentences are unchanged, including the
# missing "on" in the last one, because that is the text the macro wrote
# into the result cell.
QUESTIONS: tuple[Question, ...] = (
    Question(
        1,
        "Will the end user have an impact if this step is removed?",
        "With consideration for impact on end user if step is removed",
        "high",
    ),
    Question(
        2,
        "Do any other parties involved in the development process have a "
        "dependency on this step?",
        "With consideration for impact on other parties if step is removed",
        "high",
    ),
    Question(
        3,
        "Was this step introduced reactively to solve a problem?",
        "With consideration for impact on problem that the step solved",
        "high",
    ),
    Question(
        4,
        "Are tasks performed in this step unique (i.e. no redundant tasks in any "
        "other steps)?",
        "With consideration for removing redundant tasks",
        "low",
    ),
    Question(
        5,
        "Do the tasks performed in this step necessarily involve manual "
        "contribution (cannot be automated)?",
        "With consideration for automation of the step",
        "low",
    ),
    Question(
        6,
        "Is this step a single unit that can not be broken down into further steps?",
        "With consideration for breaking this step down to further steps",
        "low",
    ),
    Question(
        7,
        "Does this step serve a mandatory/regulatory requirement?",
        "With consideration for Regulatory requirements",
        "high",
    ),
    Question(
        8,
        "Will there be over one Full Time Equivalent man month of effort "
        "required to remove/replace this step?",
        "With consideration for the effort involved in replacing this task",
        "high",
    ),
    Question(
        9,
        "Does this step have an impact on tasks that would help make "
        "maintenance easier (logging/documentation)?",
        "With consideration for impact documentation, support and maintenance "
        "activity following removal.",
        "high",
    ),
)


@dataclass(frozen=True)
class Evaluation:
    scores: tuple[int, ...]
    total: int
    maximum: int
    threshold: int
    eliminable: bool
    verdict: str
    considerations: tuple[str, ...]

    @property
    def message(self) -> str:
        """The single sentence the workbook wrote into the result cell."""
        if not self.considerations:
            return self.verdict
        return self.verdict + " " + " ".join(self.considerations)

    def as_dict(self) -> dict[str, object]:
        return {
            "scores": list(self.scores),
            "total": self.total,
            "maximum": self.maximum,
            "threshold": self.threshold,
            "eliminable": self.eliminable,
            "verdict": self.verdict,
            "considerations": list(self.considerations),
            "message": self.message,
        }


def evaluate(scores: Sequence[int]) -> Evaluation:
    """Score one step. `scores` has one integer per question, from 0 to 8."""
    expected = len(QUESTIONS)
    if len(scores) != expected:
        raise ScoreError(
            f"Expected {expected} scores, one per question, and got {len(scores)}."
        )

    cleaned: list[int] = []
    for index, score in enumerate(scores, start=1):
        if isinstance(score, bool) or not isinstance(score, int):
            raise ScoreError(
                f"Question {index} needs an integer score from 0 to {SCALE_MAX}."
            )
        if score < 0 or score > SCALE_MAX:
            raise ScoreError(f"Question {index} needs a score from 0 to {SCALE_MAX}.")
        cleaned.append(score)

    total = sum(cleaned)
    eliminable = total <= KEEP_THRESHOLD
    considerations: list[str] = []
    if eliminable:
        for question, score in zip(QUESTIONS, cleaned, strict=True):
            if question.polarity == "high" and score > NOTE_BOUNDARY:
                considerations.append(question.consideration)
            elif question.polarity == "low" and score < NOTE_BOUNDARY:
                considerations.append(question.consideration)

    return Evaluation(
        scores=tuple(cleaned),
        total=total,
        maximum=expected * SCALE_MAX,
        threshold=KEEP_THRESHOLD,
        eliminable=eliminable,
        verdict=VERDICT_DROP if eliminable else VERDICT_KEEP,
        considerations=tuple(considerations),
    )
