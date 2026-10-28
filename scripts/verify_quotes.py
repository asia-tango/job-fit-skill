#!/usr/bin/env python3
"""Check that every quoted line in an answer exists in the source documents.

The skill quotes the vacancy and the CV as evidence. A quote that is not in
the sources is an invented claim, so the answer must not be shown.

Quotes are "…", “…”, «…» and „…“ (also the mixed "…”). A quote may contain a quote of another
kind (« "…" » and the reverse) and may be wrapped over several lines, but a blank line always ends
it. An opening quote mark with no closing one fails the check (`unpaired quote mark at line N`):
it would shift the pairing and hide the quotes after it.

Usage: python verify_quotes.py answer.md source1.txt [source2.txt ...]
Exit code 0 = all quotes found, 1 = a quote missing or a quote mark unpaired,
2 = usage or input error (missing file, not UTF-8),
3 = no quotes in the answer (nothing was checked, so it is not OK).
"""
import json
import re
import sys

MIN_LEN = 12  # shorter quoted strings (single words, tool names) are not evidence

# opening mark -> the marks that close it
PAIRS = {'"': '"”', "“": "”", "«": "»", "„": "“”"}
PARAGRAPH_BREAK = re.compile(r"\n[ \t\r]*\n")


class InputError(Exception):
    """A problem with the command line or an input file; the CLIs print it as one line and exit 2."""


def read_text(path, what="file"):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except FileNotFoundError:
        raise InputError(f"{what} not found: {path}") from None
    except UnicodeDecodeError:
        raise InputError(f"{what} is not UTF-8 text: {path} (save it as UTF-8)") from None
    except OSError as e:
        raise InputError(f"cannot read {what}: {path} ({e.strerror})") from None


def read_json(path, what="JSON file"):
    try:
        return json.loads(read_text(path, what))
    except json.JSONDecodeError as e:
        raise InputError(f"{what} is not valid JSON: {path}, line {e.lineno} column {e.colno}: {e.msg}") from None


def flag_value(args, i):
    """The value after the flag at args[i]."""
    if i + 1 >= len(args):
        raise InputError(f"{args[i]} needs a value")
    return args[i + 1]


def utf8_output():
    """Print UTF-8 even when the output is a pipe or a file (Windows would use the locale codepage)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def normalize(text):
    """Lowercase, drop list bullets, unify dashes, apostrophes and quotes, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub("[ʼ’‘]", "'", text)
    return re.sub(r"\s+", " ", text).strip()


def _scan(text, offset, quotes, unpaired):
    """Collect (quote, start) and the start of every unpaired opening mark in `text` (no blank lines)."""
    i = 0
    while i < len(text):
        closers = PAIRS.get(text[i])
        if closers is None:
            i += 1
            continue
        end = next((j for j in range(i + 1, len(text)) if text[j] in closers), None)
        if end is None:
            unpaired.append(offset + i)
            i += 1
            continue
        quotes.append((text[i + 1:end], offset + i))
        _scan(text[i + 1:end], offset + i + 1, quotes, unpaired)  # a quote of another kind inside
        i = end + 1


def _find(answer):
    quotes, unpaired, start = [], [], 0
    for m in list(PARAGRAPH_BREAK.finditer(answer)) + [None]:
        end = m.start() if m else len(answer)
        _scan(answer[start:end], start, quotes, unpaired)
        if m:
            start = m.end()
    return quotes, unpaired


def extract_quotes(answer):
    quotes, _ = _find(answer)
    return [q.strip() for q, _ in sorted(quotes, key=lambda x: x[1]) if len(q.strip()) >= MIN_LEN]


def unpaired_marks(answer):
    """One message per opening quote mark that has no closing mark before the next blank line."""
    _, unpaired = _find(answer)
    return [f"unpaired quote mark at line {answer.count(chr(10), 0, pos) + 1}" for pos in sorted(unpaired)]


def missing_quotes(answer, sources):
    """Return the problems in `answer`: unpaired quote marks first, then quotes not in any of `sources`."""
    haystack = normalize("\n".join(sources))
    return unpaired_marks(answer) + [q for q in extract_quotes(answer) if normalize(q) not in haystack]


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    try:
        answer = read_text(argv[1], "answer")
        sources = [read_text(p, "source") for p in argv[2:]]
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    quotes = extract_quotes(answer)
    unpaired = unpaired_marks(answer)
    missing = missing_quotes(answer, sources)[len(unpaired):]
    if unpaired or missing:
        parts = ([f"{len(missing)} of {len(quotes)} quotes not found in the sources"] if missing else []) + (
            [f"{len(unpaired)} unpaired quote mark(s)"] if unpaired else [])
        print(f"FAIL: {', '.join(parts)}:")
        for u in unpaired:
            print(f"  - {u}")
        for q in missing:
            print(f'  - "{q}"')
        return 1
    if not quotes:
        print("no quotes found – nothing was checked")
        return 3
    print(f"OK: all {len(quotes)} quotes found in the sources.")
    return 0


if __name__ == "__main__":
    utf8_output()
    sys.exit(main(sys.argv))
