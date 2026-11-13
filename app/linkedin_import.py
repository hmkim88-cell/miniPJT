"""내 링크드인 공고 가져오기 — 링크드인이 공식으로 주는 '내 데이터'만 사용 (서버는 링크드인에 접속하지 않음).

  1) 링크드인 데이터 내보내기 (설정 → 데이터 개인정보 → 내 데이터 사본 받기) ZIP / CSV
       - Saved Jobs.csv       : 저장한 공고  (Saved Date, Job Url, Job Title, Company Name)
       - Job Applications.csv : 지원한 공고  (Application Date, Company Name, Job Title, Job Url …)
     열 이름은 조금 달라도 'Title'·'Company'·'Url'·'Date'가 들어 있으면 읽음
  2) 링크드인 채용 알림 메일 (Gmail 등으로 받은 메일 .eml 파일, 또는 메일 내용 붙여넣기)
       - 메일 안의 'linkedin.com/…/jobs/view/번호' 링크마다 바로 위 줄들을 직무·회사·지역으로 읽음

그다음 공고마다: 직종 · 직급(일반·주니어·시니어·리더) · 예상 연봉 · 인터뷰 핵심 키워드 · 나와의 적합도(참고 100점)
"""
from __future__ import annotations

import csv
import email
import html as htmllib
import io
import re
import zipfile
from email import policy

from . import linkedin_jobs as lj
from .jobs import JOB_FAMILIES, JOBS

MAX_JOBS = 200
_JOB_ID = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?#\s\"']*-)?(\d{6,})", re.I)


# ───────── 1) 데이터 내보내기 CSV / ZIP ─────────
def _pick(row: dict, *names) -> str:
    for k, v in row.items():
        kl = (k or "").strip().lower()
        if any(n in kl for n in names):
            return (v or "").strip()
    return ""


def parse_export_csv(data: bytes, name: str) -> list[dict]:
    text = None
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("CSV 글자 인코딩을 알 수 없어요.")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or not any(("title" in (k or "").lower()) for k in rows[0].keys()):
        return []
    kind = "applied" if "application" in name.lower() or any("application" in (k or "").lower() for k in rows[0]) else "saved"
    out = []
    for r in rows:
        title, company, url = _pick(r, "title"), _pick(r, "company"), _pick(r, "url", "link")
        if not title:
            continue
        m = _JOB_ID.search(url)
        out.append({"title": title, "company": company, "location": "", "job_id": m.group(1) if m else None,
                    "url": f"https://www.linkedin.com/jobs/view/{m.group(1)}/" if m else "", "date": _pick(r, "date")[:20],
                    "kind": kind})
    return out


def parse_export_zip(data: bytes) -> list[dict]:
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            low = n.lower()
            if low.endswith(".csv") and ("saved" in low or "application" in low) and "job" in low:
                if z.getinfo(n).file_size > 5 * 1024 * 1024:
                    continue
                out += parse_export_csv(z.read(n), n)
    return out


# ───────── 2) 채용 알림 메일 ─────────
def _email_to_text(raw: bytes | str) -> str:
    """.eml → 본문 글 (HTML이면 링크 주소를 글 옆에 남기고 태그 제거)."""
    msg = email.message_from_bytes(raw if isinstance(raw, bytes) else raw.encode("utf-8"), policy=policy.default)
    parts = []
    for p in msg.walk():
        ct = p.get_content_type()
        if ct in ("text/plain", "text/html"):
            try:
                parts.append((ct, p.get_content()))
            except Exception:  # noqa: BLE001
                continue
    html_part = next((c for t, c in parts if t == "text/html"), None)
    if html_part:
        return html_to_text(html_part)
    return "\n".join(c for t, c in parts if t == "text/plain")


def html_to_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', lambda m: f"\n{m.group(2)}\n{m.group(1)}\n", h)
    h = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|td|li|h\d|table)>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return htmllib.unescape(h)


_NOISE = re.compile(r"^(view job|see all jobs|apply|easy apply|지원하기|공고 보기|new|promoted|actively recruiting|"
                    r"\d+\s*(?:connections?|alumni|applicants?)|.*(?:ago|전)$|https?://\S+|unsubscribe|.*job alert.*|.*채용 알림.*)$", re.I)


def _ok_line(t: str) -> bool:
    return bool(t) and not _JOB_ID.search(t) and not _NOISE.match(t) and len(t) <= 120


