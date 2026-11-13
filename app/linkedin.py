"""내 링크드인 연결 — 공식 'Sign in with LinkedIn using OpenID Connect'.

받는 정보: 이름, 이메일, 프로필 사진 (링크드인이 일반 앱에 허용하는 범위).
경력·기술은 공식 API로 받을 수 없으므로 프로필 붙여넣기로 받습니다. 스크래핑은 하지 않습니다.

필요한 설정 (상위 폴더 ..\\.env, 값은 출력·커밋 금지):
    LINKEDIN_CLIENT_ID=...
    LINKEDIN_CLIENT_SECRET=...
    LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback   (선택, 기본값)
"""
from __future__ import annotations

import os
import secrets
import time
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPE = "openid profile email"

router = APIRouter()
PENDING: dict[str, float] = {}   # state -> 만든 시각 (CSRF 방지, 10분 유효)
SESSIONS: dict[str, dict] = {}   # 쿠키 sid -> 링크드인 사용자 정보 (서버 메모리, 데모)


def _cfg() -> tuple[str, str, str]:
    return (os.getenv("LINKEDIN_CLIENT_ID", ""), os.getenv("LINKEDIN_CLIENT_SECRET", ""),
            os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/auth/linkedin/callback"))


def configured() -> bool:
    cid, secret, _ = _cfg()
    return bool(cid and secret)


def _home(redirect_uri: str) -> str:
    u = urlparse(redirect_uri)
    return f"{u.scheme}://{u.netloc}/"


@router.get("/auth/linkedin/login")
def login(request: Request):
    cid, _, redirect_uri = _cfg()
    if not configured():
        return RedirectResponse("/?linkedin=not_configured")
    # 쿠키는 주소(호스트)별로 따로 저장되므로, 콜백 주소와 같은 호스트에서 시작하게 맞춤
    want = urlparse(redirect_uri).netloc
    if request.url.netloc != want:
        return RedirectResponse(f"{urlparse(redirect_uri).scheme}://{want}/auth/linkedin/login")
    state = secrets.token_urlsafe(24)
    PENDING[state] = time.time()
    q = urlencode({"response_type": "code", "client_id": cid, "redirect_uri": redirect_uri,
                   "state": state, "scope": SCOPE})
    return RedirectResponse(f"{AUTH_URL}?{q}")


@router.get("/auth/linkedin/callback")
def callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    cid, secret, redirect_uri = _cfg()
    home = _home(redirect_uri)
    if error:   # 사용자가 '취소'를 누른 경우 등
        return RedirectResponse(f"{home}?{urlencode({'linkedin': 'error', 'msg': error_description or error})}")
    made = PENDING.pop(state, None)
    if made is None or time.time() - made > 600:
        return RedirectResponse(f"{home}?linkedin=error&msg=state")
    try:
        tok = httpx.post(TOKEN_URL, data={"grant_type": "authorization_code", "code": code,
                                          "redirect_uri": redirect_uri, "client_id": cid,
                                          "client_secret": secret}, timeout=15)
        tok.raise_for_status()
        info = httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {tok.json()['access_token']}"},
                         timeout=15)
        info.raise_for_status()
    except Exception as e:  # noqa: BLE001
        return RedirectResponse(f"{home}?{urlencode({'linkedin': 'error', 'msg': type(e).__name__})}")
    u = info.json()
    sid = secrets.token_urlsafe(24)
    SESSIONS[sid] = {"name": u.get("name"), "email": u.get("email"), "picture": u.get("picture"),
                     "locale": u.get("locale"), "connected_at": time.strftime("%Y-%m-%d %H:%M")}
    resp = RedirectResponse(f"{home}?linkedin=ok")
    resp.set_cookie("li_sid", sid, httponly=True, samesite="lax", max_age=60 * 60 * 8)
    return resp


@router.get("/api/linkedin/me")
def me(request: Request):
    user = SESSIONS.get(request.cookies.get("li_sid", ""))
    return {"configured": configured(), "connected": bool(user), "user": user}


@router.post("/api/linkedin/logout")
def logout(request: Request):
    SESSIONS.pop(request.cookies.get("li_sid", ""), None)
    return {"connected": False}


def current_user(request: Request) -> dict | None:
    return SESSIONS.get(request.cookies.get("li_sid", ""))


def require_user(request: Request) -> dict:
    u = current_user(request)
    if not u:
        raise HTTPException(401, "링크드인 연결이 필요해요.")
    return u
