from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from keywords import TOPICS, NEG_WORDS

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "voc.db"
REPORT_PATH = BASE / "reports" / f"{date.today().isoformat()}.md"


@dataclass
class Row:
    fetched_at: str
    title: str
    body: str


def score_topic(text: str) -> tuple[str, int]:
    best_topic = "OTHER"
    best_score = 0
    for topic, kws in TOPICS.items():
        s = 0
        for kw in kws:
            if kw in text:
                s += 1
        if s > best_score:
            best_topic, best_score = topic, s
    return best_topic, best_score


def upsert_section(md: str, header: str, content: str) -> str:
    if header not in md:
        return md.rstrip() + "\n\n" + header + "\n\n" + content

    before, rest = md.split(header, 1)
    rest = rest.lstrip("\n")
    idx = rest.find("\n## ")
    if idx == -1:
        new_rest = "\n" + content
    else:
        new_rest = "\n" + content + "\n" + rest[idx + 1 :]
    return before.rstrip() + "\n\n" + header + new_rest


def topic_counts_for_date(conn: sqlite3.Connection, ymd: str) -> Counter:
    rows = conn.execute(
        """
        SELECT fetched_at, title, body
        FROM posts
        WHERE date(fetched_at) = ?
        """,
        (ymd,),
    ).fetchall()

    c = Counter()
    for _, title, body in rows:
        text = f"{title or ''} {body or ''}".strip()
        topic, sc = score_topic(text)
        if sc == 0:
            topic = "OTHER"
        c[topic] += 1
    return c


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError("data/voc.db not found. Run fetch_posts.py first.")
    if not REPORT_PATH.exists():
        raise FileNotFoundError("Report not found. Run report.py/analyze.py first.")

    with sqlite3.connect(DB_PATH) as conn:
        days = conn.execute(
            "SELECT DISTINCT date(fetched_at) as d FROM posts ORDER BY d DESC"
        ).fetchall()
        days = [d[0] for d in days if d and d[0]]

        if len(days) < 2:
            content = "- 어제 데이터가 없어 급상승 계산 불가 (내일 수집 후 자동 계산)\n"
            md = REPORT_PATH.read_text(encoding="utf-8")
            md = upsert_section(md, "## 급상승 TOP3 (vs 어제)", content)
            REPORT_PATH.write_text(md, encoding="utf-8")
            print("[OK] wrote placeholder (need 2 days of data)")
            return

        today_ymd = days[0]
        yday_ymd = days[1]

        c_today = topic_counts_for_date(conn, today_ymd)
        c_yday = topic_counts_for_date(conn, yday_ymd)

    # OTHER는 노이즈라 급상승에서 제외 추천
    topics = set(c_today.keys()) | set(c_yday.keys())
    topics.discard("OTHER")

    deltas = []
    for t in topics:
        delta = c_today.get(t, 0) - c_yday.get(t, 0)
        deltas.append((t, delta, c_today.get(t, 0), c_yday.get(t, 0)))

    deltas.sort(key=lambda x: x[1], reverse=True)
    top3 = deltas[:3]

    lines = [f"- 비교 기준: {today_ymd} vs {yday_ymd}"]
    if not top3 or top3[0][1] <= 0:
        lines.append("- 급증 토픽 없음(증가량 ≤ 0)")
    else:
        for i, (t, d, ct, cy) in enumerate(top3, start=1):
            lines.append(f"{i}) {t}: +{d} (오늘 {ct} / 어제 {cy})")

    content = "\n".join(lines) + "\n"

    md = REPORT_PATH.read_text(encoding="utf-8")
    md = upsert_section(md, "## 급상승 TOP3 (vs 어제)", content)
    REPORT_PATH.write_text(md, encoding="utf-8")
    print(f"[OK] wrote trending TOP3 to {REPORT_PATH}")


if __name__ == "__main__":
    main()