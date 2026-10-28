#!/usr/bin/env python3
"""Render an interview prep (JSON) as the same styled page as the report.

The model writes the prep as JSON (see references/prep-schema.md). Evidence lives only in quote
fields, each checked against its own document: `requirement` (likely questions, weak spots) and
`vacancy` (brush up) against the vacancy, `episode` against the CV. Everything else is free text
and is shown without quote marks, so it never looks like a citation.

Usage:
  python build_prep.py prep.json prep.html --cv cv.txt --vacancy vacancy.txt
  python build_prep.py prep.json prep.html --cv cv.txt --vacancy vacancy.txt --pdf prep.pdf

--cv       the CV. `episode` must be quoted from it (at least 12 characters). Repeatable.
--vacancy  the vacancy. `requirement` and brush-up `vacancy` must be quoted from it. Repeatable.
--pdf      also write a PDF (needs Playwright with Chromium).
--force    write the page even if some quotes were not found (they are marked on the page).
Both --cv and --vacancy are required: without them, or with only one, no page is written (exit 2, also
with --force). There is no --source: a prep always names which file is the CV and which is the vacancy.
An empty file (only whitespace) is refused (exit 2). A file under 200 characters without spaces, or
the same file / the same text given as --cv and --vacancy, only prints a warning.
Labels follow "lang" in the JSON: "en" (default) or "uk" (case-insensitive, "uk-UA" and "ua" work too).
Every section is optional; a prep with only `brush_up` (the topic checklist) is valid.
Exit code: 0 ok, 1 invalid prep or quotes not found, 2 usage or input error (a flag without
a value, --cv or --vacancy missing, --source, a missing, empty or non-UTF-8 file, malformed JSON).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_report import (  # noqa: E402 – labels live in build_report.LABELS
    CSS, STATUS, badge, build_cli, cmd_buttons, copy_js, esc, free, labels, li, theme_button)
from evidence import blank, check_fields, confirmed_error, strip_quote_marks  # noqa: E402
from verify_quotes import InputError, utf8_output  # noqa: E402

SECTIONS = ("questions", "weak_spots", "brush_up", "ask_them", "before_call", "next_steps")
GROUPS = ("role", "technical", "behavioral", "motivation")


def items(data, key):
    """The list in `key`, or [] (every section is optional)."""
    value = data.get(key)
    return value if isinstance(value, list) else []


def validate(data):
    """Return a list of problems with the prep JSON. Empty list = valid. No field is required."""
    if not isinstance(data, dict):
        return ["the prep must be a JSON object"]
    errs = []
    for key in SECTIONS:
        if key in data and not isinstance(data[key], list):
            errs.append(f"`{key}` must be a list")
    for key in ("questions", "weak_spots", "brush_up", "ask_them", "next_steps"):
        for k, it in enumerate(items(data, key), 1):
            if not isinstance(it, dict):
                errs.append(f"{key} {k}: must be an object")
    for k, q in enumerate(items(data, "questions"), 1):
        if not isinstance(q, dict):
            continue
        where = f"question {k}"
        if "status" in q and q["status"] not in STATUS:
            errs.append(f"{where}: status must be one of {sorted(STATUS)}")
        for key in ("requirement", "episode"):
            if blank(q.get(key)):
                errs.append(f"{where}: `{key}` must be non-blank text")
        if confirmed_error(q):
            errs.append(f"{where}: {confirmed_error(q)}")
        if q.get("status") == "match" and (q.get("episode") is None or blank(q.get("episode"))):
            errs.append(f"{where}: a match needs an episode")
    for key, field in (("weak_spots", "requirement"), ("brush_up", "vacancy")):
        for k, it in enumerate(items(data, key), 1):
            if isinstance(it, dict) and blank(it.get(field)):
                errs.append(f"{key} {k}: `{field}` must be non-blank text")
    for k, n in enumerate(items(data, "next_steps"), 1):
        if isinstance(n, dict) and not (n.get("label") and n.get("command")):
            errs.append(f"next_steps {k}: needs `label` and `command`")
    return errs


def quote_fields(data):
    """Yield (label, text, doc) for every field that must be copied verbatim from a source."""
    for q in items(data, "questions"):
        if isinstance(q, dict):
            yield "requirement", q.get("requirement"), "vacancy"
            if q.get("confirmed") is not True:  # only a real `true` skips the check
                yield "episode", q.get("episode"), "cv"
    for w in items(data, "weak_spots"):
        if isinstance(w, dict):
            yield "weak spot requirement", w.get("requirement"), "vacancy"
    for b in items(data, "brush_up"):
        if isinstance(b, dict):
            yield "brush up vacancy", b.get("vacancy"), "vacancy"


def missing_quotes(data, sources=None, cv=None, vacancy=None):
    """Return [(label, text)] for quote fields not in their own document, blank, or too short (episode)."""
    sources = list(sources or [])
    return check_fields(list(quote_fields(data)), cv=list(cv or []) + sources, vacancy=list(vacancy or []) + sources)


def quote(text, label, bad):
    cls = ' class="missing"' if (label, text) in bad else ""
    return f"<q{cls}>{esc(text)}</q>"


def render_question(q, L, bad):
    head = (badge(q["status"], L) + " " if q.get("status") in STATUS else "")
    head += quote(q["requirement"], "requirement", bad) if q.get("requirement") else ""
    notes = []
    if q.get("episode"):
        if q.get("confirmed") is True:
            notes.append(f'{esc(L["tp_cv"])}: {free(q["episode"])} <span class="tag">{esc(L["confirmed"])}</span>')
        else:
            notes.append(f'{esc(L["tp_cv"])}: {quote(q["episode"], "episode", bad)}')
    else:
        notes.append(esc(L["prep_no_episode"]))
    if q.get("frame"):
        notes.append(f'{esc(L["prep_frame"])}: {free(q["frame"])}')
    return f'<li style="margin:10px 0"><strong>{head}</strong><span class="note">{"<br>".join(notes)}</span></li>'


def render(data, bad=()):
    L = labels(data.get("lang"))
    bad = set(bad)
    title = strip_quote_marks(data.get("title") or L["prep_title"])
    parts = [f"<h1>{esc(title)}</h1>"]
    if data.get("profile_source"):
        parts.append(f'<p class="src">{esc(L["profile"])}: {free(data["profile_source"])}</p>')
    if data.get("process"):
        parts.append(f'<h2>{esc(L["prep_process"])}</h2><div class="card">{free(data["process"])}</div>')
    questions = [q for q in items(data, "questions") if isinstance(q, dict)]
    if questions:
        parts.append(f'<h2>{esc(L["prep_questions"])}</h2><div class="card">')
        groups = {}
        for q in questions:
            groups.setdefault(q.get("group") or "", []).append(q)
        for name, qs in groups.items():
            if name:
                shown = L["group_" + name] if name in GROUPS else strip_quote_marks(name)
                parts.append(f'<h3 style="margin-top:0">{esc(shown)}</h3>')
            parts.append('<ol style="padding-left:1.2rem;margin:0 0 12px">'
                         + "".join(render_question(q, L, bad) for q in qs) + "</ol>")
        parts.append("</div>")
    weak = [w for w in items(data, "weak_spots") if isinstance(w, dict)]
    if weak:
        parts.append(f'<h2>{esc(L["prep_weak"])}</h2><div class="card">' + li(
            [free(w.get("text")) + (f'<span class="note">{esc(L["tp_vacancy"])}: '
                                    f'{quote(w["requirement"], "weak spot requirement", bad)}</span>'
                                    if w.get("requirement") else "") for w in weak]) + "</div>")
    brush = [b for b in items(data, "brush_up") if isinstance(b, dict)]
    if brush:
        parts.append(f'<h2>{esc(L["prep_brush"])}</h2><div class="card">' + li(
            [free(b.get("topic")) + (f'<span class="note">{esc(L["tp_vacancy"])}: '
                                     f'{quote(b["vacancy"], "brush up vacancy", bad)}</span>'
                                     if b.get("vacancy") else "") for b in brush]) + "</div>")
    if data.get("money"):
        parts.append(f'<h2>{esc(L["money"])}</h2><div class="card">{free(data["money"])}</div>')
    ask = [a for a in items(data, "ask_them") if isinstance(a, dict)]
    if ask:
        parts.append(f'<h2>{esc(L["prep_ask"])}</h2><div class="card">' + li(
            [free(a.get("question")) + (f'<span class="note">{free(a["why"])}</span>' if a.get("why") else "")
             for a in ask]) + "</div>")
    if items(data, "before_call"):
        parts.append(f'<h2>{esc(L["prep_before"])}</h2><div class="card">'
                     + li([free(x) for x in items(data, "before_call")]) + "</div>")
    steps = [n for n in items(data, "next_steps") if isinstance(n, dict)]
    if steps:
        # Not stripped: next steps are phrases to paste, not claims.
        parts.append(f'<h2>{esc(L["next_steps"])}</h2>' + cmd_buttons([(n["label"], n["command"]) for n in steps], L))
    body = "\n".join(parts)
    return (f'<!doctype html><html lang="{L["html_lang"]}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="generator" content="job-fit">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}</main>'
            f'{theme_button(L)}{copy_js(L)}</body></html>')


def main(argv):
    try:
        return build_cli(argv[1:], usage=__doc__, kind="prep JSON", validate=validate, missing=missing_quotes,
                         render=render, cv_labels=("episode",), allow_source=False)
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    utf8_output()
    sys.exit(main(sys.argv))
