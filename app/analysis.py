"""회사 인연도 (100점) — 사용자 결정 배점, 계산은 모두 코드(결정적).

① 한국 내 사업확대 20  ② 주가 분석으로 본 향후 성장성 20  ③ 내 커리어와 매칭 30
④ 사주 인연성 20  ⑤ 데이터·AI 등 미래사업 분야·회사 인지도 10
+ 참고: 사내 인맥(학연·지연·전 직장) — 점수에 넣지 않음

매칭률(커리어 34 : 연봉·직급 33 : 사주 33)과는 별개의 회사 단위 점수입니다.
"""
from __future__ import annotations

from datetime import date

from . import dashboard
from . import keywords as _kw
from .jobs import NEWS, get_job
from .network import connections
from .saju import (BRANCH_ELEM, BRANCHES, ROLE_MEANING, STEM_ELEM, STEMS, _gapja_of_solar, affinity,
                   affinity_story, element_role)
from .scoring import career, pay_level

MAX = {"korea": 20, "stock": 20, "career": 30, "saju": 20, "future": 10}   # 사용자 결정 배점

# 미래사업 분야 (회사 → 분야), 분야 기본점: AI·데이터 8 · 클라우드·반도체·로봇 6 · 보안·핀테크·모빌리티·헬스 4 · 그 외 2
SECTOR = {
    "Brightwave Data": "AI·데이터", "Elyra AI Korea": "AI·데이터", "Mirefield Analytics": "AI·데이터", "Pellucid Labs": "AI·데이터",
    "Kestrelbyte Cloud": "클라우드", "Fjordstack": "클라우드", "Ravencrest Infra": "클라우드",
    "Tidemark Semicon": "반도체", "Norvale Robotics": "로봇",
    "Granite Shield Security": "보안", "Corvant Payments": "핀테크", "Orbisfin": "핀테크",
    "Ivorpath Mobility": "모빌리티", "Aeroloop Korea": "모빌리티", "Delmora Health": "헬스케어",
    "Halcyon Commerce": "커머스", "Solenne Media": "미디어", "Lumora Games": "게임",
    "Junipra Apps": "앱 서비스", "Quillon Software": "SW 품질",
}
SECTOR_PTS = {"AI·데이터": 8, "클라우드": 6, "반도체": 6, "로봇": 6, "보안": 4, "핀테크": 4, "모빌리티": 4, "헬스케어": 4}


def _grade(score: int, mx: int) -> str:
    r = score / mx
    return "매우 좋음" if r >= 0.8 else "좋음" if r >= 0.6 else "보통" if r >= 0.4 else "낮음"


def korea_section(job: dict, profile: dict) -> dict:
    """① 한국 내 사업확대 20 = 한국 확대 계획(높음 10·보통 5·낮음 0) + 한국 파트너 1곳당 3(최대 2곳) + 한국 투자 뉴스 4."""
    info = job.get("info") or {}
    items = job.get("news") if job.get("news") is not None else NEWS.get(job["company"], [])
    mine = {s.lower() for s in profile.get("skills", [])}
    news = []
    for n in items:
        hit = [k for k in n["kw"] if k.lower() in mine]
        news.append({**n, "my_skills": hit,
                     "meaning": f"내 기술 {', '.join(hit)}이(가) 이 사업에 바로 쓰여요" if hit else "내 기술과 직접 겹치지는 않아요"})
    partners = sorted({n["partner"] for n in items if n["partner"]})
    invest = any(n["kind"] == "한국 투자" for n in items)
    parts = {"한국 확대 계획": {"높음": 10, "보통": 5, "낮음": 0}.get(info.get("expand"), 0),
             "한국 파트너": 3 * min(len(partners), 2), "한국 투자 뉴스": 4 if invest else 0}
    score = sum(parts.values())
    return {"score": score, "max": 20, "grade": _grade(score, 20), "parts": parts,
            "expand": info.get("expand"), "plan": info.get("plan"), "partners": partners,
            "korea_invest": invest, "items": news}


