import copy
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_report as br  # noqa: E402

ROLES = ["frontend", "backend", "project-manager", "designer"]


def load(role):
    d = os.path.join(ROOT, "examples", role)
    with open(os.path.join(d, "report.json"), encoding="utf-8") as f:
        data = json.load(f)
    srcs = []
    for n in ("cv.md", "vacancy.txt"):
        with open(os.path.join(d, n), encoding="utf-8") as f:
            srcs.append(f.read())
    return data, srcs


@pytest.mark.parametrize("role", ROLES)
def test_examples_valid_and_quotes_exist(role):
    data, srcs = load(role)
    assert br.validate(data) == []
    assert br.missing_quotes(data, srcs) == []


@pytest.mark.parametrize("role", ROLES)
def test_examples_render_with_marks(role):
    data, _ = load(role)
    page = br.render(data)
    assert page.startswith("<!doctype html>")
    for v in data["vacancies"]:
        assert br.VERDICT[v["verdict"]["mark"]][0] in page
        for r in v.get("requirements", []):
            assert br.STATUS[r["status"]][0] in page
    assert "prefers-color-scheme" not in page and 'data-jf="dark"' in page and "@media print" in page


def test_escapes_html():
    data, _ = load("frontend")
    d = copy.deepcopy(data)
    d["vacancies"][0]["title"] = "<script>alert(1)</script>"
    d["vacancies"][0]["verdict"]["text"] = "<img src=x onerror=1>"
    page = br.render(d)
    assert "<script>alert(1)</script>" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;" in page


def test_validation_errors():
    assert br.validate({}) != []
    bad = {"vacancies": [{"title": "", "verdict": {"mark": "great", "text": ""},
                          "requirements": [{"requirement": "x", "status": "match"}]}]}
    errs = " ".join(br.validate(bad))
    assert "missing title" in errs and "verdict.mark" in errs
    assert "verdict.text" in errs and "needs evidence" in errs


def test_growth_tag_required():
    data, _ = load("frontend")
    d = copy.deepcopy(data)
    d["vacancies"][0]["growth"] = {"new": [{"text": "x", "tag": "maybe"}]}
    assert any("growth tag" in e for e in br.validate(d))


def test_missing_quote_detected_and_confirmed_skipped():
    data, srcs = load("frontend")
    d = copy.deepcopy(data)
    r = d["vacancies"][0]["requirements"][0]
    r["evidence"] = "this sentence is nowhere in the CV at all"
    r["status"] = "partial"
    assert ("evidence", r["evidence"]) in br.missing_quotes(d, srcs)
    r["confirmed"] = True
    assert ("evidence", r["evidence"]) not in br.missing_quotes(d, srcs)


def test_missing_quote_outlined_with_force():
    data, srcs = load("frontend")
    d = copy.deepcopy(data)
    d["vacancies"][0]["red_flags"] = [{"quote": "invented red flag quote here", "text": "x"}]
    bad = br.missing_quotes(d, srcs)
    assert 'class="missing"' in br.render(d, bad)


def test_summary_and_decide_render():
    data, _ = load("frontend")
    d = copy.deepcopy(data)
    d["summary"] = {"rows": [{"vacancy": "A", "verdict": "skip", "reason": "r", "check": "c"}],
                    "patterns": ["p"], "next": ["n"]}
    d["decide"] = [{"question": "Q?", "options": ["yes", "no"], "affects": "A"}]
    page = br.render(d)
    assert "Summary" in page and "Questions that decide this" in page and "❌" in page


def test_every_language_has_every_label():
    en = br.LABELS["en"]
    for lang, labels in br.LABELS.items():
        assert set(labels) == set(en), lang
        for group in ("status", "verdict"):
            assert set(labels[group]) == set(en[group]), (lang, group)


def test_ukrainian_report_labels():
    data, _ = load("frontend")
    d = copy.deepcopy(data)
    d["lang"] = "uk"
    page = br.render(d)
    uk = br.LABELS["uk"]
    assert '<html lang="uk">' in page and uk["requirements"] in page and uk["next_steps"] in page
    assert f'{uk["profile"]}:' in page and "Profile:" not in page
    for v in d["vacancies"]:
        assert uk["verdict"][v["verdict"]["mark"]] in page
        for r in v.get("requirements", []):
            assert uk["status"][r["status"]] in page


def test_unknown_lang_falls_back_to_english_with_warning(tmp_path):
    data, srcs = load("frontend")
    d = copy.deepcopy(data)
    d["lang"] = "xx"
    j, out = tmp_path / "a.json", tmp_path / "r.html"
    j.write_text(json.dumps(d), encoding="utf-8")
    cv, vac = tmp_path / "cv.txt", tmp_path / "vac.txt"
    cv.write_text(srcs[0], encoding="utf-8")
    vac.write_text(srcs[1], encoding="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_report.py"), str(j), str(out),
                        "--cv", str(cv), "--vacancy", str(vac)], capture_output=True, text=True)
    assert r.returncode == 0 and "warning" in r.stdout and "xx" in r.stdout
    assert "Requirements vs CV" in out.read_text(encoding="utf-8")


def test_cli_fails_on_missing_quote_and_writes_on_good(tmp_path):
    data, srcs = load("frontend")
    d = copy.deepcopy(data)
    d["vacancies"][0]["red_flags"] = [{"quote": "invented red flag quote here", "text": "x"}]
    j = tmp_path / "a.json"
    j.write_text(json.dumps(d), encoding="utf-8")
    cv, vac = tmp_path / "cv.txt", tmp_path / "vac.txt"
    cv.write_text(srcs[0], encoding="utf-8")
    vac.write_text(srcs[1], encoding="utf-8")
    out = tmp_path / "r.html"
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "build_report.py"), str(j), str(out),
           "--source", str(cv), "--source", str(vac)]
    assert subprocess.run(cmd, capture_output=True).returncode == 1
    assert not out.exists()
    assert subprocess.run(cmd + ["--force"], capture_output=True).returncode == 0
    assert out.exists()


def test_letter_draft_renders_with_copy_button_and_escaping():
    data, _ = load("frontend")
    d = copy.deepcopy(data)
    d["vacancies"][0]["letter_draft"] = "Hi!\n<b>I build</b> Angular apps."
    assert br.validate(d) == []
    page = br.render(d)
    assert "Application draft" in page and "check every claim" in page
    assert "&lt;b&gt;I build&lt;/b&gt;" in page and "Copy the draft" in page


def test_letter_draft_must_be_string():
    data, _ = load("frontend")
    d = copy.deepcopy(data)
    d["vacancies"][0]["letter_draft"] = ["not", "a", "string"]
    assert any("letter_draft" in e for e in br.validate(d))
