from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from keywords import TOPICS, NEG_WORDS

QUICK_ACTION = {
    "T4_버그/서버": "장애 공지 템플릿 적용 + 발생 시간대/OS 로그 확인 + 보상 기준 안내",
    "T2_과금/BM": "문제 상품/확률 키워드 수집 → 상품 페이지 이탈/환불 지표 확인 → 안내/구성 A/B 후보 선정",
    "T9_뉴비/온보딩": "초반 7일 가이드(추천 덱/성장 루트) 강화 + 리세 강제 체감 완화(대여/확정 획득 루트)",
    "T3_이벤트/미션": "승리 강제형 미션 점검(누적형/대체 미션) + 보상 기대값 조정",
    "T6_카드/선수": "선수/구종/등급 키워드 TOP 점검 + 사용률 편중/덱 다양성 모니터링",
    "T5_성장/재화": "병목 재화(한돌/재료) 수급 루트 점검 + 강화/파밍 피로 구간 개선 후보 도출",
    "T1_매칭/밸런스": "티어별 승률/연패 구간 모니터링 + 매칭 풀/보정 로직 점검",
    "T7_UI/편의": "반복 동선/일괄 처리 요청 키워드 수집 → QoL 백로그화",
    "T8_운영/정책": "CS/제재/환불 정책 문구 명확화 + 공지/FAQ 업데이트",
}


BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "voc.db"
REPORT_PATH = BASE / "reports" / f"{date.today().isoformat()}.md"


@dataclass
class Post:
    url: str
    title: str
    body: str
    fetched_at: str


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


def highlight_score(p: Post) -> tuple[int, int, int]:
    """
    정렬용 점수(큰 게 우선):
    1) 부정/이슈 우선
    2) 토픽 매칭 강도(키워드 히트 수)
    3) 본문 길이(너무 짧은 글 배제)
    """
    text = f"{p.title} {p.body}".strip()
    topic, topic_hits = score_topic(text)

    neg = 1 if is_negative(text) else 0
    length = len(p.body or "")

    # 운영 중요 토픽 가중치(원하면 조정)
    weight = 0
    if topic in ("T4_버그/서버", "T2_과금/BM", "T3_이벤트/미션"):
        weight = 1

    # tuple 정렬: neg, weight, topic_hits, length
    return (neg, weight, topic_hits, length)


def main():
    today = date.today().isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT url, title, body, fetched_at
            FROM posts
            WHERE date(fetched_at) = ?
            ORDER BY id DESC
            """,
            (today,),
        ).fetchall()

    posts = [Post(url=r[0], title=r[1] or "", body=r[2] or "", fetched_at=r[3] or "") for r in rows]

    # 너무 짧은 글은 하이라이트에서 제외(노이즈 방지)
    posts = [p for p in posts if len((p.title + p.body).strip()) >= 20]

    # 토픽 히트가 너무 낮은 글(애매한 글)은 하이라이트에서 제외
    filtered = []
    for p in posts:
        text = f"{p.title} {p.body}".strip()
        topic, hits = score_topic(text)
        if hits >= 2:   # <- 여기 숫자만 조절하면 됨(2 추천)
            filtered.append(p)
    posts = filtered

    if not posts:
        content = "- 오늘 신규 수집 글이 없습니다.\n"
    else:
        ranked = sorted(posts, key=highlight_score, reverse=True)[:3]

        lines = []
        for i, p in enumerate(ranked, start=1):
            text = f"{p.title} {p.body}".strip()
            topic, hits = score_topic(text)
            if hits == 0:
                topic = "OTHER"
            neg_tag = "🔥" if is_negative(text) else ""
            action = QUICK_ACTION.get(topic, "—")
            lines.append(f"{i}) [{topic}]{neg_tag} {p.title} ({p.url})\n   - Quick Action: {action}")
        content = "\n".join(lines) + "\n"

    md = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else ""
    md = upsert_section(md, "## 오늘 신규 글 하이라이트 (TOP3)", content)
    REPORT_PATH.write_text(md, encoding="utf-8")
    print(f"[OK] wrote highlights to {REPORT_PATH}")


if __name__ == "__main__":
    main()