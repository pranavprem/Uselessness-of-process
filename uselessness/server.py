"""Local questionnaire page. The scoring stays in evaluate.py."""

from __future__ import annotations

import json
from collections.abc import Mapping
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs

from uselessness.evaluate import (
    QUESTIONS,
    SCALE_MAX,
    Evaluation,
    ScoreError,
    evaluate,
)

_MAX_BODY = 16_384

_PAGE = files("uselessness").joinpath("web/page.html").read_text(encoding="utf-8")
_CSS = files("uselessness").joinpath("web/style.css").read_bytes()


def scale_caption(score: int) -> str:
    if score == 0:
        return "No"
    if score == 4:
        return "To some extent"
    if score == SCALE_MAX:
        return "Yes"
    return str(score)


def render_questions(selected: Mapping[int, int]) -> str:
    blocks: list[str] = []
    for question in QUESTIONS:
        choices: list[str] = []
        for score in range(SCALE_MAX + 1):
            checked = " checked" if selected.get(question.number) == score else ""
            caption = scale_caption(score)
            choices.append(
                "<label class='choice'>"
                f"<input type='radio' name='q{question.number}' value='{score}' "
                f"required{checked} aria-label='{escape(caption)}'>"
                f"<span>{score}</span>"
                "</label>"
            )
        blocks.append(
            "<fieldset class='question'>"
            f"<legend><span class='qnum'>{question.number:02d}</span>"
            f"{escape(question.text)}</legend>"
            "<div class='scale'>"
            "<div class='scale-labels'><span>No</span>"
            "<span>To some extent</span><span>Yes</span></div>"
            f"<div class='scale-options'>{''.join(choices)}</div>"
            "</div>"
            "</fieldset>"
        )
    return "\n".join(blocks)


def render_result(result: Evaluation) -> str:
    kind = "drop" if result.eliminable else "keep"
    caveats = ""
    if result.considerations:
        items = "".join(f"<li>{escape(note)}</li>" for note in result.considerations)
        caveats = (
            f"<div class='caveats'><h3>Before removing it</h3><ul>{items}</ul></div>"
        )
    marks = "".join(f"<span>{score}</span>" for score in result.scores)
    return (
        f"<section class='verdict verdict-{kind}' aria-labelledby='verdict-heading'>"
        "<p class='kicker'>Result</p>"
        f"<h2 id='verdict-heading'>{escape(result.verdict)}</h2>"
        f"<p class='total'>Total <strong>{result.total}</strong> of {result.maximum}. "
        f"A step is kept when the total is above {result.threshold}.</p>"
        f"<p class='marks' aria-label='Scores in question order'>{marks}</p>"
        f"{caveats}"
        "</section>"
    )


def render_page(
    selected: Mapping[int, int] | None = None,
    result: Evaluation | None = None,
    error: str | None = None,
) -> str:
    selected = selected or {}
    error_html = f"<p class='error' role='alert'>{escape(error)}</p>" if error else ""
    result_html = render_result(result) if result is not None else ""
    return (
        _PAGE.replace("{{error}}", error_html)
        .replace("{{result}}", result_html)
        .replace("{{questions}}", render_questions(selected))
    )


def scores_from_mapping(mapping: Mapping[str, str]) -> list[int]:
    scores: list[int] = []
    missing: list[int] = []
    for question in QUESTIONS:
        raw = mapping.get(f"q{question.number}", "").strip()
        if raw == "":
            missing.append(question.number)
            scores.append(-1)
            continue
        if not raw.isdigit():
            raise ScoreError(
                f"Question {question.number} needs an integer score "
                f"from 0 to {SCALE_MAX}."
            )
        scores.append(int(raw))
    if missing:
        listed = ", ".join(str(number) for number in missing)
        raise ScoreError(f"Answer every question. Still open: {listed}.")
    return scores


class Handler(BaseHTTPRequestHandler):
    server_version = "uselessness/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        # The questionnaire is a local worksheet; access logs add nothing.
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            page = render_page().encode("utf-8")
            self._send(200, page, "text/html; charset=utf-8")
            return
        if path == "/style.css":
            self._send(200, _CSS, "text/css; charset=utf-8")
            return
        if path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        self._send(404, b"Not found\n", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path != "/evaluate":
            self._send(404, b"Not found\n", "text/plain; charset=utf-8")
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > _MAX_BODY:
            self._send(413, b"Request is too large\n", "text/plain; charset=utf-8")
            return
        raw = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        wants_json = content_type.startswith("application/json")

        try:
            if wants_json:
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict) or not isinstance(
                    payload.get("scores"), list
                ):
                    raise ScoreError('Send {"scores": [nine integers from 0 to 8]}.')
                result = evaluate(payload["scores"])
            else:
                parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
                flat = {key: values[-1] for key, values in parsed.items()}
                result = evaluate(scores_from_mapping(flat))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reject(wants_json, "The answers could not be read.", {})
            return
        except ScoreError as exc:
            selected = {}
            if not wants_json:
                parsed = parse_qs(
                    raw.decode("utf-8", "replace"), keep_blank_values=True
                )
                flat = {key: values[-1] for key, values in parsed.items()}
                selected = _selected_from_form(flat)
            self._reject(wants_json, str(exc), selected)
            return

        if wants_json:
            body = json.dumps(result.as_dict()).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        selected = {index: score for index, score in enumerate(result.scores, start=1)}
        page = render_page(selected, result).encode("utf-8")
        self._send(200, page, "text/html; charset=utf-8")

    def _reject(
        self, wants_json: bool, message: str, selected: Mapping[int, int]
    ) -> None:
        if wants_json:
            body = json.dumps({"error": message}).encode("utf-8")
            self._send(400, body, "application/json; charset=utf-8")
            return
        page = render_page(selected, error=message).encode("utf-8")
        self._send(400, page, "text/html; charset=utf-8")


def _selected_from_form(mapping: Mapping[str, str]) -> dict[int, int]:
    selected: dict[int, int] = {}
    for question in QUESTIONS:
        raw = mapping.get(f"q{question.number}", "").strip()
        if raw.isdigit():
            score = int(raw)
            if 0 <= score <= SCALE_MAX:
                selected[question.number] = score
    return selected


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    if port < 0 or port > 65535:
        raise ScoreError(f"Port {port} is not valid.")
    httpd = ThreadingHTTPServer((host, port), Handler)
    bound_host, bound_port = httpd.server_address
    print(f"Questionnaire at http://{bound_host}:{bound_port}/")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        httpd.server_close()
