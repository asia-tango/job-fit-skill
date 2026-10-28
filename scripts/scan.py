#!/usr/bin/env python3
"""Keyword scanner for vacancy text. Works for any role.

It only finds keywords and prints the lines they came from. It does not judge fit.

Built in: universal signals (location and legal, schedule, contract and money,
scope of responsibility, culture noise, years asked).
Per user: `stack` (skills and tools from the CV) and `avoid` (things to stay away from),
read from a JSON file made during Setup, e.g. keywords.local.json:

    {"stack": ["python", "kubernetes"], "avoid": ["gambling", "on-call"]}

Usage: python scan.py vacancy.txt [--keywords keywords.local.json]
       cat vacancy.txt | python scan.py -
"""
import json
import re
import sys

UNIVERSAL = {
    "location / legal": [
        r"\beu only\b", r"\beu-only\b", r"\bwithin the eu\b", r"\bunited kingdom\b", r"\buk[- ]based\b",
        r"\bright to work\b", r"\bwork authori[sz]ation\b", r"\bvisa\b", r"\boffice\b", r"\bhybrid\b",
        r"\bon[- ]site\b", r"\brelocat",
        r"\bвідрядженн", r"\bофіс\b", r"\bгібрид",
    ],
    "schedule": [
        r"\bshifts?\b", r"\bon[- ]call\b", r"\bovertime\b", r"\bweekends?\b", r"\bnight\b",
        r"\btime ?zone\b", r"\bhours per week\b",
        r"\bзмін[аи]\b", r"\bчергування\b", r"\bпонаднормов",
    ],
    "contract / format": [
        r"\bpart[- ]time\b", r"\bfull[- ]time\b", r"\bb2b\b", r"\bfop\b", r"\bcontractor\b",
        r"\bcontract\b", r"\bfreelance", r"\bstaff augmentation\b", r"\boutsourc",
        r"\bфоп\b", r"\bчастков", r"\bповна зайнятість\b",
    ],
    "money": [
        r"[$€£]\s?\d", r"\b\d[\d,.]*\s?(usd|eur|uah|gbp)\b", r"\bsalary\b", r"\bgross\b", r"\bnet\b",
        r"\bbonus\b", r"\bзарплат", r"\bставк", r"\bgross\b",
    ],
    "culture noise": [
        r"\bfast[- ]paced\b", r"\bwear many hats\b", r"\bwe are a family\b",
        r"\blike a family\b", r"\brockstar\b", r"\bninja\b", r"\bself[- ]starter\b",
    ],
}

SENIORITY = {
    "leadership scope": [
        r"\blead (complex )?(initiatives?|projects?|teams?)\b", r"\bdefine .*(strategy|roadmap|standards)\b",
        r"\binfluence .*(architecture|strategy|direction)\b", r"\bestablish .*standards\b",
        r"\bdirect reports?\b", r"\bmanage (a )?team\b", r"\bown (the )?(roadmap|budget|p&l)\b",
    ],
    "mentoring": [r"\bmentor", r"\bcoach"],
    "execution scope": [r"\b80% autonomy\b", r"\bfrom tickets?\b", r"\bunder the guidance\b", r"\bsupport the team\b"],
}


def term_pattern(term):
    """Case-insensitive pattern for a user keyword (works with dots, +, #).

    ASCII terms match as whole terms ("go" must not match "good").
    Terms with non-ASCII letters (Ukrainian) also match inflected endings
    ("гемблінг" matches "гемблінгу"), because those languages inflect.
    """
    term = term.strip()
    tail = r"\w*" if not term.isascii() else r"(?!\w)"
    return r"(?<!\w)" + re.escape(term) + tail


def load_keywords(path):
    with open(path, encoding="utf-8-sig") as f:  # a file saved by Windows Notepad starts with a BOM
        data = json.load(f)
    return {
        "stack": [t for t in data.get("stack", []) if t and t.strip()],
        "avoid": [t for t in data.get("avoid", []) if t and t.strip()],
    }


def years_required(text):
    """Return the biggest 'N+ years' number found, or None."""
    nums = [int(n) for n in re.findall(r"(\d{1,2})\s*\+?\s*(?:years|yrs|років|роки|рік)", text, re.I)]
    return max(nums) if nums else None


def scan(text, keywords=None):
    """Return {kind: {label: [line, ...]}} for every keyword hit.

    kinds: signal (universal), seniority, stack (from CV), avoid (user's list).
    """
    keywords = keywords or {"stack": [], "avoid": []}
    groups = [
        ("signal", UNIVERSAL),
        ("seniority", SENIORITY),
        ("stack", {t: [term_pattern(t)] for t in keywords.get("stack", [])}),
        ("avoid", {t: [term_pattern(t)] for t in keywords.get("avoid", [])}),
    ]
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    result = {}
    for kind, labelled in groups:
        for label, patterns in labelled.items():
            hits = [ln for ln in lines if any(re.search(p, ln, re.I) for p in patterns)]
            if hits:
                result.setdefault(kind, {})[label] = hits
    return result


def main(argv):
    args = argv[1:]
    keywords = None
    if "--keywords" in args:
        i = args.index("--keywords")
        keywords = load_keywords(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__)
        return 1
    text = sys.stdin.read() if args[0] == "-" else open(args[0], encoding="utf-8").read()
    found = scan(text, keywords)
    years = years_required(text)
    if years:
        print(f"[years] up to {years}+ years asked")
    if not found and not years:
        print("nothing found")
    for kind, groups in found.items():
        for label, hits in groups.items():
            print(f"[{kind}] {label}")
            for ln in hits[:3]:
                print(f"   - {ln[:140]}")
    return 0


if __name__ == "__main__":
    # Print UTF-8 even when the output is a pipe or a file (Windows would use the locale codepage).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv))
