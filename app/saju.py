"""사주팔자 계산과 '공고 마감일과의 인연' 점수.

- 계산(간지, 오행)은 이 파일의 코드가 결정적으로 합니다. 같은 입력이면 항상 같은 결과.
- 풀이 문장은 ai.py에서 Claude가 씁니다.
- 년·월·일 간지는 korean-lunar-calendar(한국천문연구원 기준 데이터)를 사용합니다.
  단, 이 라이브러리는 해와 달의 경계를 절기(입춘 등)가 아닌 음력 기준으로 잡으므로
  절기 경계 근처 생일은 전문 만세력과 다를 수 있습니다 (데모 단순화).
"""
from __future__ import annotations

from datetime import date

from korean_lunar_calendar import KoreanLunarCalendar

STEMS = "갑을병정무기경신임계"          # 천간 10
BRANCHES = "자축인묘진사오미신유술해"   # 지지 12
STEM_ELEM = "목목화화토토금금수수"
BRANCH_ELEM = "수토목목토화화토금금토수"
ELEMENTS = ["목", "화", "토", "금", "수"]
HANJA = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}

# 상생: 목→화→토→금→수→목 / 상극: 목→토→수→화→금→목
GENERATES = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
CONTROLS = {"목": "토", "토": "수", "수": "화", "화": "금", "금": "목"}
SIX_HARMONY = [{"자", "축"}, {"인", "해"}, {"묘", "술"}, {"진", "유"}, {"사", "신"}, {"오", "미"}]
THREE_HARMONY = [set("신자진"), set("해묘미"), set("인오술"), set("사유축")]


def _gapja_of_solar(d: date) -> list[str]:
    """양력 날짜 -> ['경오', '신사', '경진'] (년, 월, 일)."""
    cal = KoreanLunarCalendar()
    if not cal.setSolarDate(d.year, d.month, d.day):
        raise ValueError(f"지원하지 않는 날짜: {d}")
    return [p[:2] for p in cal.getGapJaString().split()]