def stock_section(job: dict) -> dict:
    """② 주가 분석 성장성 20 = 성장 전망(최대 8) + 주가 흐름(최대 6) + 수익성(최대 6)."""
    c = job.get("info")
    if not c:
        return {"score": 0, "max": 20, "grade": "정보 없음", "parts": {}, "info": None, "notes": ["회사 정보 미등록"]}
    notes = []
    outlook = round(8 * min(c["growth"], 40) / 40)
    if c["listed"] and c.get("w52") is not None:
        w = c["w52"]
        trend = 6 if w >= 30 else 4 if w >= 10 else 2 if w >= 0 else 0
        notes.append(f"52주 주가 {w:+d}% — " + ("시장이 성장을 강하게 기대" if w >= 30 else "꾸준한 상승" if w >= 10
                                              else "보합" if w >= 0 else "주가 약세, 실적 회복 확인 필요"))
    else:   # 비상장: 주가 대신 전년 매출 성장으로 판단
        y = c.get("yoy") or 0
        trend = 4 if y >= 40 else 3 if y >= 20 else 1
        notes.append(f"비상장 — 주가 대신 전년 매출 성장 {y:+d}%로 판단 (최대 4점)")
    m = c.get("margin")
    profit = 0 if m is None or m < 0 else 6 if m >= 15 else 4 if m >= 5 else 2
    if m is not None and m < 0:
        notes.append("아직 적자(투자 단계) — 성장은 빠르지만 안정성 확인 필요")
    parts = {"성장 전망": outlook, "주가 흐름": trend, "수익성": profit}
    score = sum(parts.values())
    return {"score": score, "max": 20, "grade": _grade(score, 20), "parts": parts, "info": c, "notes": notes}


def career_section(profile: dict, job: dict) -> dict:
    """③ 커리어 매칭 30 = (기술·경력 60% + 연봉·직급 40%) × 0.3."""
    c, p = career(profile, job), pay_level(profile, job)
    base = round(c["score"] * 0.6 + p["score"] * 0.4)
    score = round(base * 0.3)
    return {"score": score, "max": 30, "grade": _grade(score, 30), "base": base,
            "career": c, "pay": p, "english": job["english"]}


def saju_section(saju: dict, job: dict) -> dict:
    """④ 사주 인연성 20 = 이직 인연 % × 0.2. 물(水)이 회사 날짜에서 들어오는지 함께 봄."""
    a = affinity(saju, job["deadline"])
    y, m, d = _gapja_of_solar(date.fromisoformat(job["deadline"]))
    water_in = []
    for label, gz in (("년", y), ("월", m), ("일", d)):
        if STEM_ELEM[STEMS.index(gz[0])] == "수":
            water_in.append(f"{label}주 천간 {gz[0]}")
        if BRANCH_ELEM[BRANCHES.index(gz[1])] == "수":
            water_in.append(f"{label}주 지지 {gz[1]}")
    mine = saju["elements"]["수"]
    role = element_role(saju["day_master_elem"], "수")
    if water_in and mine <= 1:
        verdict, tone = "물이 들어옴 — 부족한 물을 채워 막힌 흐름이 풀려요", "good"
    elif water_in and mine >= 4:
        verdict, tone = "물이 또 들어옴 — 이미 많아 결정이 흔들릴 수 있어요", "bad"
    elif water_in:
        verdict, tone = "물이 들어옴 — 적당한 물에 힘이 더해져요", "good"
    else:
        verdict, tone = "물이 들어오지 않음 — 물의 도움 없이 다른 기운으로 봐야 해요", "soso"
    score = round(a["score"] * 0.2)
    return {"score": score, "max": 20, "grade": _grade(score, 20), "percent": a["score"],
            "water": {"in": bool(water_in), "where": water_in, "mine": mine, "role": role,
                      "role_meaning": ROLE_MEANING[role], "verdict": verdict, "tone": tone},
            "deadline_gz": f"{y}년 {m}월 {d}일", "story": affinity_story(saju, job["deadline"])}


