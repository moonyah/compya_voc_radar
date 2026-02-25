from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from keywords import TOPICS, NEG_WORDS


BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "voc.db"
REPORT_PATH = BASE / "reports" / f"{date.today().isoformat()}.md"


@dataclass
class Post:
    title: str
    body: str
    url: str


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


TEMPLATES = {
    "T2_과금/BM": {
        "hyp": [
            "확률/패키지 가치 체감이 낮아 불만이 누적되는 구간이 있다.",
            "구매 단계(노출→구성 확인→결제)에서 납득 가능한 ‘기대값’ 정보가 부족하다.",
        ],
        "act": [
            "패키지/확률형 상품에 ‘기대값(평균 소요, 획득 확률 구간)’ 안내 강화 + 비교 UI 제공",
            "불만 키워드가 많이 나오는 상품을 대상으로 A/B로 가격/구성(보장, 천장)을 조정",
        ],
        "kpi": ["결제 전환율", "환불/문의 비율", "상품 페이지 이탈률"],
    },
    "T4_버그/서버": {
        "hyp": [
            "특정 모드/시간대에 접속/매치 관련 오류가 집중된다.",
            "단말/OS(특히 iOS 업데이트) 의존 이슈가 있다.",
        ],
        "act": [
            "에러 로그에 모드/OS/시간대 태그를 붙여 재현률 높은 Top 이슈부터 핫픽스",
            "점검/장애 공지 템플릿 표준화 + 보상 정책(기준) 명확화",
        ],
        "kpi": ["크래시율", "접속 실패율", "CS 티켓(오류) 건수"],
    },
    "T6_카드/선수": {
        "hyp": [
            "특정 선수/구종/등급 관련 체감 이슈(성능/획득 난이도)가 반복된다.",
            "메타 고착으로 ‘써야 하는 선수’가 고정되는 구간이 있다.",
        ],
        "act": [
            "문제 키워드(선수명/구종/등급) 빈도 Top을 주간 밸런스 점검 리스트로 운영",
            "획득 난이도(교환/이벤트) 루트를 보완해 선택지가 생기게 조정",
        ],
        "kpi": ["특정 카드 사용률 편중", "상위티어 덱 다양성", "카드 관련 불만 글 비중"],
    },
    "T5_성장/재화": {
        "hyp": [
            "한돌/강화/재화 소모 구간에서 성장 체감이 급감한다.",
            "재화 루프(수급→소비)가 반복 피로를 만든다.",
        ],
        "act": [
            "성장 병목 구간(한돌/재료) 수급 루트 추가(주간 퀘스트/교환소) + 스킵/일괄 강화 개선",
            "성장 실패/랜덤 요소(확률) 체감 완화: 누적 보정/보장 도입",
        ],
        "kpi": ["성장 구간 이탈률", "일일 플레이타임", "재화 부족 관련 글 비중"],
    },
    "T9_뉴비/온보딩": {
        "hyp": [
            "리세/계정삭제 같은 ‘초반 최적화’가 사실상 강제되는 구조일 수 있다.",
            "초반 가이드/추천 루트가 부족해 시행착오가 커진다.",
        ],
        "act": [
            "초반 7일 온보딩 미션에 ‘추천 덱/성장 루트/리세 필요성 완화’ 가이드를 포함",
            "뉴비 전용 교환/대여 시스템(기간제 카드)로 초반 진입장벽 완화",
        ],
        "kpi": ["D1/D7 리텐션", "튜토리얼 이탈률", "뉴비 질문 글 비중"],
    },
    "T3_이벤트/미션": {
        "hyp": [
            "미션이 ‘의무 숙제’로 느껴지는 구간이 있고, 특정 조건(승리 등)이 스트레스를 만든다.",
            "보상 기대값이 낮아 참여 동기가 약해진다.",
        ],
        "act": [
            "승리 강제형 미션을 누적형(플레이/득점/이닝)으로 치환 + 대체 미션 제공",
            "보상 구조를 ‘핵심 재화/성장’에 더 직접 연결(교환소/월간 보상 강화)",
        ],
        "kpi": ["미션 완료율", "이벤트 참여율", "이벤트 기간 리텐션"],
    },
}


def make_cards(posts_by_topic: dict[str, list[Post]], top_topics: list[str]) -> str:
    blocks = []
    for idx, topic in enumerate(top_topics[:3], start=1):
        sample = posts_by_topic.get(topic, [])[:2]
        evidence = "\n".join([f"- {p.title} ({p.url})" for p in sample]) if sample else "- (sample 없음)"

        tpl = TEMPLATES.get(topic, None)
        if tpl:
            hyp_list = tpl["hyp"]
            act_list = tpl["act"]
            kpi_list = tpl["kpi"]
        else:
            hyp_list = ["(가설 템플릿 없음: 키워드 보강 필요)"]
            act_list = ["(액션 템플릿 없음)"]
            kpi_list = ["(KPI 템플릿 없음)"]

        # 카드 상단 요약(한 줄)
        headline = act_list[0]

        sep = "---\n" if idx > 1 else ""
        blocks.append(
            f"{sep}"
            f"### 카드 {idx}: {topic}\n"
            f"**한 줄 결론:** {headline}\n\n"
            f"**Evidence (근거)**\n{evidence}\n\n"
            f"**Hypothesis (가설)**\n" + "\n".join([f"- {h}" for h in hyp_list]) + "\n\n"
            f"**Action (액션)**\n" + "\n".join([f"- {a}" for a in act_list]) + "\n\n"
            f"**KPI (검증지표)**\n" + "\n".join([f"- {k}" for k in kpi_list]) + "\n"
        )
    return "\n".join(blocks).strip() + "\n"


def main():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT url, title, body FROM posts ORDER BY id DESC LIMIT 500"
        ).fetchall()

    posts = [Post(url=r[0], title=r[1] or "", body=r[2] or "") for r in rows]

    topic_counts = Counter()
    posts_by_topic = defaultdict(list)

    for p in posts:
        text = (p.title + " " + p.body).strip()
        topic, sc = score_topic(text)
        if sc == 0:
            topic = "OTHER"
        topic_counts[topic] += 1
        posts_by_topic[topic].append(p)

    # OTHER 제외한 상위 토픽 3개
    items = [(t, c) for t, c in topic_counts.items() if t != "OTHER"]
    items.sort(key=lambda x: x[1], reverse=True)
    top_topics = [t for t, _ in items[:3]]

    cards_md = make_cards(posts_by_topic, top_topics)

    md = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else ""
    md = upsert_section(md, "## Issue → Action 카드 3장", cards_md)
    REPORT_PATH.write_text(md, encoding="utf-8")

    print(f"[OK] wrote action cards to {REPORT_PATH}")
    print("[TOPICS]", top_topics)


if __name__ == "__main__":
    main()