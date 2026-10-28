#!/usr/bin/env python3
"""Render a job-fit analysis (JSON) as one self-contained, styled HTML page.

The model writes the analysis as compact JSON (see references/report-schema.md);
this script turns it into a readable page with status marks, colors, a light page with a dark toggle
and print styles. Fast, and the same look every time. Everything is escaped.

Usage:
  python build_report.py analysis.json report.html --cv cv.txt --vacancy vacancy.txt
  python build_report.py analysis.json report.html --cv cv.txt --vacancy vacancy.txt --pdf report.pdf

--cv       the CV. `evidence` and talking point `cv` must be quoted from it. Repeatable.
--vacancy  the vacancy. `requirement`, red flag `quote` and talking point `vacancy` must be
           quoted from it. Repeatable.
--source   old form: a document of unknown role, counts for both. Prints a warning; use
           --cv and --vacancy. Without any of these the quotes are NOT checked.
--pdf      also write a PDF (needs Playwright with Chromium). Otherwise open the HTML
           and print it to PDF; the print styles are included.
--force    write the page even if some quotes were not found (they are marked on the page).
Labels (headings, statuses, verdicts) follow "lang" in the JSON: "en" (default) or "uk"
(case-insensitive, "uk-UA" and "ua" work too). An unknown lang prints a warning and uses English.
`confirmed` must be true or false; a quote field that is present (not null) must be non-blank text.
Exit code: 0 ok, 1 invalid analysis or quotes not found, 2 usage or input error (a flag without
a value, a missing or non-UTF-8 file, malformed JSON).
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evidence import (  # noqa: E402,F401 – normalize and too_short are re-exported
    MIN_LEN, blank, check_fields, confirmed_error, normalize, strip_quote_marks, too_short)
from verify_quotes import InputError, flag_value, read_json, read_text, utf8_output  # noqa: E402

STATUS = {
    "match": ("✅", "Match"),
    "partial": ("⚠️", "Partial"),
    "unknown": ("❓", "Not in CV"),
    "gap": ("❌", "Gap"),
}
VERDICT = {
    "apply": ("✅", "Apply"),
    "questions": ("⚠️", "Apply with questions"),
    "check": ("❓", "Needs a check first"),
    "skip": ("❌", "Skip"),
}
TAGS = {"stated", "guess"}

# Every fixed string on the page, per language. `lang` in the JSON picks one; English is the default.
LABELS = {
    "en": {
        "html_lang": "en",
        "status": {k: v[1] for k, v in STATUS.items()},
        "verdict": {k: v[1] for k, v in VERDICT.items()},
        "would_change": "What would change the verdict",
        "requirements": "Requirements vs CV",
        "col_requirement": "Requirement", "col_evidence": "Evidence", "col_status": "Status",
        "confirmed": "confirmed by you",
        "cv_fixes": "Fix in the CV",
        "growth": "Growth", "growth_new": "New for you", "growth_same": "Same as now", "growth_unknown": "Can’t tell",
        "red_flags": "Red flags",
        "money": "Money and format",
        "questions": "Questions to ask", "questions_general": "General",
        "talking_points": "Talking points for the application", "tp_cv": "CV", "tp_vacancy": "Vacancy",
        "letter": "Application draft", "letter_note": "Draft – check every claim before sending.",
        "letter_copy": "Copy the draft",
        "summary": "Summary", "col_n": "#", "col_vacancy": "Vacancy", "col_verdict": "Verdict",
        "col_reason": "Main reason", "col_check": "Check first", "patterns": "Patterns", "next": "Next",
        "decide": "Questions that decide this", "affects": "Affects",
        "next_steps": "What next",
        "profile": "Profile", "profile_unknown": "not stated",
        "report_title": "Job fit report", "page_title": "Document",
        "theme": "Theme", "light": "Light", "dark": "Dark", "copy": "Copy", "copied": "Copied",
    },
    "uk": {
        "html_lang": "uk",
        "status": {"match": "Збіг", "partial": "Частково", "unknown": "Немає в резюме", "gap": "Прогалина"},
        "verdict": {"apply": "Подаватися", "questions": "Подаватися з питаннями",
                    "check": "Спершу перевірити", "skip": "Пропустити"},
        "would_change": "Що змінило б вердикт",
        "requirements": "Вимоги і резюме",
        "col_requirement": "Вимога", "col_evidence": "Доказ", "col_status": "Статус",
        "confirmed": "підтверджено вами",
        "cv_fixes": "Що виправити в резюме",
        "growth": "Зростання", "growth_new": "Нове для вас", "growth_same": "Як зараз", "growth_unknown": "Не зрозуміло",
        "red_flags": "Тривожні сигнали",
        "money": "Гроші й формат",
        "questions": "Що запитати", "questions_general": "Загальні",
        "talking_points": "Тези для відгуку", "tp_cv": "Резюме", "tp_vacancy": "Вакансія",
        "letter": "Чернетка відгуку", "letter_note": "Чернетка – перевірте кожне твердження перед надсиланням.",
        "letter_copy": "Скопіювати чернетку",
        "summary": "Підсумок", "col_n": "#", "col_vacancy": "Вакансія", "col_verdict": "Вердикт",
        "col_reason": "Головна причина", "col_check": "Спершу перевірити", "patterns": "Закономірності", "next": "Далі",
        "decide": "Питання, від яких залежить рішення", "affects": "Впливає на",
        "next_steps": "Що далі",
        "profile": "Профіль", "profile_unknown": "не вказано",
        "report_title": "Звіт про відповідність", "page_title": "Документ",
        "theme": "Тема", "light": "Світла", "dark": "Темна", "copy": "Копіювати", "copied": "Скопійовано",
    },
}


LANG_ALIASES = {"ua": "uk"}


def lang_key(lang):
    """`UK`, ` uk-UA `, `ua` -> "uk": case-insensitive, the part before "-", plus aliases."""
    if not isinstance(lang, str):
        return None
    key = lang.strip().lower().split("-")[0]
    return LANG_ALIASES.get(key, key)


def labels(lang):
    """The label dict for `lang`; English for a missing or unknown language (the CLI warns about it)."""
    return LABELS.get(lang_key(lang), LABELS["en"])


def warn_lang(lang):
    if lang_key(lang) not in LABELS:
        print(f"warning: unknown lang {lang!r}, using English labels (built in: {', '.join(LABELS)})")

CSS = """
:root{color-scheme:light;--bg:#f7f7f5;--card:#ffffff;--text:#1d1d1b;--muted:#5f5e5a;--line:#e3e2dc;
--ok:#1a7f37;--ok-bg:#e6f4ea;--warn:#9a6700;--warn-bg:#fff4d6;--unk:#3b5bdb;--unk-bg:#e8edff;
--bad:#c62828;--bad-bg:#fde8e8;--accent:#1d1d1b;
--mint:#3ccfa9;--mint-bg:#e2f8f1;--mint-ink:#0d6b55;--coral:#f4694c;--coral-bg:#fff0ec}
:root[data-jf="dark"]{color-scheme:dark;--mint:#3ccfa9;--mint-bg:#10302a;--mint-ink:#6fe3c5;--coral:#ff846b;--coral-bg:#341c17;--bg:#161615;--card:#1f1f1d;--text:#ececea;--muted:#a3a29c;--line:#34332f;--ok:#56d364;
--ok-bg:#12261a;--warn:#e3b341;--warn-bg:#2b2410;--unk:#8fa8ff;--unk-bg:#1a2140;--bad:#ff7b72;--bad-bg:#2d1618;--accent:#ececea}
html{color-scheme:light!important;background:var(--bg)}html[data-jf="dark"]{color-scheme:dark!important}
*{box-sizing:border-box}
main::before{content:"";display:block;height:6px;border-radius:6px;margin-bottom:22px;background:linear-gradient(90deg,var(--mint) 0 60%,var(--coral) 60% 100%)}
#tt{position:fixed;top:12px;right:12px;display:inline-flex;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:3px;gap:2px;z-index:5}
#tt button{border:0;background:transparent;color:var(--muted);font:inherit;font-size:.8rem;border-radius:999px;padding:3px 12px;cursor:pointer}
#tt button.on{background:var(--mint);color:#06372c;font-weight:600}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:900px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:1.5rem;line-height:1.25;margin:0 0 4px}
h2{font-size:1.05rem;margin:28px 0 10px;letter-spacing:.01em;padding-left:10px;border-left:4px solid var(--coral)}
h3{font-size:.95rem;margin:16px 0 6px;color:var(--muted)}
.src{color:var(--mint-ink);font-size:.85rem;margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:12px 0}
.verdict{border-left:6px solid var(--mint)}
.verdict.apply{border-left-color:var(--ok)}.verdict.questions{border-left-color:var(--warn)}
.verdict.check{border-left-color:var(--unk)}.verdict.skip{border-left-color:var(--bad)}
.vlabel{font-weight:700;font-size:1.15rem;margin:0 0 4px}
.badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 10px;font-size:.82rem;font-weight:600;white-space:nowrap}
.badge.match{color:var(--ok);background:var(--ok-bg)}.badge.partial{color:var(--warn);background:var(--warn-bg)}
.badge.unknown{color:var(--unk);background:var(--unk-bg)}.badge.gap{color:var(--bad);background:var(--bad-bg)}
.tag{font-size:.72rem;border:1px solid var(--line);border-radius:6px;padding:0 6px;color:var(--muted);margin-left:6px;white-space:nowrap}
.note{color:var(--muted);font-size:.88rem;display:block;margin-top:4px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
q{quotes:"\\201C" "\\201D"}
.ev{color:var(--muted)}
ul{margin:6px 0 0;padding-left:1.2rem}li{margin:4px 0}
.cols{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.cols .card{margin:0}
.flag{border-left:4px solid var(--bad)}
.opts{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.opt{background:var(--mint-bg);color:var(--mint-ink);border:1px solid var(--mint);border-radius:8px;padding:3px 10px;font-size:.88rem}
.kind{font-weight:600;color:var(--coral)}
a{color:var(--mint-ink)}th{border-bottom:2px solid var(--mint)}
.missing{outline:2px dashed var(--bad)}
nav ul{list-style:none;padding:0}
.cmds{display:grid;gap:10px;margin:12px 0}
.cmd{display:grid;grid-template-columns:1fr auto;gap:2px 12px;align-items:center;text-align:left;width:100%;font:inherit;color:var(--text);background:var(--card);border:1px solid var(--line);border-left:5px solid var(--mint);border-radius:12px;padding:10px 14px;cursor:pointer}
.cmd:hover{border-left-color:var(--coral)}.cmd.ok{border-left-color:var(--ok)}
.cmd .cl{font-weight:600;grid-column:1}.cmd code{grid-column:1;color:var(--mint-ink);background:var(--mint-bg);border-radius:6px;padding:2px 8px;font-size:.88rem;justify-self:start;white-space:normal}
.cmd .cp{grid-column:2;grid-row:1 / span 2;font-size:.78rem;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:2px 10px}
@media (max-width:680px){
 .cols{grid-template-columns:1fr}
 table,thead,tbody,tr,td{display:block}thead{display:none}
 tr{border:1px solid var(--line);border-radius:10px;margin:10px 0;padding:6px 4px}
 td{border:0;padding:6px 10px}td::before{content:attr(data-l);display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
}
@media print{#tt,.cp{display:none}body{background:#fff;color:#000}main{max-width:none;padding:0}.card{break-inside:avoid;border-color:#bbb}tr{break-inside:avoid}
 .verdict{border-left-width:6px}}
"""

def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def theme_button(L=None):
    L = L or LABELS["en"]
    return (
        f'<div id="tt" role="group" aria-label="{esc(L["theme"])}">'
        f'<button type="button" data-t="light" class="on">{esc(L["light"])}</button>'
        f'<button type="button" data-t="dark">{esc(L["dark"])}</button></div>'
        "<script>document.getElementById('tt').addEventListener('click',function(e){"
        "var b=e.target.closest('button');if(!b)return;"
        "document.documentElement.setAttribute('data-jf',b.dataset.t);"
        "this.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)})});</script>"
    )


def copy_js(L=None):
    L = L or LABELS["en"]
    def js(s):  # a single-quoted JS string literal
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("<", "\\x3c") + "'"
    copied, copy_ = js(L["copied"]), js(L["copy"])
    return (
        "<script>document.addEventListener('click',function(e){var b=e.target.closest('[data-cmd]');if(!b)return;"
        "var t=b.getAttribute('data-cmd'),s=b.querySelector('.cp');"
        f"function done(){{b.classList.add('ok');if(s)s.textContent={copied};"
        f"setTimeout(function(){{b.classList.remove('ok');if(s)s.textContent={copy_}}},1500)}}"
        "function fb(){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();"
        "try{document.execCommand('copy')}catch(x){}a.remove();done()}"
        "if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fb)}else{fb()}"
        "});</script>"
    )


THEME_BUTTON = theme_button()
COPY_JS = copy_js()


def cmd_buttons(items, L=None):
    """Copy-to-clipboard buttons: items = [(label, command)]. The page never sends anything itself."""
    copy_ = esc((L or LABELS["en"])["copy"])
    return '<div class="cmds">' + "".join(
        f'<button type="button" class="cmd" data-cmd="{esc(c)}"><span class="cl">{esc(l)}</span>'
        f'<code>{esc(c)}</code><span class="cp">{copy_}</span></button>' for l, c in items) + "</div>"


def check_item(errs, where, item, quote_keys):
    """Blank quote fields and a non-boolean `confirmed` in one requirement, red flag or talking point."""
    for key in quote_keys:
        if blank(item.get(key)):
            errs.append(f"{where}: `{key}` must be non-blank text")
    if confirmed_error(item):
        errs.append(f"{where}: {confirmed_error(item)}")


def validate(data):
    """Return a list of problems with the analysis JSON. Empty list = valid."""
    if not isinstance(data, dict):
        return ["the analysis must be a JSON object with `vacancies`"]
    errs = []
    vacs = data.get("vacancies")
    if not isinstance(vacs, list) or not vacs:
        return ["`vacancies` must be a non-empty list"]
    for i, v in enumerate(vacs, 1):
        p = f"vacancy {i}"
        if not v.get("title"):
            errs.append(f"{p}: missing title")
        ver = v.get("verdict") or {}
        if ver.get("mark") not in VERDICT:
            errs.append(f"{p}: verdict.mark must be one of {sorted(VERDICT)}")
        if not ver.get("text"):
            errs.append(f"{p}: verdict.text is empty")
        for j, r in enumerate(v.get("requirements", []), 1):
            if r.get("status") not in STATUS:
                errs.append(f"{p}, requirement {j}: status must be one of {sorted(STATUS)}")
            check_item(errs, f"{p}, requirement {j}", r, ("requirement", "evidence"))
            if r.get("requirement") is None:
                errs.append(f"{p}, requirement {j}: empty requirement")
            if r.get("status") == "match" and (r.get("evidence") is None or blank(r.get("evidence"))):
                errs.append(f"{p}, requirement {j}: a match needs evidence")
        for k, f in enumerate(v.get("red_flags", []), 1):
            check_item(errs, f"{p}, red flag {k}", f, ("quote",))
        for k, t in enumerate(v.get("talking_points", []), 1):
            check_item(errs, f"{p}, talking point {k}", t, ("cv", "vacancy"))
        if "letter_draft" in v and not isinstance(v["letter_draft"], str):
            errs.append(f"{p}: `letter_draft` must be a string")
        for part in ("new", "same", "unknown"):
            for g in (v.get("growth") or {}).get(part, []):
                if isinstance(g, dict) and g.get("tag") not in TAGS:
                    errs.append(f"{p}: growth tag must be 'stated' or 'guess'")
    for k, n in enumerate(data.get("next_steps", []), 1):
        if not (isinstance(n, dict) and n.get("label") and n.get("command")):
            errs.append(f"next_steps {k}: needs `label` and `command`")
    for r in (data.get("summary") or {}).get("rows", []):
        if r.get("verdict") not in VERDICT:
            errs.append(f"summary row '{r.get('vacancy')}': verdict must be one of {sorted(VERDICT)}")
    return errs


def quote_fields(v):
    """Yield (label, text, doc) for every field that must be copied verbatim from a source.

    `doc` is the document the quote must come from: "cv" or "vacancy".
    """
    # Only a real `true` skips the check: "false" (a string) is truthy in Python.
    for r in v.get("requirements", []):
        yield "requirement", r.get("requirement"), "vacancy"
        if r.get("confirmed") is not True:
            yield "evidence", r.get("evidence"), "cv"
    for f in v.get("red_flags", []):
        yield "red flag quote", f.get("quote"), "vacancy"
    for t in v.get("talking_points", []):
        if t.get("confirmed") is not True:
            yield "talking point (CV)", t.get("cv"), "cv"
        yield "talking point (vacancy)", t.get("vacancy"), "vacancy"


def missing_quotes(data, sources=None, cv=None, vacancy=None):
    """Return [(label, text)] for quoted fields not found in their own document, blank, or too short.

    `cv` and `vacancy` are lists of texts with a known role: CV quotes are checked only against
    `cv`, vacancy quotes only against `vacancy`. `sources` are texts of unknown role and count for
    both (the old behavior). Every text is checked on its own and at word boundaries (evidence.py).
    A role with no texts at all is not checked for presence, but CV quotes are always checked for length.
    """
    sources = list(sources or [])
    fields = [f for v in data.get("vacancies", []) for f in quote_fields(v)]
    return check_fields(fields, cv=list(cv or []) + sources, vacancy=list(vacancy or []) + sources)


def free(text):
    """Escape a free-text field for the page, without quote marks: only checked quote fields look like quotes."""
    return esc(strip_quote_marks(text))


def badge(status, L):
    return f'<span class="badge {status}">{STATUS[status][0]} {esc(L["status"][status])}</span>'


def li(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""


def growth_item(g):
    if isinstance(g, dict):
        return free(g.get("text")) + f'<span class="tag">{esc(g.get("tag"))}</span>'
    return free(g)


def render_vacancy(v, idx, bad, single=False, L=None):
    L = L or LABELS["en"]
    o = []
    mark = v["verdict"]["mark"]
    vm, vl = VERDICT[mark][0], esc(L["verdict"][mark])
    head = "" if single else f'<h2>{free(v["title"])}</h2>'
    o.append(f'<section id="v{idx}">{head}')
    o.append(f'<div class="card verdict {esc(mark)}"><p class="vlabel">{vm} {vl}</p>'
             f'<p style="margin:0">{free(v["verdict"]["text"])}</p></div>')
    if v.get("would_change"):
        o.append(f'<h3>{esc(L["would_change"])}</h3>' + li([free(x) for x in v["would_change"]]))
    reqs = v.get("requirements", [])
    if reqs:
        c_req, c_ev, c_st = esc(L["col_requirement"]), esc(L["col_evidence"]), esc(L["col_status"])
        o.append(f'<h2>{esc(L["requirements"])}</h2><div class="card"><table><thead><tr><th>{c_req}</th>'
                 f'<th>{c_ev}</th><th>{c_st}</th></tr></thead><tbody>')
        for r in reqs:
            req_cls = ' class="missing"' if ("requirement", r.get("requirement")) in bad else ""
            ev = r.get("evidence")
            ev_cls = ' class="missing"' if ("evidence", ev) in bad else ""
            confirmed = r.get("confirmed") is True
            ev_html = f'<q class="ev"{ev_cls}>{esc(ev)}</q>' if ev and not confirmed else (
                free(ev) if ev else '<span class="ev">—</span>')
            note = f'<span class="note">{free(r["note"])}</span>' if r.get("note") else ""
            conf = f'<span class="tag">{esc(L["confirmed"])}</span>' if confirmed else ""
            o.append(f'<tr><td data-l="{c_req}"><q{req_cls}>{esc(r["requirement"])}</q></td>'
                     f'<td data-l="{c_ev}">{ev_html}</td>'
                     f'<td data-l="{c_st}">{badge(r["status"], L)}{conf}{note}</td></tr>')
        o.append('</tbody></table></div>')
    if v.get("cv_fixes"):
        o.append(f'<h2>{esc(L["cv_fixes"])}</h2><div class="card">' + li(
            [f'<span class="kind">{free(f.get("kind"))}.</span> {free(f.get("text"))}' for f in v["cv_fixes"]]) + '</div>')
    g = v.get("growth")
    if g:
        o.append(f'<h2>{esc(L["growth"])}</h2><div class="cols">')
        for key in ("new", "same", "unknown"):
            o.append(f'<div class="card"><h3 style="margin-top:0">{esc(L["growth_" + key])}</h3>'
                     + li([growth_item(x) for x in g.get(key, [])]) + '</div>')
        o.append('</div>')
    if v.get("red_flags"):
        o.append(f'<h2>{esc(L["red_flags"])}</h2>')
        for f in v["red_flags"]:
            cls = ' class="missing"' if ("red flag quote", f.get("quote")) in bad else ""
            o.append(f'<div class="card flag"><q{cls}>{esc(f.get("quote"))}</q>'
                     f'<span class="note">{free(f.get("text"))}</span></div>')
    if v.get("money"):
        o.append(f'<h2>{esc(L["money"])}</h2><div class="card">{free(v["money"])}</div>')
    if v.get("questions"):
        o.append(f'<h2>{esc(L["questions"])}</h2><div class="card">')
        groups = {}
        for q in v["questions"]:
            groups.setdefault(q.get("group", L["questions_general"]), []).append(q)
        for name, qs in groups.items():
            o.append(f'<h3 style="margin-top:0">{free(name)}</h3>' + li(
                [free(q["question"]) + (f'<span class="note">{free(q["why"])}</span>' if q.get("why") else "")
                 for q in qs]))
        o.append('</div>')
    if v.get("talking_points"):
        o.append(f'<h2>{esc(L["talking_points"])}</h2><div class="card"><ol style="padding-left:1.2rem;margin:0">')
        tp_cv, tp_vac = esc(L["tp_cv"]), esc(L["tp_vacancy"])
        for t in v["talking_points"]:
            src = ""
            if t.get("cv"):
                src += (f'{tp_cv}: <q>{esc(t["cv"])}</q>' if t.get("confirmed") is not True
                        else f'{tp_cv}: {free(t["cv"])} <span class="tag">{esc(L["confirmed"])}</span>')
            if t.get("vacancy"):
                src += f'<br>{tp_vac}: <q>{esc(t["vacancy"])}</q>'
            o.append(f'<li style="margin:10px 0"><strong>{free(t["point"])}</strong>'
                     f'<span class="note">{src}</span></li>')
        o.append('</ol></div>')
    if v.get("letter_draft"):
        # Not stripped: the draft is the user's own text to send («Нова Пошта» is correct there).
        o.append(f'<h2>{esc(L["letter"])}</h2><div class="card">'
                 f'<p class="note" style="margin-top:0">{esc(L["letter_note"])}</p>'
                 f'<div style="white-space:pre-wrap;line-height:1.55">{esc(v["letter_draft"])}</div>'
                 + cmd_buttons([(L["letter_copy"], v["letter_draft"])], L) + '</div>')
    o.append('</section>')
    return "\n".join(o)


def render_summary(summary, vacs, L=None):
    L = L or LABELS["en"]
    cols = [esc(L[k]) for k in ("col_n", "col_vacancy", "col_verdict", "col_reason", "col_check")]
    n, vac, ver, reason, check = cols
    o = [f'<h2>{esc(L["summary"])}</h2><div class="card"><table><thead><tr>'
         + "".join(f"<th>{c}</th>" for c in cols) + '</tr></thead><tbody>']
    for i, r in enumerate(summary.get("rows", []), 1):
        mk, lb = VERDICT[r["verdict"]][0], esc(L["verdict"][r["verdict"]])
        o.append(f'<tr><td data-l="{n}">{i}</td><td data-l="{vac}"><a href="#v{i}">{free(r.get("vacancy"))}</a></td>'
                 f'<td data-l="{ver}">{mk} {lb}</td><td data-l="{reason}">{free(r.get("reason"))}</td>'
                 f'<td data-l="{check}">{free(r.get("check"))}</td></tr>')
    o.append('</tbody></table></div>')
    if summary.get("patterns"):
        o.append(f'<h3>{esc(L["patterns"])}</h3>' + li([free(x) for x in summary["patterns"]]))
    if summary.get("next"):
        o.append(f'<h3>{esc(L["next"])}</h3>' + li([free(x) for x in summary["next"]]))
    return "\n".join(o)


def render_decide(decide, L=None):
    L = L or LABELS["en"]
    o = [f'<h2>{esc(L["decide"])}</h2>']
    for d in decide:
        opts = "".join(f'<span class="opt">{free(x)}</span>' for x in d.get("options", []))
        o.append(f'<div class="card"><strong>{free(d.get("question"))}</strong>'
                 f'<div class="opts">{opts}</div>'
                 + (f'<span class="note">{esc(L["affects"])}: {free(d["affects"])}</span>' if d.get("affects") else "")
                 + '</div>')
    return "\n".join(o)


def render(data, bad=()):
    L = labels(data.get("lang"))
    vacs = data["vacancies"]
    title = strip_quote_marks(data.get("title") or (vacs[0]["title"] if len(vacs) == 1 else L["report_title"]))
    profile = data.get("profile_source", L["profile_unknown"])
    parts = [f'<h1>{esc(title)}</h1>', f'<p class="src">{esc(L["profile"])}: {free(profile)}</p>']
    if data.get("summary"):
        parts.append(render_summary(data["summary"], vacs, L))
    for i, v in enumerate(vacs, 1):
        parts.append(render_vacancy(v, i, set(bad), single=len(vacs) == 1 and not data.get("title"), L=L))
    if data.get("decide"):
        parts.append(render_decide(data["decide"], L))
    if data.get("next_steps"):
        # Not stripped: next steps are phrases to paste, not claims.
        parts.append(f'<h2>{esc(L["next_steps"])}</h2>'
                     + cmd_buttons([(n["label"], n["command"]) for n in data["next_steps"]], L))
    body = "\n".join(parts)
    return (f'<!doctype html><html lang="{L["html_lang"]}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="generator" content="job-fit">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}</main>'
            f'{theme_button(L)}{copy_js(L)}</body></html>')


def to_pdf(html_path, pdf_path):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file://" + os.path.abspath(html_path))
        page.pdf(path=pdf_path, format="A4", print_background=True, margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
        browser.close()
    return True


def main(argv):
    try:
        return build(argv[1:])
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def build(args):
    paths = {"--source": [], "--cv": [], "--vacancy": []}
    pdf, force = None, False
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in paths:
            paths[a].append(flag_value(args, i)); i += 2
        elif a == "--pdf":
            pdf = flag_value(args, i); i += 2
        elif a == "--force":
            force = True; i += 1
        else:
            pos.append(a); i += 1
    if len(pos) != 2:
        print(__doc__)
        return 2
    data = read_json(pos[0], "analysis JSON")
    if not isinstance(data, dict):
        raise InputError(f"analysis JSON must be an object with `vacancies`, not a {type(data).__name__}: {pos[0]}")
    what = {"--source": "source", "--cv": "CV", "--vacancy": "vacancy"}
    texts = {flag: [read_text(s, what[flag]) for s in files] for flag, files in paths.items()}
    errs = validate(data)
    if errs:
        print("INVALID:\n  - " + "\n  - ".join(errs))
        return 1
    warn_lang(data.get("lang", "en"))
    bad = []
    if any(paths.values()):
        if paths["--source"]:
            print("warning: --source does not know which file is the CV; use --cv and --vacancy")
        elif not paths["--cv"]:
            print("warning: no --cv given, CV quotes were NOT checked")
        elif not paths["--vacancy"]:
            print("warning: no --vacancy given, vacancy quotes were NOT checked")
        bad = missing_quotes(data, texts["--source"], cv=texts["--cv"], vacancy=texts["--vacancy"])
        if bad:
            print(f"{len(bad)} quote problem(s) (CV quotes must be in the CV, vacancy quotes in the vacancy):")
            for label, text in bad:
                doc = "cv" if label in ("evidence", "talking point (CV)") else "vacancy"
                why = (" – blank" if blank(text) else
                       f" – too short to be evidence (under {MIN_LEN} characters)" if too_short(text, doc) else "")
                print(f'  - {label}: "{text}"{why}')
            if not force:
                return 1
    else:
        print("warning: no --cv / --vacancy given, quotes were NOT checked")
    with open(pos[1], "w", encoding="utf-8") as f:
        f.write(render(data, bad))
    print(f"wrote {pos[1]}")
    if pdf:
        print(f"wrote {pdf}" if to_pdf(pos[1], pdf) else "PDF skipped: Playwright is not installed; open the HTML and print to PDF")
    return 0


if __name__ == "__main__":
    utf8_output()
    sys.exit(main(sys.argv))
