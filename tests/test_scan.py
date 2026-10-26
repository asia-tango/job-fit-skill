import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from scan import scan, years_required, term_pattern  # noqa: E402


def test_pixi_is_flagged_only_if_the_user_avoids_it():
    text = "Senior Angular Developer\nYou will build games with Pixi.js and WebGL."
    assert "avoid" not in scan(text)
    found = scan(text, {"stack": ["angular"], "avoid": ["pixi.js", "webgl"]})
    assert set(found["avoid"]) == {"pixi.js", "webgl"}
    assert "angular" in found["stack"]


def test_term_pattern_handles_symbols_and_whole_words():
    import re
    assert re.search(term_pattern("c#"), "we use C# daily", re.I)
    assert not re.search(term_pattern("go"), "good tools", re.I)
    assert re.search(term_pattern("node.js"), "Node.js and Express", re.I)


def test_location_and_money_signals():
    found = scan("Location: United Kingdom. Occasional office visits. Salary 4000 USD gross.")
    assert "location / legal" in found["signal"]
    assert "money" in found["signal"]


def test_leadership_scope_detected():
    found = scan("You will lead complex initiatives and mentor engineers.")
    assert "leadership scope" in found["seniority"]
    assert "mentoring" in found["seniority"]


def test_management_scope_detected():
    found = scan("You will manage a team of ten and own the roadmap.")
    assert "leadership scope" in found["seniority"]


def test_years():
    assert years_required("8+ years of experience, 3 years of Angular") == 8
    assert years_required("Досвід від 5 років") == 5
    assert years_required("no numbers here") is None


def test_ukrainian_keywords():
    found = scan("Гібридний формат, офіс у Львові. Потрібні відрядження.")
    assert "location / legal" in found["signal"]
    found = scan("Проєкт у сфері гемблінгу", {"avoid": ["гемблінг"]})
    assert "гемблінг" in found["avoid"]


def test_empty_vacancy():
    assert scan("") == {}
