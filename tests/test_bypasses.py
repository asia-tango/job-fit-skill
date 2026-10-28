"""Regression tests for guard bypasses found in a real run (2026-10-27).

Each test reproduces one way an invented or misplaced quote got past the checks.
They are written before the fix: all of them fail on the old scripts.
"""
import copy
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
from verify_quotes import extract_quotes, missing_quotes  # noqa: E402

EX = os.path.join(ROOT, "examples", "frontend")
CV = os.path.join(EX, "cv.md")
VAC = os.path.join(EX, "vacancy.txt")


def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def report_with(tmp_path, mutate):
    with open(os.path.join(EX, "report.json"), encoding="utf-8") as f:
        data = json.load(f)
    d = copy.deepcopy(data)
    mutate(d["vacancies"][0])
    j = tmp_path / "a.json"
    j.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return j


def build(tmp_path, j):
    return run("build_report.py", j, tmp_path / "r.html", "--cv", CV, "--vacancy", VAC)


# --- build_report.py: quotes must come from the right document -----------------

def test_examples_pass_with_cv_and_vacancy_roles(tmp_path):
    for role in ("frontend", "backend", "project-manager", "designer"):
        d = os.path.join(ROOT, "examples", role)
        r = run("build_report.py", os.path.join(d, "report.json"), tmp_path / f"{role}.html",
                "--cv", os.path.join(d, "cv.md"), "--vacancy", os.path.join(d, "vacancy.txt"))
        assert r.returncode == 0, (role, r.stdout, r.stderr)


def test_evidence_copied_from_vacancy_is_rejected(tmp_path):
    def m(v):
        r = v["requirements"][0]
        r["evidence"], r["status"], r["confirmed"] = r["requirement"], "match", False
    assert build(tmp_path, report_with(tmp_path, m)).returncode == 1


def test_talking_point_cv_copied_from_vacancy_is_rejected(tmp_path):
    def m(v):
        t = v["talking_points"][0]
        t["cv"], t["confirmed"] = t["vacancy"], False
    assert build(tmp_path, report_with(tmp_path, m)).returncode == 1


def test_requirement_copied_from_cv_is_rejected(tmp_path):
    def m(v):
        r = v["requirements"][0]
        if r.get("evidence") and not r.get("confirmed"):
            r["requirement"] = r["evidence"]
    assert build(tmp_path, report_with(tmp_path, m)).returncode == 1


def test_trivially_short_evidence_is_rejected(tmp_path):
    def m(v):
        r = v["requirements"][0]
        r["evidence"], r["status"], r["confirmed"] = "Angular", "match", False
    assert build(tmp_path, report_with(tmp_path, m)).returncode == 1


def test_ukrainian_headings(tmp_path):
    with open(os.path.join(EX, "report.json"), encoding="utf-8") as f:
        data = json.load(f)
    data["lang"] = "uk"
    j = tmp_path / "uk.json"
    j.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "uk.html"
    assert run("build_report.py", j, out, "--cv", CV, "--vacancy", VAC).returncode == 0
    page = out.read_text(encoding="utf-8")
    assert "Requirements vs CV" not in page and "What next" not in page


# --- verify_quotes.py: every quote style is seen --------------------------------

SRC = ["Redesigned the RBAC architecture into a scalable reactive model."]


def test_guillemet_quote_is_checked():
    assert missing_quotes("Доказ: «Led a team of ten engineers in three countries»", SRC)


def test_low_high_quote_is_checked():
    assert missing_quotes("Доказ: „Led a team of ten engineers in three countries“", SRC)


def test_quote_broken_by_a_line_wrap_is_checked():
    answer = 'Evidence: "Redesigned the RBAC architecture into a scalable\nreactive model with React and Tailwind"'
    assert missing_quotes(answer, SRC)


def test_real_quote_broken_by_a_line_wrap_passes():
    answer = 'Evidence: "Redesigned the RBAC architecture into a\nscalable reactive model"'
    assert extract_quotes(answer) and missing_quotes(answer, SRC) == []


def test_ukrainian_apostrophes_are_equal():
    src = ["Досвід: зʼявилась нова роль у команді"]
    for a in ("з'явилась", "з’явилась", "зʼявилась"):
        assert missing_quotes(f'"Досвід: {a} нова роль у команді"', src) == [], a


def test_answer_without_quotes_is_not_ok(tmp_path):
    ans = tmp_path / "a.md"
    ans.write_text("Great fit, apply.", encoding="utf-8")
    src = tmp_path / "s.txt"
    src.write_text(SRC[0], encoding="utf-8")
    assert run("verify_quotes.py", ans, src).returncode == 3  # no quotes: nothing was checked


# --- build_page.py: prep pages are quote-checked too ------------------------------

def test_prep_page_checks_quotes(tmp_path):
    with open(os.path.join(EX, "prep.md"), encoding="utf-8") as f:
        prep = f.read()
    good = tmp_path / "good.md"
    good.write_text(prep, encoding="utf-8")
    assert run("build_page.py", good, tmp_path / "g.html", "--source", CV, "--source", VAC).returncode == 0
    bad = tmp_path / "bad.md"
    bad.write_text(prep + '\n- CV: "Led the frontend guild of forty engineers"\n', encoding="utf-8")
    r = run("build_page.py", bad, tmp_path / "b.html", "--source", CV, "--source", VAC)
    assert r.returncode == 1 and not (tmp_path / "b.html").exists()
