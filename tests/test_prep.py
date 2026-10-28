"""Step 7c: interview prep is built from JSON, so evidence lives only in checked quote fields."""
import copy
import html
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import build_report as br  # noqa: E402
from verify_quotes import extract_quotes  # noqa: E402

EX = os.path.join(ROOT, "examples", "frontend")
CV, VAC = os.path.join(EX, "cv.md"), os.path.join(EX, "vacancy.txt")
CV_LINE = "Added real-time updates over WebSocket"
VAC_LINE = "Mentor and coach engineers"


def bp():
    import build_prep  # imported here so each test fails on its own before the script exists
    return build_prep


def run(*args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build_prep.py"), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    r.out = r.stdout + r.stderr
    return r


def prep():
    with open(os.path.join(EX, "prep.json"), encoding="utf-8") as f:
        return json.load(f)


def texts():
    with open(CV, encoding="utf-8") as f, open(VAC, encoding="utf-8") as g:
        return f.read(), g.read()


def build(tmp_path, d, *flags):
    j = tmp_path / "p.json"
    j.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "p.html"
    return run(j, out, "--cv", CV, "--vacancy", VAC, *flags), out


def shown(text):
    return html.escape(text, quote=True)


def first_question(d, **changes):
    d["questions"][0].update(changes)
    return d


# --- the example ----------------------------------------------------------------------

def test_prep_example_builds_with_cv_and_vacancy(tmp_path):
    r = run(os.path.join(EX, "prep.json"), tmp_path / "p.html", "--cv", CV, "--vacancy", VAC)
    assert r.returncode == 0, r.out
    page = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert page.count('<meta name="generator" content="job-fit">') == 1
    assert br.LABELS["en"]["prep_questions"] in page and "<q>" in page


def test_prep_json_has_the_same_evidence_as_prep_md():
    with open(os.path.join(EX, "prep.md"), encoding="utf-8") as f:
        md_quotes = set(extract_quotes(f.read()))
    json_quotes = {text for _, text, _ in bp().quote_fields(prep()) if text}
    assert md_quotes <= json_quotes, md_quotes - json_quotes
    assert bp().validate(prep()) == []


# --- evidence only in checked fields, each from its own document -------------------------

def test_vacancy_line_as_episode_is_rejected(tmp_path):
    d = first_question(prep(), episode=VAC_LINE, confirmed=False)
    cv, vac = texts()
    assert ("episode", VAC_LINE) in bp().missing_quotes(d, cv=[cv], vacancy=[vac])
    r, out = build(tmp_path, d)
    assert r.returncode == 1 and not out.exists()


def test_cv_line_as_requirement_is_rejected(tmp_path):
    d = first_question(prep(), requirement=CV_LINE)
    r, out = build(tmp_path, d)
    assert r.returncode == 1 and not out.exists() and CV_LINE in r.out


def test_cv_line_in_weak_spot_or_brush_up_is_rejected():
    cv, vac = texts()
    d = prep()
    d["weak_spots"] = [{"text": "x", "requirement": CV_LINE}]
    d["brush_up"] = [{"topic": "y", "vacancy": CV_LINE}]
    labels = {label for label, _ in bp().missing_quotes(d, cv=[cv], vacancy=[vac])}
    assert {"weak spot requirement", "brush up vacancy"} <= labels


def test_short_episode_is_rejected():
    d = first_question(prep(), episode="Angular", confirmed=False)
    cv, vac = texts()
    assert ("episode", "Angular") in bp().missing_quotes(d, cv=[cv], vacancy=[vac])


def test_confirmed_must_be_a_boolean(tmp_path):
    d = first_question(prep(), episode="Led a team of 40 engineers at Google", confirmed="false")
    assert any("`confirmed`" in e for e in bp().validate(d))
    cv, vac = texts()
    assert ("episode", "Led a team of 40 engineers at Google") in bp().missing_quotes(d, cv=[cv], vacancy=[vac])
    r, out = build(tmp_path, d)
    assert r.returncode == 1 and not out.exists()


def test_confirmed_episode_is_free_text_with_the_tag():
    d = first_question(prep(), episode='Led the "Atlas" initiative end to end', confirmed=True)
    cv, vac = texts()
    assert bp().missing_quotes(d, cv=[cv], vacancy=[vac]) == []
    page = bp().render(d)
    assert br.LABELS["en"]["confirmed"] in page and "Led the Atlas initiative end to end" in page


def test_a_match_needs_an_episode():
    d = first_question(prep(), status="match")
    d["questions"][0].pop("episode", None)
    assert any("a match needs an episode" in e for e in bp().validate(d))


def test_status_and_blank_fields_are_validated():
    d = first_question(prep(), status="great", requirement="   ")
    errs = " ".join(bp().validate(d))
    assert "status must be one of" in errs and "`requirement` must be non-blank text" in errs


# --- every section optional, labels, free text ---------------------------------------------

def test_prep_with_only_brush_up_builds(tmp_path):
    d = {"brush_up": [{"topic": "React basics", "vacancy": "TypeScript and React or Angular"}]}
    assert bp().validate(d) == []
    r, out = build(tmp_path, d)
    assert r.returncode == 0, r.out
    page = out.read_text(encoding="utf-8")
    assert f"<title>{br.LABELS['en']['prep_title']}</title>" in page
    assert br.LABELS["en"]["prep_questions"] not in page


def test_ukrainian_prep_labels():
    d = {**prep(), "lang": "uk-UA"}
    page = bp().render(d)
    uk = br.LABELS["uk"]
    assert '<html lang="uk">' in page
    for key in ("prep_process", "prep_questions", "prep_weak", "prep_brush", "money", "prep_ask", "prep_before",
                "next_steps", "group_role", "group_technical"):
        assert uk[key] in page, key
    assert br.LABELS["en"]["prep_questions"] not in page


def test_free_text_is_stripped_and_quote_fields_are_quotes():
    d = prep()
    d["questions"][0]["frame"] = 'Say "six years" plainly, mention «Acme Analytics».'
    d["money"] = "Ask for «gross» or net."
    d["next_steps"] = [{"label": "Prep «Acme»", "command": 'Prepare me for "Senior Frontend"'}]
    page = bp().render(d)
    assert "Say six years plainly, mention Acme Analytics." in page and "Ask for gross or net." in page
    assert f"<q>{shown(d['questions'][0]['requirement'])}</q>" in page
    assert f'data-cmd="{shown(d["next_steps"][0]["command"])}"' in page  # next steps keep their marks
    assert shown("Prep «Acme»") in page


def test_force_writes_and_marks_missing_quotes(tmp_path):
    d = first_question(prep(), requirement=CV_LINE)
    r, out = build(tmp_path, d, "--force")
    assert r.returncode == 0 and 'class="missing"' in out.read_text(encoding="utf-8")


def test_source_is_not_a_prep_flag(tmp_path):
    r = run(os.path.join(EX, "prep.json"), tmp_path / "p.html", "--source", CV)
    assert r.returncode == 2 and len(r.out.strip().splitlines()) == 1 and not (tmp_path / "p.html").exists()


def test_prep_page_is_light_with_the_same_look():
    page = bp().render(prep())
    assert ':root[data-jf="dark"]' in page and 'data-t="light"' in page and "prefers-color-scheme" not in page