def parse_alert_text(text: str) -> list[dict]:
    """메일 글에서 공고 링크마다 직무 · 회사 · 지역을 읽음 (같은 공고는 한 번만).
    · HTML 메일: 링크 글자 = 직무, 링크 '아래' 줄들 = 회사·지역 (사진 링크처럼 글자 없는 링크는 건너뛰고 다음 링크 사용)
    · 글 메일: 'View job: 주소' 줄 '위' 줄들 = 직무·회사·지역"""
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    is_link = [bool(_JOB_ID.search(x)) for x in lines]
    order, occ = [], {}
    for i, ln in enumerate(lines):
        m = _JOB_ID.search(ln)
        if m:
            occ.setdefault(m.group(1), []).append(i)
            if m.group(1) not in order:
                order.append(m.group(1))
    out = []
    for jid in order:
        title = company = location = ""
        for i in occ[jid]:   # ① HTML 방식: 주소만 있는 줄 + 바로 위 줄이 링크 글자
            if lines[i].lower().startswith("http") and i > 0 and _ok_line(lines[i - 1]):
                title, after = lines[i - 1], []
                for k in range(i + 1, min(len(lines), i + 14)):
                    t = lines[k]
                    if is_link[k] or (k + 1 < len(lines) and is_link[k + 1] and _ok_line(t)):   # 다음 링크(또는 그 링크 글자)에서 멈춤
                        break
                    if _ok_line(t):
                        after.append(t)
                        if len(after) == 2:
                            break
                company = after[0] if after else ""
                location = after[1] if len(after) > 1 else ""
                break
        if not title:   # ② 글 방식: 링크 줄 위의 줄들
            i, ctx = occ[jid][0], []
            for k in range(i - 1, max(-1, i - 12), -1):
                if is_link[k]:
                    break
                if _ok_line(lines[k]):
                    ctx.append(lines[k])
                    if len(ctx) == 3:
                        break
            ctx.reverse()
            if not ctx:
                continue
            title, company, location = ctx[0], (ctx[1] if len(ctx) > 1 else ""), (ctx[2] if len(ctx) > 2 else "")
        if "·" in company and not location:   # '회사 · 지역'이 한 줄
            company, location = [x.strip() for x in company.split("·", 1)]
        out.append({"title": title, "company": company, "location": location, "job_id": jid,
                    "url": f"https://www.linkedin.com/jobs/view/{jid}/", "date": "", "kind": "alert"})
    return out


class SinglePosting(Exception):
    """PDF가 공고 1개짜리(공고 화면 저장)일 때 — 목록 대신 '자세히 분석'으로 넘김."""
    def __init__(self, text: str, url: str = ""):
        super().__init__("single")
        self.text, self.url = text, url


def parse_any(filename: str, data: bytes | None, pasted: str = "") -> tuple[list[dict], str]:
    name = (filename or "").lower()
    if data:
        if name.endswith(".zip"):
            return parse_export_zip(data), "링크드인 데이터 내보내기 (ZIP)"
        if name.endswith(".csv"):
            return parse_export_csv(data, filename), "링크드인 데이터 내보내기 (CSV)"
        if name.endswith(".eml"):
            return parse_alert_text(_email_to_text(data)), "링크드인 채용 알림 메일 (.eml)"
        if name.endswith((".html", ".htm")):
            return parse_alert_text(html_to_text(data.decode("utf-8", "ignore"))), "링크드인 채용 알림 메일 (HTML)"
        if name.endswith(".txt"):
            return parse_alert_text(data.decode("utf-8", "ignore")), "링크드인 채용 알림 메일 (글)"
        if name.endswith(".pdf"):   # 채용 알림 메일·검색 결과·공고 화면을 'PDF로 저장'한 파일
            from .resume_file import pdf_text_with_links
            try:
                text = pdf_text_with_links(data)
            except ValueError:
                raise
            except Exception:  # noqa: BLE001
                raise ValueError("PDF를 읽지 못했어요. 파일이 손상되지 않았는지 확인해 주세요.")
            if len(text.strip()) < 30:
                raise ValueError("PDF에서 글자를 찾지 못했어요. 스캔한 이미지 PDF라면 글을 복사해 붙여넣어 주세요.")
            jobs = parse_alert_text(text)
            if len(jobs) >= 2:
                return jobs, "링크드인 채용 PDF (알림·검색 결과)"
            raise SinglePosting(text, jobs[0]["url"] if jobs else "")
        raise ValueError("ZIP·CSV(데이터 내보내기), .eml·.html·.txt(채용 알림 메일), PDF(채용 화면 저장)만 올릴 수 있어요.")
    if pasted.strip():
        t = html_to_text(pasted) if "<a " in pasted.lower() else pasted
        return parse_alert_text(t), "링크드인 채용 알림 메일 (붙여넣기)"
    raise ValueError("파일을 올리거나 메일 내용을 붙여넣어 주세요.")


