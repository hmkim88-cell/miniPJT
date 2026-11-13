"""인맥 추천: 나와 같은 학교·같은 전 직장 출신의 '추천인' 찾기.

추천인 = 이 서비스에 **스스로 추천인으로 등록하고 공개에 동의한** 외국계 IT 재직자 (데모는 가상 인물).
링크드인 등 외부에서 다른 사람 정보를 수집하지 않습니다. 이름은 가운데 글자를 가려 보여 줍니다.
학교·인맥은 매칭률에 넣지 않습니다 (참고용, 추천 요청 경로만 보여 줌).
"""
from __future__ import annotations

from datetime import datetime

from .jobs import get_job


def _p(id, name, company, role, school, major, past, years):
    return {"id": id, "name": name, "company": company, "role": role, "school": school, "major": major,
            "past": past, "years_here": years, "consent": True}


REFERRERS = [
    _p(1, "김도현", "Aeroloop Korea", "Senior Backend Engineer", "서울대학교", "컴퓨터공학", ["네이버", "삼성SDS"], 3),
    _p(2, "이서윤", "Brightwave Data", "Data Engineering Manager", "KAIST", "전산학", ["카카오"], 4),
    _p(3, "박준호", "Brightwave Data", "Data Engineer", "연세대학교", "산업공학", ["삼성SDS", "쿠팡"], 2),
    _p(4, "최유나", "Corvant Payments", "Staff Engineer", "고려대학교", "컴퓨터학", ["토스", "LG CNS"], 5),
    _p(5, "정민석", "Delmora Health", "Frontend Lead", "한양대학교", "소프트웨어", ["라인"], 2),
    _p(6, "강지민", "Elyra AI Korea", "ML Engineer", "서울대학교", "통계학", ["삼성SDS"], 2),
    _p(7, "윤하은", "Elyra AI Korea", "Engineering Manager", "POSTECH", "컴퓨터공학", ["네이버", "SK C&C"], 4),
    _p(8, "임재훈", "Fjordstack", "DevOps Engineer", "성균관대학교", "소프트웨어", ["LG CNS"], 3),
    _p(9, "한소희", "Granite Shield Security", "Security Architect", "KAIST", "정보보호", ["안랩"], 6),
    _p(10, "오세진", "Halcyon Commerce", "Full-stack Engineer", "중앙대학교", "컴퓨터공학", ["쿠팡"], 2),
    _p(11, "서다은", "Ivorpath Mobility", "Android Lead", "한양대학교", "전자공학", ["현대오토에버", "삼성SDS"], 4),
    _p(12, "신우진", "Junipra Apps", "iOS Engineer", "건국대학교", "컴퓨터공학", ["라인"], 1),
    _p(13, "권태양", "Kestrelbyte Cloud", "Principal Architect", "연세대학교", "전기전자", ["삼성SDS", "AWS"], 5),
    _p(14, "황예린", "Kestrelbyte Cloud", "Solutions Architect", "고려대학교", "경영학", ["SK C&C"], 3),
    _p(15, "문지후", "Lumora Games", "Server Engineer", "홍익대학교", "게임공학", ["넥슨"], 2),
    _p(16, "장하늘", "Mirefield Analytics", "Senior ML Engineer", "서울대학교", "산업공학", ["카카오"], 3),
    _p(17, "배승민", "Norvale Robotics", "Robotics SW Lead", "KAIST", "기계공학", ["삼성전자"], 5),
    _p(18, "유채은", "Orbisfin", "Backend Engineer", "성균관대학교", "컴퓨터공학", ["토스"], 2),
    _p(19, "남궁현", "Pellucid Labs", "Founding Engineer", "고려대학교", "컴퓨터학", ["삼성SDS", "네이버"], 1),
    _p(20, "노은비", "Quillon Software", "QA Lead", "이화여자대학교", "컴퓨터공학", ["LG CNS"], 4),
    _p(21, "하준영", "Ravencrest Infra", "SRE", "부산대학교", "정보컴퓨터", ["카카오"], 3),
    _p(22, "고은솔", "Solenne Media", "Product Engineer", "연세대학교", "컴퓨터과학", ["네이버"], 2),
    _p(23, "차윤호", "Tidemark Semicon", "Director of Engineering", "POSTECH", "전자공학", ["삼성전자", "SK하이닉스"], 7),
    _p(24, "백지수", "Tidemark Semicon", "Software Engineer", "서울대학교", "전기정보공학", ["삼성SDS"], 2),
]

