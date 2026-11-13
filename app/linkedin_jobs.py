"""링크드인 공고 분석 (구직자용 특별 섹션) — 모두 코드 계산, 결정적.

입력: 구직자가 링크드인 공고 화면에서 복사해 붙여넣은 글 (+ 공고 주소).
      서버는 링크드인에 접속하지 않음 (공개 API 없음 · 자동 수집은 약관 위반).
출력:
  1) 직종: 키워드 점수로 세일즈·개발·딜리버리 등 판단 + 찾은 키워드(근거)
  2) 직급: 일반 · 주니어 · 시니어 · 리더 (링크드인 Seniority level 기준과 맞춤)
  3) 예상 연봉: 공고에 원화가 있으면 그 값, 없으면 서비스 공고의 같은 직종·직급 중간값, 그것도 없으면 기준표(가정치)
  4) 인터뷰 핵심 키워드: 직종별 핵심 역량 중 공고에 나온 것 우선 + 공고 필수 기술 → '왜 중요' + '준비 방법'
"""
from __future__ import annotations

import re
from statistics import median

from .jobs import JOB_FAMILIES

# ── 1) 직종 키워드 사전 (가중치: 직무명에서 찾으면 ×3) ──
FAMILY_KEYWORDS: dict[str, list[str]] = {
    "세일즈": ["account executive", "account manager", "sales", "quota", "pipeline", "prospecting", "closing", "revenue target",
              "business development", "new logo", "territory", "enterprise sales", "영업", "세일즈", "수주", "매출 목표", "고객 발굴", "신규 고객",
              # 파트너십 · 사업개발 (링크드인 'Partner' 검색에서 많이 나오는 직무)
              "partner manager", "partnership", "partnerships", "alliance", "alliances", "channel partner", "channel sales", "bd manager",
              "go-to-market", "파트너십", "제휴", "사업개발"],
    "프리세일즈": ["solutions engineer", "solution engineer", "sales engineer", "pre-sales", "presales", "technical demo", "demo", "proof of concept",
                "poc", "rfp", "solution consultant", "솔루션 엔지니어", "프리세일즈", "기술 영업", "데모", "제안서"],
    "딜리버리": ["delivery", "project manager", "program manager", "implementation", "deployment consultant", "consultant", "project plan",
              "stakeholder", "go-live", "pmp", "scope", "milestone", "딜리버리", "구축", "프로젝트 관리", "이행", "pm", "일정 관리"],
    "고객 성공": ["customer success", "csm", "technical account manager", "tam", "retention", "renewal", "churn", "onboarding", "adoption",
               "nrr", "고객 성공", "고객 유지", "재계약", "온보딩"],
    "데이터·AI": ["data engineer", "data scientist", "machine learning", "ml engineer", "llm", "rag", "deep learning", "pytorch", "spark",
               "airflow", "analytics", "데이터", "머신러닝", "인공지능"],
    "인프라·클라우드": ["devops", "site reliability", "sre", "kubernetes", "terraform", "cloud architect", "solutions architect", "cloud", "infrastructure", "security engineer",
                  "observability", "ci/cd", "인프라", "클라우드", "보안"],
    "개발": ["software engineer", "backend", "frontend", "full-stack", "fullstack", "developer", "mobile", "android", "ios", "api",
           "java", "python", "react", "개발자", "백엔드", "프론트엔드"],
}


def _count(text: str, word: str) -> int:
    return len(re.findall(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text))


