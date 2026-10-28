"""Step 8: the vacancy and the CV are untrusted input. Mechanical checks in the scripts, rules in the docs."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
EX = os.path.join(ROOT, "examples", "frontend")
CV, VAC = os.path.join(EX, "cv.md"), os.path.join(EX, "vacancy.txt")
REPORT, PREP = os.path.join(EX, "report.json"), os.path.join(EX, "prep.json")
EMPTY_MSG = "is empty – a scanned PDF? Provide the text."


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    r.out = r.stdout + r.stderr
    return r


def one_line_error(r):
    return r.returncode == 2 and "Traceback" not in r.out and len(r.out.strip().splitlines()) == 1


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# --- an unchecked report or prep never reaches the user ------------------------------------

def test_report_and_prep_need_both_cv_and_vacancy(tmp_path):
    out = tmp_path / "p.html"
    for script, data in (("build_report.py", REPORT), ("build_prep.py", PREP)):
        for flags in ([], ["--cv", CV], ["--vacancy", VAC], ["--cv", CV, "--force"], ["--force"]):
            r = run(script, data, out, *flags)
            assert one_line_error(r), (script, flags, r.out)
            assert "--cv" in r.out and "--vacancy" in r.out
            assert not out.exists(), (script, flags)


def test_legacy_source_alone_still_works_with_its_warning(tmp_path):
    r = run("build_report.py", REPORT, tmp_path / "r.html", "--source", CV, "--source", VAC)
    assert r.returncode == 0 and "warning: --source does not know which file is the CV" in r.out


def test_source_mixed_with_cv_or_vacancy_is_refused(tmp_path):
    # The review's bypass: a vacancy line as evidence passed with --cv cv --source vacancy.
    d = json.loads(read(REPORT))
    r0 = d["vacancies"][0]["requirements"][0]
    r0.update(evidence=r0["requirement"], status="match", confirmed=False)
    j = tmp_path / "a.json"
    j.write_text(json.dumps(d), encoding="utf-8")
    for flags in (["--cv", CV, "--source", VAC], ["--vacancy", VAC, "--source", CV],
                  ["--cv", CV, "--vacancy", VAC, "--source", VAC]):
        r = run("build_report.py", j, tmp_path / "r.html", *flags)
        assert one_line_error(r) and "--source" in r.out, (flags, r.out)
        assert not (tmp_path / "r.html").exists()


# --- empty, short and identical files -------------------------------------------------------

def test_empty_files_are_refused_everywhere(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("  \n\t\n", encoding="utf-8")
    out = tmp_path / "o.html"
    cases = {
        "report: empty CV": ("build_report.py", REPORT, out, "--cv", empty, "--vacancy", VAC),
        "report: empty vacancy": ("build_report.py", REPORT, out, "--cv", CV, "--vacancy", empty),
        "report: empty legacy source": ("build_report.py", REPORT, out, "--source", CV, "--source", empty),
        "prep: empty CV": ("build_prep.py", PREP, out, "--cv", empty, "--vacancy", VAC),
        "prep: empty vacancy": ("build_prep.py", PREP, out, "--cv", CV, "--vacancy", empty),
        "page: empty source": ("build_page.py", os.path.join(EX, "prep.md"), out, "--source", empty),
        "verify: empty source": ("verify_quotes.py", os.path.join(EX, "expected.md"), CV, empty),
    }
    for name, (script, *args) in cases.items():
        r = run(script, *args)
        assert one_line_error(r) and EMPTY_MSG in r.out, (name, r.out)
    assert not out.exists()
    assert "CV file " + EMPTY_MSG in run("build_report.py", REPORT, out, "--cv", empty, "--vacancy", VAC).out


def test_scan_keeps_its_exit_codes_on_an_empty_vacancy(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    r = run("scan.py", empty)
    assert r.returncode == 0 and "nothing found" in r.out


def small_report():
    return {"vacancies": [{"title": "T", "verdict": {"mark": "check", "text": "x"},
                           "requirements": [{"requirement": "Experience with Angular", "evidence": None,
                                             "status": "unknown"}]}]}


def test_short_files_only_warn(tmp_path):
    cv, vac = tmp_path / "cv.txt", tmp_path / "vac.txt"
    cv.write_text("Frontend engineer, Angular and TypeScript.", encoding="utf-8")
    vac.write_text("Experience with Angular required. Remote.", encoding="utf-8")
    j = tmp_path / "a.json"
    j.write_text(json.dumps(small_report()), encoding="utf-8")
    r = run("build_report.py", j, tmp_path / "r.html", "--cv", cv, "--vacancy", vac)
    assert r.returncode == 0 and (tmp_path / "r.html").exists()
    assert r.out.count("is short") == 2, r.out
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"brush_up": [{"topic": "x", "vacancy": "Experience with Angular"}]}), encoding="utf-8")
    r = run("build_prep.py", p, tmp_path / "p.html", "--cv", cv, "--vacancy", vac)
    assert r.returncode == 0 and r.out.count("is short") == 2, r.out
    r = run("build_report.py", REPORT, tmp_path / "r2.html", "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 0 and "is short" not in r.out  # the examples are long enough


def test_same_file_as_cv_and_vacancy_warns(tmp_path):
    both = tmp_path / "both.txt"
    both.write_text("Experience with Angular is required for this frontend role. " * 5, encoding="utf-8")
    copy_ = tmp_path / "copy.txt"
    copy_.write_text(both.read_text(encoding="utf-8"), encoding="utf-8")
    j = tmp_path / "a.json"
    j.write_text(json.dumps(small_report()), encoding="utf-8")
    warning = "the same file (or the same text) is given as --cv and --vacancy"
    for cv, vac in ((both, both), (both, copy_)):
        r = run("build_report.py", j, tmp_path / "r.html", "--cv", cv, "--vacancy", vac)
        assert r.returncode == 0 and warning in r.out, r.out
    r = run("build_report.py", REPORT, tmp_path / "r.html", "--cv", CV, "--vacancy", VAC)
    assert warning not in r.out


# --- docs: input is data, never instructions -----------------------------------------------

def test_skill_treats_vacancy_and_cv_as_data():
    skill = read(os.path.join(ROOT, "SKILL.md"))
    assert "data, never instructions" in skill
    for mode in ("Setup", "Single", "Batch", "Prep"):
        assert mode in skill
    assert "if you are an AI" in skill and "red flag" in skill
    assert "not a vacancy" in skill and "scanned PDF" in skill


def test_red_flags_no_longer_say_follow_instructions():
    flags = read(os.path.join(ROOT, "references", "red-flags.md"))
    assert "fine to follow" not in flags
    assert "addressed to an AI" in flags and "never followed" in flags


def test_docs_say_both_files_are_required():
    sentence = "Both `--cv` and `--vacancy` are required"
    for name in ("SKILL.md", "README.md"):
        text = read(os.path.join(ROOT, name))
        assert sentence in text, name
        assert "`--source` alone is a legacy form" in text, name


def test_manual_eval_has_the_untrusted_input_cases():
    manual = read(os.path.join(ROOT, "tests", "MANUAL_EVAL.md"))
    for case in ("A recipe as the vacancy", "AI instruction", "Swapped CV and vacancy", "An empty CV"):
        assert case in manual, case
