"""외국계 IT 기업 채용 공고 (데모용 예시 20개, 회사·담당자 모두 가상).

- 실제 서비스에서는 외국계 기업의 채용 담당자(구인자)가 '구인자' 화면에서 공고를 직접 등록합니다.
- salary_min/max 단위는 만원(연봉). 나이 조건은 넣지 않습니다 (연령차별 금지).
- deadline(마감일)은 사주 인연 계산에서 '회사 쪽 날짜'로 쓰입니다.
"""
from __future__ import annotations

LEVELS = ["주니어", "미들", "시니어", "리드"]

# ── 직종 (외국계 IT 회사의 직무군) ──
# 점수(매칭률·회사 인연도)에는 넣지 않고 걸러 보기·표시에만 씀 (배점 변경은 사용자 확인 필요)
JOB_FAMILIES = ["개발", "데이터·AI", "인프라·클라우드", "세일즈", "프리세일즈", "딜리버리", "고객 성공"]
FAMILY_DESC = {
    "개발": "백엔드·프론트엔드·모바일·게임·임베디드·QA",
    "데이터·AI": "데이터 엔지니어·ML·LLM 애플리케이션",
    "인프라·클라우드": "DevOps·SRE·클라우드 아키텍트·보안",
    "세일즈": "Account Executive·파트너 영업·영업 관리",
    "프리세일즈": "솔루션 엔지니어·세일즈 엔지니어·기술 컨설팅(영업 단계)",
    "딜리버리": "Delivery·PM·구축(Implementation)·컨설턴트",
    "고객 성공": "Customer Success·Technical Account Manager·지원",
}
# 직무명으로 직종 판단 (위에서부터 먼저 맞는 것)
_FAMILY_RULES = [
    ("프리세일즈", r"solutions? engineer|sales engineer|pre-?sales|프리세일즈|solution consultant|솔루션 엔지니어"),
    ("고객 성공", r"customer success|technical account manager|\bTAM\b|support engineer|고객 성공"),
    ("딜리버리", r"delivery|project manager|program manager|implementation|consultant|\bPM\b|딜리버리|구축|컨설턴트"),
    ("세일즈", r"account executive|account manager|sales|business development|\bBDR?\b|\bSDR\b|영업|세일즈"),
    ("데이터·AI", r"data|machine learning|\bML\b|\bAI\b|LLM|analytics|데이터"),
    ("인프라·클라우드", r"devops|site reliability|\bSRE\b|cloud|infra|security|platform ops|인프라|보안"),
]


def family_of(title: str) -> str:
    import re
    for fam, pat in _FAMILY_RULES:
        if re.search(pat, title or "", re.I):
            return fam
    return "개발"


# ── 공고 출처 (구직 사이트) — 서버는 이 사이트들에 접속하지 않음. 구인자가 붙여넣은 글 + 원문 주소만 ──
SOURCE_SITES = {
    "linkedin":    {"name": "링크드인", "domains": ["linkedin.com"]},
    "wanted":      {"name": "원티드", "domains": ["wanted.co.kr"]},
    "remember":    {"name": "리멤버", "domains": ["rememberapp.co.kr"]},
    "jumpit":      {"name": "점핏", "domains": ["jumpit.saramin.co.kr"]},
    "saramin":     {"name": "사람인", "domains": ["saramin.co.kr"]},
    "jobkorea":    {"name": "잡코리아", "domains": ["jobkorea.co.kr"]},
    "rocketpunch": {"name": "로켓펀치", "domains": ["rocketpunch.com"]},
    "careers":     {"name": "회사 채용 페이지", "domains": []},     # 아무 https 주소
    "direct":      {"name": "직접 작성", "domains": None},          # 주소 없음
}
SAMPLE_SOURCE = {"key": "sample", "name": "예시 공고(가상)"}

_R = "Talent Acquisition Partner"


