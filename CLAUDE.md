# CLAUDE.md — mini-pjt 작업 규약

서비스 정의는 `SERVICE.md`가 기준입니다. 기능을 바꾸면 SERVICE.md도 함께 고칩니다.

## 사용자
- 비전공자 학습자(삼성SDS AX 교육: LangChain/Bedrock/LangGraph). **설명은 항상 한국어로, 쉽게, 단계별로.**
- 코드 주석도 한국어로 짧게. 화면을 바꾸면 브라우저로 열어서 보여 줌.

## 서비스 한 줄
외국계 IT 특화 구인·구직 연결.
- **매칭률**(공고) = 커리어 34 + 연봉·직급 33 + 사주 인연 33
- **회사 인연도**(회사, 100) = 한국 사업확대 20 + 주가 성장성 20 + 커리어 30 + 사주 인연 20 + 미래사업·인지도 10
- **커리어 인연 종합 대시보드**(모든 회사 비교) → **회사 인연도 대시보드**(회사 1곳, 탭 8개, **점수 계산 풀이·키워드 매칭** 포함) → 담당자 연결 요청 + 사내 추천 요청

## 구조
```
mini-pjt/
├─ app/
│  ├─ main.py       FastAPI 라우트 (API 목록은 SERVICE.md 12절)
│  ├─ linkedin.py   내 링크드인 연결 (OpenID Connect, 이름·이메일·사진)
│  ├─ ai.py         Bedrock Claude: 첨삭 · 사주 풀이(물·이직운) · 매칭 코멘트 · 인터뷰 전략(interview_plan)
│  ├─ saju.py       사주·오행, water_analysis(물), move_luck(이직운), affinity(인연 %), affinity_story(인연 이유 6가지)
│  ├─ scoring.py    매칭률: career(skill·yr) · pay_level(sal·lv) · affinity, WEIGHTS 34/33/33, 합격률, fate_ranking(이직 인연 랭킹)
│  ├─ analysis.py   회사 인연도: korea · stock · career · saju · future (MAX 20/20/30/20/10), 참고 인맥, fit_total, overview(종합 대시보드), score_breakdown(점수 계산 풀이·시뮬레이션)
│  ├─ dashboard.py  대시보드 탭: tendency · posting · finance · applicant · interview_base(인터뷰 기본안)
│  ├─ keywords.py   구인 요건 키워드(중요도) · 레주메 키워드 매칭(있음 1/관련 0.5/없음 0, 동의어 SYNONYMS) → /api/keywords
│  ├─ network.py    추천인(동의한 재직자, 가상 24명), connections(학연·지연·전 직장), request_referral
│  ├─ jobs.py       가상 외국계 IT 공고 20개 + COMPANY_INFO + NEWS + build_job(입력→공고) · add_job(등록·저장) · restore_jobs · delete_job
│  ├─ store.py      DB 저장 (SQLAlchemy): DATABASE_URL 없으면 SQLite data/careerfate.db, 있으면 PostgreSQL(pool). records 표 + resumes 표
│  ├─ resume_file.py 레주메 파일(PDF·docx·txt)에서 글자만 추출 (파일은 저장 안 함) → /api/resume/extract
│  └─ resumes.py    구직자 레주메 장기 보관: 동의·암호화(Fernet)·주인 해시·365일·이전 버전 5개 → /api/resumes/me
├─ static/          index.html · style.css · app.js (바닐라 JS) — 구직자 5단계 + ★종합 대시보드(view-overview) + 회사 대시보드 모달 + 구인자 화면
├─ run.bat          서버 실행 + 브라우저 열기
├─ data/careerfate.db  DB 파일 (SQLite 사용 시 자동 생성, 지우면 초기화)
├─ data/.resume.key    개발용 레주메 암호화 키 (자동 생성). **공유·커밋 금지, 지우면 저장된 레주메를 못 읽음**
├─ data/rooms.json · src/tools.py · src/agent.py   교육 실습용 회의실 Agent (서비스와 별개)
├─ SERVICE.md
└─ CLAUDE.md
```

## 환경
- Python: 상위 폴더 venv `..\.venv\Scripts\python.exe` (fastapi, uvicorn, langchain-aws, korean-lunar-calendar, httpx, sqlalchemy, psycopg[binary], cryptography, pypdf, python-docx)
- AWS 키·링크드인 키·DB 주소: 상위 폴더 `..\.env` (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, 선택 `LINKEDIN_REDIRECT_URI`, 선택 `DATABASE_URL=postgresql+psycopg://...`, 운영 필수 `RESUME_ENC_KEY`(Fernet 키), 선택 `DB_POOL_SIZE`·`DB_MAX_OVERFLOW`). **값을 출력·커밋하지 않음**
- 모델: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, 리전 `us-east-1`
- 접속 주소: **http://localhost:8000** (링크드인 콜백과 같은 호스트)
- 실행: `mini-pjt` 폴더에서 `..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` (파이썬 코드 바꾸면 서버 재시작, static만 바꾸면 새로고침)

