"""Score one software-development process step and decide if it can be removed."""

from uselessness.evaluate import (
    KEEP_THRESHOLD,
    QUESTIONS,
    SCALE_MAX,
    Evaluation,
    Question,
    ScoreError,
    evaluate,
)

__all__ = [
    "KEEP_THRESHOLD",
    "QUESTIONS",
    "SCALE_MAX",
    "Evaluation",
    "Question",
    "ScoreError",
    "evaluate",
]

__version__ = "1.0.0"
