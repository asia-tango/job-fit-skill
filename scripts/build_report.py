#!/usr/bin/env python3
"""Render a job-fit analysis (JSON) as one self-contained, styled HTML page.

The model writes the analysis as compact JSON (see references/report-schema.md);
this script turns it into a readable page with status marks, colors, a light page with a dark toggle
and print styles. Fast, and the same look every time. Everything is escaped.

Usage:
  python build_report.py analysis.json report.html --source cv.txt --source vacancy.txt
  python build_report.py analysis.json report.html --source cv.txt --pdf report.pdf

--source   a document the quotes must come from (CV, vacancy). Repeat it. Without any
           --source the quotes are NOT checked and a warning is printed.
--pdf      also write a PDF (needs Playwright with Chromium). Otherwise open the HTML
           and print it to PDF; the print styles are included.
--force    write the page even if some quotes were not found (they are marked on the page).
Exit code: 0 ok, 1 invalid input or quotes not found, 2 usage.
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_quotes import normalize  # noqa: E402

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

THEME_BUTTON = (
    '<div id="tt" role="group" aria-label="Theme">'
    '<button type="button" data-t="light" class="on">Light</button>'
    '<button type="button" data-t="dark">Dark</button></div>'
    "<script>document.getElementById('tt').addEventListener('click',function(e){"
    "var b=e.target.closest('button');if(!b)return;"
    "document.documentElement.setAttribute('data-jf',b.dataset.t);"
    "this.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)})});</script>"
)

COPY_JS = (
    "<script>document.addEventListener('click',function(e){var b=e.target.closest('[data-cmd]');if(!b)return;"
    "var t=b.getAttribute('data-cmd'),s=b.querySelector('.cp');"
    "function done(){b.classList.add('ok');if(s)s.textContent='Copied';"
    "setTimeout(function(){b.classList.remove('ok');if(s)s.textContent='Copy'},1500)}"
    "function fb(){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();"
    "try{document.execCommand('copy')}catch(x){}a.remove();done()}"
    "if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fb)}else{fb()}"
    "});</script>"
)


def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def cmd_buttons(items):
    """Copy-to-clipboard buttons: items = [(label, command)]. The page never sends anything itself."""
    return '<div class="cmds">' + "".join(
        f'<button type="button" class="cmd" data-cmd="{esc(c)}"><span class="cl">{esc(l)}</span>'
        f'<code>{esc(c)}</code><span class="cp">Copy</span></button>' for l, c in items) + "</div>"


def validate(data):
    """Return a list of problems with the analysis JSON. Empty list = valid."""
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
            if not r.get("requirement"):
                errs.append(f"{p}, requirement {j}: empty requirement")
            if r.get("status") == "match" and not r.get("evidence"):
                errs.append(f"{p}, requirement {j}: a match needs evidence")
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
    """Yield (label, text) for every field that must be copied verbatim from a source."""
    for r in v.get("requirements", []):
        yield "requirement", r.get("requirement")
        if not r.get("confirmed"):
            yield "evidence", r.get("evidence")
    for f in v.get("red_flags", []):
        yield "red flag quote", f.get("quote")
    for t in v.get("talking_points", []):
        if not t.get("confirmed"):
            yield "talking point (CV)", t.get("cv")
        yield "talking point (vacancy)", t.get("vacancy")


def missing_quotes(data, sources):
    """Return [(label, text)] for quoted fields not found in any source."""
    haystack = normalize("\n".join(sources))
    out = []
    for v in data.get("vacancies", []):
        for label, text in quote_fields(v):
            if text and normalize(text) not in haystack:
                out.append((label, text))
    return out


def badge(status):
    mark, label = STATUS[status]
    return f'<span class="badge {status}">{mark} {label}</span>'


def li(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""


def growth_item(g):
    if isinstance(g, dict):
        return esc(g.get("text")) + f'<span class="tag">{esc(g.get("tag"))}</span>'
    return esc(g)


def render_vacancy(v, idx, bad, single=False):
    o = []
    vm, vl = VERDICT[v["verdict"]["mark"]]
    head = "" if single else f'<h2>{esc(v["title"])}</h2>'
    o.append(f'<section id="v{idx}">{head}')
    o.append(f'<div class="card verdict {esc(v["verdict"]["mark"])}"><p class="vlabel">{vm} {vl}</p>'
             f'<p style="margin:0">{esc(v["verdict"]["text"])}</p></div>')
    if v.get("would_change"):
        o.append('<h3>What would change the verdict</h3>' + li([esc(x) for x in v["would_change"]]))
    reqs = v.get("requirements", [])
    if reqs:
        o.append('<h2>Requirements vs CV</h2><div class="card"><table><thead><tr><th>Requirement</th>'
                 '<th>Evidence</th><th>Status</th></tr></thead><tbody>')
        for r in reqs:
            req_cls = ' class="missing"' if ("requirement", r.get("requirement")) in bad else ""
            ev = r.get("evidence")
            ev_cls = ' class="missing"' if ("evidence", ev) in bad else ""
            ev_html = f'<q class="ev"{ev_cls}>{esc(ev)}</q>' if ev and not r.get("confirmed") else (
                esc(ev) if ev else '<span class="ev">—</span>')
            note = f'<span class="note">{esc(r["note"])}</span>' if r.get("note") else ""
            conf = '<span class="tag">confirmed by you</span>' if r.get("confirmed") else ""
            o.append(f'<tr><td data-l="Requirement"><q{req_cls}>{esc(r["requirement"])}</q></td>'
                     f'<td data-l="Evidence">{ev_html}</td>'
                     f'<td data-l="Status">{badge(r["status"])}{conf}{note}</td></tr>')
        o.append('</tbody></table></div>')
    if v.get("cv_fixes"):
        o.append('<h2>Fix in the CV</h2><div class="card">' + li(
            [f'<span class="kind">{esc(f.get("kind"))}.</span> {esc(f.get("text"))}' for f in v["cv_fixes"]]) + '</div>')
    g = v.get("growth")
    if g:
        o.append('<h2>Growth</h2><div class="cols">')
        for key, title in (("new", "New for you"), ("same", "Same as now"), ("unknown", "Can’t tell")):
            o.append(f'<div class="card"><h3 style="margin-top:0">{title}</h3>'
                     + li([growth_item(x) for x in g.get(key, [])]) + '</div>')
        o.append('</div>')
    if v.get("red_flags"):
        o.append('<h2>Red flags</h2>')
        for f in v["red_flags"]:
            cls = ' class="missing"' if ("red flag quote", f.get("quote")) in bad else ""
            o.append(f'<div class="card flag"><q{cls}>{esc(f.get("quote"))}</q>'
                     f'<span class="note">{esc(f.get("text"))}</span></div>')
    if v.get("money"):
        o.append(f'<h2>Money and format</h2><div class="card">{esc(v["money"])}</div>')
    if v.get("questions"):
        o.append('<h2>Questions to ask</h2><div class="card">')
        groups = {}
        for q in v["questions"]:
            groups.setdefault(q.get("group", "General"), []).append(q)
        for name, qs in groups.items():
            o.append(f'<h3 style="margin-top:0">{esc(name)}</h3>' + li(
                [esc(q["question"]) + (f'<span class="note">{esc(q["why"])}</span>' if q.get("why") else "")
                 for q in qs]))
        o.append('</div>')
    if v.get("talking_points"):
        o.append('<h2>Talking points for the application</h2><div class="card"><ol style="padding-left:1.2rem;margin:0">')
        for t in v["talking_points"]:
            src = ""
            if t.get("cv"):
                src += f'CV: <q>{esc(t["cv"])}</q>' if not t.get("confirmed") else f'CV: {esc(t["cv"])} <span class="tag">confirmed by you</span>'
            if t.get("vacancy"):
                src += f'<br>Vacancy: <q>{esc(t["vacancy"])}</q>'
            o.append(f'<li style="margin:10px 0"><strong>{esc(t["point"])}</strong>'
                     f'<span class="note">{src}</span></li>')
        o.append('</ol></div>')
    if v.get("letter_draft"):
        o.append('<h2>Application draft</h2><div class="card">'
                 '<p class="note" style="margin-top:0">Draft – check every claim before sending.</p>'
                 f'<div style="white-space:pre-wrap;line-height:1.55">{esc(v["letter_draft"])}</div>'
                 + cmd_buttons([("Copy the draft", v["letter_draft"])]) + '</div>')
    o.append('</section>')
    return "\n".join(o)


def render_summary(summary, vacs):
    o = ['<h2>Summary</h2><div class="card"><table><thead><tr><th>#</th><th>Vacancy</th><th>Verdict</th>'
         '<th>Main reason</th><th>Check first</th></tr></thead><tbody>']
    for i, r in enumerate(summary.get("rows", []), 1):
        mk, lb = VERDICT[r["verdict"]]
        o.append(f'<tr><td data-l="#">{i}</td><td data-l="Vacancy"><a href="#v{i}">{esc(r.get("vacancy"))}</a></td>'
                 f'<td data-l="Verdict">{mk} {lb}</td><td data-l="Main reason">{esc(r.get("reason"))}</td>'
                 f'<td data-l="Check first">{esc(r.get("check"))}</td></tr>')
    o.append('</tbody></table></div>')
    if summary.get("patterns"):
        o.append('<h3>Patterns</h3>' + li([esc(x) for x in summary["patterns"]]))
    if summary.get("next"):
        o.append('<h3>Next</h3>' + li([esc(x) for x in summary["next"]]))
    return "\n".join(o)


def render_decide(decide):
    o = ['<h2>Questions that decide this</h2>']
    for d in decide:
        opts = "".join(f'<span class="opt">{esc(x)}</span>' for x in d.get("options", []))
        o.append(f'<div class="card"><strong>{esc(d.get("question"))}</strong>'
                 f'<div class="opts">{opts}</div>'
                 + (f'<span class="note">Affects: {esc(d["affects"])}</span>' if d.get("affects") else "") + '</div>')
    return "\n".join(o)


def render(data, bad=()):
    vacs = data["vacancies"]
    title = data.get("title") or (vacs[0]["title"] if len(vacs) == 1 else "Job fit report")
    parts = [f'<h1>{esc(title)}</h1>', f'<p class="src">Profile: {esc(data.get("profile_source", "not stated"))}</p>']
    if data.get("summary"):
        parts.append(render_summary(data["summary"], vacs))
    for i, v in enumerate(vacs, 1):
        parts.append(render_vacancy(v, i, set(bad), single=len(vacs) == 1 and not data.get("title")))
    if data.get("decide"):
        parts.append(render_decide(data["decide"]))
    if data.get("next_steps"):
        parts.append("<h2>What next</h2>" + cmd_buttons([(n["label"], n["command"]) for n in data["next_steps"]]))
    body = "\n".join(parts)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="generator" content="job-fit">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}</main>'
            f'{THEME_BUTTON}{COPY_JS}</body></html>')


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
    args = argv[1:]
    sources, pdf, force = [], None, False
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--source":
            sources.append(args[i + 1]); i += 2
        elif a == "--pdf":
            pdf = args[i + 1]; i += 2
        elif a == "--force":
            force = True; i += 1
        else:
            pos.append(a); i += 1
    if len(pos) != 2:
        print(__doc__)
        return 2
    with open(pos[0], encoding="utf-8") as f:
        data = json.load(f)
    errs = validate(data)
    if errs:
        print("INVALID:\n  - " + "\n  - ".join(errs))
        return 1
    bad = []
    if sources:
        texts = []
        for s in sources:
            with open(s, encoding="utf-8") as f:
                texts.append(f.read())
        bad = missing_quotes(data, texts)
        if bad:
            print(f"{len(bad)} quote(s) not found in the sources:")
            for label, text in bad:
                print(f'  - {label}: "{text}"')
            if not force:
                return 1
    else:
        print("warning: no --source given, quotes were NOT checked")
    with open(pos[1], "w", encoding="utf-8") as f:
        f.write(render(data, bad))
    print(f"wrote {pos[1]}")
    if pdf:
        print(f"wrote {pdf}" if to_pdf(pos[1], pdf) else "PDF skipped: Playwright is not installed; open the HTML and print to PDF")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
