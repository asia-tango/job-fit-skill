import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_page as bp  # noqa: E402


def test_profile_example_renders():
    with open(os.path.join(ROOT, "examples", "profile.example.md"), encoding="utf-8") as f:
        page = bp.render(f.read())
    assert "<h1>Profile" in page and "<h2>Constraints</h2>" in page
    assert "<table>" in page and "<li>Mentoring people</li>" in page
    assert "prefers-color-scheme" not in page and 'id="tt"' in page


def test_escapes_html_and_bad_links():
    page = bp.render("# T\n\n<script>alert(1)</script> [x](javascript:alert(1)) [ok](https://a.dev)")
    assert "<script>alert" not in page
    assert 'href="javascript' not in page
    assert 'href="https://a.dev"' in page


def test_inline_and_quote():
    page = bp.render("# T\n\n**bold** *it* `code`\n\n> quoted line")
    assert "<strong>bold</strong>" in page and "<em>it</em>" in page
    assert "<code>code</code>" in page and "<blockquote>quoted line</blockquote>" in page


def test_ordered_list_and_rule_no_hang():
    page = bp.render("1. a\n2. b\n\n---\n\ntext\n#nospace\n")
    assert "<ol>" in page and "<hr>" in page


def test_cli(tmp_path):
    src = tmp_path / "a.md"
    src.write_text("# Hi\n\n- x\n", encoding="utf-8")
    out = tmp_path / "a.html"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_page.py"), str(src), str(out)])
    assert r.returncode == 0 and "<h1>Hi</h1>" in out.read_text(encoding="utf-8")
    assert subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_page.py")],
                          capture_output=True).returncode == 2


def test_page_without_quotes_builds_with_sources(tmp_path):
    # The "no quotes" exit 3 belongs to the verify_quotes.py CLI only: a profile, menu or research
    # page that quotes nothing is a normal page.
    d = os.path.join(ROOT, "examples", "frontend")
    script = os.path.join(ROOT, "scripts", "build_page.py")
    for name, md in (("profile", os.path.join(ROOT, "examples", "profile.example.md")),
                     ("menu", os.path.join(ROOT, "references", "menu.md"))):
        out = tmp_path / f"{name}.html"
        r = subprocess.run([sys.executable, script, md, str(out),
                            "--source", os.path.join(d, "cv.md"), "--source", os.path.join(d, "vacancy.txt")],
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0 and out.exists(), (name, r.stdout)
    out = tmp_path / "menu-cards.html"
    r = subprocess.run([sys.executable, script, os.path.join(ROOT, "references", "menu.md"), str(out), "--cards"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and out.exists() and "warning" not in r.stdout


def test_page_fixed_strings_follow_lang():
    import build_report as br
    uk = br.LABELS["uk"]
    page = bp.render("# T\n\n[[cmd: A | b]]", lang="uk")
    assert '<html lang="uk">' in page
    for key in ("light", "dark", "copy", "copied"):
        assert uk[key] in page, key
    assert ">Light<" not in page and ">Copy<" not in page
    assert '<html lang="en">' in bp.render("# T")


def test_prep_example_quotes_exist_and_render():
    import verify_quotes as vq
    d = os.path.join(ROOT, "examples", "frontend")
    read = lambda n: open(os.path.join(d, n), encoding="utf-8").read()  # noqa: E731
    prep = read("prep.md")
    assert vq.missing_quotes(prep, [read("cv.md"), read("vacancy.txt")]) == []
    for sec in ("Likely questions", "Weak spots", "Brush up", "Money and format", "Your questions for them", "Before the call"):
        assert f"## {sec}" in prep
    assert "<h2>Likely questions</h2>" in bp.render(prep)


def test_skill_has_prep_mode():
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "**Prep**" in skill and "references/interview-prep.md" in skill
    assert os.path.exists(os.path.join(ROOT, "references", "interview-prep.md"))


def test_menu_renders_with_copy_buttons_and_no_chat_sending():
    page = bp.render(open(os.path.join(ROOT, "references", "menu.md"), encoding="utf-8").read())
    assert page.count('class="cmd"') >= 6
    assert 'data-cmd="reset"' in page and "navigator.clipboard" in page
    assert "fetch(" not in page and "XMLHttpRequest" not in page


def test_cmd_text_is_escaped():
    page = bp.render('# T\n\n[[cmd: A | say "x" <b>]]')
    assert "<b>]" not in page and "&lt;b&gt;" in page


def test_report_next_steps(tmp_path):
    import json
    import build_report as br
    d = json.load(open(os.path.join(ROOT, "examples", "frontend", "report.json"), encoding="utf-8"))
    assert br.validate(d) == [] and "What next" in br.render(d)
    d["next_steps"] = [{"label": "x"}]
    assert any("next_steps" in e for e in br.validate(d))


def test_menu_cards_layout():
    md = open(os.path.join(ROOT, "references", "menu.md"), encoding="utf-8").read()
    page = bp.render(md, cards=True)
    assert page.count('class="tile"') == 5 and 'class="hero"' in page and 'class="n">1<' in page
    assert 'class="foot"' in page and page.count('class="cmd"') >= 6
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "menu.html --cards" in skill


def test_pages_carry_generator_marker_and_skill_forbids_hand_made_pages():
    import build_report as br
    assert 'name="generator" content="job-fit"' in bp.render("# T")
    import json
    d = json.load(open(os.path.join(ROOT, "examples", "frontend", "report.json"), encoding="utf-8"))
    assert 'name="generator" content="job-fit"' in br.render(d)
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "Never publish Markdown as an artifact" in skill and "generator" in skill


def test_light_by_default_ignores_host_theme_and_has_two_way_switch():
    page = bp.render("# T")
    assert "data-theme" not in page and "prefers-color-scheme" not in page
    assert ':root[data-jf="dark"]' in page
    assert 'data-t="light"' in page and 'data-t="dark"' in page
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "always light by default" in skill


def test_no_open_text_questions_anywhere():
    intake = open(os.path.join(ROOT, "references", "intake.md"), encoding="utf-8").read()
    assert "free-text prompt asking which" not in intake
    assert "Follow-ups are quizzes too" in intake and "Other" in intake
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "Don't ask open-sentence questions, ever" in skill



def test_ready_made_followup_cards_exist():
    intake = open(os.path.join(ROOT, "references", "intake.md"), encoding="utf-8").read()
    assert "Ready-made follow-up cards" in intake
    for key in ("What did it involve?", "Which should go in the profile?", "used it in real work"):
        assert key in intake
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    assert "a question in plain prose means rewrite it as a card" in skill
