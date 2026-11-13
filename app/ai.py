"""Bedrock Claude 호출: 이력서 첨삭, 사주 풀이, 추천 코멘트."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
REGION = "us-east-1"
_llm = None


def llm():
    global _llm
    if _llm is None:
        from langchain_aws import ChatBedrockConverse
        _llm = ChatBedrockConverse(model=MODEL_ID, region_name=REGION, temperature=0.3)
    return _llm


# ---------- 이력서 첨삭 ----------
class Rewrite(BaseModel):
    before: str = Field(description="원문 문장")
    after: str = Field(description="개선한 문장")


class ResumeReview(BaseModel):
    summary: str = Field(description="이 지원자를 한 문장으로 소개")
    score: int = Field(description="이력서 완성도 0~100")
    strengths: list[str] = Field(description="강점 3개 이내")
    weaknesses: list[str] = Field(description="보완점 3개 이내")
    rewrites: list[Rewrite] = Field(description="고쳐 쓰면 좋은 문장 2~3개")
    skills: list[str] = Field(description="보유 기술 (Python, AWS, React 등 영문 표준 표기)")
    years: int = Field(description="총 실무 경력 연수. 신입이면 0")
    level: str = Field(description="주니어/미들/시니어/리드 중 하나")
    job_family: str = Field(description="지원자 경력에 가장 가까운 직종: 개발/데이터·AI/인프라·클라우드/세일즈/프리세일즈/딜리버리/고객 성공 중 하나")


def review_resume(text: str) -> dict:
    prompt = (
        "당신은 IT 채용 전문 커리어 코치입니다. 아래 프로필(링크드인/리멤버에서 복사한 내용)을 읽고 "
        "이력서 관점에서 첨삭하세요. 프로필에 없는 경력이나 기술을 지어내지 마세요. "
        "나이·성별·출신 등 개인 특성은 평가하지 마세요.\n"
        f"오늘 날짜는 {date.today():%Y-%m-%d} 입니다. '현재/재직중' 경력은 오늘까지로 계산하세요.\n\n"
        f"[프로필]\n{text}"
    )
    return llm().with_structured_output(ResumeReview).invoke(prompt).model_dump()


# ---------- 레주메 분석 요약 (채용 담당자에게도 보이는 요약) ----------
class Career(BaseModel):
    company: str = Field(description="회사명 (레주메에 적힌 그대로)")
    role: str = Field(description="직무·직책")
    period: str = Field(description="기간 (예: 2022.03~현재). 적혀 있지 않으면 빈 문자열")
    highlights: list[str] = Field(description="이 회사에서 한 일 1~3개, 짧게")


class SkillGroup(BaseModel):
    group: str = Field(description="언어 / 프레임워크 / 클라우드·인프라 / 데이터 / AI·ML / 협업·기타 중 하나")
    items: list[str] = Field(description="영문 표준 표기 (Python, AWS 등)")


class Change(BaseModel):
    kind: str = Field(description="추가 / 보완 / 삭제 중 하나")
    text: str = Field(description="무엇이 바뀌었는지 한 문장")


class ResumeSummary(BaseModel):
    headline: str = Field(description="한 줄 소개 (예: 'Python·AWS 백엔드 4년차, 주문/결제 API 전문')")
    summary: list[str] = Field(description="핵심 요약 3문장 (경력·전문 분야·강점), 레주메 근거만")
    careers: list[Career] = Field(description="경력 타임라인, 최근 순")
    achievements: list[str] = Field(description="주요 성과 2~4개. 숫자는 레주메에 있는 것만 (없으면 숫자 없이)")
    skill_groups: list[SkillGroup] = Field(description="기술을 분류")
    years: int = Field(description="총 실무 경력 연수 (인턴 제외, 신입이면 0)")
    level: str = Field(description="주니어/미들/시니어/리드 중 하나")
    certificates: list[str] = Field(description="자격증 (없으면 빈 목록)")
    languages: list[str] = Field(description="외국어 능력 (레주메에 적힌 것만, 없으면 빈 목록)")
    fit_roles: list[str] = Field(description="잘 맞는 외국계 IT 직무 2~3개 (영문 직무명)")
    gaps: list[str] = Field(description="채용 담당자가 물어볼 만한 빈 곳 2~3개 (예: '영어 협업 경험 미기재')")
    changes: list[Change] = Field(description="이전 버전과 비교한 변경점 (이전 버전이 없으면 빈 목록)")


def summarize_resume(text: str, prev_text: str | None = None) -> dict:
    prompt = (
        "당신은 외국계 IT 기업의 시니어 리크루터입니다. 아래 지원자 레주메를 채용 담당자가 30초 안에 파악할 수 있게 "
        "분석·요약하세요. 규칙: 레주메에 없는 경력·기술·숫자를 지어내지 말 것. "
        "나이·성별·출신 지역·학교 서열·가족 등 개인 특성은 평가하거나 언급하지 말 것. 한국어로 작성.\n"
        f"오늘 날짜는 {date.today():%Y-%m-%d} 입니다. '현재/재직중' 경력은 오늘까지로 계산하고, 경력 연수는 인턴을 빼고 만 연수로.\n\n"
        f"[레주메]\n{text}"
    )
    if prev_text:
        prompt += f"\n\n[이전 버전 레주메 — 변경점(changes)만 비교에 사용]\n{prev_text}"
    return llm().with_structured_output(ResumeSummary).invoke(prompt).model_dump()


# ---------- 링크드인 공고 글 → 공고 등록 칸 (구인자가 붙여넣은 글만, 링크드인 접속 없음) ----------
class JobDraft(BaseModel):
    company: str = Field(description="회사명 (공고에 적힌 그대로, 없으면 빈 문자열)")
    hq: str = Field(description="본사 국가를 한국어로 (예: 미국). 공고에서 알 수 없으면 빈 문자열")
    title: str = Field(description="포지션명 (영문 그대로)")
    level: str = Field(description="주니어/미들/시니어/리드 중 하나. 'Senior'→시니어, 'Staff/Principal/Lead/Manager'→리드, 'Associate/Junior/Entry'→주니어, 그 외 경력 연수로 판단. 근거 없으면 빈 문자열")
    years_min: int | None = Field(description="최소 경력 연수 ('5+ years'→5). 없으면 null")
    years_max: int | None = Field(description="최대 경력 연수. 범위가 없으면 null")
    must_skills: list[str] = Field(description="필수(Requirements/Qualifications) 기술, 중요한 순서로 최대 5개, 영문 표준 표기 (Python, AWS, Kubernetes)")
    nice_skills: list[str] = Field(description="우대(Preferred/Nice to have) 기술 최대 5개")
    salary_min: int | None = Field(description="연봉 최소, 만원 단위. 공고에 원화로 적혀 있을 때만 (예: 8,000만원→8000). 달러 등 외화·없음이면 null")
    salary_max: int | None = Field(description="연봉 최대, 만원 단위. 원화로 적혀 있을 때만, 아니면 null")
    salary_text: str = Field(description="공고에 적힌 급여 문구 그대로 (외화 포함). 없으면 빈 문자열")
    english: str = Field(description="필요한 영어 수준: 유창/비즈니스/업무 가능/기초 중 하나. 'fluent/native'→유창, 'business/professional'→비즈니스, 영어 공고인데 언급 없으면 업무 가능. 근거 없으면 빈 문자열")
    location: str = Field(description="근무지를 한국어로 (예: 서울 강남, 원격 근무, 하이브리드 서울). 없으면 빈 문자열")
    deadline: str = Field(description="지원 마감일 YYYY-MM-DD. 공고에 날짜가 있을 때만, 없으면 빈 문자열 (임의로 정하지 말 것)")
    recruiter_name: str = Field(description="공고에 적힌 채용 담당자 이름 (Meet the hiring team 등). 없으면 빈 문자열")
    sector: str = Field(description="회사·포지션 분야. 주어진 분야 목록 중 하나. 판단 어려우면 '기타'")
    employment: str = Field(description="고용 형태 (정규직/계약직/인턴 등), 없으면 빈 문자열")
    summary: list[str] = Field(description="포지션이 하는 일 2~3줄 요약 (한국어, 공고 근거만)")
    job_family: str = Field(description="직종: 주어진 직종 목록 중 하나. 영업(Account Executive 등)=세일즈, 솔루션/세일즈 엔지니어=프리세일즈, Delivery/PM/구축/컨설턴트=딜리버리, Customer Success/TAM=고객 성공")

    @field_validator("years_min", "years_max", "salary_min", "salary_max", mode="before")
    @classmethod
    def _blank_is_none(cls, v):
        """AI가 'null'·''·'없음' 같은 글자로 줘도 '값 없음'으로 처리 (숫자 글자는 숫자로)."""
        if isinstance(v, str):
            t = v.strip().replace(",", "").lower()
            if t in ("", "null", "none", "n/a", "없음", "-"):
                return None
            return int(float(t)) if t.replace(".", "", 1).isdigit() else None
        return v


def parse_job_posting(text: str, sectors: list[str], families: list[str] | None = None, site: str = "링크드인") -> dict:
    prompt = (
        f"당신은 외국계 IT 채용 담당자를 돕는 어시스턴트입니다. 아래는 채용 담당자가 {site} 채용 공고 화면에서 직접 복사해 붙여넣은 글입니다. "
        "공고 등록 칸에 맞게 정리하세요. 규칙: 공고에 없는 내용은 지어내지 말고 빈 값/null로 둘 것(특히 연봉·마감일·담당자). "
        "나이·성별·국적 등 차별적 조건은 옮기지 말 것. 한국어로 작성.\n"
        f"오늘 날짜: {date.today():%Y-%m-%d}. 분야 목록: {', '.join(sectors)}. 직종 목록: {', '.join(families or [])}\n\n"
        f"[{site} 공고 글]\n{text}"
    )
    return llm().with_structured_output(JobDraft).invoke(prompt).model_dump()


# ---------- 사주 풀이 ----------
class SajuReading(BaseModel):
    personality: str = Field(description="일간과 오행 분포로 본 성향, 3~4문장")
    work_style: str = Field(description="어울리는 IT 직무와 일하는 방식, 2~3문장")
    this_year: str = Field(description="올해 커리어·이직 운세, 3~4문장")
    best_months: list[str] = Field(description="이직·지원에 좋은 달 2~3개. 반드시 제공된 '좋은 달' 계산값에서 고를 것 (예: '12월')")
    company_types: list[str] = Field(description="잘 맞는 회사 유형 3개 (예: '빠르게 성장하는 스타트업')")
    water: str = Field(description="물(水)이 있는지·얼마나·나에게 어떤 역할인지와 커리어에 주는 의미, 3~4문장")
    move_now: str = Field(description="지금(오늘) 지원하면 이직이 될지: 계산된 이직운 점수·판정·근거를 풀어서 설명, 3~4문장")
    advice: str = Field(description="한 줄 조언")


def read_saju(saju: dict, this_year: int, this_year_gz: str) -> dict:
    pillars = " / ".join(f"{p['name']} {p['gz']}" for p in saju["pillars"])
    prompt = (
        "당신은 명리학 해석가입니다. 아래는 프로그램이 계산한 사주팔자입니다. 계산값을 바꾸지 말고 "
        "이 값만 근거로 커리어 관점의 풀이를 따뜻하고 구체적으로 써 주세요.\n\n"
        f"사주: {pillars}\n일간: {saju['day_master']}({saju['day_master_elem']})\n"
        f"오행 분포: {saju['elements']} (가장 강함 {saju['strongest']}, 가장 약함 {saju['weakest']})\n"
        f"시주 포함 여부: {saju['has_hour']}\n올해: {this_year}년 {this_year_gz}년\n"
    )
    w, mv = saju.get("water"), saju.get("move")
    if w:
        prompt += (f"물(水): {w['count']}개({w['status']}), 위치 {w['where'] or '없음'}, "
                   f"나에게 {w['role']}({w['role_meaning']})\n")
    if mv:
        best = ", ".join(f"{b['ym']}({b['score']}점)" for b in mv["best"])
        prompt += (f"오늘({mv['date']}, {mv['year_gz']}년 {mv['month_gz']}월) 지원 시 이직운: {mv['score']}점, "
                   f"판정 '{mv['verdict']}'\n근거: {'; '.join(mv['notes'])}\n좋은 달(계산값): {best}\n")
    prompt += ("점수·판정·좋은 달은 위 계산값을 그대로 쓰고 바꾸지 마세요. "
               "합격을 보장하는 표현은 쓰지 말고, 명리 해석은 참고용이라는 톤을 유지하세요.")
    return llm().with_structured_output(SajuReading).invoke(prompt).model_dump()


# ---------- 추천 코멘트 (상위 공고 한 번에) ----------
class JobComment(BaseModel):
    job_id: int
    comment: str = Field(description="이 공고를 추천하는 이유와 준비할 점, 2문장")


class JobComments(BaseModel):
    items: list[JobComment]


def comment_jobs(profile: dict, top: list[dict]) -> dict[int, str]:
    lines = [
        f"- id {r['job']['id']}: {r['job']['company']}({r['job']['hq']} 본사) {r['job']['title']} | 일치 기술 {r['career']['matched']} "
        f"| 부족 기술 {r['career']['missing']} | {r['career']['notes'][1]} | {' / '.join(r['pay']['notes'])} "
        f"| 영어 {r['job']['english']} | 인연 {r['affinity']['notes'][0]}"
        for r in top
    ]
    prompt = (
        "외국계 IT 기업 전문 커리어 코치로서 아래 추천 공고마다 2문장 코멘트를 써 주세요. "
        "첫 문장은 왜 맞는지(커리어·연봉/직급·인연), 둘째 문장은 지원 전 준비할 점(영문 이력서·인터뷰 포함). "
        "지원자 정보에 없는 경력을 지어내지 마세요.\n"
        f"지원자: 기술 {profile.get('skills')}, 경력 {profile.get('years')}년, 현재 {profile.get('level')}, "
        f"희망 {profile.get('desired_level')}, 기대 연봉 {profile.get('expected_salary')}만\n"
        + "\n".join(lines)
    )
    out = llm().with_structured_output(JobComments).invoke(prompt)
    return {c.job_id: c.comment for c in out.items}


# ---------- 인터뷰 전략 (회사 1곳) ----------
class QA(BaseModel):
    q: str = Field(description="예상 질문 (영어 질문이면 영어 + 괄호 안에 한국어 뜻)")
    tip: str = Field(description="답변 방향, 1~2문장, 지원자의 실제 경력·기술만 근거로")


class InterviewPlan(BaseModel):
    key_messages: list[str] = Field(description="면접에서 꼭 전달할 핵심 메시지 3개")
    questions: list[QA] = Field(description="예상 질문 5개 (자기소개·기술·부족 기술·지원 동기·설계/코딩)")
    weakness_plan: list[str] = Field(description="부족 기술·약점 대응 방법 2~3개 (지원 전 준비 행동)")
    ask_them: list[str] = Field(description="면접관에게 할 역질문 3개 (회사 뉴스·재무 근거)")
    english: str = Field(description="영어 인터뷰 준비 팁 1~2문장")
    timing: str = Field(description="지원·면접 시기 조언 1~2문장. 제공된 좋은 달 계산값만 사용, 합격 보장 표현 금지")


def interview_plan(job: dict, profile: dict, career: dict, news: list[dict], fin: dict | None, best: list[dict]) -> dict:
    fin_line = (f"성장률 연 {fin['info']['growth']}%, 영업이익률 {fin['info']['margin']}%, 한국 확대 {fin['info']['expand']}({fin['info']['plan']})"
                if fin else "재무 정보 없음")
    prompt = (
        "외국계 IT 기업 면접 코치로서 아래 지원자가 이 회사 인터뷰를 준비하는 전략을 써 주세요. "
        "지원자 정보에 없는 경력·성과를 지어내지 말고, 나이·성별·출신으로 판단하지 마세요. "
        "합격을 보장하는 표현은 쓰지 마세요. 사주는 시기 조언에만 참고로 쓰세요.\n"
        f"[회사] {job['company']}({job['hq']} 본사) / {job['title']} / {job['level']} / 경력 {job['years_min']}~{job['years_max']}년 "
        f"/ 요구 기술 {job['skills']} / 영어 {job['english']}\n"
        f"[재무] {fin_line}\n[한국 사업 뉴스(가상 예시)] " + "; ".join(f"{n['date']} {n['title']}" for n in news) + "\n"
        f"[지원자] 요약 {profile.get('summary')} / 기술 {profile.get('skills')} / 경력 {profile.get('years')}년 / 현재 {profile.get('level')} "
        f"/ 강점 {profile.get('strengths')} / 보완점 {profile.get('weaknesses')}\n"
        f"[일치 기술] {career['matched']} [부족 기술] {career['missing']}\n"
        f"[레주메 최근 업무 강조 키워드] {profile.get('recent_focus') or '없음'} — 핵심 메시지 첫 번째는 이 최근 업무를 중심으로\n"
        f"[좋은 달(계산값)] {', '.join(b['ym'] for b in best) or '없음'}"
    )
    out = llm().with_structured_output(InterviewPlan).invoke(prompt).model_dump()
    out["source"] = "AI 코치 (Claude)"
    return out