def _j(id, company, hq, title, level, ymin, ymax, skills, smin, smax, english, location, deadline, recruiter):
    return {"id": id, "company": company, "hq": hq, "company_type": f"외국계 · {hq} 본사", "title": title,
            "level": level, "years_min": ymin, "years_max": ymax, "skills": skills,
            "salary_min": smin, "salary_max": smax, "salary": f"{smin:,}~{smax:,}만",
            "english": english, "location": location, "deadline": deadline,
            "recruiter": {"name": recruiter, "role": _R}, "source": "예시 공고",
            "family": family_of(title), "source_site": SAMPLE_SOURCE["key"], "source_site_name": SAMPLE_SOURCE["name"],
            "info": COMPANY_INFO.get(company)}


# 회사 정보 (모두 가상 예시 값, 기준일 2026-11-12).
# 실제 서비스: 구인자가 등록 + 공시(DART 등)·시세 API로 갱신. 종목코드는 실제 종목과 겹치지 않게 표시하지 않음.
# listed: 상장 시장 or None(비상장), price/chg: 주가·전일 대비 %, revenue: 글로벌 연매출(억 달러),
# emp: 글로벌 직원 수, emp_kr: 한국 법인 인원, growth: 향후 3년 연평균 매출 성장률 전망(%),
# expand: 한국 확대 가능성 (높음/보통/낮음), plan: 확대 근거
def _c(listed, price, chg, revenue, emp, emp_kr, growth, expand, plan):
    return {"listed": listed, "price": price, "chg": chg, "revenue": revenue, "emp": emp, "emp_kr": emp_kr,
            "growth": growth, "expand": expand, "plan": plan, "as_of": "2026-11-12", "sample": True}


COMPANY_INFO = {
    "Aeroloop Korea":   _c("NASDAQ", "$42.10", 1.8, 8.5, 3200, 85, 18, "높음", "서울 R&D 센터 2배 증원 계획"),
    "Brightwave Data":  _c("SGX", "S$18.40", -0.6, 4.2, 1900, 60, 22, "높음", "아시아 데이터센터 신규 2곳 구축"),
    "Corvant Payments": _c("LSE", "£31.75", 0.9, 21.0, 7800, 140, 12, "보통", "국내 간편결제 제휴 확대"),
    "Delmora Health":   _c(None, None, None, 2.1, 950, 40, 25, "높음", "시리즈 C 투자 유치, 아시아 진출 거점"),
    "Elyra AI Korea":   _c("NASDAQ", "$128.60", 3.2, 15.4, 4100, 120, 35, "높음", "생성형 AI 한국어 모델 팀 신설"),
    "Fjordstack":       _c("Oslo Børs", "NOK 214", 0.4, 3.0, 1300, 25, 15, "보통", "원격 엔지니어 채용 확대"),
    "Granite Shield Security": _c("NASDAQ", "$76.30", -1.2, 9.8, 3600, 55, 17, "보통", "금융권 보안 고객 증가"),
    "Halcyon Commerce": _c("NYSE", "$54.90", 0.2, 30.5, 12000, 160, 9, "보통", "크로스보더 커머스 운영팀 유지"),
    "Ivorpath Mobility": _c("XETRA", "€67.20", -0.3, 12.7, 5400, 90, 14, "높음", "국내 완성차 협력 SW 조직 확대"),
    "Junipra Apps":     _c("TSE", "¥2,480", 1.1, 5.6, 2700, 70, 11, "보통", "한·일 공동 앱 서비스 운영"),
    "Kestrelbyte Cloud": _c("NYSE", "$212.40", 2.4, 68.0, 21000, 300, 20, "높음", "서울 리전 2단계 증설"),
    "Lumora Games":     _c(None, None, None, 3.4, 800, 45, 16, "보통", "아시아 퍼블리싱 서버 이전"),
    "Mirefield Analytics": _c("TSX", "C$39.80", 0.7, 6.1, 2200, 50, 24, "높음", "AI 분석 플랫폼 아시아 본부 설립"),
    "Norvale Robotics": _c("SIX", "CHF 88.50", -0.8, 7.9, 3000, 65, 19, "높음", "판교 로봇 SW 연구소 확장"),
    "Orbisfin":         _c("HKEX", "HK$56.30", 1.5, 11.2, 4500, 110, 13, "보통", "디지털 자산 결제 라이선스 추진"),
    "Pellucid Labs":    _c(None, None, None, 1.6, 600, 30, 40, "높음", "한국 AI 플랫폼 조직 신설 (초기 멤버)"),
    "Quillon Software": _c("Euronext Dublin", "€22.10", 0.0, 2.8, 1500, 35, 8, "낮음", "기존 QA 조직 유지"),
    "Ravencrest Infra": _c("ASX", "A$14.90", 0.5, 4.7, 2000, 40, 15, "보통", "아태 운영센터 통합"),
    "Solenne Media":    _c("Euronext Paris", "€45.60", -0.4, 9.1, 3800, 75, 10, "보통", "K-콘텐츠 제휴 서비스 확대"),
    "Tidemark Semicon": _c("Euronext Amsterdam", "€310.20", 1.9, 95.0, 26000, 420, 21, "높음", "국내 반도체 고객 지원 엔지니어링 확대"),
}


