"""Regression tests for the bypasses and crashes found in the review round (2026-10-28).

Each test reproduces one way an invented quote got past the checks, or one input that
crashed a script with a traceback instead of a one-line error.
"""
import copy
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import build_page as bp  # noqa: E402
import build_report as br  # noqa: E402
from verify_quotes import missing_quotes  # noqa: E402

EX = os.path.join(ROOT, "examples", "frontend")
CV = os.path.join(EX, "cv.md")
VAC = os.path.join(EX, "vacancy.txt")
SRC = ["Led a small team. Redesigned the RBAC architecture into a scalable reactive model."]
INVENTED = "Led a team of 40 engineers at Google"


def run(script, *args):
    """Run a CLI the way tests and Claude do: output to a pipe, no UTF-8 override from the caller."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                       capture_output=True, env=env)
    r.out = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r


def report(mutate=None):
    with open(os.path.join(EX, "report.json"), encoding="utf-8") as f:
        d = json.load(f)
    if mutate:
        mutate(d["vacancies"][0])
    return d


def write_json(tmp_path, d, name="a.json", encoding="utf-8"):
    j = tmp_path / name
    j.write_text(json.dumps(d, ensure_ascii=False), encoding=encoding)
    return j


def texts():
    with open(CV, encoding="utf-8") as f, open(VAC, encoding="utf-8") as g:
        return f.read(), g.read()


# --- verify_quotes.py: nested and unpaired quote marks --------------------------------

def test_nested_outer_guillemet_quote_is_checked():
    answer = f'«{INVENTED} as "tech lead" there»'
    assert any(INVENTED in m for m in missing_quotes(answer, SRC))


def test_nested_outer_straight_quote_is_checked():
    answer = f'"{INVENTED} as «tech lead» there"'
    assert any(INVENTED in m for m in missing_quotes(answer, SRC))


def test_real_nested_quote_passes():
    src = ["Led the «Atlas» migration for the payments team."]
    assert missing_quotes('Evidence: "Led the «Atlas» migration for the payments team"', src) == []


def test_stray_quote_mark_fails_closed():
    # 27" opens a pair with the next mark, so the invented quote would be outside every pair.
    missing = missing_quotes(f'Monitor 27" wide. Evidence: "{INVENTED}"', SRC)
    assert "unpaired quote mark at line 1" in missing


def test_blank_line_inside_quote_fails_closed():
    answer = f'Evidence: "{INVENTED}\n\nin Zurich" and "Redesigned the RBAC architecture"'
    assert any(m.startswith("unpaired quote mark at line") for m in missing_quotes(answer, SRC))


def test_mixed_straight_curly_pair_stays_allowed():
    assert missing_quotes('"Redesigned the RBAC architecture into a scalable reactive model”', SRC) == []


def test_answer_with_only_an_unpaired_mark_exits_1(tmp_path):
    ans, src = tmp_path / "a.md", tmp_path / "s.txt"
    ans.write_text(f'Great fit.\nEvidence: "{INVENTED}\n', encoding="utf-8")
    src.write_text(SRC[0], encoding="utf-8")
    r = run("verify_quotes.py", ans, src)
    assert r.returncode == 1 and "unpaired quote mark at line 2" in r.out


def test_unpaired_mark_blocks_the_page(tmp_path):
    md = tmp_path / "p.md"
    md.write_text(f'# Prep\n\n- CV: "{INVENTED}\n', encoding="utf-8")
    r = run("build_page.py", md, tmp_path / "p.html", "--source", CV, "--source", VAC)
    assert r.returncode == 1 and "unpaired quote mark at line 3" in r.out
    assert not (tmp_path / "p.html").exists()


# --- build_report.py: `confirmed` and blank quote fields ------------------------------

def test_confirmed_must_be_a_boolean():
    def m(v):
        v["requirements"][0]["confirmed"] = "false"
        v["talking_points"][0]["confirmed"] = "yes"
    errs = " ".join(br.validate(report(m)))
    assert "requirement 1: `confirmed`" in errs and "talking point 1: `confirmed`" in errs


def test_confirmed_string_does_not_skip_the_check():
    def m(v):
        r = v["requirements"][0]
        r["evidence"], r["status"], r["confirmed"] = INVENTED, "match", "false"
    d = report(m)
    cv, vac = texts()
    assert ("evidence", INVENTED) in br.missing_quotes(d, cv=[cv], vacancy=[vac])
    assert "confirmed by you" not in br.render(d)


def test_confirmed_string_is_rejected_by_the_cli(tmp_path):
    def m(v):
        r = v["requirements"][0]
        r["evidence"], r["status"], r["confirmed"] = INVENTED, "match", "false"
    r = run("build_report.py", write_json(tmp_path, report(m)), tmp_path / "r.html", "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 1 and not (tmp_path / "r.html").exists()


def test_confirmed_match_needs_real_evidence():
    def m(v):
        r = v["requirements"][0]
        r["evidence"], r["status"], r["confirmed"] = "   ", "match", True
    assert any("needs evidence" in e for e in br.validate(report(m)))


def test_blank_quote_fields_are_rejected():
    def m(v):
        v["requirements"][0]["requirement"] = "   "
        v["requirements"][1]["evidence"] = " "
        v["red_flags"] = [{"quote": "  ", "text": "x"}]
        v["talking_points"][0]["vacancy"] = "\t"
    d = report(m)
    errs = " ".join(br.validate(d))
    for field in ("requirement 1: `requirement`", "requirement 2: `evidence`", "red flag 1: `quote`",
                  "talking point 1: `vacancy`"):
        assert field in errs, field
    cv, vac = texts()
    labels = {label for label, _ in br.missing_quotes(d, cv=[cv], vacancy=[vac])}
    assert {"requirement", "evidence", "red flag quote", "talking point (vacancy)"} <= labels


def test_null_evidence_still_means_none():
    assert br.validate(report()) == []  # the examples use "evidence": null for "no evidence"


def test_short_vacancy_quotes_are_allowed():
    def m(v):
        v["requirements"] = [{"requirement": "Node.js", "evidence": None, "status": "unknown"}]
        v["red_flags"] = [{"quote": "до $1000", "text": "low pay"}]
        v["talking_points"] = []
    d = report(m)
    assert br.validate(d) == []
    assert br.missing_quotes(d, cv=["CV text"], vacancy=["Node.js, React. Зарплата до $1000."]) == []


# --- small extras: BOM, lang, one-line errors, UTF-8 output ---------------------------

def test_json_with_bom_is_read(tmp_path):
    j = write_json(tmp_path, report(), encoding="utf-8-sig")
    assert run("build_report.py", j, tmp_path / "r.html", "--cv", CV, "--vacancy", VAC).returncode == 0
    kw = tmp_path / "kw.json"
    kw.write_text(json.dumps({"stack": ["angular"]}), encoding="utf-8-sig")
    r = run("scan.py", VAC, "--keywords", kw)
    assert r.returncode == 0 and "[stack] angular" in r.out


def test_lang_variants_map_to_ukrainian(tmp_path):
    for lang in ("UK", "uk-UA", "ua", "UA", " Uk "):
        assert '<html lang="uk">' in br.render({**report(), "lang": lang}), lang
        assert '<html lang="uk">' in bp.render("# T", lang=lang), lang
    r = run("build_report.py", write_json(tmp_path, {**report(), "lang": "uk-UA"}), tmp_path / "r.html",
            "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 0 and "unknown lang" not in r.out
    r = run("build_page.py", os.path.join(ROOT, "references", "menu.md"), tmp_path / "m.html", "--cards", "--lang", "UA")
    assert r.returncode == 0 and "unknown lang" not in r.out


def one_line_error(r):
    return r.returncode == 2 and "Traceback" not in r.out and len(r.out.strip().splitlines()) == 1


def test_bad_input_gives_one_line_error_and_exit_2(tmp_path):
    good = write_json(tmp_path, report())
    out = tmp_path / "r.html"
    cp1251 = tmp_path / "cv1251.txt"
    cp1251.write_bytes("Досвід роботи з React".encode("cp1251"))
    broken = tmp_path / "broken.json"
    broken.write_text('{"vacancies": [', encoding="utf-8")
    listed = tmp_path / "list.json"
    listed.write_text("[]", encoding="utf-8")
    cases = {
        "report: flag without value": ("build_report.py", good, out, "--cv"),
        "report: missing JSON": ("build_report.py", tmp_path / "nope.json", out, "--cv", CV, "--vacancy", VAC),
        "report: missing CV": ("build_report.py", good, out, "--cv", tmp_path / "nope.md", "--vacancy", VAC),
        "report: non-UTF-8 CV": ("build_report.py", good, out, "--cv", cp1251, "--vacancy", VAC),
        "report: malformed JSON": ("build_report.py", broken, out, "--cv", CV, "--vacancy", VAC),
        "report: JSON is not an object": ("build_report.py", listed, out, "--cv", CV, "--vacancy", VAC),
        "page: flag without value": ("build_page.py", os.path.join(EX, "prep.md"), out, "--source"),
        "page: missing input": ("build_page.py", tmp_path / "nope.md", out),
        "page: non-UTF-8 source": ("build_page.py", os.path.join(EX, "prep.md"), out, "--source", cp1251),
        "verify: missing answer": ("verify_quotes.py", tmp_path / "nope.md", CV),
        "verify: non-UTF-8 source": ("verify_quotes.py", os.path.join(EX, "prep.md"), cp1251),
    }
    for name, (script, *args) in cases.items():
        r = run(script, *args)
        assert one_line_error(r), (name, r.returncode, r.out)
    assert not out.exists()


def test_cli_output_is_utf8_through_a_pipe(tmp_path):
    quote = "Досвідʼ ✅ роботи з React понад п'ять років"
    def m(v):
        r = v["requirements"][0]
        r["evidence"], r["status"], r["confirmed"] = quote, "match", False
    r = run("build_report.py", write_json(tmp_path, report(m)), tmp_path / "r.html", "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 1 and quote in r.out and "Traceback" not in r.out
    ans = tmp_path / "a.md"
    ans.write_text(f'"{quote}"', encoding="utf-8")
    r = run("verify_quotes.py", ans, CV)
    assert r.returncode == 1 and quote in r.out and "Traceback" not in r.out
    md = tmp_path / "p.md"
    md.write_text(f'# T\n\n- "{quote}"\n', encoding="utf-8")
    r = run("build_page.py", md, tmp_path / "p.html", "--source", CV)
    assert r.returncode == 1 and quote in r.out and "Traceback" not in r.out
    vac = tmp_path / "v.txt"
    vac.write_text("Офіс у Львові ✅, зʼявилась гібридна модель", encoding="utf-8")
    r = run("scan.py", vac)
    assert r.returncode == 0 and "зʼявилась" in r.out and "Traceback" not in r.out
