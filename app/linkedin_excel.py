"""링크드인 구인 내용 엑셀(.xlsx) 읽기 — 사용자가 내려받아 올린 파일만 (서버는 링크드인에 접속하지 않음).

· 열 이름은 영어·한글 모두 (Job Title / 직무명, Company / 회사, Description / 공고 내용 …), 순서·위치 상관없음
· 머리글 줄은 위쪽 15줄 안에서 '직무명'이 있는 줄을 찾음, 모든 시트를 읽음
· 같은 공고(링크 번호 또는 회사+직무명)는 한 번만
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime

MAX_ROWS = 2000
# 칸 이름 → 머리글로 쓰일 수 있는 말 (소문자 · 띄어쓰기/기호 빼고 비교)
ALIASES = {
    "title": ["jobtitle", "title", "position", "positiontitle", "role", "jobname", "직무", "직무명", "공고명", "공고제목", "포지션", "채용제목", "직책"],
    "company": ["company", "companyname", "employer", "organization", "회사", "회사명", "기업", "기업명", "채용회사"],
    "location": ["location", "joblocation", "city", "근무지", "근무지역", "지역", "위치"],
    "work_type": ["workplacetype", "worktype", "workplace", "remote", "onsiteremote", "근무형태", "근무방식"],
    "employment": ["employmenttype", "jobtype", "contracttype", "고용형태", "채용형태"],
    "seniority": ["senioritylevel", "seniority", "experiencelevel", "level", "직급", "경력수준", "레벨", "경력"],
    "posted": ["posted", "posteddate", "dateposted", "postedat", "listedat", "listed", "postingdate", "게시일", "등록일", "게시", "공고일"],
    "url": ["url", "joburl", "link", "joblink", "applyurl", "linkedinurl", "링크", "공고링크", "주소", "공고주소"],
    "description": ["description", "jobdescription", "aboutthejob", "details", "공고내용", "상세", "상세내용", "내용", "직무설명", "직무내용", "주요업무"],
    "salary": ["salary", "compensation", "pay", "salaryrange", "연봉", "급여", "보상", "연봉범위"],
    "applicants": ["applicants", "applicantcount", "numberofapplicants", "지원자", "지원자수"],
    "industry": ["industry", "industries", "산업", "업종"],
    "function": ["jobfunction", "function", "직무분야", "직군"],
    "job_id": ["jobid", "id", "공고번호", "공고id"],
}
_LI = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?#\s]*-)?(\d{6,})", re.I)


def _norm(h) -> str:
    return re.sub(r"[\s_\-./()·:]+", "", str(h or "")).lower()


def _map_header(row: list) -> dict[str, int]:
    found = {}
    for i, h in enumerate(row):
        n = _norm(h)
        if not n:
            continue
        for field, names in ALIASES.items():
            if field not in found and n in names:
                found[field] = i
                break
    return found


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def parse_excel(data: bytes) -> tuple[list[dict], dict]:
    """→ (공고 목록, 정보{시트, 머리글 줄, 찾은 칸, 못 찾은 칸, 건너뛴 줄})."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001
        raise ValueError("엑셀 파일을 열지 못했어요. .xlsx 파일인지, 암호가 걸려 있지 않은지 확인해 주세요.")
    jobs, info, seen = [], {"sheets": [], "skipped": 0}, set()
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        head, cols, k = None, {}, 0
        for row in rows:
            k += 1
            m = _map_header(list(row))
            if "title" in m and len(m) >= 2:
                head, cols = k, m
                break
            if k >= 15:
                break
        if not head:
            continue
        info["sheets"].append({"sheet": ws.title, "header_row": head, "columns": sorted(cols),
                               "missing": [f for f in ("company", "location", "url", "description", "seniority", "salary") if f not in cols]})
        for row in rows:
            if len(jobs) >= MAX_ROWS:
                break
            g = lambda f: _cell(row[cols[f]]) if f in cols and cols[f] < len(row) else ""
            title = g("title")
            if not title:
                info["skipped"] += 1
                continue
            url = g("url")
            m = _LI.search(url) or _LI.search(g("job_id"))
            jid = m.group(1) if m else (g("job_id") or "")
            key = jid or (g("company").lower() + "|" + title.lower())
            if key in seen:
                info["skipped"] += 1
                continue
            seen.add(key)
            desc = g("description")[:8000]
            jobs.append({"title": title[:160], "company": g("company")[:120], "location": g("location")[:120],
                         "job_id": jid, "url": f"https://www.linkedin.com/jobs/view/{jid}/" if m else url[:400],
                         "date": g("posted")[:20], "posted": g("posted")[:40], "kind": "excel",
                         "work_type": g("work_type")[:40], "employment": g("employment")[:40], "seniority": g("seniority")[:60],
                         "description": desc, "salary_text": g("salary")[:120], "applicants": g("applicants")[:20],
                         "industry": g("industry")[:80], "function": g("function")[:80]})
    if not info["sheets"]:
        raise ValueError("엑셀에서 '직무명(Job Title)' 열을 찾지 못했어요. 첫 줄(또는 위쪽 줄)에 열 이름이 있는지 확인해 주세요. "
                         "화면의 '엑셀 양식 받기'로 열 이름을 맞출 수 있어요.")
    return jobs, info


def template_xlsx() -> bytes:
    """열 이름을 맞추기 쉬운 빈 양식 + 예시 1줄(가상)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "LinkedIn Jobs"
    head = ["Job Title", "Company", "Location", "Workplace Type", "Employment Type", "Seniority Level", "Posted Date",
            "Job URL", "Salary", "Applicants", "Industry", "Description"]
    ws.append(head)
    ws.append(["Partner Manager, Korea", "Nimbus Cloud (예시·가상)", "Seoul, South Korea", "Hybrid", "Full-time", "Mid-Senior level",
               "2026-11-12", "https://www.linkedin.com/jobs/view/4100000001/", "KRW 90,000,000 - 120,000,000", "25",
               "Software Development", "We are hiring a Partner Manager to grow our partner ecosystem in Korea. Requirements: 7+ years of partnerships experience, Salesforce, fluent English."])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="0A66C2")
    for col, w in zip("ABCDEFGHIJKL", [34, 24, 22, 14, 14, 16, 12, 44, 26, 10, 22, 80]):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
