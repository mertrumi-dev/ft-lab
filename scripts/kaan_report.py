"""One short daily report in simple Turkish: docs/fresh/report-YYYY-MM-DD.md + latest.md.

Written as the last step of scripts/daily.py from things that step already measured
(no extra backtests, read-only on the bot). Stdlib only, so it runs on the Mac.
Each section is built by a small pure function, so the rendering is tested with fake inputs.
"""

import csv
import re
from pathlib import Path

SCAN_ROW = re.compile(r"^(\S+)\s+(.+?)\s+([+-]\d+\.\d+%)\s+(\S+)\s+(\d+%)( \*)?\s*$")
STATE_TR = {
    "ENTRY NOW": "ALIM SİNYALİ",
    "in trend": "trendde (yukarı)",
    "above EMA200, short trend down": "EMA200 üstü, kısa vade aşağı",
    "below EMA200": "EMA200 altında (bekliyor)",
}
BOT_ROWS = (
    "Buy & hold", "Weekly DCA", "Grid bot", "DCA bot (3Commas", "TSMOM", "TrendEma ", "TrendEmaVolTarget ",
    "TrendEmaVolTarget2h", "VolTarget 1h+2h",
)  # fmt: skip


def clean(text: str) -> str:
    """Drop docker noise lines from a captured ft.py output."""
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith(("$ docker", " Container"))).strip()


def core_scan_rows(scan_text: str) -> list[dict]:
    """The bot's 5 coins (rows marked with *) from `ft.py scan` output."""
    rows = []
    for line in scan_text.splitlines():
        m = SCAN_ROW.match(line)
        if m and m.group(6):
            rows.append({"pair": m.group(1), "state": m.group(2).strip(), "vs": m.group(3), "size": m.group(5)})
    return rows


def breadth_rows(path: Path, days: int = 7) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))[-days:]


BOTS_ROW = re.compile(r"^(.*?)\s{2,}(\S+)\s+([+-]?[\d.]+%)\s+([+-]?[\d.]+%)\s+([\d.]+%)\s+(\S+)(\s+<50 trades)?\s*$")
TABLE_HEAD = f"{'Bot':<36}{'İşlem':>7}{'Getiri':>10}{'Yıllık':>10}{'MaxDD':>8}{'Calmar':>8}"


def tidy_bots_row(line: str) -> str:
    """Re-align one bots-table row with a wide name column (long names broke the alignment)."""
    m = BOTS_ROW.match(line)
    if not m:
        return line
    name, trades, ret, cagr, mdd, calmar, few = m.groups()
    return f"{name.strip():<36}{trades:>7}{ret:>10}{cagr:>10}{mdd:>8}{calmar:>8}" + ("  <50 işlem" if few else "")


def bots_rows(bots_text: str) -> list[str]:
    """Only the rows Kaan needs from a `ft.py bots` table (first table; year rows skipped)."""
    out, seen = [], set()
    for line in bots_text.splitlines():
        if line.startswith("Year by year"):
            break
        for key in BOT_ROWS:
            if line.startswith(key) and key not in seen:
                out.append(tidy_bots_row(line.rstrip()))
                seen.add(key)
    return out


def ai_counts(path: Path) -> tuple[int, int]:
    """(views written, views scored). Single source: docs/fresh/ai-scores.csv (written by ft.py ai-score);
    falls back to counting the views in ai-views.md if the CSV does not exist yet."""
    scores = path.with_name("ai-scores.csv")
    if scores.exists():
        with scores.open() as f:
            rows = list(csv.DictReader(f))
        return len(rows), sum(1 for r in rows if r.get("hit", "") != "")
    if not path.exists():
        return 0, 0
    return len([r for r in path.read_text().splitlines() if r.startswith("| 20")]), 0


def chart_reading(text: str) -> list[str]:
    """The reading lines of one `ft.py chart --tr` output (download logs and the closing line dropped)."""
    lines = clean(text).splitlines()
    start = next((i for i, ln in enumerate(lines) if "— günlük grafik" in ln), None)
    if start is None:
        return []
    body = [ln for ln in lines[start:] if ln.strip() and not ln.startswith(("Geçmişin okunması", "$ "))]
    return [f"**{body[0]}**", *body[1:]]