## 꼭 지킬 규칙

**점수·계산**
1. **계산은 코드, 해석은 AI.** 간지·물·이직운·인연 %·매칭률·합격률·회사 인연도·점수 풀이·시뮬레이션·재무 진단·로드맵은 코드가 계산. 점수 풀이 총점은 `company_analysis` 총점과 항상 같아야 함. LLM은 숫자·판정·좋은 달을 만들거나 바꾸지 않음.
2. **매칭률 비율은 사용자 결정: 34 : 33 : 33** (`scoring.WEIGHTS`). 인연의 회사 쪽 날짜는 공고 마감일. 이직운은 넣지 않음.
3. **회사 인연도 배점은 사용자 결정: 20 · 20 · 30 · 20 · 10** (`analysis.MAX`). 매칭률과 섞지 않음. 사내 인맥은 "참고"(점수 0).
4. 2·3번 비율을 바꾸려면 **사용자 확인 후** SERVICE.md도 함께 수정.
5. **나이로 판단하지 않음.** 생년월일은 사주 계산에만. **학연·지연도 점수에 넣지 않음.** 키워드 매칭률은 따로 보여 주기만 하고 매칭률·회사 인연도에 섞지 않음.
5-1. **키워드 근거는 레주메 원문 문장만** 보여 줌(지어내기 금지). 레주메 원문(`resume_text`)은 구인자에게 보내지 않음 (`SHARE_KEYS`에 넣지 않기). 보관된 레주메도 본인만 조회.

**화면**
6. **사주 화면 순서 고정:** 4기둥 → 물·이직운 → 오행·AI 풀이 → 맨 아래 **"참고사항" 박스(`.ref-box`)** 안 이직 인연 랭킹. 물·이직운·랭킹은 빼거나 숨기지 않음.
7. **대시보드 두 개 유지:** ★ 종합 대시보드(필터 한 줄 · KPI · 누적 막대 순위 · 사분면 산점도 · 12개월 · 마감 · 분야 · 전체 표)와 회사 인연도 대시보드(전체 화면 모달 + 탭 8개: 종합 인연도 · **점수 계산**(폭포 차트·매칭률 식·점수 올리기 시뮬레이션·항목별 풀이, `analysis.score_breakdown`) · **키워드 매칭**(요건 핵심 키워드·레주메 매칭률·근거 문장, `keywords.keyword_match`) · 커리어 성향·연간 방향 · 구인 내용 · 회사 재무 분석 · 내 커리어 분석 · 인터뷰 전략). 빼지 않음. 모든 차트 값은 표나 글자로도 확인 가능해야 함(툴팁만으로 보여 주지 않음).
8. **합격률·이직운·회사 인연도는 참고용으로 표시.** "AI 추정치", "합격을 보장하지 않아요" 문구 유지.

**AI**
9. **AI 프롬프트에 금지 문구 유지:** 프로필에 없는 경력·성과 지어내기 금지, 계산값 변경 금지, 나이·성별·출신 판단 금지, 합격 보장 표현 금지.
10. **AI 실패해도 화면은 동작:** 첨삭 → `simple_review`, 사주 풀이 → `reading_error`(계산값 표시), 매칭 코멘트 → 없이 순위만, 인터뷰 전략 → `interview_base`(+`ai_error`).

**개인정보·데이터**
11. **구인자·추천인에게 사주 정보 전달 금지.** `/api/recruiter/*`·추천 요청에 생년월일·사주·인연 점수·회사 인연도를 넣지 않음. 구인자 전달 항목은 `main.SHARE_KEYS` + 커리어·연봉/직급 점수뿐.
12. **링크드인은 본인 개인 연결만.** 공식 OAuth만 사용, 스크래핑·로그인 대행·타인 프로필 수집·비공식 API 금지. `state` 검증 유지, 액세스 토큰 저장 안 함.
13. **인맥은 스스로 등록·공개 동의(`consent`)한 추천인만**, 이름은 가림. 외부에서 인물 정보를 모으는 코드 금지.
14. **예시 데이터는 모두 가상:** 회사·담당자·추천인·재무·주가·뉴스·파트너. 실존 인물 금지, 종목코드 표시 안 함, 가상 회사와 실존 한국 기업을 엮은 뉴스 금지. 화면에 "가상 예시" 표시 유지.
15. **DB에는 필요한 것만 저장:** 등록 공고·연결 요청(상태)·추천 요청·**동의한 구직자의 레주메(암호화)**. 생년월일·사주 결과·동의 없는 레주메·링크드인 세션은 저장하지 않음. 레주메는 반드시 `resumes.py`를 거쳐 암호화·주인 해시·보관 기한을 지킴(평문 저장·주인 아닌 사람 조회 금지). 저장 코드는 `store.py`만 거치게(SQL 직접 작성 금지 → DB를 바꿔도 그대로 동작). DB 주소·비밀번호는 화면·로그·`/api/admin/db`에 보이지 않게.
16. **구인자 공고 등록은 화면·서버 같은 점검 규칙**(`main._check_job`). 예시 공고 20개는 삭제 불가, 직접 등록한 공고만 삭제.

