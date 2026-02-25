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


def is_negative(text: str) -> bool:
    return any(w in text for w in NEG_WORDS)


def render_top10_table(topic_counts: Counter, topic_neg: Counter) -> str:
    items = [(t, c) for t, c in topic_counts.items() if t != "OTHER"]
    items.sort(key=lambda x: x[1], reverse=True)
    top = items[:10]
    lines = [
        "| Rank | Topic | Volume | NegRatio |",
        "|---:|---|---:|---:|",
    ]
    for i, (topic, vol) in enumerate(top, start=1):
        neg_ratio = (topic_neg[topic] / vol) if vol else 0.0
        lines.append(f"| {i} | {topic} | {vol} | {neg_ratio:.2f} |")
    return "\n".join(lines) + "\n"


def upsert_section(md: str, header: str, content: str) -> str:
    # header(예: "## 오늘의 이슈 TOP10") 아래 내용을 교체
    if header not in md:
        return md.rstrip() + "\n\n" + header + "\n\n" + content

    before, rest = md.split(header, 1)
    rest = rest.lstrip("\n")

    # 다음 섹션(## ) 시작 전까지를 잘라 교체
    idx = rest.find("\n## ")
    if idx == -1:
        new_rest = "\n" + content
    else:
        new_rest = "\n" + content + "\n" + rest[idx + 1 :]

    return before.rstrip() + "\n\n" + header + new_rest


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError("data/voc.db not found. Run fetch_posts.py first.")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT title, body FROM posts ORDER BY id DESC LIMIT 500").fetchall()

    data = [Row(title=r[0] or "", body=r[1] or "") for r in rows]

    topic_counts = Counter()
    topic_neg = Counter()

    for r in data:
        text = (r.title + " " + r.body).strip()
        topic, sc = score_topic(text)
        if sc == 0:
            topic = "OTHER"
        topic_counts[topic] += 1
        if is_negative(text):
            topic_neg[topic] += 1

    # 리포트 파일 없으면 기본 뼈대 생성
    if not REPORT_PATH.exists():
        REPORT_PATH.write_text(
            f"# 컴프야 VOC 레이더 리포트\n- Date: {date.today().isoformat()}\n\n"
            "## 오늘의 이슈 TOP10\n\n"
            "## 급상승 TOP3 (vs 어제)\n\n"
            "## Issue → Action 카드 3장\n",
            encoding="utf-8",
        )

    md = REPORT_PATH.read_text(encoding="utf-8")

    top10_table = render_top10_table(topic_counts, topic_neg)
    total = sum(topic_counts.values())
    noise = topic_counts.get("OTHER", 0)
    noise_ratio = noise / total if total else 0
    noise_line = f"- Noise(OTHER): {noise}/{total} ({noise_ratio:.2f})\n"
    md = upsert_section(md, "## 오늘의 이슈 TOP10", top10_table + "\n" + noise_line)
    
    REPORT_PATH.write_text(md, encoding="utf-8")
    print(f"[OK] wrote TOP10 to {REPORT_PATH}")


if __name__ == "__main__":
    main()