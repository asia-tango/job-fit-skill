#!/usr/bin/env python3
"""Check that every quoted line in an answer exists in the source documents.

The skill quotes the vacancy and the CV as evidence. A quote that is not in
the sources is an invented claim, so the answer must not be shown.

Quotes are "…", “…”, «…» and „…“. A quote may be wrapped over several lines, but a blank line
always ends it.

Usage: python verify_quotes.py answer.md source1.txt [source2.txt ...]
Exit code 0 = all quotes found, 1 = at least one missing, 2 = usage,
3 = no quotes in the answer (nothing was checked, so it is not OK).
"""
import re
import sys

MIN_LEN = 12  # shorter quoted strings (single words, tool names) are not evidence

_Q = '"“”«»„'
# One or more lines of non-quote text; a line break may not start a blank line.
_BODY = rf"[^{_Q}\n]+(?:\n(?![ \t\r]*(?:\n|$))[^{_Q}\n]+)*"
QUOTE_RE = re.compile(rf'["“]({_BODY})["”]|«({_BODY})»|„({_BODY})[“”]')


def normalize(text):
    """Lowercase, drop list bullets, unify dashes, apostrophes and quotes, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub("[ʼ’‘]", "'", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_quotes(answer):
    quotes = ("".join(m.groups(default="")).strip() for m in QUOTE_RE.finditer(answer))
    return [q for q in quotes if len(q) >= MIN_LEN]


def missing_quotes(answer, sources):
    """Return the quotes from `answer` that do not appear in any of `sources`."""
    haystack = normalize("\n".join(sources))
    return [q for q in extract_quotes(answer) if normalize(q) not in haystack]


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        answer = f.read()
    sources = []
    for path in argv[2:]:
        with open(path, encoding="utf-8") as f:
            sources.append(f.read())
    quotes = extract_quotes(answer)
    if not quotes:
        print("no quotes found – nothing was checked")
        return 3
    missing = missing_quotes(answer, sources)
    if missing:
        print(f"FAIL: {len(missing)} of {len(quotes)} quotes not found in the sources:")
        for q in missing:
            print(f'  - "{q}"')
        return 1
    print(f"OK: all {len(quotes)} quotes found in the sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