# 직무명 우선 규칙 — 위에서부터 '가장 구체적인 말'이 먼저 (예: 'Sales Engineer'는 sales보다 프리세일즈가 먼저)
TITLE_RULES: list[tuple[str, str]] = [
    ("기타", r"\b(hr|human resources|people partner|recruit\w*|talent acquisition|finance|accountant|accounting|legal|counsel|marketing|"
             r"brand|admin\w*|office manager|payroll|product manager|product owner|designer|ux|ui designer)\b|인사(?!이트)|채용 담당|재무|회계|법무|마케팅|디자이너|서비스 기획|제품 기획"),
    ("프리세일즈", r"\b(sales engineer|solutions? engineer|pre-?sales|presales|customer engineer|solutions? consultant|technical consultant)\b|기술\s?영업|프리세일즈|솔루션 엔지니어"),
    ("고객 성공", r"\b(technical account manager|tam|customer success|customer support|support engineer|client success)\b|고객\s?성공|고객 지원|기술 지원"),
    ("딜리버리", r"\b(engagement manager|implementation|professional services|delivery|program manager|project manager|pmo|pm|"
                r"deployment (consultant|engineer)|(?<!sales )consultant)\b|딜리버리|구축|프로젝트\s?매니저|프로젝트 관리|컨설턴트"),
    ("세일즈", r"\b(account executive|account manager|account director|partner development|business development|bdr|sdr|sales|channel|"
              r"partnerships?|alliances?|country manager|general manager)\b|영업|세일즈|제휴|사업\s?개발"),
    ("데이터·AI", r"\b(data|machine learning|ml|mlops|ai|genai|scientist|analytics|llm|nlp|computer vision)\b|데이터|머신러닝|인공지능|딥러닝"),
    ("인프라·클라우드", r"\b(sre|site reliability|devops|cloud|platform|security|infrastructure|network|solutions architect|architect)\b|클라우드|인프라|보안|네트워크"),
    ("개발", r"\b(engineer(ing)?|developer|programmer|software|backend|frontend|full-?stack|mobile|ios|android|qa|sdet|embedded)\b|개발|엔지니어|프로그래머"),
]


def classify_family(title: str, text: str) -> dict:
    """① 직무명 우선 규칙(가장 구체적인 말 먼저) → ② 없으면 본문 키워드 점수 → ③ 그래도 없으면 '기타'(모름).
    근거 키워드와 직종별 점수 비율도 함께 (본문이 있을 때)."""
    t, b = (title or "").lower(), (text or "").lower()
    rule = next(((fam, m.group(0)) for fam, pat in TITLE_RULES for m in [re.search(pat, t)] if m), None)
    if rule and rule[0] == "기타":
        return {"family": "기타", "evidence": [rule[1]], "scores": [], "confident": True, "by": "직무명"}
    scores, hits = {}, {}
    for fam, words in FAMILY_KEYWORDS.items():
        found = []
        sc = 0
        for w in words:
            n_title, n_body = _count(t, w), _count(b, w)
            if n_title or n_body:
                found.append(w)
                sc += 3 * min(n_title, 1) + min(n_body, 3)
        scores[fam], hits[fam] = sc, found
    total = sum(scores.values()) or 1
    ranked = sorted(((f, scores[f]) for f in JOB_FAMILIES if scores[f]), key=lambda x: -x[1])
    pct = [{"family": f, "score": s, "pct": round(100 * s / total)} for f, s in ranked][:4]
    if rule:   # 직무명이 직종을 분명히 말하면 그것이 우선 (본문 점수는 참고로)
        fam = rule[0]
        return {"family": fam, "evidence": list(dict.fromkeys([rule[1], *hits.get(fam, [])]))[:8], "scores": pct, "confident": True, "by": "직무명"}
    best = max(JOB_FAMILIES, key=lambda f: (scores.get(f, 0), -JOB_FAMILIES.index(f)))
    if scores[best] == 0:   # 아무 단서도 없으면 IT 직종으로 억지로 넣지 않음
        return {"family": "기타", "evidence": [], "scores": [], "confident": False, "by": "모름"}
    return {"family": best, "evidence": hits[best][:8], "scores": pct, "confident": scores[best] >= 4, "by": "본문"}