# ───────── 3) 나와의 적합도 (참고 100점: 직종 40 + 직급 30 + 기술 키워드 30) ─────────
NEAR = {  # 옮겨 가기 쉬운 이웃 직종 (반점)
    "개발": {"데이터·AI", "인프라·클라우드", "프리세일즈"}, "데이터·AI": {"개발", "프리세일즈"}, "인프라·클라우드": {"개발", "프리세일즈"},
    "세일즈": {"프리세일즈", "고객 성공"}, "프리세일즈": {"세일즈", "개발", "데이터·AI", "인프라·클라우드", "딜리버리"},
    "딜리버리": {"프리세일즈", "고객 성공"}, "고객 성공": {"세일즈", "딜리버리"},
}


def my_tier(profile: dict) -> str:
    y = profile.get("years")
    lvl = profile.get("desired_level") or profile.get("level")
    if lvl == "리드" or (y is not None and y >= 10):
        return "리더"
    if lvl == "시니어" or (y is not None and y >= 5):
        return "시니어"
    if y is not None and y < 1:
        return "일반"
    return "주니어"


def fit(job: dict, fam: str, tier: str, profile: dict) -> dict:
    mine_f = profile.get("desired_family") or profile.get("job_family") or ""
    mine_t = my_tier(profile)
    reasons = []
    if not mine_f:
        f_pts = 20; reasons.append("내 직종을 몰라 직종 20점(중간)")
    elif fam == mine_f:
        f_pts = 40; reasons.append(f"직종 일치 ({fam}) +40")
    elif fam in NEAR.get(mine_f, set()):
        f_pts = 20; reasons.append(f"이웃 직종 ({mine_f} → {fam}) +20")
    else:
        f_pts = 0; reasons.append(f"다른 직종 ({mine_f} ≠ {fam}) +0")
    d = abs(lj.TIERS.index(tier) - lj.TIERS.index(mine_t))
    t_pts = 30 if d == 0 else 15 if d == 1 else 0
    reasons.append(f"직급 {tier} · 나 {mine_t} " + ("일치 +30" if d == 0 else "한 단계 차이 +15" if d == 1 else "두 단계 이상 +0"))
    skills = [s for s in (profile.get("skills") or []) if s]
    title = job.get("title", "")
    hits = [s for s in skills if re.search(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9])", title, re.I)]
    if hits:
        k_pts = min(30, 10 + 10 * len(hits)); reasons.append(f"직무명에 내 기술 {', '.join(hits[:3])} +{k_pts}")
    else:
        k_pts = 10; reasons.append("직무명에 내 기술 없음 +10 (상세 분석에서 다시 확인)")
    return {"score": f_pts + t_pts + k_pts, "parts": {"family": f_pts, "tier": t_pts, "keyword": k_pts}, "reasons": reasons,
            "my_family": mine_f, "my_tier": mine_t}


def analyze(jobs: list[dict], profile: dict) -> list[dict]:
    def svc_job(j):   # 서비스에 같은 회사 공고가 있으면: 같은 직무명 → 없으면 그 회사의 첫 공고
        same = [x for x in JOBS if x["company"].lower() == (j.get("company") or "").lower()]
        return next((x for x in same if x["title"].lower() == j["title"].lower()), same[0] if same else None)
    out = []
    for j in jobs[:MAX_JOBS]:
        fam = lj.classify_family(j["title"], j["title"])["family"]
        tier = lj.classify_tier(j["title"], "", None)
        sal = lj.estimate_salary({}, fam, tier["tier"], JOBS)
        f = fit(j, fam, tier["tier"], profile)
        iv = lj.interview_keywords(fam, j["title"], [])[:3]
        svc = svc_job(j)
        out.append({**j, "family": fam, "tier": tier["tier"], "tier_why": tier["why"],
                    "salary": {"min": sal["min"], "max": sal["max"], "kind": sal["kind"], "n": sal["n"]},
                    "fit": f, "interview": [{"keyword": x["keyword"], "prep": x["prep"]} for x in iv],
                    "service_job_id": svc["id"] if svc else None})
    out.sort(key=lambda x: (-x["fit"]["score"], x["title"]))
    for i, x in enumerate(out):
        x["rank"] = i + 1
    return out
