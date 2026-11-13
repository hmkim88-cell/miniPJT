"""구인 요건 키워드 분석 + 레주메(이력서) 키워드 매칭 (모두 코드 계산, 결정적).

1) 요건 키워드: 공고의 기술·직무·경력·언어를 키워드로 뽑고 '중요도'(0~100)를 매김
   - 필수 기술: 공고에 먼저 나온 기술일수록 중요 (100 · 92 · 84), 직무명에 들어 있으면 +8
   - 우대 기술: 4번째부터 (70 · 62 · ...)
   - 직무 도메인: 직무명에서 뽑은 핵심 업무 키워드 (75)
   - 경력·직급(85), 영어(유창 80 · 비즈니스 65 · 업무 가능 50 · 기초 35)
2) 레주메 매칭: 키워드마다 레주메 글에서 찾음
   - 있음(1.0): 키워드가 그대로 있음 · 관련 경험(0.5): 같은 뜻의 다른 말이 있음 · 없음(0)
   - 키워드 매칭률 = Σ(중요도 × 매칭) / Σ중요도 × 100
"""
from __future__ import annotations

import re

# 같은 뜻으로 볼 말 (관련 경험)
SYNONYMS = {
    "Python": ["파이썬"], "Java": ["자바"], "JavaScript": ["JS", "자바스크립트"], "TypeScript": ["TS"],
    "React": ["리액트", "Next.js"], "Node.js": ["Node", "Express"], "Go": ["Golang"],
    "PostgreSQL": ["Postgres", "MySQL", "RDB", "SQL"], "MySQL": ["PostgreSQL", "RDB", "SQL"], "SQL": ["쿼리", "PostgreSQL", "MySQL"],
    "AWS": ["ECS", "EC2", "Lambda", "S3", "Bedrock", "클라우드"], "Docker": ["컨테이너"], "Kubernetes": ["k8s", "EKS", "컨테이너 오케스트레이션"],
    "Terraform": ["IaC", "CloudFormation"], "Kafka": ["메시지 큐", "RabbitMQ", "SQS"], "Redis": ["캐시", "캐싱"],
    "Spark": ["PySpark", "대용량 데이터"], "Airflow": ["워크플로", "배치", "ETL"],
    "LangChain": ["LLM", "Bedrock", "챗봇"], "LangGraph": ["LangChain", "에이전트", "Agent"], "RAG": ["검색 증강", "벡터 DB", "임베딩", "챗봇"],
    "PyTorch": ["TensorFlow", "딥러닝"], "MLOps": ["모델 배포", "SageMaker", "MLflow"],
    "FastAPI": ["Django", "Flask", "REST API"], "Django": ["FastAPI", "Flask"], "Spring": ["Spring Boot", "자바 백엔드"],
    "Linux": ["리눅스", "Ubuntu", "서버 운영"], "Git": ["GitHub", "GitLab", "형상 관리"], "Prometheus": ["Grafana", "모니터링"],
    "CSS": ["SCSS", "Tailwind"], "Kotlin": ["Android"], "Android": ["Kotlin", "모바일 앱"], "Swift": ["iOS"], "iOS": ["Swift", "모바일 앱"],
    "C#": ["Unity", ".NET"], "C++": ["C언어", "임베디드"], "ROS": ["로봇"], "Selenium": ["테스트 자동화", "Playwright", "Cypress"],
    "보안": ["Security", "취약점", "침해 대응"], "네트워크": ["Network", "TCP/IP", "방화벽"], "리더십": ["팀장", "리드", "멘토링", "매니저"],
    # 세일즈 · 프리세일즈 · 딜리버리 · 고객 성공
    "B2B 영업": ["영업", "수주", "신규 고객", "엔터프라이즈 영업", "Account Executive", "bookings", "new logos", "new logo"], "Enterprise Sales": ["엔터프라이즈 영업", "대기업 영업", "금융권 영업"],
    "파트너 영업": ["파트너", "채널 영업", "리셀러"], "협상": ["계약 체결", "수주", "가격 협상"], "Salesforce": ["CRM", "파이프라인 관리", "HubSpot"],
    "클라우드": ["AWS", "GCP", "Azure", "클라우드 전환"], "핀테크": ["결제", "금융"], "SaaS": ["구독", "B2B 솔루션"],
    "고객 성공": ["고객 유지", "재계약", "이탈", "Customer Success"], "온보딩": ["도입 지원", "교육"], "데이터 분석": ["SQL", "대시보드", "지표"],
    "LLM": ["챗봇", "GPT", "Bedrock", "생성형"], "기술 PoC": ["PoC", "개념 검증"], "고객 데모": ["데모", "시연"],
    "PMP": ["프로젝트 관리", "PM"], "Agile": ["스크럼", "애자일", "Scrum"], "Jira": ["Confluence"], "리스크 관리": ["위험 관리", "이슈 관리"],
    "고객 커뮤니케이션": ["고객 보고", "이해관계자"], "데이터 마이그레이션": ["마이그레이션", "이관"], "요구사항 분석": ["요구사항", "현업 인터뷰"],
}

