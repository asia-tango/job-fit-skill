"""The shared evidence checker (Step 7a): word boundaries and per-file matching, on every path."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import build_report as br  # noqa: E402
import verify_quotes as vq  # noqa: E402

EX = os.path.join(ROOT, "examples", "frontend")
CV_TEXT = ("Built data-heavy dashboards in Angular with RxJS and NgRx.\n"
           "Languages: C++ and Python 3. Optimized AG Grid for 10,000+ rows.\n"
           "Server-side rendering (SSR) with Angular Universal.\n"
           "Досвід роботи з React понад 5 років. Досвід: зʼявилась нова роль у команді.")
VAC_TEXT = "We need C++, (SSR) and 10,000+ rows. Досвід роботи з Node.js."


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    r.out = r.stdout + r.stderr
    return r


def report(evidence_text=None, requirement="Experience with Angular"):
    return {"vacancies": [{"title": "T", "verdict": {"mark": "check", "text": "x"},
                           "requirements": [{"requirement": requirement, "evidence": evidence_text,
                                             "status": "partial"}]}]}


def cv_problems(evidence_text, cv=(CV_TEXT,)):
    return br.missing_quotes(report(evidence_text, requirement="We need C++"), cv=list(cv), vacancy=[VAC_TEXT])


# --- one implementation ----------------------------------------------------------------

def test_one_checker_behind_every_name():
    import evidence
    assert vq.normalize is evidence.normalize and br.normalize is evidence.normalize
    assert vq.MIN_LEN == br.MIN_LEN == evidence.MIN_LEN
    assert evidence.confirmed_error({"confirmed": "false"}) and evidence.confirmed_error({"confirmed": True}) is None
    assert evidence.check_fields([("evidence", "Optimized AG Grid for 10,000+ rows", "cv")], [CV_TEXT], [VAC_TEXT]) == []


# --- word boundaries -------------------------------------------------------------------

def test_quote_cut_in_the_middle_of_a_word_is_rejected():
    assert cv_problems("ngular with RxJS and Ng")
    assert cv_problems("Built data-heavy dashboards in Angular with RxJS and Ng")
    assert br.missing_quotes(report(None, requirement="eed C++"), cv=[CV_TEXT], vacancy=[VAC_TEXT])


def test_quotes_with_symbols_at_the_edges_pass():
    for ev in ("Languages: C++ and Python 3", "Optimized AG Grid for 10,000+ rows",
               "Server-side rendering (SSR)", "(SSR) with Angular Universal"):
        assert cv_problems(ev) == [], ev
    for req in ("C++", "(SSR)", "10,000+ rows", "We need C++,"):
        assert br.missing_quotes(report(None, requirement=req), cv=[CV_TEXT], vacancy=[VAC_TEXT]) == [], req


def test_ukrainian_words_and_apostrophes():
    assert cv_problems("Досвід роботи з React понад") == []
    assert cv_problems("Досвід: з'явилась нова роль у команді") == []
    assert cv_problems("освід роботи з React понад")  # starts mid-word
    assert cv_problems("явилась нова роль у команді")  # starts after the apostrophe inside з'явилась
    assert cv_problems("Досвід роботи з Reac")  # ends mid-word


def test_free_text_path_checks_word_boundaries_too(tmp_path):
    assert vq.missing_quotes('"ngular with RxJS and NgRx"', [CV_TEXT])
    assert vq.missing_quotes('"Built data-heavy dashboards in Angular"', [CV_TEXT]) == []
    md = tmp_path / "p.md"
    md.write_text('# Prep\n\n- CV: "uilt data-heavy dashboards in Angular"\n', encoding="utf-8")
    r = run("build_page.py", md, tmp_path / "p.html", "--source", os.path.join(EX, "cv.md"))
    assert r.returncode == 1 and not (tmp_path / "p.html").exists()


# --- no stitching across files ---------------------------------------------------------

A = "Led the payments migration end to end."
B = "Mentored three junior engineers."
STITCHED = "end to end. Mentored three junior engineers"  # end of A + start of B


def test_quote_may_not_join_two_cv_files():
    assert cv_problems(STITCHED, cv=(A, B))
    assert cv_problems("Led the payments migration end to end", cv=(A, B)) == []
    assert cv_problems("Mentored three junior engineers", cv=(A, B)) == []


def test_quote_may_not_join_two_legacy_sources():
    assert ("evidence", STITCHED) in br.missing_quotes(report(STITCHED), [A, B])


def test_free_text_quote_may_not_join_two_sources(tmp_path):
    assert vq.missing_quotes(f'"{STITCHED}"', [A, B])
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text(A, encoding="utf-8")
    b.write_text(B, encoding="utf-8")
    ans = tmp_path / "ans.md"
    ans.write_text(f'Evidence: "{STITCHED}"', encoding="utf-8")
    assert run("verify_quotes.py", ans, a, b).returncode == 1
    md = tmp_path / "p.md"
    md.write_text(f'# Prep\n\n- CV: "{STITCHED}"\n', encoding="utf-8")
    r = run("build_page.py", md, tmp_path / "p.html", "--source", a, "--source", b)
    assert r.returncode == 1 and not (tmp_path / "p.html").exists()


def test_report_cli_checks_each_cv_file_on_its_own(tmp_path):
    a, b = tmp_path / "cv1.md", tmp_path / "cv2.md"
    a.write_text(A, encoding="utf-8")
    b.write_text(B, encoding="utf-8")
    vac = os.path.join(EX, "vacancy.txt")
    with open(os.path.join(EX, "report.json"), encoding="utf-8") as f:
        d = json.load(f)
    v = d["vacancies"][0]
    v["talking_points"], v["red_flags"] = [], []
    v["requirements"] = [{**v["requirements"][0], "evidence": STITCHED, "status": "partial", "confirmed": False}]
    j = tmp_path / "a.json"
    j.write_text(json.dumps(d), encoding="utf-8")
    r = run("build_report.py", j, tmp_path / "r.html", "--cv", a, "--cv", b, "--vacancy", vac)
    assert r.returncode == 1 and STITCHED in r.out


def test_a_quote_may_still_wrap_lines_inside_one_file():
    src = ["Led the payments migration\nend to end, with two teams."]
    assert vq.missing_quotes('"Led the payments migration end to end"', src) == []
    assert cv_problems("Led the payments migration end to end", cv=src) == []