## 디자인 규칙
- 기본: 네이비(`--navy-*`) + 골드(`--gold*`) 포인트, Pretendard
- 사주 영역: 한지 배경(`--hanji`), Noto Serif KR, 오행 색 `--wood/--fire/--earth/--metal/--water`
- 매칭 공고 카드의 3요소 색: ① 커리어 `--comp` · ② 연봉·직급 `--pay` · ③ 인연 `--aff` (대시보드 안에서는 아래 검증 팔레트 사용)
- 회사 인연도 5항목 색(색약 검증 통과, 바꾸면 dataviz `validate_palette.js`로 다시 검증): ① `--s-korea` #eb6834 · ② `--s-stock` #1baf7a · ③ `--s-career` #2a78d6 · ④ `--s-saju` #eda100 · ⑤ `--s-future` #6250d6. 매칭률 3요소는 커리어 `--s-career` · 연봉·직급 `--s-pay` #e87ba4 · 사주 `--s-saju` (검증 통과). 두 대시보드 모두 같은 색, 순서 유지. 참고 인맥 `--aff`(점선)
- 차트: 값 글자는 잉크색(항목 색 글자 금지), 큰 숫자는 Pretendard, 강조 1색(`--emph`)+회색(`--deemph`), 격자선은 실선 1px, 막대 조각 사이 2px 간격, 범례 항상 표시
- 대시보드 CSS 클래스는 `ov-`/`ovsc`/`ovst` 접두어 사용 (기존 `.sc`·`.st`와 충돌했던 적 있음)
- 대시보드: 남색 그라데이션 머리띠 + 총점 원형 게이지, 흰 카드(`.dcard`, 금색 제목 막대), 차트는 인라인 SVG(레이더·막대), 좋음 `--ok`/보통 `--gold`/주의 `--aff` 점
- 색은 `style.css`의 `:root` 변수로만 지정. 980px 이하 반응형 유지
- 탭 내용은 `hidden` 속성으로 전환 → `.dpane[hidden]{display:none}` 지우지 말 것
- 좁은 화면: `.main{min-width:0}`·`.side{min-width:0}` 유지 (넓은 표·단계 메뉴가 화면을 넓히지 않게)