# 직무명 → 핵심 업무 키워드와 레주메에서 찾을 말
DOMAIN = [
    (r"LLM|AI Platform", "LLM 서비스 개발", ["LLM", "챗봇", "생성형", "LangChain", "Bedrock", "GPT", "프롬프트"]),
    (r"Data Engineer", "데이터 파이프라인", ["파이프라인", "ETL", "Airflow", "Spark", "데이터 엔지니어"]),
    (r"Machine Learning", "머신러닝 모델", ["머신러닝", "모델", "ML", "PyTorch", "학습"]),
    (r"Backend|Product Engineer|Full-stack|Game Server", "API·서버 개발", ["API", "백엔드", "서버", "FastAPI", "Django", "Spring"]),
    (r"Frontend|Full-stack", "웹 UI 개발", ["프론트", "React", "UI", "화면"]),
    (r"DevOps|Site Reliability|Cloud", "배포·운영 자동화", ["CI/CD", "배포 자동화", "운영", "인프라", "ECS", "Kubernetes"]),
    (r"Security", "보안 엔지니어링", ["보안", "취약점", "침해"]),
    (r"Android|iOS", "모바일 앱 개발", ["앱", "Android", "iOS", "모바일"]),
    (r"Embedded", "임베디드 SW", ["임베디드", "펌웨어", "C++"]),
    (r"QA", "테스트 자동화", ["테스트", "QA", "자동화"]),
    (r"Manager|Lead", "팀 리딩", ["리드", "팀장", "매니저", "리딩", "멘토링"]),
    (r"Architect", "클라우드 아키텍처 설계", ["아키텍처", "설계", "Solutions Architect"]),
    (r"Payments|fin", "결제·금융 도메인", ["결제", "금융", "주문"]),
]
ENGLISH = {"유창": 80, "비즈니스": 65, "업무 가능": 50}
ENGLISH_WORDS = ["영어", "English", "TOEIC", "OPIc", "IELTS", "글로벌", "해외", "본사"]


def _has(text: str, word: str) -> bool:
    """단어 단위로 찾기 (Go 가 Google 안에서 잡히지 않게)."""
    return bool(re.search(rf"(?<![A-Za-z0-9+#.]){re.escape(word)}(?![A-Za-z0-9+#]|-[A-Za-z])", text, re.IGNORECASE))


def _evidence(text: str, words: list[str]) -> str | None:
    """레주메에서 그 말이 들어 있는 줄(짧게)을 근거로 돌려줌."""
    for line in text.splitlines():
        if any(_has(line, w) for w in words):
            ln = line.strip(" -·•\t")
            return ln if len(ln) <= 70 else ln[:68] + "…"
    return None


def requirement_keywords(job: dict) -> list[dict]:
    kws = []
    title = job["title"]
    for i, sk in enumerate(job["skills"]):
        core = i < 3
        imp = (100, 92, 84)[i] if core else max(40, 70 - 8 * (i - 3))
        if _has(title, sk):
            imp = min(100, imp + 8)
        kws.append({"kw": sk, "type": "필수 기술" if core else "우대 기술", "imp": imp, "words": [sk], "alt": SYNONYMS.get(sk, [])})
    for pat, name, words in DOMAIN:
        if re.search(pat, title + " " + job["company"], re.IGNORECASE) and len([k for k in kws if k["type"] == "직무 업무"]) < 2:
            kws.append({"kw": name, "type": "직무 업무", "imp": 75, "words": words[:2], "alt": words[2:]})
    kws.append({"kw": f"경력 {job['years_min']}~{job['years_max']}년 · {job['level']}", "type": "경력·직급", "imp": 85, "words": [], "alt": []})
    eng = next((v for k, v in ENGLISH.items() if k in job["english"]), 35)
    kws.append({"kw": f"영어 {job['english']}", "type": "언어·협업", "imp": eng, "words": ["영어", "English"], "alt": ENGLISH_WORDS[2:]})
    kws.sort(key=lambda k: -k["imp"])
    return kws


