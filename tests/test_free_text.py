"""Step 7b: free text never looks like a citation. Only checked quote fields are shown as quotes."""
import copy
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_report as br  # noqa: E402

EX = os.path.join(ROOT, "examples", "frontend")


def report():
    with open(os.path.join(EX, "report.json"), encoding="utf-8") as f:
        return json.load(f)


def shown(text):
    """How `text` appears in the page source after escaping."""
    return html.escape(text, quote=True)


def test_strip_quote_marks_helper():
    from evidence import strip_quote_marks
    assert strip_quote_marks('«Нова Пошта» pays "led a team of 40" „x“ “y” ‘z’ \'w\'') == \
        "Нова Пошта pays led a team of 40 x y z w"
    for kept in ("з'явилась", "зʼявилась", "don't", "it’s", "the 1990's", "4'5"):
        assert strip_quote_marks(kept) == kept
    assert strip_quote_marks("the students' work, a 27\" screen") == "the students work, a 27 screen"
    assert strip_quote_marks(None) is None and strip_quote_marks(5) == 5


def test_quote_marks_in_note_money_and_verdict_are_removed():
    d = report()
    v = d["vacancies"][0]
    v["verdict"]["text"] = 'The CV says "led a team of 40" – check it.'
    v["money"] = "Paid via «Нова Пошта» transfers."
    v["requirements"][0]["note"] = '"led a team of 40" is not in the CV'
    page = br.render(d)
    for marked in ('"led a team of 40"', "«Нова Пошта»"):
        assert shown(marked) not in page, marked
    assert "led a team of 40" in page and "Нова Пошта" in page


# Every free-text field of the report that is stripped, set to a marker wrapped in quote marks.
# Not here on purpose: letter_draft and next_steps (see test_letter_draft_and_next_steps_keep_their_marks).
def fill_free_text(d):
    n = iter(range(1000))
    def mark():
        k = next(n)
        return f'«F{k}a» "F{k}b"', k
    marks = []
    def put(obj, key):
        text, k = mark()
        obj[key] = text
        marks.append(k)
    put(d, "title")
    put(d, "profile_source")
    v = d["vacancies"][0]
    put(v, "title")
    put(v["verdict"], "text")
    text, k = mark(); v["would_change"] = [text]; marks.append(k)
    put(v["requirements"][0], "note")
    v["cv_fixes"] = [{"kind": "Reword", "text": None}]; put(v["cv_fixes"][0], "text")
    text, k = mark(); text2, k2 = mark()
    v["growth"] = {"new": [{"text": text, "tag": "guess"}], "same": [text2], "unknown": []}; marks += [k, k2]
    v["red_flags"] = [{"quote": v["requirements"][0]["requirement"], "text": None}]; put(v["red_flags"][0], "text")
    put(v, "money")
    v["questions"] = [{"question": None, "why": None}]
    put(v["questions"][0], "question"); put(v["questions"][0], "why")
    v["talking_points"] = [{"point": None, "cv": None, "vacancy": None}]; put(v["talking_points"][0], "point")
    row = {"vacancy": None, "verdict": "skip", "reason": None, "check": None}
    put(row, "vacancy"); put(row, "reason"); put(row, "check")
    text, k = mark(); text2, k2 = mark()
    d["summary"] = {"rows": [row], "patterns": [text], "next": [text2]}; marks += [k, k2]
    dec = {"question": None, "options": [None], "affects": None}
    put(dec, "question"); text, k = mark(); dec["options"] = [text]; marks.append(k); put(dec, "affects")
    d["decide"] = [dec]
    return marks


def test_every_free_text_field_is_shown_without_quote_marks():
    d = report()
    marks = fill_free_text(d)
    assert br.validate(d) == []
    page = br.render(d)
    for k in marks:
        assert f"F{k}a" in page and f"F{k}b" in page, k
        for marked in (f"«F{k}a»", f'"F{k}b"'):
            assert shown(marked) not in page, (k, marked)


def test_quote_fields_still_render_as_quotes():
    d = report()
    v = d["vacancies"][0]
    v["red_flags"] = [{"quote": "«Нова Пошта» pays до $1000", "text": "low pay"}]
    page = br.render(d)
    assert f'<q>{shown("«Нова Пошта» pays до $1000")}</q>' in page  # the quote field keeps its marks
    req = v["requirements"][0]["requirement"]
    assert f"<q>{shown(req)}</q>" in page


def test_apostrophes_inside_words_are_kept():
    d = report()
    d["vacancies"][0]["money"] = "Ставка зʼявилась; it’s net; we don't know; з'явилась"
    page = br.render(d)
    for word in ("зʼявилась", "it’s", "don't", "з'явилась"):
        assert shown(word) in page, word


def test_letter_draft_and_next_steps_keep_their_marks():
    # The draft is the user's own text to send; next steps are phrases to paste, not claims.
    d = report()
    draft = 'I shipped "fast checkout" at «Нова Пошта».'
    d["vacancies"][0]["letter_draft"] = draft
    d["next_steps"] = [{"label": "Prep for «Нова Пошта»", "command": 'Prepare me for "Senior QA" at «Нова Пошта»'}]
    page = br.render(d)
    assert f'<div style="white-space:pre-wrap;line-height:1.55">{shown(draft)}</div>' in page
    assert f'data-cmd="{shown(draft)}"' in page  # the copy button copies it unchanged
    assert f'<span class="cl">{shown("Prep for «Нова Пошта»")}</span>' in page
    assert f'data-cmd="{shown(d["next_steps"][0]["command"])}"' in page


def test_json_is_not_changed_by_rendering():
    d = report()
    d["vacancies"][0]["money"] = "«Нова Пошта»"
    before = copy.deepcopy(d)
    br.render(d)
    assert d == before and br.validate(d) == []
