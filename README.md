# 미니 PJT: 커리어인연 — 외국계 IT 커리어 × AI 코칭 × 사주 매칭

## 무엇을 푸나
외국계 IT 기업으로 이직하려는 사람이 **링크드인 공고 중 어떤 회사·직무가 나와 맞는지, 그 회사가 무엇을 뽑는지, 면접에서 무엇을 강조해야 하는지**를 한 화면에서 판단하기 어려운 문제를 푼다.
(레주메 → AI 첨삭·요약 → 공고 매칭 → 구인 회사 분석 → 인터뷰 전략, 참고용 사주 인연까지)

## 활용한 패턴 (Day 1~7)
- **Day 1: LangChain + Bedrock Claude (`ChatBedrockConverse`)** — `with_structured_output(Pydantic 모델)`로 레주메 첨삭·레주메 요약·공고 글 → 등록 칸 정리·사주 풀이·추천 코멘트·인터뷰 전략을 **정해진 JSON 모양**으로 받음 (`app/ai.py`)
- **Day 1: 프롬프트 규칙** — "레주메·공고에 없는 경력·숫자·연봉·마감일을 지어내지 말 것", "나이·성별·출신 평가 금지", "합격 보장 표현 금지", 오늘 날짜를 넣어 '현재' 경력 계산
- **Day 1: 실패 대비(폴백)** — AI 호출이 실패하면(하루 토큰 한도·검증 오류) 코드 규칙으로 간이 결과를 만들어 화면이 멈추지 않게 (`main.simple_review`, `_draft_fallback`, 간이 레주메 요약)
- **Day 3: LangGraph Agent** — 교육 실습용 회의실 안내 Agent (`src/agent.py`, `src/tools.py`, START → agent ⇄ tools → END). 서비스 본체와는 별개
- **도구 연동 설계 (Agent ↔ 서비스)** — 링크드인을 읽는 일은 사용자가 직접 돌리는 브라우저 에이전트가 하고, 서비스는 토큰으로 보호된 배치 API(`POST /api/batch/linkedin-scan`)로 결과만 받음 (`docs/LINKEDIN_BATCH_PLAN.md`)
- **평가 세트로 개선** — 링크드인 직무명 81개(정답 포함) 회귀 시험으로 분류 규칙을 고치고 다시 측정 (`tests/test_linkedin_matching.py`)
- 쓰지 않은 것: RAG(Day 2) · MCP(Day 4) — 이 서비스는 문서 검색이 아니라 **구조화된 공고·레주메 데이터의 규칙 계산 + LLM 구조화 출력**이 중심이라 적용하지 않음

