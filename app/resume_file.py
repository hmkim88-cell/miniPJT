"""레주메 파일에서 글자만 뽑기 — PDF · Word(.docx) · 텍스트(.txt/.md).

· 파일 자체는 저장하지 않음 (메모리에서 글자만 뽑고 버림)
· 뽑은 글은 화면의 입력칸에 넣어 지원자가 직접 확인·수정한 뒤 분석
· 스캔한 이미지 PDF는 글자가 없어 읽을 수 없음 → 안내
"""
from __future__ import annotations

import io
import re

MAX_BYTES = 5 * 1024 * 1024        # 5MB
MAX_CHARS = 20000                  # 보관 한도와 같게
TYPES = {".pdf": "PDF", ".docx": "Word", ".txt": "텍스트", ".md": "텍스트"}


def _clean(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKC", text)   # PDF 합자(ﬁ·ﬂ)·전각 문자를 보통 글자로
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def _pdf(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    if r.is_encrypted:
        try:
            r.decrypt("")
        except Exception:  # noqa: BLE001
            raise ValueError("암호가 걸린 PDF는 읽을 수 없어요. 암호를 풀고 다시 올려 주세요.")
    return "\n".join((p.extract_text() or "") for p in r.pages), len(r.pages)


def _docx(data: bytes) -> tuple[str, int]:
    import docx
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:                       # 표로 만든 경력란도 읽기
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
    return "\n".join(parts), 0


def _txt(data: bytes) -> tuple[str, int]:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc), 0
        except UnicodeDecodeError:
            continue
    raise ValueError("글자 인코딩을 알 수 없어요. UTF-8로 저장해 다시 올려 주세요.")


def extract(filename: str, data: bytes) -> dict:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in TYPES:
        raise ValueError("PDF, Word(.docx), 텍스트(.txt) 파일만 올릴 수 있어요. (.doc·한글 파일은 PDF로 저장해 주세요)")
    if not data:
        raise ValueError("빈 파일이에요.")
    if len(data) > MAX_BYTES:
        raise ValueError("파일은 5MB까지 올릴 수 있어요.")
    try:
        raw, pages = {".pdf": _pdf, ".docx": _docx}.get(ext, _txt)(data)
    except ValueError:
        raise
    except Exception:  # noqa: BLE001  (깨진 파일 등)
        raise ValueError(f"{TYPES[ext]} 파일을 읽지 못했어요. 파일이 손상되지 않았는지 확인해 주세요.")
    text = _clean(raw)
    # 링크드인 프로필 PDF('더보기 → PDF로 저장')인지와 프로필 주소 (본인이 내려받은 파일에서만 읽음)
    li_url = profile_url(text)
    li_pdf = bool(li_url) and bool(re.search(r"\(LinkedIn\)|Top Skills|주요 기술|Experience\b|경력\b", text))
    text = re.sub(r"(?im)^\s*page \d+ of \d+\s*$", "", text).strip()
    if len(text) < 30:
        raise ValueError("파일에서 글자를 거의 찾지 못했어요. 스캔한 이미지 PDF라면 글자를 복사해 붙여넣어 주세요.")
    cut = len(text) > MAX_CHARS
    return {"text": text[:MAX_CHARS], "chars": min(len(text), MAX_CHARS), "pages": pages,
            "type": TYPES[ext], "filename": filename[-80:], "truncated": cut, "linkedin_url": li_url, "linkedin_pdf": li_pdf,
            "job_urls": job_urls(data if ext == ".pdf" else b"", text)[:20]}   # 링크드인 공고 PDF면 공고 주소도


_JOB_LINK = re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?#\s]*-)?(\d{6,})", re.I)


def pdf_text_with_links(data: bytes) -> str:
    """PDF 글자를 줄 단위로 읽고, 링크(주석)가 걸린 줄 바로 아래에 그 링크 주소를 끼워 넣음.
    PDF로 저장하면 링크 주소는 글자에 안 나오고 '링크 영역'으로만 남기 때문 → 링크드인 채용 알림·검색 결과 PDF에서 직무명과 공고 링크를 짝지음."""
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    if r.is_encrypted:
        try:
            r.decrypt("")
        except Exception:  # noqa: BLE001
            raise ValueError("암호가 걸린 PDF는 읽을 수 없어요.")
    out: list[str] = []
    for page in r.pages:
        segs: list[tuple[float, float, str]] = []

        def visit(text, cm, tm, *_):
            if text and text.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                segs.append((y, x, text))
        try:
            page.extract_text(visitor_text=visit)
        except Exception:  # noqa: BLE001
            continue
        rows: dict[int, list[tuple[float, str]]] = {}
        for y, x, t in segs:   # 같은 높이(±2pt)의 조각을 한 줄로
            k = next((kk for kk in rows if abs(kk - y) <= 2), round(y))
            rows.setdefault(k, []).append((x, t))
        ys = sorted(rows, reverse=True)
        lines = [_clean("".join(t for _, t in sorted(rows[y]))).replace("\n", " ") for y in ys]
        links: dict[int, list[str]] = {}
        for a in page.get("/Annots") or []:
            try:
                o = a.get_object()
                uri = (o.get("/A") or {}).get("/URI")
                rect = [float(v) for v in o.get("/Rect")]
            except Exception:  # noqa: BLE001
                continue
            if not uri or not _JOB_LINK.search(str(uri)) or not ys:
                continue
            yc = (rect[1] + rect[3]) / 2
            i = min(range(len(ys)), key=lambda n: abs(ys[n] - yc))
            if abs(ys[i] - yc) <= max(6, abs(rect[3] - rect[1])):
                links.setdefault(i, []).append(str(uri))
        for i, ln in enumerate(lines):
            out.append(ln)
            for u in links.get(i, [])[:1]:
                out.append(u)
    return "\n".join(x for x in out if x.strip())


def job_urls(data: bytes, text: str) -> list[str]:
    """PDF 링크 영역 + 글자에서 링크드인 공고 주소(정리된 모양) 목록."""
    found = []
    try:
        from pypdf import PdfReader
        for page in PdfReader(io.BytesIO(data)).pages:
            for a in page.get("/Annots") or []:
                uri = str(((a.get_object().get("/A") or {}).get("/URI")) or "")
                m = _JOB_LINK.search(uri)
                if m:
                    found.append(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    found += [m.group(1) for m in _JOB_LINK.finditer(text or "")]
    return [f"https://www.linkedin.com/jobs/view/{i}/" for i in dict.fromkeys(found)]


_PROFILE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.|www\.)?linkedin\.com/in/([A-Za-z0-9\-_%]{3,100})/?", re.I)


def profile_url(text_or_url: str) -> str:
    """링크드인 '내 프로필' 주소를 정해진 모양으로 (https://www.linkedin.com/in/아이디/). 없으면 빈 문자열."""
    m = _PROFILE.search(text_or_url or "")
    return f"https://www.linkedin.com/in/{m.group(1).strip('/')}/" if m else ""