## 확인 방법 (변경 후)
1. 서버 재시작 후 API 흐름 `/api/resume/review` → `/api/saju` → `/api/recommend` → `/api/overview` → `/api/company-analysis` → `/api/score-breakdown` → `/api/apply` → `/api/recruiter/requests` 모두 200
2. 사주 기준값: 양력 1994-08-17 8시 → `갑술 임신 을해 경진`(물 2개·적당·인성), 1990-05-15 → `경오 신사 경진`(물 0개·없음)
3. 이직운 기준값(지원일 2026-11-11, 병오년 기해월): 1994-08-17 8시 → 50점, 1990-05-15 → 80점
4. 이직 인연 랭킹 1위: 1994-08-17 8시 → Brightwave Data 76%, 1990-05-15 → Corvant Payments 81% (5~99 범위)
5. 회사 인연도: 1994-08-17 8시 · 서울대학교 · 부산 · 삼성SDS · 기술 Python/FastAPI/PostgreSQL/Docker/AWS/LangChain · 미들 · 7500 → Elyra AI Korea(job 5) **83점**(16·19·25·14·9), 최하위 Quillon Software 29점. 각 항목은 배점 이하
6. 인맥: 서울대·삼성SDS → Aeroloop Korea·Elyra AI Korea·Tidemark Semicon에 두 가지가 겹치는 추천인. `/api/referral` 같은 요청 두 번째는 409
7. `/api/recruiter/requests` 응답에 `saju`, `birth`, `affinity`, `total`, `company_fit` 키가 없을 것
8. 회사 대시보드: 탭 8개가 각각 다른 내용으로 바뀌고, 인터뷰 탭 출처가 "AI 코치 (Claude)" 또는 "기본 전략 (코드)"
9. 점수 계산 탭(`/api/score-breakdown`): Elyra AI Korea → 16+19+25+14+9 = 83 (company-analysis 총점과 같아야 함), 사주 기본 +95 −1 = 94 → 72% → 14, 매칭률 72×0.34+100×0.33+72×0.33 = 81.3 → 81%, 합격 가능성 78%, 시뮬레이션 1위 "LangGraph, RAG 모두 익히기" +5 / +10 / +9
10. 종합 대시보드(`/api/overview`): 전체 20곳·1위 Elyra AI Korea 83, 평균 56, 60점 이상 8곳 / "AI·데이터" 필터 → 4곳·평균 75. 420px 폭에서 가로 넘침 없음(scrollWidth = innerWidth)
10-1. 키워드 매칭(`/api/keywords`, 예시 프로필): Elyra AI Korea 78%(필수 2/3, LangGraph·RAG = 관련 경험, 영어 = 없음), Aeroloop Korea·Solenne Media 91%, Corvant Payments 35%. "영어" 보완 문구는 영어 경험 안내여야 함(미니 프로젝트 아님)
11. 링크드인: 키 없이 `/api/linkedin/me` → `configured:false`, `/auth/linkedin/login` → `/?linkedin=not_configured`
12. 공고 등록(시험 DB로): 연봉 최소 > 최대면 400, 예시(Nimbusway AI) 미리보기 회사 쪽 42/50(17·16·9), 등록 → 회사 인연도 계산됨 → 연결 요청·상태 변경·추천 요청 후 **재시작해도 남아 있음** → 삭제 가능, 예시 공고(5) 삭제는 404
12-1. 레주메 보관(시험 DB로): 동의 없으면 400 · 빈 글 400 → 저장 v1(기한 +365일, 쿠키 발급) → 글 바꿔 저장 v2(이전 버전 1) → 다른 브라우저는 saved:false → DB 표에 이름·학교가 평문으로 없음 → 삭제 후 saved:false. 테스트 레주메는 지우기
13. 브라우저에서 1~5단계 + 두 대시보드 + 구인자 화면(요청·등록·등록한 공고)까지 클릭만으로 통과. **테스트로 넣은 데이터는 지우기**(DB에 남음): 구인자 화면 "삭제" 또는 `data/careerfate.db` 파일 삭제

