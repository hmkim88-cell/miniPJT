"""하루 한 번 도는 공고 배치.

  실행:  ..\\.venv\\Scripts\\python -m app.batch ats                     # 회사 공개 채용 페이지(Greenhouse·Lever·Ashby) 가져오기
         ..\\.venv\\Scripts\\python -m app.batch linkedin-file 결과.json   # 에이전트 스캔 결과 파일을 넣기 (JSON 또는 CSV)
  예약:  Windows 작업 스케줄러에 매일 07:00 위 명령 등록 (SERVICE.md 14-4) 또는 .env BATCH_TIME=07:00 → 서버가 켜져 있는 동안 매일 실행

회사 목록: data/ats_sources.json  예) [{"ats": "greenhouse", "slug": "회사아이디", "company": "회사 이름"}]
  - slug는 그 회사 채용 페이지 주소에 있는 아이디 (boards.greenhouse.io/<slug> · jobs.lever.co/<slug> · jobs.ashbyhq.com/<slug>)
  - 공개 API라 로그인·키가 필요 없고, 회사가 채용 페이지에 올리라고 연 주소만 씀
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from . import jobfeed

CONFIG = Path(__file__).resolve().parents[1] / "data" / "ats_sources.json"
KOREA = re.compile(r"korea|seoul|서울|대한민국|한국|pangyo|판교|busan|부산", re.I)
UA = {"User-Agent": "careerfate-batch/1.0 (job board reader)"}


def _get(url: str):
    import httpx
    r = httpx.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_ats(ats: str, slug: str, company: str, korea_only: bool = True, getter=_get) -> list[dict]:
    """회사 공개 채용 API → 공통 모양. korea_only면 근무지에 한국이 들어간 공고만."""
    out = []
    if ats == "greenhouse":
        for j in getter(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").get("jobs", []):
            out.append({"job_id": j.get("id"), "title": j.get("title"), "company": company, "location": (j.get("location") or {}).get("name", ""),
                        "url": j.get("absolute_url"), "posted": (j.get("updated_at") or "")[:10]})
    elif ats == "lever":
        for j in getter(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
            cat = j.get("categories") or {}
            out.append({"job_id": j.get("id"), "title": j.get("text"), "company": company, "location": cat.get("location", ""),
                        "work_type": j.get("workplaceType") or cat.get("commitment", ""), "url": j.get("hostedUrl"),
                        "posted": datetime.fromtimestamp((j.get("createdAt") or 0) / 1000).strftime("%Y-%m-%d") if j.get("createdAt") else ""})
    elif ats == "ashby":
        for j in getter(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", []):
            out.append({"job_id": j.get("id"), "title": j.get("title"), "company": company, "location": j.get("location", ""),
                        "work_type": j.get("workplaceType", ""), "url": j.get("jobUrl"), "posted": (j.get("publishedAt") or "")[:10]})
    else:
        raise ValueError(f"모르는 ats: {ats}")
    return [x for x in out if not korea_only or KOREA.search(x.get("location") or "")]


def run_ats(getter=_get) -> list[dict]:
    if not CONFIG.exists():
        return [{"source": "ats", "error": f"{CONFIG.name}이 없어요 — 회사 목록을 먼저 넣어 주세요"}]
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    logs = []
    for c in cfg:
        try:
            items = fetch_ats(c["ats"], c["slug"], c.get("company") or c["slug"], c.get("korea_only", True), getter)
            log = jobfeed.ingest(items, c["ats"])
            logs.append({**log, "company": c.get("company") or c["slug"]})
        except Exception as e:  # noqa: BLE001  한 회사가 실패해도 나머지는 계속
            logs.append({"source": c.get("ats"), "company": c.get("company") or c.get("slug"), "error": f"{type(e).__name__}: {str(e)[:120]}"})
        time.sleep(1)   # 회사 서버에 부담 주지 않게 천천히
    return logs


def read_scan_file(path: str) -> list[dict]:
    """에이전트 스캔 결과: JSON(리스트 또는 {items:[…]}) 또는 CSV."""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    if p.suffix.lower() == ".csv":
        return list(csv.DictReader(io.StringIO(text)))
    data = json.loads(text)
    return data.get("items", []) if isinstance(data, dict) else data


def start_scheduler() -> None:
    """.env BATCH_TIME=HH:MM 이면 서버가 켜져 있는 동안 매일 그 시각에 ATS 배치 실행 (한 번만)."""
    at = os.getenv("BATCH_TIME", "").strip()
    if not re.fullmatch(r"\d{2}:\d{2}", at):
        return

    def loop():
        done = None
        while True:
            now = datetime.now()
            if now.strftime("%H:%M") == at and done != now.date():
                done = now.date()
                run_ats()
            time.sleep(30)
    threading.Thread(target=loop, daemon=True, name="daily-batch").start()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "ats":
        for lg in run_ats():
            print(lg)
    elif cmd == "linkedin-file" and len(sys.argv) > 2:
        print(jobfeed.ingest(read_scan_file(sys.argv[2]), "linkedin-scan"))
    else:
        print(__doc__)
