from pathlib import Path
from datetime import date

def main():
    base = Path(__file__).resolve().parents[1]  # 프로젝트 루트
    reports_dir = base / "reports"
    reports_dir.mkdir(exist_ok=True)

    today = date.today().isoformat()  # 예: 2026-02-25
    out = reports_dir / f"{today}.md"

    content = f"""# 컴프야 VOC 레이더 리포트
- Date: {today}

## 오늘의 이슈 TOP10

## 급상승 TOP3 (vs 어제)

## Issue → Action 카드 3장
"""
    out.write_text(content, encoding="utf-8")
    print(f"[OK] Wrote report: {out}")

if __name__ == "__main__":
    main()