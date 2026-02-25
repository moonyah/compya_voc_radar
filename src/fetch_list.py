from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup


BASE = "https://gall.dcinside.com"
LIST_URL = "https://gall.dcinside.com/mgallery/board/lists/?id=com2usbaseball&page=1"

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "list_urls.txt"


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }

    r = requests.get(LIST_URL, headers=headers, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # 글 링크는 보통 /mgallery/board/view/?id=...&no=... 형태로 들어있음
    urls = []

    # 디시 목록은 보통 글 1개 = tr 1개
    for tr in soup.select("tr.ub-content.us-post"):
        # 말머리/분류(공지, AD, 설문, 일반 등)가 들어있는 칸
        subj_el = tr.select_one("td.gall_subject")
        subj = subj_el.get_text(strip=True) if subj_el else ""

        # 공지/AD/설문/갤클 제외
        if subj in ("공지", "AD", "설문", "갤클"):
            continue

        a = tr.select_one('a[href*="/mgallery/board/view/"]')
        if not a:
            continue

        href = a.get("href", "").strip()
        if not href:
            continue

        full = urljoin(BASE, href)

        # 같은 글 중복 방지: t=cv 같은 파라미터 제거하고 id/no/page만 남김
        sp = urlsplit(full)
        q = dict(parse_qsl(sp.query, keep_blank_values=True))
        keep = {k: q[k] for k in ["id", "no", "page"] if k in q}
        clean_query = urlencode(keep)
        full = urlunsplit((sp.scheme, sp.netloc, sp.path, clean_query, ""))

        if full not in urls:
            urls.append(full)

    # 상위 30개만
    urls = urls[:30]

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")

    print(f"[OK] total found: {len(urls)}")
    print(f"[OK] saved to: {OUT_PATH}")
    if urls:
        print("[SAMPLE]")
        for u in urls[:5]:
            print(" -", u)

    # 예의상 (다음 단계에서 상세 수집 때 더 중요)
    time.sleep(1.0)


if __name__ == "__main__":
    main()