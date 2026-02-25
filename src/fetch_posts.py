from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, parse_qsl

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "voc.db"
URL_LIST_PATH = BASE_DIR / "data" / "list_urls.txt"


@dataclass
class Post:
    url: str
    created_at: str
    title: str
    body: str
    views: Optional[int] = None
    upvotes: Optional[int] = None


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          url TEXT UNIQUE,
          created_at TEXT,
          title TEXT,
          body TEXT,
          views INTEGER,
          upvotes INTEGER,
          fetched_at TEXT
        );
        """
    )
    conn.commit()


def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_int(s: str) -> Optional[int]:
    if not s:
        return None
    s = re.sub(r"[^\d]", "", s)
    return int(s) if s else None


def fetch_one(url: str, session: requests.Session) -> Optional[Post]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://gall.dcinside.com/",
    }

    r = session.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # 제목: 디시 view 페이지는 보통 title 클래스가 고정적이지만 변형 대비로 후보를 여러 개 둠
    title_el = soup.select_one(".title_subject") or soup.select_one("span.title_subject")
    if not title_el:
        return None
    title = clean_text(title_el.get_text(" ", strip=True))

    # 본문: 여러 후보를 시도
    body_el = (
        soup.select_one(".write_div")
        or soup.select_one("div.write_div")
        or soup.select_one("div.view_content_wrap")
    )
    if not body_el:
        return None
    body = clean_text(body_el.get_text(" ", strip=True))

    # 작성시간: 후보 selector
    time_el = soup.select_one(".gall_date") or soup.select_one("span.gall_date")
    created_at = clean_text(time_el.get_text(" ", strip=True)) if time_el else ""

    # 조회/추천(있으면)
    views_el = soup.select_one(".gall_count") or soup.select_one("span.gall_count")
    up_el = soup.select_one(".gall_reply_num")  # 추천은 페이지마다 다를 수 있어 일단 비워둠

    views = parse_int(views_el.get_text(" ", strip=True)) if views_el else None
    upvotes = None  # 추천 selector는 다음 단계에서 확인 후 추가

    # created_at이 비었으면 URL 파라미터에서라도 보정할 수 없으니 fetched_at로만 남겨도 OK
    if not created_at:
        created_at = ""

    return Post(url=url, created_at=created_at, title=title, body=body, views=views, upvotes=upvotes)


def save_post(conn: sqlite3.Connection, p: Post) -> bool:
    now = datetime.now().isoformat(timespec="seconds")
    try:
        conn.execute(
            """
            INSERT INTO posts (url, created_at, title, body, views, upvotes, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (p.url, p.created_at, p.title, p.body, p.views, p.upvotes, now),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # 이미 저장됨(url UNIQUE)
        return False


def main():
    if not URL_LIST_PATH.exists():
        raise FileNotFoundError(f"Missing {URL_LIST_PATH}. Run fetch_list.py first.")

    urls = [line.strip() for line in URL_LIST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not urls:
        print("[WARN] No URLs in list_urls.txt")
        return

    DB_PATH.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)

        session = requests.Session()
        ok, skipped, failed = 0, 0, 0

        for i, url in enumerate(urls, start=1):
            try:
                post = fetch_one(url, session)
                if not post:
                    failed += 1
                    print(f"[{i:03d}] FAIL parse: {url}")
                else:
                    inserted = save_post(conn, post)
                    if inserted:
                        ok += 1
                        print(f"[{i:03d}] OK saved: {post.title[:30]}...")
                    else:
                        skipped += 1
                        print(f"[{i:03d}] SKIP exists")
            except Exception as e:
                failed += 1
                print(f"[{i:03d}] ERROR {type(e).__name__}: {e}")

            time.sleep(1.5)  # 요청 간격(차단 방지)

        print(f"\n[SUMMARY] saved={ok}, skipped={skipped}, failed={failed}")
        print(f"[DB] {DB_PATH}")


if __name__ == "__main__":
    main()