# ── 2) 직급: 일반 · 주니어 · 시니어 · 리더 ──
TIERS = ["일반", "주니어", "시니어", "리더"]
TIER_DESC = {"일반": "신입·인턴 (Entry level · Internship, 경력 0~1년)", "주니어": "Associate (경력 1~4년)",
             "시니어": "Mid-Senior level (경력 5년 이상)", "리더": "Director · Manager · Lead · Principal (팀·조직 리딩)"}
TIER_TO_LEVEL = {"일반": "주니어", "주니어": "주니어", "시니어": "시니어", "리더": "리드"}   # 서비스의 직급(매칭률 ②)과 연결


def classify_tier(title: str, text: str, years_min: int | None) -> dict:
    """순서: ① 직무명의 직급 표현 → ② 링크드인 Seniority level 표시 → ③ 요구 경력 연수 → ④ 기본값."""
    t, b = (title or ""), (text or "")
    # ① 직무명 ('Account Executive'·'Account/Customer Success Manager'는 직무 이름이라 직급으로 보지 않음)
    tt = re.sub(r"(account|customer success|partner|product|project|program|delivery|sales|success)\s+(executive|manager)", " ", t, flags=re.I)
    title_rules = [
        ("리더", r"\b(director|head of|head|vp|vice president|chief|principal|staff|lead|team lead|engineering manager|country manager|general manager)\b|팀장|리더|본부장|실장"),
        ("시니어", r"\b(senior|sr\.?)\b|시니어"),
        ("일반", r"\b(intern|internship|new grad|graduate|entry[- ]level)\b|신입|인턴"),
        ("주니어", r"\b(junior|jr\.?|associate)\b|주니어"),
    ]
    for tier, pat in title_rules:
        m = re.search(pat, tt, re.I)
        if m:
            return _tier_out(tier, f"직무명의 '{m.group(0)}'", years_min)
    # ② 링크드인 공고 위쪽의 Seniority level 표시 (대소문자 그대로인 표시만)
    # 본문에 다시 나오는 직무 이름('Account Executive', 'Account/Project Manager')은 지우고 찾음
    head = re.sub(r"(account|customer success|partner|product|project|program|delivery|sales|success)\s+(executive|manager|director)", " ", b[:600], flags=re.I)
    found = re.findall(r"(?<![A-Za-z])(Internship|Entry level|Associate|Mid-Senior level|Director|Executive)(?![A-Za-z])", head)
    # 여러 개면 링크드인 표시로 자주 쓰는 정확한 표현 우선 (Mid-Senior level > Entry level > Internship > Director > Associate > Executive)
    order = ["Mid-Senior level", "Entry level", "Internship", "Director", "Associate", "Executive"]
    label = re.search("(" + re.escape(min(found, key=order.index)) + ")", head) if found else None
    if label:
        tier = {"Internship": "일반", "Entry level": "일반", "Associate": "주니어", "Mid-Senior level": "시니어",
                "Director": "리더", "Executive": "리더"}[label.group(1)]
        # Mid-Senior인데 요구 경력이 10년 이상이면 리더급 기대
        if tier == "시니어" and years_min and years_min >= 10:
            tier = "리더"
        return _tier_out(tier, f"링크드인 직급 표시 '{label.group(1)}'" + (f" · 요구 경력 {years_min}년" if years_min else ""), years_min)
    if years_min is None:   # 직무명·본문의 '5년 이상' · '5+ years' · '경력 3~7년'
        ym = re.search(r"(\d{1,2})\s*(?:년\s*이상|\+?\s*years?|\s*[~\-–]\s*\d{1,2}\s*년)", t + "\n" + b[:2000], re.I)
        years_min = int(ym.group(1)) if ym and int(ym.group(1)) <= 25 else None
    if years_min is not None:
        tier = "리더" if years_min >= 10 else "시니어" if years_min >= 5 else "주니어" if years_min >= 1 else "일반"
        return _tier_out(tier, f"요구 경력 {years_min}년 이상", years_min)
    return _tier_out("주니어", "직급 표현·경력 연수가 없어 기본값", years_min)