JOBS = [
    _j(1, "Aeroloop Korea", "미국", "Backend Engineer (Python)", "주니어", 0, 2, ["Python", "FastAPI", "PostgreSQL", "Docker"], 4800, 6000, "업무 가능", "서울 강남", "2026-11-20", "정유진"),
    _j(2, "Brightwave Data", "싱가포르", "Data Engineer", "미들", 3, 6, ["Python", "Spark", "Airflow", "AWS", "SQL"], 7000, 8800, "비즈니스", "서울 광화문", "2026-11-25", "한서준"),
    _j(3, "Corvant Payments", "영국", "Senior Backend Engineer (Java)", "시니어", 7, 12, ["Java", "Spring", "Kafka", "MySQL", "AWS"], 9500, 12500, "비즈니스", "서울 을지로", "2026-11-30", "오민지"),
    _j(4, "Delmora Health", "독일", "Frontend Engineer (React)", "주니어", 1, 3, ["JavaScript", "TypeScript", "React", "CSS"], 5000, 6200, "업무 가능", "서울 성수", "2026-12-03", "윤재현"),
    _j(5, "Elyra AI Korea", "미국", "LLM Application Engineer", "미들", 2, 5, ["Python", "LangChain", "LangGraph", "AWS", "RAG"], 7500, 9800, "비즈니스", "서울 역삼", "2026-12-05", "강하린"),
    _j(6, "Fjordstack", "노르웨이", "DevOps Engineer", "미들", 3, 7, ["AWS", "Kubernetes", "Terraform", "Docker", "Linux"], 8000, 10000, "비즈니스", "원격 근무", "2026-12-08", "임도윤"),
    _j(7, "Granite Shield Security", "이스라엘", "Security Engineer", "시니어", 6, 10, ["Linux", "네트워크", "보안", "Python"], 9000, 11500, "비즈니스", "서울 구로", "2026-12-10", "서지아"),
    _j(8, "Halcyon Commerce", "미국", "Full-stack Engineer", "미들", 2, 5, ["TypeScript", "React", "Node.js", "PostgreSQL"], 6500, 8200, "업무 가능", "원격 근무", "2026-12-12", "조은우"),
    _j(9, "Ivorpath Mobility", "독일", "Android Engineer", "미들", 3, 6, ["Kotlin", "Android", "Java"], 7000, 8800, "업무 가능", "서울 서초", "2026-12-14", "백소율"),
    _j(10, "Junipra Apps", "일본", "iOS Engineer", "주니어", 0, 3, ["Swift", "iOS", "Git"], 4800, 6200, "기초 (일본어 우대)", "서울 마포", "2026-12-15", "신하준"),
    _j(11, "Kestrelbyte Cloud", "미국", "Cloud Solutions Architect", "시니어", 7, 12, ["AWS", "Kubernetes", "Python", "Terraform"], 11000, 14500, "유창", "서울 삼성", "2026-12-16", "권나은"),
    _j(12, "Lumora Games", "핀란드", "Game Server Engineer", "미들", 3, 6, ["C#", "Redis", "AWS", "Docker"], 6800, 8500, "업무 가능", "판교", "2026-12-18", "황시우"),
    _j(13, "Mirefield Analytics", "캐나다", "Machine Learning Engineer", "미들", 2, 6, ["Python", "PyTorch", "MLOps", "AWS"], 8000, 10500, "비즈니스", "서울 역삼", "2026-12-19", "문채원"),
    _j(14, "Norvale Robotics", "스위스", "Embedded Software Engineer", "시니어", 6, 11, ["C++", "Linux", "ROS"], 8500, 11000, "비즈니스", "판교", "2026-12-21", "장예준"),
    _j(15, "Orbisfin", "홍콩", "Backend Lead (Go)", "리드", 9, 15, ["Go", "Kubernetes", "PostgreSQL", "Kafka", "AWS"], 13000, 17000, "유창", "서울 여의도", "2026-12-22", "유다인"),
    _j(16, "Pellucid Labs", "미국", "AI Platform Engineer", "시니어", 5, 10, ["Python", "LangChain", "AWS", "Kubernetes", "FastAPI"], 10000, 13500, "유창", "서울 강남", "2026-12-24", "남건우"),
    _j(17, "Quillon Software", "아일랜드", "QA Automation Engineer", "주니어", 1, 3, ["Python", "Selenium", "Git"], 4500, 5800, "업무 가능", "서울 영등포", "2026-12-26", "노서아"),
    _j(18, "Ravencrest Infra", "호주", "Site Reliability Engineer", "미들", 3, 7, ["Linux", "Kubernetes", "Prometheus", "Go", "AWS"], 8000, 10200, "비즈니스", "원격 근무", "2026-12-28", "하지호"),
    _j(19, "Solenne Media", "프랑스", "Product Engineer (Python)", "미들", 2, 5, ["Python", "Django", "PostgreSQL", "AWS"], 6500, 8000, "업무 가능", "서울 성수", "2026-12-30", "고윤서"),
    _j(20, "Tidemark Semicon", "네덜란드", "Engineering Manager", "리드", 10, 16, ["Python", "AWS", "Kubernetes", "리더십"], 14000, 18000, "유창", "판교", "2026-12-31", "차민재"),
    # 세일즈 · 프리세일즈 · 딜리버리 · 고객 성공 (가상, 기존 예시 회사의 다른 직무)
    _j(21, "Kestrelbyte Cloud", "미국", "Enterprise Account Executive", "시니어", 7, 12, ["B2B 영업", "Enterprise Sales", "Salesforce", "클라우드", "협상"], 12000, 16000, "유창", "서울 삼성", "2026-12-11", "권나은"),
    _j(22, "Elyra AI Korea", "미국", "Solutions Engineer (Presales)", "미들", 4, 8, ["Python", "AWS", "LLM", "기술 PoC", "고객 데모"], 9000, 12000, "비즈니스", "서울 역삼", "2026-12-09", "강하린"),
    _j(23, "Tidemark Semicon", "네덜란드", "Technical Delivery Manager", "시니어", 8, 14, ["PMP", "Agile", "Jira", "리스크 관리", "고객 커뮤니케이션"], 11000, 14000, "유창", "판교", "2026-12-17", "차민재"),
    _j(24, "Brightwave Data", "싱가포르", "Implementation Consultant", "미들", 3, 7, ["SQL", "데이터 마이그레이션", "요구사항 분석", "Jira"], 7000, 9000, "비즈니스", "서울 광화문", "2026-12-13", "한서준"),
    _j(25, "Mirefield Analytics", "캐나다", "Customer Success Manager", "미들", 3, 6, ["고객 성공", "SaaS", "온보딩", "Salesforce", "데이터 분석"], 6500, 8500, "비즈니스", "서울 역삼", "2026-12-23", "문채원"),
    _j(26, "Corvant Payments", "영국", "Partner Sales Manager", "시니어", 6, 10, ["파트너 영업", "B2B 영업", "핀테크", "협상", "Salesforce"], 10000, 13000, "비즈니스", "서울 을지로", "2026-12-27", "오민지"),
]

