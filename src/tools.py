"""회의실 안내 도구 (1일차: 2개).

- find_rooms_by_capacity : 인원으로 찾기
- get_room_detail        : 이름으로 상세 조회
예약 조회 도구는 2일차에 추가합니다.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool

# 이 파일 위치 기준으로 data/rooms.json 을 찾으므로 어느 폴더에서 실행해도 됩니다
ROOMS_PATH = Path(__file__).resolve().parents[1] / "data" / "rooms.json"


@lru_cache(maxsize=1)
def load_rooms() -> list[dict]:
    """rooms.json 을 한 번만 읽어 둡니다."""
    return json.loads(ROOMS_PATH.read_text(encoding="utf-8"))


def _line(r: dict) -> str:
    return f"{r['name']} ({r['floor']}층, 최대 {r['capacity']}명)"


@tool
def find_rooms_by_capacity(people: int) -> str:
    """참석 인원으로 들어갈 수 있는 회의실을 찾습니다.
    사용자가 '8명이 쓸 방', '10명 회의할 곳'처럼 인원을 말할 때 사용하세요.
    people: 참석 인원 수 (정수). 이 인원 이상 수용 가능한 방을 작은 방부터 돌려줍니다.
    예약 여부는 알 수 없습니다."""
    if people < 1:
        return "인원은 1명 이상이어야 합니다."
    rooms = sorted((r for r in load_rooms() if r["capacity"] >= people), key=lambda r: r["capacity"])
    if not rooms:
        biggest = max(load_rooms(), key=lambda r: r["capacity"])
        return f"{people}명이 들어갈 회의실이 없습니다. 가장 큰 방은 {_line(biggest)}입니다."
    return f"{people}명 이상 수용 가능한 회의실 {len(rooms)}곳 (작은 순):\n" + "\n".join(f"- {_line(r)}" for r in rooms)


@tool
def get_room_detail(name: str) -> str:
    """회의실 이름으로 상세 정보(층, 수용 인원, 장비, 특징)를 조회합니다.
    사용자가 특정 회의실 이름을 말하거나, 찾은 목록 중 한 방을 더 알고 싶을 때 사용하세요.
    name: 회의실 이름 (예: '설악', '백두'). '설악실'처럼 붙여 써도 찾습니다."""
    key = name.strip().removesuffix("회의실").removesuffix("실").strip()
    room = next((r for r in load_rooms() if r["name"] == key), None)
    if room is None:
        names = ", ".join(r["name"] for r in load_rooms())
        return f"'{name}' 회의실은 없습니다. 있는 회의실: {names}"
    return (f"{room['name']} 회의실\n- 위치: {room['floor']}층\n- 수용 인원: 최대 {room['capacity']}명\n"
            f"- 장비: {', '.join(room['equipment'])}\n- 특징: {room['note']}")


TOOLS = [find_rooms_by_capacity, get_room_detail]
