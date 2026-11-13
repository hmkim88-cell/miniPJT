"""회사 인연도 대시보드의 추가 탭 (모두 코드 계산, 결정적).

1) 지원자의 커리어 성향 · 연간 방향성   2) 대상 회사 구인 내용   3) 회사 재무 분석
4) 지원자의 커리어 분석               5) 인터뷰 전략 (기본안 — AI 전략이 실패할 때도 보여 줌)
"""
from __future__ import annotations

from collections import Counter
from datetime import date

from .jobs import JOBS, LEVELS, NEWS

# 일간 오행별 일하는 성향 (명리 해석, 참고용)
TENDENCY = {
    "목": ("성장·기획형", "새 프로젝트를 키우고 방향을 잡는 일에서 힘이 나요. 초기 제품·신규 조직과 잘 맞아요."),
    "화": ("표현·리더형", "발표·설득·팀 분위기를 이끄는 데 강해요. 고객 접점이 있는 역할에서 돋보여요."),
    "토": ("안정·조율형", "운영·일정·이해관계 조율에 강해요. 큰 조직의 핵심 시스템을 맡기기 좋은 사람이에요."),
    "금": ("원칙·분석형", "품질·보안·구조 설계처럼 기준이 분명한 일에 강해요. 꼼꼼함이 신뢰가 돼요."),
    "수": ("탐구·문제해결형", "데이터·리서치·어려운 문제 해결에 강해요. 깊게 파고드는 일이 잘 맞아요."),
}

# 기술 → 분야
CATEGORY = {
    "백엔드": {"Python", "FastAPI", "Django", "Java", "Spring", "Go", "Node.js", "PostgreSQL", "MySQL", "Kafka", "Redis", "C#"},
    "AI·데이터": {"LangChain", "LangGraph", "RAG", "PyTorch", "MLOps", "Spark", "Airflow", "SQL"},
    "클라우드·인프라": {"AWS", "Docker", "Kubernetes", "Terraform", "Linux", "Prometheus"},
    "프론트·모바일": {"JavaScript", "TypeScript", "React", "CSS", "Kotlin", "Android", "Swift", "iOS"},
    "보안·임베디드": {"보안", "네트워크", "C++", "ROS"},
    "협업·품질": {"Git", "Selenium", "리더십"},
}


def _cat(skill: str) -> str:
    return next((c for c, s in CATEGORY.items() if skill in s), "기타")


# ---------- 1) 커리어 성향 · 연간 방향성 ----------
def tendency_section(saju: dict, profile: dict) -> dict:
    name, desc = TENDENCY[saju["day_master_elem"]]
    cats = Counter(_cat(s) for s in profile.get("skills", []))
    main = cats.most_common(1)[0][0] if cats else "미정"
    months = (saju.get("move") or {}).get("months", [])
    gaps = applicant_section(profile)["market_gaps"][:2]
    plan = []
    for m in months:
        s = m["score"]
        if s >= 70:
            act, kind = "지원 집중 — 마감 임박 공고에 바로 지원, 추천 요청", "go"
        elif s >= 50:
            act, kind = "인맥·추천 — 추천인에게 연락, 커피챗, 영문 이력서 다듬기", "net"
        else:
            act, kind = ("역량 보완 — " + (", ".join(gaps) + " 학습·포트폴리오" if gaps else "포트폴리오 정리")), "prep"
        plan.append({"ym": m["ym"], "gz": m["gz"], "score": s, "action": act, "kind": kind})
    reading = saju.get("reading") or {}
    return {"type": name, "desc": desc, "main_field": main,
            "fields": dict(cats.most_common()), "work_style": reading.get("work_style"),
            "personality": reading.get("personality"),
            "direction": f"{name} 성향 + 주력 분야 '{main}' → 올해는 "
                         + ("AI·데이터 쪽으로 넓히는 해" if main != "AI·데이터" else "AI·데이터 전문성을 굳히는 해"),
            "plan": plan, "best": (saju.get("move") or {}).get("best", [])}


