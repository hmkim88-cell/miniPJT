"""IT 커리어 매칭 데모 서버.

실행:  run.bat  (또는 mini-pjt 폴더에서  ..\\.venv\\Scripts\\python -m uvicorn app.main:app --reload)
브라우저: http://127.0.0.1:8000
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, analysis, dashboard, keywords, linkedin, network, resume_file, resumes, store  # ai를 먼저 불러와 ..\.env(AWS·링크드인 키)를 읽음
from .jobs import (ALL_SKILLS, ENGLISH_LEVELS, EXPAND_LEVELS, FAMILY_DESC, JOB_FAMILIES, JOBS, LEVELS, NEWS_KINDS, SOURCE_SITES,
                   add_job, build_job, delete_job, family_of, get_job, restore_jobs)
from urllib.parse import urlsplit, urlunsplit
from .saju import calc_saju, move_luck, water_analysis, year_gapja
from .scoring import fate_ranking, recommend

STATIC = Path(__file__).resolve().parents[1] / "static"
app = FastAPI(title="커리어인연 데모")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.include_router(linkedin.router)   # 내 링크드인 연결 (Sign in with LinkedIn)

APPLICATIONS: list[dict] = []   # 연결 요청 (DB에 저장, 서버 시작 때 복원)

# ── 서버 시작 때 DB에서 복원: 등록 공고 → 연결 요청 → 추천 요청 ──
restore_jobs()
APPLICATIONS.extend(store.load("application"))
network.REFERRAL_REQUESTS.extend(store.load("referral"))
store.resume_purge_expired()   # 보관 기한 지난 레주메 정리


@app.get("/")
def index():
    # 화면을 고치면 바로 보이게: 첫 페이지는 캐시하지 않음 (CSS·JS는 주소의 ?v= 로 갱신)
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/jobs")
def jobs(q: str = "", level: str = "", family: str = ""):
    q = q.strip().lower()
    out = [j for j in JOBS
           if (not q or q in (j["title"] + j["company"] + " ".join(j["skills"])).lower())
           and (not level or j["level"] == level) and (not family or j.get("family") == family)]
    return out


@app.get("/api/families")
def families():
    """직종 목록 + 설명 + 지금 공고 수."""
    return [{"name": f, "desc": FAMILY_DESC[f], "count": sum(1 for j in JOBS if j.get("family") == f)} for f in JOB_FAMILIES]


class ResumeIn(BaseModel):
    text: str


@app.post("/api/resume/review")
def resume_review(body: ResumeIn):
    if len(body.text.strip()) < 30:
        raise HTTPException(400, "프로필 내용을 30자 이상 넣어 주세요.")
    try:
        return ai.review_resume(body.text)
    except Exception as e:  # noqa: BLE001
        return simple_review(body.text, f"{type(e).__name__}")


def simple_review(text: str, err: str) -> dict:
    """AI가 실패했을 때: 코드로 기술·경력만 간단히 뽑아 다음 단계로 갈 수 있게 함 (첨삭 문장은 없음)."""
    # 단어 단위로만 찾기 (Django 안의 'go', PostgreSQL 안의 'SQL' 같은 오검출 방지)
    skills = [s for s in ALL_SKILLS
              if re.search(rf"(?<![A-Za-z0-9+#.]){re.escape(s)}(?![A-Za-z0-9+#])", text, re.IGNORECASE)]
    yrs = [int(n) for n in re.findall(r"(\d{1,2})\s*년(?:차)?", text) if int(n) <= 40]
    years = max(yrs) if yrs else 0
    level = "주니어" if years < 3 else "미들" if years < 7 else "시니어" if years < 10 else "리드"
    return {"summary": "AI 첨삭을 지금 쓸 수 없어 프로필에서 기술·경력만 간단히 뽑았어요.", "score": 0,
            "strengths": [], "weaknesses": [], "rewrites": [], "skills": skills, "years": years, "level": level,
            "job_family": family_of(" ".join(text.splitlines()[:3])),   # 첫 줄(직함)으로 직종 짐작
            "ai_error": f"AI 첨삭 실패({err}) — 간이 추출 결과"}


# ---------- 레주메 파일 올리기 · 분석 요약 ----------
@app.post("/api/resume/extract")
async def resume_extract(file: UploadFile = File(...)):
    """PDF·Word·텍스트 파일에서 글자만 뽑아 돌려줌 (파일은 저장하지 않음)."""
    data = await file.read(resume_file.MAX_BYTES + 1)
    try:
        return resume_file.extract(file.filename or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))


class SummaryIn(BaseModel):
    text: str
    prev_text: str | None = None   # 이전 버전 (변경점 비교용, 선택)


GROUPS = {"언어": {"Python", "Java", "Kotlin", "Go", "TypeScript", "JavaScript", "C#", "C++", "Swift", "SQL", "Rust", "Scala"},
          "클라우드·인프라": {"AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Linux", "Prometheus"},
          "데이터": {"PostgreSQL", "MySQL", "Redis", "Spark", "Airflow", "Kafka", "MongoDB"},
          "AI·ML": {"LangChain", "LangGraph", "PyTorch", "TensorFlow", "MLOps", "RAG"}}


def _years_from_periods(careers: list[dict]) -> int:
    """'2022.03 ~ 현재' 같은 기간을 더해 경력 연수 계산 (인턴·아르바이트 제외, 겹치면 한 번만)."""
    months: set[int] = set()
    now = date.today()
    for c in careers:
        if re.search(r"인턴|intern|아르바이트", c["company"] + c.get("role", ""), re.I):
            continue
        m = re.match(r"(\d{4})\.(\d{1,2})\s*~\s*(?:(\d{4})\.(\d{1,2})|현재|재직중)", c["period"])
        if not m:
            continue
        s = int(m.group(1)) * 12 + int(m.group(2)) - 1
        e = int(m.group(3)) * 12 + int(m.group(4)) - 1 if m.group(3) else now.year * 12 + now.month - 1
        months.update(range(s, e + 1))
    return len(months) // 12   # 4년 8개월 → 4년 (만 연수)


@app.post("/api/resume/summary")
def resume_summary(body: SummaryIn):
    text = body.text.strip()
    if len(text) < 30:
        raise HTTPException(400, "레주메 내용을 30자 이상 넣어 주세요.")
    prev = (body.prev_text or "").strip() or None
    if prev == text:
        prev = None
    try:
        out = ai.summarize_resume(text[:20000], prev[:20000] if prev else None)
        out["ai"] = True
    except Exception as e:  # noqa: BLE001  AI 실패 → 코드로 간이 요약 (지어내지 않음)
        b = simple_review(text, type(e).__name__)
        groups = [{"group": g, "items": [x for x in b["skills"] if x in names]} for g, names in GROUPS.items()]
        rest = [x for x in b["skills"] if not any(x in n for n in GROUPS.values())]
        groups = [g for g in groups if g["items"]] + ([{"group": "프레임워크·기타", "items": rest}] if rest else [])
        careers = [{"company": m.group(1).strip(" ·-|"), "role": "", "period": m.group(2), "highlights": []}
                   for m in re.finditer(r"^(.{2,40}?)\s*[\(·|-]?\s*\(?(\d{4}\.\d{1,2}\s*~\s*(?:\d{4}\.\d{1,2}|현재|재직중))", text, re.M)][:6]
        years = b["years"] or _years_from_periods(careers)   # "N년"이 없으면 경력 기간(인턴 제외)으로 계산
        level = b["level"] if b["years"] else ("주니어" if years < 3 else "미들" if years < 7 else "시니어" if years < 10 else "리드")
        out = {"headline": f"경력 {years}년 · {level} · 기술 {len(b['skills'])}개", "summary": [], "careers": careers,
               "achievements": [], "skill_groups": groups, "years": years, "level": level, "certificates": [],
               "languages": [], "fit_roles": [], "gaps": [], "changes": [], "ai": False,
               "ai_error": f"AI 요약 실패({type(e).__name__}) — 기술·경력·기간만 간이 추출"}
    if prev:   # 글자 수 변화 (사실값)
        out["diff"] = {"before": len(prev), "after": len(text)}
    out["skills"] = sorted({x for g in out["skill_groups"] for x in g["items"]})
    out["as_of"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return out


class SajuIn(BaseModel):
    birth: str                 # YYYY-MM-DD
    hour: int | None = None    # 0~23, 모르면 None
    calendar: str = "solar"    # solar | lunar
    leap: bool = False


@app.post("/api/saju")
def saju(body: SajuIn):
    try:
        y, m, d = map(int, body.birth.split("-"))
        result = calc_saju(y, m, d, body.hour, body.calendar, body.leap)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"생년월일을 확인해 주세요: {e}")
    result["water"] = water_analysis(result)     # 물(水) 유무·역할
    result["move"] = move_luck(result)            # 오늘 지원 시 이직운 + 12개월
    result["fate_ranking"] = fate_ranking(result)  # 공고 회사별 이직 인연 % 랭킹
    this_year = date.today().year
    gz = year_gapja(this_year)
    try:
        result["reading"] = ai.read_saju(result, this_year, gz)
    except Exception as e:  # noqa: BLE001
        result["reading"] = None
        result["reading_error"] = f"AI 풀이 실패: {type(e).__name__}"
    result["this_year"] = {"year": this_year, "gz": gz}
    return result


class RecommendIn(BaseModel):
    profile: dict   # {skills, years, level, desired_level, expected_salary}
    saju: dict      # /api/saju 결과


@app.post("/api/recommend")
def recommend_jobs(body: RecommendIn):
    ranked = recommend(body.profile, body.saju)
    top = ranked[:5]
    try:
        comments = ai.comment_jobs(body.profile, top)
    except Exception:  # noqa: BLE001
        comments = {}
    for r in ranked:
        r["comment"] = comments.get(r["job"]["id"])
        r["company_fit"] = analysis.fit_total(r["job"], body.saju, body.profile)   # 회사 인연도 (100점, 매칭률과 별개)
        r["keyword_match"] = keywords.keyword_match(r["job"], body.profile.get("resume_text", ""), body.profile)["rate"]
    return ranked


class ApplyIn(BaseModel):
    job_id: int
    total: int | None = None
    pass_rate: int | None = None
    candidate: dict = {}   # 구인자에게 보낼 정보: 요약·기술·경력·직급·기대연봉·링크드인 URL (사주·생년월일 제외)
    career_score: int | None = None
    pay_score: int | None = None


SHARE_KEYS = ("summary", "skills", "years", "level", "desired_level", "expected_salary", "linkedin_url", "resume_summary")
# 구인자에게 보내는 레주메 '요약'의 항목 (원문·변경점·빈 곳(gaps)은 보내지 않음)
SUMMARY_SHARE = ("headline", "summary", "careers", "achievements", "skill_groups", "years", "level", "certificates", "languages", "fit_roles", "as_of")


def _share(candidate: dict) -> dict:
    c = {k: candidate.get(k) for k in SHARE_KEYS}
    rs = c.get("resume_summary")
    c["resume_summary"] = {k: rs.get(k) for k in SUMMARY_SHARE} if isinstance(rs, dict) else None
    c["linkedin_url"] = resume_file.profile_url(c.get("linkedin_url") or "") or None   # 링크드인 프로필 주소 모양만 전달
    return c


@app.post("/api/apply")
def apply(body: ApplyIn, request: Request):
    """구직자 → 구인자(채용 담당자) 연결 요청."""
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(404, "없는 공고예요.")
    if any(a["job"]["id"] == body.job_id for a in APPLICATIONS):
        raise HTTPException(409, "이미 연결 요청한 공고예요.")
    entry = {"id": len(APPLICATIONS) + 1, "job": job, "total": body.total, "pass_rate": body.pass_rate,
             "candidate": _share(body.candidate),
             "verified": _verified(request),
             "career_score": body.career_score, "pay_score": body.pay_score,
             "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "status": "연결 요청됨"}
    APPLICATIONS.append(entry)
    store.save("application", entry["id"], entry)
    return entry


def _verified(request: Request) -> dict | None:
    """링크드인으로 본인 확인된 이름·이메일 (연결했을 때만, 구직자가 연결 요청할 때 구인자에게 전달)."""
    u = linkedin.current_user(request)
    return {"name": u["name"], "email": u["email"]} if u else None


class NetworkIn(BaseModel):
    school: str = ""
    hometown: str = ""
    past_companies: list[str] = []


@app.post("/api/network")
def my_network(body: NetworkIn):
    """나와 학연·지연·전 직장으로 연결된 추천인 (회사 이름별). 매칭률에는 넣지 않음."""
    return {"schools": network.SCHOOLS, "regions": network.REGIONS,
            "by_company": network.connections(body.school, body.past_companies, body.hometown)}


class AnalysisIn(BaseModel):
    job_id: int
    saju: dict
    profile: dict
    school: str = ""
    hometown: str = ""
    past_companies: list[str] = []


@app.post("/api/company-analysis")
def company_analysis(body: AnalysisIn):
    """대상 회사 인연 분석 5섹션: ①사주(물) ②커리어 ③재무·성장성 ④사내 인맥 ⑤한국 사업 뉴스."""
    try:
        return analysis.company_analysis(body.job_id, body.saju, body.profile,
                                         body.school, body.hometown, body.past_companies)
    except ValueError as e:
        raise HTTPException(404, str(e))


class ReferralIn(BaseModel):
    referrer_id: int
    job_id: int


@app.post("/api/referral")
def referral(body: ReferralIn, request: Request):
    """추천인에게 추천 요청 (링크드인 확인 이름·이메일만 함께 전달, 사주 정보 없음)."""
    try:
        return network.request_referral(body.referrer_id, body.job_id, _verified(request))
    except ValueError as e:
        raise HTTPException(404, str(e))
    except LookupError as e:
        raise HTTPException(409, str(e))


class InterviewIn(BaseModel):
    job_id: int
    saju: dict
    profile: dict


class OverviewIn(BaseModel):
    saju: dict
    profile: dict
    school: str = ""
    hometown: str = ""
    past_companies: list[str] = []


@app.post("/api/overview")
def overview(body: OverviewIn):
    """종합 대시보드: 모든 회사의 회사 인연도(5항목)·매칭률·인맥 + 나의 이직운·물·성향 요약."""
    return analysis.overview(body.saju, body.profile, body.school, body.hometown, body.past_companies)


class BreakdownIn(BaseModel):
    job_id: int
    saju: dict
    profile: dict


@app.post("/api/score-breakdown")
def score_breakdown(body: BreakdownIn):
    """추천 점수 풀이: 회사 인연도 100점·매칭률·합격 가능성 계산 과정 + 점수 올리기 시뮬레이션."""
    try:
        return analysis.score_breakdown(body.job_id, body.saju, body.profile)
    except ValueError as e:
        raise HTTPException(404, str(e))


class KeywordIn(BaseModel):
    job_id: int
    profile: dict   # resume_text(레주메 원문) · skills · years


@app.post("/api/keywords")
def job_keywords(body: KeywordIn):
    """구인 요건 핵심 키워드(중요도) + 레주메 키워드 매칭률."""
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(404, "없는 공고예요.")
    return keywords.keyword_match(job, body.profile.get("resume_text", ""), body.profile)


@app.post("/api/interview-strategy")
def interview_strategy(body: InterviewIn):
    """회사 1곳 인터뷰 전략: AI(Claude) → 실패하면 코드 기본안."""
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(404, "없는 공고예요.")
    from .scoring import career
    c = career(body.profile, job)
    base = dashboard.interview_base(job, body.profile, c)
    # 최근 업무 강조 키워드: 레주메 원문에서 코드로 (AI 성공·실패와 관계없이 항상)
    focus = keywords.recent_focus(job, body.profile.get("resume_text") or "", body.profile, ALL_SKILLS)
    try:
        best = (body.saju.get("move") or {}).get("best", [])
        out = ai.interview_plan(job, {**body.profile, "recent_focus": [f["keyword"] for f in focus["items"]]}, c,
                                job.get("news") or analysis.NEWS.get(job["company"], []), dashboard.finance_section(job), best)
    except Exception as e:  # noqa: BLE001
        out = base
        out["ai_error"] = f"AI 전략 실패({type(e).__name__}) — 기본 전략 표시"
    out["recent_focus"] = focus
    return out


class FocusIn(BaseModel):
    profile: dict
    job_id: int | None = None


@app.post("/api/recent-focus")
def recent_focus(body: FocusIn):
    """레주메의 최근 업무 → 인터뷰 강조 키워드 + 2줄 설명 (공고를 주면 그 공고 기준)."""
    job = get_job(body.job_id) if body.job_id else None
    return keywords.recent_focus(job, body.profile.get("resume_text") or "", body.profile, ALL_SKILLS)


@app.get("/api/applications")
def applications():
    return APPLICATIONS


# ---------- 구인자(채용 담당자) ----------
class NewsIn(BaseModel):
    title: str
    partner: str = ""
    kind: str = "제휴"
    date: str = ""
    kw: list[str] = []


class JobIn(BaseModel):
    # 포지션
    company: str
    hq: str
    title: str
    level: str
    years_min: int
    years_max: int
    skills: list[str]
    salary_min: int
    salary_max: int
    english: str = "업무 가능"
    location: str
    deadline: str          # YYYY-MM-DD (사주 인연의 회사 쪽 날짜)
    recruiter_name: str
    # 회사 정보 (회사 인연도 ①②⑤ 계산에 사용)
    sector: str = "기타"
    listed: str = ""       # 상장 시장 (비상장이면 빈칸)
    price: str = ""
    chg: float | None = None
    w52: int | None = None
    revenue: float = 0     # 글로벌 연매출 (억 달러)
    emp: int = 0
    emp_kr: int = 0
    growth: int = 0        # 향후 3년 연평균 성장률 전망 %
    yoy: int = 0
    margin: int = 0
    expand: str = "보통"
    plan: str = ""
    news: list[NewsIn] = []
    family: str = ""        # 직종 (개발·데이터·AI·인프라·클라우드·세일즈·프리세일즈·딜리버리·고객 성공)
    source_site: str = "direct"   # 공고 출처: linkedin / wanted / remember / jumpit / saramin / jobkorea / rocketpunch / careers / direct
    source_url: str = ""   # 출처 사이트의 원문 주소 (원문 링크로만 보여 줌, 서버는 접속하지 않음)


def _check_job(b: JobIn) -> None:
    """등록 전에 입력값 점검 (화면에서도 같은 안내를 보여 줌)."""
    errs = []
    for f, label in (("company", "회사명"), ("hq", "본사 국가"), ("title", "포지션"), ("location", "근무지"), ("recruiter_name", "담당자 이름")):
        if not getattr(b, f).strip():
            errs.append(f"{label}을(를) 입력해 주세요")
    if b.level not in LEVELS:
        errs.append("직급을 골라 주세요")
    if not 1 <= len([x for x in b.skills if x.strip()]) <= 8:
        errs.append("요구 기술은 1~8개예요")
    if b.years_min > b.years_max or b.years_min < 0:
        errs.append("경력 범위를 확인해 주세요")
    if b.salary_min <= 0 or b.salary_min > b.salary_max:
        errs.append("연봉 범위를 확인해 주세요")
    if b.english not in ENGLISH_LEVELS:
        errs.append("영어 수준을 골라 주세요")
    if b.expand not in EXPAND_LEVELS:
        errs.append("한국 확대 가능성을 골라 주세요")
    try:
        date.fromisoformat(b.deadline)
    except ValueError:
        errs.append("마감일은 YYYY-MM-DD 형식이에요")
    if b.family and b.family not in JOB_FAMILIES:   # 비어 있으면 직무명으로 자동 분류 (build_job)
        errs.append("직종을 다시 골라 주세요")
    if b.source_site not in SOURCE_SITES:
        errs.append("공고 출처를 골라 주세요")
    else:
        try:
            normalize_source_url(b.source_site, b.source_url)
        except ValueError as e:
            errs.append(str(e))
    if errs:
        raise HTTPException(400, " · ".join(errs))


def _job_data(b: JobIn) -> dict:
    d = b.model_dump()
    d["source_url"] = normalize_source_url(b.source_site, b.source_url)   # 주소는 정리된 모양으로만 저장
    d["skills"] = list(dict.fromkeys(x.strip() for x in b.skills if x.strip()))
    return d


@app.get("/api/recruiter/meta")
def recruiter_meta():
    """공고 등록 화면의 선택지."""
    return {"levels": LEVELS, "english": ENGLISH_LEVELS, "expand": EXPAND_LEVELS, "news_kinds": NEWS_KINDS,
            "sectors": SECTORS, "families": [{"name": f, "desc": FAMILY_DESC[f]} for f in JOB_FAMILIES],
            "sites": [{"key": k, "name": v["name"], "needs_url": v["domains"] is not None,
                       "example": SITE_EXAMPLE.get(k, "")} for k, v in SOURCE_SITES.items()],
            "skills": sorted({x for j in JOBS for x in j["skills"]})}


@app.post("/api/recruiter/preview")
def recruiter_preview(body: JobIn):
    """등록 전 미리보기: 회사 쪽 점수(① 한국 사업확대 · ② 주가 성장성 · ⑤ 미래사업) — 구직자와 무관한 50점."""
    _check_job(body)
    job = build_job(_job_data(body), 0)
    k, st, fu = analysis.korea_section(job, {}), analysis.stock_section(job), analysis.future_section(job)
    return {"korea": {"score": k["score"], "max": 20, "parts": k["parts"]},
            "stock": {"score": st["score"], "max": 20, "parts": st["parts"], "notes": st["notes"]},
            "future": {"score": fu["score"], "max": 10, "parts": fu["parts"]},
            "company_side": k["score"] + st["score"] + fu["score"]}


@app.post("/api/recruiter/jobs")
def recruiter_add_job(body: JobIn):
    _check_job(body)
    d = _job_data(body)
    if d["source_url"] and any(j.get("source_url") == d["source_url"] for j in JOBS):
        raise HTTPException(409, f"이미 등록한 {SOURCE_SITES[d['source_site']]['name']} 공고예요.")
    return add_job(d)


# ---------- 링크드인 공고 가져오기 (붙여넣기 → AI가 등록 칸 채우기) ----------
# 링크드인은 공고를 가져가는 공개 API가 없고, 화면 자동 수집(스크래핑)은 이용약관 위반 → 서버는 링크드인에 접속하지 않음.
# 구인자가 자기 공고(또는 등록 권한이 있는 공고) 화면을 복사해 붙여넣은 글만 정리함.
SECTORS = ["AI·데이터", "클라우드", "반도체", "로봇", "보안", "핀테크", "모빌리티", "헬스케어", "커머스", "미디어", "게임", "앱 서비스", "기타"]
_LI_JOB = re.compile(r"^https?://([a-z]{2,3}\.)?(www\.)?linkedin\.com/(jobs/view/(?:[^/?#]*-)?(\d{6,})|jobs/(?:collections|search)[^?#]*\?[^#]*currentJobId=(\d{6,}))", re.I)


def linkedin_job_id(url: str) -> str | None:
    m = _LI_JOB.match((url or "").strip())
    return (m.group(4) or m.group(5)) if m else None


SITE_EXAMPLE = {"linkedin": "https://www.linkedin.com/jobs/view/1234567890", "wanted": "https://www.wanted.co.kr/wd/123456",
                "remember": "https://career.rememberapp.co.kr/job/posting/123456", "jumpit": "https://jumpit.saramin.co.kr/position/123456",
                "saramin": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345678",
                "jobkorea": "https://www.jobkorea.co.kr/Recruit/GI_Read/12345678", "rocketpunch": "https://www.rocketpunch.com/jobs/123456",
                "careers": "https://careers.회사도메인.com/jobs/123"}


def normalize_source_url(site: str, url: str) -> str:
    """출처 사이트에 맞는 주소인지 확인하고 정리 (조각(#)·추적값 제거). 서버는 이 주소를 열지 않음."""
    url = (url or "").strip()
    info = SOURCE_SITES.get(site)
    if not url or info is None or info["domains"] is None:
        return ""
    name = info["name"]
    if site == "linkedin":
        lid = linkedin_job_id(url)
        if not lid:
            raise ValueError(f"링크드인 공고 주소 형식이 아니에요 (예: {SITE_EXAMPLE['linkedin']})")
        return f"https://www.linkedin.com/jobs/view/{lid}/"
    u = urlsplit(url)
    host = (u.hostname or "").lower()
    if u.scheme not in ("http", "https") or not host or len(url) > 400:
        raise ValueError(f"{name} 공고 주소를 확인해 주세요 (예: {SITE_EXAMPLE.get(site, 'https://…')})")
    if info["domains"] and not any(host == d or host.endswith("." + d) for d in info["domains"]):
        raise ValueError(f"{name} 주소가 아니에요 ({', '.join(info['domains'])} 주소만, 예: {SITE_EXAMPLE.get(site, '')})")
    if site == "saramin" and host.startswith("jumpit."):
        raise ValueError("점핏 공고예요. 출처를 '점핏'으로 골라 주세요")
    keep = "&".join(x for x in u.query.split("&") if x.split("=")[0].lower() in ("rec_idx", "gno", "id", "idx", "currentjobid"))
    return urlunsplit(("https", host, u.path.rstrip("/") or "/", keep, ""))


class PostingImportIn(BaseModel):
    site: str = "linkedin"
    url: str = ""
    text: str


class LinkedInImportIn(BaseModel):   # 예전 주소 호환
    url: str = ""
    text: str


def _draft_fallback(text: str) -> dict:
    """AI를 못 쓸 때: 링크드인 공고의 정해진 모양(제목 · '회사 · 위치' 줄 · Meet the hiring team · Requirements …)에서
    적혀 있는 값만 코드로 읽음. 적혀 있지 않은 값은 비워 둠 (지어내지 않음)."""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    low = text.lower()

    def sec(*names):   # 'Requirements' 같은 소제목 아래 글 (다음 소제목 전까지)
        m = re.search(r"(?im)^\s*(?:" + "|".join(names) + r")\b.*$([\s\S]*?)(?=^\s*(?:[A-Z][A-Za-z' ]{2,40}|[가-힣 ]{2,12})\s*:?\s*$|\Z)", text)
        return m.group(1) if m else ""

    def find_skills(t):
        hits = [(m.start(), s) for s in ALL_SKILLS
                for m in [re.search(rf"(?<![A-Za-z0-9+#.]){re.escape(s)}(?![A-Za-z0-9+#]|-[A-Za-z])", t, re.I)] if m]
        return [s for _, s in sorted(hits)]   # 글에 나온 순서대로 ('go-live'의 go는 Go 기술로 보지 않음)

    must = find_skills(sec("requirements", "qualifications", "basic qualifications", "minimum qualifications", "what you(?:'|’)ll need", "자격 요건", "필수"))
    nice = find_skills(sec("nice to have", "preferred", "preferred qualifications", "bonus", "우대 사항", "우대"))
    allsk = find_skills(text)
    skills = list(dict.fromkeys([*must, *[s for s in allsk if s not in nice], *nice]))

    # 회사 · 위치: 제목 다음의 "Quillstone · Seoul, South Korea (Hybrid) · 1 week ago" 줄
    company, location = "", ""
    for ln in lines[1:4]:
        parts = [p.strip() for p in re.split(r"\s+[·•|]\s+", ln)]
        if len(parts) >= 2 and len(parts[0]) <= 40:
            company, place = parts[0], parts[1]
            city = {"seoul": "서울", "busan": "부산", "pangyo": "판교", "seongnam": "성남", "incheon": "인천"}
            location = next((v for k, v in city.items() if k in place.lower()), place)
            if re.search(r"remote", ln, re.I): location = "원격 근무" if location == place else f"{location} · 원격 가능"
            elif re.search(r"hybrid", ln, re.I): location = f"{location} · 하이브리드"
            break

    lvl = ""
    if re.search(r"\b(staff|principal|head of|director|engineering manager|tech lead|team lead)\b", text, re.I): lvl = "리드"
    elif re.search(r"\b(senior|sr\.?|mid-senior level)\b", text, re.I): lvl = "시니어"
    elif re.search(r"\b(entry level|junior|associate|new grad)\b", text, re.I): lvl = "주니어"
    elif re.search(r"\bmid[- ]level\b", text, re.I): lvl = "미들"

    ys = [int(a or b) for a, b in re.findall(r"(\d{1,2})\s*\+?\s*(?:years?|yrs)\b|(\d{1,2})\s*년\s*이상", text, re.I) if int(a or b) <= 25]
    rng = re.search(r"(\d{1,2})\s*[-~–]\s*(\d{1,2})\s*(?:years?|년)", text, re.I)

    smin = smax = None
    sal = re.search(r"(?:KRW|₩)\s*([\d,]{7,})\s*(?:[-~–]|to)\s*(?:KRW|₩)?\s*([\d,]{7,})", text, re.I)
    if sal:
        smin, smax = (int(x.replace(",", "")) // 10000 for x in sal.groups())
    else:
        sal = re.search(r"([\d,]{3,6})\s*(?:만원|만)\s*[-~–]\s*([\d,]{3,6})\s*(?:만원|만)", text)
        if sal: smin, smax = (int(x.replace(",", "")) for x in sal.groups())
    sal_text = ""
    st = re.search(r"(?im)^.*(?:compensation|salary|pay range|연봉|급여).*$", text)
    if st: sal_text = st.group(0).strip()[:120]

    eng = ""
    if re.search(r"(fluent|native)[^.\n]{0,20}english|english[^.\n]{0,20}(fluen|native)", low): eng = "유창"
    elif re.search(r"(business|professional)[^.\n]{0,25}english|english[^.\n]{0,25}(business|professional)", low): eng = "비즈니스"
    elif "english" in low: eng = "업무 가능"

    dl = ""
    m = re.search(r"(?:deadline|apply by|closing date|마감)[^\n\d]{0,20}(\d{4}-\d{2}-\d{2})", text, re.I)
    if m: dl = m.group(1)

    rec = ""
    m = re.search(r"(?im)^\s*meet the hiring team\s*$\s*^\s*([^\n]{2,40})$", text)
    if m and not re.search(r"\b(at|job poster)\b", m.group(1), re.I): rec = m.group(1).strip()

    hq = ""
    countries = {"미국": r"\b(US|U\.S\.|USA|United States|San Francisco|New York|Seattle|Silicon Valley)\b", "영국": r"\b(UK|United Kingdom|London)\b",
                 "독일": r"\b(Germany|Berlin|Munich)\b", "프랑스": r"\b(France|Paris)\b", "싱가포르": r"\bSingapore\b", "일본": r"\b(Japan|Tokyo)\b",
                 "캐나다": r"\b(Canada|Toronto|Vancouver)\b", "이스라엘": r"\b(Israel|Tel Aviv)\b", "네덜란드": r"\b(Netherlands|Amsterdam)\b"}
    m = re.search(r"(?i)[^.\n]{0,40}(headquartered in|based in|-based)[^.\n]{0,60}", text) or re.search(r"(?i)[A-Za-z. ]{2,20}-based", text)
    if m:
        hq = next((k for k, pat in countries.items() if re.search(pat, m.group(0))), "")

    emp = next((v for k, v in {"full-time": "정규직", "contract": "계약직", "internship": "인턴", "part-time": "파트타임"}.items() if k in low), "")
    sector = "AI·데이터" if re.search(r"\b(genai|llm|machine learning|\bai\b|data platform)", low) else "기타"
    return {"company": company, "hq": hq, "title": lines[0][:80] if lines else "", "level": lvl,
            "years_min": int(rng.group(1)) if rng else (min(ys) if ys else None), "years_max": int(rng.group(2)) if rng else None,
            "must_skills": skills[:5], "nice_skills": skills[5:8], "salary_min": smin, "salary_max": smax, "salary_text": sal_text,
            "english": eng, "location": location, "deadline": dl, "recruiter_name": rec, "sector": sector,
            "employment": emp, "summary": [], "job_family": family_of(lines[0] if lines else "")}


@app.post("/api/recruiter/import-linkedin")
def recruiter_import_linkedin(body: LinkedInImportIn):
    return recruiter_import_posting(PostingImportIn(site="linkedin", url=body.url, text=body.text))


@app.post("/api/recruiter/import-posting")
def recruiter_import_posting(body: PostingImportIn):
    """구직 사이트(링크드인·원티드·리멤버·점핏·사람인·잡코리아·로켓펀치·회사 채용 페이지)에 올린 공고 글을 붙여넣으면 등록 칸으로 정리.
    서버는 그 사이트에 접속하지 않음 (공개 API 없음·자동 수집은 약관 위반)."""
    if body.site not in SOURCE_SITES:
        raise HTTPException(400, "공고 출처를 골라 주세요.")
    site_name = SOURCE_SITES[body.site]["name"]
    text = body.text.strip()
    if len(text) < 80:
        raise HTTPException(400, f"{site_name} 공고 화면의 글을 통째로 복사해 붙여넣어 주세요 (80자 이상).")
    try:
        src = normalize_source_url(body.site, body.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    lid = linkedin_job_id(src) if body.site == "linkedin" else None
    try:
        d, used_ai, err = ai.parse_job_posting(text[:15000], SECTORS, JOB_FAMILIES, site_name), True, None
    except Exception as e:  # noqa: BLE001
        d, used_ai, err = _draft_fallback(text), False, type(e).__name__
    if d.get("job_family") not in JOB_FAMILIES:
        d["job_family"] = family_of(d.get("title") or "")
    # 선택지 밖 값은 비우기 → 화면에서 '직접 확인' 표시
    if d.get("level") not in LEVELS: d["level"] = ""
    if d.get("english") not in ENGLISH_LEVELS: d["english"] = ""
    if d.get("sector") not in SECTORS: d["sector"] = "기타"
    try:
        if d.get("deadline"): date.fromisoformat(d["deadline"])
    except ValueError:
        d["deadline"] = ""
    skills = list(dict.fromkeys([*(d.pop("must_skills", None) or []), *(d.pop("nice_skills", None) or [])]))[:8]
    d["skills"] = skills
    need = {"company": "회사명", "hq": "본사 국가", "title": "포지션", "level": "직급", "years_min": "경력", "salary_min": "연봉(원화)",
            "english": "영어 수준", "location": "근무지", "deadline": "마감일", "recruiter_name": "담당자 이름"}
    missing = [label for k, label in need.items() if d.get(k) in (None, "", 0)]
    if not skills: missing.append("요구 기술")
    if d.get("years_min") is not None and d.get("years_max") is None: missing.append("경력 최대")   # '5+ years'처럼 최대가 없으면 직접 정하게
    if d.get("salary_min") and not d.get("salary_max"): missing.append("연봉 최대")
    return {"draft": d, "missing": missing, "site": body.site, "site_name": site_name, "source_url": src,
            "linkedin_job_id": lid, "duplicate": bool(src and any(j.get("source_url") == src for j in JOBS)),
            "ai": used_ai, "ai_error": err,
            "company_info_note": f"회사 재무·주가·한국 사업 정보는 {site_name} 공고에 없어요. 회사 인연도(①②⑤)를 위해 직접 넣어 주세요."}


@app.get("/api/recruiter/jobs")
def recruiter_my_jobs():
    """구인자가 직접 등록한 공고 목록 (+ 받은 연결 요청 수)."""
    mine = [j for j in JOBS if j.get("source") == "구인자 직접 등록"]
    return [{**j, "requests": sum(1 for a in APPLICATIONS if a["job"]["id"] == j["id"])} for j in mine]


@app.delete("/api/recruiter/jobs/{job_id}")
def recruiter_delete_job(job_id: int):
    if not delete_job(job_id):
        raise HTTPException(404, "직접 등록한 공고만 삭제할 수 있어요.")
    return {"deleted": job_id}


@app.get("/api/admin/db")
def db_info():
    """저장소 상태 (DB 주소·비밀번호·레주메 내용은 보여 주지 않음)."""
    return {"backend": store.backend(), "counts": {**store.counts(), "resume": store.resume_count()},
            "resume_key": resumes.key_source()}


# ---------- 구직자 레주메 장기 보관 (동의한 경우만, 암호화) ----------
class ResumeSaveIn(BaseModel):
    consent: bool
    resume_text: str
    linkedin_url: str | None = None
    expected_salary: int | None = None
    desired_level: str | None = None
    desired_family: str | None = None
    school: str = ""
    hometown: str = ""
    past_companies: list[str] = []
    review: dict | None = None     # AI 첨삭 결과(요약·기술·경력·강점·보완점)
    resume_summary: dict | None = None   # AI 레주메 분석 요약


@app.get("/api/resumes/me")
def my_resume(request: Request):
    """내가 저장한 레주메 (본인만: 링크드인 확인 또는 이 브라우저 쿠키)."""
    return resumes.load(request)


@app.post("/api/resumes/me")
def save_my_resume(body: ResumeSaveIn, request: Request, response: Response):
    if not body.consent:
        raise HTTPException(400, "레주메 보관에 동의해야 저장할 수 있어요.")
    try:
        data = body.model_dump()
        data["linkedin_url"] = resume_file.profile_url(data.get("linkedin_url") or "") or None
        return resumes.save(request, response, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/resumes/me")
def delete_my_resume(request: Request, response: Response):
    """보관한 레주메 바로 삭제 (이전 버전 포함)."""
    return resumes.delete(request, response)


@app.get("/api/recruiter/requests")
def recruiter_requests():
    """구인자가 보는 연결 요청: 사주·생년월일·인연 점수는 빼고 커리어·연봉/직급만."""
    return [{"id": a["id"], "job": {"id": a["job"]["id"], "company": a["job"]["company"], "title": a["job"]["title"]},
             "candidate": a["candidate"], "verified": a.get("verified"),
             "career_score": a["career_score"], "pay_score": a["pay_score"],
             "applied_at": a["applied_at"], "status": a["status"]} for a in APPLICATIONS]


class StatusIn(BaseModel):
    status: str   # 연결 요청됨 / 검토중 / 인터뷰 제안 / 보류


@app.post("/api/recruiter/requests/{req_id}/status")
def recruiter_set_status(req_id: int, body: StatusIn):
    a = next((x for x in APPLICATIONS if x["id"] == req_id), None)
    if not a:
        raise HTTPException(404, "없는 요청이에요.")
    a["status"] = body.status
    store.save("application", a["id"], a)
    return {"id": req_id, "status": a["status"]}


# ---------- 구직자: 링크드인 공고 분석 (특별 섹션) ----------
# 구직자가 링크드인 공고 화면을 복사해 붙여넣으면 직종 · 직급(일반·주니어·시니어·리더) · 예상 연봉 · 인터뷰 핵심 키워드.
# 서버는 링크드인에 접속하지 않음 (공개 API 없음 · 자동 수집은 약관 위반). 결과는 저장하지 않음.
class LinkedInAnalyzeIn(BaseModel):
    url: str = ""
    text: str
    profile: dict = {}


@app.post("/api/linkedin/analyze")
def linkedin_analyze(body: LinkedInAnalyzeIn):
    from . import linkedin_jobs as lj
    text = body.text.strip()
    if len(text) < 80:
        raise HTTPException(400, "링크드인 공고 화면의 글을 통째로 복사해 붙여넣어 주세요 (80자 이상).")
    try:
        src = normalize_source_url("linkedin", body.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        d, used_ai, err = ai.parse_job_posting(text[:15000], SECTORS, JOB_FAMILIES, "링크드인"), True, None
    except Exception as e:  # noqa: BLE001
        d, used_ai, err = _draft_fallback(text), False, type(e).__name__
    skills = list(dict.fromkeys([*(d.get("must_skills") or []), *(d.get("nice_skills") or [])]))[:8]
    if d.get("english") not in ENGLISH_LEVELS:
        d["english"] = ""
    fam = lj.classify_family(d.get("title") or "", text)
    tier = lj.classify_tier(d.get("title") or "", text, d.get("years_min"))
    sal = lj.estimate_salary(d, fam["family"], tier["tier"], JOBS)
    iv = lj.interview_keywords(fam["family"], text, skills)
    out = {"source_url": src, "linkedin_job_id": linkedin_job_id(src) if src else None, "ai": used_ai, "ai_error": err,
           "posting": {"company": d.get("company") or "", "title": d.get("title") or "", "location": d.get("location") or "",
                       "hq": d.get("hq") or "", "years_min": d.get("years_min"), "years_max": d.get("years_max"),
                       "english": d.get("english") or "", "deadline": d.get("deadline") or "", "employment": d.get("employment") or "",
                       "summary": d.get("summary") or [], "skills": skills, "ai_family": d.get("job_family")},
           "family": fam, "tier": tier, "salary": sal, "interview": iv, "me": None}
    # 내 레주메가 있으면: 키워드 매칭률 + 최근 업무 중 이 공고에서 강조할 것
    resume = (body.profile or {}).get("resume_text") or ""
    if resume.strip() and skills:
        tmp = {"id": 0, "company": d.get("company") or "", "title": d.get("title") or "", "skills": skills,
               "years_min": d.get("years_min") or 0, "years_max": d.get("years_max") or (d.get("years_min") or 0) + 4,
               "level": tier["service_level"], "english": d.get("english") or "업무 가능"}
        km = keywords.keyword_match(tmp, resume, body.profile)
        rf = keywords.recent_focus(tmp, resume, body.profile, ALL_SKILLS)
        want = body.profile.get("expected_salary")
        out["me"] = {"rate": km["rate"], "have": [k["kw"] for k in km["rows"] if k["status"] == "있음"][:6], "partial": [k["kw"] for k in km["rows"] if k["status"] == "관련 경험"][:4],
                     "missing": [k["kw"] for k in km["rows"] if k["status"] == "없음" and k["type"] in ("필수 기술", "우대 기술")][:5], "must_ok": km["must_ok"], "must_total": km["must_total"],
                     "focus": rf["items"][:3], "recent": rf["recent"],
                     "salary_fit": (None if not want else "범위 안" if sal["min"] <= want <= sal["max"]
                                    else "범위보다 낮음 (협상 여지)" if want < sal["min"] else "범위보다 높음")}
    return out


# ---------- 구직자: 내 링크드인 공고 가져오기 (데이터 내보내기 ZIP/CSV · 채용 알림 메일) ----------
# 링크드인이 공식으로 주는 '내 데이터'만 사용. 서버는 링크드인에 접속하지 않음. 가져온 목록은 저장하지 않음.
from fastapi import Form  # noqa: E402


@app.post("/api/linkedin/import")
async def linkedin_import(file: UploadFile | None = File(None), text: str = Form(""), profile: str = Form("{}")):
    import json as _json
    from . import linkedin_import as li
    data = await file.read(25 * 1024 * 1024 + 1) if file else None
    if data and len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "파일은 25MB까지 올릴 수 있어요. (데이터 내보내기 ZIP이 크면 'Saved Jobs.csv'·'Job Applications.csv'만 올려 주세요)")
    try:
        jobs, source = li.parse_any(file.filename if file else "", data, text)
    except li.SinglePosting as sp:   # 공고 1개짜리 PDF → 화면이 '자세히 분석'으로 넘겨 바로 분석
        return {"single": True, "text": sp.text[:15000], "url": sp.url, "source": "링크드인 공고 PDF (1개)"}
    except zipfile_error() as e:
        raise HTTPException(400, f"ZIP 파일을 열지 못했어요: {type(e).__name__}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not jobs:
        raise HTTPException(400, "링크드인 공고를 찾지 못했어요. 데이터 내보내기의 'Saved Jobs.csv'·'Job Applications.csv'나 "
                                 "링크드인 채용 알림 메일(공고 링크가 들어 있는 메일)인지 확인해 주세요.")
    try:
        prof = _json.loads(profile or "{}")
    except ValueError:
        prof = {}
    out = li.analyze(jobs, prof if isinstance(prof, dict) else {})
    fams = {}
    for j in out:
        fams[j["family"]] = fams.get(j["family"], 0) + 1
    mine = out[0]["fit"]["my_family"] if out else ""
    return {"source": source, "count": len(out), "jobs": out,
            "summary": {"families": [{"family": f, "n": n} for f, n in sorted(fams.items(), key=lambda x: -x[1])],
                        "kinds": {k: sum(1 for j in out if j["kind"] == k) for k in ("saved", "applied", "alert")},
                        "same_family": sum(1 for j in out if mine and j["family"] == mine),
                        "good": sum(1 for j in out if j["fit"]["score"] >= 70),
                        "my_family": mine, "my_tier": out[0]["fit"]["my_tier"] if out else ""},
            "formula": "참고 적합도 100 = 직종 40(같음 40 · 이웃 직종 20) + 직급 30(같음 30 · 한 단계 15) + 직무명 속 내 기술 30(1개 20 · 2개 이상 30 · 없음 10) — 매칭률·회사 인연도와 별개"}


def zipfile_error():
    import zipfile as _z
    return _z.BadZipFile


# ---------- 하루 한 번 배치 공고 피드 (에이전트 스캔 결과 받기 · 회사 공개 채용 API) ----------
from . import batch as _batch, jobfeed  # noqa: E402

_batch.start_scheduler()   # .env BATCH_TIME=HH:MM 이면 매일 그 시각 ATS 배치


class ScanIn(BaseModel):
    run_at: str | None = None
    items: list[dict]


@app.post("/api/batch/linkedin-scan")
def batch_linkedin_scan(body: ScanIn, request: Request):
    """사용자의 브라우저 에이전트(본인 로그인·읽기만)가 매일 읽은 링크드인 검색 결과를 받음. 서버는 링크드인에 접속하지 않음.
    헤더 X-Batch-Token = ..\\.env 의 BATCH_TOKEN (없으면 받지 않음)."""
    import hmac
    import os
    tok = os.getenv("BATCH_TOKEN", "").strip()
    if not tok:
        raise HTTPException(503, "배치 받기가 꺼져 있어요 — ..\\.env 에 BATCH_TOKEN 을 넣고 서버를 다시 켜 주세요.")
    if not hmac.compare_digest(request.headers.get("X-Batch-Token", ""), tok):
        raise HTTPException(401, "배치 토큰이 맞지 않아요.")
    if not body.items:
        raise HTTPException(400, "items가 비어 있어요.")
    return jobfeed.ingest(body.items, "linkedin-scan", body.run_at)


@app.get("/api/batch/status")
def batch_status():
    import os
    f = jobfeed.feed(days=3650)
    return {"token_set": bool(os.getenv("BATCH_TOKEN", "").strip()), "batch_time": os.getenv("BATCH_TIME", "").strip() or None,
            "ats_config": _batch.CONFIG.exists(), "runs": f["runs"], "total": len(f["items"])}


class FeedIn(BaseModel):
    profile: dict = {}
    days: int = 7


@app.post("/api/feed")
def feed_list(body: FeedIn):
    """최근 N일 배치 공고 + 나와 맞는 순위 (참고 적합도). '오늘 새로' 표시."""
    from . import linkedin_import as li
    f = jobfeed.feed(max(1, min(body.days, 60)))
    rows = [{"title": x["title"], "company": x["company"], "location": x["location"], "job_id": x["job_id"], "url": x["url"],
             "date": x["first_seen"], "kind": "feed", "source": x["source"], "source_name": x["source_name"], "is_new": x["is_new"],
             "tags": x.get("tags", []), "alumni": x.get("alumni", 0), "work_type": x.get("work_type", ""), "posted": x.get("posted", ""),
             "first_seen": x["first_seen"], "runs": x.get("runs", 1)} for x in f["items"]]
    out = li.analyze(rows, body.profile) if rows else []
    # 같은 점수면 오늘 새로 나온 공고 먼저
    out.sort(key=lambda x: (-x["fit"]["score"], not x["is_new"], x["title"]))
    for i, x in enumerate(out):
        x["rank"] = i + 1
    return {"jobs": out, "last_run": f["last_run"], "runs": f["runs"], "new": sum(1 for x in out if x["is_new"]),
            "sources": sorted({x["source_name"] for x in out})}


# ---------- ★ 구인 회사 분석 (링크드인 공고 → 회사별) ----------
class CompaniesIn(BaseModel):
    profile: dict = {}
    saju: dict | None = None
    days: int = 14
    imported: list[dict] = []   # ① 가져오기 결과(화면이 가진 목록)도 함께


@app.post("/api/companies")
def companies(body: CompaniesIn):
    """매일 배치 피드 + 가져온 공고를 회사별로 묶어 채용 규모·신호·나와의 적합을 분석."""
    from . import company_scan, linkedin_import as li
    f = jobfeed.feed(max(1, min(body.days, 60)))
    rows = [{"title": x["title"], "company": x["company"], "location": x["location"], "job_id": x["job_id"], "url": x["url"],
             "date": x["first_seen"], "kind": "feed", "source_name": x["source_name"], "is_new": x["is_new"], "tags": x.get("tags", []),
             "alumni": x.get("alumni", 0), "work_type": x.get("work_type", ""), "posted": x.get("posted", ""), "runs": x.get("runs", 1)}
            for x in f["items"]]
    seen = {r["url"] or r["job_id"] for r in rows}
    for j in body.imported[:300]:
        k = j.get("url") or j.get("job_id")
        if j.get("title") and k not in seen:
            rows.append({k2: j.get(k2) for k2 in ("title", "company", "location", "job_id", "url", "date", "kind")} | {"is_new": False})
            seen.add(k)
    if not rows:
        return {"companies": [], "count": 0, "jobs": 0}
    analyzed = li.analyze(rows, body.profile)
    out = company_scan.analyze_companies(analyzed, body.profile)
    if body.saju:   # 서비스에 있는 회사면 회사 인연도(100점)도
        for c in out:
            if c["service_job_id"]:
                c["company_fit"] = analysis.fit_total(get_job(c["service_job_id"]), body.saju, body.profile)
    return {"companies": out, "count": len(out), "jobs": len(analyzed),
            "formula": "회사 적합도(참고 100) = 가장 잘 맞는 공고 적합도 × 0.6 + 내 직종 공고 비중 × 20 + 채용 활발도 20(공고 수 최대 10 + 새 공고 10) — 매칭률·회사 인연도와 별개"}