def keyword_match(job: dict, resume: str, profile: dict) -> dict:
    """요건 키워드 × 레주메 매칭 결과 + 매칭률."""
    resume = resume or ""
    years = profile.get("years", 0) or 0
    skills = {s.lower() for s in profile.get("skills", [])}
    rows = []
    for k in requirement_keywords(job):
        if k["type"] == "경력·직급":
            lo, hi = job["years_min"], job["years_max"]
            st = "있음" if lo <= years <= hi or years > hi else "관련 경험" if lo - years <= 1 else "없음"
            ev = f"레주메 경력 {years}년"
        else:
            if any(_has(resume, w) for w in k["words"]) or (k["type"].endswith("기술") and k["kw"].lower() in skills):
                st, ev = "있음", _evidence(resume, k["words"]) or "첨삭에서 뽑은 보유 기술"
            elif any(_has(resume, w) for w in k["alt"]):
                st, ev = "관련 경험", _evidence(resume, k["alt"])
            else:
                st, ev = "없음", None
        rows.append({"kw": k["kw"], "type": k["type"], "imp": k["imp"], "status": st,
                     "score": {"있음": 1.0, "관련 경험": 0.5, "없음": 0.0}[st], "evidence": ev})
    total = sum(r["imp"] for r in rows)
    rate = round(100 * sum(r["imp"] * r["score"] for r in rows) / total) if total else 0
    must = [r for r in rows if r["type"] == "필수 기술"]
    req_words = {r["kw"].lower() for r in rows}
    extra = [s for s in profile.get("skills", []) if s.lower() not in req_words][:6]
    return {"rate": rate, "rows": rows,
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in ("있음", "관련 경험", "없음")},
            "must_ok": sum(1 for r in must if r["status"] == "있음"), "must_total": len(must),
            "top_gaps": [r["kw"] for r in rows if r["status"] == "없음"][:3],
            "extra": extra, "has_resume": bool(resume.strip())}


# ───────── 인터뷰 전략: 레주메의 '최근 업무'를 강조 키워드 + 2줄 설명으로 ─────────
# 근거(1줄째)는 레주메 문장을 그대로, 강조 방법(2줄째)은 공고와의 관계로 코드가 만듦 (지어내지 않음)
_PERIOD = re.compile(r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*월?\s*[~\-–]\s*(?:(\d{4})\s*[.\-/년]\s*(\d{1,2})|현재|재직\s*중|재직중|present|now)", re.I)
_SECTION = re.compile(r"^\s*[\[【(]?\s*(기술|스킬|자격증|학력|교육|소개|프로젝트|수상|skills?|education|certifications?|about)\b", re.I)
# 앞에 있을수록 구체적인 말 (성과·업무 성격 → 일반 도메인 순)
_DOMAIN_WORDS = ["튜닝", "배포 자동화", "CI/CD", "챗봇", "LLM", "데이터 파이프라인", "모니터링", "마이그레이션", "수주", "매출", "계약",
                 "협상", "파트너", "파이프라인 관리", "PoC", "데모", "구축", "프로젝트 관리", "온보딩", "재계약", "리딩", "멘토링",
                 "결제", "주문", "API", "신규 고객", "고객", "영업",
                 # 영문 레주메·링크드인 PDF
                 "bookings", "new logos", "quota", "forecast", "pipeline", "revenue", "renewal", "retention", "onboarding",
                 "implementation", "migration", "go-live", "latency", "deployment", "customers", "deal"]


def _period_key(m: re.Match) -> int:
    """기간의 끝(현재면 가장 큼) → 최근 순 정렬용."""
    if m.group(3):
        return int(m.group(3)) * 12 + int(m.group(4))
    return 10 ** 6


_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_EN_MONTH = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})\b", re.I)
_LOCATION = re.compile(r"^[^\d]{2,40}(,\s*(south korea|korea|대한민국|republic of korea|united states|japan|singapore))\s*$|^(서울|경기|판교|seoul)[^\d]{0,30}$", re.I)


def _norm_period(line: str) -> str:
    """링크드인 PDF의 'March 2022 - Present' → '2022.03 - Present' (한국어 '2022년 3월 - 현재'는 그대로 인식)."""
    return _EN_MONTH.sub(lambda m: f"{m.group(2)}.{_MONTHS[m.group(1).lower()[:3]]:02d}", line)