# ---------- 2) 구인 내용 ----------
def posting_section(job: dict) -> dict:
    sk = job["skills"]
    dday = (date.fromisoformat(job["deadline"]) - date.today()).days
    return {
        "company": job["company"], "hq": job["hq"], "title": job["title"], "level": job["level"],
        "years": f"{job['years_min']}~{job['years_max']}년", "salary": job["salary"] + "원",
        "english": job["english"], "location": job["location"], "deadline": job["deadline"],
        "dday": dday, "recruiter": job["recruiter"], "source": job.get("source_site_name") or job["source"], "source_url": job.get("source_url", ""), "family": job.get("family", ""),
        "duties": [f"{', '.join(sk[:2])} 기반 서비스 설계·개발·운영", f"{job['title']} 역할로 글로벌 본사({job['hq']})와 협업",
                   "코드 리뷰·문서화 등 영어 기반 협업"],
        "requirements": [f"관련 경력 {job['years_min']}~{job['years_max']}년", f"{', '.join(sk[:3])} 실무 경험",
                         f"영어 {job['english']} 수준"],
        "preferred": [f"{s} 경험" for s in sk[3:]] or ["관련 오픈소스·포트폴리오"],
        "skills": sk,
    }


# ---------- 3) 회사 재무 분석 ----------
def finance_section(job: dict) -> dict | None:
    c = job.get("info")
    if not c:
        return None
    rev, g, m = c["revenue"], c["growth"], c["margin"]
    proj = [{"year": 2026 + i, "rev": round(rev * (1 + g / 100) ** i, 1)} for i in range(4)]
    op = round(rev * m / 100, 2)
    per_emp = round(rev * 1e8 * 1300 / c["emp"] / 1e8, 2)   # 억 달러 → 원(1달러 1,300원 가정) → 1인당 억 원
    checks = [
        {"k": "성장성", "v": f"향후 연 {g}% · 전년 {c['yoy']:+d}%",
         "tone": "good" if g >= 20 else "soso" if g >= 10 else "bad",
         "t": "빠르게 크는 회사 — 새 팀·새 자리가 생겨요" if g >= 20 else "꾸준히 성장" if g >= 10 else "성장 둔화 — 기존 조직 유지 위주"},
        {"k": "수익성", "v": f"영업이익률 {m}% (약 ${op}억)",
         "tone": "good" if m >= 15 else "soso" if m >= 0 else "bad",
         "t": "돈을 잘 버는 회사 — 보상·복지 여력 큼" if m >= 15 else "흑자 유지" if m >= 0 else "적자(투자 단계) — 투자 유치 상황 확인"},
        {"k": "주가·시장 평가", "v": (f"{c['listed']} {c['price']} · 52주 {c['w52']:+d}%" if c["listed"] else "비상장"),
         "tone": "good" if (c.get("w52") or 0) >= 20 else "soso" if c["listed"] and c["w52"] >= 0 else "bad" if c["listed"] else "soso",
         "t": ("시장이 성장을 기대 — 스톡옵션·RSU 가치 기대" if (c.get("w52") or 0) >= 20 else "주가 보합" if c["listed"] and c["w52"] >= 0
               else "주가 약세 — 실적 회복 여부 확인" if c["listed"] else "상장 전 — 지분 보상 조건 확인")},
        {"k": "한국 비중", "v": f"한국 {c['emp_kr']}명 / 전 세계 {c['emp']:,}명 ({c['emp_kr'] / c['emp'] * 100:.1f}%)",
         "tone": "good" if c["expand"] == "높음" else "soso",
         "t": f"한국 확대 {c['expand']} — {c['plan']}"},
        {"k": "생산성", "v": f"직원 1인당 매출 약 {per_emp}억 원", "tone": "soso",
         "t": "1인당 매출이 높을수록 연봉 협상 여지가 커요"},
    ]
    return {"info": c, "projection": proj, "op_profit": op, "per_emp": per_emp, "checks": checks,
            "note": "가상 예시 값 · 환율 1달러=1,300원 가정"}


