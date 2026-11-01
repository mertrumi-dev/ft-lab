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
    """(views written, views scored) from docs/fresh/ai-views.md."""
    if not path.exists():
        return 0, 0
    rows = [r for r in path.read_text().splitlines() if r.startswith("| 20")]
    scored = [r for r in rows if r.rstrip("|").split("|")[-1].strip()]
    return len(rows), len(scored)


def render(date: str, health: dict, scan_text: str, breadth: list[dict], bots_core: str, bots_gold: str,
           execution_text: str, ai: tuple[int, int]) -> str:  # fmt: skip
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
        f"- Kill switch: zirveden düşüş %{h.get('drawdown', 0.0) * 100:.1f} (sınır %20)",
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
    gold = [r for r in bots_rows(bots_gold) if r.startswith("TrendEmaVolTarget ")]
    if gold:
        lines += ["", "İzleme (altın dahil 6 coin): ", "```", TABLE_HEAD, *gold, "```"]
    exec_lines = [ln for ln in execution_text.splitlines() if ln.strip() and not ln.startswith(("$ docker", " Container"))]
    lines += ["", "## 5. Emir kalitesi", "", "```", *(exec_lines or ["(rapor yok)"]), "```", "",
              "## 6. Yapay zeka grafik yorumları", ""]  # fmt: skip
    written, scored = ai
    lines.append(f"- Kaydedilen yorum: {written}, puanlanan: {scored}. Bota bağlanması için önce 50+ puanlanmış tahminde"
                 " yazı-tura ve 'hep yukarı'yı geçmesi gerekiyor.")  # fmt: skip
    return "\n".join(lines) + "\n"


def write(out_dir: Path, date: str, text: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"report-{date}.md"
    path.write_text(text)
    (out_dir / "latest.md").write_text(text)
    return path
