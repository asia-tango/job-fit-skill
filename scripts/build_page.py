#!/usr/bin/env python3
"""Render any long Markdown text (profile, company research, interview prep) as the same styled HTML page.

Usage:
  python build_page.py input.md output.html [--title "Title"] [--cards] [--source doc.txt ...] [--force]
                       [--lang uk]
--lang    language of the page's fixed strings (theme switch, copy buttons): en (default) or uk
          (case-insensitive, uk-UA and ua work too).
--cards   menu layout (hero banner, sections as cards in two columns). The menu quotes nothing, so it
          needs no --source.
--source  a document the page's quotes must come from (CV, vacancy). Repeat it. Every quote (see
          verify_quotes.py) must be in one of them, or no page is written. A page with no quotes builds.
          Without any --source the quotes are NOT checked and a warning is printed.
--force   write the page even if some quotes were not found (exit 0). Unlike build_report.py, this
          script does not mark the missing quotes on the page yet.

Supported Markdown: # ## ### headings, paragraphs, - and 1. lists, > quotes, tables, ---, **bold**, *italic*,
`code`, [text](https://link), and copy buttons: a line `[[cmd: Label | text to copy]]`
(consecutive lines form one group). Everything is HTML-escaped first; only http(s) links are kept.
The first `# Heading` becomes the page title. The look matches build_report.py (light default, dark toggle, print).
Exit code: 0 ok, 1 quotes not found or a quote mark unpaired, 2 usage or input error
(a flag without a value, a missing, empty or non-UTF-8 file).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_report import CSS, esc, cmd_buttons, copy_js, labels, theme_button, warn_lang  # noqa: E402
from verify_quotes import (  # noqa: E402
    InputError, flag_value, missing_quotes, read_source, read_text, unpaired_marks, utf8_output)

EXTRA_CSS = """
.page p{margin:8px 0}.page blockquote{margin:10px 0;padding:6px 14px;border-left:4px solid var(--mint);color:var(--muted)}
.page code{background:var(--mint-bg);color:var(--mint-ink);border-radius:5px;padding:1px 6px;font-size:.9em}
.hero{background:linear-gradient(135deg,var(--mint-bg),var(--coral-bg));border-radius:16px;padding:22px 24px;margin-bottom:18px}
.hero h1{margin:0 0 8px;font-size:1.9rem}.hero p{margin:0;color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:18px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;gap:8px}
.tile:last-child:nth-child(odd){grid-column:1/-1}
.tile h2{border:0;padding:0;margin:0;font-size:1.05rem;display:flex;gap:10px;align-items:center}
.tile .n{display:inline-grid;place-items:center;flex:none;width:26px;height:26px;border-radius:50%;background:var(--coral);color:#fff;font-size:.85rem}
.tile p{margin:0;color:var(--muted);font-size:.92rem}.tile .cmds{margin:4px 0 0;gap:8px}.tile .cmd{padding:8px 12px;border-radius:10px}
.foot p{color:var(--muted);font-size:.9rem}
@media (max-width:760px){.tiles{grid-template-columns:1fr}}
.page hr{border:0;border-top:1px solid var(--line);margin:22px 0}.page ol{padding-left:1.4rem}
"""


CMD_RE = re.compile(r"\[\[cmd:\s*(.+?)\s*\|\s*(.+?)\s*\]\]$")


def inline(text):
    t = esc(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r'<a href="\2" rel="noopener">\1</a>', t)
    return t


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(md, L=None):
    lines = md.splitlines()
    out, title, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
        elif s.startswith("#"):
            level = min(len(s) - len(s.lstrip("#")), 3)
            text = s.lstrip("#").strip()
            if level == 1 and title is None:
                title = text
                out.append(f"<h1>{inline(text)}</h1>")
            else:
                out.append(f"<h{max(level, 2)}>{inline(text)}</h{max(level, 2)}>")
            i += 1
        elif CMD_RE.match(s):
            items = []
            while i < len(lines) and CMD_RE.match(lines[i].strip()):
                m = CMD_RE.match(lines[i].strip())
                items.append((m.group(1).strip(), m.group(2).strip()))
                i += 1
            out.append(cmd_buttons(items, L))
        elif re.fullmatch(r"-{3,}|\*{3,}", s):
            out.append("<hr>")
            i += 1
        elif s.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\|?\s*:?-{2,}[-:| ]*", lines[i + 1].strip()):
            head = split_row(s)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(h)}</th>" for h in head)
            body = "".join("<tr>" + "".join(f'<td data-l="{esc(head[k]) if k < len(head) else ""}">{inline(c)}</td>'
                                            for k, c in enumerate(r)) + "</tr>" for r in rows)
            out.append(f'<div class="card"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')
        elif re.match(r"[-*]\s+", s) or re.match(r"\d+[.)]\s+", s):
            ordered = bool(re.match(r"\d+[.)]\s+", s))
            items = []
            while i < len(lines) and (re.match(r"\s*[-*]\s+", lines[i]) or re.match(r"\s*\d+[.)]\s+", lines[i])):
                items.append(re.sub(r"^\s*([-*]|\d+[.)])\s+", "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<div class=\"card\"><{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}></div>")
        elif s.startswith(">"):
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(q))}</blockquote>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"\s*(#|[-*]\s|\d+[.)]\s|>|\||\[\[cmd:)", lines[i]):
                para.append(lines[i].strip())
                i += 1
            if not para:  # safety: never loop forever
                para, i = [s], i + 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return title, "\n".join(out)


def tiles(body):
    """Menu layout: a hero banner, then each `##` section as a card in a two-column grid."""
    head, *secs = re.split(r"\n(?=<h2>)", body)
    last = secs[-1] if secs else ""
    foot = ""
    if "<hr>" in last:
        secs[-1], foot = last.split("<hr>", 1)
    cards = []
    for sec in secs:
        sec = re.sub(r"<h2>(\d+)\.\s*", r'<h2><span class="n">\1</span>', sec, count=1)
        cards.append(f'<section class="tile">{sec}</section>')
    out = f'<header class="hero">{head}</header><div class="tiles">{"".join(cards)}</div>'
    return out + (f'<div class="foot">{foot}</div>' if foot.strip() else "")


def render(md, title=None, cards=False, lang="en"):
    L = labels(lang)
    t, body = convert(md, L)
    if cards:
        body = tiles(body)
    t = title or t or L["page_title"]
    return (f'<!doctype html><html lang="{L["html_lang"]}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="generator" content="job-fit">'
            f'<title>{esc(t)}</title><style>{CSS}{EXTRA_CSS}</style></head><body><main class="page">{body}</main>'
            f'{theme_button(L)}{copy_js(L)}</body></html>')


def main(argv):
    try:
        return build(argv[1:])
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def build(args):
    title, pos, i, cards = None, [], 0, False
    sources, force, lang = [], False, "en"
    while i < len(args):
        if args[i] == "--cards":
            cards = True
            i += 1
        elif args[i] == "--force":
            force = True
            i += 1
        elif args[i] == "--title":
            title = flag_value(args, i)
            i += 2
        elif args[i] == "--source":
            sources.append(flag_value(args, i))
            i += 2
        elif args[i] == "--lang":
            lang = flag_value(args, i)
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if len(pos) != 2:
        print(__doc__)
        return 2
    md = read_text(pos[0], "page text")
    texts = [read_source(s, "source") for s in sources]
    warn_lang(lang)
    if sources:
        missing = missing_quotes(md, texts)
        if missing:
            marks = set(unpaired_marks(md))
            print(f"{len(missing)} quote problem(s): not found in the sources, or an unpaired quote mark:")
            for q in missing:
                print(f"  - {q}" if q in marks else f'  - "{q}"')
            if not force:
                return 1
    elif not cards:
        print("warning: no --source given, quotes were NOT checked")
    with open(pos[1], "w", encoding="utf-8") as f:
        f.write(render(md, title, cards, lang))
    print(f"wrote {pos[1]}")
    return 0


if __name__ == "__main__":
    utf8_output()
    sys.exit(main(sys.argv))