# ---------- 4) 지원자의 커리어 분석 ----------
def applicant_section(profile: dict) -> dict:
    mine = profile.get("skills", [])
    mine_l = {s.lower() for s in mine}
    demand = Counter(s for j in JOBS for s in j["skills"])
    have = sorted(({"skill": s, "jobs": demand.get(s, 0)} for s in mine), key=lambda x: -x["jobs"])
    gaps = [s for s, _ in demand.most_common() if s.lower() not in mine_l][:5]
    reach = sum(1 for j in JOBS if sum(s.lower() in mine_l for s in j["skills"]) / len(j["skills"]) >= 0.5)
    years = profile.get("years", 0) or 0
    lv = profile.get("level", "주니어")
    nxt = LEVELS[min(LEVELS.index(lv) + 1, 3)] if lv in LEVELS else "미들"
    cats = Counter(_cat(s) for s in mine)
    return {"years": years, "level": lv, "next_level": nxt, "skills": have,
            "fields": dict(cats.most_common()), "market_gaps": gaps, "reach": reach, "total_jobs": len(JOBS),
            "summary": profile.get("summary"),
            "strengths": profile.get("strengths") or [], "weaknesses": profile.get("weaknesses") or []}


# ---------- 5) 인터뷰 전략 (기본안) ----------
def interview_base(job: dict, profile: dict, career: dict) -> dict:
    matched, missing = career["matched"], career["missing"]
    news = job.get("news") if job.get("news") is not None else NEWS.get(job["company"], [])
    c = job.get("info") or {}
    return {
        "source": "기본 전략 (코드)",
        "key_messages": [f"{', '.join(matched[:3]) or '보유 기술'}로 바로 기여할 수 있다는 실제 사례",
                         f"경력 {profile.get('years', 0)}년 동안 만든 성과를 숫자로 (속도·비용·사용자 수)",
                         f"{job['hq']} 본사와 영어로 협업할 수 있다는 근거 (문서·회의 경험)"],
        "questions": [
            {"q": "Tell me about yourself. (1분 자기소개)", "tip": "직무 관련 경력 → 대표 성과 1개 → 지원 이유 순서로 60초"},
            {"q": f"{matched[0] if matched else '주력 기술'}로 해결한 가장 어려운 문제는?", "tip": "STAR(상황·과제·행동·결과)로, 결과는 숫자로"},
            {"q": f"{missing[0]} 경험이 있나요?" if missing else "새 기술을 어떻게 빨리 배우나요?",
             "tip": (f"솔직히 부족하다고 말하고, 지금 공부 중인 내용·비슷한 경험({matched[0] if matched else ''})으로 연결") if missing else "최근 배운 기술과 적용 사례"},
            {"q": "Why our company? (왜 우리 회사인가)",
             "tip": (f"'{news[0]['title']}' 같은 한국 사업 소식을 언급하며 내 역할 연결" if news else f"{c.get('plan', '회사의 성장 방향')}과 내 경험 연결")},
            {"q": "System design / 코딩 테스트", "tip": f"{', '.join(job['skills'][:3])} 중심으로 설계 이유를 말로 설명하는 연습"},
        ],
        "weakness_plan": ([f"{s}: 지원 전 2주 미니 프로젝트 → 깃허브 링크 준비" for s in missing[:3]]
                          or ["요구 기술을 모두 갖춤 — 깊이(성능·장애 대응) 사례를 준비"]),
        "ask_them": ([f"{news[0]['partner'] or '한국'} 관련 사업에서 이 포지션의 역할은?"] if news else [])
                    + ["입사 후 3개월 안에 기대하는 성과는?", "한국 팀과 본사의 협업 방식은?"],
        "english": f"영어 요구: {job['english']} — 자기소개·대표 프로젝트 2개는 영어로 외워서 말할 수 있게",
    }