def _tier_out(tier: str, why: str, years_min) -> dict:
    return {"tier": tier, "desc": TIER_DESC[tier], "why": why, "service_level": TIER_TO_LEVEL[tier], "years_min": years_min}


# ── 3) 예상 연봉 (만원) ──
# 기준표(가정치): 서비스에 같은 직종·직급 공고가 없을 때만 씀. 운영에서는 실제 채용 데이터로 교체해야 함
BASE_TABLE = {"일반": (4000, 5500), "주니어": (5500, 7500), "시니어": (8500, 12000), "리더": (12000, 16000)}
FAMILY_FACTOR = {"세일즈": 1.05, "프리세일즈": 1.05, "딜리버리": 0.95, "고객 성공": 0.9, "데이터·AI": 1.05, "인프라·클라우드": 1.0, "개발": 1.0}


def estimate_salary(draft: dict, family: str, tier: str, jobs: list[dict]) -> dict:
    if draft.get("salary_min") and draft.get("salary_max"):
        return {"min": draft["salary_min"], "max": draft["salary_max"], "basis": "공고에 적힌 연봉 (원화)", "kind": "posted", "n": 0}
    level = TIER_TO_LEVEL[tier]
    same = [j for j in jobs if j.get("family") == family and j["level"] == level]
    note = ""
    if tier == "일반":
        same = []   # 서비스 공고에는 신입 전용 공고가 거의 없어 기준표로
    if len(same) >= 1:
        lo, hi = round(median(j["salary_min"] for j in same) / 100) * 100, round(median(j["salary_max"] for j in same) / 100) * 100
        basis, kind = f"서비스에 등록된 같은 직종·직급 공고 {len(same)}개의 연봉 중간값", "peer"
        if any((j.get("info") or {}).get("sample") for j in same):
            note = "데모의 예시 공고(가상) 기준이라 실제 시장 값과 다를 수 있어요"
    else:
        f = FAMILY_FACTOR.get(family, 1.0)
        lo, hi = (round(x * f / 100) * 100 for x in BASE_TABLE[tier])
        basis, kind = f"서비스 기준표({tier}) × 직종 보정 {f} — 가정치", "table"
        note = "같은 직종·직급 공고가 없어 기준표로 계산했어요. 운영에서는 실제 채용 데이터로 바꿔야 해요"
    eng = (draft.get("english") or "")
    if eng in ("유창",) and kind != "posted":
        lo, hi = round(lo * 1.05 / 100) * 100, round(hi * 1.05 / 100) * 100
        basis += " · 영어 유창 요구 +5%"
    sal_note = ""
    if family == "세일즈":
        sal_note = "외국계 세일즈는 기본급 + 인센티브(OTE) 구조가 많아요 — 면접에서 기본급:인센티브 비율과 목표(Quota)를 꼭 확인하세요"
    return {"min": lo, "max": hi, "basis": basis, "kind": kind, "n": len(same), "note": note, "extra": sal_note,
            "posted_text": draft.get("salary_text") or ""}


