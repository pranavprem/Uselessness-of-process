import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from uselessness.evaluate import QUESTIONS
from uselessness.server import Handler

EXAMPLE = (0, 4, 0, 0, 8, 0, 0, 4, 0)


@pytest.fixture
def base_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _read(url: str, data: bytes | None = None, content_type: str | None = None):
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request) as response:
            return response.status, response.headers.get_content_type(), response.read()
    except HTTPError as exc:
        return exc.code, exc.headers.get_content_type(), exc.read()


def test_questionnaire_page_lists_every_question(base_url):
    status, content_type, body = _read(base_url + "/")
    page = body.decode()
    assert status == 200
    assert content_type == "text/html"
    assert "Usefulness Indexing" in page
    assert "Evaluate" in page
    for question in QUESTIONS:
        assert question.text in page
    assert "serve to service" not in page
    assert "maintence" not in page


def test_stylesheet_is_served(base_url):
    status, content_type, body = _read(base_url + "/style.css")
    assert status == 200
    assert content_type == "text/css"
    assert b".verdict" in body


def test_form_post_returns_the_verdict_and_keeps_the_answers(base_url):
    payload = {f"q{index}": str(score) for index, score in enumerate(EXAMPLE, start=1)}
    status, _, body = _read(base_url + "/evaluate", urlencode(payload).encode())
    page = body.decode()
    assert status == 200
    assert "The Process can be eliminated!" in page
    assert "Total <strong>16</strong> of 72" in page
    assert "removing redundant tasks" in page
    assert "breaking this step down" in page
    assert page.count(" checked") == 9
    assert "name='q5' value='8' required checked" in page


def test_missing_answers_are_rejected(base_url):
    status, _, body = _read(
        base_url + "/evaluate",
        urlencode({"q1": "0", "q2": "4"}).encode(),
    )
    page = body.decode()
    assert status == 400
    assert "Still open: 3, 4, 5, 6, 7, 8, 9" in page
    assert "value='0' required checked" in page
    assert "The Process can be eliminated!" not in page


def test_json_api(base_url):
    status, content_type, body = _read(
        base_url + "/evaluate",
        json.dumps({"scores": list(EXAMPLE)}).encode(),
        "application/json",
    )
    assert status == 200
    assert content_type == "application/json"
    payload = json.loads(body)
    assert payload["total"] == 16
    assert payload["message"].startswith("The Process can be eliminated!")

    status, _, body = _read(
        base_url + "/evaluate",
        json.dumps({"scores": [0]}).encode(),
        "application/json",
    )
    assert status == 400
    assert "error" in json.loads(body)


def test_unknown_path(base_url):
    status, _, body = _read(base_url + "/missing")
    assert status == 404
    assert body == b"Not found\n"
