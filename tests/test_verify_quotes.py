import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from verify_quotes import extract_quotes, missing_quotes  # noqa: E402

def test_real_quote_passes():
    sources = ["Added real-time updates over WebSocket."]
    answer = 'Evidence: "Added real-time updates over WebSocket".'
    assert missing_quotes(answer, sources) == []


def test_invented_quote_fails():
    sources = ["Added real-time updates over WebSocket."]
    answer = 'Evidence: "Led a team of ten engineers across three countries".'
    assert missing_quotes(answer, sources) == ["Led a team of ten engineers across three countries"]


def test_whitespace_bullets_and_case_are_ignored():
    sources = ["- Reviewed code and\n  mentored two junior developers."]
    answer = 'x "reviewed code and mentored two junior developers"'
    assert missing_quotes(answer, sources) == []


def test_short_quotes_are_not_evidence():
    assert extract_quotes('tools: "React" and "Python"') == []


def test_cli_exit_codes(tmp_path):
    script = os.path.join(ROOT, "scripts", "verify_quotes.py")
    src = tmp_path / "src.txt"
    src.write_text("Optimized AG Grid for 10,000+ rows.", encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text('"Optimized AG Grid for 10,000+ rows"', encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text('"Optimized AG Grid for 1,000,000 rows"', encoding="utf-8")
    assert subprocess.run([sys.executable, script, str(good), str(src)]).returncode == 0
    assert subprocess.run([sys.executable, script, str(bad), str(src)]).returncode == 1