def future_section(job: dict) -> dict:
    """⑤ 미래사업 분야·인지도 10 = 분야(AI·데이터 8 / 클라우드·반도체·로봇 6 / 보안·핀테크·모빌리티·헬스 4 / 그 외 2)
    + 인지도(글로벌 직원 1만 명 이상 2 · 3천 명 이상 1)."""
    sector = job.get("sector") or SECTOR.get(job["company"], "기타")
    emp = (job.get("info") or {}).get("emp", 0)
    parts = {f"분야: {sector}": SECTOR_PTS.get(sector, 2), "인지도(회사 규모)": 2 if emp >= 10000 else 1 if emp >= 3000 else 0}
    score = sum(parts.values())
    return {"score": score, "max": 10, "grade": _grade(score, 10), "sector": sector, "emp": emp, "parts": parts}


def network_section(job: dict, school: str, hometown: str, past: list[str]) -> dict:
    """참고: 사내 인맥 (점수 미포함)."""
    people = connections(school, past, hometown).get(job["company"], [])
    rec = sum(1 for p in people if p["can_recommend"])
    return {"people": people, "recommenders": rec,
            "grade": "연결 없음" if not rec else f"추천서 가능 {rec}명"}


def fit_total(job: dict, saju: dict, profile: dict) -> int:
    """매칭 카드에 붙일 회사 인연도 총점만 빠르게."""
    return (korea_section(job, profile)["score"] + stock_section(job)["score"] + career_section(profile, job)["score"]
            + round(affinity(saju, job["deadline"])["score"] * 0.2) + future_section(job)["score"])


def company_analysis(job_id: int, saju: dict, profile: dict, school: str = "", hometown: str = "",
                     past: list[str] | None = None) -> dict:
    job = get_job(job_id)
    if not job:
        raise ValueError("없는 공고예요.")
    secs = {"korea": korea_section(job, profile), "stock": stock_section(job),
            "career": career_section(profile, job), "saju": saju_section(saju, job), "future": future_section(job)}
    total = sum(s["score"] for s in secs.values())
    grade = "인연 매우 강함" if total >= 75 else "인연 강함" if total >= 60 else "인연 보통" if total >= 45 else "인연 약함"
    return {"job": job, "total": total, "grade": grade, **secs,
            "network": network_section(job, school, hometown, past or []),
            # 대시보드 추가 탭 (코드 계산)
            "tendency": dashboard.tendency_section(saju, profile),
            "posting": dashboard.posting_section(job),
            "finance": dashboard.finance_section(job),
            "applicant": dashboard.applicant_section(profile),
            "interview": dashboard.interview_base(job, profile, secs["career"]["career"])}


def overview(saju: dict, profile: dict, school: str = "", hometown: str = "", past: list[str] | None = None) -> dict:
    """종합 대시보드: 지금 올라온 모든 회사의 회사 인연도·매칭률 + 나의 요약 (모두 코드 계산)."""
    from datetime import date as _d
    from .jobs import JOBS
    from .scoring import match_job
    net = connections(school, past or [], hometown)
    rows = []
    for job in JOBS:
        secs = {"korea": korea_section(job, profile), "stock": stock_section(job),
                "career": career_section(profile, job), "future": future_section(job)}
        aff = affinity(saju, job["deadline"])
        secs["saju"] = {"score": round(aff["score"] * 0.2), "max": 20}
        total = sum(s["score"] for s in secs.values())
        m = match_job(profile, saju, job)
        people = net.get(job["company"], [])
        rows.append({
            "job_id": job["id"], "company": job["company"], "hq": job["hq"], "title": job["title"],
            "level": job["level"], "deadline": job["deadline"],
            "dday": (_d.fromisoformat(job["deadline"]) - _d.today()).days,
            "sector": job.get("sector") or SECTOR.get(job["company"], "기타"), "family": job.get("family", "개발"), "source_site_name": job.get("source_site_name", ""), "source_url": job.get("source_url", ""),
            "parts": {k: secs[k]["score"] for k in MAX}, "total": total,
            "grade": "인연 매우 강함" if total >= 75 else "인연 강함" if total >= 60 else "인연 보통" if total >= 45 else "인연 약함",
            "match": m["total"], "affinity": aff["score"],
            "keyword": _kw.keyword_match(job, profile.get("resume_text", ""), profile)["rate"],
            "referrers": sum(1 for p in people if p["can_recommend"]),
            "growth": (job.get("info") or {}).get("growth"),
        })
    rows.sort(key=lambda r: (-r["total"], r["dday"]))
    move = saju.get("move") or {}
    water = saju.get("water") or {}
    from .dashboard import TENDENCY, applicant_section
    app_ = applicant_section(profile)
    sectors: dict[str, list[int]] = {}
    for r in rows:
        sectors.setdefault(r["sector"], []).append(r["total"])
    return {
        "companies": rows, "max": MAX,
        "me": {"water": water, "move": {k: move.get(k) for k in ("score", "verdict", "months", "best", "year_gz", "month_gz")},
               "tendency": TENDENCY[saju["day_master_elem"]][0], "elem": saju["day_master_elem"],
               "years": app_["years"], "level": app_["level"], "skills": len(app_["skills"]),
               "gaps": app_["market_gaps"][:3]},
        "sectors": sorted(({"sector": k, "avg": round(sum(v) / len(v)), "n": len(v)} for k, v in sectors.items()),
                          key=lambda x: -x["avg"]),
    }


