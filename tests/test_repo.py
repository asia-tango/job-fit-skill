"""Step 10: repo hygiene – CI, license, what git must ignore, and the README record."""
import os
import re
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def git(*args):
    try:
        r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if r.returncode not in (0, 1):  # check-ignore exits 1 when nothing is ignored
        pytest.skip(f"not a git checkout: {r.stderr.strip()}")
    return r


def test_ci_runs_the_tests_on_linux_and_windows():
    wf = read(".github", "workflows", "tests.yml")
    for needle in ("ubuntu-latest", "windows-latest", '"3.11"', '"3.12"', "pip install pytest", "pytest tests"):
        assert needle in wf, needle
    assert "actions/badge" not in wf
    assert "actions/workflows/tests.yml/badge.svg" in read("README.md")


def test_license_is_mit():
    text = read("LICENSE")
    assert text.startswith("MIT License") and "Copyright (c) 2026 Oleksandra Kaplun" in text
    assert "WITHOUT WARRANTY OF ANY KIND" in text


def test_gitignore_keeps_private_files_out():
    lines = [ln.strip() for ln in read(".gitignore").splitlines() if ln.strip() and not ln.startswith("#")]
    for pattern in ("references/profile.local.md", "references/keywords.local.json", "*.local.*", "profile.md",
                    "cv.*", "CV.*", "*.pdf", "*.docx", "*resume*", "*Resume*", "report*.html", "analysis*.json",
                    "prep*.html", "prep*.json"):
        assert pattern in lines, pattern
    assert lines.index("!examples/**") > max(lines.index(p) for p in ("cv.*", "*resume*", "*.docx", "prep*.json"))


def test_private_files_are_ignored_and_examples_are_not():
    private = ["my_resume.docx", "Resume 2026.pdf", "cv.md", "CV.pdf", "profile.md", "prep.json",
               "prep-acme.html", "references/profile.local.md", "notes.local.txt", "analysis.json"]
    r = git("check-ignore", "--no-index", *private)
    assert sorted(r.stdout.split("\n")[:-1]) == sorted(private), r.stdout
    kept = ["examples/frontend/cv.md", "examples/frontend/prep.json", "examples/profile.example.md",
            "tests/test_prep.py", "references/prep-schema.md", "docs/example-report.html"]
    assert git("check-ignore", "--no-index", *kept).stdout.strip() == ""


def test_no_real_cv_or_profile_is_tracked():
    tracked = git("ls-files").stdout.splitlines()
    assert tracked, "git ls-files returned nothing"
    # The same names .gitignore treats as private: cv.*, *resume*, profile.md, *.local.*, .docx, .pdf.
    private = re.compile(r"^cv\.|resume|^profile\.md$|\.local\.|\.(docx|pdf)$", re.I)
    for path in tracked:
        if private.search(os.path.basename(path)):
            assert path.startswith("examples/"), path  # only the fictional examples may look like a CV


def test_readme_shows_the_run_record():
    readme = read("README.md")
    assert "## Recorded runs" in readme and "| 2026-10-27 |" in readme and "| 2026-10-28 |" in readme
    manual = read("tests", "MANUAL_EVAL.md")
    for date in ("| 2026-10-27 |", "| 2026-10-28 |"):
        row = next(ln for ln in manual.splitlines() if ln.startswith(date))
        assert row in readme, f"README and MANUAL_EVAL disagree on {date}"