# 재무 보강 (가상): yoy 전년 매출 성장 %, margin 영업이익률 %, w52 최근 52주 주가 변동 % (비상장 None)
_FIN = {
    "Aeroloop Korea": (21, 12, 34), "Brightwave Data": (26, 9, 18), "Corvant Payments": (11, 18, 6),
    "Delmora Health": (48, -8, None), "Elyra AI Korea": (52, 15, 71), "Fjordstack": (14, 7, 9),
    "Granite Shield Security": (19, 16, -4), "Halcyon Commerce": (7, 5, -12), "Ivorpath Mobility": (15, 10, 11),
    "Junipra Apps": (9, 13, 3), "Kestrelbyte Cloud": (24, 22, 41), "Lumora Games": (12, 6, None),
    "Mirefield Analytics": (29, 11, 27), "Norvale Robotics": (22, 14, 19), "Orbisfin": (13, 17, 8),
    "Pellucid Labs": (85, -20, None), "Quillon Software": (4, 8, -9), "Ravencrest Infra": (16, 9, 7),
    "Solenne Media": (8, 10, -3), "Tidemark Semicon": (23, 28, 37),
}
for _name, (_yoy, _mg, _w52) in _FIN.items():
    COMPANY_INFO[_name].update({"yoy": _yoy, "margin": _mg, "w52": _w52})

