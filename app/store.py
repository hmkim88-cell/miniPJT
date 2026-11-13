"""데이터 저장 — 오래 운영할 수 있게 'DB 주소만 바꾸면 옮겨 가는' 구조 (SQLAlchemy).

  · 기본(개발): SQLite 파일  mini-pjt/data/careerfate.db
  · 운영(장기): PostgreSQL — AWS RDS·Supabase 등. ..\\.env 에 한 줄만 넣으면 됨
        DATABASE_URL=postgresql+psycopg://사용자:비밀번호@호스트:5432/DB이름
    (값은 출력·커밋 금지. 표는 처음 연결할 때 자동으로 만들어짐)

저장하는 것: 구인자가 등록한 공고(job) · 연결 요청(application) · 추천 요청(referral)
            + 구직자 레주메(동의한 경우만, 암호화해서 별도 표 careerfate_resumes — resumes.py 참고)
저장하지 않는 것: 사주 결과·생년월일(요청마다 계산), 링크드인 세션(보안상 메모리에만)
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

from contextlib import nullcontext

from sqlalchemy import Column, DateTime, Index, Integer, MetaData, String, Table, Text, create_engine, delete as sa_delete, func, select

DEFAULT_SQLITE = Path(__file__).resolve().parents[1] / "data" / "careerfate.db"
_meta = MetaData()
records = Table(
    "careerfate_records", _meta,
    Column("kind", String(32), primary_key=True),      # job / application / referral
    Column("id", Integer, primary_key=True),
    Column("data", Text, nullable=False),               # 내용(JSON 글자)
    Column("updated_at", DateTime, nullable=False),
)
# 구직자 레주메 (장기 보관): 주인 식별값은 해시만, 내용은 암호문만 저장
resumes = Table(
    "careerfate_resumes", _meta,
    Column("owner", String(80), primary_key=True),       # 쿠키 토큰 또는 링크드인 이메일의 SHA-256 (원문 저장 안 함)
    Column("data_enc", Text, nullable=False),             # 레주메 내용(JSON)을 암호화한 글자
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("expires_at", DateTime, nullable=False),       # 보관 기한 (지나면 자동 삭제)
)
Index("ix_resumes_expires_at", resumes.c.expires_at)     # 기한 지난 레주메를 빨리 찾아 지우기 (사람이 많아져도)
Index("ix_records_kind_updated", records.c.kind, records.c.updated_at)
_engine = None
_sqlite_lock = threading.Lock()   # SQLite(파일 DB)는 동시에 한 곳만 쓰기 → 그때만 줄 세움


def _lock_ctx():
    """SQLite일 때만 잠금. PostgreSQL은 DB가 동시 처리를 하므로 잠그지 않음(사용자가 많아져도 병목 없음)."""
    return _sqlite_lock if engine().dialect.name == "sqlite" else nullcontext()


def engine():
    """처음 쓸 때 DB에 연결하고 표를 만듦 (DATABASE_URL 없으면 SQLite 파일)."""
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL", "").strip()
        if not url:
            DEFAULT_SQLITE.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{DEFAULT_SQLITE.as_posix()}"
        elif url.startswith("postgres://"):          # 일부 서비스가 주는 옛 형식 주소 보정
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        if url.startswith("sqlite"):
            _engine = create_engine(url, future=True)
        else:   # 운영 DB: 연결을 재사용(pool)해 요청이 많아도 빠르게
            _engine = create_engine(url, future=True, pool_pre_ping=True, pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
                                    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")), pool_recycle=1800)
        _meta.create_all(_engine)
    return _engine


def backend() -> str:
    return engine().dialect.name   # sqlite / postgresql


def save(kind: str, rid: int, data: dict) -> None:
    """같은 종류·번호가 있으면 바꿔 쓰기 (상태 변경도 이걸로 저장). 어느 DB에서나 같은 방식."""
    with _lock_ctx(), engine().begin() as con:
        con.execute(sa_delete(records).where(records.c.kind == kind, records.c.id == rid))
        con.execute(records.insert().values(kind=kind, id=rid, data=json.dumps(data, ensure_ascii=False),
                                            updated_at=datetime.now()))


def load(kind: str) -> list[dict]:
    with _lock_ctx(), engine().connect() as con:
        rows = con.execute(select(records.c.data).where(records.c.kind == kind).order_by(records.c.id)).all()
    return [json.loads(r[0]) for r in rows]


def delete(kind: str, rid: int) -> None:
    with _lock_ctx(), engine().begin() as con:
        con.execute(sa_delete(records).where(records.c.kind == kind, records.c.id == rid))


def counts() -> dict[str, int]:
    with _lock_ctx(), engine().connect() as con:
        rows = con.execute(select(records.c.kind, func.count()).group_by(records.c.kind)).all()
    return {k: n for k, n in rows}


# ---------- 구직자 레주메 표 ----------
def resume_get(owner: str) -> dict | None:
    with _lock_ctx(), engine().connect() as con:
        r = con.execute(select(resumes).where(resumes.c.owner == owner)).mappings().first()
    return dict(r) if r else None


def resume_put(owner: str, data_enc: str, version: int, created_at: datetime, expires_at: datetime) -> None:
    with _lock_ctx(), engine().begin() as con:
        con.execute(sa_delete(resumes).where(resumes.c.owner == owner))
        con.execute(resumes.insert().values(owner=owner, data_enc=data_enc, version=version, created_at=created_at,
                                            updated_at=datetime.now(), expires_at=expires_at))


def resume_delete(owner: str) -> int:
    with _lock_ctx(), engine().begin() as con:
        return con.execute(sa_delete(resumes).where(resumes.c.owner == owner)).rowcount


def resume_purge_expired() -> int:
    """보관 기한이 지난 레주메 자동 삭제."""
    with _lock_ctx(), engine().begin() as con:
        return con.execute(sa_delete(resumes).where(resumes.c.expires_at < datetime.now())).rowcount


def resume_count() -> int:
    with _lock_ctx(), engine().connect() as con:
        return con.execute(select(func.count()).select_from(resumes)).scalar() or 0