def recent_block(resume: str) -> dict | None:
    """레주메에서 가장 최근 경력(기간 끝이 가장 늦은 것, '현재' 우선)의 회사줄·기간·업무 줄.
    일반 레주메('회사 · 직무 (2022.03 ~ 현재)')와 링크드인 PDF(회사 / 직무 / 기간 / 지역 줄이 따로) 둘 다."""
    raw = resume.splitlines()
    lines = [_norm_period(x) for x in raw]
    heads = [(i, m) for i, ln in enumerate(lines) for m in [_PERIOD.search(ln)] if m]
    if not heads:
        return None
    i, m = max(heads, key=lambda h: (_period_key(h[1]), -h[0]))
    head = raw[i].strip(" -·•\t")
    before = lines[i][:m.start()].strip(" -·•\t(")
    li_style = not re.search(r"[A-Za-z가-힣]{2,}", before)
    if not li_style:
        company = re.split(r"\s*[·|(\-–]\s*", before)[0].strip() or head[:20]
    else:   # 기간만 있는 줄 → 바로 위 줄들(링크드인 PDF: 회사 / 직무)
        prev = [raw[k].strip() for k in range(i - 1, max(-1, i - 3), -1) if raw[k].strip() and not _PERIOD.search(lines[k])]
        company = prev[-1] if len(prev) >= 2 else (prev[0] if prev else head[:20])
        if len(prev) >= 2:
            head = f"{prev[-1]} · {prev[0]} ({m.group(0).strip()})"
    tasks = []
    for k, ln in enumerate(lines[i + 1:], start=i + 1):
        t = raw[k].strip()
        if not t:
            if tasks:
                break
            continue
        if _PERIOD.search(ln) or _SECTION.match(t):
            if li_style and _PERIOD.search(ln):   # 링크드인 PDF: 다음 경력의 '회사 / 직무' 줄이 앞에 붙어 있음 → 빼기
                for _ in range(2):
                    if tasks and len(tasks[-1]) <= 30 and not re.search(r"\d|[.,]$", tasks[-1]):
                        tasks.pop()
            break
        if re.match(r"^page \d+ of \d+$", t, re.I):   # PDF 쪽 번호
            continue
        if not tasks and _LOCATION.match(t):   # 기간 바로 아래 지역 줄(링크드인 PDF)은 건너뜀
            continue
        tasks.append(t.strip(" -·•*\t"))
    return {"head": head, "company": company, "period": m.group(0).strip(), "tasks": [t for t in tasks if len(t) >= 4][:8]}


# 업무 종류별로 무엇을 강조하면 좋은지 (2줄째 설명)
_ANGLES = [
    (r"튜닝|개선|최적화|단축|성능|latency|improv|reduc|optimi", "개선 전 → 후 숫자(응답 시간·비용)를 먼저 말하고, 원인을 어떻게 찾았는지 설명하세요."),
    (r"영업|수주|매출|계약|파트너|협상|세일즈|파이프라인 관리|Salesforce|CRM|신규 고객|bookings|quota|new logos?|revenue|closed|deal|forecast|pipeline","계약 규모·매출·고객 수와 내가 이끈 단계(발굴→제안→계약)를 숫자로 말하세요."),
    (r"배포|CI/CD|자동화|데이터 파이프라인|ETL", "배포 시간·횟수가 어떻게 달라졌는지와 팀이 얻은 효과(실수 감소·속도)를 말하세요."),
    (r"LLM|챗봇|\bAI\b|PoC|생성형|모델", "최신 AI 경험이에요. 내가 맡은 부분·결과(도입 여부)·배운 한계를 솔직하게 말하세요."),
    (r"고객|온보딩|지원|데모|customer|onboarding|retention|renewal|demo","고객 문제를 어떻게 듣고 해결했는지, 고객 만족·유지(재계약) 결과로 말하세요."),
    (r"구축|프로젝트|\bPM\b|일정|마이그레이션|요구사항|implementation|project|migration|go-live", "일정·범위·이해관계자를 어떻게 관리했고 위험을 막은 순간이 언제였는지 말하세요."),
    (r"리딩|리드|팀장|멘토링|매니저", "팀 규모와 내가 내린 결정, 팀원이 성장한 사례를 함께 말하세요."),
    (r"API|서버|백엔드|결제|주문|운영", "트래픽·사용자 규모와 장애 없이 운영한 경험(책임 범위)을 강조하세요."),
]