## 아키텍처
```
[구직자 브라우저]  static/index.html · app.js (단계 1~5 · 대시보드 · 링크드인 공고 분석 · 레주메 업데이트)
[구인자 브라우저]  공고 등록 · 받은 연결 요청 · 구직 사이트 공고 가져오기(붙여넣기)
        │ fetch /api/*
        ▼
[FastAPI 서버 app/main.py  (uvicorn :8000)]
   ├─ ai.py ───────────── AWS Bedrock Claude (구조화 출력, 실패 시 코드 폴백)
   ├─ scoring.py · analysis.py · keywords.py · dashboard.py ── 매칭률 · 회사 인연도 · 키워드 매칭 · 인터뷰 기본안
   ├─ saju.py ─────────── 사주 4기둥 · 물(水) · 이직운 · 공고 마감일과의 인연 %
   ├─ linkedin_jobs.py ── 링크드인 공고 → 직종 · 직급 · 예상 연봉 · 인터뷰 핵심 키워드
   ├─ linkedin_import.py  데이터 내보내기 ZIP/CSV · 채용 알림 메일(.eml/HTML/붙여넣기) · 채용 화면 PDF → 공고 목록 + 참고 적합도
   ├─ linkedin_excel.py ─ 링크드인 구인 엑셀(.xlsx) → 공고 목록 (영어·한글 열 이름 자동 인식, 쌓기·NEW)
   ├─ li_dashboard.py ─── 📊 채용 대시보드: KPI · 직종·직급 분포 · 회사 Top 10 · 예상 연봉 · 인터뷰 키워드
   ├─ company_scan.py ─── 링크드인 공고를 회사별로: 채용 규모 · 채용 신호 · 나와의 적합
   ├─ jobfeed.py · batch.py  매일 배치: 에이전트 스캔 결과 받기 · Greenhouse/Lever/Ashby 공개 채용 API · 중복 제거 · NEW
   ├─ resume_file.py ──── PDF·Word·txt 글자 추출 (링크드인 프로필 PDF · PDF 링크 영역 → 공고 주소)
   ├─ resumes.py ──────── 동의한 레주메만 Fernet 암호화 · 주인 해시 · 365일 · 이전 버전 5개
   ├─ linkedin.py ─────── Sign in with LinkedIn (OAuth 2.0/OIDC, 이름·이메일·사진)
   └─ store.py ────────── SQLAlchemy: SQLite(기본) / PostgreSQL(DATABASE_URL)

[사용자 브라우저 에이전트 (선택)] ── 하루 1회 링크드인 검색 1~3쪽 읽기(본인 로그인·읽기만) ── POST /api/batch/linkedin-scan
※ 서비스 서버는 링크드인에 접속하지 않음 (스크래핑·로그인 대리 없음)
```

## 실행 방법
```bat
:: 1) 가상환경 (상위 폴더에 .venv)
python -m venv ..\.venv
..\.venv\Scripts\python -m pip install -r requirements.txt

:: 2) 상위 폴더 ..\.env  (값은 커밋·공유 금지)
::    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION=us-east-1   ← Bedrock Claude
::    (선택) LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET                        ← 내 링크드인 연결
::    (선택) DATABASE_URL=postgresql+psycopg://...                              ← 없으면 SQLite data/careerfate.db
::    (운영 필수) RESUME_ENC_KEY=<Fernet 키>                                    ← 없으면 개발용 data/.resume.key 자동 생성
::    (선택) BATCH_TOKEN=<긴 무작위 글자>, BATCH_TIME=07:00                    ← 매일 배치 받기·실행

:: 3) 서버 실행 → http://localhost:8000
run.bat
::  또는  ..\.venv\Scripts\python -m uvicorn app.main:app --port 8000

:: 4) 매일 배치 (선택)
..\.venv\Scripts\python -m app.batch ats                    & rem 회사 공개 채용 API (data/ats_sources.json)
..\.venv\Scripts\python -m app.batch linkedin-file 결과.json & rem 에이전트 스캔 결과 파일 넣기

:: 5) 회귀 시험
..\.venv\Scripts\python tests\test_linkedin_matching.py     & rem → OK 81/81
```
처음 써 볼 때: 1단계 "예시 프로필" → "AI 분석 시작" → 매칭 공고 · ★ 종합 대시보드 · in 링크드인 공고 분석(예시 데이터로 해 보기)

## RAGAS 평가 결과
- **해당 없음** — 이 프로젝트는 RAG(문서 검색 → 답변) 파이프라인을 쓰지 않아 RAGAS 지표(context_recall · context_precision · faithfulness · answer_relevancy)를 측정하지 않았다.
- 대신 아래 **정답이 있는 인-아웃 세트**로 분류·매칭 품질을 측정했다. (faithfulness에 해당하는 "지어내지 않기"는 프롬프트 규칙 + 코드 확인으로 점검: 인터뷰 '최근 업무 강조 키워드'의 근거 문장이 레주메 원문 그대로인지 시험)

## 인-아웃 세트 통과율 (자체 평가)
링크드인 공고 직무명 → 정답 **직종**(개발·데이터·AI·인프라·세일즈·프리세일즈·딜리버리·고객 성공·기타) · **직급**(일반·주니어·시니어·리더)

