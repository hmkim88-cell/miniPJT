"""공고 피드 — 하루 한 번 배치로 들어온 공고를 쌓고(DB), 중복을 빼고, '오늘 새로 나온 공고'를 표시.

들어오는 곳 (서버는 링크드인에 접속하지 않음):
  · linkedin-scan : 사용자가 직접 돌리는 브라우저 에이전트(예: Claude 'linkedin-job-scan' 스킬, 본인 로그인 · 읽기만)가
                    매일 정해진 시각에 읽은 결과(JSON/CSV)를 POST /api/batch/linkedin-scan 으로 보냄 (BATCH_TOKEN 필요)
  · ats           : 외국계 회사들이 공개한 채용 페이지 API (Greenhouse · Lever · Ashby) — app/batch.py 가 매일 직접 가져옴
  · linkedin-export / linkedin-alert : 링크드인 데이터 내보내기 · 채용 알림 메일 (화면에서 올린 것, 원하면 피드에도 저장)

저장: careerfate_records 표에 kind='feed' (id = 출처+공고번호의 crc32). first_seen(처음 본 날) · last_seen(마지막으로 본 날) · runs(본 횟수)
"""
from __future__ import annotations

import re
import zlib
from datetime import date, datetime

from . import store

SOURCES = {"linkedin-excel": "링크드인 구인 엑셀", "linkedin-scan": "링크드인 (에이전트 스캔)", "greenhouse": "Greenhouse 채용 페이지", "lever": "Lever 채용 페이지",
           "ashby": "Ashby 채용 페이지", "linkedin-export": "링크드인 데이터 내보내기", "linkedin-alert": "링크드인 채용 알림"}
_LI = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?#\s]*-)?(\d{6,})", re.I)


def _key(source: str, job_id: str) -> int:
    return zlib.crc32(f"{source}:{job_id}".encode()) & 0x7FFFFFFF


def normalize(item: dict, source: str) -> dict | None:
    """에이전트·API마다 다른 이름의 칸을 하나로. 직무명이 없으면 버림."""
    g = lambda *ks: next((str(item[k]).strip() for k in ks if item.get(k) not in (None, "")), "")
    title = g("title", "job_title", "Job Title", "name", "text")
    if not title:
        return None
    url = g("url", "link", "job_url", "Job Url", "hostedUrl", "absolute_url", "jobUrl")
    m = _LI.search(url)
    job_id = g("job_id", "id", "jobId") or (m.group(1) if m else "") or str(zlib.crc32((title + g("company")).encode()))
    if m:
        url = f"https://www.linkedin.com/jobs/view/{m.group(1)}/"
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[;,|]", tags) if t.strip()]
    alumni = g("alumni", "alumni_count")
    return {"source": source, "source_name": SOURCES.get(source, source), "job_id": str(job_id)[:40], "title": title[:160],
            "company": g("company", "company_name", "Company Name", "org")[:120], "location": g("location", "loc", "Location")[:120],
            "work_type": g("work_type", "workplace", "workplaceType", "type")[:40], "posted": g("posted", "posting_age", "posted_at", "updated_at")[:40],
            "tags": [str(t)[:40] for t in tags][:6], "alumni": int(re.sub(r"\D", "", alumni) or 0) if alumni else 0, "url": url[:400],
            # 엑셀처럼 칸이 더 있으면 함께 (분석 정확도 ↑)
            "description": g("description")[:8000], "seniority": g("seniority")[:60], "salary_text": g("salary_text", "salary")[:120],
            "employment": g("employment")[:40], "industry": g("industry")[:80], "applicants": g("applicants")[:20]}


def ingest(items: list[dict], source: str, run_at: str | None = None) -> dict:
    """배치 한 번 결과를 저장. 처음 보는 공고는 new, 이미 본 공고는 last_seen만 갱신."""
    today = (run_at or date.today().isoformat())[:10]
    have = {(_key(x["source"], x["job_id"])): x for x in store.load("feed")}
    new = seen = skipped = 0
    new_ids: list[str] = []
    for raw in items[:500]:
        it = normalize(raw, source)
        if not it:
            skipped += 1
            continue
        k = _key(source, it["job_id"])
        old = have.get(k)
        if old:
            old.update({**it, "first_seen": old["first_seen"], "last_seen": today, "runs": old.get("runs", 1) + 1})
            store.save("feed", k, old); seen += 1
        else:
            rec = {**it, "key": k, "first_seen": today, "last_seen": today, "runs": 1}
            store.save("feed", k, rec); have[k] = rec; new += 1; new_ids.append(it["job_id"])
    log = {"source": source, "run_at": run_at or datetime.now().strftime("%Y-%m-%d %H:%M"), "new": new, "seen": seen, "skipped": skipped,
           "total": new + seen, "new_ids": new_ids[:500]}
    runs = [x for x in store.load("feedrun")]
    store.save("feedrun", len(runs) + 1, log)
    return log


def feed(days: int = 7) -> dict:
    """최근 N일 안에 본 공고 + 마지막 배치 기록."""
    today = date.today()
    items = [x for x in store.load("feed") if (today - date.fromisoformat(x["last_seen"])).days < days]
    runs = sorted(store.load("feedrun"), key=lambda r: r["run_at"], reverse=True)
    last = runs[0] if runs else None
    for x in items:
        x["is_new"] = x["first_seen"] == (last["run_at"][:10] if last else today.isoformat())
    return {"items": items, "last_run": last, "runs": runs[:10]}