def render(date: str, health: dict, scan_text: str, breadth: list[dict], bots_core: str, bots_gold: str,
           execution_text: str, ai: tuple[int, int], expected_text: str = "", explained: str = "",
           ai_score_text: str = "", charts: list[str] | None = None, forward_text: str = "") -> str:  # fmt: skip
    h = health
    lines = [f"# Günlük rapor {date}", "",
             "Sadece ölçüm. Kurallar bu rapora bakılarak değiştirilmez. Yatırım tavsiyesi değildir.", "",
             "## 1. Bot sağlığı", ""]  # fmt: skip
    lines += [
        f"- Çalışıyor mu: {h.get('status', '?')}",
        f"- Kendi kodundaki hata: {h.get('other_errors', '?')} (bağlantı hatası: {h.get('network_errors', '?')}"
        + (f", en çok {h['network_peak']}" if h.get("network_peak") else "") + ")",
        f"- En uzun bağlantısız süre: {h.get('longest_gap', 'yok')}",
        f"- İşlemler: {h.get('open', 0)} açık, {h.get('closed', 0)} kapanmış, gerçekleşen kâr/zarar {h.get('profit', 0.0):+.2f} USDT",
        f"- Kill switch: zirveden düşüş şu an %{h.get('drawdown', 0.0) * 100:.1f}, en kötü %{h.get('worst', h.get('drawdown', 0.0)) * 100:.1f}"
        " (sınır %20" + ("; TETİKLENDİ, yeni işlem yok, insan bakana kadar)" if h.get("worst", 0.0) >= 0.20 else ")"),
        *(["- Ne yapmalı (R13 eki): en az 14 gün bekle + journal'a yazılı inceleme; adımlar: docs/proposals/kill-switch-restart.md"]
          if h.get("worst", 0.0) >= 0.20 else []),
        f"- Faz 0: {h.get('phase0', '?')}",
        "", "## 2. Botun 5 coini şu an (1 saatlik grafik)", "",
    ]  # fmt: skip
    rows = core_scan_rows(scan_text)
    if rows:
        lines += ["| Coin | Durum | EMA200'e uzaklık | Pozisyon boyutu |", "|---|---|---|---|"]
        lines += [f"| {r['pair']} | {STATE_TR.get(r['state'], r['state'])} | {r['vs']} | {r['size']} |" for r in rows]
    else:
        lines.append("- Tarama sonucu yok.")
    lines += ["", "## 3. Piyasa genişliği (havuzdaki coinlerin yüzde kaçı EMA200 üstünde)", ""]
    if breadth:
        lines += [f"- {b['date']}: %{float(b['breadth']) * 100:.0f} ({b['n_in_trend']} coin trendde, {b['n_entry_now']} alım sinyali)"
                  for b in breadth]  # fmt: skip
    else:
        lines.append("- Henüz kayıt yok.")
    lines += ["", "## 4. Taze veri (testten sonraki gerçek fiyatlar), 5 coin", "",
              "Getiri ve düşüş, taze dilimin başından bugüne. Yıllık = o hızla bir yıl sürseydi."
              " 50'den az işlem = henüz anlamlı değil.", "", "```", TABLE_HEAD]  # fmt: skip
    lines += bots_rows(bots_core) or ["(tablo yok)"]
    lines += ["```"]
    exp = [ln.removeprefix("expected_line: ") for ln in expected_text.splitlines() if ln.startswith("expected_line: ")]
    if exp:
        lines += ["", f"VolTarget beklenen aralıkta mı? {exp[0]}"]
    fwd = [ln.removeprefix("forward_line: ") for ln in forward_text.splitlines() if ln.startswith("forward_line: ")]
    if fwd:
        lines += ["", f"İleriye risk: {fwd[0]}"]
    stress = [ln.removeprefix("forward_stress: ") for ln in forward_text.splitlines() if ln.startswith("forward_stress: ")]
    if stress:
        lines.append(f"Stres (kötü dönem dahil): {stress[0]}")
    gold = [r for r in bots_rows(bots_gold) if r.startswith("TrendEmaVolTarget ")]
    if gold:
        lines += ["", "İzleme (altın dahil 6 coin): ", "```", TABLE_HEAD, *gold, "```"]
    exec_lines = [ln for ln in execution_text.splitlines() if ln.strip() and not ln.startswith(("$ docker", " Container"))]
    lines += ["", "## 5. Emir kalitesi", "", "```", *(exec_lines or ["(rapor yok)"]), "```", "",
              "## 6. Yapay zeka grafik yorumları", ""]  # fmt: skip
    written, scored = ai
    lines.append(f"- Kaydedilen yorum: {written}, puanlanan: {scored}. Bota bağlanması için önce 50+ puanlanmış tahminde"
                 " yazı-tura ve 'hep yukarı'yı geçmesi gerekiyor.")  # fmt: skip
    for ln in ai_score_text.splitlines():
        if ln.startswith("ai_score: "):
            lines.append(f"- Puanlama: {ln.removeprefix('ai_score: ')}")
    body = [ln for ln in explained.splitlines() if ln and not ln.startswith("# ") and not ln.startswith("Sahte para")]
    lines += ["", "## 7. İşlemler (sade dille)", ""]
    lines += body[:15] or ["- Açıklama yok."]
    if len(body) > 15:
        lines.append("- ... tamamı: docs/fresh/trades-explained.md")
    readings = [r for r in (chart_reading(c) for c in charts or []) if r]
    if readings:
        lines += ["", "## 8. Grafik okuma (günlük grafik, sade dille)", ""]
        for r in readings:
            lines += [*r, ""]
        lines.append("Geçmişin okunması, tahmin değil, yatırım tavsiyesi değil.")
    return "\n".join(lines) + "\n"


def write(out_dir: Path, date: str, text: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"report-{date}.md"
    path.write_text(text)
    (out_dir / "latest.md").write_text(text)
    return path