# 한국 기업과의 사업 추진 뉴스 (모두 가상 예시: 회사·파트너·기사 전부 지어낸 데모 데이터)
# 실제 서비스: 뉴스 검색 API로 수집 → AI 요약. kw = 기사에 나온 기술 키워드 (내 기술과 연결)
def _n(date, title, partner, kind, kw):
    return {"date": date, "title": title, "partner": partner, "kind": kind, "kw": kw, "source": "예시 뉴스(가상)"}


NEWS = {
    "Aeroloop Korea": [_n("2026-10-28", "Aeroloop, 한빛물류와 항공화물 예약 API 공동 개발", "한빛물류", "공동 개발", ["Python", "FastAPI"]),
                       _n("2026-09-14", "Aeroloop 서울 R&D 센터 인력 2배 확대 발표", None, "한국 투자", ["Docker"])],
    "Brightwave Data": [_n("2026-11-03", "Brightwave, 누리뱅크 데이터 레이크 구축 수주", "누리뱅크", "공급 계약", ["Spark", "AWS"]),
                        _n("2026-08-21", "Brightwave·세온리테일 고객 분석 MOU", "세온리테일", "업무 협약(MOU)", ["SQL", "Airflow"])],
    "Corvant Payments": [_n("2026-10-10", "Corvant, 다온페이와 해외 결제 연동 제휴", "다온페이", "제휴", ["Java", "Kafka"])],
    "Delmora Health": [_n("2026-10-02", "Delmora, 한결병원그룹과 원격진료 화면 공동 개발", "한결병원그룹", "공동 개발", ["React", "TypeScript"])],
    "Elyra AI Korea": [_n("2026-11-05", "Elyra AI, 미래손해보험 상담 LLM 도입 계약", "미래손해보험", "공급 계약", ["LangChain", "RAG"]),
                       _n("2026-09-30", "Elyra AI·가온통신 한국어 AI 에이전트 공동 연구", "가온통신", "공동 개발", ["LangGraph", "Python"])],
    "Fjordstack": [_n("2026-09-08", "Fjordstack, 새봄게임즈 클라우드 이전 지원", "새봄게임즈", "공급 계약", ["Kubernetes", "Terraform"])],
    "Granite Shield Security": [_n("2026-10-19", "Granite Shield, 한별증권 보안관제 수주", "한별증권", "공급 계약", ["보안", "네트워크"])],
    "Halcyon Commerce": [_n("2026-07-25", "Halcyon, 소담몰 역직구 플랫폼 연동", "소담몰", "제휴", ["Node.js", "React"])],
    "Ivorpath Mobility": [_n("2026-10-22", "Ivorpath, 대륙자동차 차량 앱 소프트웨어 공급", "대륙자동차", "공급 계약", ["Kotlin", "Android"]),
                          _n("2026-08-11", "Ivorpath·푸른모터스 전기차 충전 앱 협력", "푸른모터스", "업무 협약(MOU)", ["Android"])],
    "Junipra Apps": [_n("2026-09-02", "Junipra, 하늘여행 한·일 여행 앱 공동 출시", "하늘여행", "공동 개발", ["Swift", "iOS"])],
    "Kestrelbyte Cloud": [_n("2026-11-07", "Kestrelbyte, 서울 리전 2단계 증설… 국내 기업 고객 확대", None, "한국 투자", ["AWS", "Kubernetes"]),
                          _n("2026-10-15", "Kestrelbyte·한마음금융 클라우드 전환 계약", "한마음금융", "공급 계약", ["Terraform", "Python"])],
    "Lumora Games": [_n("2026-08-29", "Lumora, 별빛엔터와 모바일 게임 국내 퍼블리싱", "별빛엔터", "제휴", ["C#", "Redis"])],
    "Mirefield Analytics": [_n("2026-10-26", "Mirefield, 온누리유통 수요예측 AI 도입", "온누리유통", "공급 계약", ["PyTorch", "MLOps"])],
    "Norvale Robotics": [_n("2026-10-08", "Norvale, 동해중공업 물류로봇 소프트웨어 공동 개발", "동해중공업", "공동 개발", ["C++", "ROS"])],
    "Orbisfin": [_n("2026-09-18", "Orbisfin, 바른저축은행 디지털 결제 인프라 구축", "바른저축은행", "공급 계약", ["Go", "Kafka"])],
    "Pellucid Labs": [_n("2026-11-01", "Pellucid Labs 한국 법인 설립… 초기 엔지니어 채용", None, "한국 투자", ["Python", "LangChain"])],
    "Quillon Software": [],
    "Ravencrest Infra": [_n("2026-09-25", "Ravencrest, 태평양통신 서비스 안정화(SRE) 계약", "태평양통신", "공급 계약", ["Kubernetes", "Prometheus"])],
    "Solenne Media": [_n("2026-10-12", "Solenne, 아리랑스튜디오와 K-콘텐츠 추천 서비스 제휴", "아리랑스튜디오", "제휴", ["Python", "Django"])],
    "Tidemark Semicon": [_n("2026-11-06", "Tidemark, 한국반도체소재와 장비 소프트웨어 협력 확대", "한국반도체소재", "업무 협약(MOU)", ["Python", "AWS"]),
                         _n("2026-10-01", "Tidemark 판교 엔지니어링 센터 증원", None, "한국 투자", ["Kubernetes"])],
}

