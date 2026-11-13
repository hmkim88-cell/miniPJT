# 링크드인 공고 매일 배치 — 방안 · 연동 설명서

> 목표: **하루에 정해진 시각**에 링크드인에서 구직(검색) 결과를 모아 **오늘의 새 공고**와 **나와 맞는 회사 순위**를 보여 준다.
> 이 서비스(커리어인연) 서버는 **링크드인에 접속하지 않는다.** 링크드인을 읽는 일은 사용자가 직접 돌리는 에이전트가 하고, 서비스는 결과를 받아 쌓고 분석한다.

---

## 1. 왜 이렇게 나누나

| 하지 않는 것 | 이유 |
|---|---|
| 서비스 서버가 링크드인에 로그인 쿠키를 넣고 Playwright·Selenium·requests로 검색 결과를 긁기 | 링크드인 이용약관(자동 수집·봇 금지) 위반. 봇으로 감지되면 **본인 계정이 제한**될 수 있음. 링크드인은 이 문제로 소송에서 이긴 적이 있음(hiQ 사건, 2022) |
| 다른 사람 프로필·지원자 수집 | 개인정보 · 약관 문제 |

| 하는 것 | 내용 |
|---|---|
| ① 사용자의 브라우저 에이전트가 읽은 결과 **받기** | 예: Claude **linkedin-job-scan** 스킬 — 사용자가 본인 계정으로 로그인한 브라우저에서 **하루 한 번 · 1~3쪽 · 읽기만**(지원·저장·메시지 안 함). 결과 JSON을 서비스로 보냄 |
| ② 회사 **공개 채용 API** 직접 가져오기 | Greenhouse · Lever · Ashby — 회사가 채용 페이지용으로 공개한 주소(로그인·키 없음). 한국 근무 공고만 |
| ③ 링크드인이 본인에게 주는 데이터 | 데이터 내보내기 ZIP(저장·지원한 공고) · 채용 알림 메일 — 화면에서 올리기 |

> ①도 링크드인 입장에선 자동화된 읽기라 **위험이 0은 아님**. 하루 1회 · 3쪽 이하 · 읽기만 · 사람이 쓰는 브라우저로 제한하고, 계정 경고가 오면 바로 멈춘다. 가장 안전한 것은 ②·③.

---

## 2. 전체 흐름 (매일 07:00 예시)

```
[07:00 사용자 PC / 에이전트]                         [커리어인연 서비스]
 링크드인 검색 결과 1~3쪽 읽기 (본인 로그인, 읽기만)
   └─ JSON 만들기 ──── POST /api/batch/linkedin-scan ──▶ 받기(토큰 확인)
                                                        ├─ 칸 맞추기(normalize)
[07:05 서비스 배치]                                     ├─ 중복 제거 (출처+공고번호)
 python -m app.batch ats  ── Greenhouse/Lever/Ashby ──▶ ├─ 처음 본 날 · 마지막 본 날 · 본 횟수
                                                        └─ DB 저장 (careerfate_records kind=feed)
[구직자 화면]
 링크드인 공고 분석 → ⓪ 오늘의 새 공고
   NEW 표시 · 직종(세일즈·파트너십/개발/딜리버리…) · 직급(일반·주니어·시니어·리더)
   · 예상 연봉 · 인터뷰 핵심 키워드 · 참고 적합도 순위 · 원문 링크 · 자세히 분석
```

---

## 3. 에이전트 → 서비스 데이터 약속 (그대로 맞추면 됨)

**주소** `POST http://<서비스>/api/batch/linkedin-scan`
**헤더** `X-Batch-Token: <BATCH_TOKEN>` · `Content-Type: application/json`

```json
{
  "run_at": "2026-11-12 07:00",
  "items": [
    {
      "title": "Partner Manager, Korea",
      "company": "회사 이름",
      "location": "Seoul, South Korea",
      "work_type": "Hybrid",
      "posted": "2 days ago",
      "tags": ["Easy Apply", "Be an early applicant"],
      "alumni": 3,
      "url": "https://www.linkedin.com/jobs/view/4100000001/"
    }
  ]
}
```

| 칸 | 필수 | 설명 |
|---|---|---|
| title | ✓ | 직무명 (없으면 그 줄은 버림) |
| url | 권장 | 공고 주소 — `jobs/view/번호`에서 공고 번호를 뽑아 **중복 제거 기준**으로 씀 |
| company · location · work_type · posted | | 회사 · 근무지 · On-site/Hybrid/Remote · 게시 시점 |
| tags | | Easy Apply · Be an early applicant 등 (배열 또는 쉼표 글) |
| alumni | | 동문 수 (숫자 또는 "3 alumni") |

- 한 번에 최대 500개. 같은 공고를 다시 보내면 새로 쌓지 않고 '마지막 본 날 · 본 횟수'만 바뀜
- 응답: `{"new": 새 공고 수, "seen": 이미 본 수, "skipped": 버린 줄, "total": …}`
- 오류: 토큰 미설정 503 · 토큰 틀림 401 · items 비었음 400

