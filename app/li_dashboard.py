"""📊 링크드인 채용 대시보드 — 쌓인 링크드인 공고(엑셀·배치·가져오기)를 한 화면 차트용으로 모음 (모두 코드 계산).

KPI · 직종 분포 · 직급 분포 · 채용 많은 회사(직종 구성) · 나와 맞는 공고 · 직종별 예상 연봉 · 인터뷰 핵심 키워드 · 날짜별 새 공고 · 근무 형태 · 출처
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import median

from .jobs import JOB_FAMILIES
from .linkedin_jobs import TIERS

FAMS = JOB_FAMILIES + ["기타"]


def build(jobs: list[dict], companies: list[dict], profile: dict, days: int) -> dict:
    """jobs = linkedin_import.analyze() 결과, companies = company_scan.analyze_companies() 결과."""
    my_f = profile.get("desired_family") or profile.get("job_family") or ""
    want = profile.get("expected_salary")
    n = len(jobs)
    fam = Counter(j["family"] for j in jobs)
    new = sum(1 for j in jobs if j.get("is_new"))

    # 직종별: 공고 수 · 새 공고 · 평균 적합도
    families = []
    for f in FAMS:
        js = [j for j in jobs if j["family"] == f]
        if js:
            families.append({"family": f, "n": len(js), "new": sum(1 for j in js if j.get("is_new")),
                             "avg_fit": round(sum(j["fit"]["score"] for j in js) / len(js)), "mine": f == my_f})
    families.sort(key=lambda x: -x["n"])

    tiers = [{"tier": t, "n": sum(1 for j in jobs if j["tier"] == t),
              "mine_family": sum(1 for j in jobs if j["tier"] == t and my_f and j["family"] == my_f)} for t in TIERS]

    top_cos = [{"company": c["company"], "n": c["count"], "new": c["new"], "score": c["score"],
                "families": {f["family"]: f["n"] for f in c["families"]}, "service_job_id": c["service_job_id"]}
               for c in sorted(companies, key=lambda c: (-c["count"], -c["score"]))[:10]]

    top_jobs = [{"title": j["title"], "company": j["company"], "family": j["family"], "tier": j["tier"], "score": j["fit"]["score"],
                 "parts": j["fit"]["parts"], "url": j.get("url"), "is_new": j.get("is_new", False),
                 "salary": j["salary"], "job_id": j.get("job_id")} for j in jobs[:8]]

    # 직종별 예상 연봉 (공고마다 범위의 중간값 → 직종 안에서 최저·중간·최고)
    sal = []
    for f in FAMS:
        js = [j for j in jobs if j["family"] == f]
        if js:
            mids = [(j["salary"]["min"] + j["salary"]["max"]) / 2 for j in js]
            sal.append({"family": f, "lo": min(j["salary"]["min"] for j in js), "hi": max(j["salary"]["max"] for j in js),
                        "mid": round(median(mids) / 100) * 100, "n": len(js),
                        "posted": sum(1 for j in js if j["salary"]["kind"] == "posted"), "mine": f == my_f})
    sal.sort(key=lambda x: -x["mid"])

    kw = Counter(x["keyword"] for j in jobs for x in j.get("interview", [])
                 if not my_f or j["family"] == my_f)   # 내 직종이 있으면 내 직종 공고의 키워드만
    keywords = [{"keyword": k, "n": c} for k, c in kw.most_common(12)]

    today = date.today()
    per_day = Counter(j.get("first_seen") or j.get("date") or "" for j in jobs if j.get("is_new") or j.get("first_seen"))
    daily = []
    for i in range(min(days, 30) - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        daily.append({"date": d, "n": per_day.get(d, 0)})

    work = Counter((j.get("work_type") or "정보 없음").strip().title() for j in jobs)
    sources = Counter(j.get("source_name") or "가져온 공고" for j in jobs)
    mine_n = fam.get(my_f, 0) if my_f else 0
    mine_sal = next((s for s in sal if s["family"] == my_f), None)
    return {
        "kpi": {"jobs": n, "new": new, "companies": len(companies), "mine": mine_n, "mine_pct": round(100 * mine_n / n) if n and my_f else None,
                "good": sum(1 for j in jobs if j["fit"]["score"] >= 70), "my_family": my_f,
                "mine_salary_mid": mine_sal["mid"] if mine_sal else None, "want": want,
                "best": top_jobs[0] if top_jobs else None},
        "families": families, "tiers": tiers, "companies": top_cos, "top_jobs": top_jobs, "salary": sal,
        "keywords": keywords, "daily": daily, "work_types": [{"k": k, "n": v} for k, v in work.most_common(5)],
        "sources": [{"k": k, "n": v} for k, v in sources.most_common()],
        "table": [{"rank": j["rank"], "title": j["title"], "company": j["company"], "family": j["family"], "tier": j["tier"],
                   "fit": j["fit"]["score"], "sal": f"{j['salary']['min']:,}~{j['salary']['max']:,}", "new": j.get("is_new", False),
                   "work_type": j.get("work_type", ""), "url": j.get("url", "")} for j in jobs],
    }