ALL_SKILLS = sorted({s for j in JOBS for s in j["skills"]})


def get_job(job_id: int) -> dict | None:
    return next((j for j in JOBS if j["id"] == job_id), None)


EXPAND_LEVELS = ["높음", "보통", "낮음"]
ENGLISH_LEVELS = ["기초", "업무 가능", "비즈니스", "유창"]
NEWS_KINDS = ["제휴", "공동 개발", "공급 계약", "업무 협약(MOU)", "한국 투자"]


def build_job(data: dict, job_id: int) -> dict:
    """구인자 입력 → 공고 dict (목록에 넣지는 않음, 미리보기에도 사용)."""
    job = _j(job_id, data["company"].strip(), data["hq"].strip(), data["title"].strip(), data["level"],
             data["years_min"], data["years_max"], data["skills"], data["salary_min"], data["salary_max"],
             data.get("english", "업무 가능"), data["location"].strip(), data["deadline"], data["recruiter_name"].strip())
    job["source"] = "구인자 직접 등록"
    job["sector"] = data.get("sector") or "기타"
    job["family"] = data.get("family") if data.get("family") in JOB_FAMILIES else family_of(job["title"])
    site = data.get("source_site") if data.get("source_site") in SOURCE_SITES else "direct"
    job["source_site"], job["source_site_name"] = site, SOURCE_SITES[site]["name"]
    if data.get("source_url"):   # 구직 사이트에서 가져온 경우: 원문 링크만 (내용은 구인자가 확인해 등록)
        job["source_url"] = data["source_url"]
    listed = (data.get("listed") or "").strip() or None
    job["info"] = {
        "listed": listed, "price": (data.get("price") or None) if listed else None,
        "chg": data.get("chg") if listed else None, "w52": data.get("w52") if listed else None,
        "revenue": data.get("revenue") or 0, "emp": data.get("emp") or 0, "emp_kr": data.get("emp_kr") or 0,
        "growth": data.get("growth") or 0, "yoy": data.get("yoy") or 0, "margin": data.get("margin") or 0,
        "expand": data.get("expand") or "보통", "plan": (data.get("plan") or "").strip(),
        "as_of": data.get("as_of") or __import__("datetime").date.today().isoformat(), "sample": False,
    }
    job["news"] = [{"date": n.get("date") or job["info"]["as_of"], "title": n["title"].strip(),
                    "partner": (n.get("partner") or "").strip() or None, "kind": n.get("kind") or "제휴",
                    "kw": [k for k in n.get("kw", []) if k], "source": "구인자 등록"}
                   for n in data.get("news", []) if (n.get("title") or "").strip()]
    return job