# ── 4) 인터뷰 핵심 키워드 (직종별 핵심 역량) ──
# (키워드, 공고에서 찾을 말, 왜 중요한지, 어떻게 준비할지)
INTERVIEW_FOCUS: dict[str, list[tuple[str, list[str], str, str]]] = {
    "세일즈": [
        ("Quota 달성률", ["quota", "target", "목표", "attainment"], "외국계 세일즈 면접의 첫 질문 — 숫자로 성과를 증명해야 해요.", "최근 2~3년 목표 대비 달성률(%)·순위를 표로 준비하고 달성 방법을 1분으로."),
        ("파이프라인 관리", ["pipeline", "forecast", "crm", "salesforce", "파이프라인"], "예측 가능한 매출을 만드는 능력을 봐요.", "단계별 전환율·예측 정확도와 CRM(Salesforce) 사용 습관을 사례로."),
        ("딜 사이즈 · 영업 사이클", ["deal", "enterprise", "cycle", "acv", "계약"], "다뤄 본 계약 규모가 이 포지션과 맞는지 확인해요.", "대표 계약 2건의 금액·기간·의사결정자 수를 STAR로 정리."),
        ("신규 고객 발굴", ["prospecting", "new logo", "outbound", "hunting", "발굴", "신규"], "신규 로고 확보가 핵심 KPI인 경우가 많아요.", "콜드 아웃리치 → 미팅 → 계약까지 직접 만든 사례와 숫자."),
        ("협상 · 클로징", ["negotiat", "closing", "협상", "클로징"], "가격·조건 협상에서 회사 이익을 지키는지 봐요.", "할인 요구를 다른 가치로 바꿔 닫은 사례 1개."),
    ],
    "프리세일즈": [
        ("기술 데모", ["demo", "데모", "presentation"], "고객 앞에서 제품 가치를 보여 주는 능력이 평가의 중심이에요.", "10분 데모 시나리오(문제 → 해결 → 효과)를 실제로 시연할 수 있게."),
        ("PoC 설계 · 성공 기준", ["poc", "proof of concept", "pilot", "검증"], "PoC를 계약으로 연결한 경험을 가장 많이 물어요.", "성공 기준을 고객과 합의한 방법과 계약 전환 결과."),
        ("고객 요구 → 솔루션", ["requirement", "discovery", "rfp", "요구사항", "제안"], "비즈니스 문제를 기술 설계로 바꾸는 사고를 봐요.", "RFP·요구사항을 아키텍처로 바꾼 사례를 그림 1장으로."),
        ("영업과의 협업", ["account executive", "sales team", "영업"], "AE와 짝을 이뤄 딜을 이기는 역할이에요.", "AE와 역할을 나눠 딜을 이긴 사례, 갈등을 푼 방법."),
        ("기술 깊이", ["api", "cloud", "aws", "llm", "integration", "architecture"], "기술 질문에 바로 답할 수 있는 깊이를 확인해요.", "제품과 연동되는 핵심 기술(클라우드·API)을 화이트보드로 설명하는 연습."),
    ],
    "딜리버리": [
        ("범위 · 일정 관리", ["scope", "timeline", "milestone", "schedule", "일정", "범위"], "약속한 범위와 일정을 지키는 것이 딜리버리의 기본이에요.", "변경 요청을 통제하며 일정 내 오픈한 프로젝트 사례(규모·기간)."),
        ("리스크 · 이슈 관리", ["risk", "issue", "escalation", "리스크", "이슈"], "문제가 생겼을 때 어떻게 막고 알렸는지를 꼭 물어요.", "리스크를 미리 찾아 막은 사례와 에스컬레이션 기준."),
        ("이해관계자 커뮤니케이션", ["stakeholder", "client", "customer", "보고", "고객"], "고객·본사·개발팀 사이 조율이 핵심 역량이에요.", "주간 보고 구조, 의견이 갈린 이해관계자를 맞춘 사례."),
        ("고객 오픈 · 인수", ["go-live", "acceptance", "handover", "오픈", "인수"], "끝맺음(Go-live·검수)까지 책임지는지 봐요.", "오픈 체크리스트와 오픈 후 안정화 기간에 한 일."),
        ("방법론 (Agile · PMP)", ["agile", "scrum", "pmp", "waterfall", "jira"], "어떤 방식으로 팀을 굴리는지 확인해요.", "사용한 방법론·도구(Jira 등)와 상황에 따라 바꾼 이유."),
    ],
    "고객 성공": [
        ("고객 유지 · 재계약", ["retention", "renewal", "churn", "nrr", "재계약", "유지"], "CSM의 핵심 KPI(재계약률·NRR)를 숫자로 물어요.", "담당 고객 재계약률·이탈 방어 사례를 숫자로."),
        ("온보딩 · 도입 확대", ["onboarding", "adoption", "온보딩", "도입"], "고객이 제품을 실제로 쓰게 만드는 능력이에요.", "온보딩 기간 단축·사용률 증가 사례."),
        ("고객 건강도 관리", ["health", "qbr", "success plan", "지표"], "위험 고객을 먼저 알아채는 방식을 봐요.", "건강도 지표와 QBR(분기 리뷰) 운영 경험."),
        ("에스컬레이션 대응", ["escalation", "support", "issue", "장애"], "불만 고객을 다루는 태도를 확인해요.", "화난 고객을 재계약까지 돌린 사례 1개."),
        ("업셀 협업", ["upsell", "expansion", "영업"], "확장 매출 기회를 영업에 넘기는 역할도 커요.", "고객 요구에서 확장 기회를 찾은 사례."),
    ],
    "개발": [
        ("시스템 설계", ["design", "architecture", "scalab", "설계"], "외국계 면접의 핵심 라운드(System Design)예요.", "내가 만든 서비스 구조를 그림으로, 트래픽이 10배일 때 바꿀 점까지."),
        ("코딩 테스트", ["algorithm", "coding", "data structure", "코딩"], "라이브 코딩·온라인 테스트가 거의 항상 있어요.", "자료구조·알고리즘 문제를 말로 설명하며 푸는 연습(영어 포함)."),
        ("장애 대응 · 운영", ["on-call", "incident", "production", "monitoring", "운영", "장애"], "운영 책임감을 사례로 확인해요.", "장애 원인을 찾고 재발을 막은 사례(타임라인)."),
        ("코드 품질 · 테스트", ["test", "code review", "quality", "ci/cd", "리뷰"], "팀 단위 개발 습관을 봐요.", "테스트·코드 리뷰로 품질을 올린 사례."),
        ("영어 협업", ["english", "global", "영어", "본사"], "본사 엔지니어와 매일 일하는 경우가 많아요.", "대표 프로젝트 2개를 영어로 2분 안에 설명하는 연습."),
    ],
    "데이터·AI": [
        ("데이터 파이프라인", ["pipeline", "etl", "airflow", "spark", "파이프라인"], "데이터를 안정적으로 흘리는 설계를 물어요.", "처리량·지연·실패 재처리 방식을 숫자와 함께."),
        ("모델 · LLM 성능 평가", ["evaluation", "metric", "accuracy", "llm", "rag", "평가"], "만든 모델이 '좋다'는 근거를 요구해요.", "평가 지표와 개선 전후 수치, 실패 사례."),
        ("운영 (MLOps)", ["mlops", "deploy", "monitoring", "serving", "배포"], "모델을 서비스로 운영한 경험을 봐요.", "배포·모니터링·재학습 흐름을 그림으로."),
        ("비즈니스 영향", ["business", "impact", "stakeholder", "성과"], "기술 결과가 매출·비용에 준 영향을 물어요.", "프로젝트 결과를 돈·시간으로 환산해 말하기."),
        ("시스템 설계", ["design", "architecture", "설계"], "데이터·AI 시스템 설계 라운드가 있어요.", "RAG·추천 시스템 설계를 화이트보드로 연습."),
    ],
    "인프라·클라우드": [
        ("가용성 · 안정성 (SRE)", ["reliability", "sla", "slo", "availability", "uptime", "가용성"], "서비스가 멈추지 않게 하는 방법을 깊게 물어요.", "SLO 설정과 장애 회고(포스트모템) 사례."),
        ("IaC · 자동화", ["terraform", "iac", "automation", "ci/cd", "자동화"], "수작업을 코드로 바꾼 경험이 핵심이에요.", "Terraform 등으로 자동화한 범위와 효과(시간·실수)."),
        ("컨테이너 · 쿠버네티스", ["kubernetes", "k8s", "docker", "eks"], "대부분의 외국계 인프라 면접 단골 주제예요.", "클러스터 운영 경험과 트러블슈팅 사례."),
        ("보안", ["security", "iam", "compliance", "보안"], "클라우드 보안 기본기를 확인해요.", "권한 최소화·비밀 관리 방식 설명."),
        ("비용 최적화", ["cost", "finops", "비용"], "클라우드 비용 절감 경험을 자주 물어요.", "절감 금액·비율과 방법."),
    ],
}


