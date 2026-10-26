"""Every example pair must hold up, for every role family."""
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from scan import scan  # noqa: E402
from verify_quotes import extract_quotes, missing_quotes  # noqa: E402

EX = os.path.join(ROOT, "examples")
ROLES = sorted(d for d in os.listdir(EX) if os.path.isdir(os.path.join(EX, d)))


def read(role, name):
    with open(os.path.join(EX, role, name), encoding="utf-8") as f:
        return f.read()


def test_there_are_several_role_families():
    assert len(ROLES) >= 4


@pytest.mark.parametrize("role", ROLES)
def test_expected_output_quotes_exist_in_sources(role):
    answer = read(role, "expected.md")
    sources = [read(role, "cv.md"), read(role, "vacancy.txt")]
    assert len(extract_quotes(answer)) >= 8
    assert missing_quotes(answer, sources) == []


@pytest.mark.parametrize("role", ROLES)
def test_expected_output_has_all_required_sections(role):
    answer = read(role, "expected.md")
    for heading in [
        "**Verdict**", "**What would change the verdict**", "**Requirements vs CV**",
        "**Fix in the CV**", "**Growth**", "**Red flags**", "**Money and format**",
        "**Questions to ask**", "**Talking points for the application**",
    ]:
        assert heading in answer, f"{role}: missing {heading}"


@pytest.mark.parametrize("role", ROLES)
def test_every_status_has_the_matching_mark(role):
    marks = {"match": "\u2705", "partial": "\u26a0", "not": "\u2753", "gap": "\u274c"}
    answer = read(role, "expected.md")
    rows = [ln for ln in answer.splitlines() if ln.startswith("| ") and "---" not in ln][1:]
    assert rows
    for row in rows:
        status = row.split("|")[-2].strip()
        mark, word = status.split()[0], status.split()[1].lower()
        assert word in marks, f"{role}: {status}"
        assert mark.startswith(marks[word]), f"{role}: {status}"


@pytest.mark.parametrize("role", ROLES)
def test_verdict_starts_with_a_mark(role):
    answer = read(role, "expected.md")
    line = [ln for ln in answer.splitlines() if ln.startswith("**Verdict**")][0]
    assert line.split(" \u2013 ")[1].startswith(("\u2705", "\u26a0", "\u2753", "\u274c")), line


@pytest.mark.parametrize("role", ROLES)
def test_no_personal_keywords_without_config(role):
    """With no config the scanner must not report any stack or avoid hits (no hard-coded role bias)."""
    found = scan(read(role, "vacancy.txt"))
    assert "stack" not in found
    assert "avoid" not in found


def test_config_picks_up_the_users_own_terms():
    text = read("backend", "vacancy.txt")
    found = scan(text, {"stack": ["python", "kubernetes"], "avoid": ["pci dss"]})
    assert set(found["stack"]) == {"python", "kubernetes"}
    assert "pci dss" in found["avoid"]


def test_universal_signals_work_for_non_engineering_roles():
    pm = scan(read("project-manager", "vacancy.txt"))
    assert "location / legal" in pm["signal"]
    assert "money" in pm["signal"]
    designer = scan(read("designer", "vacancy.txt"))
    assert "contract / format" in designer["signal"]
    assert "schedule" in designer["signal"]


def test_intake_questions_are_multiple_choice():
    """Setup questions must come with options, so the skill never asks open sentences."""
    with open(os.path.join(ROOT, "references", "intake.md"), encoding="utf-8") as f:
        text = f.read()
    rows = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("| ") and ln.strip().split("|")[1].strip().isdigit()]
    assert len(rows) >= 8
    for row in rows:
        options = row.split("|")[3]
        assert options.count("·") >= 1 or "type your own" in options, row
    assert "AskUserQuestion" in text and "lettered options" in text


def test_skill_requires_multiple_choice_questions_and_marks_guesses():
    with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as f:
        skill = f.read()
    assert "Questions that decide this" in skill
    assert "multiple-choice" in skill
    assert "`guess`" in skill


def test_profile_persistence_is_designed_for_chat_apps():
    with open(os.path.join(ROOT, "references", "intake.md"), encoding="utf-8") as f:
        intake = f.read()
    with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as f:
        skill = f.read()
    with open(os.path.join(ROOT, "references", "profile.template.md"), encoding="utf-8") as f:
        template = f.read()
    assert "## Saved profile" in intake and "fresh sandbox" in intake
    assert "attached or pasted" in skill and "Don't start a full Setup unprompted" in skill
    assert "## Keywords" in template


def test_profile_source_line_memory_marking_and_reset():
    with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as f:
        skill = f.read()
    assert "Profile: <source>" in skill
    assert "from memory – confirm" in skill
    assert '"reset"' in skill and "run Setup from the beginning" in skill
