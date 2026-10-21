# AGENTS.md

Guide for working on Uselessness of process. Read this before editing.

## What this is

A questionnaire that scores one step in a software development process and recommends whether that step can be removed. Pranav Prem built it in January 2017 as an Excel workbook (`Usefulness of process workbook.xlsm`, plus an earlier `.xlsx` draft) while watching process accumulate on an Agile team at HSBC Software Development India.

The runnable program today is a Python port of that workbook. The workbooks stay in the repo as the historical artifact. They are not generated, and they are not rewritten in place.

## Architecture

`uselessness/evaluate.py` is the source of truth for questions, the 0–8 scale, the threshold, and the consideration sentences.

`uselessness/cli.py` is a thin command-line wrapper. `uselessness/server.py` renders `uselessness/web/page.html` and `style.css` and posts answers back through `evaluate`. There is no client-side scoring and no JavaScript.

`workbook/Module1.bas` is a corrected Excel macro for people who still open the `.xlsm`. It must use the same verdict strings, consideration sentences, threshold (`total > 30`), row mapping (`question + 4`, so question 1 is row 5), and column mapping (`column - 7`, so column G is 0 and column O is 8). A test fails if those phrases drift.

The original `.xlsm` still contains the 2017 macro. Clicking its Evaluate button does not run the corrected code.

## Scoring rules

Nine questions. Each answer is an integer from 0 (No) to 8 (Yes). 4 is "To some extent". Yes always points toward keeping the step. The later workbook reworded the redundancy and automation questions so that this direction holds; the `.xlsx` draft still has the older, inverted wording for those two.

The total runs from 0 to 72. The step is kept only when the total is above 30. A total of 30 can be removed. That cutoff is the author's, and it is slightly below a sheet of all "To some extent" answers (9 × 4 = 36), so the tool leans toward removal.

When the step can be removed, some answers add a caveat:

- Questions 1, 2, 3, 7, 8, and 9 add a caveat when the score is above 5.
- Questions 4, 5, and 6 add a caveat when the score is below 5. Those questions are the ones where No means redundant, automatable, or splittable.

A score of exactly 5 adds nothing. Caveats are withheld entirely when the step is kept. The single-cell sentence (`Evaluation.message`) joins the verdict and the caveats with spaces and no extra punctuation, matching the cell the macro wrote to `Sheets(3)!I7`.

Do not add questions, change the threshold, or flip a polarity without a reason that preserves this model. Rows 10–16 in the sheet are blank numbered placeholders. They are not secret questions.

Two question strings differ from the workbook on purpose: question 7 no longer says "serve to service", and question 9 spells "maintenance". The consideration sentences, including the awkward last one, are verbatim.

## Commands

Requires Python 3.11 or newer. Runtime dependencies: none. Dev tools are pinned in `pyproject.toml`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m uselessness
python -m uselessness 0 4 0 0 8 0 0 4 0
python -m uselessness --json 0 4 0 0 8 0 0 4 0
python -m uselessness --serve

ruff check .
ruff format .
pytest
```

`--serve` binds `127.0.0.1:8000` and is meant for a local browser. CI runs ruff, a format check, and pytest on Python 3.12 (`.github/workflows/ci.yml`).

## Conventions

- Keep scoring in `evaluate.py`. Call it from the CLI, the server, and tests. Do not reimplement it in the page.
- The page is a normal HTML form. Keep it usable without JavaScript.
- Escape anything taken from the request before putting it back in HTML.
- Prefer the standard library. A new runtime dependency needs a real reason, and it gets pinned.
- Format with ruff. Line length is 88. Target Python 3.11.
- Tests live in `tests/` and should lock behavior: the threshold boundaries, both polarities, withheld caveats, the worked example `0 4 0 0 8 0 0 4 0`, and the workbook's original question text.
- The public verdict strings stay as the author wrote them, including "can not".

## Gotchas

- The 2017 macro is wrong even after the last commit, which only switched the answer mark from `Y` to `A`, commented out a debug dump into column P, and replaced a duplicated caveat on question 9. It still maps counters 1 and 2 onto column G, never reads column O, and scans rows 1–10. Do not "fix" the Python port by copying those bugs back in. Do not patch `vbaProject.bin` by hand.
- `Cells` in the old macro means the active sheet. The button sits on the questionnaire, which is why it appeared to run. The replacement macro addresses `Sheets(2)` and `Sheets(3)` directly. Sheet 3 is named `Result` in the `.xlsm` and `Results` in the `.xlsx`.
- An unanswered question is not a zero. The old macro treated empty cells as 0, and the "below 5" caveats then fired on blank answers.
- More than one `A` on a row is an error in the replacement macro. The old macro added every mark it found.
- `importlib.resources` reads the HTML and CSS out of the package. If you move `web/`, update `server.py` and `[tool.setuptools.package-data]`.
- The workbooks embed a desktop path (`C:\Users\Pranav\Desktop\Usefulness of process workbook\`) and printer-settings blobs. That is leftover Excel metadata, not a credential. Leave the files byte-for-byte.
- There is no license file. Do not add one.
- The author's email appears in the README because the 2017 README published it as a contact. Do not copy it into config, samples, or logs.

## Leave alone

The two workbooks, the decision to score one step rather than a whole product, the threshold of 30, and the recommendation to remove process rather than add it. This is not a framework, a web service, or a new methodology.