# ---------- 점수 계산 풀이 (대시보드 "점수 계산" 탭) ----------
import re as _re
from .scoring import WEIGHTS as _W, match_job as _match_job


def _fit_and_match(job: dict, saju: dict, profile: dict) -> tuple[int, int, int]:
    fit = (korea_section(job, profile)["score"] + stock_section(job)["score"] + career_section(profile, job)["score"]
           + round(affinity(saju, job["deadline"])["score"] * 0.2) + future_section(job)["score"])
    m = _match_job(profile, saju, job)
    return fit, m["total"], m["pass_rate"]


def score_breakdown(job_id: int, saju: dict, profile: dict) -> dict:
    """회사 인연도(100)·매칭률·합격 가능성이 어떻게 계산됐는지 한 줄씩 + 점수 올리기 시뮬레이션."""
    job = get_job(job_id)
    if not job:
        raise ValueError("없는 공고예요.")
    k, st, cr, fu = korea_section(job, profile), stock_section(job), career_section(profile, job), future_section(job)
    aff = affinity(saju, job["deadline"])
    info = job.get("info") or {}
    c, p = cr["career"], cr["pay"]
    sj = round(aff["score"] * 0.2)

    def ln(label, value, pts, mx):
        return {"label": label, "value": value, "pts": pts, "max": mx}

    trend_label = ("52주 주가 흐름", f"{info['w52']:+d}%") if info.get("listed") and info.get("w52") is not None \
        else ("매출 성장 (비상장)", f"전년 {info.get('yoy', 0):+d}%")
    saju_lines = []
    for n in aff["notes"]:
        m = _re.search(r"\(([+-]\d+)\)", n)
        saju_lines.append({"label": _re.sub(r"\s*\([+-]\d+\)", "", n), "pts": int(m.group(1)) if m else None})
    fit_items = [
        {"key": "korea", "name": "① 한국 내 사업확대", "score": k["score"], "max": 20, "lines": [
            ln("한국 확대 계획", info.get("expand", "-"), k["parts"]["한국 확대 계획"], 10),
            ln("한국 파트너 기업", f"{len(k['partners'])}곳", k["parts"]["한국 파트너"], 6),
            ln("한국 투자 뉴스", "있음" if k["korea_invest"] else "없음", k["parts"]["한국 투자 뉴스"], 4)],
         "rule": "높음 10·보통 5 + 파트너 1곳당 3(최대 2곳) + 투자 뉴스 4"},
        {"key": "stock", "name": "② 주가 성장성", "score": st["score"], "max": 20, "lines": [
            ln("향후 성장률 전망", f"연 {info.get('growth', 0)}%", st["parts"].get("성장 전망", 0), 8),
            ln(trend_label[0], trend_label[1], st["parts"].get("주가 흐름", 0), 6),
            ln("수익성 (영업이익률)", f"{info.get('margin', 0)}%", st["parts"].get("수익성", 0), 6)],
         "rule": "성장률 40%면 8(비례) + 52주 +30%↑ 6·+10%↑ 4·0%↑ 2 + 이익률 15%↑ 6·5%↑ 4·흑자 2"},
        {"key": "career", "name": "③ 커리어 매칭", "score": cr["score"], "max": 30, "lines": [
            ln("기술 일치", f"{len(c['matched'])}/{len(job['skills'])}개", c["skill"], 70),
            ln("경력 연차", f"{profile.get('years', 0)}년 (요구 {job['years_min']}~{job['years_max']}년)", c["yr"], 30),
            ln("기대 연봉", f"{profile.get('expected_salary') or '-'}만 (공고 {job['salary']})", p["sal"], 60),
            ln("희망 직급", f"{profile.get('desired_level') or profile.get('level')} → 공고 {job['level']}", p["lv"], 40)],
         "calc": f"(커리어 {c['score']} × 0.6 + 연봉·직급 {p['score']} × 0.4) = {cr['base']} → × 0.3 = {cr['score']}",
         "rule": "커리어 = 기술 70 + 경력 30 · 연봉·직급 = 연봉 60 + 직급 40"},
        {"key": "saju", "name": "④ 사주 인연", "score": sj, "max": 20, "saju_lines": saju_lines, "raw": aff["raw"],
         "calc": f"원점수 {aff['raw']} (범위 7~129) → 인연 {aff['score']}% → × 0.2 = {sj}",
         "rule": "일주 궁합 35~95 + 육합·삼합·충·부족 오행 + 천간합·월주·년주·월지 보조"},
        {"key": "future", "name": "⑤ 미래사업·인지도", "score": fu["score"], "max": 10, "lines": [
            ln("미래사업 분야", fu["sector"], list(fu["parts"].values())[0], 8),
            ln("회사 인지도 (글로벌 직원)", f"{fu['emp']:,}명", list(fu["parts"].values())[1], 2)],
         "rule": "AI·데이터 8 · 클라우드·반도체·로봇 6 · 보안·핀테크·모빌리티·헬스 4 · 그 외 2 + 1만 명↑ 2 · 3천 명↑ 1"},
    ]
    fit_total = sum(i["score"] for i in fit_items)
    m = _match_job(profile, saju, job)
    match = {"total": m["total"], "pass_rate": m["pass_rate"], "items": [
        {"key": "career", "name": "① 커리어", "raw": c["score"], "w": _W["career"], "contrib": round(c["score"] * _W["career"], 1)},
        {"key": "pay", "name": "② 연봉·직급", "raw": p["score"], "w": _W["pay"], "contrib": round(p["score"] * _W["pay"], 1)},
        {"key": "affinity", "name": "③ 사주 인연", "raw": aff["score"], "w": _W["affinity"], "contrib": round(aff["score"] * _W["affinity"], 1)}]}

    # 점수 올리기: 내가 바꿀 수 있는 것만 (사주·회사 항목은 바꿀 수 없음)
    base_fit, base_match, base_pass = fit_total, m["total"], m["pass_rate"]
    tries = []
    for sk in c["missing"][:3]:
        tries.append((f"{sk} 익히기", "기술 일치 +1개", {**profile, "skills": list(profile.get("skills", [])) + [sk]}))
    if len(c["missing"]) >= 2:
        tries.append((f"{', '.join(c['missing'][:2])} 모두 익히기", f"기술 일치 +2개", {**profile, "skills": list(profile.get("skills", [])) + c["missing"][:2]}))
    if p["sal"] < 60 and profile.get("expected_salary"):
        tries.append((f"기대 연봉을 {job['salary_max']:,}만으로 조정", "공고 상한 이하", {**profile, "expected_salary": job["salary_max"]}))
    if p["lv"] < 40:
        tries.append((f"희망 직급을 '{job['level']}'(으)로", "공고 직급과 일치", {**profile, "desired_level": job["level"]}))
    whatif = []
    for label, why, prof2 in tries:
        f2, m2, p2 = _fit_and_match(job, saju, prof2)
        whatif.append({"action": label, "why": why, "fit": f2, "fit_gain": f2 - base_fit,
                       "match": m2, "match_gain": m2 - base_match, "pass": p2, "pass_gain": p2 - base_pass})
    whatif.sort(key=lambda x: -(x["fit_gain"] + x["match_gain"]))
    return {"job": {"id": job["id"], "company": job["company"]}, "fit": {"total": fit_total, "items": fit_items},
            "match": match, "whatif": whatif}