# 출신 지역(지연) — 추천인이 공개에 동의한 값
HOMETOWN = {1: "부산", 2: "대전", 3: "서울", 4: "대구", 5: "경기", 6: "부산", 7: "경북", 8: "광주", 9: "서울",
            10: "경기", 11: "부산", 12: "전북", 13: "서울", 14: "대구", 15: "경기", 16: "광주", 17: "경북",
            18: "서울", 19: "부산", 20: "충남", 21: "부산", 22: "강원", 23: "경북", 24: "대전"}
for _r in REFERRERS:
    _r["hometown"] = HOMETOWN[_r["id"]]
REGIONS = ["서울", "경기", "인천", "강원", "충북", "충남", "대전", "세종", "전북", "전남", "광주",
           "경북", "경남", "대구", "울산", "부산", "제주"]

SCHOOLS = sorted({r["school"] for r in REFERRERS})
REFERRAL_REQUESTS: list[dict] = []   # 추천 요청 (DB에 저장, 서버 시작 때 복원)


def _norm(s: str) -> str:
    return s.replace(" ", "").replace("(주)", "").lower()


def _same_school(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    # '서울대' ↔ '서울대학교'처럼 줄여 쓴 경우도 같은 학교로 봄
    return a == b or a.replace("학교", "") == b.replace("학교", "") or (len(a) >= 3 and b.startswith(a)) or (len(b) >= 3 and a.startswith(b))


def _mask(name: str) -> str:
    return name[0] + "*" + name[-1] if len(name) == 3 else name[0] + "*" * (len(name) - 1)


def connections(school: str, past_companies: list[str], hometown: str = "") -> dict[str, list[dict]]:
    """회사 이름 → 나와 연결된 추천인 목록 (학연: 학교 동문 / 지연: 같은 고향 / 전 직장 동료 출신)."""
    mine = {_norm(c) for c in past_companies if c.strip()}
    out: dict[str, list[dict]] = {}
    for r in REFERRERS:
        if not r["consent"]:
            continue
        links = []
        if _same_school(school, r["school"]):
            links.append(f"학연 ({r['school']} {r['major']} 동문)")
        if hometown and hometown == r["hometown"]:
            links.append(f"지연 ({r['hometown']} 출신)")
        shared = [c for c in r["past"] if _norm(c) in mine]
        if shared:
            links.append(f"전 직장 동료 출신 ({', '.join(shared)})")
        if links:
            out.setdefault(r["company"], []).append({
                "id": r["id"], "name": _mask(r["name"]), "role": r["role"], "years_here": r["years_here"],
                "links": links, "strength": len(links),
                # 사내 추천(추천서) 가능: 재직 1년 이상 (데모 기준)
                "can_recommend": r["years_here"] >= 1})
    for v in out.values():
        v.sort(key=lambda x: -x["strength"])
    return out


def request_referral(referrer_id: int, job_id: int, verified: dict | None) -> dict:
    r = next((x for x in REFERRERS if x["id"] == referrer_id), None)
    job = get_job(job_id)
    if not r or not job:
        raise ValueError("없는 추천인 또는 공고예요.")
    if any(q["referrer_id"] == referrer_id and q["job_id"] == job_id for q in REFERRAL_REQUESTS):
        raise LookupError("이미 추천을 요청했어요.")
    q = {"id": len(REFERRAL_REQUESTS) + 1, "referrer_id": referrer_id, "referrer": _mask(r["name"]),
         "company": r["company"], "job_id": job_id, "job_title": job["title"], "verified": verified,
         "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "status": "추천 요청됨"}
    REFERRAL_REQUESTS.append(q)
    from . import store
    store.save("referral", q["id"], q)
    return q