| 세트 | 1차 (개선 전) | 2차 (개선 후) |
|---|---|---|
| 직무명 51개 (영문·한글, 어려운 경우 포함) — 직종 | 40 / 51 (78%) | **51 / 51** |
| 같은 51개 — 직급 | 49 / 51 (96%) | **51 / 51** |
| **처음 보는 직무명 30개** (규칙을 맞추지 않은 세트) — 직종 / 직급 | 29 / 30 · 30 / 30 | 30 / 30 · 30 / 30 (MLOps 단어 추가) |

- 개선폭: **+11 건** (51개 직종 기준). 주요 개선: ① 단서가 없는 직무명을 '개발'로 넣던 것을 '기타'로 (개발자 순위에 Country Manager가 80점으로 올라오던 문제) ② 직무명의 **가장 구체적인 말을 먼저** 보는 규칙 (Sales Engineer·Pre-sales·기술영업 → 프리세일즈, Technical Account Manager → 고객 성공) ③ "(5년 이상)"·"5+ years"로 직급 판단
- 51개는 규칙을 맞춘 세트라 낙관적일 수 있어, 처음 보는 30개(97%)를 더 정직한 수치로 본다
- 처음부터 끝까지 시험(배치 15개 → 피드 → 회사 분석 → AI 상세): 파트너십 영업 9년 기준 상위 7개 모두 파트너십·제휴·채널·BD, 이름만 Partner인 HR·마케팅·채용 직무는 맨 아래, 8/8 통과
- 서비스 전체 흐름 시험 12/12, DB·레주메 암호화 보관·링크드인 PDF·공고 가져오기·배치 시험 모두 통과 (예시 회사·인물은 모두 가상)
- 링크드인 구인 엑셀 시험 14/14 (영어/한글 머리글 · 3번째 줄 머리글 · 2번 올리기 NEW 구분 · '억' 연봉 · .xls 안내)
- 최종 점검 (2026-11-13): 자동 시험 **158개 모두 통과** — 상세는 `docs/COMPLETION_REPORT.md`

## 트라이앤에러 회고
- **시도했지만 실패한(채택하지 않은) 접근**
  - 서버가 링크드인에 로그인 쿠키로 접속해 공고를 긁기 → 링크드인 이용약관(자동 수집 금지) 위반 · 본인 계정 제한 위험 → 채택 안 함
  - 직무명 키워드 **점수 합**으로 직종 판단 → 'Sales Engineer'의 sales 때문에 세일즈로, 단서 없는 직무명은 '개발'로 들어가 직종 정확도 78%
  - AI 구조화 출력을 그대로 신뢰 → 경력 최대값을 숫자 대신 글자 `'null'`로 줘서 검증 오류 → 공고 자동 채우기가 간이 결과로 떨어짐
  - 정규식이 든 코드를 셸 heredoc으로 끼워 넣기 → `\b`가 백스페이스 문자로 바뀌어 'Senior'를 못 찾는 버그
  - PDF 글자만 읽기 → 'PDF로 저장'하면 링크 주소가 글에 없어서 직무명과 공고 링크를 짝지을 수 없음
- **최종 채택한 접근 · 이유**
  - 링크드인은 **본인이 받은 데이터**(데이터 내보내기 ZIP·채용 알림 메일·채용 화면 PDF) + **사용자 에이전트가 읽은 결과를 배치 API로 받기** + 회사 **공개 채용 API**(Greenhouse·Lever·Ashby) → 약관·계정 위험 없이 매일 공고를 모음
  - 직종은 **직무명 우선 규칙(가장 구체적인 말 먼저) → 본문 점수 → 없으면 '기타'** → 51개 100%, 처음 보는 30개 97%
  - AI 출력은 Pydantic `field_validator`로 `'null'`·빈 글자를 '값 없음'으로 정리, AI 실패 시 코드 폴백 (Bedrock 하루 토큰 한도에 걸려도 동작)
  - PDF는 **링크 영역(주석) 위치를 글 줄과 맞춰** 직무명 ↔ 공고 링크 짝짓기
  - 점수(매칭률 34:33:33, 회사 인연도 20/20/30/20/10)는 사용자가 정한 배점만 쓰고, 새 지표(참고 적합도·회사 적합도)는 별개로 표시
  - 개인정보: 생년월일·사주·레주메 원문은 구인자에게 보내지 않음, 레주메는 동의한 경우만 암호화 보관
