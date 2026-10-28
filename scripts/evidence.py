"""The one evidence checker: is a quote really in its own document?

Used by build_report.py and, through verify_quotes.py, by build_page.py. A quote counts as found
only if it appears, after `normalize`, in a single source file (never across two files) and does
not start or end in the middle of a word there.
"""
import re
import unicodedata

MIN_LEN = 12  # shorter quoted strings (single words, tool names) are not evidence


def normalize(text):
    """Lowercase, drop list bullets, unify dashes, apostrophes and quotes, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub("[ʼ’‘]", "'", text)
    return re.sub(r"\s+", " ", text).strip()


def _in_word(text, k):
    """Is text[k] part of a word: a letter or digit, or an apostrophe between two of them (з'явилась)?"""
    if not 0 <= k < len(text):
        return False
    if text[k].isalnum():
        return True
    return text[k] == "'" and 0 < k < len(text) - 1 and text[k - 1].isalnum() and text[k + 1].isalnum()


def occurs(quote, text):
    """`quote` and `text` are normalized. True if the quote is in the text at word boundaries.

    The boundary is checked only on a side where the quote itself begins or ends with a letter or
    digit, so `C++`, `(SSR)` and `10,000+ rows` still match.
    """
    if not quote:
        return False
    start = text.find(quote)
    while start != -1:
        end = start + len(quote)
        cut_left = quote[0].isalnum() and _in_word(text, start - 1)
        cut_right = quote[-1].isalnum() and _in_word(text, end)
        if not (cut_left or cut_right):
            return True
        start = text.find(quote, start + 1)
    return False


def found(quote, texts):
    """True if `quote` is in one of `texts` (raw source texts), each file checked on its own."""
    q = normalize(quote)
    return any(occurs(q, normalize(t)) for t in texts)


# Quote marks that are not in Unicode's initial/final quote categories (Pi, Pf): low, fullwidth, prime, CJK.
EXTRA_QUOTE_MARKS = set('"‚„＂＇″〝〞〟‹›')
APOSTROPHES = "'ʼ’"


def is_quote_mark(c):
    return c in EXTRA_QUOTE_MARKS or unicodedata.category(c) in ("Pi", "Pf")


def strip_quote_marks(text):
    """Free text without quote marks, so it never looks like a citation (only checked fields may).

    Removes every initial or final quote mark (Unicode Pi, Pf: “ ” « » ‘ ‹ › ‛ ‟ …) and the look-alikes
    in EXTRA_QUOTE_MARKS. An apostrophe between two letters or digits stays (з'явилась, зʼявилась, don't,
    it’s, 1990's); elsewhere it is a single quote mark and goes too. Anything that is not a string is
    returned unchanged.
    """
    if not isinstance(text, str):
        return text
    out = []
    for i, c in enumerate(text):
        if c in APOSTROPHES:
            if 0 < i < len(text) - 1 and text[i - 1].isalnum() and text[i + 1].isalnum():
                out.append(c)
            continue
        if is_quote_mark(c):
            continue
        out.append(c)
    return "".join(out)


def not_text(value):
    """True for a free-text field that is present (not null) but not a string."""
    return value is not None and not isinstance(value, str)


def blank(value):
    """True for a quote field that is present (not null) but has no text: "", "   ", or not a string."""
    return value is not None and (not isinstance(value, str) or not value.strip())


def too_short(text, doc):
    """A CV quote shorter than MIN_LEN ("the", "Angular") proves nothing, even if it is in the CV."""
    return doc == "cv" and len(normalize(text)) < MIN_LEN


def confirmed_error(item):
    """A message if `confirmed` is present but not a real boolean ("false" is truthy), else None."""
    value = item.get("confirmed")
    if value is not None and not isinstance(value, bool):
        return f"`confirmed` must be true or false, not {value!r}"
    return None


def check_fields(fields, cv, vacancy):
    """Return [(label, text)] for quote fields that fail: blank, too short (CV side), or not found.

    `fields` is [(label, text, doc)] with doc "cv" or "vacancy"; a text of None is an absent field.
    `cv` and `vacancy` are lists of source texts, each checked on its own. A role given as None or
    an empty list is not checked for presence; CV quotes are still checked for length.
    """
    sources = {"cv": [normalize(t) for t in cv or []], "vacancy": [normalize(t) for t in vacancy or []]}
    out = []
    for label, text, doc in fields:
        if text is None:
            continue
        if blank(text) or too_short(text, doc):
            out.append((label, text))
            continue
        q = normalize(text)
        if sources[doc] and not any(occurs(q, s) for s in sources[doc]):
            out.append((label, text))
    return out
