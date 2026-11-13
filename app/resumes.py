"""구직자 레주메 장기 보관 — 동의한 사람만, 암호화해서, 기한을 두고, 언제든 삭제.

· 동의: 화면의 "레주메 보관에 동의" 체크가 있어야만 저장 (consent=True)
· 주인 확인: 링크드인으로 본인 확인했으면 이메일 기준(다른 브라우저에서도 불러오기 가능),
            아니면 이 브라우저의 쿠키(cr_owner) 기준. DB에는 둘 다 SHA-256 해시만 저장
· 암호화: Fernet(AES) — 키는 ..\\.env 의 RESUME_ENC_KEY (없으면 개발용 키 파일 data/.resume.key 자동 생성)
          키를 잃어버리면 저장된 레주메를 읽을 수 없음 → 운영에서는 키를 안전한 곳(AWS Secrets Manager 등)에 보관
· 보관 기한: 마지막 저장 후 365일. 지나면 자동 삭제
· 이전 버전: 최근 5개까지 함께 보관 (되돌리기용)
· 생년월일·사주는 저장하지 않음. 구인자에게 레주메 원문을 보내지 않음
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request, Response

from . import linkedin, store

RETENTION_DAYS = 365
MAX_HISTORY = 5
COOKIE = "cr_owner"
KEY_FILE = Path(__file__).resolve().parents[1] / "data" / ".resume.key"
SAVE_FIELDS = ("resume_text", "linkedin_url", "expected_salary", "desired_level", "desired_family", "school", "hometown", "past_companies", "review", "resume_summary")
_fernet: Fernet | None = None


def _cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.getenv("RESUME_ENC_KEY", "").strip()
        if not key:   # 개발용: 키 파일을 한 번 만들어 계속 사용
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not KEY_FILE.exists():
                KEY_FILE.write_text(Fernet.generate_key().decode(), encoding="utf-8")
            key = KEY_FILE.read_text(encoding="utf-8").strip()
        _fernet = Fernet(key.encode())
    return _fernet


def key_source() -> str:
    return "env" if os.getenv("RESUME_ENC_KEY", "").strip() else "dev-file"


def _h(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def owner_of(request: Request) -> tuple[str | None, str]:
    """(DB에 쓰는 주인 해시, 방식). 링크드인 확인이 우선, 없으면 쿠키."""
    u = linkedin.current_user(request)
    if u and u.get("email"):
        return "li:" + _h(u["email"].strip().lower()), "linkedin"
    tok = request.cookies.get(COOKIE)
    return ("ck:" + _h(tok), "cookie") if tok else (None, "cookie")


def _ensure_cookie(request: Request, response: Response) -> str:
    """쿠키가 없으면 새로 만들어 붙이고 주인 해시를 돌려줌."""
    owner, how = owner_of(request)
    if owner:
        return owner
    tok = secrets.token_urlsafe(32)
    response.set_cookie(COOKIE, tok, max_age=RETENTION_DAYS * 86400, httponly=True, samesite="lax")
    return "ck:" + _h(tok)


def _meta(row: dict, data: dict, how: str) -> dict:
    rv = data.get("review") or {}
    return {"saved": True, "version": row["version"], "owner_type": how,
            "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M"), "updated_at": row["updated_at"].strftime("%Y-%m-%d %H:%M"),
            "expires_at": row["expires_at"].strftime("%Y-%m-%d"), "chars": len(data.get("resume_text") or ""),
            "skills": len(rv.get("skills") or []), "history": len(data.get("history") or [])}


def load(request: Request) -> dict:
    store.resume_purge_expired()
    owner, how = owner_of(request)
    row = store.resume_get(owner) if owner else None
    if not row:
        return {"saved": False, "owner_type": how}
    try:
        data = json.loads(_cipher().decrypt(row["data_enc"].encode()))
    except InvalidToken:   # 암호화 키가 바뀐 경우
        return {"saved": False, "owner_type": how, "error": "암호화 키가 달라 저장된 레주메를 열 수 없어요."}
    out = {k: data.get(k) for k in SAVE_FIELDS}
    # 이전 버전 목록 (본인만): 번호·저장일·글자 수 + 글 (되돌리기용)
    hist = [{"version": h.get("version"), "saved_at": h.get("saved_at"), "chars": len(h.get("resume_text") or ""),
             "resume_text": h.get("resume_text")} for h in (data.get("history") or [])]
    return {**_meta(row, data, how), "data": out, "history_list": hist}


def save(request: Request, response: Response, payload: dict) -> dict:
    owner = _ensure_cookie(request, response)
    _, how = owner_of(request)
    new = {k: payload.get(k) for k in SAVE_FIELDS}
    if not (new.get("resume_text") or "").strip():
        raise ValueError("저장할 레주메 내용이 없어요.")
    if len(new["resume_text"]) > 20000:
        raise ValueError("레주메는 2만 자까지 저장할 수 있어요.")
    old_row = store.resume_get(owner)
    history, version, created = [], 1, datetime.now()
    if old_row:
        try:
            old = json.loads(_cipher().decrypt(old_row["data_enc"].encode()))
            if (old.get("resume_text") or "") != new["resume_text"]:   # 글이 바뀐 경우만 이전 버전으로 보관
                history = ([{"version": old_row["version"], "saved_at": old_row["updated_at"].strftime("%Y-%m-%d %H:%M"),
                             "resume_text": old.get("resume_text")}] + (old.get("history") or []))[:MAX_HISTORY]
            else:
                history = old.get("history") or []
        except InvalidToken:
            history = []
        version, created = old_row["version"] + 1, old_row["created_at"]
    new["history"] = history
    enc = _cipher().encrypt(json.dumps(new, ensure_ascii=False).encode()).decode()
    store.resume_put(owner, enc, version, created, datetime.now() + timedelta(days=RETENTION_DAYS))
    return _meta(store.resume_get(owner), new, how)


def delete(request: Request, response: Response) -> dict:
    owner, how = owner_of(request)
    n = store.resume_delete(owner) if owner else 0
    return {"deleted": bool(n), "owner_type": how}
