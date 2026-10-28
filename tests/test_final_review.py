"""Step 11: findings of the final reviews (free-text types, look-alike and unpaired quotes, short quotes,
same-file roles, nothing written before the page is rendered)."""
import json
import os
import subprocess
import sys
import unicodedata

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import build_prep as bpr  # noqa: E402
import build_report as br  # noqa: E402
import verify_quotes as vq  # noqa: E402
from evidence import strip_quote_marks  # noqa: E402

EX = os.path.join(ROOT, "examples", "frontend")
CV, VAC = os.path.join(EX, "cv.md"), os.path.join(EX, "vacancy.txt")
REPORT, PREP = os.path.join(EX, "report.json"), os.path.join(EX, "prep.json")
INVENTED = "Led a team of 40 engineers at Google"


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    r.out = r.stdout + r.stderr
    return r


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(tmp_path, d, name="a.json"):
    j = tmp_path / name
    j.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return j


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# --- 1. free-text fields must be strings ---------------------------------------------------

def test_report_free_text_must_be_strings(tmp_path):
    d = load(REPORT)
    v = d["vacancies"][0]
    v["verdict"]["text"] = {"claim": INVENTED}  # a dict would render as {'claim': '…'}, quote marks and all
    v["money"] = 5
    v["would_change"] = ["ok", 3]
    v["requirements"][0]["note"] = ["x"]
    v["questions"] = [{"question": {"q": "x"}, "why": 1}]
    d["next_steps"] = [{"label": 3, "command": "x"}]
    d["summary"] = {"rows": [{"vacancy": "A", "verdict": "skip", "reason": None, "check": 7}], "patterns": [None]}
    errs = " ".join(br.validate(d))
    for field in ("verdict.text", "`money`", "would_change 2", "requirement 1: `note`", "question 1: `question`",
                  "question 1: `why`", "next_steps 1: `label`", "summary row 1: `check`", "summary patterns 1"):
        assert field in errs and "must be text" in errs, field
    assert "`reason`" not in errs  # null means absent, like quote fields
    r = run("build_report.py", write(tmp_path, d), tmp_path / "r.html", "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 1 and not (tmp_path / "r.html").exists()


def test_prep_free_text_must_be_strings(tmp_path):
    d = load(PREP)
    d["process"] = 7
    d["questions"][0]["frame"] = {"say": INVENTED}
    d["before_call"] = ["ok", 3]
    d["ask_them"][0]["why"] = ["x"]
    errs = " ".join(bpr.validate(d))
    for field in ("`process`", "question 1: `frame`", "before_call 2", "ask_them 1: `why`"):
        assert field in errs and "must be text" in errs, field
    r = run("build_prep.py", write(tmp_path, d), tmp_path / "p.html", "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 1 and not (tmp_path / "p.html").exists()


def test_schemas_say_free_text_is_a_string():
    for name in ("report-schema.md", "prep-schema.md"):
        assert "free text is a string" in read("references", name), name


# --- 2. look-alike quote marks are stripped from free text ---------------------------------

def test_every_initial_and_final_quote_mark_is_stripped():
    marks = [chr(c) for c in range(0x110000) if unicodedata.category(chr(c)) in ("Pi", "Pf")]
    marks += list("‚„＂＇″〝〞〟‹›")
    for m in marks:
        assert strip_quote_marks(f" {m}Нова Пошта{m} ") == " Нова Пошта ", hex(ord(m))
    for kept in ("з'явилась", "зʼявилась", "don't", "it’s", "the 1990's"):
        assert strip_quote_marks(kept) == kept


def test_look_alike_marks_do_not_reach_the_page():
    d = load(REPORT)
    d["vacancies"][0]["money"] = "‹Нова Пошта› ‚pays‘ ＂well＂ 〝often〞 ″now″"
    page = br.render(d)
    assert "Нова Пошта pays well often now" in page
    for m in "‹›‚‘＂〝〞″":
        assert m not in page, m  # none of these appears anywhere else on the page (labels, CSS, JS)
    assert "‹" in read("references", "report-schema.md") and "Pi" in read("references", "report-schema.md")


# --- 3. the free-text check sees short quotes too -------------------------------------------

def test_short_quotes_are_checked_in_free_text(tmp_path):
    assert vq.missing_quotes('Stack: "Rust" and "Angular"', [read("examples", "frontend", "cv.md")]) == ["Rust"]
    assert vq.missing_quotes('Stack: "" and "Angular"', ["Angular"]) == []  # an empty pair has nothing to check
    md = tmp_path / "p.md"
    md.write_text('# Prep\n\n- CV: "Rust"\n', encoding="utf-8")
    r = run("build_page.py", md, tmp_path / "p.html", "--source", CV, "--source", VAC)
    assert r.returncode == 1 and not (tmp_path / "p.html").exists()
    ans = tmp_path / "a.md"
    ans.write_text('Tools: "Angular" and "RxJS"', encoding="utf-8")
    r = run("verify_quotes.py", ans, CV)
    assert r.returncode == 0 and "2 quotes" in r.out  # checked, not "nothing was checked"


def test_docs_say_short_quotes_are_checked_in_the_fallback():
    for name in ("README.md", "SKILL.md"):
        assert "whatever its length" in read(name), name


# --- 4. the same file or text in both roles is refused ---------------------------------------

def test_same_file_or_text_in_both_roles_is_refused(tmp_path):
    copy_ = tmp_path / "vac-copy.txt"
    copy_.write_text(read("examples", "frontend", "vacancy.txt"), encoding="utf-8")
    out = tmp_path / "o.html"
    for script, data in (("build_report.py", REPORT), ("build_prep.py", PREP)):
        for flags in (["--cv", VAC, "--vacancy", VAC], ["--cv", copy_, "--vacancy", VAC],
                      ["--cv", CV, "--cv", VAC, "--vacancy", VAC]):
            r = run(script, data, out, *flags)
            assert r.returncode == 2 and len(r.out.strip().splitlines()) == 1, (script, flags, r.out)
            assert "both the CV and the vacancy" in r.out
            assert not out.exists()


# --- 5. a closing quote mark without an opener is unpaired -----------------------------------

def test_closing_mark_without_opener_is_unpaired(tmp_path):
    src = [read("examples", "frontend", "cv.md")]
    assert "unpaired quote mark at line 1" in vq.missing_quotes(f"Evidence: ”{INVENTED}”", src)
    assert "unpaired quote mark at line 2" in vq.missing_quotes(f"x\nEvidence: »{INVENTED}«", src)
    assert vq.missing_quotes('"Optimized AG Grid for 10,000+ rows”', src) == []  # the mixed pair stays allowed
    ans = tmp_path / "a.md"
    ans.write_text(f"Evidence: ”{INVENTED}”", encoding="utf-8")
    r = run("verify_quotes.py", ans, CV)
    assert r.returncode == 1 and "unpaired quote mark at line 1" in r.out


# --- render before writing ----------------------------------------------------------------

def test_nothing_is_written_if_rendering_fails(tmp_path):
    out = tmp_path / "r.html"
    def boom(data, bad=()):
        raise RuntimeError("render failed")
    for validate, missing in ((br.validate, br.missing_quotes), (bpr.validate, bpr.missing_quotes)):
        data = REPORT if validate is br.validate else PREP
        with pytest.raises(RuntimeError):
            br.build_cli([data, str(out), "--cv", CV, "--vacancy", VAC], usage="", kind="JSON", validate=validate,
                         missing=missing, render=boom, cv_labels=(), allow_source=False)
        assert not out.exists()


# --- docs ---------------------------------------------------------------------------------

def test_skill_inputs_cover_batches_swaps_and_what_counts_as_a_vacancy():
    skill = read("SKILL.md")
    inputs = skill[skill.index("## Inputs"):skill.index("## Profile source")]
    assert "several vacancies" in inputs and "split" in inputs
    assert "swapped" in inputs
    assert "neither requirements nor duties" in inputs
    assert "`build_prep.py` has no `--source` at all" in skill


def test_readme_names_the_single_quote_gap_plainly():
    limits = read("README.md").split("## Known limitations")[1].split("\n## ")[0]
    assert "'…' and ‘…’ single quotes are not checked" in limits and "apostrophe" in limits


def test_review_round_is_not_presented_as_a_run():
    for text in (read("README.md"), read("tests", "MANUAL_EVAL.md")):
        assert "| 2026-10-28 |" not in text
        assert "not a run" in text
        for commit in ("234756b", "f929c8a", "6f8b9e5", "8098642", "a11f347"):
            assert commit in text, commit


def test_gitignore_covers_more_cv_formats():
    lines = [ln.strip() for ln in read(".gitignore").splitlines()]
    for pattern in ("резюме.*", "*.doc", "*.odt", "*.rtf", "profile*.html"):
        assert pattern in lines, pattern
    assert lines[-1] == "!examples/**"
    names = ["резюме.pdf", "Резюме.docx", "old.doc", "cv-2026.odt", "letter.rtf", "profile-page.html"]
    try:
        r = subprocess.run(["git", "-C", ROOT, "-c", "core.quotepath=off", "check-ignore", "--no-index", *names],
                           capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if r.returncode not in (0, 1):
        pytest.skip(f"not a git checkout: {r.stderr.strip()}")
    ignored = set(r.stdout.splitlines())
    assert ignored >= {"резюме.pdf", "old.doc", "cv-2026.odt", "letter.rtf", "profile-page.html"}, ignored