## 화면 수정 시
- `static/index.html`의 `style.css?v=…`·`app.js?v=…` 값을 바꿔야 사용자 브라우저에 새 화면이 보임 (첫 페이지는 no-cache)
- 매칭 공고 정렬·필터 상태는 `state.mf`, 프로필 입력 확인은 `updateReady()` — 값을 코드로 채운 뒤에는 `updateReady()` 호출
- 레주메 요약(`state.summary`)은 `summaryHtml()` 하나로 구직자(업데이트·첨삭 화면)·구인자(받은 연결 요청)에 같이 씀. 구인자 쪽은 서버 `_share()`가 `SUMMARY_SHARE` 항목만 남김 → **원문·changes·gaps를 구인자에게 보내는 코드 금지**
- 레주메 요약 점검: `POST /api/resume/extract`(txt·docx·pdf 200, .hwp·빈 파일 400) → `/api/resume/summary` 이전 버전과 비교 시 changes·diff → 연결 요청 후 `/api/recruiter/requests`에 resume_summary 있고 원문·changes·gaps·생년월일 없음. Bedrock 하루 토큰 한도에 걸리면 간이 요약(ai:false)으로 동작
- **링크드인 공고 가져오기는 붙여넣은 글만** (`/api/recruiter/import-linkedin`). 서버에서 링크드인 주소를 열거나(httpx 등) 공고를 자동 수집하는 코드 금지 — 약관 위반. 주소는 `linkedin_job_id()`로 공고 번호만 뽑아 정해진 모양으로 저장
- 공고에 없는 값(연봉·마감일·담당자·경력 최대)을 AI나 코드가 짐작해 채우지 않음 → `missing`으로 "확인 필요" 표시
- 정규식을 heredoc/파이썬 문자열로 끼워 넣을 때 `\b`가 백스페이스 문자로 바뀌는 사고가 있었음 → 정규식이 든 코드는 Write/Edit로 넣고, `b'\x08' in 파일` 확인
- 링크드인 가져오기 점검: 짧은 글·링크드인 아닌 주소 400 → 예시 글(가상 회사)로 12칸 채움, 경력 최대 '확인 필요' → 원문 주소 저장·origin LinkedIn → 같은 공고 다시 등록 409
- **직종(`family`)은 필터·표시용** — 매칭률·회사 인연도 계산에 넣지 않음(배점 변경은 사용자 확인). 새 공고는 `family`·`source_site`·`source_site_name` 필수 필드(없으면 `build_job`/`restore_jobs`가 채움)
- 공고 출처 주소는 `main.normalize_source_url(site, url)`만 거쳐 저장 (사이트별 도메인 확인). 서버에서 출처 사이트에 접속하는 코드 금지
- 인터뷰 최근 업무 키워드(`keywords.recent_focus`)의 근거는 레주메 문장 그대로 — 근거를 바꿔 쓰거나 숫자를 만들지 않기
- 점검: `fam_test.py`(직종 7개·26개, 세일즈/딜리버리 필터, 원티드 주소 정리·도메인 거절·중복 409, 직종 자동 분류, 최근 업무 키워드 근거 = 레주메 원문)
- 링크드인 공고 분석(`linkedin_jobs.py`)은 붙여넣은 글만 — 링크드인 자동 수집·로그인 대리 금지. 사용자의 링크드인 계정 비밀번호는 받거나 저장하지 않음(로그인은 본인이 브라우저에서 OAuth로)
- 직급 4단계(일반·주니어·시니어·리더)는 이 섹션 전용 표시, 매칭률 계산은 기존 직급(주니어·미들·시니어·리드)과 `TIER_TO_LEVEL`로 연결
- 예상 연봉 기준표는 가정치 — 화면에 근거(공고/같은 직종·직급 N개/기준표)를 반드시 함께 표시
- 사용자 개인 링크드인 주소를 코드·예시 데이터에 넣지 않음(화면에서 본인이 입력). 프로필 주소는 `resume_file.profile_url()`로만 정리
- 링크드인 PDF 점검: `lipdf_test.py`(가상 인물 영문·한글 PDF → 프로필 주소·최근 경력·지역/다음 경력 줄 제외)
- 링크드인 공고 '가져오기'는 사용자가 받은 데이터(데이터 내보내기 ZIP/CSV · 채용 알림 메일)만 — `linkedin_import.py`. 링크드인 접속·스크래핑 코드 금지. Gmail 자동 연동은 사용자가 Google OAuth 키를 준비한 뒤에만
- 점검: `liimp_test.py`(가상 ZIP 저장 3+지원 1, .eml 알림 2개 직무·회사·지역, 붙여넣기 2개, 잘못된 파일 400)
- 매일 배치: `jobfeed.py`(받기·중복 제거·피드) · `batch.py`(ATS 공개 API · 파일 넣기 · BATCH_TIME 예약). **서비스 코드에서 링크드인 접속·로그인 쿠키 사용 금지** — 링크드인은 사용자 에이전트가 읽어 `/api/batch/linkedin-scan`으로 보냄(BATCH_TOKEN). 방안 문서 `docs/LINKEDIN_BATCH_PLAN.md`
- 점검: `feed_test.py`(토큰 401 · 1일차 새 3 · 2일차 새 1/이미 본 2 · ATS 한국만 · 실패 회사 건너뜀 · 파트너십=세일즈 위, HRBP=기타 아래)
- 구인 회사 분석(`company_scan.py`): 회사별 묶기·채용 신호는 공고 데이터만으로 — 회사 재무·주가 등 없는 정보를 지어내지 않기. 회사 적합도 배점 변경은 사용자 확인
- 링크드인 직종·직급 규칙(`linkedin_jobs.TITLE_RULES` · `classify_tier`)을 바꾸면 **`python tests\test_linkedin_matching.py`가 OK 81/81** 이어야 함. 새로 틀린 직무명을 발견하면 정답과 함께 이 파일에 추가

- 링크드인 채용 PDF: 직무명↔링크는 PDF 링크 영역 위치로 짝지음(`pdf_text_with_links`). 점검 `pdf_job_test.py`(알림 4 · 검색 3 · 1개 → 자세히 분석 · 깨진 PDF 400)
- 링크드인 구인 엑셀: `linkedin_excel.ALIASES`에 열 이름을 추가해 확장(영어·한글). 점검 `excel_test.py`(영어/한글 머리글 · 3번째 줄 머리글 · 2회 올리기 NEW · 한글 연봉 '억' · .xls 안내)
- 📊 대시보드 CSS 클래스는 `ld-` 접두사, 탭은 `dashtab` (회사 대시보드 창의 `.dash`와 겹치지 않게). 직종 색은 `--fam-0..7`만 사용
- 패키지: openpyxl 추가 (requirements.txt)