def _wa(word: str) -> str:
    """'와/과' 고르기: 마지막 글자에 받침이 있으면 '과' (영문은 읽는 소리 기준으로 대략)."""
    ch = (word or " ")[-1]
    if "가" <= ch <= "힣":
        return "과" if (ord(ch) - 0xAC00) % 28 else "와"
    return "과" if ch.lower() in "lmnr" or ch.isdigit() and ch in "0136789" else "와"


def _angle(task: str, num) -> str:
    base = next((a for pat, a in _ANGLES if re.search(pat, task, re.I)), "맡은 범위(혼자/팀)와 내 결정을 STAR(상황·과제·행동·결과)로 1분 안에 말하세요.")
    return (f"레주메의 성과 '{num.group(0).strip()}'를 첫 문장에 두세요. " + base) if num else base


def recent_focus(job: dict | None, resume: str, profile: dict, skills_pool: list[str]) -> dict:
    """최근 업무 강조 키워드 (최대 5개). 각 키워드 = {keyword, evidence(레주메 원문), pitch(강조 방법), tag}."""
    blk = recent_block(resume or "")
    if not blk or not blk["tasks"]:
        return {"recent": None, "items": [], "note": "레주메에서 '2022.03 ~ 현재'처럼 기간이 적힌 최근 경력을 찾지 못했어요. 경력마다 기간과 한 일을 줄로 적어 주세요."}
    jskills = (job or {}).get("skills") or []
    must, nice = jskills[:3], jskills[3:]
    pool = list(dict.fromkeys([*jskills, *skills_pool, *(profile.get("skills") or [])]))
    items = []
    for t in blk["tasks"]:
        found = [s for s in pool if _has(t, s)]
        topic = next((w for w in _DOMAIN_WORDS if w.lower() in t.lower()), "")
        nums = re.findall(r"\d+(?:[.,]\d+)?\s*(?:%|배|분|초|시간|명|건|곳|개사|억|만|x|[BMK](?![a-z])|bn|million|billion|new logos?|customers?|deals?)", t)
        # 금액(억·만·B·M)·비율(%)을 먼저 강조
        num = next((re.search(re.escape(n), t) for n in sorted(nums, key=lambda n: (not re.search(r"억|만|%|[BMK]$|bn|illion", n)))), None)
        rel = None   # 공고와의 관계
        if job:
            hit = next((s for s in must if s in found), None) or next((s for s in nice if s in found), None)
            if hit:
                rel = ("필수", hit) if hit in must else ("우대", hit)
            else:
                for js in jskills:
                    if any(_has(t, w) for w in SYNONYMS.get(js, [])):
                        rel = ("관련", js)
                        break
        key_sk = (rel[1] if rel and rel[0] != "관련" else (found[0] if found else ""))
        keyword = " · ".join(x for x in [key_sk, topic] if x) or (t[:16] + ("…" if len(t) > 16 else ""))
        ev = f"“{t if len(t) <= 80 else t[:78] + '…'}” — {blk['company']}, {blk['period']}"
        angle = _angle(t, num)
        if not job:
            pitch, tag = angle, "최근 업무"
        elif rel and rel[0] == "필수":
            pitch, tag = f"공고 필수 기술 '{rel[1]}'{_wa(rel[1])} 바로 연결 — " + angle, "필수 기술"
        elif rel and rel[0] == "우대":
            pitch, tag = f"우대 기술 '{rel[1]}' 경험으로 차별점이 돼요 — " + angle, "우대 기술"
        elif rel:
            pitch, tag = f"공고의 '{rel[1]}'{_wa(rel[1])} 맞닿는 경험 — " + angle, "관련 경험"
        else:
            pitch, tag = "요건엔 직접 없지만 최근 업무라 질문이 나와요 — " + angle, "최근 업무"
        score = {"필수 기술": 4, "우대 기술": 3, "관련 경험": 2}.get(tag, 1) + (1.5 if num else 0) + (0.5 if found else 0)
        items.append({"keyword": keyword, "evidence": ev, "pitch": pitch, "tag": tag, "has_number": bool(num), "_s": score})
    items.sort(key=lambda x: -x["_s"])
    for x in items:
        x.pop("_s")
    return {"recent": {"head": blk["head"], "company": blk["company"], "period": blk["period"]}, "items": items[:5],
            "note": "근거는 레주메 문장 그대로예요. 키워드는 면접 첫 1분(자기소개)과 '최근 프로젝트' 질문에 순서대로 쓰세요."}
