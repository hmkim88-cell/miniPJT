r"""링크드인 공고 직종·직급 분류 회귀 시험 (직무명 81개: 규칙 맞춤 51 + 처음 보는 30).
실행:  ..\.venv\Scripts\python tests\test_linkedin_matching.py   (mini-pjt 폴더에서)  → 모두 맞으면 'OK 81/81'
규칙(app/linkedin_jobs.py TITLE_RULES · classify_tier)을 바꾼 뒤 꼭 돌려 보기."""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import linkedin_import as li

CASES = [
    ("Software Engineer II", {"개발"}, {"주니어"}),
    ("Staff Software Engineer", {"개발"}, {"리더"}),
    ("Principal Engineer", {"개발"}, {"리더"}),
    ("Frontend Developer", {"개발"}, {"주니어"}),
    ("iOS Engineer", {"개발"}, {"주니어"}),
    ("Engineering Manager, Payments", {"개발"}, {"리더"}),
    ("Intern, Software Engineering", {"개발"}, {"일반"}),
    ("New Grad Software Engineer", {"개발"}, {"일반"}),
    ("Senior Backend Engineer (Java/Kotlin)", {"개발"}, {"시니어"}),
    ("Data Scientist", {"데이터·AI"}, {"주니어"}),
    ("Machine Learning Engineer", {"데이터·AI"}, {"주니어"}),
    ("AI Research Scientist", {"데이터·AI"}, {"주니어"}),
    ("Analytics Engineer", {"데이터·AI"}, {"주니어"}),
    ("Lead Data Engineer", {"데이터·AI"}, {"리더"}),
    ("Site Reliability Engineer", {"인프라·클라우드"}, {"주니어"}),
    ("Cloud Engineer", {"인프라·클라우드"}, {"주니어"}),
    ("Security Engineer", {"인프라·클라우드"}, {"주니어"}),
    ("Platform Engineer", {"인프라·클라우드", "개발"}, {"주니어"}),
    ("Senior Account Executive, Enterprise", {"세일즈"}, {"시니어"}),
    ("Account Manager - Strategic Accounts", {"세일즈"}, {"주니어"}),
    ("Sales Development Representative", {"세일즈"}, {"일반", "주니어"}),
    ("Business Development Manager", {"세일즈"}, {"주니어"}),
    ("Partner Development Manager", {"세일즈"}, {"주니어"}),
    ("Channel Account Manager", {"세일즈"}, {"주니어"}),
    ("Head of Sales, Korea", {"세일즈"}, {"리더"}),
    ("Director, Partnerships APAC", {"세일즈"}, {"리더"}),
    ("Country Manager, Korea", {"세일즈", "기타"}, {"리더"}),
    ("Solutions Architect", {"프리세일즈", "인프라·클라우드"}, {"주니어"}),
    ("Pre-Sales Consultant", {"프리세일즈"}, {"주니어"}),
    ("Sales Engineer", {"프리세일즈"}, {"주니어"}),
    ("Customer Engineer", {"프리세일즈"}, {"주니어"}),
    ("Associate Solutions Engineer", {"프리세일즈"}, {"주니어"}),
    ("Technical Account Manager", {"고객 성공"}, {"주니어"}),
    ("Customer Success Manager", {"고객 성공"}, {"주니어"}),
    ("Implementation Manager", {"딜리버리"}, {"주니어"}),
    ("Professional Services Consultant", {"딜리버리"}, {"주니어"}),
    ("Engagement Manager", {"딜리버리"}, {"주니어"}),
    ("Technical Program Manager", {"딜리버리"}, {"주니어"}),
    ("Marketing Manager", {"기타"}, {"주니어"}),
    ("Recruiter", {"기타"}, {"주니어"}),
    ("Product Manager", {"기타"}, {"주니어"}),
    # 한글 공고
    ("백엔드 개발자 (5년 이상)", {"개발"}, {"시니어"}),
    ("기술영업 (Pre-sales)", {"프리세일즈"}, {"주니어"}),
    ("영업 대표 (Account Executive)", {"세일즈"}, {"주니어"}),
    ("고객성공 매니저", {"고객 성공"}, {"주니어"}),
    ("데이터 엔지니어 (3년 이상)", {"데이터·AI"}, {"주니어"}),
    ("프로젝트 매니저 (PM)", {"딜리버리"}, {"주니어"}),
    ("인사담당자 (HRBP)", {"기타"}, {"주니어"}),
    ("클라우드 엔지니어", {"인프라·클라우드"}, {"주니어"}),
    ("영업팀장", {"세일즈"}, {"리더"}),
    ("신입 웹 개발자", {"개발"}, {"일반"}),
    # ── 처음 보는 30개 ──
    ("Senior Full Stack Engineer", {"개발"}, {"시니어"}),
    ("Android Developer", {"개발"}, {"주니어"}),
    ("Backend Engineer, Growth", {"개발"}, {"주니어"}),
    ("Software Development Engineer in Test", {"개발"}, {"주니어"}),
    ("Tech Lead, Mobile", {"개발"}, {"리더"}),
    ("Junior Java Developer", {"개발"}, {"주니어"}),
    ("Senior Data Analyst", {"데이터·AI"}, {"시니어"}),
    ("Applied Scientist, NLP", {"데이터·AI"}, {"주니어"}),
    ("MLOps Engineer", {"데이터·AI", "인프라·클라우드"}, {"주니어"}),
    ("Generative AI Engineer", {"데이터·AI"}, {"주니어"}),
    ("DevOps Engineer (Kubernetes)", {"인프라·클라우드"}, {"주니어"}),
    ("Senior Cloud Security Architect", {"인프라·클라우드"}, {"시니어"}),
    ("Network Engineer", {"인프라·클라우드"}, {"주니어"}),
    ("Enterprise Account Executive, Financial Services", {"세일즈"}, {"주니어"}),
    ("Inside Sales Representative", {"세일즈"}, {"주니어", "일반"}),
    ("Strategic Alliances Manager", {"세일즈"}, {"주니어"}),
    ("Regional Sales Director", {"세일즈"}, {"리더"}),
    ("Key Account Manager", {"세일즈"}, {"주니어"}),
    ("Senior Solutions Engineer", {"프리세일즈"}, {"시니어"}),
    ("Presales Solution Architect", {"프리세일즈"}, {"주니어"}),
    ("Customer Success Lead", {"고객 성공"}, {"리더"}),
    ("Technical Support Engineer", {"고객 성공"}, {"주니어"}),
    ("Implementation Specialist", {"딜리버리"}, {"주니어"}),
    ("Senior Project Manager, Cloud Migration", {"딜리버리"}, {"시니어"}),
    ("Delivery Lead", {"딜리버리"}, {"리더"}),
    ("Talent Partner", {"기타"}, {"주니어"}),
    ("Product Marketing Manager", {"기타"}, {"주니어"}),
    ("영업관리 담당 (B2B, 7년 이상)", {"세일즈"}, {"시니어"}),
    ("머신러닝 엔지니어", {"데이터·AI"}, {"주니어"}),
    ("SI 프로젝트 PM (10년 이상)", {"딜리버리"}, {"리더"}),
]


def main() -> int:
    jobs = [{"title": t, "company": "C", "location": "", "job_id": str(i), "url": "", "date": "", "kind": "alert"} for i, (t, _, _) in enumerate(CASES)]
    out = {j["job_id"]: j for j in li.analyze(jobs, {})}
    bad = []
    for i, (t, fams, tiers) in enumerate(CASES):
        r = out[str(i)]
        if r["family"] not in fams or r["tier"] not in tiers:
            bad.append(f"  {t} → {r['family']} · {r['tier']}  (정답 {'/'.join(fams)} · {'/'.join(tiers)})")
    print(("OK" if not bad else "FAIL") + f" {len(CASES) - len(bad)}/{len(CASES)}")
    print("\n".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())