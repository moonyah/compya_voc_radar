# Com2usProYagu VOC Radar (DCInside)

DCInside(디시인사이드) **컴투스프로야구 갤러리** 게시글(제목/본문)을 수집해  
**토픽 분류 → 노이즈(잡담) 분리 → 운영 리포트 자동 생성**까지 수행하는 VOC 레이더입니다.

## What it does

- 게시글 수집: 최신 리스트에서 글 URL 수집 → 상세 페이지에서 **제목/본문** 저장(SQLite)
- VOC 분류: 토픽 키워드 사전 기반으로 분류 (예: 버그/서버, 과금/BM, 뉴비/온보딩 등)
- 리포트 자동 생성(마크다운)
  - **오늘의 이슈 TOP10** (Noise(OTHER) 비율 포함)
  - **Issue → Action 카드 3장** (Evidence → Hypothesis → Action → KPI)
  - **오늘 신규 글 하이라이트 TOP3** (+ Quick Action)
  - **급상승 TOP3 (vs 어제)** _(데이터가 2일 이상 쌓이면 자동 계산)_

## Project structure

```bash
compya_voc_radar/
data/
    voc.db # 수집 데이터(SQLite)
    list_urls.txt # 최신 글 URL 목록
reports/
    YYYY-MM-DD.md # 일일 리포트
src/
    fetch_list.py # 최신 글 URL 수집
    fetch_posts.py # 글 상세 수집 → DB 저장
    analyze.py # TOP10/Noise 리포트 생성
    action_cards.py # Issue→Action 카드 3장 생성
    trending.py # 전일 대비 급상승 TOP3
    highlights.py # 오늘 신규 글 하이라이트 TOP3 (+ Quick Action)
    keywords.py # 토픽 키워드/부정 키워드 사전
run_daily.sh # 원클릭 실행 스크립트
```

## Setup

### 1) 가상환경 생성/활성화

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) 패키지 설치

```bash
pip install -r requirements.txt
```

## Run (Daily)

### 원클릭 실행:

```bash
./run_daily.sh
```

### 실행 결과:

- data/voc.db에 신규 글이 누적 저장됩니다. (중복은 자동 SKIP)
- reports/YYYY-MM-DD.md 리포트가 생성/갱신됩니다.

## Tuning (키워드 개선)

분류 정확도를 높이려면 src/keywords.py의 토픽 키워드를 보강하세요.

- TOPICS: 토픽별 키워드 목록
- NEG_WORDS: 부정/불만 감지 키워드 목록 (하이라이트 우선순위에 영향)

## Notes

- 급상승 TOP3는 서로 다른 날짜의 데이터가 최소 2일치 이상 있어야 계산됩니다.
- 커뮤니티 글 특성상 잡담/짤글이 많아 OTHER가 발생할 수 있으며, 리포트에서 Noise 비율로 명시합니다.