INTERVIEW_FOCUS["기타"] = [
    ("직무 적합 근거", ["experience", "경험"], "IT 외 직무라 이 직무 경험을 먼저 확인해요.", "이 직무와 직접 맞는 경험 2개를 숫자와 함께."),
    ("이해관계자 협업", ["stakeholder", "business", "협업"], "여러 부서와 일하는 방식을 봐요.", "의견이 다른 부서를 설득한 사례."),
    ("영어 커뮤니케이션", ["english", "global", "영어"], "외국계라 본사와의 소통을 확인해요.", "대표 경험을 영어로 2분 안에 설명하는 연습."),
]


# 세일즈 중 파트너십·제휴·채널 직무 (링크드인 'Partner' 검색의 핵심) — 일반 영업과 면접 포인트가 다름
INTERVIEW_FOCUS["파트너십"] = [
    ("파트너 생태계 구축", ["ecosystem", "partner program", "recruit partners", "생태계", "파트너 발굴"], "어떤 파트너를 어떻게 골라 키웠는지가 첫 질문이에요.", "파트너 선정 기준 · 온보딩 · 1년 뒤 성과를 표 하나로 정리."),
    ("파트너 소싱 매출", ["partner-sourced", "partner sourced", "revenue", "pipeline", "매출"], "파트너 덕분에 생긴 매출·파이프라인을 숫자로 물어요.", "파트너 소싱/영향 매출 금액과 전체 대비 비율을 준비."),
    ("공동 판매 (Co-sell)", ["co-sell", "co sell", "joint", "go-to-market", "gtm", "공동"], "파트너와 함께 고객을 공략한 방식을 확인해요.", "공동 제안으로 딜을 이긴 사례 1개 — 역할 분담과 결과."),
    ("계약 · 협상", ["agreement", "negotiat", "contract", "terms", "계약", "협상"], "파트너 계약 조건(수수료·독점·목표)을 다뤄 봤는지 봐요.", "조건을 조정해 양쪽이 이긴 협상 사례."),
    ("SI · 리셀러 관리", ["system integrator", " si ", " sis ", "reseller", "distributor", "channel", "리셀러", "총판"], "한국은 SI·리셀러 채널이 중요해 실제 관계를 물어요.", "함께 일한 SI·리셀러 유형과 관계를 유지한 방법."),
]
_PARTNER_ROLE = re.compile(r"partner(?!\s+(marketing|sales engineer))|alliance|channel|파트너|제휴|총판", re.I)


def interview_keywords(family: str, text: str, skills: list[str]) -> list[dict]:
    low = (text or "").lower()
    out = []
    key = "파트너십" if family == "세일즈" and _PARTNER_ROLE.search(low[:300]) else family
    for kw, triggers, why, prep in INTERVIEW_FOCUS.get(key, INTERVIEW_FOCUS["개발"]):
        hit = next((t for t in triggers if t in low), None)
        out.append({"keyword": kw, "in_posting": bool(hit), "evidence": hit or "", "why": why, "prep": prep, "kind": "역량"})
    out.sort(key=lambda x: not x["in_posting"])   # 공고에 나온 역량 먼저
    picked = out[:4]
    # 공고 필수 기술 1~2개 (앞쪽 = 필수)
    for s in skills[:2]:
        picked.append({"keyword": s, "in_posting": True, "evidence": s, "kind": "필수 기술",
                       "why": f"공고 요구사항 앞부분에 나온 필수 기술이에요 — 기술 면접에서 깊이를 확인해요.",
                       "prep": f"'{s}'로 직접 해결한 문제 1개를 규모·결과 숫자와 함께, 설계 이유까지 설명할 수 있게."})
    return picked[:6]
