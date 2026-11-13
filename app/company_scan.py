"""구인 회사 분석 — 링크드인 공고(매일 배치 피드 + 가져온 공고)를 회사별로 묶어 '어떤 회사가 무엇을 얼마나 뽑는지'와 나와의 적합을 분석.

모두 공고 데이터에서 나온 사실 + 규칙으로 만든 '채용 신호(추정)'. 회사 재무·주가 같은 외부 정보는 지어내지 않음
(서비스에 이미 있는 회사면 그 회사의 회사 인연도 점수와 대시보드를 연결).

회사 적합도(참고 100) = 가장 잘 맞는 공고의 적합도 × 0.6  +  내 직종 공고 비중 × 20  +  채용 활발도 20 (공고 수 최대 10 + 새 공고 10)
"""
from __future__ import annotations

from collections import Counter

from .jobs import JOBS
from .linkedin_jobs import TIERS

SALES_LIKE = {"세일즈", "프리세일즈", "고객 성공"}
TECH_LIKE = {"개발", "데이터·AI", "인프라·클라우드"}


def _signals(js: list[dict]) -> list[dict]:
    fam = Counter(j["family"] for j in js)
    tiers = Counter(j["tier"] for j in js)
    korea = sum(1 for j in js if any(k in (j.get("location") or "").lower() for k in ("korea", "seoul", "서울", "판교", "pangyo")))
    out = []
    if len(js) >= 3:
        out.append({"tone": "up", "text": f"채용이 활발해요 — 공고 {len(js)}개를 동시에 열었어요"})
    if sum(fam[f] for f in SALES_LIKE) >= 2:
        out.append({"tone": "up", "text": f"영업·고객 조직 확대 신호 (세일즈·프리세일즈·고객 성공 {sum(fam[f] for f in SALES_LIKE)}건){' — 한국 근무' if korea else ''}"})
    if sum(fam[f] for f in TECH_LIKE) >= 2:
        out.append({"tone": "up", "text": f"엔지니어링 확대 신호 (개발·데이터·인프라 {sum(fam[f] for f in TECH_LIKE)}건)"})
    if fam["딜리버리"] >= 1:
        out.append({"tone": "info", "text": "딜리버리(구축·PM) 채용 — 고객 프로젝트가 늘고 있을 가능성"})
    if tiers["리더"] >= 1:
        out.append({"tone": "info", "text": f"리더급 {tiers['리더']}건 — 팀 신설·확장 단계일 가능성"})
    new = sum(1 for j in js if j.get("is_new"))
    if new:
        out.append({"tone": "up", "text": f"최근 새 공고 {new}개 — 지금 지원하면 빠른 지원자"})
    old = [j for j in js if (j.get("runs") or 1) >= 5]
    if old:
        out.append({"tone": "warn", "text": f"오래 열린 공고 {len(old)}개 — 맞는 사람을 아직 못 찾은 상태(협상 여지)"})
    alumni = sum(int(j.get("alumni") or 0) for j in js)
    if alumni:
        out.append({"tone": "info", "text": f"동문 {alumni}명 재직 표시 — 추천·커피챗 경로"})
    early = sum(1 for j in js if any("early" in t.lower() for t in (j.get("tags") or [])))
    if early:
        out.append({"tone": "up", "text": f"'Be an early applicant' {early}건 — 지원자가 아직 적어요"})
    if fam["기타"] and fam["기타"] == len(js):
        out.append({"tone": "warn", "text": "IT 외 직무만 채용 중"})
    return out


def analyze_companies(jobs: list[dict], profile: dict) -> list[dict]:
    """jobs = linkedin_import.analyze()를 거친 공고들 (fit·family·tier·salary·interview 포함)."""
    groups: dict[str, list[dict]] = {}
    for j in jobs:
        name = (j.get("company") or "").strip() or "회사 정보 없음"
        groups.setdefault(name, []).append(j)
    my_f = profile.get("desired_family") or profile.get("job_family") or ""
    out = []
    for name, js in groups.items():
        js.sort(key=lambda x: -x["fit"]["score"])
        best = js[0]
        fam = Counter(j["family"] for j in js)
        mine = fam.get(my_f, 0) if my_f else 0
        new = sum(1 for j in js if j.get("is_new"))
        score_best = round(best["fit"]["score"] * 0.6)
        score_mine = round(20 * mine / len(js)) if my_f else 10
        score_act = min(10, 2 * len(js)) + (10 if new else 0)
        total = score_best + score_mine + score_act
        kw = Counter(x["keyword"] for j in js for x in j.get("interview", []))
        svc = next((x for x in JOBS if x["company"].lower() == name.lower()), None)
        lo = min(j["salary"]["min"] for j in js)
        hi = max(j["salary"]["max"] for j in js)
        out.append({
            "company": name, "score": total, "parts": {"best": score_best, "mine": score_mine, "activity": score_act},
            "count": len(js), "new": new, "my_family_count": mine,
            "families": [{"family": f, "n": n} for f, n in fam.most_common()],
            "tiers": [{"tier": t, "n": sum(1 for j in js if j["tier"] == t)} for t in TIERS if any(j["tier"] == t for j in js)],
            "work_types": [w for w, _ in Counter((j.get("work_type") or "").title() for j in js if j.get("work_type")).most_common(3)],
            "locations": [l for l, _ in Counter(j.get("location") for j in js if j.get("location")).most_common(2)],
            "salary": {"min": lo, "max": hi}, "best": {"title": best["title"], "score": best["fit"]["score"], "url": best.get("url"), "job_id": best.get("job_id")},
            "interview": [k for k, _ in kw.most_common(4)], "signals": _signals(js),
            "sources": sorted({j.get("source_name") or {"saved": "저장한 공고", "applied": "지원한 공고", "alert": "채용 알림"}.get(j.get("kind"), "링크드인") for j in js}),
            "postings": [{"title": j["title"], "family": j["family"], "tier": j["tier"], "fit": j["fit"]["score"], "url": j.get("url"),
                          "is_new": j.get("is_new", False), "posted": j.get("posted") or j.get("date") or "", "work_type": j.get("work_type", "")} for j in js],
            "service_job_id": svc["id"] if svc else None, "service_company": bool(svc),
        })
    out.sort(key=lambda c: (-c["score"], -c["count"], c["company"]))
    for i, c in enumerate(out):
        c["rank"] = i + 1
    return out
