"""The bot map (docs/learn/00-harita.md) names code by file:line; those references must stay true."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "docs" / "learn" / "00-harita.md"
REF = re.compile(r"^- `([\w./-]+):(\d+)` → `(.+)`$", re.M)


def test_every_line_reference_points_at_the_code_it_quotes():
    refs = REF.findall(MAP.read_text())
    assert len(refs) >= 20
    for path, line, snippet in refs:
        lines = (ROOT / path).read_text().splitlines()
        assert snippet in lines[int(line) - 1], f"{path}:{line} no longer contains {snippet!r}: update the map"


def test_each_part_of_the_bot_has_a_question_and_the_plan_has_seven_days():
    text = MAP.read_text()
    for part in ("Giriş", "Çıkış", "Stop", "Miktar", "Kill switch", "Korumalar"):
        assert re.search(rf"^## \d\. {part}", text, re.M), part
    assert text.count("**Kendi cümlenle cevapla:**") == 6
    assert all(re.search(rf"^\| {day} \|", text, re.M) for day in range(1, 8))