**파일로 넣기** (에이전트가 파일만 만들 때): `python -m app.batch linkedin-file 결과.json` (JSON 또는 CSV, 같은 칸 이름)

---

## 4. 사용자 Python 에이전트 서비스에 넣는 코드 (예시)

```python
import os, requests
from datetime import datetime

SERVICE = os.getenv("CAREERFATE_URL", "http://localhost:8000")
TOKEN = os.getenv("BATCH_TOKEN")          # 서비스의 .env 와 같은 값 (코드·깃에 넣지 않기)

def send_scan(rows: list[dict]) -> dict:
    """에이전트가 읽은 링크드인 검색 결과(rows)를 커리어인연으로 보냄."""
    body = {"run_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "items": [{"title": r["title"], "company": r.get("company"), "location": r.get("location"),
                       "work_type": r.get("work_type"), "posted": r.get("posted"), "tags": r.get("tags", []),
                       "alumni": r.get("alumni", 0), "url": r.get("url")} for r in rows]}
    res = requests.post(f"{SERVICE}/api/batch/linkedin-scan", json=body,
                        headers={"X-Batch-Token": TOKEN}, timeout=30)
    res.raise_for_status()
    return res.json()            # {"new": 4, "seen": 18, ...}
```

에이전트 쪽 규칙 (꼭 지키기)
1. **하루 1번**, 검색 결과 **1~3쪽**만, 쪽 사이 몇 초씩 쉬기
2. **읽기만** — 지원 · 저장 · 메시지 · 숨기기 누르지 않기
3. 링크드인이 본인 확인·캡차·경고를 띄우면 **바로 멈추고 사람에게 알리기**
4. 로그인 비밀번호·쿠키를 코드·파일에 저장하지 않기 (사람이 브라우저에서 로그인)

---

## 5. 서비스 쪽 설정

| 설정 | 어디 | 내용 |
|---|---|---|
| `BATCH_TOKEN` | 상위 폴더 `.env` | 에이전트가 보낼 때 쓰는 비밀값(긴 무작위 글자). 없으면 받기 꺼짐 |
| `BATCH_TIME` | 상위 폴더 `.env` (선택) | `07:00` → 서버가 켜져 있는 동안 매일 그 시각 ATS 배치 |
| `data/ats_sources.json` | 프로젝트 | 공개 채용 API 회사 목록 (`data/ats_sources.example.json` 참고) |
| 작업 스케줄러 (선택) | Windows | 매일 07:05 `..\.venv\Scripts\python.exe -m app.batch ats` (작업 폴더 = mini-pjt) |

---

## 6. 화면 (구직자)

**★ 구인 회사 분석 (첫 탭 · 가장 중요)** — 쌓인 링크드인 공고를 회사별로: 무엇을 얼마나 뽑나 · 채용 신호(추정) · 나와의 연결(가장 잘 맞는 공고 · 인터뷰 공통 키워드 · 서비스에 있는 회사면 회사 인연도) · 회사 적합도 순위


링크드인 공고 분석 → **⓪ 오늘의 새 공고**
- 마지막 배치(시각 · 출처 · 새 공고 수), KPI: 오늘 가장 잘 맞는 공고 · 오늘 새로 나온 공고 · 쌓인 공고(14일) · 적합도 70↑
- 직종 칩 필터 + **새 공고만**
- 공고 카드: NEW · 직종 · 회사 · 근무 형태 · 게시 시점 · 직급 · 예상 연봉 · Easy Apply/early applicant/동문 수 · 출처·처음 본 날·본 횟수 · 인터뷰 핵심 키워드 3개 · 적합도 이유 · 원문 ↗ · 자세히 분석 · (서비스에 있는 회사면) 회사 인연도 ↗
- 직종 분류: 파트너십·제휴·사업개발(Partner Manager · Alliance · Partnerships · Channel)은 **세일즈**, HR Business Partner · Talent Acquisition 같은 IT 외 직무는 **기타**(아래로)
- 참고 적합도 100 = 직종 40 + 직급 30 + 직무명 속 내 기술 30 (매칭률·회사 인연도와 별개 — 배점 변경은 사용자 결정)

---

## 7. 단계별 일정

| 단계 | 할 일 | 상태 |
|---|---|---|
| 1 | 받기 API · 중복 제거 · 피드 저장 · 오늘의 새 공고 화면 · ATS 가져오기 · 배치 명령 | ✅ 완료 (시험 통과) |
| 2 | `.env`에 BATCH_TOKEN · (선택) BATCH_TIME, `data/ats_sources.json`에 지원할 회사 목록 | 사용자 |
| 3 | 에이전트(linkedin-job-scan 등)가 결과를 3장 모양으로 보내게 연결 · 예약 실행 | 사용자 에이전트 |
| 4 | 새 공고 알림(메일·메신저), 오래된 공고 정리(30일), 에이전트 실행 기록 화면 | 다음 |