def _register(job: dict) -> None:
    JOBS.append(job)
    if job.get("news"):
        NEWS[job["company"]] = job["news"]


def add_job(data: dict) -> dict:
    """구인자(채용 담당자)가 등록한 공고를 목록에 추가하고 DB에 저장."""
    from . import store
    job = build_job(data, max(j["id"] for j in JOBS) + 1)
    _register(job)
    store.save("job", job["id"], job)
    return job


def restore_jobs() -> int:
    """서버 시작 때 DB에 저장된 등록 공고를 다시 불러옴."""
    from . import store
    n = 0
    for job in store.load("job"):
        # 예전에 저장된 공고 보정: 직종·출처가 없으면 채움 (링크드인 주소가 있으면 링크드인)
        job.setdefault("family", family_of(job.get("title", "")))
        if "source_site" not in job:
            job["source_site"] = "linkedin" if "linkedin.com" in (job.get("source_url") or "") else "direct"
            job["source_site_name"] = SOURCE_SITES[job["source_site"]]["name"]
        job.pop("origin", None)
        if not get_job(job["id"]):
            _register(job)
            n += 1
    return n


def delete_job(job_id: int) -> bool:
    """구인자가 등록한 공고만 삭제 가능 (예시 공고는 삭제 불가)."""
    from . import store
    job = get_job(job_id)
    if not job or job.get("source") != "구인자 직접 등록":
        return False
    JOBS.remove(job)
    if NEWS.get(job["company"]) is job.get("news"):
        NEWS.pop(job["company"], None)
    store.delete("job", job_id)
    return True
