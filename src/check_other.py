from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from keywords import TOPICS, NEG_WORDS

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "voc.db"

@dataclass
class Post:
    url: str
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

def main(limit: int = 50):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT url, title, body FROM posts ORDER BY id DESC LIMIT 500"
        ).fetchall()

    posts = [Post(url=r[0], title=r[1] or "", body=r[2] or "") for r in rows]

    other_posts = []
    neg_cnt = 0
    for p in posts:
        text = (p.title + " " + p.body).strip()
        topic, sc = score_topic(text)
        if sc == 0:
            topic = "OTHER"
        if topic == "OTHER":
            other_posts.append(p)
            if is_negative(text):
                neg_cnt += 1

    print(f"[OTHER] {len(other_posts)} posts (neg={neg_cnt})\n")

    # OTHER 제목 상위 패턴 확인(대충 느낌 잡기)
    head_words = []
    for p in other_posts:
        # 제목 첫 단어만
        w = (p.title.strip().split()[:1] or [""])[0]
        head_words.append(w)
    top_heads = Counter(head_words).most_common(10)
    print("[OTHER title head top10]")
    for w, c in top_heads:
        if w:
            print(f"- {w}: {c}")
    print()

    # 실제 글 목록 출력
    print("[SAMPLE OTHER LIST]")
    for i, p in enumerate(other_posts[:limit], start=1):
        flag = " (NEG)" if is_negative((p.title + " " + p.body)) else ""
        print(f"{i:02d}. {p.title[:60]}{flag}")
        print(f"    {p.url}")

if __name__ == "__main__":
    main()