- **남은 한계 · 향후 개선 방향**
  - 예시 공고·회사·뉴스·추천인은 모두 **가상 데이터**, 예상 연봉 기준표는 가정치 → 실제 채용 데이터로 교체 필요
  - 실제 링크드인 공고로는 아직 정확도 측정 전 → 첫 배치가 들어오면 틀린 직무명을 `tests/test_linkedin_matching.py`에 추가
  - 링크드인 로그인(OAuth) 앱 키 · PostgreSQL 운영 DB · 운영 암호화 키 미설정, Gmail 자동 연동은 Google OAuth 키 준비 후
  - 로그인 구분(구직자·구인자·추천인), 새 공고 알림, 개인정보 처리방침

## 핵심 코드 위치
- `app/main.py:63` — 레주메 AI 첨삭 API (실패 시 `simple_review` 폴백, :73)
- `app/main.py:189` — 매칭 공고 추천 (매칭률 + 회사 인연도 + 키워드 매칭)
- `app/main.py:779` — 링크드인 공고 1개 상세 분석 (직종·직급·예상 연봉·인터뷰 키워드·내 레주메 비교)
- `app/main.py:828` — 내 링크드인 공고 가져오기 (ZIP·CSV·메일·PDF → 나와 맞는 순위)
- `app/main.py:888` — 매일 배치 받기 (`X-Batch-Token`) · `:944` 구인 회사 분석 · `:972` 엑셀 양식 · `:986` 📊 채용 대시보드
- `app/ai.py:43` · `:87` · `:134` · `:223` — Bedrock Claude 구조화 출력 (첨삭 · 레주메 요약 · 공고 정리 · 인터뷰 전략)
- `app/linkedin_jobs.py:45` — 직무명 우선 규칙 `TITLE_RULES` · `:60` 직종 · `:96` 직급 · `:144` 예상 연봉 · `:246` 인터뷰 핵심 키워드
- `app/linkedin_import.py:110` — 채용 알림 메일/PDF 파싱 · `:167` 파일 종류별 읽기 · `:228` 참고 적합도 · `:307` 공고 분석
- `app/linkedin_excel.py:15` — 엑셀 열 이름 사전 `ALIASES` · `:61` 엑셀 읽기 · `:113` 엑셀 양식
- `app/li_dashboard.py:17` — 📊 채용 대시보드 데이터 만들기
- `app/company_scan.py:51` — 회사별 채용 규모·신호·회사 적합도
- `app/jobfeed.py:52` · `app/batch.py` — 배치 받기·중복 제거 · 공개 채용 API
- `app/keywords.py:94` — 레주메 키워드 매칭 · `:222` 인터뷰 '최근 업무 강조 키워드'
- `app/saju.py:198` — 사주 인연 % · `app/analysis.py:140` 회사 인연도(100점)
- `app/resumes.py:99` — 레주메 암호화 보관 · `app/store.py:54` DB 연결(SQLite/PostgreSQL)
- `src/agent.py` — (교육 실습) LangGraph 회의실 안내 Agent · `src/tools.py` 도메인 도구
- 문서: `SERVICE.md`(서비스 설계 전체) · `CLAUDE.md`(개발 규칙) · `docs/LINKEDIN_BATCH_PLAN.md`(링크드인 매일 배치 방안) · **`docs/COMPLETION_REPORT.md`(완료 보고서)**
