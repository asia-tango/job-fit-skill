"""Step 9: the docs describe what the scripts really do (trust model, limitations, exit codes, records)."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    """The text of a `## heading` section, up to the next `## `."""
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


def test_rubric_has_the_accepted_lower_pay_exception():
    rubric = read("references", "fit-rubric.md")
    blockers = section(rubric, "1. Hard blockers")
    assert "accepts lower pay" in blockers and "`confirmed by you`" in blockers
    assert "update the minimum" in blockers and "rest of the rubric" in blockers
    stop_line = next(ln for ln in blockers.splitlines() if "Stop there" in ln)
    assert "lower pay" in stop_line  # the stop rule names its one exception


def test_profile_buttons_only_on_the_page():
    saved = section(read("references", "intake.md"), "Saved profile")
    assert "never into `profile.md`" in saved and "examples/profile.example.md" in saved


def test_readme_trust_section_matches_the_scripts():
    trust = section(read("README.md"), "Why you can trust the output")
    for phrase in ("checked fields", "its own document", "word", "12 characters", "Both `--cv` and `--vacancy`",
                   "data, never instructions", "without quote marks"):
        assert phrase in trust, phrase


def test_readme_has_no_stale_claims():
    readme = read("README.md")
    assert not re.search(r"\b\d+ pytest tests", readme)  # no hard-coded test count
    assert "English first" not in readme and "**Your language.**" in readme
    assert "Both `--cv` and `--vacancy` are required" in section(readme, "In short")


def test_readme_limitations_are_listed():
    limits = section(read("README.md"), "Known limitations")
    for phrase in ("`confirmed: true` skips the check", "regex fallback", "removed when the page is built",
                   "`letter_draft`", "two lines of the same file", "Batch mode", "mechanical",
                   "no CV/vacancy split", "`[[cmd: …]]`"):
        assert phrase in limits, phrase


def test_readme_structure_and_exit_codes():
    readme = read("README.md")
    structure = section(readme, "Structure")
    for path in ("scripts/evidence.py", "scripts/build_prep.py", "references/prep-schema.md",
                 "examples/frontend/prep.json"):
        assert path in structure, path
    codes = section(readme, "Exit codes")
    assert "--force" in codes and "build_page.py" in codes and "| 2 |" in codes and "| 3 |" in codes
    assert "does not mark" in read("scripts", "build_page.py")


def test_schemas_state_boolean_confirmed_and_input_checks():
    for name in ("report-schema.md", "prep-schema.md"):
        text = read("references", name)
        assert "boolean" in text and "empty" in text and "same file" in text, name


def test_report_check_instructions_point_at_the_builders():
    cv_check = read("references", "cv-check.md")
    assert "must pass `scripts/verify_quotes.py`" not in cv_check and "build_report.py" in cv_check
    manual = read("tests", "MANUAL_EVAL.md")
    quotes_line = next(ln for ln in manual.splitlines() if ln.startswith("1. **Quotes.**"))
    assert "build_report.py" in quotes_line and "--cv" in quotes_line
    skill = read("SKILL.md")
    step10 = skill[skill.index("10. Verify"):skill.index("## Output format")]
    assert "build_report.py" in step10 and "only if" in step10.lower() and "chat" in step10


def test_manual_eval_records_the_real_runs():
    record = section(read("tests", "MANUAL_EVAL.md"), "Record")
    assert "| 2026-10-27 |" in record and "3–4x below" in record and "apply with questions" in record
    assert "| 2026-10-28 |" in record
