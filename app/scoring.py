"""매칭률 = ① 커리어 34% + ② 기대 연봉·직급 33% + ③ 사주 인연 33% (사용자 결정).

나이는 쓰지 않습니다. 경력 연차와 직급 레벨만 봅니다.
"""
from __future__ import annotations

from .jobs import JOBS, LEVELS
from .saju import affinity, affinity_story

WEIGHTS = {"career": 0.34, "pay": 0.33, "affinity": 0.33}


def _norm(s: str) -> str:
    return s.lower().replace(" ", "").replace(".", "").replace("-", "")


def career(profile: dict, job: dict) -> dict:
    """① 일한 커리어 매칭: 기술 70 + 경력 연차 30 = 100점."""
    mine = {_norm(s) for s in profile.get("skills", [])}
    matched = [s for s in job["skills"] if _norm(s) in mine]
    missing = [s for s in job["skills"] if s not in matched]
    skill = round(70 * len(matched) / len(job["skills"]))

    years = profile.get("years", 0) or 0
    lo, hi = job["years_min"], job["years_max"]
    if lo <= years <= hi:
        yr, yr_note = 30, f"경력 {years}년 · 요구 {lo}~{hi}년에 부합"
    elif years > hi:
        yr, yr_note = 22, f"경력 {years}년 · 요구({lo}~{hi}년)보다 많음"
    elif lo - years <= 1:
        yr, yr_note = 18, f"경력 {years}년 · 요구({lo}~{hi}년)에 1년 이내 부족"
    else:
        yr, yr_note = 4, f"경력 {years}년 · 요구({lo}~{hi}년)에 {lo - years}년 부족"

    return {"score": skill + yr, "skill": skill, "yr": yr, "matched": matched, "missing": missing,
            "notes": [f"기술 {len(matched)}/{len(job['skills'])}개 일치", yr_note]}


def pay_level(profile: dict, job: dict) -> dict:
    """② 기대 연봉 60 + 희망 직급 40 = 100점."""
    exp = profile.get("expected_salary")
    lo, hi = job["salary_min"], job["salary_max"]
    if not exp:
        sal, s_note = 45, "기대 연봉 미입력 (중간 점수)"
    elif exp <= hi:
        sal = 60
        s_note = (f"기대 {exp:,}만 · 공고 {lo:,}~{hi:,}만 범위 안" if exp >= lo
                  else f"기대 {exp:,}만 · 공고 하한보다 낮음 (협상 여지 큼)")
    else:
        over = (exp - hi) / hi
        sal = 40 if over <= 0.10 else 20 if over <= 0.20 else 5
        s_note = f"기대 {exp:,}만 · 공고 상한보다 {round(over * 100)}% 높음"

    want = profile.get("desired_level") or profile.get("level", "주니어")
    gap = abs(LEVELS.index(job["level"]) - LEVELS.index(want)) if want in LEVELS else 2
    lv = {0: 40, 1: 20}.get(gap, 0)
    l_note = f"희망 {want} · 공고 {job['level']}" + (" 일치" if gap == 0 else f" ({gap}단계 차이)")
    return {"score": sal + lv, "sal": sal, "lv": lv, "notes": [s_note, l_note]}


def match_job(profile: dict, saju: dict, job: dict) -> dict:
    c = career(profile, job)
    p = pay_level(profile, job)
    a = affinity(saju, job["deadline"])
    rate = round(WEIGHTS["career"] * c["score"] + WEIGHTS["pay"] * p["score"] + WEIGHTS["affinity"] * a["score"])
    # 합격 가능성: 매칭률을 5~95% 범위로 옮긴 추정치 (실제 통계 아님)
    return {"job": job, "career": c, "pay": p, "affinity": a,
            "total": rate, "pass_rate": round(5 + rate * 0.9)}


def fate_ranking(saju: dict) -> list[dict]:
    """사주만으로 본 '이직 인연' %: 지금 올라와 있는 모든 공고 회사와의 인연 점수 순위.
    (커리어·연봉과 무관한 순수 사주 인연 = 매칭률 ③과 같은 값)"""
    out = []
    for job in JOBS:
        a = affinity(saju, job["deadline"])
        out.append({"job_id": job["id"], "company": job["company"], "hq": job["hq"], "title": job["title"],
                    "deadline": job["deadline"], "deadline_gz": a["deadline_gz"],
                    "percent": a["score"], "notes": a["notes"],
                    "story": affinity_story(saju, job["deadline"]),   # 왜 인연이 높은가 (내 사주 여러 관점)
                    "info": job.get("info")})                          # 성장률·확대 가능성·주가·매출·사원수
        out[-1]["raw"] = a["raw"]
    out.sort(key=lambda x: (-x["raw"], x["deadline"]))   # 같은 %면 세부 원점수 → 마감일 빠른 순
    for i, x in enumerate(out, 1):
        x["rank"] = i
    return out


def recommend(profile: dict, saju: dict) -> list[dict]:
    results = [match_job(profile, saju, job) for job in JOBS]
    results.sort(key=lambda r: r["total"], reverse=True)
    return results
