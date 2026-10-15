"""The original .xlsm stays the historical source of the nine questions."""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

# Text as stored in the macro workbook, typos included. The Python questions
# correct "serve to service" and "maintence"; this test keeps the file honest.
WORKBOOK_QUESTIONS = (
    "Will the end user have an impact if this step is removed?",
    "Do any other parties involved in the development process have a "
    "dependency on this step?",
    "Was this step introduced reactively to solve a problem?",
    "Are tasks performed in this step unique (i.e. no redundant tasks in any "
    "other steps)?",
    "Do the tasks performed in this step necessarily involve manual "
    "contribution (cannot be automated)?",
    "Is this step a single unit that can not be broken down into further steps?",
    "Does this step serve to service a mandatory/regulatory requirement?",
    "Will there be over one Full Time Equivalent man month of effort required "
    "to remove/replace this step?",
    "Does this step have an impact on tasks that would help make maintence "
    "easier (logging/documentation)?",
)


def _shared_strings(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as workbook:
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("m:si", NS):
        text_nodes = item.iter(f"{{{NS['m']}}}t")
        strings.append("".join(text.text or "" for text in text_nodes))
    return strings


def test_macro_workbook_still_holds_the_original_questions():
    strings = _shared_strings(ROOT / "Usefulness of process workbook.xlsm")
    for question in WORKBOOK_QUESTIONS:
        assert question in strings
    assert "No" in strings
    assert "Yes" in strings
    assert "To some extent" in strings
    assert "RESULT" in strings


def test_earlier_draft_keeps_its_own_wording():
    strings = _shared_strings(ROOT / "Usefulness of process workbook.xlsx")
    assert "Was this step introduce reactively to solve a problem?" in strings
    assert (
        "Are tasks performed in this step redundant to tasks performed in "
        "other steps of the development process?" in strings
    )
    assert "Can the tasks performed in this step be automated by code?" in strings
