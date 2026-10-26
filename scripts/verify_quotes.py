#!/usr/bin/env python3
"""Check that every quoted line in an answer exists in the source documents.

The skill quotes the vacancy and the CV as evidence. A quote that is not in
the sources is an invented claim, so the answer must not be shown.

Usage: python verify_quotes.py answer.md source1.txt [source2.txt ...]
Exit code 0 = all quotes found, 1 = at least one missing.
"""
import re
import sys

MIN_LEN = 12  # shorter quoted strings (single words, tool names) are not evidence

QUOTE_RE = re.compile(r'["“]([^"“”\n]+)["”]')


def normalize(text):
    """Lowercase, drop list bullets, unify dashes and quotes, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def extract_quotes(answer):
    return [q.strip() for q in QUOTE_RE.findall(answer) if len(q.strip()) >= MIN_LEN]


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