def _hour_pillar(day_stem: str, hour: int) -> str:
    """시주: 시간 -> 지지, 일간 -> 천간 (갑·기일 자시 = 갑자 규칙)."""
    b = ((hour + 1) // 2) % 12
    s = (STEMS.index(day_stem) % 5 * 2 + b) % 10
    return STEMS[s] + BRANCHES[b]


def to_solar(year: int, month: int, day: int, calendar: str, leap: bool = False) -> date:
    if calendar == "lunar":
        cal = KoreanLunarCalendar()
        if not cal.setLunarDate(year, month, day, leap):
            raise ValueError("올바르지 않은 음력 날짜예요.")
        y, m, d = map(int, cal.SolarIsoFormat().split("-"))
        return date(y, m, d)
    return date(year, month, day)


def calc_saju(year: int, month: int, day: int, hour: int | None, calendar: str = "solar", leap: bool = False) -> dict:
    """사주팔자와 오행 분포를 계산합니다. hour=None이면 시주 없이 세 기둥만."""
    solar = to_solar(year, month, day, calendar, leap)
    y, m, d = _gapja_of_solar(solar)
    pillars = [{"name": "년주", "gz": y}, {"name": "월주", "gz": m}, {"name": "일주", "gz": d}]
    if hour is not None:
        pillars.append({"name": "시주", "gz": _hour_pillar(d[0], hour)})

    counts = {e: 0 for e in ELEMENTS}
    for p in pillars:
        stem, branch = p["gz"][0], p["gz"][1]
        p["stem_elem"] = STEM_ELEM[STEMS.index(stem)]
        p["branch_elem"] = BRANCH_ELEM[BRANCHES.index(branch)]
        counts[p["stem_elem"]] += 1
        counts[p["branch_elem"]] += 1

    day_master = d[0]
    return {
        "solar_date": solar.isoformat(),
        "pillars": pillars,
        "elements": counts,
        "day_master": day_master,
        "day_master_elem": STEM_ELEM[STEMS.index(day_master)],
        "day_branch": d[1],
        "strongest": max(counts, key=counts.get),
        "weakest": min(counts, key=counts.get),
        "has_hour": hour is not None,
    }


def year_gapja(y: int) -> str:
    return _gapja_of_solar(date(y, 6, 1))[0]


# ---------- 십성(나와 오행의 관계) ----------
ROLE_MEANING = {
    "관성": "직장·직책·조직 (취업·이직의 별)",
    "인성": "도와주는 사람·합격 문서·자격",
    "재성": "성과·보상·연봉",
    "식상": "실력 발휘·기술·표현",
    "비겁": "나와 같은 힘·경쟁자",
}


def element_role(me: str, e: str) -> str:
    """일간 오행(me) 기준으로 오행 e가 어떤 역할인지 (십성 5분류)."""
    if e == me:
        return "비겁"
    if GENERATES[e] == me:
        return "인성"
    if GENERATES[me] == e:
        return "식상"
    if CONTROLS[me] == e:
        return "재성"
    return "관성"


def water_analysis(saju: dict) -> dict:
    """사주 안에 물(水)이 있는지, 몇 개·어디에 있는지, 나에게 어떤 역할인지."""
    where = []
    for p in saju["pillars"]:
        if p["stem_elem"] == "수":
            where.append(f"{p['name']} 천간 {p['gz'][0]}")
        if p["branch_elem"] == "수":
            where.append(f"{p['name']} 지지 {p['gz'][1]}")
    n = saju["elements"]["수"]
    status = "없음" if n == 0 else "약함" if n == 1 else "적당" if n <= 3 else "많음"
    role = element_role(saju["day_master_elem"], "수")
    return {"count": n, "status": status, "where": where, "role": role, "role_meaning": ROLE_MEANING[role]}


# 역마(이동·이직의 기운): 일지가 속한 삼합의 첫 글자를 충하는 지지
YEOKMA = {**dict.fromkeys("신자진", "인"), **dict.fromkeys("인오술", "신"),
          **dict.fromkeys("사유축", "해"), **dict.fromkeys("해묘미", "사")}
ROLE_POINTS = {"관성": 15, "인성": 10, "재성": 5, "식상": 0, "비겁": -5}


def _luck_score(saju: dict, year_gz: str, month_gz: str) -> tuple[int, list[str]]:
    """세운(그 해)·월운(그 달) 간지로 이직운 점수(0~100)와 근거를 계산."""
    me = saju["day_master_elem"]
    score, notes = 45, []
    for label, gz in (("세운", year_gz), ("월운", month_gz)):
        el = STEM_ELEM[STEMS.index(gz[0])]
        role = element_role(me, el)
        pts = ROLE_POINTS[role]
        score += pts
        notes.append(f"{label} {gz}: {el} 기운 = 나에게 {role}({ROLE_MEANING[role]}) {pts:+d}")

    branches = {year_gz[1], month_gz[1]}
    if YEOKMA[saju["day_branch"]] in branches:
        score += 10
        notes.append(f"역마 {YEOKMA[saju['day_branch']]}가 들어옴: 자리를 옮기는 기운 +10")
    if any(abs(BRANCHES.index(saju["day_branch"]) - BRANCHES.index(b)) == 6 for b in branches):
        score += 5
        notes.append(f"일지 {saju['day_branch']}와 충: 변화의 계기 (급한 결정은 주의) +5")

    luck_has_water = any(STEM_ELEM[STEMS.index(g[0])] == "수" or BRANCH_ELEM[BRANCHES.index(g[1])] == "수"
                         for g in (year_gz, month_gz))
    water = saju["elements"]["수"]
    if luck_has_water and water <= 1:
        score += 10
        notes.append("부족한 물(水)을 운에서 채워 줌: 막힌 흐름이 풀림 +10")
    elif luck_has_water and water >= 4:
        score -= 5
        notes.append("물(水)이 이미 많은데 더 들어옴: 생각이 많아 결정이 흔들림 -5")
    return max(0, min(100, score)), notes


def _verdict(score: int) -> str:
    if score >= 70:
        return "지원 적기 — 이직 가능성 높음"
    if score >= 50:
        return "도전해 볼 만함 — 준비가 된 공고 위주로"
    return "준비하며 다음 기회 — 좋은 달을 노리기"


def move_luck(saju: dict, apply_date: date | None = None) -> dict:
    """apply_date(기본 오늘)에 지원하면 이직운이 어떤지 + 앞으로 12개월 달별 점수."""
    today = apply_date or date.today()
    y, m, _ = _gapja_of_solar(today)
    score, notes = _luck_score(saju, y, m)

    months = []
    for i in range(12):
        yy, mm = divmod(today.month - 1 + i, 12)
        d = date(today.year + yy, mm + 1, 15)          # 그 달 15일의 간지로 월운을 봄
        gy, gm, _ = _gapja_of_solar(d)
        s, _n = _luck_score(saju, gy, gm)
        months.append({"ym": f"{d.year}-{d.month:02d}", "gz": f"{gy}년 {gm}월", "score": s})
    best = sorted(months, key=lambda x: -x["score"])[:3]
    return {
        "date": today.isoformat(), "year_gz": y, "month_gz": m,
        "score": score, "verdict": _verdict(score), "notes": notes,
        "months": months, "best": sorted(best, key=lambda x: x["ym"]),
    }


STEM_HAP = [{"갑", "기"}, {"을", "경"}, {"병", "신"}, {"정", "임"}, {"무", "계"}]   # 천간합
# 마감일 월주·년주 천간이 나(일간)에게 주는 보조 점수: 생해줌 / 비화 / 내가 생함 / 내가 극함 / 극당함
SUB_POINTS = {"월": {"인성": 4, "비겁": 2, "식상": 1, "재성": -1, "관성": -3},
              "년": {"인성": 2, "비겁": 1, "식상": 0, "재성": 0, "관성": -2}}
RAW_MIN, RAW_MAX = 7, 129   # 아래 가감을 모두 합한 이론상 최저·최고점


def affinity(saju: dict, deadline: str) -> dict:
    """구직자 사주 vs 공고 마감일 사주로 이직 인연 %(5~99)를 냅니다.
    중심은 일주끼리의 궁합, 여기에 천간합·월주/년주 기운·월지 관계를 더해 잘게 나눕니다."""
    dl = date.fromisoformat(deadline)
    dl_year, dl_month, dl_day = _gapja_of_solar(dl)
    me_elem = saju["day_master_elem"]
    dl_elem = STEM_ELEM[STEMS.index(dl_day[0])]

    if dl_elem == me_elem:
        score, rel = 70, f"같은 {me_elem} 기운 (비화: 서로 힘이 됨)"
    elif GENERATES[dl_elem] == me_elem:
        score, rel = 95, f"마감일의 {dl_elem}이(가) 나의 {me_elem}을(를) 살림 (상생: 회사가 나를 도움)"
    elif GENERATES[me_elem] == dl_elem:
        score, rel = 80, f"나의 {me_elem}이(가) 마감일의 {dl_elem}을(를) 살림 (상생: 내가 회사에 기여)"
    elif CONTROLS[me_elem] == dl_elem:
        score, rel = 55, f"나의 {me_elem}이(가) 마감일의 {dl_elem}을(를) 누름 (상극: 주도권은 나)"
    else:
        score, rel = 35, f"마감일의 {dl_elem}이(가) 나의 {me_elem}을(를) 누름 (상극: 부담이 큼)"

    notes = [rel]
    pair = {saju["day_branch"], dl_day[1]}
    if pair in SIX_HARMONY:
        score += 10
        notes.append(f"일지 {saju['day_branch']}·{dl_day[1]} 육합 (+10)")
    elif any(pair <= g for g in THREE_HARMONY) and len(pair) == 2:
        score += 5
        notes.append(f"일지 {saju['day_branch']}·{dl_day[1]} 삼합 (+5)")
    if abs(BRANCHES.index(saju["day_branch"]) - BRANCHES.index(dl_day[1])) == 6:
        score -= 20
        notes.append(f"일지 {saju['day_branch']}·{dl_day[1]} 충 (-20)")
    if dl_elem == saju["weakest"]:
        score += 10
        notes.append(f"부족한 {dl_elem} 기운을 채워줌 (+10)")

    # ── 세부 가감 (동점을 줄이기 위한 보조 궁합) ──
    if {saju["day_master"], dl_day[0]} in STEM_HAP:
        score += 5
        notes.append(f"일간 {saju['day_master']}·{dl_day[0]} 천간합 (+5)")
    for label, gz in (("월", dl_month), ("년", dl_year)):
        role = element_role(me_elem, STEM_ELEM[STEMS.index(gz[0])])
        pts = SUB_POINTS[label][role]
        if pts:
            score += pts
            notes.append(f"마감 {label}주 {gz}: 나에게 {role} ({pts:+d})")
    my_month_branch = next(p["gz"][1] for p in saju["pillars"] if p["name"] == "월주")
    if {my_month_branch, dl_day[1]} in SIX_HARMONY:
        score += 3
        notes.append(f"내 월지 {my_month_branch}·마감 일지 {dl_day[1]} 육합 (+3)")
    elif abs(BRANCHES.index(my_month_branch) - BRANCHES.index(dl_day[1])) == 6:
        score -= 3
        notes.append(f"내 월지 {my_month_branch}·마감 일지 {dl_day[1]} 충 (-3)")

    percent = round(5 + 94 * (score - RAW_MIN) / (RAW_MAX - RAW_MIN))
    return {"score": max(5, min(99, percent)), "raw": score, "deadline_gz": dl_day, "notes": notes}


def affinity_story(saju: dict, deadline: str) -> list[dict]:
    """'왜 이 회사와 인연이 높은가'를 내 사주의 여러 관점으로 풀어 줌 (점수는 바꾸지 않는 설명용).
    각 항목: {title, text, tone: good|soso|bad}"""
    dl = date.fromisoformat(deadline)
    dl_year, dl_month, dl_day = _gapja_of_solar(dl)
    me, me_elem = saju["day_master"], saju["day_master_elem"]
    co_elem = STEM_ELEM[STEMS.index(dl_day[0])]
    out = []

    # 1) 일간 궁합: 나 vs 회사(마감일)
    if GENERATES[co_elem] == me_elem:
        t, tone = f"회사의 {co_elem}({HANJA[co_elem]}) 기운이 나의 {me_elem}({HANJA[me_elem]})을 살려 줘요. 회사가 나를 키워 주는 관계예요.", "good"
    elif GENERATES[me_elem] == co_elem:
        t, tone = f"나의 {me_elem} 기운이 회사의 {co_elem}을 살려 줘요. 내 실력이 회사 성과로 바로 이어지는 관계예요.", "good"
    elif co_elem == me_elem:
        t, tone = f"나와 회사가 같은 {me_elem} 기운이에요. 문화가 비슷해 적응이 빠르지만, 같은 자리를 놓고 경쟁도 있어요.", "soso"
    elif CONTROLS[me_elem] == co_elem:
        t, tone = f"나의 {me_elem}이 회사의 {co_elem}을 다스려요. 내가 주도권을 쥐는 관계라 협상(연봉·직급)에 유리해요.", "soso"
    else:
        t, tone = f"회사의 {co_elem}이 나의 {me_elem}을 눌러요. 규율이 강하고 부담이 큰 관계예요.", "bad"
    out.append({"title": f"① 일간 궁합 — 나 {me}({me_elem}) × 회사 {dl_day[0]}({co_elem})", "text": t, "tone": tone})

    # 2) 십성: 회사 기운이 나에게 어떤 별인가
    role = element_role(me_elem, co_elem)
    role_txt = {"관성": "직장·직책의 별이에요. 조직에 자리를 잡는 인연이 강해요.",
                "인성": "도와주는 사람·합격 문서의 별이에요. 추천인·인맥을 통한 입사와 잘 맞아요.",
                "재성": "성과·연봉의 별이에요. 보상 협상에서 얻는 것이 많아요.",
                "식상": "실력 발휘의 별이에요. 기술을 보여 주는 과제·코딩 테스트에서 강해요.",
                "비겁": "나와 같은 힘(경쟁자)의 별이에요. 동료와 함께 성장하지만 경쟁도 치열해요."}[role]
    out.append({"title": f"② 회사 기운의 역할 — 나에게 {role}", "text": role_txt,
                "tone": "good" if role in ("관성", "인성", "재성") else "soso" if role == "식상" else "bad"})

    # 3) 오행 보완: 내 부족한/넘치는 기운
    if co_elem == saju["weakest"]:
        out.append({"title": "③ 오행 보완", "tone": "good",
                    "text": f"내 사주에서 가장 부족한 {co_elem}({HANJA[co_elem]})을 회사가 채워 줘요. 들어가면 균형이 맞춰지는 곳이에요."})
    elif co_elem == saju["strongest"]:
        out.append({"title": "③ 오행 보완", "tone": "soso",
                    "text": f"이미 가장 많은 {co_elem} 기운이 더해져요. 장점은 커지지만 한쪽으로 치우칠 수 있어요."})
    else:
        out.append({"title": "③ 오행 보완", "tone": "soso",
                    "text": f"회사 기운({co_elem})은 내 사주에 {saju['elements'][co_elem]}개 있어 무난한 수준이에요."})

    # 4) 물(水) 흐름: 회사 쪽 간지에 물이 있는가
    co_water = sum(1 for g in (dl_year, dl_month, dl_day)
                   for e in (STEM_ELEM[STEMS.index(g[0])], BRANCH_ELEM[BRANCHES.index(g[1])]) if e == "수")
    my_water = saju["elements"]["수"]
    w_role = element_role(me_elem, "수")
    if co_water and my_water <= 1:
        out.append({"title": "④ 물(水) 흐름", "tone": "good",
                    "text": f"내 물이 {my_water}개로 부족한데 회사 쪽 날짜에 물이 {co_water}개 있어요. 막힌 흐름을 풀어 주는 회사예요 (물 = 나에게 {w_role})."})
    elif co_water and my_water >= 4:
        out.append({"title": "④ 물(水) 흐름", "tone": "bad",
                    "text": f"내 물이 이미 {my_water}개로 많은데 회사 쪽에도 물이 {co_water}개 있어요. 고민이 길어질 수 있어요."})
    else:
        out.append({"title": "④ 물(水) 흐름", "tone": "soso",
                    "text": f"내 물 {my_water}개, 회사 쪽 물 {co_water}개 — 물의 흐름은 크게 바뀌지 않아요."})

    # 5) 지지 관계: 일지(나의 자리) · 월지(사회 환경)
    my_mb = next(p["gz"][1] for p in saju["pillars"] if p["name"] == "월주")
    bits, tone = [], "soso"
    pair = {saju["day_branch"], dl_day[1]}
    if pair in SIX_HARMONY:
        bits.append(f"일지 {saju['day_branch']}·{dl_day[1]} 육합 — 마음이 잘 맞는 자리"); tone = "good"
    elif len(pair) == 2 and any(pair <= g for g in THREE_HARMONY):
        bits.append(f"일지 {saju['day_branch']}·{dl_day[1]} 삼합 — 같은 목표로 뭉치는 팀"); tone = "good"
    if abs(BRANCHES.index(saju["day_branch"]) - BRANCHES.index(dl_day[1])) == 6:
        bits.append(f"일지 {saju['day_branch']}·{dl_day[1]} 충 — 환경 변화가 큼"); tone = "bad"
    if {my_mb, dl_day[1]} in SIX_HARMONY:
        bits.append(f"월지 {my_mb}·{dl_day[1]} 육합 — 일하는 방식이 맞음")
    if {me, dl_day[0]} in STEM_HAP:
        bits.append(f"일간 {me}·{dl_day[0]} 천간합 — 첫인상·면접 궁합이 좋음"); tone = "good"
    out.append({"title": "⑤ 합·충 (자리·환경)", "tone": tone,
                "text": " · ".join(bits) if bits else "특별한 합·충이 없어 무난해요."})

    # 6) 마감 달 이직운
    luck, _ = _luck_score(saju, dl_year, dl_month)
    out.append({"title": f"⑥ 마감 달 이직운 — {dl_year}년 {dl_month}월", "tone": "good" if luck >= 70 else "soso" if luck >= 50 else "bad",
                "text": f"마감 달의 이직운은 {luck}점({_verdict(luck)})이에요."})
    return out
