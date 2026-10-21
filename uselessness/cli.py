"""Command-line runner for the process evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence

from uselessness.evaluate import QUESTIONS, SCALE_MAX, Evaluation, ScoreError, evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uselessness",
        description=(
            "Score one software-development process step and decide whether "
            "it can be removed."
        ),
    )
    parser.add_argument(
        "scores",
        nargs="*",
        type=int,
        help=(
            f"Nine integers from 0 (No) to {SCALE_MAX} (Yes), in question order. "
            "Leave them out to answer at the prompt."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the evaluation as JSON.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the questionnaire in a browser on localhost.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for --serve (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for --serve (default: 8000).",
    )
    return parser


def prompt_scores(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> list[int]:
    output_fn(
        f"Answer each question from 0 (No) to {SCALE_MAX} (Yes). 4 is 'To some extent'."
    )
    scores: list[int] = []
    for question in QUESTIONS:
        output_fn("")
        output_fn(f"{question.number}. {question.text}")
        while True:
            raw = input_fn(f"Score [0-{SCALE_MAX}]: ").strip()
            if not raw.isdigit():
                output_fn(f"Enter a whole number from 0 to {SCALE_MAX}.")
                continue
            score = int(raw)
            if score > SCALE_MAX:
                output_fn(f"Enter a whole number from 0 to {SCALE_MAX}.")
                continue
            scores.append(score)
            break
    return scores


def format_text(result: Evaluation) -> str:
    lines = [
        result.verdict,
        f"Total: {result.total} / {result.maximum} "
        f"(kept when the total is above {result.threshold})",
    ]
    if result.considerations:
        lines.append("")
        lines.extend(result.considerations)
    return "\n".join(lines)


def main(
    argv: Sequence[str] | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    error_fn: Callable[[str], None] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    def default_error(message: str) -> None:
        print(message, file=sys.stderr)

    if error_fn is None:
        error_fn = default_error

    if args.serve:
        if args.scores:
            error_fn("Pass either scores or --serve, not both.")
            return 2
        from uselessness.server import serve

        serve(args.host, args.port)
        return 0

    try:
        scores = (
            list(args.scores) if args.scores else prompt_scores(input_fn, output_fn)
        )
        result = evaluate(scores)
    except EOFError:
        error_fn("Stopped before every question was answered.")
        return 2
    except ScoreError as exc:
        error_fn(str(exc))
        return 2

    if args.json:
        output_fn(json.dumps(result.as_dict(), indent=2))
    else:
        output_fn(format_text(result))
    return 0
